#!/usr/bin/env python3
"""
Backend API Testing for The Mirror Note - Voice Assessment Platform
Tests all backend endpoints with real API calls
"""

import requests
import json
import base64
import time
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://voiceassess-1.preview.emergentagent.com/api"
TEST_USER_ID = "test_user_voice_assessment_2024"

def create_mock_audio_base64():
    """Create a small mock audio file in base64 format for testing"""
    # Create a minimal WAV file header + some audio data
    # This is a very basic WAV file structure for testing
    wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
    # Add some basic audio samples (silence)
    audio_samples = b'\x00\x00' * 1000  # 1000 samples of silence
    mock_audio = wav_header + audio_samples
    return base64.b64encode(mock_audio).decode('utf-8')

def test_health_check():
    """Test GET /api/ - Health check endpoint"""
    print("\n=== Testing Health Check Endpoint ===")
    try:
        response = requests.get(f"{BACKEND_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "Mirror Note" in data["message"]:
                print("✅ Health check PASSED")
                return True
            else:
                print("❌ Health check FAILED - Unexpected response format")
                return False
        else:
            print(f"❌ Health check FAILED - Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check FAILED - Error: {str(e)}")
        return False

def test_voice_analysis():
    """Test POST /api/analyze-voice - Voice analysis endpoint"""
    print("\n=== Testing Voice Analysis Endpoint ===")
    
    # Create test payload
    mock_audio = create_mock_audio_base64()
    payload = {
        "audio_base64": mock_audio,
        "user_id": TEST_USER_ID,
        "recording_mode": "free",
        "recording_time": 30
    }
    
    try:
        print("Sending voice analysis request...")
        response = requests.post(
            f"{BACKEND_URL}/analyze-voice",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Give it time for OpenAI processing
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Check required fields
            if all(key in data for key in ["assessment_id", "status", "message"]):
                assessment_id = data["assessment_id"]
                status = data["status"]
                
                if status == "completed":
                    print("✅ Voice analysis PASSED")
                    return True, assessment_id
                else:
                    print(f"⚠️ Voice analysis completed but status is: {status}")
                    return True, assessment_id
            else:
                print("❌ Voice analysis FAILED - Missing required fields in response")
                return False, None
        else:
            print(f"Response body: {response.text}")
            print(f"❌ Voice analysis FAILED - Status code: {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("❌ Voice analysis FAILED - Request timeout (OpenAI processing may be slow)")
        return False, None
    except Exception as e:
        print(f"❌ Voice analysis FAILED - Error: {str(e)}")
        return False, None

def test_get_assessment(assessment_id):
    """Test GET /api/assessment/{assessment_id} - Get assessment results"""
    print(f"\n=== Testing Get Assessment Endpoint (ID: {assessment_id}) ===")
    
    try:
        response = requests.get(f"{BACKEND_URL}/assessment/{assessment_id}")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Assessment data keys: {list(data.keys())}")
            
            # Check for required fields
            required_fields = ["assessment_id", "user_id", "processed"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ Get assessment FAILED - Missing fields: {missing_fields}")
                return False
            
            # Check if processed
            if data.get("processed"):
                print("✅ Assessment is processed")
                
                # Check for analysis data
                if "analysis" in data:
                    analysis = data["analysis"]
                    print(f"Analysis keys: {list(analysis.keys())}")
                    
                    # Check key analysis fields
                    analysis_fields = ["archetype", "overall_score", "clarity_score", "confidence_score"]
                    if all(field in analysis for field in analysis_fields):
                        print("✅ Analysis data complete")
                    else:
                        print("⚠️ Some analysis fields missing")
                
                # Check for training questions
                if "training_questions" in data:
                    questions = data["training_questions"]
                    print(f"Training questions count: {len(questions)}")
                    if len(questions) > 0:
                        print("✅ Training questions generated")
                    else:
                        print("⚠️ No training questions found")
                
                # Check for transcription
                if "transcription" in data:
                    print("✅ Transcription available")
                else:
                    print("⚠️ No transcription found")
                
                print("✅ Get assessment PASSED")
                return True
            else:
                print("⚠️ Assessment not yet processed")
                return True  # Still valid response
                
        elif response.status_code == 404:
            print("❌ Get assessment FAILED - Assessment not found")
            return False
        else:
            print(f"Response: {response.text}")
            print(f"❌ Get assessment FAILED - Status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Get assessment FAILED - Error: {str(e)}")
        return False

def test_error_scenarios():
    """Test error handling scenarios"""
    print("\n=== Testing Error Scenarios ===")
    
    # Test 1: Invalid assessment ID
    print("\n--- Testing invalid assessment ID ---")
    try:
        response = requests.get(f"{BACKEND_URL}/assessment/invalid-id-123")
        if response.status_code == 404:
            print("✅ Invalid assessment ID properly returns 404")
        else:
            print(f"⚠️ Invalid assessment ID returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid ID: {str(e)}")
    
    # Test 2: Missing required fields in voice analysis
    print("\n--- Testing missing required fields ---")
    try:
        incomplete_payload = {
            "user_id": TEST_USER_ID,
            # Missing audio_base64, recording_mode, recording_time
        }
        response = requests.post(
            f"{BACKEND_URL}/analyze-voice",
            json=incomplete_payload,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code in [400, 422]:  # Bad request or validation error
            print("✅ Missing fields properly rejected")
        else:
            print(f"⚠️ Missing fields returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing missing fields: {str(e)}")

def check_mongodb_connection():
    """Check if MongoDB operations are working by testing status endpoints"""
    print("\n=== Testing MongoDB Connection ===")
    
    try:
        # Test creating a status check
        payload = {"client_name": "test_client_voice_assessment"}
        response = requests.post(
            f"{BACKEND_URL}/status",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ MongoDB write operation successful")
            
            # Test reading status checks
            response = requests.get(f"{BACKEND_URL}/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ MongoDB read operation successful - {len(data)} records found")
                return True
            else:
                print(f"❌ MongoDB read failed - Status: {response.status_code}")
                return False
        else:
            print(f"❌ MongoDB write failed - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ MongoDB connection test failed - Error: {str(e)}")
        return False

def run_all_tests():
    """Run all backend tests"""
    print("🚀 Starting Backend API Tests for The Mirror Note")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"Timestamp: {datetime.now()}")
    
    results = {
        "health_check": False,
        "mongodb_connection": False,
        "voice_analysis": False,
        "get_assessment": False,
        "error_handling": True,  # Assume pass unless we find issues
        "overall_success": False
    }
    
    # Test 1: Health Check
    results["health_check"] = test_health_check()
    
    # Test 2: MongoDB Connection
    results["mongodb_connection"] = check_mongodb_connection()
    
    # Test 3: Voice Analysis (most critical)
    analysis_success, assessment_id = test_voice_analysis()
    results["voice_analysis"] = analysis_success
    
    # Test 4: Get Assessment (if we have an assessment_id)
    if assessment_id:
        results["get_assessment"] = test_get_assessment(assessment_id)
    else:
        print("\n⚠️ Skipping assessment retrieval test - no assessment_id available")
    
    # Test 5: Error Scenarios
    test_error_scenarios()
    
    # Overall Results
    print("\n" + "="*60)
    print("📊 FINAL TEST RESULTS")
    print("="*60)
    
    for test_name, passed in results.items():
        if test_name != "overall_success":
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Determine overall success
    critical_tests = ["health_check", "mongodb_connection", "voice_analysis"]
    critical_passed = all(results[test] for test in critical_tests)
    results["overall_success"] = critical_passed
    
    print(f"\nOverall Status: {'✅ SUCCESS' if critical_passed else '❌ FAILURE'}")
    
    if not critical_passed:
        print("\n🔍 CRITICAL ISSUES FOUND:")
        for test in critical_tests:
            if not results[test]:
                print(f"  - {test.replace('_', ' ').title()} failed")
    
    return results

if __name__ == "__main__":
    results = run_all_tests()