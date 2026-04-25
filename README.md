# VaaNi — AI Voice System for 1092 Helpline
### Karnataka Government · AI for Bharat Hackathon 2026

> **"Understanding comes before action"**
> VaaNi ensures citizens are correctly understood before any response is given.

---

## What is VaaNi?

VaaNi (ವಾಣಿ) is a real-time AI voice-to-voice assistant for Karnataka's 1092 citizen helpline. It bridges language, dialect, and cultural gaps between citizens and government agents using Claude AI.

## Features

- 🎙️ Multilingual: Kannada, Hindi, English
- 🗣️ Dialect-aware: Dharwad, Mysore, Coastal, Rural
- ✅ Verified understanding loop — AI confirms before agent responds
- 💭 Sentiment & distress detection
- 🚨 Automatic escalation to human agent
- 📊 Agent dashboard with live interpretation
- 🧠 Continuous learning from corrections

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/vaani.git
cd vaani/backend
pip install -r requirements.txt
python main.py
```
Open `frontend/index.html` in your browser.

## Project Structure

```
vaani/
├── frontend/
│   └── index.html       # Agent dashboard
├── backend/
│   ├── main.py          # FastAPI server
│   └── requirements.txt
├── render.yaml          # Render deployment config
└── START_VAANI.bat      # Windows one-click launcher
```

## Tech Stack

- **AI**: Claude 3.5 Haiku via OpenRouter
- **Backend**: FastAPI + SQLite
- **Frontend**: Vanilla HTML/CSS/JS
- **Deployment**: Render

## Live Demo

🌐 [vaani-1092.onrender.com](https://vaani-1092.onrender.com)

---

*Built for AI for Bharat Hackathon — PAN IIT Bangalore & Government of Karnataka*
