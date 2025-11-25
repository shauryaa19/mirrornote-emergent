from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Request, Response
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
import os

# Session validation endpoint
EMERGENT_SESSION_API = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

class AuthService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db
    
    async def get_current_user(self, request: Request):
        """
        Get current user from session token
        Checks both cookie and Authorization header
        """
        # Try cookie first (preferred)
        session_token = request.cookies.get("session_token")
        
        # Fallback to Authorization header
        if not session_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                session_token = auth_header.replace("Bearer ", "")
        
        if not session_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Check if session exists and is valid
        session = await self.db.user_sessions.find_one({
            "session_token": session_token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not session:
            raise HTTPException(status_code=401, detail="Session expired or invalid")
        
        # Get user data
        user = await self.db.users.find_one({"id": session["user_id"]})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Remove MongoDB _id field
        user.pop("_id", None)
        return user
    
    async def process_session_id(self, session_id: str, response: Response):
        """
        Exchange session_id for user data and session_token
        This function is idempotent - calling it multiple times with the same session_id
        will only create one user and one session.
        """
        async with httpx.AsyncClient() as client:
            api_response = await client.get(
                EMERGENT_SESSION_API,
                headers={"X-Session-ID": session_id},
                timeout=10.0
            )
            
            if api_response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail="Failed to validate session"
                )
            
            user_data = api_response.json()
        
        session_token = user_data["session_token"]
        
        # IDEMPOTENCY CHECK: Check if session already exists
        existing_session = await self.db.user_sessions.find_one({
            "session_token": session_token
        })
        
        if existing_session:
            # Session already exists - return existing user data
            existing_user = await self.db.users.find_one({"id": existing_session["user_id"]})
            if existing_user:
                existing_user.pop("_id", None)
                return {
                    "id": existing_user["id"],
                    "email": existing_user["email"],
                    "name": existing_user["name"],
                    "picture": existing_user.get("picture"),
                    "session_token": session_token
                }
        
        # Check if user exists by email (idempotent check)
        existing_user = await self.db.users.find_one({"email": user_data["email"]})
        
        if not existing_user:
            # Use upsert to prevent duplicate user creation in race conditions
            # Try to insert, but if duplicate key error, fetch existing
            try:
                user_doc = {
                    "id": user_data["id"],
                    "email": user_data["email"],
                    "name": user_data["name"],
                    "picture": user_data.get("picture"),
                    "created_at": datetime.now(timezone.utc)
                }
                await self.db.users.insert_one(user_doc)
            except Exception as e:
                # If insert fails (e.g., duplicate key error), fetch existing user
                # MongoDB duplicate key error code is 11000
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "E11000" in error_str:
                    existing_user = await self.db.users.find_one({"email": user_data["email"]})
                    if existing_user:
                        user_data["id"] = existing_user["id"]
                    else:
                        # Try by id as fallback
                        existing_user = await self.db.users.find_one({"id": user_data["id"]})
                        if existing_user:
                            user_data["id"] = existing_user["id"]
                        else:
                            # Re-raise if we can't find the user
                            raise
                else:
                    # Re-raise if it's not a duplicate error
                    raise
        else:
            user_data["id"] = existing_user["id"]
        
        # Create session only if it doesn't exist (idempotent)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Use update_one with upsert to prevent duplicate sessions
        await self.db.user_sessions.update_one(
            {"session_token": session_token},
            {
                "$setOnInsert": {
                    "user_id": user_data["id"],
                    "session_token": session_token,
                    "expires_at": expires_at,
                    "created_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "session_token": session_token  # Include token in response for React Native
        }
    
    async def logout(self, request: Request, response: Response):
        """
        Logout user and clear session
        """
        # Try cookie first
        session_token = request.cookies.get("session_token")
        
        # Fallback to Authorization header
        if not session_token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                session_token = auth_header.replace("Bearer ", "")
        
        if session_token:
            # Delete session from database
            await self.db.user_sessions.delete_one({"session_token": session_token})
        
        # Clear cookie
        response.delete_cookie(
            key="session_token",
            path="/",
            domain=None
        )
        
        return {"message": "Logged out successfully"}