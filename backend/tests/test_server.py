"""
Tests for server.py functions and endpoints.

Run with: pytest tests/test_server.py -v
"""
import pytest
import numpy as np
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDetectFillerWords:
    """Tests for detect_filler_words function"""
    
    def test_no_fillers(self):
        """Should return empty dict for clean speech"""
        from server import detect_filler_words
        
        text = "The quick brown fox jumps over the lazy dog."
        result = detect_filler_words(text)
        
        # Should not detect fillers in clean sentence
        assert "um" not in result
        assert "uh" not in result
    
    def test_detects_common_fillers(self):
        """Should detect um, uh, like, you know, etc."""
        from server import detect_filler_words
        
        text = "Um, I think, uh, it was like really good, you know."
        result = detect_filler_words(text)
        
        assert result.get("um", 0) == 1
        assert result.get("uh", 0) == 1
        assert result.get("like", 0) == 1
        assert result.get("you know", 0) == 1
    
    def test_case_insensitive(self):
        """Should detect fillers regardless of case"""
        from server import detect_filler_words
        
        text = "UM and Um and um"
        result = detect_filler_words(text)
        
        assert result.get("um", 0) == 3
    
    def test_extended_um_uh(self):
        """Should detect extended fillers like 'umm' and 'uhh'"""
        from server import detect_filler_words
        
        text = "Ummmm, I was thinking, uhhhhh, maybe we should go."
        result = detect_filler_words(text)
        
        # Pattern uses um+ and uh+ to catch extended versions
        assert result.get("um", 0) == 1
        assert result.get("uh", 0) == 1
    
    def test_counts_multiple_occurrences(self):
        """Should count multiple occurrences correctly"""
        from server import detect_filler_words
        
        text = "Actually, I basically think actually we should basically do it."
        result = detect_filler_words(text)
        
        assert result.get("actually", 0) == 2
        assert result.get("basically", 0) == 2
    
    def test_new_filler_patterns(self):
        """Should detect newly added filler patterns"""
        from server import detect_filler_words
        
        text = "I mean, literally, it's honestly kind of hard to explain, right?"
        result = detect_filler_words(text)
        
        assert result.get("I mean", 0) == 1
        assert result.get("literally", 0) == 1
        assert result.get("honestly", 0) == 1
        assert result.get("kind of", 0) == 1
        assert result.get("right", 0) == 1


class TestGPTInsightsResponse:
    """Tests for GPTInsightsResponse Pydantic model"""
    
    def test_provides_defaults(self):
        """Should provide defaults for missing fields"""
        from server import GPTInsightsResponse
        
        response = GPTInsightsResponse()
        
        assert response.voice_personality == "Balanced Communicator"
        assert response.overall_score == 75
        assert response.clarity_score == 75
        assert response.confidence_score == 70
    
    def test_clamps_scores(self):
        """Should clamp scores to 0-100 range"""
        from server import GPTInsightsResponse
        
        response = GPTInsightsResponse(
            overall_score=150,  # Over 100
            clarity_score=-10,  # Under 0
            confidence_score=50  # Valid
        )
        
        assert response.overall_score == 100
        assert response.clarity_score == 0
        assert response.confidence_score == 50
    
    def test_handles_invalid_score_types(self):
        """Should handle non-numeric scores gracefully"""
        from server import GPTInsightsResponse
        
        response = GPTInsightsResponse(
            overall_score="not a number"
        )
        
        # Should fall back to default
        assert response.overall_score == 75
    
    def test_accepts_valid_response(self):
        """Should accept fully valid GPT response"""
        from server import GPTInsightsResponse
        
        valid_data = {
            "voice_personality": "Dynamic Storyteller",
            "headline": "Your voice captivates listeners",
            "key_insights": ["Great pacing", "Natural pauses"],
            "strengths": ["Clear articulation"],
            "improvements": ["Reduce fillers"],
            "tone_description": "warm, engaging",
            "archetype": "Storyteller",
            "overall_score": 85,
            "clarity_score": 90,
            "confidence_score": 80,
            "actionable_tips": ["Try pausing more"]
        }
        
        response = GPTInsightsResponse(**valid_data)
        
        assert response.voice_personality == "Dynamic Storyteller"
        assert response.overall_score == 85
        assert len(response.key_insights) == 2


class TestVoiceAnalysisRequest:
    """Tests for VoiceAnalysisRequest model"""
    
    def test_accepts_valid_request(self):
        """Should accept valid request data"""
        from server import VoiceAnalysisRequest
        
        request = VoiceAnalysisRequest(
            audio_base64="SGVsbG8gV29ybGQ=",
            user_id="test-user-123",
            recording_mode="freestyle",
            recording_time=30
        )
        
        assert request.user_id == "test-user-123"
        assert request.recording_time == 30


# Integration tests require mocking external services
class TestAnalyzeVoiceEndpoint:
    """Integration tests for /analyze-voice endpoint"""
    
    @pytest.fixture
    def mock_services(self):
        """Mock external services for testing"""
        with patch('server.auth_service') as mock_auth, \
             patch('server.usage_service') as mock_usage, \
             patch('server.db') as mock_db, \
             patch('server.openai_audio_client') as mock_audio, \
             patch('server.openai_text_client') as mock_text:
            
            # Setup auth mock
            mock_auth.get_current_user = AsyncMock(return_value={"id": "test-user"})
            
            # Setup usage mock
            mock_usage.track_analysis = AsyncMock()
            
            # Setup db mocks
            mock_db.assessments.insert_one = AsyncMock()
            mock_db.assessments.update_one = AsyncMock()
            mock_db.training_questions.insert_one = AsyncMock()
            
            # Setup OpenAI audio mock
            mock_audio.audio.transcriptions.create.return_value = "Hello, this is a test transcription."
            
            # Setup OpenAI text mock
            mock_gpt_response = MagicMock()
            mock_gpt_response.choices = [MagicMock()]
            mock_gpt_response.choices[0].message.content = json.dumps({
                "voice_personality": "Test Speaker",
                "headline": "Test headline",
                "key_insights": [],
                "strengths": [],
                "improvements": [],
                "tone_description": "neutral",
                "archetype": "Test",
                "overall_score": 80,
                "clarity_score": 85,
                "confidence_score": 75,
                "actionable_tips": []
            })
            mock_text.chat.completions.create.return_value = mock_gpt_response
            
            yield {
                "auth": mock_auth,
                "usage": mock_usage,
                "db": mock_db,
                "audio": mock_audio,
                "text": mock_text
            }
    
    @pytest.mark.asyncio
    async def test_requires_authentication(self):
        """Should require authentication"""
        from fastapi.testclient import TestClient
        from server import app
        
        client = TestClient(app)
        
        # Without auth, should fail
        with patch('server.auth_service.get_current_user', 
                   AsyncMock(side_effect=Exception("Unauthorized"))):
            response = client.post("/api/analyze-voice", json={
                "audio_base64": "test",
                "user_id": "test",
                "recording_mode": "freestyle",
                "recording_time": 30
            })
            
            # Should return error (either 401 or 500 depending on implementation)
            assert response.status_code >= 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
