# Production Integration Guide
## Google Authentication & Razorpay Payment for The Mirror Note

This guide explains how to implement real Google Authentication and Razorpay payments in production.

---

## 🔐 Part 1: Google Authentication Integration

### Overview
Replace the current simple email/name login with Google OAuth using Emergent Auth service.

### Step 1: Install Required Package

**Backend:**
```bash
cd /app/backend
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
pip freeze > requirements.txt
```

**Frontend:**
No additional packages needed - uses standard fetch/axios

### Step 2: Update Backend Authentication

**Create `/app/backend/auth.py`:**

```python
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
```

**Update `/app/backend/server.py`:**

```python
from fastapi import Depends, Response
from auth import AuthService

# Initialize auth service
auth_service = AuthService(db)

# Add auth endpoints
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

# Protect existing endpoints
@api_router.post("/analyze-voice")
async def analyze_voice(
    request_data: VoiceAnalysisRequest,
    request: Request
):
    # Get authenticated user
    user = await auth_service.get_current_user(request)
    
    # Use user.id instead of request.user_id
    # ... rest of your code
```

### Step 3: Update Frontend Authentication

**Update `/app/frontend/app/context/AuthContext.tsx`:**

```typescript
import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import * as Linking from 'expo-linking';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;
const AUTH_URL = 'https://auth.emergentagent.com';

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  isPremium: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  loginWithGoogle: () => void;
  logout: () => Promise<void>;
  updatePremiumStatus: (isPremium: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initializeAuth();
    
    // Listen for deep links (returning from Google auth)
    const subscription = Linking.addEventListener('url', handleDeepLink);
    
    return () => subscription.remove();
  }, []);

  const initializeAuth = async () => {
    try {
      // Check for session_id in URL (coming back from Google auth)
      const url = await Linking.getInitialURL();
      if (url) {
        const { queryParams } = Linking.parse(url);
        if (queryParams?.session_id) {
          await processSessionId(queryParams.session_id as string);
          return;
        }
      }
      
      // Check existing session
      await checkSession();
    } catch (error) {
      console.error('Auth initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeepLink = async ({ url }: { url: string }) => {
    const { queryParams } = Linking.parse(url);
    if (queryParams?.session_id) {
      await processSessionId(queryParams.session_id as string);
    }
  };

  const processSessionId = async (sessionId: string) => {
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/auth/session`,
        { session_id: sessionId },
        { withCredentials: true }
      );
      setUser(response.data);
    } catch (error) {
      console.error('Session processing error:', error);
    }
  };

  const checkSession = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/auth/me`, {
        withCredentials: true
      });
      setUser(response.data);
    } catch (error) {
      // No valid session
      setUser(null);
    }
  };

  const loginWithGoogle = () => {
    // Redirect URL is your app's main route (dashboard)
    const redirectUrl = Linking.createURL('/(tabs)/dashboard');
    const authUrl = `${AUTH_URL}/?redirect=${encodeURIComponent(redirectUrl)}`;
    
    // Open auth URL in browser
    Linking.openURL(authUrl);
  };

  const logout = async () => {
    try {
      await axios.post(`${BACKEND_URL}/api/auth/logout`, {}, {
        withCredentials: true
      });
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const updatePremiumStatus = (isPremium: boolean) => {
    if (user) {
      setUser({ ...user, isPremium });
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, logout, updatePremiumStatus }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

**Update `/app/frontend/app/auth/login.tsx`:**

```typescript
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, FONT_SIZES, BORDER_RADIUS } from '../constants/theme';

export default function LoginScreen() {
  const { loginWithGoogle } = useAuth();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.logo}>🎤</Text>
        <Text style={styles.title}>Welcome to</Text>
        <Text style={styles.appName}>The Mirror Note</Text>
        <Text style={styles.tagline}>
          Discover Your Voice, Elevate Your Communication
        </Text>

        <TouchableOpacity style={styles.googleButton} onPress={loginWithGoogle}>
          <Ionicons name="logo-google" size={24} color={COLORS.textWhite} />
          <Text style={styles.googleButtonText}>Continue with Google</Text>
        </TouchableOpacity>

        <Text style={styles.note}>
          Secure authentication powered by Google OAuth
        </Text>
      </View>
    </SafeAreaView>
  );
}

// ... styles
```

**Update app.json for deep linking:**

```json
{
  "expo": {
    "scheme": "mirrornote",
    "ios": {
      "bundleIdentifier": "com.yourcompany.mirrornote"
    },
    "android": {
      "package": "com.yourcompany.mirrornote"
    }
  }
}
```

---

## 💳 Part 2: Razorpay Payment Integration

### Step 1: Get Razorpay Credentials

1. Sign up at [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Get your **Key ID** and **Key Secret** from API Keys section
3. Generate **Webhook Secret** from Webhooks section

### Step 2: Install Razorpay SDK

**Backend:**
```bash
cd /app/backend
pip install razorpay
pip freeze > requirements.txt
```

**Frontend:**
```bash
cd /app/frontend
yarn add react-native-razorpay
```

### Step 3: Update Backend .env

```bash
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### Step 4: Backend Payment Implementation

**Create `/app/backend/payment.py`:**

```python
import razorpay
from fastapi import HTTPException, Request
from datetime import datetime, timezone, timedelta
import os
import hmac
import hashlib

razorpay_client = razorpay.Client(auth=(
    os.environ['RAZORPAY_KEY_ID'],
    os.environ['RAZORPAY_KEY_SECRET']
))

class PaymentService:
    def __init__(self, db):
        self.db = db
    
    async def create_subscription_order(self, user_id: str, plan_type: str):
        """
        Create Razorpay order for subscription
        """
        # Plan amounts in paise
        plans = {
            "monthly": 49900,  # ₹499
            "yearly": 399900,  # ₹3,999
        }
        
        if plan_type not in plans:
            raise HTTPException(status_code=400, detail="Invalid plan type")
        
        amount = plans[plan_type]
        
        # Create Razorpay order
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "user_id": user_id,
                "plan_type": plan_type
            }
        })
        
        # Save order to database
        await self.db.payment_orders.insert_one({
            "order_id": order["id"],
            "user_id": user_id,
            "plan_type": plan_type,
            "amount": amount,
            "currency": "INR",
            "status": "created",
            "created_at": datetime.now(timezone.utc)
        })
        
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key_id": os.environ['RAZORPAY_KEY_ID']
        }
    
    async def verify_payment(self, payment_data: dict):
        """
        Verify Razorpay payment signature
        """
        try:
            # Verify signature
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': payment_data['order_id'],
                'razorpay_payment_id': payment_data['payment_id'],
                'razorpay_signature': payment_data['signature']
            })
            
            # Get order details
            order = await self.db.payment_orders.find_one({
                "order_id": payment_data['order_id']
            })
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            
            # Update order status
            await self.db.payment_orders.update_one(
                {"order_id": payment_data['order_id']},
                {"$set": {
                    "payment_id": payment_data['payment_id'],
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc)
                }}
            )
            
            # Calculate subscription dates
            starts_at = datetime.now(timezone.utc)
            if order["plan_type"] == "monthly":
                ends_at = starts_at + timedelta(days=30)
            else:  # yearly
                ends_at = starts_at + timedelta(days=365)
            
            # Create/update subscription
            await self.db.subscriptions.update_one(
                {"user_id": order["user_id"]},
                {"$set": {
                    "user_id": order["user_id"],
                    "plan_type": order["plan_type"],
                    "status": "active",
                    "payment_id": payment_data['payment_id'],
                    "order_id": payment_data['order_id'],
                    "starts_at": starts_at,
                    "ends_at": ends_at,
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            
            # Update user premium status
            await self.db.users.update_one(
                {"id": order["user_id"]},
                {"$set": {"isPremium": True}}
            )
            
            return {"status": "success", "subscription_ends": ends_at.isoformat()}
            
        except razorpay.errors.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    async def handle_webhook(self, request: Request):
        """
        Handle Razorpay webhooks
        """
        payload = await request.body()
        signature = request.headers.get('X-Razorpay-Signature', '')
        
        # Verify webhook signature
        expected_signature = hmac.new(
            os.environ['RAZORPAY_WEBHOOK_SECRET'].encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected_signature:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        event = await request.json()
        
        # Handle different events
        if event['event'] == 'payment.captured':
            payment = event['payload']['payment']['entity']
            # Update payment status
            await self.db.payment_orders.update_one(
                {"order_id": payment['order_id']},
                {"$set": {"webhook_received": True}}
            )
        
        return {"status": "processed"}
```

**Update `/app/backend/server.py`:**

```python
from payment import PaymentService

payment_service = PaymentService(db)

@api_router.post("/payment/create-order")
async def create_payment_order(plan_type: str, request: Request):
    user = await auth_service.get_current_user(request)
    return await payment_service.create_subscription_order(user["id"], plan_type)

@api_router.post("/payment/verify")
async def verify_payment(payment_data: dict):
    return await payment_service.verify_payment(payment_data)

@api_router.post("/payment/webhook")
async def payment_webhook(request: Request):
    return await payment_service.handle_webhook(request)
```

### Step 5: Frontend Razorpay Implementation

**Update `/app/frontend/app/payment.tsx`:**

```typescript
import { useState } from 'react';
import { Alert } from 'react-native';
import RazorpayCheckout from 'react-native-razorpay';
import axios from 'axios';
import { useAuth } from './context/AuthContext';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

export default function PaymentScreen() {
  const { user, updatePremiumStatus } = useAuth();
  const router = useRouter();
  const [selectedPlan, setSelectedPlan] = useState<'monthly' | 'yearly'>('yearly');
  const [processing, setProcessing] = useState(false);

  const handlePayment = async () => {
    setProcessing(true);

    try {
      // Create order on backend
      const orderResponse = await axios.post(
        `${BACKEND_URL}/api/payment/create-order`,
        { plan_type: selectedPlan },
        { withCredentials: true }
      );

      const { order_id, amount, currency, key_id } = orderResponse.data;

      // Open Razorpay checkout
      const options = {
        description: `The Mirror Note ${selectedPlan === 'monthly' ? 'Monthly' : 'Yearly'} Subscription`,
        image: 'https://your-logo-url.com/logo.png',
        currency: currency,
        key: key_id,
        amount: amount,
        name: 'The Mirror Note',
        order_id: order_id,
        prefill: {
          email: user?.email,
          name: user?.name,
        },
        theme: { color: '#8A9A5B' }
      };

      const data = await RazorpayCheckout.open(options);

      // Payment successful, verify on backend
      const verifyResponse = await axios.post(
        `${BACKEND_URL}/api/payment/verify`,
        {
          order_id: data.razorpay_order_id,
          payment_id: data.razorpay_payment_id,
          signature: data.razorpay_signature,
        },
        { withCredentials: true }
      );

      if (verifyResponse.data.status === 'success') {
        updatePremiumStatus(true);
        Alert.alert(
          'Payment Successful! 🎉',
          'You now have premium access to all features.',
          [
            {
              text: 'Continue',
              onPress: () => router.replace('/(tabs)/dashboard'),
            },
          ]
        );
      }
    } catch (error: any) {
      console.error('Payment error:', error);
      Alert.alert(
        'Payment Failed',
        error.response?.data?.detail || error.message || 'Something went wrong'
      );
    } finally {
      setProcessing(false);
    }
  };

  // ... rest of your UI code
}
```

### Step 6: Configure Webhooks

1. Go to Razorpay Dashboard → Webhooks
2. Add webhook URL: `https://your-app.com/api/payment/webhook`
3. Select events:
   - payment.captured
   - payment.failed
   - subscription.charged
4. Note down the webhook secret

---

## 🧪 Testing

### Google Auth Testing:
```bash
# Create test user in MongoDB
mongosh --eval "
use('test_database');
db.users.insertOne({
  id: 'test-user-123',
  email: 'test@example.com',
  name: 'Test User',
  isPremium: false,
  created_at: new Date()
});
"

# Test auth endpoint
curl -X GET "https://your-app.com/api/auth/me" \
  -H "Authorization: Bearer test_session_token"
```

### Razorpay Testing:
Use Razorpay test cards:
- **Success**: 4111 1111 1111 1111
- **Failure**: 4000 0000 0000 0002
- **CVV**: Any 3 digits
- **Expiry**: Any future date

---

## 🚀 Production Checklist

### Google Auth:
- [ ] Update redirect URLs to production domain
- [ ] Configure proper app scheme in app.json
- [ ] Test on both iOS and Android devices
- [ ] Verify session expiry (7 days)
- [ ] Test logout functionality

### Razorpay:
- [ ] Switch to live API keys in production
- [ ] Configure webhook with production URL
- [ ] Test actual payment flow
- [ ] Verify subscription renewal logic
- [ ] Set up payment failure notifications
- [ ] Configure GST/tax settings in Razorpay Dashboard

---

## 📚 Additional Resources

- [Emergent Auth Documentation](https://auth.emergentagent.com/docs)
- [Razorpay API Documentation](https://razorpay.com/docs/api/)
- [Expo Deep Linking](https://docs.expo.dev/guides/linking/)
- [React Native Razorpay](https://github.com/razorpay/react-native-razorpay)

---

## 🆘 Common Issues

### Google Auth:
**Issue**: Session not persisting
**Fix**: Ensure cookies are set with `httpOnly=True, secure=True, samesite="none"`

**Issue**: Deep link not working
**Fix**: Check app.json has correct scheme and linking configuration

### Razorpay:
**Issue**: Payment signature verification failed
**Fix**: Ensure using correct key_secret and order_id/payment_id match

**Issue**: Webhook not triggering
**Fix**: Check webhook URL is publicly accessible and signature verification is correct

---

For more help, contact support or check the testing playbook saved at `/app/auth_testing.md`
