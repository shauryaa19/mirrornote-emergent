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
from payment import PaymentService
from usage import UsageService


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client - configured for Emergent LLM
openai_client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
    base_url="https://llm.kindo.ai/v1"
)

# Initialize services
auth_service = AuthService(db)
payment_service = PaymentService(db)
usage_service = UsageService(db)

# Create the main app without a prefix
app = FastAPI()

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
async def create_session(session_id: str, response: Response):
    """
    Exchange session_id from URL for session_token
    """
    return await auth_service.process_session_id(session_id, response)

@api_router.get("/auth/me")
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

# ============ PAYMENT ENDPOINTS ============
@api_router.post("/payment/create-order")
async def create_payment_order(plan_type: str, request: Request):
    """
    Create Razorpay order for subscription
    """
    user = await auth_service.get_current_user(request)
    return await payment_service.create_subscription_order(user["id"], plan_type)

@api_router.post("/payment/verify")
async def verify_payment(payment_data: dict, request: Request):
    """
    Verify Razorpay payment
    """
    # Ensure user is authenticated
    await auth_service.get_current_user(request)
    return await payment_service.verify_payment(payment_data)

@api_router.post("/payment/webhook")
async def payment_webhook(request: Request):
    """
    Handle Razorpay webhooks
    """
    return await payment_service.handle_webhook(request)

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
async def analyze_voice(request_data: VoiceAnalysisRequest, request: Request):
    """
    Analyzes voice recording using OpenAI Whisper and GPT-4
    """
    try:
        # Get authenticated user (required for usage tracking)
        user = await auth_service.get_current_user(request)
        user_id = user["id"]
        
        # Check usage limits
        usage_check = await usage_service.check_can_create_assessment(user_id)
        if not usage_check["allowed"]:
            raise HTTPException(
                status_code=403, 
                detail={
                    "message": usage_check["reason"],
                    "usage": usage_check["usage"]
                }
            )
        
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
            # Decode base64 audio
            audio_bytes = base64.b64decode(request_data.audio_base64)

            # Save temporarily to a cross-platform temp directory
            temp_dir = tempfile.gettempdir()
            temp_audio_path = os.path.join(temp_dir, f"{assessment_id}.m4a")
            with open(temp_audio_path, "wb") as f:
                f.write(audio_bytes)

            # Transcribe with Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcription_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
                transcription = transcription_response if isinstance(transcription_response, str) else transcription_response.text

            # Clean up temp file (best-effort)
            try:
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
            except Exception:
                pass
            
            # Analyze transcription text
            analysis = analyze_transcription(transcription, request.recording_time)
            
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
            logger.error(f"Error processing audio: {str(e)}")
            await db.assessments.update_one(
                {"assessment_id": assessment_id},
                {"$set": {
                    "processed": True,
                    "error": str(e),
                    "processed_at": datetime.utcnow()
                }}
            )
            raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in analyze_voice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/assessment/{assessment_id}")
async def get_assessment(assessment_id: str):
    """
    Get assessment results
    """
    assessment = await db.assessments.find_one({"assessment_id": assessment_id})
    
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
        response = openai_client.chat.completions.create(
            model="gpt-4",
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
    "is_free": boolean (first 3 are true, rest false)
  }}
]
"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert communication coach."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        questions = result.get("questions", [])
        
        # Ensure first 3 are marked as free
        for i, q in enumerate(questions):
            q["is_free"] = i < 3
        
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
