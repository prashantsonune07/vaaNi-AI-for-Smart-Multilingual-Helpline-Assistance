# VaaNi — AI for Smart Multilingual Helpline Assistance

<div align="center">

![VaaNi](https://img.shields.io/badge/VaaNi-1092%20AI%20Helpline-FF6B00?style=for-the-badge)
![Hackathon](https://img.shields.io/badge/AI%20for%20Bharat-PAN%20IIT%20Bangalore-2D3FBF?style=for-the-badge)
![Live](https://img.shields.io/badge/Status-Live%20on%20Render-0D9E6B?style=for-the-badge)

**"Accurate Understanding Before Response"**

An AI System for Accurate Understanding, Verification, and Response
in Multilingual Citizen Helpline Interactions

🌐 **Live Demo:** [vaani-ai-for-smart-multilingual-helpline.onrender.com](https://vaani-ai-for-smart-multilingual-helpline.onrender.com)

</div>

---

## Problem Statement

Karnataka's 1092 citizen helpline handles thousands of calls daily across **multiple languages, dialects, and emotional states**. Agents often misunderstand citizen issues due to:

- Language barriers (Kannada, Hindi, English, Telugu)
- Regional dialects (Dharwad, Mysore, Coastal, Rural)
- Emotionally charged communication (distress, urgency, confusion)
- No verification step before responding

**The biggest failure in citizen services is not lack of response — but wrong response due to wrong understanding.**

---

## Solution — VaaNi (ವಾಣಿ)

VaaNi is a real-time AI voice-to-voice assistant that acts as an **intelligent interpreter layer** between citizens and government agents. It ensures accurate understanding is verified **before** any response is given.

### Core Flow

```
Citizen Speaks  →  AI Interprets  →  AI Verifies  →  Agent Responds
(any language)    (dialect-aware)   "Did I understand    (with context)
                                     you correctly?")
                                          ↓
                                    If unclear or distress:
                                    Human Takeover (seamless)
```

---

## Key Features

### 🎙️ Voice-to-Voice Communication
- Real-time speech processing for live helpline calls
- Support for **Kannada, Hindi, English** with dialect awareness
- Low-latency AI interpretation suitable for live call environments

### ✅ Verified Understanding Loop
- AI restates the interpreted issue to the citizen
- Citizen confirms (Yes) or corrects (No)
- **Understanding is verified before the agent responds** — the core innovation
- If corrected: AI re-interprets with citizen's input and verifies again

### ❌ Smart Correction Flow
- Citizen clicks "Needs Correction" → correction panel appears
- 6 quick-select issue categories (Ration Card, Pension, Water, Emergency, Land Records, Other)
- Editable text box pre-filled with AI's interpretation
- AI re-runs with corrected input → new verification question generated in correct language
- All corrections saved to learning log for continuous improvement

### 💛 Sentiment & Emotion Detection
- Detects: Distress · Urgency · Anger · Fear · Confusion · Calm
- Confidence scoring per interpretation
- Automatic escalation trigger on high distress

### 🛡️ Human Takeover (Graceful Escalation)
- Triggers when: confidence is low, repeated misunderstanding, distress detected
- Seamless handover — agent gets full context before taking over
- No friction in the escalation process

### 🌐 Dialect & Cultural Awareness
- Dharwad, Mysore, Coastal, Rural Kannada variations
- Local expressions and colloquial usage
- Cultural context in interpretation

### 📊 Live Agent Dashboard
- Real-time call status and timer (resets per scenario)
- AI interpretation with confidence score
- Sentiment bars (Distress · Urgency · Clarity · AI Confidence)
- Live transcript and learning log
- Session-level statistics

### 🧠 Continuous Learning
- Every confirmed interpretation → validated training signal
- Every correction → captured for model improvement
- Learning log visible in admin panel

### 🏛️ Admin Panel (`/admin`)
- Password-protected dashboard
- Sessions viewer with full metadata (language, category, emotion, confidence, verified, corrections, escalated)
- Transcripts viewer per session
- Learning log with confirmed/corrected entries
- User management (Superuser creation)
- API reference documentation

---

## Live Demo Scenarios

| Scenario | Language | Issue |
|---|---|---|
| 🌾 Ration Card | ಕನ್ನಡ (Kannada) | Family ration card not issued for 3 months |
| 👴 Pension Issue | ಕನ್ನಡ (Kannada) | Widow pension stopped without notice |
| 💧 Water Supply | हिंदी (Hindi) | No water for 5 days in colony |
| 🚨 Emergency | URGENT | Medical emergency — high distress |
| 📋 Land Records | English | Need certified copy of land records |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **AI Model** | Claude 3.5 Haiku via OpenRouter API |
| **Backend** | Python · FastAPI · Uvicorn |
| **Database** | SQLite (persistent disk on Render) |
| **Frontend** | Vanilla HTML · CSS · JavaScript |
| **Deployment** | Render (Web Service + Persistent Disk) |
| **Real-time** | WebSocket + Server-Sent Events (SSE) |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main agent dashboard |
| `GET` | `/health` | System health check |
| `GET` | `/stats` | Live statistics (calls, accuracy, verified, escalated) |
| `POST` | `/session/create` | Create new call session |
| `POST` | `/interpret` | AI interpretation of citizen speech |
| `POST` | `/feedback` | Record citizen confirmation / correction / escalation |
| `POST` | `/transcript` | Save conversation transcript entry |
| `GET` | `/training-data` | Export learning log data |
| `WS` | `/ws/{session_id}` | WebSocket for real-time updates |
| `GET` | `/admin` | Admin panel (password protected) |
| `POST` | `/admin/login` | Admin authentication |
| `GET` | `/admin/sessions` | View all sessions |
| `GET` | `/admin/transcripts` | View transcripts |
| `GET` | `/admin/learning` | View learning log |

---

## Project Structure

```
vaani/
├── backend/
│   ├── main.py              # FastAPI server + embedded frontend HTML
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── index.html           # Agent dashboard (served by backend)
├── render.yaml              # Render deployment config
├── START_VAANI.bat          # Windows one-click local launcher
└── README.md
```

---

## Local Setup

### Prerequisites
- Python 3.8+ (`py --version`)
- pip

### Installation

```bash
# Clone the repo
git clone https://github.com/prashantsonune07/vaaNi-AI-for-Smart-Multilingual-Helpline-Assistance.git
cd vaaNi-AI-for-Smart-Multilingual-Helpline-Assistance/backend

# Install dependencies
py -m pip install -r requirements.txt

# Start the server
py main.py
```

Open your browser at: `http://localhost:8000`

### Windows — One Click Start

Double-click `START_VAANI.bat` — it installs nothing, just starts the server and opens the browser automatically.

---

## Environment Variables

Set these in your Render dashboard (Environment tab):

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter API key (get from openrouter.ai) |
| `ADMIN_PASSWORD` | Password for `/admin` panel |
| `DB_PATH` | Database path (set to `/var/data/vaani.db` on Render) |

---

## Deployment (Render)

The app is configured via `render.yaml`:

```yaml
startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

A **persistent disk** is mounted at `/var/data` to preserve the SQLite database across deploys.

---

## Evaluation Criteria Alignment

| Criterion | Weight | VaaNi Implementation |
|---|---|---|
| Voice-to-voice assistance | 25% | Real-time AI interpretation with SSE streaming |
| Understanding verification & guardrails | 20% | Explicit verify loop + correction flow + escalation |
| Dialect & cultural understanding | 15% | Dharwad/Mysore/Coastal/Rural Kannada awareness |
| Sentiment & emotional interpretation | 15% | Distress/Urgency/Clarity/Confidence scoring |
| Ease of use for agents | 15% | Clean dashboard, one-click scenarios, live brief |
| Technical design & extensibility | 10% | REST API + WebSocket + persistent DB + admin panel |

---

## Disclaimer

> ⚠️ This is a **prototype demo** and not an official government system.
> AI-powered prototype demonstrating multilingual voice understanding and verification for citizen services.

---

<div align="center">

Built with ❤️ for **AI for Bharat Hackathon** — PAN IIT Bangalore & Government of Karnataka

*VaaNi — Because understanding comes before action*

</div>
