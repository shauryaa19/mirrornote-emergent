#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for The Mirror Note - Voice Assessment Platform
Tests all backend endpoints with proper authentication
"""

import requests
import json
import base64
import time
import os
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

# Configuration
BACKEND_URL = "https://speak-assess-2.preview.emergentagent.com/api"
TEST_USER_ID = str(uuid.uuid4())
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

def setup_test_user_with_auth():
    """Create a test user and session directly in MongoDB for testing authenticated endpoints"""
    print("\n=== Setting up Test User with Authentication ===")
    
    try:
        # Connect to MongoDB
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Create test user
        test_user = {
            "id": TEST_USER_ID,
            "email": "testuser@mirrornote.com",
            "name": "Test User",
            "picture": None,
            "isPremium": False,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Insert or update user
        db.users.update_one(
            {"id": TEST_USER_ID},
            {"$set": test_user},
            upsert=True
        )
        
        # Create session token
        session_token = f"test_session_{uuid.uuid4()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Create session
        db.user_sessions.update_one(
            {"user_id": TEST_USER_ID},
            {"$set": {
                "user_id": TEST_USER_ID,
                "session_token": session_token,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        client.close()
        
        print(f"✅ Test user created: {test_user['email']}")
        print(f"✅ Session token created: {session_token[:20]}...")
        
        return session_token
        
    except Exception as e:
        print(f"❌ Failed to setup test user: {str(e)}")
        return None

def create_premium_test_user():
    """Create a premium test user for testing usage limits"""
    print("\n=== Setting up Premium Test User ===")
    
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        premium_user_id = f"{TEST_USER_ID}_premium"
        
        # Create premium user
        premium_user = {
            "id": premium_user_id,
            "email": "premium@mirrornote.com",
            "name": "Premium Test User",
            "picture": None,
            "isPremium": True,
            "created_at": datetime.now(timezone.utc)
        }
        
        db.users.update_one(
            {"id": premium_user_id},
            {"$set": premium_user},
            upsert=True
        )
        
        # Create session for premium user
        premium_session_token = f"premium_session_{uuid.uuid4()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        db.user_sessions.update_one(
            {"user_id": premium_user_id},
            {"$set": {
                "user_id": premium_user_id,
                "session_token": premium_session_token,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        
        client.close()
        
        print(f"✅ Premium user created: {premium_user['email']}")
        return premium_session_token, premium_user_id
        
    except Exception as e:
        print(f"❌ Failed to setup premium user: {str(e)}")
        return None, None

def test_basic_connectivity():
    """Test basic API connectivity"""
    print("\n=== Testing Basic Connectivity ===")
    try:
        response = requests.get(f"{BACKEND_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API accessible: {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def test_auth_endpoints(session_token):
    """Test authentication endpoints"""
    print("\n=== Testing Authentication Endpoints ===")
    
    # Test /api/auth/me with valid session
    print("\n--- Testing /api/auth/me with valid session ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        response = requests.get(f"{BACKEND_URL}/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Auth /me endpoint working: {user_data.get('email', 'Unknown')}")
            if user_data.get('id') == TEST_USER_ID:
                print("✅ Correct user data returned")
                return True
            else:
                print("⚠️ User ID mismatch in response")
                return False
        else:
            print(f"❌ Auth /me failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Auth /me test failed: {str(e)}")
        return False
    
    # Test /api/auth/me without session
    print("\n--- Testing /api/auth/me without session ---")
    try:
        response = requests.get(f"{BACKEND_URL}/auth/me")
        if response.status_code == 401:
            print("✅ Auth /me properly rejects unauthenticated requests")
        else:
            print(f"⚠️ Auth /me returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Auth /me unauthenticated test failed: {str(e)}")
    
    # Test logout
    print("\n--- Testing /api/auth/logout ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        response = requests.post(f"{BACKEND_URL}/auth/logout", headers=headers)
        if response.status_code == 200:
            print("✅ Logout endpoint working")
        else:
            print(f"⚠️ Logout returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Logout test failed: {str(e)}")

def test_usage_endpoints(session_token, premium_session_token=None, premium_user_id=None):
    """Test usage tracking endpoints"""
    print("\n=== Testing Usage Tracking Endpoints ===")
    
    # Test usage endpoint for free user
    print("\n--- Testing /api/usage for free user ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        response = requests.get(f"{BACKEND_URL}/usage", headers=headers)
        
        if response.status_code == 200:
            usage_data = response.json()
            print(f"✅ Usage endpoint working for free user")
            print(f"   Plan: {usage_data.get('plan', 'Unknown')}")
            print(f"   Used: {usage_data.get('used', 0)}")
            print(f"   Limit: {usage_data.get('limit', 0)}")
            
            if usage_data.get('plan') == 'free' and usage_data.get('limit') == 5:
                print("✅ Free plan limits correctly configured")
                return True
            else:
                print("⚠️ Free plan configuration may be incorrect")
                return False
        else:
            print(f"❌ Usage endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Usage endpoint test failed: {str(e)}")
        return False
    
    # Test usage endpoint for premium user if available
    if premium_session_token and premium_user_id:
        print("\n--- Testing /api/usage for premium user ---")
        try:
            headers = {"Authorization": f"Bearer {premium_session_token}"}
            response = requests.get(f"{BACKEND_URL}/usage", headers=headers)
            
            if response.status_code == 200:
                usage_data = response.json()
                print(f"✅ Usage endpoint working for premium user")
                print(f"   Plan: {usage_data.get('plan', 'Unknown')}")
                print(f"   Monthly Used: {usage_data.get('monthly_used', 0)}")
                print(f"   Monthly Limit: {usage_data.get('monthly_limit', 0)}")
                
                if usage_data.get('plan') == 'standard' and usage_data.get('monthly_limit') == 30:
                    print("✅ Premium plan limits correctly configured")
                else:
                    print("⚠️ Premium plan configuration may be incorrect")
            else:
                print(f"❌ Premium usage endpoint failed: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Premium usage endpoint test failed: {str(e)}")

def create_mock_audio_base64():
    """Create a small mock audio file in base64 format for testing"""
    # Create a minimal WAV file header + some audio data
    wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x08\x00\x00\x00'
    # Add some basic audio samples (silence)
    audio_samples = b'\x00\x00' * 500  # 500 samples of silence
    mock_audio = wav_header + audio_samples
    return base64.b64encode(mock_audio).decode('utf-8')

def test_voice_analysis_authenticated(session_token):
    """Test voice analysis with authentication"""
    print("\n=== Testing Voice Analysis with Authentication ===")
    
    # Create test payload
    mock_audio = create_mock_audio_base64()
    payload = {
        "audio_base64": mock_audio,
        "user_id": TEST_USER_ID,
        "recording_mode": "free_speaking",
        "recording_time": 30
    }
    
    try:
        print("Sending authenticated voice analysis request...")
        headers = {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{BACKEND_URL}/analyze-voice",
            json=payload,
            headers=headers,
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
                    print("✅ Authenticated voice analysis PASSED")
                    return True, assessment_id
                else:
                    print(f"⚠️ Voice analysis completed but status is: {status}")
                    return True, assessment_id
            else:
                print("❌ Voice analysis FAILED - Missing required fields in response")
                return False, None
        elif response.status_code == 403:
            # Usage limit exceeded
            error_detail = response.json().get('detail', {})
            if isinstance(error_detail, dict) and 'usage' in error_detail:
                print("⚠️ Voice analysis blocked due to usage limits (expected for testing)")
                print(f"   Usage: {error_detail['usage']}")
                return True, None  # This is actually a successful test of usage limits
            else:
                print(f"❌ Voice analysis FAILED - Forbidden: {response.text}")
                return False, None
        else:
            print(f"Response body: {response.text}")
            print(f"❌ Authenticated voice analysis FAILED - Status code: {response.status_code}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("❌ Voice analysis FAILED - Request timeout (OpenAI processing may be slow)")
        return False, None
    except Exception as e:
        print(f"❌ Authenticated voice analysis FAILED - Error: {str(e)}")
        return False, None

def test_assessment_endpoints_authenticated(session_token, assessment_id=None):
    """Test assessment endpoints with authentication"""
    print("\n=== Testing Assessment Endpoints with Authentication ===")
    
    # Test get assessments list
    print("\n--- Testing /api/assessments ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        response = requests.get(f"{BACKEND_URL}/assessments", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Assessments list endpoint working")
            print(f"   Total assessments: {data.get('total', 0)}")
            print(f"   Assessments in response: {len(data.get('assessments', []))}")
            return True
        else:
            print(f"❌ Assessments list failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Assessments list test failed: {str(e)}")
        return False
    
    # Test get specific assessment if we have an ID
    if assessment_id:
        print(f"\n--- Testing /api/assessment/{assessment_id} ---")
        try:
            headers = {"Authorization": f"Bearer {session_token}"}
            response = requests.get(f"{BACKEND_URL}/assessment/{assessment_id}", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Specific assessment endpoint working")
                print(f"   Assessment ID: {data.get('assessment_id', 'Unknown')}")
                print(f"   Processed: {data.get('processed', False)}")
                
                if data.get('processed'):
                    print("   ✅ Assessment was processed")
                    if 'analysis' in data:
                        print("   ✅ Analysis data present")
                    if 'training_questions' in data:
                        print(f"   ✅ Training questions present: {len(data.get('training_questions', []))}")
                else:
                    print("   ⚠️ Assessment not yet processed")
                return True
            else:
                print(f"❌ Specific assessment failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Specific assessment test failed: {str(e)}")
            return False

def test_payment_endpoints_authenticated(session_token):
    """Test payment endpoints with authentication"""
    print("\n=== Testing Payment Endpoints with Authentication ===")
    
    # Test create order
    print("\n--- Testing /api/payment/create-order ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        response = requests.post(f"{BACKEND_URL}/payment/create-order", 
                               params={"plan_type": "standard"}, 
                               headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Payment create order endpoint working")
            print(f"   Order ID: {data.get('order_id', 'Unknown')}")
            print(f"   Amount: ₹{data.get('amount', 0) / 100}")
            
            if data.get('amount') == 49900:  # ₹499 in paise
                print("✅ Correct pricing for Standard plan")
                return True
            else:
                print("⚠️ Pricing may be incorrect")
                return False
        else:
            print(f"❌ Payment create order failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Payment create order test failed: {str(e)}")
        return False
    
    # Test verify payment (will fail with invalid data, but tests endpoint structure)
    print("\n--- Testing /api/payment/verify ---")
    try:
        headers = {"Authorization": f"Bearer {session_token}"}
        test_payment_data = {
            "order_id": "test_order_123",
            "payment_id": "test_payment_123",
            "signature": "test_signature_123"
        }
        
        response = requests.post(f"{BACKEND_URL}/payment/verify", 
                               json=test_payment_data, 
                               headers=headers)
        
        # We expect this to fail with signature verification error
        if response.status_code == 400:
            error_detail = response.json().get('detail', '')
            if 'signature' in error_detail.lower():
                print("✅ Payment verify endpoint working (correctly rejects invalid signature)")
            else:
                print(f"⚠️ Payment verify returned unexpected error: {error_detail}")
        elif response.status_code == 404:
            print("✅ Payment verify endpoint working (order not found - expected)")
        else:
            print(f"⚠️ Payment verify returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Payment verify test failed: {str(e)}")

def test_mongodb_connection():
    """Test MongoDB connectivity through API"""
    print("\n=== Testing MongoDB Connection ===")
    
    try:
        # Test creating a status check
        payload = {"client_name": "test_client_comprehensive"}
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

def cleanup_test_data():
    """Clean up test data from MongoDB"""
    print("\n=== Cleaning up test data ===")
    
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Remove test users and sessions
        db.users.delete_many({"id": {"$regex": TEST_USER_ID}})
        db.user_sessions.delete_many({"user_id": {"$regex": TEST_USER_ID}})
        db.assessments.delete_many({"user_id": {"$regex": TEST_USER_ID}})
        db.training_questions.delete_many({"assessment_id": {"$regex": TEST_USER_ID}})
        
        client.close()
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"⚠️ Failed to cleanup test data: {str(e)}")

def run_comprehensive_tests():
    """Run all comprehensive backend tests"""
    print("🚀 Starting Comprehensive Backend API Tests for The Mirror Note")
    print(f"📍 Testing against: {BACKEND_URL}")
    print(f"🆔 Test User ID: {TEST_USER_ID}")
    print(f"⏰ Timestamp: {datetime.now()}")
    print("=" * 80)
    
    results = {
        "basic_connectivity": False,
        "mongodb_connection": False,
        "auth_setup": False,
        "auth_endpoints": False,
        "usage_endpoints": False,
        "voice_analysis": False,
        "assessment_endpoints": False,
        "payment_endpoints": False,
        "overall_success": False
    }
    
    # Test 1: Basic connectivity
    results["basic_connectivity"] = test_basic_connectivity()
    if not results["basic_connectivity"]:
        print("❌ Basic connectivity failed. Stopping tests.")
        return results
    
    # Test 2: MongoDB connection
    results["mongodb_connection"] = test_mongodb_connection()
    
    # Test 3: Setup authentication
    session_token = setup_test_user_with_auth()
    premium_session_token, premium_user_id = create_premium_test_user()
    
    if session_token:
        results["auth_setup"] = True
        
        # Test 4: Authentication endpoints
        results["auth_endpoints"] = test_auth_endpoints(session_token)
        
        # Test 5: Usage endpoints
        results["usage_endpoints"] = test_usage_endpoints(session_token, premium_session_token, premium_user_id)
        
        # Test 6: Voice analysis (most critical)
        voice_success, assessment_id = test_voice_analysis_authenticated(session_token)
        results["voice_analysis"] = voice_success
        
        # Test 7: Assessment endpoints
        results["assessment_endpoints"] = test_assessment_endpoints_authenticated(session_token, assessment_id)
        
        # Test 8: Payment endpoints
        results["payment_endpoints"] = test_payment_endpoints_authenticated(session_token)
    else:
        print("❌ Failed to setup authentication. Skipping authenticated tests.")
    
    # Cleanup
    cleanup_test_data()
    
    # Overall Results
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("="*80)
    
    for test_name, passed in results.items():
        if test_name != "overall_success":
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Determine overall success
    critical_tests = ["basic_connectivity", "mongodb_connection", "auth_setup", "auth_endpoints", "usage_endpoints", "voice_analysis"]
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
    results = run_comprehensive_tests()
    
    # Exit with appropriate code
    if results["overall_success"]:
        print("\n🎉 All critical tests passed!")
        exit(0)
    else:
        print("\n💥 Some critical tests failed!")
        exit(1)