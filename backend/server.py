from fastapi import FastAPI, APIRouter, File, UploadFile, Form, HTTPException, Request, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import tempfile
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import base64
import re
import json
from openai import OpenAI
from auth import AuthService
from usage import UsageService
import audio_utils
import vad
import feature_extractor
import insights_generator
import prompt_builder

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI clients
# For Whisper (audio transcription) - use direct OpenAI API
openai_audio_client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY']
)

# For GPT-4 (text analysis) - use direct OpenAI API
openai_text_client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY']
)

# Initialize services
auth_service = AuthService(db)
usage_service = UsageService(db)

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Create the main app without a prefix
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class VoiceAnalysisRequest(BaseModel):
    audio_base64: str
    user_id: str
    recording_mode: str
    recording_time: int

class VoiceAnalysisResponse(BaseModel):
    assessment_id: str
    status: str
    message: str

class AssessmentStatus(BaseModel):
    assessment_id: str
    processed: bool
    results: Optional[Dict[str, Any]] = None

class SessionRequest(BaseModel):
    session_id: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "The Mirror Note API - Voice Assessment Platform"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# ============ AUTH ENDPOINTS ============
@api_router.post("/auth/session")
@limiter.limit("10/minute")
async def create_session(request: Request, request_data: SessionRequest, response: Response):
    """
    Exchange session_id from URL for session_token
    """
    return await auth_service.process_session_id(request_data.session_id, response)

@api_router.get("/auth/me")
@limiter.limit("60/minute")
async def get_me(request: Request):
    """
    Get current authenticated user
    """
    return await auth_service.get_current_user(request)

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """
    Logout user
    """
    return await auth_service.logout(request, response)

# ============ USAGE ENDPOINTS ============
@api_router.get("/usage")
async def get_usage(request: Request):
    """
    Get current user's usage statistics
    """
    user = await auth_service.get_current_user(request)
    return await usage_service.get_user_usage(user["id"])

# ============ VOICE ANALYSIS ENDPOINTS ============
@api_router.post("/analyze-voice", response_model=VoiceAnalysisResponse)
@limiter.limit("5/minute")
async def analyze_voice(request: Request, request_data: VoiceAnalysisRequest):
    """
    Analyzes voice recording using OpenAI Whisper and GPT-4
    """
    try:
        # Get authenticated user (required for usage tracking)
        user = await auth_service.get_current_user(request)
        user_id = user["id"]
        
        # Create assessment record
        assessment_id = str(uuid.uuid4())
        
        # Save initial assessment to database
        assessment = {
            "assessment_id": assessment_id,
            "user_id": user_id,
            "recording_mode": request_data.recording_mode,
            "recording_time": request_data.recording_time,
            "audio_data": request_data.audio_base64,
            "processed": False,
            "created_at": datetime.utcnow()
        }
        
        await db.assessments.insert_one(assessment)
        
        # Process audio in background (simplified for now - in production use Celery/background tasks)
        # For MVP, we'll process immediately
        try:
            # ===== NEW ACOUSTIC ANALYSIS PIPELINE =====
            
            # 1. Load audio from base64
            audio, sr = audio_utils.load_audio_from_base64(request_data.audio_base64, target_sr=16000)
            duration = audio_utils.get_audio_duration(audio, sr)
            
            # 2. Voice Activity Detection and timing analysis
            segments = vad.segment_speech(audio, sr)
            timing_metrics = vad.compute_timing_metrics(segments, duration)
            
            # 3. Extract all acoustic features
            acoustic_features = feature_extractor.extract_all_features(audio, sr, segments)
            
            # 4. Transcription with Whisper
            temp_wav_path = audio_utils.save_temp_wav(audio, sr)
            try:
                with open(temp_wav_path, "rb") as audio_file:
                    transcription_response = openai_audio_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                    transcription = transcription_response if isinstance(transcription_response, str) else transcription_response.text
            finally:
                # Clean up temp file
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)
            
            # 5. Detect filler words
            filler_words = detect_filler_words(transcription)
            word_count = len(transcription.split())
            speaking_pace = int((word_count / duration) * 60) if duration > 0 else 0
            
            # 6. Build comprehensive metrics
            all_metrics = {
                "transcription": transcription,
                "duration": duration,
                "word_count": word_count,
                "speaking_pace": speaking_pace,
                "filler_words": filler_words,
                "timing": timing_metrics,
                "prosody": acoustic_features["prosody"],
                "loudness": acoustic_features["loudness"],
                "quality": acoustic_features["quality"],
                "spectral": acoustic_features["spectral"]
            }
            
            # 7. Generate rule-based personalized insights
            rule_based_insights = insights_generator.generate_personalized_summary(all_metrics)
            
            # 8. Enhanced GPT analysis with acoustic context
            gpt_prompt = prompt_builder.build_gpt_analysis_prompt(
                transcription=transcription,
                acoustic_metrics=all_metrics,
                duration=duration
            )
            
            try:
                gpt_response = openai_text_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": prompt_builder.SYSTEM_PROMPT},
                        {"role": "user", "content": gpt_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                gpt_insights = json.loads(gpt_response.choices[0].message.content)
            except Exception as e:
                logger.error(f"GPT analysis failed: {e}. Using rule-based insights.")
                gpt_insights = {}
            
            # 9. Merge insights: GPT + rule-based fallbacks
            analysis = {
                # User-facing insights (personalized narrative)
                "insights": {
                    "voice_personality": gpt_insights.get("voice_personality", rule_based_insights["voice_personality"]),
                    "headline": gpt_insights.get("headline", rule_based_insights["headline"]),
                    "key_insights": gpt_insights.get("key_insights", rule_based_insights["key_insights"]),
                    "what_went_well": gpt_insights.get("strengths", rule_based_insights["what_went_well"]),
                    "growth_opportunities": gpt_insights.get("improvements", rule_based_insights["growth_opportunities"]),
                    "tone_description": gpt_insights.get("tone_description", rule_based_insights["tone_description"]),
                    "voice_archetype": gpt_insights.get("archetype", rule_based_insights["voice_personality"]),
                    "overall_score": gpt_insights.get("overall_score", 75),
                    "clarity_score": gpt_insights.get("clarity_score", 75),
                    "confidence_score": gpt_insights.get("confidence_score", 70),
                    "personalized_tips": gpt_insights.get("actionable_tips", [])
                },
                
                # Simplified metrics for UI display
                "metrics": {
                    "speaking_pace": speaking_pace,
                    "word_count": word_count,
                    "pause_effectiveness": timing_metrics["pause_count"],
                    "vocal_variety": "High" if acoustic_features["prosody"]["pitch_std"] > 40 else "Moderate",
                    "energy_level": "Dynamic" if acoustic_features["loudness"]["dynamic_range_db"] > 10 else "Consistent",
                    "clarity_rating": "Excellent" if acoustic_features["quality"]["hnr_mean"] > 15 else "Good"
                },
                
                # Raw technical data (for debugging/advanced view)
                "technical": {
                    "prosody": acoustic_features["prosody"],
                    "loudness": acoustic_features["loudness"],
                    "quality": acoustic_features["quality"],
                    "spectral": acoustic_features["spectral"],
                    "timing": timing_metrics,
                    "filler_words": filler_words
                },
                
                # Timelines for visualization
                "timelines": {
                    "pitch": acoustic_features["prosody"].get("pitch_series", []),
                    "loudness": acoustic_features["loudness"].get("rms_series", []),
                    "pauses": timing_metrics.get("pause_events", [])
                },
                
                # Legacy fields for backward compatibility
                "archetype": gpt_insights.get("archetype", rule_based_insights["voice_personality"]),
                "overall_score": gpt_insights.get("overall_score", 75),
                "clarity_score": gpt_insights.get("clarity_score", 75),
                "confidence_score": gpt_insights.get("confidence_score", 70),
                "tone": gpt_insights.get("tone_description", rule_based_insights["tone_description"]),
                "strengths": gpt_insights.get("strengths", rule_based_insights["what_went_well"]),
                "improvements": gpt_insights.get("improvements", rule_based_insights["growth_opportunities"]),
                "speaking_pace": speaking_pace,
                "filler_words": filler_words,
                "filler_count": sum(filler_words.values()),
                "word_count": word_count
            }
            
            # Update assessment with results
            await db.assessments.update_one(
                {"assessment_id": assessment_id},
                {"$set": {
                    "transcription": transcription,
                    "analysis": analysis,
                    "processed": True,
                    "processed_at": datetime.utcnow()
                }}
            )
            
            # Generate training questions
            training_questions = generate_training_questions(analysis, transcription)
            await db.training_questions.insert_one({
                "assessment_id": assessment_id,
                "questions": training_questions,
                "created_at": datetime.utcnow()
            })
            
            return VoiceAnalysisResponse(
                assessment_id=assessment_id,
                status="completed",
                message="Analysis completed successfully"
            )
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing audio: {str(e)}\n{traceback.format_exc()}")
            await db.assessments.update_one(
                {"assessment_id": assessment_id},
                {"$set": {
                    "processed": True,
                    "error": str(e),
                    "processed_at": datetime.utcnow()
                }}
            )
            raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
            
    except HTTPException:
        # Re-raise HTTPExceptions (like 401, 403) as-is - don't convert to 500
        raise
    except Exception as e:
        # Log unexpected errors with full traceback
        import traceback
        logger.error(f"Unexpected error in analyze_voice: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.get("/assessment/{assessment_id}")
@limiter.limit("30/minute")
async def get_assessment(request: Request, assessment_id: str):
    """
    Get assessment results
    """
    # Verify user owns this assessment
    user = await auth_service.get_current_user(request)
    
    assessment = await db.assessments.find_one({
        "assessment_id": assessment_id,
        "user_id": user["id"]
    })
    
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Get training questions
    training_questions = await db.training_questions.find_one({"assessment_id": assessment_id})
    
    # Remove MongoDB _id field
    assessment.pop("_id", None)
    if training_questions:
        training_questions.pop("_id", None)
        assessment["training_questions"] = training_questions.get("questions", [])
    
    return assessment

@api_router.get("/assessments")
@limiter.limit("20/minute")
async def get_assessments(request: Request, limit: int = 10, skip: int = 0):
    """
    Get user's assessment history
    """
    user = await auth_service.get_current_user(request)
    
    # Get assessments with pagination
    assessments = await db.assessments.find(
        {"user_id": user["id"]},
        {"audio_data": 0}  # Exclude large audio data
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Remove MongoDB _id field
    for assessment in assessments:
        assessment.pop("_id", None)
    
    return {
        "assessments": assessments,
        "total": await db.assessments.count_documents({"user_id": user["id"]})
    }

def analyze_transcription(text: str, recording_time: int) -> Dict[str, Any]:
    """
    Analyze transcription using GPT-4
    """
    # Calculate basic metrics
    word_count = len(text.split())
    speaking_pace = int((word_count / recording_time) * 60) if recording_time > 0 else 0
    
    # Detect filler words
    filler_words = detect_filler_words(text)
    filler_count = sum(filler_words.values())
    
    # Use GPT-4 for advanced analysis
    prompt = f"""Analyze this voice transcription and provide a detailed assessment:

Transcription: "{text}"

Speaking pace: {speaking_pace} WPM
Filler words detected: {filler_count}

Please provide:
1. Voice Archetype (e.g., "Warm Storyteller", "Confident Presenter", "Analytical Thinker")
2. Overall score (0-100)
3. Clarity score (0-100)
4. Confidence score (0-100)
5. Tone analysis (professional/casual/friendly/etc)
6. 3-4 key strengths
7. 3-4 areas for improvement
8. Estimated pitch range (Low/Medium/High with average Hz estimate)

Format your response as JSON with these exact keys:
{{
  "archetype": "string",
  "overall_score": number,
  "clarity_score": number,
  "confidence_score": number,
  "tone": "string",
  "strengths": ["string", "string", ...],
  "improvements": ["string", "string", ...],
  "pitch_avg": number,
  "pitch_range": "Low/Medium/High"
}}
"""
    
    try:
        response = openai_text_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an expert voice and communication coach."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        gpt_analysis = json.loads(response.choices[0].message.content)
        
        # Combine with basic metrics
        return {
            "archetype": gpt_analysis.get("archetype", "Emerging Communicator"),
            "overall_score": gpt_analysis.get("overall_score", 70),
            "clarity_score": gpt_analysis.get("clarity_score", 75),
            "confidence_score": gpt_analysis.get("confidence_score", 70),
            "tone": gpt_analysis.get("tone", "Neutral"),
            "strengths": gpt_analysis.get("strengths", []),
            "improvements": gpt_analysis.get("improvements", []),
            "pitch_avg": gpt_analysis.get("pitch_avg", 150),
            "pitch_range": gpt_analysis.get("pitch_range", "Medium"),
            "speaking_pace": speaking_pace,
            "filler_words": filler_words,
            "filler_count": filler_count,
            "word_count": word_count
        }
        
    except Exception as e:
        logger.error(f"Error in GPT analysis: {str(e)}")
        # Return default analysis if GPT fails
        return {
            "archetype": "Emerging Communicator",
            "overall_score": 70,
            "clarity_score": 75,
            "confidence_score": 70,
            "tone": "Neutral",
            "strengths": ["Clear articulation", "Good pacing"],
            "improvements": ["Reduce filler words", "Vary tone more"],
            "pitch_avg": 150,
            "pitch_range": "Medium",
            "speaking_pace": speaking_pace,
            "filler_words": filler_words,
            "filler_count": filler_count,
            "word_count": word_count
        }

def detect_filler_words(text: str) -> Dict[str, int]:
    """
    Detect filler words in transcription
    """
    filler_patterns = {
        "um": r'\bum\b',
        "uh": r'\buh\b',
        "like": r'\blike\b',
        "you know": r'\byou know\b',
        "so": r'\bso\b',
        "actually": r'\bactually\b',
        "basically": r'\bbasically\b',
    }
    
    text_lower = text.lower()
    filler_counts = {}
    
    for filler, pattern in filler_patterns.items():
        count = len(re.findall(pattern, text_lower))
        if count > 0:
            filler_counts[filler] = count
    
    return filler_counts

def generate_training_questions(analysis: Dict[str, Any], transcription: str) -> List[Dict[str, Any]]:
    """
    Generate personalized training questions using GPT-4
    """
    prompt = f"""Based on this voice analysis, generate 10 training questions to help improve communication skills:

Analysis:
- Archetype: {analysis.get('archetype')}
- Strengths: {', '.join(analysis.get('strengths', []))}
- Areas for improvement: {', '.join(analysis.get('improvements', []))}
- Filler words: {analysis.get('filler_count', 0)}
- Speaking pace: {analysis.get('speaking_pace', 0)} WPM

Generate 10 questions with answers that address the improvement areas. Make them practical and actionable.

Format as JSON array with this structure:
[
  {{
    "question": "string",
    "answer": "string",
    "is_free": boolean (always true)
  }}
]
"""
    
    try:
        response = openai_text_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an expert communication coach."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        questions = result.get("questions", [])
        
        # Ensure all are marked as free
        for q in questions:
            q["is_free"] = True
        
        return questions[:10]
        
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        # Return default questions
        return [
            {
                "question": "How can I reduce filler words in my speech?",
                "answer": "Practice pausing instead of using filler words. Record yourself and identify patterns.",
                "is_free": True
            },
            {
                "question": "What exercises improve speaking clarity?",
                "answer": "Try tongue twisters, slow reading aloud, and articulation exercises daily.",
                "is_free": True
            },
            {
                "question": "How do I project more confidence?",
                "answer": "Maintain good posture, make eye contact, and practice power poses before speaking.",
                "is_free": True
            }
        ]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add global exception handler to log all exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Log HTTPExceptions (401, 403, 404, etc.) with their status codes
    """
    logger.warning(f"HTTPException {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    # Let FastAPI handle the response normally
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail} if isinstance(exc.detail, str) else exc.detail
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to log all unhandled exceptions
    """
    import traceback
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}\n{traceback.format_exc()}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
