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
        
        # Check if user exists
        existing_user = await self.db.users.find_one({"email": user_data["email"]})
        
        if not existing_user:
            # Create new user
            user_doc = {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data["name"],
                "picture": user_data.get("picture"),
                "isPremium": False,
                "created_at": datetime.now(timezone.utc)
            }
            await self.db.users.insert_one(user_doc)
        else:
            user_data["id"] = existing_user["id"]
        
        # Create session
        session_token = user_data["session_token"]
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        await self.db.user_sessions.insert_one({
            "user_id": user_data["id"],
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        })
        
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
            "isPremium": existing_user.get("isPremium", False) if existing_user else False
        }
    
    async def logout(self, request: Request, response: Response):
        """
        Logout user and clear session
        """
        session_token = request.cookies.get("session_token")
        
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