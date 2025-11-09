# 🎤 The Mirror Note

**AI-Powered Voice Assessment Platform**

> Discover your voice, elevate your communication skills, and unlock your full potential as a speaker with personalized AI-driven insights.

[![Built with Expo](https://img.shields.io/badge/Built%20with-Expo-000020.svg?style=flat&logo=expo)](https://expo.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)](https://openai.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Production Integration](#-production-integration)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🌟 Overview

**The Mirror Note** is a revolutionary mobile application that analyzes your voice to provide actionable insights on your speaking style, clarity, confidence, and communication effectiveness. Using cutting-edge AI technologies (OpenAI Whisper for transcription and GPT-4 for analysis), the app helps users improve their public speaking, presentation skills, and overall communication abilities.

### Why The Mirror Note?

- 🎯 **Personalized Feedback**: Get detailed insights tailored to your unique voice profile
- 📊 **Comprehensive Analysis**: Track metrics like speaking pace, filler words, pitch, clarity, and confidence
- 🧠 **AI-Powered Coaching**: Receive personalized training questions to improve weak areas
- 📱 **Mobile-First**: Practice and analyze your voice anytime, anywhere
- 🎨 **Beautiful UI**: Sage green themed design for a calming, professional experience

---

## ✨ Features

### Core Functionality

#### 🎙️ Voice Recording
- **Two Recording Modes**: Free Speaking & Guided Practice (up to 2 minutes)
- Real-time waveform visualization
- Microphone permission handling

#### 🧪 AI-Powered Analysis
- **Speech Transcription**: OpenAI Whisper for accurate transcription
- **Voice Metrics**: Speaking pace (WPM), filler word detection, pitch analysis (Hz)
- **Scoring**: Overall (0-100), Clarity, Confidence, Tone
- **Voice Archetype**: Identifies unique speaking style (e.g., "Warm Storyteller")

#### 📈 Comprehensive Results
- Visual charts for metrics (bar charts, donut charts)
- Detailed filler words breakdown
- Strengths and improvement areas
- Pitch visualization

#### 🎓 Personalized Training
- AI-generated training questions based on your analysis
- Free tier: 3 questions per assessment
- Premium tier: 10 questions with detailed answers

#### 💎 Premium Features
- Subscription plans: Monthly (₹499), Yearly (₹3,999)
- Unlimited assessments
- Access to all training questions
- Razorpay payment integration (production-ready)

#### 👤 User Management
- Simple email/name authentication (current)
- Google OAuth ready (see integration guide)
- Assessment history tracking

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|----------|
| React Native | 0.79 | Cross-platform mobile framework |
| Expo | 54 | Development platform & build tools |
| TypeScript | 5.8 | Type-safe development |
| Expo AV | 16 | Audio recording & playback |
| Axios | 1.13 | HTTP client for API calls |
| Expo Router | 5 | File-based navigation |

### Backend
| Technology | Version | Purpose |
|------------|---------|----------|
| FastAPI | 0.110 | High-performance Python web framework |
| Python | 3.10+ | Backend programming language |
| Motor | 3.3 | Async MongoDB driver |
| OpenAI API | 2.7 | Whisper + GPT-4 |
| Pydantic | 2.12 | Data validation |
| Uvicorn | 0.25 | ASGI server |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│         Mobile App (React Native/Expo)      │
│  Dashboard → Recording → Processing → Results│
│                      ↓ (Axios)              │
└─────────────────────┬───────────────────────┘
                      │
┌─────────────────────▼───────────────────────┐
│            FastAPI Backend                  │
│  /api/analyze-voice, /api/assessment/{id}   │
│          ↓            ↓            ↓         │
│     OpenAI      MongoDB       Razorpay      │
│  Whisper+GPT4   (Motor)       (Prod)        │
└─────────────────────────────────────────────┘
```

**Data Flow**: Recording → Base64 Upload → Whisper Transcription → GPT-4 Analysis → MongoDB Storage → Results Display

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ - [Download](https://nodejs.org/)
- **Python** 3.10+ - [Download](https://www.python.org/)
- **MongoDB** - [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) or local
- **OpenAI API Key** - [Get Key](https://platform.openai.com/)
- **Expo CLI** - `npm install -g expo-cli`

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cat > .env << EOF
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/
DB_NAME=mirrornote
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
EOF

# 5. Run server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000` | Docs: `http://localhost:8000/docs`

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install  # or yarn install

# 3. Create .env file
echo "EXPO_PUBLIC_BACKEND_URL=http://localhost:8000" > .env

# For physical device testing:
# Replace localhost with your computer's IP (find via ipconfig/ifconfig)
# Example: EXPO_PUBLIC_BACKEND_URL=http://192.168.1.100:8000

# 4. Start Expo
npx expo start

# 5. Run on device/emulator
# Option A: Scan QR with Expo Go app (recommended)
# Option B: Press 'i' for iOS simulator (macOS only)
# Option C: Press 'a' for Android emulator
# Option D: Press 'w' for web browser
```

---

## 📁 Project Structure

```
mirrornote-emergent/
├── backend/
│   ├── server.py              # FastAPI app with all endpoints
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables (create)
│
├── frontend/
│   ├── app/
│   │   ├── (tabs)/           # Tab navigation
│   │   │   ├── dashboard.tsx # Main dashboard
│   │   │   ├── history.tsx   # Assessment history
│   │   │   └── profile.tsx   # User profile
│   │   ├── auth/
│   │   │   └── login.tsx     # Login screen
│   │   ├── context/
│   │   │   └── AuthContext.tsx # Auth state
│   │   ├── constants/
│   │   │   └── theme.ts      # Design system
│   │   ├── index.tsx         # Splash screen
│   │   ├── recording.tsx     # Voice recording
│   │   ├── processing.tsx    # Analysis processing
│   │   ├── results.tsx       # Results display
│   │   └── payment.tsx       # Subscription
│   ├── package.json
│   └── .env                  # Environment variables (create)
│
├── PRODUCTION_INTEGRATION_GUIDE.md  # Google Auth & Razorpay
├── QUICK_START_PRODUCTION.md        # Quick setup guide
├── test_result.md                   # Testing documentation
└── README.md                        # This file
```

---

## 📡 API Documentation

### Base URL
```
Development: http://localhost:8000/api
Production: https://your-domain.com/api
```

### Endpoints

#### 1. Health Check
```http
GET /api/
```
**Response**:
```json
{ "message": "The Mirror Note API - Voice Assessment Platform" }
```

#### 2. Analyze Voice
```http
POST /api/analyze-voice
```
**Request**:
```json
{
  "audio_base64": "base64_encoded_audio_string",
  "user_id": "user_123",
  "recording_mode": "free",
  "recording_time": 30
}
```
**Response**:
```json
{
  "assessment_id": "uuid-v4",
  "status": "completed",
  "message": "Analysis completed successfully"
}
```

**Processing Steps**:
1. Decode base64 audio
2. Transcribe with OpenAI Whisper
3. Analyze with GPT-4 (archetype, scores, metrics)
4. Generate training questions
5. Store in MongoDB

#### 3. Get Assessment
```http
GET /api/assessment/{assessment_id}
```
**Response**:
```json
{
  "assessment_id": "uuid-v4",
  "user_id": "user_123",
  "processed": true,
  "transcription": "Your transcribed speech...",
  "analysis": {
    "archetype": "Confident Presenter",
    "overall_score": 85,
    "clarity_score": 88,
    "confidence_score": 82,
    "tone": "Professional",
    "strengths": ["Clear articulation", "Consistent pacing"],
    "improvements": ["Reduce filler words", "Vary tone"],
    "speaking_pace": 145,
    "pitch_avg": 165,
    "pitch_range": "Medium",
    "filler_words": { "um": 3, "like": 5 },
    "filler_count": 8,
    "word_count": 75
  },
  "training_questions": [
    {
      "question": "How can I reduce filler words?",
      "answer": "Practice pausing instead...",
      "is_free": true
    }
  ]
}
```

### Production Endpoints
See `PRODUCTION_INTEGRATION_GUIDE.md` for:
- `POST /api/auth/session` - Google OAuth
- `GET /api/auth/me` - Get current user
- `POST /api/payment/create-order` - Razorpay
- `POST /api/payment/verify` - Payment verification

---

## 🧪 Testing

### Backend Tests

```bash
# Run automated test suite
cd backend
python ../backend_test.py
```

**Tests include**:
- ✅ Health check endpoint
- ✅ MongoDB connectivity
- ✅ Voice analysis with mock audio
- ✅ Assessment retrieval
- ✅ Error handling

### Frontend Testing

**Manual Test Flow**:
1. Launch → Splash screen
2. Login → Email/name entry
3. Dashboard → View stats
4. Record → Choose mode, record voice (up to 2 min)
5. Process → Watch analysis stages
6. Results → View scores, charts, training questions
7. Payment → Mock subscription flow
8. History → View past assessments

**Test on**:
- iOS Simulator (macOS)
- Android Emulator
- Physical device (Expo Go)
- Web browser (limited audio support)

### Interactive API Docs
```
http://localhost:8000/docs
```

---

## 🔐 Production Integration

### Google Authentication (5 minutes)

**Production-ready** using Emergent Auth service.

```bash
# Backend
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

1. Add `auth.py` to backend
2. Update frontend `AuthContext.tsx`
3. Configure deep linking in `app.json`:
```json
{ "expo": { "scheme": "mirrornote" } }
```

**Flow**: User → Google Auth → App with session → Backend verifies → httpOnly cookie

### Razorpay Payments (10 minutes)

**Payment UI implemented** with mock flow. Production integration ready.

1. Get credentials from [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Install: `pip install razorpay` + `yarn add react-native-razorpay`
3. Add to `.env`:
```bash
RAZORPAY_KEY_ID=rzp_live_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
RAZORPAY_WEBHOOK_SECRET=whsec_xxxxx
```
4. Add `payment.py` to backend
5. Configure webhooks

**Plans**: Monthly ₹499 | Yearly ₹3,999  
**Test Cards**: Success `4111 1111 1111 1111` | Fail `4000 0000 0000 0002`

**Full Details**: See `PRODUCTION_INTEGRATION_GUIDE.md`

---

## 🚢 Deployment

### Backend

**Option 1: Emergent Agent Platform**
- Deploy via CLI/dashboard
- Set environment variables
- URL: `https://your-app.preview.emergentagent.com`

**Option 2: Traditional Hosting** (Heroku, Railway, Render)
```bash
# Example: Railway
npm install -g @railway/cli
railway login
railway init
railway up
```

### Frontend

**Option 1: EAS (iOS & Android)**
```bash
npm install -g eas-cli
eas login
eas build:configure
eas build --platform all
eas submit --platform ios
eas submit --platform android
```

**Option 2: Web**
```bash
npx expo export:web
# Deploy web-build/ to Netlify/Vercel
```

---

## 🎨 Design System

### Color Palette (Sage Green Theme)

```typescript
const COLORS = {
  primary: '#8A9A5B',       // Sage green
  primaryDark: '#6B7A3F',   // Darker sage
  background: '#F8F9F5',    // Off-white green tint
  textPrimary: '#2D3319',   // Dark olive
  error: '#D32F2F',
  success: '#4CAF50',
};
```

### Typography & Spacing
```typescript
FONT_SIZES: { xs: 12, sm: 14, md: 16, lg: 18, xl: 24, xxl: 32 }
SPACING: { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 }
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

**Standards**:
- Frontend: TypeScript, functional components, theme system
- Backend: PEP 8, type hints, docstrings
- Test all features before PR
- Update documentation

---

## 🆘 Support & Troubleshooting

### Common Issues

**Backend won't start**:
- Check Python 3.10+: `python --version`
- Verify `.env` variables
- Test MongoDB connection

**Frontend won't build**:
- Clear cache: `npx expo start -c`
- Reinstall: `rm -rf node_modules && npm install`
- Check Node 18+: `node --version`

**Audio not working**:
- Check microphone permissions
- Test on physical device
- Ensure HTTPS in production

**OpenAI errors**:
- Verify API key validity
- Check billing/quota limits
- Ensure model names: `whisper-1`, `gpt-4`

### Documentation
- Production Integration: `PRODUCTION_INTEGRATION_GUIDE.md`
- Quick Start: `QUICK_START_PRODUCTION.md`
- Test Results: `test_result.md`
- API Docs: `http://localhost:8000/docs`

---

## 🗺️ Roadmap

### Current (v1.0.0)
- ✅ Voice recording (free & guided)
- ✅ AI transcription & analysis
- ✅ Results dashboard with charts
- ✅ Training questions
- ✅ Premium UI (mocked)
- ✅ User authentication
- ✅ Assessment history

### Upcoming
- [ ] Social sharing features
- [ ] Progress comparison over time
- [ ] Advanced analytics & trends
- [ ] Live AI coaching sessions
- [ ] Multilingual support
- [ ] Team/corporate plans
- [ ] API access for developers
- [ ] Podcast/meeting analysis

---

## 📄 License

This project is proprietary software. All rights reserved.

**Copyright © 2024 The Mirror Note**

Unauthorized copying, distribution, or modification is prohibited.

---

## 👥 Credits

- **Developer**: Shaurya
- **Platform**: Emergent Agent
- **AI**: OpenAI (Whisper + GPT-4)
- **Frameworks**: Expo, FastAPI

---

## 🎯 Quick Links

- [Getting Started](#-getting-started)
- [API Documentation](#-api-documentation)
- [Production Integration Guide](PRODUCTION_INTEGRATION_GUIDE.md)
- [Quick Start Guide](QUICK_START_PRODUCTION.md)
- [Test Documentation](test_result.md)
- [API Interactive Docs](http://localhost:8000/docs)

---

<div align="center">

**Made with ❤️ using Expo, FastAPI, and OpenAI**

[⭐ Star this repo](https://github.com/yourusername/mirrornote-emergent) | [🐛 Report Bug](https://github.com/yourusername/mirrornote-emergent/issues) | [💡 Request Feature](https://github.com/yourusername/mirrornote-emergent/issues)

</div>
