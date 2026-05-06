# VaaNi — AI for Smart Multilingual Helpline Assistance
### Prototype for Karnataka 1092 Helpline (AI for Bharat Hackathon)

> **"Understanding comes before action"**
> VaaNi ensures citizens are correctly understood before any response is given.

---

🌐 **Live Demo:** [vaani-ai-for-smart-multilingual-helpline.onrender.com](https://vaani-ai-for-smart-multilingual-helpline.onrender.com)

## What is VaaNi?

VaaNi (ವಾಣಿ) is a real-time AI voice-to-voice assistant that acts as an intelligent interpreter layer between citizens and government agents. It ensures accurate understanding is verified before any response is given.

### Core Flow

```
Citizen Speaks  →  AI Interprets  →  AI Verifies  →  Agent Responds
(any language)    (dialect-aware)   "Did I understand    (with context)
                                     you correctly?")
                                          ↓
                                    If unclear or distress:
                                    Human Takeover (seamless)
```

## Features

- 🎙️ Multilingual: Kannada, Hindi, English
- 🗣️ Dialect-aware: Dharwad, Mysore, Coastal, Rural
- ✅ Verified understanding loop — AI confirms before agent responds
- 💭 Sentiment & distress detection
- 🚨 Automatic escalation to human agent
- 📊 Agent dashboard with live interpretation
- 🧠 Continuous learning from corrections


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


*Built for AI for Bharat Hackathon — PAN IIT Bangalore & Government of Karnataka*
