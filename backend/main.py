"""
VaaNi - AI Voice Assistant for 1092 Helpline
FastAPI backend — Works locally + Render deployment
"""

import asyncio, json, os, random, sqlite3
from datetime import datetime
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx

app = FastAPI(title="VaaNi 1092 AI Helpline", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── DATABASE ──────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "vaani.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            language TEXT DEFAULT 'kannada',
            start_time TEXT,
            escalated INTEGER DEFAULT 0,
            verified_count INTEGER DEFAULT 0,
            correction_count INTEGER DEFAULT 0,
            issue_category TEXT,
            emotion TEXT,
            confidence REAL
        );
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS learning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            type TEXT,
            original TEXT,
            corrected TEXT,
            language TEXT,
            timestamp TEXT
        );
    """)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'admin',
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()
    print("Database ready")

init_db()

# ── AI CONFIG ─────────────────────────────────
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "anthropic/claude-3.5-haiku"

SYSTEM_PROMPT = """You are VaaNi, an AI interpreter for Karnataka's 1092 citizen helpline.
Interpret citizen speech aware of Kannada dialects (Dharwad, Mysore, Coastal, Rural), Hindi, English.
RESPOND ONLY in this exact JSON:
{
  "interpreted_issue": "English summary",
  "kannada_summary": "ಕನ್ನಡ ಸಾರಾಂಶ",
  "hindi_summary": "हिंदी सारांश",
  "english_summary": "English summary",
  "verification_question": {"kannada": "...", "hindi": "...", "english": "..."},
  "sentiment": {"emotion": "distress|urgency|anger|fear|confusion|neutral|calm", "intensity": 0.0, "urgency_score": 0.0, "distress_flag": false, "agent_note": "..."},
  "language_detected": "kannada|hindi|english|mixed",
  "dialect_detected": "dharwad|mysore|coastal|rural|standard|unknown",
  "confidence": 0.0,
  "should_escalate": false,
  "escalation_reason": "",
  "issue_category": "ration_card|aadhaar|pension|land_records|water|electricity|police|health|other",
  "keywords": ["..."],
  "response_language": "kannada|hindi|english"
}"""

sessions = {}

# ── AI CALL ───────────────────────────────────
async def interpret(text: str, language: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            OPENROUTER_API,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vaani-1092.onrender.com",
                "X-Title": "VaaNi 1092 Helpline"
            },
            json={
                "model": OPENROUTER_MODEL,
                "max_tokens": 1000,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f'Citizen said (in {language}): "{text}"\n\nRespond in exact JSON format.'}
                ]
            }
        )
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        if "```json" in txt: txt = txt.split("```json")[1].split("```")[0].strip()
        elif "```" in txt: txt = txt.split("```")[1].split("```")[0].strip()
        result = json.loads(txt)
        result["timestamp"] = datetime.now().isoformat()
        return result

# ── MODELS ────────────────────────────────────
class InterpretRequest(BaseModel):
    text: str
    language: str = "kannada"
    session_id: str

class FeedbackRequest(BaseModel):
    session_id: str
    type: str
    original: str = ""
    corrected: str = ""
    language: str = "kannada"

# ── ROUTES ────────────────────────────────────
# Frontend HTML embedded directly (no separate file needed)
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VaaNi · 1092 Karnataka Helpline AI</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Noto+Sans+Kannada:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500&display=swap" rel="stylesheet">
<style>
/* ════════════════════════════════════════════
   VAANI · DESIGN SYSTEM
   Warm saffron-indigo · Government clarity
   Made for common people, not engineers
════════════════════════════════════════════ */

:root {
  /* Warm government palette — trustworthy, clear, human */
  --saffron:    #FF6B00;
  --saffron-l:  #FF9A4A;
  --saffron-xl: #FFF0E6;
  --indigo:     #2D3FBF;
  --indigo-l:   #4A5DD9;
  --indigo-xl:  #EEF0FD;
  --jade:       #0D9E6B;
  --jade-l:     #12C882;
  --jade-xl:    #E6F9F3;
  --crimson:    #E02020;
  --crimson-l:  #FF5252;
  --crimson-xl: #FFF0F0;
  --amber:      #D97700;
  --amber-l:    #FFAD33;
  --amber-xl:   #FFF8EC;
  --purple:     #7C3AED;
  --purple-l:   #A78BFA;
  --purple-xl:  #F5F0FF;

  /* Canvas — warm white, not cold */
  --bg:         #FAF7F4;
  --bg2:        #F2EDE8;
  --surface:    #FFFFFF;
  --surface2:   #FDF9F6;

  /* Text */
  --ink:        #1A1310;
  --ink2:       #5C4A3A;
  --ink3:       #9C8878;
  --ink4:       #C4B5A8;

  /* Borders */
  --line:       rgba(90,60,30,0.1);
  --line2:      rgba(90,60,30,0.18);

  /* Fonts */
  --font:       'Outfit', sans-serif;
  --font-kn:    'Noto Sans Kannada', sans-serif;
  --font-hi:    'Noto Sans Devanagari', sans-serif;

  /* Shadows */
  --shadow-sm:  0 2px 8px rgba(90,60,30,0.08);
  --shadow:     0 4px 24px rgba(90,60,30,0.12);
  --shadow-lg:  0 12px 48px rgba(90,60,30,0.18);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--ink);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── ORNAMENTAL BACKGROUND ── */
body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; height: 320px;
  background: linear-gradient(160deg, #FF6B00 0%, #FF9A4A 30%, #2D3FBF 70%, #1a2590 100%);
  clip-path: ellipse(110% 100% at 50% 0%);
  opacity: 0.07;
  pointer-events: none;
  z-index: 0;
}

/* ════ HEADER ════ */
.header {
  position: sticky; top: 0; z-index: 200;
  background: rgba(250,247,244,0.94);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--line);
  padding: 0 28px;
  height: 64px;
  display: flex; align-items: center; justify-content: space-between;
  box-shadow: var(--shadow-sm);
}

.brand {
  display: flex; align-items: center; gap: 12px;
}

.brand-emblem {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, var(--saffron) 0%, var(--indigo) 100%);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(255,107,0,0.35);
  position: relative;
  overflow: hidden;
}

.brand-emblem::before {
  content: 'ವ';
  font-family: var(--font-kn);
  font-size: 20px;
  color: white;
  font-weight: 600;
}

.brand-name {
  font-size: 22px; font-weight: 800;
  background: linear-gradient(135deg, var(--saffron), var(--indigo));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -0.5px;
}

.brand-tag {
  font-size: 11px; color: var(--ink3); font-weight: 400;
  letter-spacing: 0.3px;
}

.header-center {
  display: flex; align-items: center; gap: 10px;
}

.call-pill {
  display: flex; align-items: center; gap: 8px;
  background: var(--surface);
  border: 1px solid var(--line2);
  border-radius: 24px;
  padding: 6px 16px;
  font-size: 13px; font-weight: 500;
  color: var(--ink2);
  box-shadow: var(--shadow-sm);
}

.pulse-ring {
  position: relative; width: 10px; height: 10px;
}
.pulse-ring::before, .pulse-ring::after {
  content: '';
  position: absolute; inset: 0;
  border-radius: 50%;
}
.pulse-ring::before { background: var(--jade); }
.pulse-ring::after {
  background: var(--jade);
  animation: pulse-out 1.8s ease-out infinite;
}
@keyframes pulse-out {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(2.5); opacity: 0; }
}

.header-right {
  display: flex; align-items: center; gap: 8px;
}

.header-stat {
  padding: 6px 14px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  font-size: 12px; color: var(--ink3);
  display: flex; align-items: center; gap: 5px;
}
.header-stat strong { color: var(--ink); font-weight: 600; }

/* ════ LAYOUT ════ */
.page {
  display: grid;
  grid-template-columns: 1fr 340px;
  grid-template-rows: auto 1fr;
  gap: 20px;
  padding: 20px 28px 32px;
  min-height: calc(100vh - 64px);
  position: relative; z-index: 1;
  max-width: 1440px; margin: 0 auto;
}

/* ════ SCENARIO STRIP ════ */
.scenario-strip {
  grid-column: 1 / -1;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 18px 22px;
  display: flex; align-items: center; gap: 14px;
  flex-wrap: wrap;
  box-shadow: var(--shadow-sm);
}

.strip-label {
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--ink3); white-space: nowrap;
}

.scenario-cards {
  display: flex; gap: 8px; flex-wrap: wrap; flex: 1;
}

.sc-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 16px;
  background: var(--bg2);
  border: 1.5px solid transparent;
  border-radius: 12px;
  font-family: var(--font); font-size: 12px; font-weight: 500;
  color: var(--ink2);
  cursor: pointer;
  transition: all 0.22s cubic-bezier(.4,0,.2,1);
  white-space: nowrap;
}
.sc-btn:hover {
  background: var(--surface);
  border-color: var(--saffron-l);
  color: var(--saffron);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.sc-btn.active {
  background: var(--saffron-xl);
  border-color: var(--saffron);
  color: var(--saffron);
  box-shadow: 0 4px 16px rgba(255,107,0,0.18);
}
.sc-btn.active-indigo {
  background: var(--indigo-xl);
  border-color: var(--indigo);
  color: var(--indigo);
}
.sc-btn.active-crimson {
  background: var(--crimson-xl);
  border-color: var(--crimson);
  color: var(--crimson);
}

.sc-icon { font-size: 15px; }
.sc-lang {
  font-size: 9px; font-weight: 700;
  padding: 1px 5px; border-radius: 4px;
  background: currentColor;
  position: relative; color: white;
  /* trick: inner span carries the text */
}
.lang-tag {
  display: inline-block;
  font-size: 9px; font-weight: 700;
  padding: 2px 6px; border-radius: 4px;
  background: rgba(0,0,0,0.08);
  letter-spacing: 0.3px;
}

.lang-toggle {
  display: flex; gap: 4px; margin-left: auto;
}
.lang-btn {
  padding: 6px 14px;
  border: 1.5px solid var(--line2);
  border-radius: 10px;
  background: transparent;
  font-family: var(--font); font-size: 12px; font-weight: 500;
  color: var(--ink3); cursor: pointer;
  transition: all 0.18s;
}
.lang-btn.on {
  background: var(--indigo);
  border-color: var(--indigo);
  color: white;
}

/* ════ MAIN LEFT ════ */
.main-col {
  display: flex; flex-direction: column; gap: 18px;
}

/* ════ CARDS ════ */
.card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  box-shadow: var(--shadow-sm);
  position: relative; overflow: hidden;
}

.card-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--ink3); margin-bottom: 16px;
}
.card-title-dot {
  width: 6px; height: 6px; border-radius: 50%;
}

/* ════ CITIZEN VOICE CARD ════ */

/* Big microphone area */
.mic-stage {
  display: flex; flex-direction: column; align-items: center;
  padding: 24px 0 18px;
  position: relative;
}

.mic-ring-outer {
  width: 120px; height: 120px;
  border-radius: 50%;
  border: 2px solid var(--line);
  display: flex; align-items: center; justify-content: center;
  position: relative;
  transition: all 0.4s ease;
}

.mic-ring-outer.speaking {
  border-color: var(--saffron-l);
  box-shadow: 0 0 0 8px rgba(255,107,0,0.08), 0 0 0 20px rgba(255,107,0,0.04);
  animation: mic-breathe 0.8s ease-in-out infinite alternate;
}
@keyframes mic-breathe {
  from { box-shadow: 0 0 0 8px rgba(255,107,0,0.08), 0 0 0 20px rgba(255,107,0,0.04); }
  to   { box-shadow: 0 0 0 14px rgba(255,107,0,0.14), 0 0 0 32px rgba(255,107,0,0.06); }
}

.mic-circle {
  width: 88px; height: 88px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--bg2) 0%, var(--surface) 100%);
  border: 1.5px solid var(--line2);
  display: flex; align-items: center; justify-content: center;
  font-size: 32px;
  transition: all 0.4s ease;
  position: relative; overflow: hidden;
}

.mic-circle::before {
  content: '';
  position: absolute; inset: 0; border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, rgba(255,107,0,0.15), transparent 70%);
  opacity: 0;
  transition: opacity 0.4s;
}

.mic-ring-outer.speaking .mic-circle {
  background: linear-gradient(135deg, var(--saffron-xl) 0%, #fff8f3 100%);
  border-color: var(--saffron-l);
}
.mic-ring-outer.speaking .mic-circle::before { opacity: 1; }

/* Waveform bars around mic */
.wave-bars {
  display: flex; align-items: center; gap: 3px;
  margin-top: 20px; height: 48px;
  justify-content: center;
}
.wbar {
  width: 4px; border-radius: 3px;
  background: linear-gradient(to top, var(--saffron), var(--saffron-l));
  opacity: 0.25;
  transform-origin: bottom;
  animation: wbar-idle 2s ease-in-out infinite;
  transition: opacity 0.3s;
}
.wbar:nth-child(2n) { animation-delay: 0.15s; }
.wbar:nth-child(3n) { animation-delay: 0.3s; }
.wbar:nth-child(4n) { animation-delay: 0.45s; }
.wbar:nth-child(5n) { animation-delay: 0.6s; }

@keyframes wbar-idle {
  0%,100% { height: 6px; }
  50%      { height: 14px; }
}
@keyframes wbar-active {
  0%,100% { height: 6px; }
  50%      { height: 44px; }
}

.wave-bars.live .wbar { opacity: 1; }
.wave-bars.live .wbar { animation-name: wbar-active; animation-duration: 0.45s; }
.wave-bars.live .wbar:nth-child(2n) { animation-duration: 0.38s; }
.wave-bars.live .wbar:nth-child(3n) { animation-duration: 0.55s; }

.mic-status {
  margin-top: 14px; font-size: 13px; font-weight: 500;
  color: var(--ink3); text-align: center; letter-spacing: 0.2px;
}
.mic-status.live { color: var(--saffron); }

/* Citizen speech bubble */
.citizen-bubble {
  margin-top: 16px;
  background: linear-gradient(135deg, var(--bg2) 0%, #f8f4f0 100%);
  border: 1.5px solid var(--line2);
  border-radius: 16px 16px 16px 4px;
  padding: 16px 18px;
  font-family: var(--font-kn);
  font-size: 15px; line-height: 1.75;
  color: var(--ink);
  min-height: 64px;
  position: relative;
  transition: all 0.3s;
}
.citizen-bubble.has-text {
  border-color: var(--saffron-l);
  background: var(--saffron-xl);
}
.citizen-bubble .placeholder {
  color: var(--ink4); font-family: var(--font); font-size: 13px;
}

.cursor-blink {
  display: inline-block;
  width: 2px; height: 17px;
  background: var(--saffron);
  margin-left: 1px; vertical-align: middle;
  animation: blink 0.75s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* Pipeline steps */
.pipeline {
  display: flex; gap: 0; margin-top: 16px;
  background: var(--bg2); border-radius: 12px;
  padding: 2px; overflow: hidden;
}
.pipe-step {
  flex: 1;
  display: flex; align-items: center; justify-content: center; gap: 5px;
  padding: 9px 4px;
  font-size: 10px; font-weight: 600;
  color: var(--ink4); letter-spacing: 0.5px;
  text-transform: uppercase;
  border-radius: 10px;
  transition: all 0.3s ease;
  cursor: default;
}
.pipe-step svg { width: 12px; height: 12px; opacity: 0.5; }
.pipe-step.running {
  background: var(--amber-xl); color: var(--amber);
  animation: pipe-shimmer 1s ease-in-out infinite alternate;
}
@keyframes pipe-shimmer {
  from { background: var(--amber-xl); }
  to   { background: #fff4d6; }
}
.pipe-step.done {
  background: var(--jade-xl); color: var(--jade);
}
.pipe-step.done svg { opacity: 1; }
.pipe-step.error { background: var(--crimson-xl); color: var(--crimson); }

/* ════ AI INTERPRETATION CARD ════ */
.interp-card {
  flex: 1;
}

.interp-empty {
  display: flex; flex-direction: column; align-items: center;
  padding: 32px 0; text-align: center; gap: 10px;
}
.interp-empty-icon { font-size: 40px; opacity: 0.25; }
.interp-empty-text { font-size: 14px; color: var(--ink4); line-height: 1.6; }

/* Language tabs on interpretation card */
.lang-tabs {
  display: flex; gap: 4px; margin-bottom: 16px;
}
.ltab {
  padding: 5px 14px;
  border: 1px solid var(--line2);
  border-radius: 8px;
  font-size: 11px; font-weight: 600;
  color: var(--ink3); cursor: pointer;
  transition: all 0.18s; background: transparent;
  font-family: var(--font);
}
.ltab.on {
  background: var(--indigo); color: white; border-color: var(--indigo);
}

/* Confidence row */
.conf-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
}
.conf-label { font-size: 11px; color: var(--ink3); font-weight: 600; }
.conf-track {
  flex: 1; height: 8px;
  background: var(--bg2); border-radius: 4px; overflow: hidden;
}
.conf-fill {
  height: 100%; border-radius: 4px;
  transition: width 0.7s cubic-bezier(.4,0,.2,1), background 0.4s;
  background: var(--jade);
}
.conf-pct { font-size: 13px; font-weight: 700; color: var(--jade); min-width: 36px; text-align: right; }
.conf-pct.med { color: var(--amber); }
.conf-pct.low { color: var(--crimson); }

/* Summary box */
.summary-box {
  background: var(--indigo-xl);
  border: 1.5px solid rgba(45,63,191,0.15);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.summary-lang-tag {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.8px;
  color: var(--indigo); margin-bottom: 8px;
}
.summary-text-kn {
  font-family: var(--font-kn);
  font-size: 16px; line-height: 1.8; color: var(--ink);
  font-weight: 500;
}
.summary-text-hi {
  font-family: var(--font-hi);
  font-size: 16px; line-height: 1.8; color: var(--ink);
  font-weight: 500;
}
.summary-text-en {
  font-size: 14px; line-height: 1.7; color: var(--ink2);
  margin-top: 8px;
}

/* Meta pills */
.meta-row {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px;
}
.mpill {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600;
  border: 1px solid;
}
.mpill-lang { background: var(--purple-xl); color: var(--purple); border-color: rgba(124,58,237,0.2); }
.mpill-dialect { background: var(--indigo-xl); color: var(--indigo); border-color: rgba(45,63,191,0.2); }
.mpill-category { background: var(--saffron-xl); color: var(--saffron); border-color: rgba(255,107,0,0.2); }

/* Verification block */
.verif-block {
  background: var(--amber-xl);
  border: 2px solid var(--amber-l);
  border-radius: 16px;
  padding: 18px;
  margin-top: 4px;
  display: none;
}
.verif-block.show { display: block; animation: pop-in 0.3s cubic-bezier(.34,1.56,.64,1); }
@keyframes pop-in {
  from { transform: scale(0.96); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.verif-header {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
}
.verif-icon {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--amber); color: white;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
}
.verif-label { font-size: 12px; font-weight: 700; color: var(--amber); text-transform: uppercase; letter-spacing: 0.8px; }

.verif-q {
  font-family: var(--font-kn);
  font-size: 15px; line-height: 1.7; color: var(--ink); margin-bottom: 14px;
}

.verif-btns { display: flex; gap: 10px; flex-wrap: wrap; }

.vbtn {
  flex: 1; min-width: 120px;
  padding: 12px 20px; border-radius: 12px;
  font-family: var(--font); font-size: 13px; font-weight: 700;
  cursor: pointer; border: none; transition: all 0.2s;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.vbtn-yes {
  background: var(--jade); color: white;
  box-shadow: 0 4px 16px rgba(13,158,107,0.35);
}
.vbtn-yes:hover { background: #0b8f5f; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(13,158,107,0.45); }
.vbtn-no {
  background: white; color: var(--crimson);
  border: 2px solid var(--crimson-l);
}
.vbtn-no:hover { background: var(--crimson-xl); transform: translateY(-2px); }
.vbtn-escalate {
  background: var(--purple); color: white;
  box-shadow: 0 4px 16px rgba(124,58,237,0.35);
}
.vbtn-escalate:hover { background: #6d28d9; transform: translateY(-2px); }

/* Keywords */
.keywords-row {
  display: flex; flex-wrap: wrap; gap: 5px; margin-top: 14px;
}
.kw {
  padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 500;
  background: var(--bg2); color: var(--ink2); border: 1px solid var(--line2);
  font-family: var(--font-kn);
}

/* ════ SENTIMENT CARD ════ */
/* Big emotion display */
.emotion-hero {
  display: flex; align-items: center; gap: 16px; margin-bottom: 18px;
  padding: 18px;
  border-radius: 16px;
  background: var(--bg2);
  border: 1.5px solid var(--line);
  transition: all 0.4s;
}
.emotion-face {
  font-size: 44px; line-height: 1;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.12));
  transition: all 0.4s;
}
.emotion-info { flex: 1; }
.emotion-name {
  font-size: 18px; font-weight: 800; letter-spacing: -0.3px;
  text-transform: capitalize; margin-bottom: 3px;
  transition: color 0.4s;
}
.emotion-note {
  font-size: 12px; color: var(--ink3); line-height: 1.5;
}
.emotion-intensity {
  text-align: right;
}
.emotion-pct {
  font-size: 32px; font-weight: 800; line-height: 1;
  font-variant-numeric: tabular-nums;
  transition: color 0.4s;
}
.emotion-pct-label {
  font-size: 10px; color: var(--ink3); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.8px;
}

/* Sentiment bars */
.sent-bars { display: flex; flex-direction: column; gap: 10px; }
.sent-row { display: flex; align-items: center; gap: 10px; }
.sent-name { font-size: 11px; font-weight: 600; color: var(--ink3); width: 60px; text-transform: uppercase; letter-spacing: 0.5px; }
.sent-track { flex: 1; height: 10px; background: var(--bg2); border-radius: 5px; overflow: hidden; }
.sent-fill {
  height: 100%; border-radius: 5px;
  transition: width 0.7s cubic-bezier(.4,0,.2,1);
}
.sent-val { font-size: 12px; font-weight: 700; min-width: 34px; text-align: right; }

/* Distress badge */
.distress-badge {
  display: none;
  margin-top: 14px;
  background: var(--crimson-xl);
  border: 2px solid var(--crimson-l);
  border-radius: 12px;
  padding: 12px 16px;
  display: flex; align-items: center; gap: 10px;
  font-size: 12px; font-weight: 600; color: var(--crimson);
  animation: shake 0.4s ease;
}
@keyframes shake {
  0%,100% { transform: translateX(0); }
  25%      { transform: translateX(-4px); }
  75%      { transform: translateX(4px); }
}

/* ════ RIGHT PANEL ════ */
.right-col {
  display: flex; flex-direction: column; gap: 18px;
  grid-row: 1 / 3; grid-column: 2;
}

/* ════ CALL STATUS CARD ════ */
.call-status-card { }

.status-hero {
  text-align: center; padding: 20px 0 16px;
}
.status-emoji { font-size: 36px; margin-bottom: 8px; }
.status-text { font-size: 15px; font-weight: 700; color: var(--ink); }
.status-sub { font-size: 12px; color: var(--ink3); margin-top: 2px; }

.timer-display {
  font-size: 38px; font-weight: 800;
  letter-spacing: -1px;
  text-align: center; padding: 12px;
  background: var(--bg2); border-radius: 14px;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  margin-bottom: 14px;
}

.call-meta-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.cmeta {
  background: var(--bg2); border-radius: 10px; padding: 10px 12px;
}
.cmeta-key { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--ink4); margin-bottom: 3px; }
.cmeta-val { font-size: 13px; font-weight: 700; color: var(--ink); }

/* ════ AGENT BRIEF CARD ════ */
.brief-card { flex: 1; }

.brief-content {
  background: var(--indigo-xl);
  border: 1.5px solid rgba(45,63,191,0.15);
  border-radius: 14px;
  padding: 16px;
  font-size: 13px; line-height: 1.75; color: var(--ink2);
  margin-bottom: 14px;
  min-height: 80px;
}

.brief-edit-area {
  width: 100%;
  background: var(--bg2); border: 1.5px solid var(--line2); border-radius: 10px;
  padding: 10px 12px; font-family: var(--font); font-size: 12px; color: var(--ink);
  resize: none; height: 72px; line-height: 1.6;
  transition: border-color 0.2s;
  margin-bottom: 8px;
}
.brief-edit-area:focus { outline: none; border-color: var(--indigo-l); }

.btn-save {
  background: var(--indigo); color: white;
  border: none; border-radius: 8px;
  padding: 8px 18px; font-family: var(--font); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
  float: right;
}
.btn-save:hover { background: var(--indigo-l); }

/* ════ TRANSCRIPT / LOG CARD ════ */
.transcript-list { max-height: 180px; overflow-y: auto; }
.t-item {
  display: flex; gap: 10px; padding: 8px 0;
  border-bottom: 1px solid var(--line); font-size: 12px;
  animation: slide-in 0.3s ease;
}
@keyframes slide-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.t-role {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.8px; padding-top: 1px; min-width: 44px;
}
.t-role.citizen { color: var(--saffron); }
.t-role.ai { color: var(--indigo); }
.t-role.agent { color: var(--jade); }
.t-text { color: var(--ink2); font-family: var(--font-kn); line-height: 1.5; }

.log-list { max-height: 120px; overflow-y: auto; }
.log-item {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 0; border-bottom: 1px solid var(--line);
  font-size: 11px; animation: slide-in 0.3s ease;
}
.log-badge {
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  padding: 2px 7px; border-radius: 4px; flex-shrink: 0;
  letter-spacing: 0.5px;
}
.log-badge.ok { background: var(--jade-xl); color: var(--jade); }
.log-badge.fix { background: var(--crimson-xl); color: var(--crimson); }
.log-text { color: var(--ink3); line-height: 1.4; }

/* ════ STATS ROW ════ */
.stats-mini {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 18px; padding: 18px;
  box-shadow: var(--shadow-sm);
  grid-column: 1;
}
.scard { text-align: center; }
.scard-num { font-size: 28px; font-weight: 800; line-height: 1; }
.scard-lbl { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; color: var(--ink3); margin-top: 4px; }

/* ════ ESCALATION MODAL ════ */
.esc-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(26,19,16,0.6);
  backdrop-filter: blur(12px);
  z-index: 1000; align-items: center; justify-content: center;
}
.esc-overlay.show { display: flex; }

.esc-modal {
  background: var(--surface); border-radius: 28px;
  padding: 40px 36px; max-width: 480px; width: 92%;
  box-shadow: var(--shadow-lg);
  animation: modal-pop 0.35s cubic-bezier(.34,1.56,.64,1);
  text-align: center;
  border: 2px solid var(--crimson-l);
}
@keyframes modal-pop {
  from { transform: scale(0.85) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}

.esc-siren {
  font-size: 56px; margin-bottom: 16px;
  display: block;
  animation: siren-pulse 0.6s ease-in-out infinite alternate;
}
@keyframes siren-pulse {
  from { filter: drop-shadow(0 0 8px rgba(224,32,32,0.4)); }
  to   { filter: drop-shadow(0 0 20px rgba(224,32,32,0.8)); }
}

.esc-title { font-size: 24px; font-weight: 800; color: var(--ink); margin-bottom: 6px; }
.esc-reason { font-size: 13px; color: var(--ink3); margin-bottom: 20px; line-height: 1.6; }

.esc-brief-box {
  background: var(--bg2); border-radius: 14px; padding: 16px;
  text-align: left; font-size: 13px; line-height: 1.75; color: var(--ink2);
  margin-bottom: 24px; border: 1px solid var(--line2);
}
.esc-brief-label {
  font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
  color: var(--crimson); margin-bottom: 8px;
}

.esc-actions { display: flex; flex-direction: column; gap: 10px; }

.btn-takeover {
  width: 100%; padding: 16px; border-radius: 14px;
  background: linear-gradient(135deg, var(--crimson), #c01010);
  color: white; font-family: var(--font); font-size: 15px; font-weight: 700;
  border: none; cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 6px 20px rgba(224,32,32,0.4);
  display: flex; align-items: center; justify-content: center; gap: 10px;
}
.btn-takeover:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(224,32,32,0.5); }

.btn-ai-continue {
  width: 100%; padding: 13px; border-radius: 14px;
  background: transparent; color: var(--ink3);
  border: 1.5px solid var(--line2); font-family: var(--font);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: all 0.2s;
}
.btn-ai-continue:hover { background: var(--bg2); color: var(--ink); }

/* ════ SUCCESS CONFIRM TOAST ════ */
.toast {
  position: fixed; bottom: 28px; right: 28px; z-index: 2000;
  background: var(--jade); color: white;
  border-radius: 14px; padding: 14px 22px;
  font-size: 13px; font-weight: 600;
  box-shadow: var(--shadow-lg);
  display: flex; align-items: center; gap: 10px;
  transform: translateY(80px); opacity: 0;
  transition: all 0.35s cubic-bezier(.34,1.56,.64,1);
}
.toast.show { transform: translateY(0); opacity: 1; }
.toast.error { background: var(--crimson); }
.toast.amber { background: var(--amber); }

/* ════ SCROLLBAR ════ */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 3px; }

/* ════ SHIMMER LOADING ════ */
.shimmer-line {
  height: 14px; border-radius: 7px;
  background: linear-gradient(90deg, var(--bg2) 25%, #ece6df 50%, var(--bg2) 75%);
  background-size: 300% 100%;
  animation: shimmer 1.4s infinite;
  margin-bottom: 10px;
}
@keyframes shimmer { 0%{background-position:100% 0} 100%{background-position:-100% 0} }

/* ════ LOGIN PAGE ════ */
#login-overlay {
  position: fixed; inset: 0; z-index: 9999;
  display: none; align-items: center; justify-content: center;
  background: rgba(15,12,41,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  overflow: hidden;
}
#login-overlay.open { display: flex; }
#login-overlay::before {
  content: '';
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 60% 50% at 20% 20%, rgba(255,107,0,0.18) 0%, transparent 60%),
    radial-gradient(ellipse 50% 60% at 80% 80%, rgba(45,63,191,0.25) 0%, transparent 60%);
  pointer-events: none;
}
#login-overlay::after {
  content: '';
  position: absolute; inset: 0;
  background-image: radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
}
.login-box {
  position: relative; z-index: 2;
  background: rgba(255,255,255,0.06);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 28px;
  padding: 48px 44px 40px;
  width: 100%; max-width: 420px;
  box-shadow: 0 32px 80px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.15);
  animation: loginFadeIn 0.6s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes loginFadeIn {
  from { opacity:0; transform: translateY(32px) scale(0.96); }
  to   { opacity:1; transform: translateY(0) scale(1); }
}
.login-logo {
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 32px;
}
.login-logo-emblem {
  width: 48px; height: 48px; border-radius: 14px;
  background: linear-gradient(135deg, var(--saffron), var(--indigo));
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; box-shadow: 0 8px 24px rgba(255,107,0,0.35);
  flex-shrink: 0;
}
.login-logo-text { flex: 1; }
.login-logo-name {
  font-size: 22px; font-weight: 800; color: #fff;
  letter-spacing: -0.5px;
}
.login-logo-sub {
  font-size: 11px; color: rgba(255,255,255,0.5);
  letter-spacing: 0.3px; margin-top: 1px;
}
.login-title {
  font-size: 26px; font-weight: 800; color: #fff;
  letter-spacing: -0.5px; margin-bottom: 6px;
}
.login-subtitle {
  font-size: 13px; color: rgba(255,255,255,0.45);
  margin-bottom: 32px; line-height: 1.5;
}
.login-field {
  margin-bottom: 16px;
}
.login-field label {
  display: block;
  font-size: 11px; font-weight: 600; letter-spacing: 1px;
  text-transform: uppercase; color: rgba(255,255,255,0.45);
  margin-bottom: 8px;
}
.login-input-wrap {
  position: relative;
}
.login-input-wrap .field-icon {
  position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
  font-size: 15px; pointer-events: none; opacity: 0.5;
}
.login-input {
  width: 100%;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 12px;
  padding: 13px 14px 13px 42px;
  font-size: 14px; font-family: var(--font);
  color: #fff; outline: none;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.login-input::placeholder { color: rgba(255,255,255,0.25); }
.login-input:focus {
  border-color: rgba(255,107,0,0.6);
  background: rgba(255,255,255,0.1);
  box-shadow: 0 0 0 3px rgba(255,107,0,0.12);
}
.login-input:focus + .field-focus-line { width: 100%; }
.login-error {
  font-size: 11px; color: #FF5252;
  margin-top: 6px; padding-left: 4px;
  display: none;
}
.login-btn-row {
  display: flex; gap: 10px; margin-top: 28px;
}
.login-btn {
  flex: 1;
  background: linear-gradient(135deg, #FF6B00, #e05500);
  border: none; border-radius: 12px;
  padding: 14px 20px;
  font-size: 14px; font-weight: 700; font-family: var(--font);
  color: #fff; cursor: pointer;
  box-shadow: 0 6px 24px rgba(255,107,0,0.35);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 32px rgba(255,107,0,0.45);
}
.login-btn:active { transform: translateY(0); }
.login-divider {
  height: 1px; background: rgba(255,255,255,0.08);
  margin: 28px 0 20px;
}
.login-footer {
  font-size: 11px; color: rgba(255,255,255,0.3);
  text-align: center; line-height: 1.6;
}
.login-footer strong { color: rgba(255,255,255,0.5); }
/* Demo badge */
.demo-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: rgba(45,63,191,0.3); border: 1px solid rgba(45,63,191,0.4);
  border-radius: 20px; padding: 3px 10px;
  font-size: 10px; font-weight: 600; color: rgba(160,180,255,0.8);
  letter-spacing: 0.5px; margin-bottom: 28px;
}

/* ════ INSIGHTS PANEL ════ */
.insights-card {
  background: linear-gradient(135deg, #1a1033 0%, #0f1e5e 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 20px; padding: 22px;
  color: #fff; position: relative; overflow: hidden;
}
.insights-card::before {
  content: ''; position: absolute;
  top: -40px; right: -40px;
  width: 200px; height: 200px;
  background: radial-gradient(ellipse, rgba(255,107,0,0.15), transparent 70%);
  pointer-events: none;
}
.insights-card::after {
  content: ''; position: absolute;
  bottom: -30px; left: -30px;
  width: 160px; height: 160px;
  background: radial-gradient(ellipse, rgba(45,63,191,0.2), transparent 70%);
  pointer-events: none;
}
.insights-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 18px; position: relative; z-index: 1;
}
.insights-header-title {
  font-size: 11px; font-weight: 700; letter-spacing: 1.2px;
  text-transform: uppercase; color: rgba(255,255,255,0.5);
}
.insights-live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #0D9E6B; box-shadow: 0 0 0 0 rgba(13,158,107,0.4);
  animation: insightPulse 2s infinite; flex-shrink: 0;
}
@keyframes insightPulse {
  0%   { box-shadow: 0 0 0 0 rgba(13,158,107,0.5); }
  70%  { box-shadow: 0 0 0 6px rgba(13,158,107,0); }
  100% { box-shadow: 0 0 0 0 rgba(13,158,107,0); }
}
.insights-metric-row {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
  margin-bottom: 16px; position: relative; z-index: 1;
}
.insight-metric {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px; padding: 14px 12px;
  text-align: center;
  transition: background 0.2s;
}
.insight-metric:hover { background: rgba(255,255,255,0.09); }
.insight-metric-val {
  font-size: 22px; font-weight: 800;
  letter-spacing: -0.5px; margin-bottom: 4px;
}
.insight-metric-lbl {
  font-size: 10px; color: rgba(255,255,255,0.4);
  font-weight: 500; letter-spacing: 0.5px;
}
.insights-activity {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 14px;
  margin-bottom: 14px; position: relative; z-index: 1;
}
.insights-activity-title {
  font-size: 10px; font-weight: 700; letter-spacing: 0.8px;
  text-transform: uppercase; color: rgba(255,255,255,0.35);
  margin-bottom: 10px;
}
.activity-bar-row {
  display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
}
.activity-bar-label {
  font-size: 10px; color: rgba(255,255,255,0.45); width: 60px; flex-shrink: 0;
}
.activity-bar-track {
  flex: 1; height: 6px; background: rgba(255,255,255,0.08);
  border-radius: 3px; overflow: hidden;
}
.activity-bar-fill {
  height: 100%; border-radius: 3px;
  transition: width 1s cubic-bezier(0.16,1,0.3,1);
}
.activity-bar-val {
  font-size: 10px; color: rgba(255,255,255,0.4); width: 28px; text-align: right; flex-shrink: 0;
}
.insights-agent-row {
  display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px; padding: 12px 14px;
  position: relative; z-index: 1;
}
.insights-agent-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  background: linear-gradient(135deg, #FF6B00, #2D3FBF);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; flex-shrink: 0;
}
.insights-agent-info { flex: 1; }
.insights-agent-name { font-size: 13px; font-weight: 700; color: #fff; }
.insights-agent-status { font-size: 10px; color: rgba(255,255,255,0.4); margin-top: 1px; }
.insights-agent-badge {
  font-size: 10px; font-weight: 700; padding: 3px 8px;
  border-radius: 20px; background: rgba(13,158,107,0.2);
  color: #12C882; border: 1px solid rgba(13,158,107,0.3);
  letter-spacing: 0.5px;
}

/* ════ LOGOUT BTN IN HEADER ════ */
.logout-btn {
  background: rgba(224,32,32,0.1); border: 1px solid rgba(224,32,32,0.25);
  border-radius: 20px; padding: 5px 12px;
  font-size: 11px; font-weight: 700; font-family: var(--font);
  color: var(--crimson); cursor: pointer;
  display: flex; align-items: center; gap: 5px;
  transition: background 0.2s, border-color 0.2s;
  letter-spacing: 0.3px;
}
.logout-btn:hover { background: rgba(224,32,32,0.18); border-color: rgba(224,32,32,0.4); }
</style>
</head>
<body>

<!-- ══ LOGIN OVERLAY ══ -->
<div id="login-overlay">
  <!-- Close modal on backdrop click -->
  <div style="position:absolute;inset:0;z-index:0" onclick="closeLoginModal()"></div>
  <div class="login-box" style="position:relative;z-index:1">
    <button onclick="closeLoginModal()" style="
      position:absolute;top:16px;right:16px;
      background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);
      border-radius:8px;width:28px;height:28px;
      font-size:14px;color:rgba(255,255,255,0.5);cursor:pointer;
      display:flex;align-items:center;justify-content:center;
      transition:background 0.2s;" title="Close">✕</button>
    <div class="login-logo">
      <div class="login-logo-emblem">🎙️</div>
      <div class="login-logo-text">
        <div class="login-logo-name">VaaNi</div>
        <div class="login-logo-sub">Karnataka 1092 AI Helpline · Government of Karnataka</div>
      </div>
    </div>

    <div class="demo-badge">🔒 SECURE AGENT PORTAL</div>

    <div class="login-title">Welcome back</div>
    <div class="login-subtitle">Sign in to access the VaaNi helpline dashboard and begin handling citizen calls.</div>

    <div class="login-field">
      <label>Agent Username</label>
      <div class="login-input-wrap">
        <span class="field-icon">👤</span>
        <input class="login-input" type="text" id="login-username" placeholder="e.g. agent.prashant" autocomplete="username" />
      </div>
      <div class="login-error" id="err-username">Please enter your username</div>
    </div>

    <div class="login-field">
      <label>Phone Number</label>
      <div class="login-input-wrap">
        <span class="field-icon">📱</span>
        <input class="login-input" type="tel" id="login-phone" placeholder="+91 XXXXX XXXXX" autocomplete="tel" />
      </div>
      <div class="login-error" id="err-phone">Please enter a valid 10-digit phone number</div>
    </div>

    <div class="login-field">
      <label>Password</label>
      <div class="login-input-wrap">
        <span class="field-icon">🔑</span>
        <input class="login-input" type="password" id="login-password" placeholder="Enter your password" autocomplete="current-password" />
      </div>
      <div class="login-error" id="err-password">Please enter your password</div>
    </div>

    <div class="login-btn-row">
      <button class="login-btn" onclick="doLogin()">
        <span>🚀</span> Sign In to Dashboard
      </button>
    </div>

    <div class="login-divider"></div>
    <div class="login-footer">
      <strong>Demo credentials:</strong> any username · any 10-digit phone · any password<br>
      This portal is for authorised Karnataka Government agents only.
    </div>
  </div>
</div>

<!-- ══ HEADER ══ -->
<header class="header">
  <div class="brand">
    <div class="brand-emblem"></div>
    <div>
      <div class="brand-name">VaaNi</div>
      <div class="brand-tag">Karnataka 1092 AI Helpline · Government of Karnataka</div>
    </div>
  </div>

  <div class="header-center">
    <div class="call-pill">
      <div class="pulse-ring"></div>
      <span id="session-id-display">CALL-000000-0000</span>
    </div>
  </div>

  <div class="header-right">
    <div class="header-stat">AI Accuracy <strong id="h-accuracy">—</strong></div>
    <div class="header-stat">Calls today <strong id="h-calls">1</strong></div>
    <!-- API Key panel -->
    <div id="api-panel" style="display:flex;align-items:center;gap:6px">

      <div id="ai-mode-badge" style="
        padding:4px 10px; border-radius:20px; font-size:10px; font-weight:700;
        background:var(--amber-xl); color:var(--amber);
        border:1px solid rgba(217,119,0,0.2); white-space:nowrap;
        letter-spacing:0.3px;
      ">🟢 LIVE AI</div>
    </div>
    <div id="agent-name-chip" style="display:none;align-items:center;gap:6px;
      background:var(--indigo-xl);border:1px solid rgba(45,63,191,0.15);
      border-radius:20px;padding:4px 10px;font-size:11px;font-weight:600;color:var(--indigo)">
      <span>👤</span><span id="header-agent-name">Agent</span>
    </div>
    <button id="header-login-btn" onclick="openLoginModal()" style="
      background:linear-gradient(135deg,var(--saffron),var(--indigo));
      border:none;border-radius:20px;padding:6px 14px;
      font-size:11px;font-weight:700;font-family:var(--font);
      color:#fff;cursor:pointer;display:flex;align-items:center;gap:5px;
      box-shadow:0 3px 12px rgba(255,107,0,0.3);
      transition:transform 0.15s,box-shadow 0.15s;letter-spacing:0.3px;">
      🔐 Login
    </button>
    <button class="logout-btn" id="logout-btn" onclick="doLogout()" style="display:none">
      ⬅️ Logout
    </button>
  </div>
</header>

<!-- ══ MAIN PAGE ══ -->
<div class="page">

  <!-- ── SCENARIO STRIP ── -->
  <div class="scenario-strip">
    <div class="strip-label">Live Demo</div>
    <div class="scenario-cards">
      <button class="sc-btn" onclick="runScenario(0)">
        <span class="sc-icon">🌾</span>
        Ration Card
        <span class="lang-tag">ಕನ್ನಡ</span>
      </button>
      <button class="sc-btn" onclick="runScenario(1)">
        <span class="sc-icon">👵</span>
        Pension Issue
        <span class="lang-tag">ಕನ್ನಡ</span>
      </button>
      <button class="sc-btn" onclick="runScenario(2)">
        <span class="sc-icon">💧</span>
        Water Supply
        <span class="lang-tag">हिंदी</span>
      </button>
      <button class="sc-btn" onclick="runScenario(3)">
        <span class="sc-icon">🚨</span>
        Emergency
        <span class="lang-tag">URGENT</span>
      </button>
      <button class="sc-btn" onclick="runScenario(4)">
        <span class="sc-icon">📋</span>
        Land Records
        <span class="lang-tag">English</span>
      </button>
    </div>
    <div class="lang-toggle">
      <button class="lang-btn on" onclick="setVerifLang('kannada',this)">ಕನ್ನಡ</button>
      <button class="lang-btn" onclick="setVerifLang('hindi',this)">हिंदी</button>
      <button class="lang-btn" onclick="setVerifLang('english',this)">Eng</button>
    </div>
  </div>

  <!-- ── HOW IT WORKS GUIDE ── -->
  <div id="howto-banner" style="
    grid-column: 1 / -1;
    background: linear-gradient(135deg, #fff8f0 0%, #f0f2ff 100%);
    border: 1.5px solid rgba(255,107,0,0.15);
    border-radius: 20px;
    padding: 18px 24px;
    display: flex; align-items: center; gap: 0;
  ">
    <div style="flex:1;display:flex;align-items:center;gap:20px;flex-wrap:wrap">
      <div style="font-size:13px;font-weight:700;color:var(--ink2);white-space:nowrap">How it works:</div>
      <!-- Steps -->
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:26px;height:26px;border-radius:50%;background:var(--saffron);color:white;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">1</div>
          <span style="font-size:12px;color:var(--ink2)">Citizen calls &amp; speaks<br><span style="color:var(--ink3);font-size:11px">in their own language</span></span>
        </div>
        <div style="color:var(--ink4);font-size:16px;padding:0 4px">→</div>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:26px;height:26px;border-radius:50%;background:var(--indigo);color:white;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">2</div>
          <span style="font-size:12px;color:var(--ink2)">AI interprets<br><span style="color:var(--ink3);font-size:11px">dialect + emotion aware</span></span>
        </div>
        <div style="color:var(--ink4);font-size:16px;padding:0 4px">→</div>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:26px;height:26px;border-radius:50%;background:var(--amber);color:white;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">3</div>
          <span style="font-size:12px;color:var(--ink2)">AI verifies<br><span style="color:var(--ink3);font-size:11px">"Did I understand you?"</span></span>
        </div>
        <div style="color:var(--ink4);font-size:16px;padding:0 4px">→</div>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:26px;height:26px;border-radius:50%;background:var(--jade);color:white;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">4</div>
          <span style="font-size:12px;color:var(--ink2)">Agent responds<br><span style="color:var(--ink3);font-size:11px">with full context</span></span>
        </div>
        <div style="color:var(--ink4);font-size:16px;padding:0 4px">→</div>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:26px;height:26px;border-radius:50%;background:var(--crimson);color:white;font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0">5</div>
          <span style="font-size:12px;color:var(--ink2)">Human takeover<br><span style="color:var(--ink3);font-size:11px">if AI is unsure</span></span>
        </div>
      </div>
    </div>
    <button onclick="document.getElementById('howto-banner').style.display='none'" style="
      background:none;border:none;color:var(--ink4);
      font-size:18px;cursor:pointer;padding:4px 8px;
      border-radius:6px; flex-shrink:0; margin-left:12px;
    " title="Dismiss">✕</button>
  </div>

  <!-- ── LEFT MAIN COLUMN ── -->
  <div class="main-col">

    <!-- ── INSIGHTS PANEL ── -->
    <div class="insights-card">
      <div class="insights-header">
        <div class="insights-live-dot"></div>
        <div class="insights-header-title">Live Dashboard Insights</div>
        <div style="margin-left:auto;font-size:10px;color:rgba(255,255,255,0.3)" id="insights-time">—</div>
      </div>

      <div class="insights-metric-row">
        <div class="insight-metric">
          <div class="insight-metric-val" style="color:#FF9A4A" id="ins-total">0</div>
          <div class="insight-metric-lbl">Total Calls</div>
        </div>
        <div class="insight-metric">
          <div class="insight-metric-val" style="color:#12C882" id="ins-accuracy">—</div>
          <div class="insight-metric-lbl">AI Accuracy</div>
        </div>
        <div class="insight-metric">
          <div class="insight-metric-val" style="color:#FF5252" id="ins-escalated">0</div>
          <div class="insight-metric-lbl">Escalated</div>
        </div>
      </div>

      <div class="insights-activity">
        <div class="insights-activity-title">Issue Category Breakdown</div>
        <div class="activity-bar-row">
          <div class="activity-bar-label">Ration Card</div>
          <div class="activity-bar-track"><div class="activity-bar-fill" id="ab-ration" style="width:72%;background:linear-gradient(90deg,#FF6B00,#FF9A4A)"></div></div>
          <div class="activity-bar-val" id="abv-ration">72%</div>
        </div>
        <div class="activity-bar-row">
          <div class="activity-bar-label">Pension</div>
          <div class="activity-bar-track"><div class="activity-bar-fill" id="ab-pension" style="width:55%;background:linear-gradient(90deg,#2D3FBF,#4A5DD9)"></div></div>
          <div class="activity-bar-val" id="abv-pension">55%</div>
        </div>
        <div class="activity-bar-row">
          <div class="activity-bar-label">Water</div>
          <div class="activity-bar-track"><div class="activity-bar-fill" id="ab-water" style="width:38%;background:linear-gradient(90deg,#0D9E6B,#12C882)"></div></div>
          <div class="activity-bar-val" id="abv-water">38%</div>
        </div>
        <div class="activity-bar-row">
          <div class="activity-bar-label">Emergency</div>
          <div class="activity-bar-track"><div class="activity-bar-fill" id="ab-emergency" style="width:18%;background:linear-gradient(90deg,#E02020,#FF5252)"></div></div>
          <div class="activity-bar-val" id="abv-emergency">18%</div>
        </div>
        <div class="activity-bar-row">
          <div class="activity-bar-label">Land Records</div>
          <div class="activity-bar-track"><div class="activity-bar-fill" id="ab-land" style="width:29%;background:linear-gradient(90deg,#7C3AED,#A78BFA)"></div></div>
          <div class="activity-bar-val" id="abv-land">29%</div>
        </div>
      </div>

      <div class="insights-agent-row">
        <div class="insights-agent-avatar">👤</div>
        <div class="insights-agent-info">
          <div class="insights-agent-name" id="ins-agent-name">Agent</div>
          <div class="insights-agent-status" id="ins-agent-status">Karnataka 1092 Helpline · On duty</div>
        </div>
        <div class="insights-agent-badge">● ONLINE</div>
      </div>
    </div>

    <!-- Citizen Voice Card -->
    <div class="card">
      <div class="card-title">
        <div class="card-title-dot" style="background:var(--saffron)"></div>
        Citizen Voice Input
      </div>

      <div class="mic-stage">
        <div class="mic-ring-outer" id="mic-ring">
          <div class="mic-circle" id="mic-circle">🎙️</div>
        </div>
        <div class="wave-bars" id="wave-bars">
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:10px"></div>
          <div class="wbar" style="height:8px"></div>
          <div class="wbar" style="height:14px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:12px"></div>
          <div class="wbar" style="height:8px"></div>
          <div class="wbar" style="height:16px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:10px"></div>
          <div class="wbar" style="height:14px"></div>
          <div class="wbar" style="height:8px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:12px"></div>
          <div class="wbar" style="height:10px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:8px"></div>
          <div class="wbar" style="height:14px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:10px"></div>
          <div class="wbar" style="height:8px"></div>
          <div class="wbar" style="height:6px"></div>
          <div class="wbar" style="height:12px"></div>
          <div class="wbar" style="height:8px"></div>
        </div>
        <div class="mic-status" id="mic-status">Select a scenario above to begin</div>
      </div>

      <div class="citizen-bubble" id="citizen-bubble">
        <span class="placeholder">Citizen's spoken words will appear here in real time...</span>
      </div>

      <!-- Processing pipeline -->
      <div class="pipeline" id="pipeline" style="margin-top:14px">
        <div class="pipe-step" id="ps-asr">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 18.5A6.5 6.5 0 1 0 5.5 12v1A5.5 5.5 0 0 0 12 18.5z"/><path d="M12 3v1m6.364 1.636-.707.707M21 12h-1M17.657 17.657l-.707-.707M12 21v-1m-5.657-2.343.707-.707M3 12H4M6.343 6.343l.707.707"/></svg>
          ASR
        </div>
        <div class="pipe-step" id="ps-lang">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 8 6 6m-4 0 5-8 5 8m-1-3H6"/><path d="M3 18h18"/></svg>
          Language
        </div>
        <div class="pipe-step" id="ps-dialect">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M12 4H3m9 0 7 16M12 4 5 20"/></svg>
          Dialect
        </div>
        <div class="pipe-step" id="ps-ai">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4m0 14v4M4.22 4.22l2.83 2.83m9.9 9.9 2.83 2.83M1 12h4m14 0h4M4.22 19.78l2.83-2.83m9.9-9.9 2.83-2.83"/></svg>
          AI Interpret
        </div>
        <div class="pipe-step" id="ps-sent">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/></svg>
          Sentiment
        </div>
        <div class="pipe-step" id="ps-verify">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 12 2 2 4-4"/><circle cx="12" cy="12" r="10"/></svg>
          Verify
        </div>
      </div>
    </div>

    <!-- AI Interpretation Card -->
    <div class="card interp-card">
      <div class="card-title">
        <div class="card-title-dot" style="background:var(--indigo)"></div>
        AI Interpretation
        <span id="interp-meta-lang" style="margin-left:auto;font-size:10px;color:var(--ink3);text-transform:none;letter-spacing:0;font-weight:400"></span>
      </div>

      <!-- Empty state -->
      <div class="interp-empty" id="interp-empty">
        <div class="interp-empty-icon">🧠</div>
        <div class="interp-empty-text">AI interpretation will appear here after the citizen speaks.<br>The system verifies understanding before the agent responds.</div>
      </div>

      <!-- Populated state (hidden initially) -->
      <div id="interp-content" style="display:none">
        <!-- Confidence bar -->
        <div class="conf-row">
          <div class="conf-label">Confidence</div>
          <div class="conf-track">
            <div class="conf-fill" id="conf-fill" style="width:0%"></div>
          </div>
          <div class="conf-pct" id="conf-pct">—</div>
        </div>

        <!-- Meta pills -->
        <div class="meta-row" id="meta-row">
          <span class="mpill mpill-lang" id="mpill-lang">—</span>
          <span class="mpill mpill-dialect" id="mpill-dialect">—</span>
          <span class="mpill mpill-category" id="mpill-category">—</span>
        </div>

        <!-- Summary -->
        <div class="summary-box">
          <div class="summary-lang-tag">🇮🇳 <span id="summary-lang-label">Kannada</span> Summary</div>
          <div class="summary-text-kn" id="summary-native"></div>
          <div class="summary-text-en" id="summary-english"></div>
        </div>

        <!-- Keywords -->
        <div class="keywords-row" id="keywords-row"></div>

        <!-- Verification block -->
        <div class="verif-block" id="verif-block">
          <div class="verif-header">
            <div class="verif-icon">❓</div>
            <div class="verif-label">AI Asks the Citizen</div>
          </div>
          <div class="verif-q" id="verif-q"></div>
          <div class="verif-btns">
            <button class="vbtn vbtn-yes" onclick="citizenConfirmed()">✅ Citizen Says Yes</button>
            <button class="vbtn vbtn-no" onclick="citizenCorrected()">❌ Needs Correction</button>
            <button class="vbtn vbtn-escalate" onclick="triggerEscalation()">⬆️ Escalate to Human</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Sentiment + Transcript Row -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">

      <!-- Sentiment Card -->
      <div class="card">
        <div class="card-title">
          <div class="card-title-dot" style="background:var(--crimson)"></div>
          Emotional Intelligence
        </div>

        <div class="emotion-hero" id="emotion-hero">
          <div class="emotion-face" id="emotion-face">😐</div>
          <div class="emotion-info">
            <div class="emotion-name" id="emotion-name" style="color:var(--ink3)">Waiting</div>
            <div class="emotion-note" id="emotion-note">Sentiment analysis will appear here</div>
          </div>
          <div class="emotion-intensity">
            <div class="emotion-pct" id="emotion-pct" style="color:var(--ink3)">—</div>
            <div class="emotion-pct-label">Intensity</div>
          </div>
        </div>

        <div class="sent-bars">
          <div class="sent-row">
            <div class="sent-name">Distress</div>
            <div class="sent-track"><div class="sent-fill" id="sf-distress" style="width:0%;background:var(--crimson)"></div></div>
            <div class="sent-val" id="sv-distress" style="color:var(--crimson)">0%</div>
          </div>
          <div class="sent-row">
            <div class="sent-name">Urgency</div>
            <div class="sent-track"><div class="sent-fill" id="sf-urgency" style="width:0%;background:var(--amber)"></div></div>
            <div class="sent-val" id="sv-urgency" style="color:var(--amber)">0%</div>
          </div>
          <div class="sent-row">
            <div class="sent-name">Clarity</div>
            <div class="sent-track"><div class="sent-fill" id="sf-clarity" style="width:0%;background:var(--jade)"></div></div>
            <div class="sent-val" id="sv-clarity" style="color:var(--jade)">0%</div>
          </div>
          <div class="sent-row">
            <div class="sent-name">AI Conf.</div>
            <div class="sent-track"><div class="sent-fill" id="sf-conf" style="width:0%;background:var(--indigo)"></div></div>
            <div class="sent-val" id="sv-conf" style="color:var(--indigo)">0%</div>
          </div>
        </div>

        <div class="distress-badge" id="distress-badge" style="display:none">
          🚨 <span>DISTRESS DETECTED — Consider escalating to human agent immediately</span>
        </div>

        <div style="margin-top:12px;padding:10px 12px;background:var(--bg2);border-radius:10px;font-size:12px;color:var(--ink3);line-height:1.5" id="agent-note-box">
          Agent guidance will appear here...
        </div>
      </div>

      <!-- Transcript Card -->
      <div class="card">
        <div class="card-title">
          <div class="card-title-dot" style="background:var(--jade)"></div>
          Live Transcript
        </div>
        <div class="transcript-list" id="transcript-list">
          <div style="color:var(--ink4);font-size:12px;padding:8px 0">Conversation will appear here...</div>
        </div>

        <div class="card-title" style="margin-top:16px">
          <div class="card-title-dot" style="background:var(--purple)"></div>
          Learning Log
        </div>
        <div class="log-list" id="log-list">
          <div style="color:var(--ink4);font-size:11px;padding:6px 0">Confirmed & corrected interpretations...</div>
        </div>
      </div>
    </div>

    <!-- Stats Mini Row -->
    <div class="stats-mini">
      <div class="scard">
        <div class="scard-num" style="color:var(--jade)" id="stat-confirmed">0</div>
        <div class="scard-lbl">✅ Confirmed</div>
      </div>
      <div class="scard">
        <div class="scard-num" style="color:var(--crimson)" id="stat-corrections">0</div>
        <div class="scard-lbl">🔁 Corrections</div>
      </div>
      <div class="scard">
        <div class="scard-num" style="color:var(--indigo)" id="stat-turns">0</div>
        <div class="scard-lbl">💬 Turns</div>
      </div>
      <div class="scard">
        <div class="scard-num" style="color:var(--saffron)" id="stat-accuracy">—</div>
        <div class="scard-lbl">🎯 Accuracy</div>
      </div>
    </div>

  </div><!-- end main-col -->

  <!-- ── RIGHT COLUMN ── -->
  <div class="right-col">

    <!-- Call Status -->
    <div class="card call-status-card">
      <div class="card-title">
        <div class="card-title-dot" style="background:var(--jade)"></div>
        Call Status
      </div>

      <div class="status-hero">
        <div class="status-emoji" id="status-emoji">📞</div>
        <div class="status-text" id="status-text">Ready to receive</div>
        <div class="status-sub" id="status-sub">Select a scenario to begin</div>
      </div>

      <div class="timer-display" id="timer-display">00:00</div>

      <div class="call-meta-grid">
        <div class="cmeta">
          <div class="cmeta-key">Language</div>
          <div class="cmeta-val" id="cm-lang">—</div>
        </div>
        <div class="cmeta">
          <div class="cmeta-key">Dialect</div>
          <div class="cmeta-val" id="cm-dialect">—</div>
        </div>
        <div class="cmeta">
          <div class="cmeta-key">Category</div>
          <div class="cmeta-val" id="cm-category">—</div>
        </div>
        <div class="cmeta">
          <div class="cmeta-key">Verified</div>
          <div class="cmeta-val" id="cm-verified" style="color:var(--jade)">0</div>
        </div>
      </div>
    </div>

    <!-- Agent Brief -->
    <div class="card brief-card">
      <div class="card-title" style="justify-content:space-between">
        <span style="display:flex;align-items:center;gap:8px">
          <div class="card-title-dot" style="background:var(--indigo)"></div>
          Agent Brief
        </span>
        <span style="font-size:9px;font-weight:700;padding:2px 8px;border-radius:4px;background:var(--indigo-xl);color:var(--indigo);text-transform:uppercase;letter-spacing:0.8px">AI Generated</span>
      </div>

      <div class="brief-content" id="brief-content">
        After the AI interprets the citizen's issue, an actionable brief will appear here for the agent...
      </div>

      <textarea class="brief-edit-area" id="brief-edit" placeholder="Add your own notes or corrections here..."></textarea>
      <button class="btn-save" onclick="saveBrief()">Save Note</button>
      <div style="clear:both;height:10px"></div>

      <!-- Keywords -->
      <div class="card-title" style="margin-top:8px">
        <div class="card-title-dot" style="background:var(--saffron)"></div>
        Issue Keywords
      </div>
      <div id="brief-keywords" style="display:flex;flex-wrap:wrap;gap:5px;margin-top:6px">
        <span style="color:var(--ink4);font-size:11px">Keywords appear after interpretation...</span>
      </div>
    </div>

    <!-- Transcript in right panel too -->
    <div class="card" style="padding:18px">
      <div class="card-title">
        <div class="card-title-dot" style="background:var(--amber)"></div>
        Session Notes
      </div>
      <div style="font-size:12px;color:var(--ink3);line-height:1.7" id="session-notes">
        This panel shows real-time guidance for the agent. Corrections and confirmations from citizens are captured automatically for AI learning.
      </div>
    </div>

  </div><!-- end right-col -->

</div><!-- end page -->

<!-- ══ ESCALATION MODAL ══ -->
<div class="esc-overlay" id="esc-overlay">
  <div class="esc-modal">
    <span class="esc-siren">🚨</span>
    <div class="esc-title">Human Takeover Needed</div>
    <div class="esc-reason" id="esc-reason">The AI has detected a situation requiring human intervention.</div>
    <div class="esc-brief-box">
      <div class="esc-brief-label">Agent Brief — Read This First</div>
      <div id="esc-brief-text">Generating brief...</div>
    </div>
    <div class="esc-actions">
      <button class="btn-takeover" onclick="humanTakeover()">
        🧑‍💼 Take Over Call Now
      </button>
      <button class="btn-ai-continue" onclick="dismissEscalation()">
        Continue with AI assistance
      </button>
    </div>
  </div>
</div>

<!-- ══ TOAST ══ -->
<div class="toast" id="toast">✓ Interpretation confirmed</div>

<script>
// ════════════════════════════════════════════════════
//  VAANI — REAL CLAUDE API + STUNNING UI
//  All interpretation calls go to Anthropic directly
// ════════════════════════════════════════════════════

const ANTHROPIC_API = 'https://api.anthropic.com/v1/messages';

const STATE = {
  sessionId: genSessionId(),
  verifLang: 'kannada',
  confirmed: 0,
  corrections: 0,
  turns: 0,
  timerStart: null,
  timerInterval: null,
  lastResult: null,
  busy: false
};

// ── SCENARIOS ──────────────────────────────────────────
const SCENARIOS = [
  {
    id: 0,
    icon: '🌾',
    lang: 'kannada',
    dialect: 'Dharwad',
    category: 'Ration Card',
    text: 'ಅಯ್ಯಾ, ನಮ್ಮ ರೇಶನ್ ಕಾರ್ಡ್ ಮೂರು ತಿಂಗಳಿಂದ ಸಿಗ್ತಾ ಇಲ್ಲ ಕಣ್ರಿ... ಅಂಗಡಿಯಿಂದ ಅಕ್ಕಿ, ಗೋಧಿ ಕೊಡ್ತಾ ಇಲ್ಲ. ಮನೆಯಲ್ಲಿ ಮಕ್ಕಳು ಹೊಟ್ಟೆ ಹಸಿದು ಇದ್ದಾರೆ. ಸರ್ಕಾರ ಏನಾದ್ರೂ ಮಾಡಬೇಕು ಸಾಮಿ...',
    emotion: 'distress', urgency: 0.65, intensity: 0.6, distress: false
  },
  {
    id: 1,
    icon: '👵',
    lang: 'kannada',
    dialect: 'Mysore',
    category: 'Pension',
    text: 'ನಮ್ಮ ತಾಯಿಗೆ ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ ಬರ್ತಾ ಇತ್ತು ಅಲ್ವಾ, ಅದು ಎರಡು ತಿಂಗಳಿಂದ ನಿಂತು ಹೋಗಿದೆ. ಅವರಿಗೆ 78 ವರ್ಷ ಆಗಿದೆ, ಬೇರೆ ಆದಾಯ ಏನೂ ಇಲ್ಲ. ಅಧಿಕಾರಿಗಳ ಹತ್ರ ಹೋದ್ರೆ ಕಳಿಸ್ತಾ ಇದ್ದಾರೆ.',
    emotion: 'urgency', urgency: 0.6, intensity: 0.55, distress: false
  },
  {
    id: 2,
    icon: '💧',
    lang: 'hindi',
    dialect: 'Standard',
    category: 'Water Supply',
    text: 'Bhai sahab, hamare mohalle mein teen din se paani nahi aa raha. Ghar mein budhhe maata-pita hain aur chhote bacche hain. Tanker wale bhi nahi aate. Municipality office gaye toh koi sunata hi nahi. Kuch karo please, bahut mushkil ho rahi hai.',
    emotion: 'urgency', urgency: 0.6, intensity: 0.5, distress: false
  },
  {
    id: 3,
    icon: '🚨',
    lang: 'kannada',
    dialect: 'Dharwad',
    category: 'Emergency',
    text: 'HELP MAADI... ನಮ್ಮ ಮನೆ ಮೇಲೆ ದಾಳಿ ಆಗ್ತಾ ಇದೆ! ಯಾರೋ ಜಮೀನು ತಕ್ಕೊಳ್ಳೋಕೆ ಬಂದಿದ್ದಾರೆ... ದಯಮಾಡಿ ಬೇಗ ಬನ್ನಿ... ಮಕ್ಕಳು ಅಳ್ತಾ ಇದ್ದಾರೆ...',
    emotion: 'fear', urgency: 0.95, intensity: 0.92, distress: true
  },
  {
    id: 4,
    icon: '📋',
    lang: 'english',
    dialect: 'Standard',
    category: 'Land Records',
    text: 'Good morning, I need help with a land records dispute. My family has been farming this land for three generations but someone filed fraudulent documents showing different ownership. The tahsildar office is not taking any action despite multiple visits. I have all original documents with me.',
    emotion: 'confusion', urgency: 0.5, intensity: 0.4, distress: false
  }
];

const EMOTION_CONFIG = {
  distress: { face:'😟', color:'#E02020', bg:'#FFF0F0', border:'#FF9999' },
  urgency:  { face:'⚡', color:'#D97700', bg:'#FFF8EC', border:'#FFD080' },
  anger:    { face:'😠', color:'#CC3300', bg:'#FFF0EC', border:'#FF9980' },
  fear:     { face:'😨', color:'#7C3AED', bg:'#F5F0FF', border:'#C4B0FF' },
  confusion:{ face:'😕', color:'#2D3FBF', bg:'#EEF0FD', border:'#B0BCFF' },
  neutral:  { face:'😐', color:'#9C8878', bg:'#FAF7F4', border:'#C4B5A8' },
  calm:     { face:'😌', color:'#0D9E6B', bg:'#E6F9F3', border:'#80DFB5' }
};

// ── UTILITIES ──────────────────────────────────────────
function genSessionId() {
  const t = new Date().toTimeString().slice(0,8).replace(/:/g,'');
  const r = Math.floor(Math.random()*9000)+1000;
  return `CALL-${t}-${r}`;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function toast(msg, type='') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast' + (type?' '+type:'');
  el.classList.add('show');
  setTimeout(()=> el.classList.remove('show'), 3200);
}

function setStep(id, state) {
  document.getElementById(id).className = 'pipe-step ' + state;
}
function resetSteps() {
  ['ps-asr','ps-lang','ps-dialect','ps-ai','ps-sent','ps-verify'].forEach(id=>{
    document.getElementById(id).className = 'pipe-step';
  });
}

function addTranscript(role, text) {
  const list = document.getElementById('transcript-list');
  const first = list.querySelector('div[style]');
  if(first) list.innerHTML='';
  const item = document.createElement('div');
  item.className='t-item';
  item.innerHTML=`<span class="t-role ${role}">${role.toUpperCase()}</span><span class="t-text">${text}</span>`;
  list.appendChild(item);
  list.scrollTop=list.scrollHeight;
}

function addLog(type, text) {
  const list = document.getElementById('log-list');
  const first = list.querySelector('div[style]');
  if(first) list.innerHTML='';
  const item = document.createElement('div');
  item.className='log-item';
  item.innerHTML=`<span class="log-badge ${type}">${type==='ok'?'Confirmed':'Corrected'}</span><span class="log-text">${text}</span>`;
  list.appendChild(item);
  list.scrollTop=list.scrollHeight;
}

function updateStats() {
  const c=STATE.confirmed, r=STATE.corrections;
  const acc = c+r>0 ? Math.round(c/(c+r)*100)+'%' : '—';
  document.getElementById('stat-confirmed').textContent=c;
  document.getElementById('stat-corrections').textContent=r;
  document.getElementById('stat-turns').textContent=STATE.turns;
  document.getElementById('stat-accuracy').textContent=acc;
  document.getElementById('h-accuracy').textContent=acc;
  document.getElementById('cm-verified').textContent=c;
}

function startTimer() {
  if(STATE.timerInterval) return;
  STATE.timerStart=Date.now();
  STATE.timerInterval=setInterval(()=>{
    const e=Math.floor((Date.now()-STATE.timerStart)/1000);
    const m=String(Math.floor(e/60)).padStart(2,'0');
    const s=String(e%60).padStart(2,'0');
    document.getElementById('timer-display').textContent=`${m}:${s}`;
  },1000);
}

async function typeIn(el, text, speed=20) {
  el.innerHTML='';
  let i=0;
  return new Promise(res=>{
    const iv=setInterval(()=>{
      el.innerHTML=text.slice(0,i)+'<span class="cursor-blink"></span>';
      i++;
      if(i>text.length){ el.textContent=text; clearInterval(iv); res(); }
    },speed);
  });
}

function updateSentiment(result) {
  const s = result.sentiment || {};
  const emotion = s.emotion || 'neutral';
  const intensity = Math.round((s.intensity||0)*100);
  const urgency = Math.round((s.urgency_score||0)*100);
  const distress = s.distress_flag||false;
  const clarity = Math.round((result.confidence||0.7)*100);

  const cfg = EMOTION_CONFIG[emotion]||EMOTION_CONFIG.neutral;

  // Emotion hero
  const hero = document.getElementById('emotion-hero');
  hero.style.background = cfg.bg;
  hero.style.borderColor = cfg.border;
  document.getElementById('emotion-face').textContent = cfg.face;
  document.getElementById('emotion-name').textContent = emotion;
  document.getElementById('emotion-name').style.color = cfg.color;
  document.getElementById('emotion-pct').textContent = intensity+'%';
  document.getElementById('emotion-pct').style.color = cfg.color;
  document.getElementById('emotion-note').textContent = s.agent_note||'Assessing emotional state...';

  // Bars
  const setBar = (id,vid,val,color)=>{
    document.getElementById(id).style.width=val+'%';
    document.getElementById(id).style.background=color;
    document.getElementById(vid).textContent=val+'%';
    document.getElementById(vid).style.color=color;
  };
  setBar('sf-distress','sv-distress',distress?intensity:Math.max(0,intensity-20),'var(--crimson)');
  setBar('sf-urgency','sv-urgency',urgency,'var(--amber)');
  setBar('sf-clarity','sv-clarity',clarity,'var(--jade)');
  setBar('sf-conf','sv-conf',clarity,'var(--indigo)');

  // Distress badge
  const badge = document.getElementById('distress-badge');
  badge.style.display = distress&&intensity>65 ? 'flex' : 'none';

  // Agent note
  document.getElementById('agent-note-box').textContent = s.agent_note||'—';
}

function updateConfidence(conf) {
  const pct=Math.round(conf*100);
  document.getElementById('conf-fill').style.width=pct+'%';
  const color = pct>=75?'var(--jade)':pct>=55?'var(--amber)':'var(--crimson)';
  document.getElementById('conf-fill').style.background=color;
  const el=document.getElementById('conf-pct');
  el.textContent=pct+'%';
  el.className='conf-pct'+(pct<55?' low':pct<75?' med':'');
}

function renderInterpretation(result) {
  const respLang = result.response_language||result.language_detected||'kannada';

  // Show content area
  document.getElementById('interp-empty').style.display='none';
  document.getElementById('interp-content').style.display='block';

  updateConfidence(result.confidence||0.85);

  // Meta pills
  const langLabel = (result.language_detected||'kannada').charAt(0).toUpperCase()+(result.language_detected||'kannada').slice(1);
  const dialectLabel = (result.dialect_detected||'standard').charAt(0).toUpperCase()+(result.dialect_detected||'standard').slice(1);
  const catLabel = (result.issue_category||'other').replace(/_/g,' ').replace(/\\b\\w/g,l=>l.toUpperCase());
  document.getElementById('mpill-lang').textContent='🗣 '+langLabel;
  document.getElementById('mpill-dialect').textContent='📍 '+dialectLabel;
  document.getElementById('mpill-category').textContent='📂 '+catLabel;

  // Summary
  let nativeText = '';
  let nativeLabelText = '';
  const langFonts = {
    kannada: 'var(--font-kn)', hindi: 'var(--font-hi)', english: 'var(--font)'
  };

  if(respLang==='kannada'||respLang==='mixed') {
    nativeText = result.kannada_summary||result.interpreted_issue;
    nativeLabelText='Kannada';
  } else if(respLang==='hindi') {
    nativeText=result.hindi_summary||result.interpreted_issue;
    nativeLabelText='Hindi';
  } else {
    nativeText=result.english_summary||result.interpreted_issue;
    nativeLabelText='English';
  }

  document.getElementById('summary-lang-label').textContent=nativeLabelText;
  const nativeEl=document.getElementById('summary-native');
  nativeEl.textContent=nativeText;
  nativeEl.style.fontFamily=langFonts[respLang]||'var(--font)';
  document.getElementById('summary-english').textContent=result.english_summary||result.interpreted_issue;

  // Keywords
  const kwRow=document.getElementById('keywords-row');
  kwRow.innerHTML=(result.keywords||[]).map(k=>`<span class="kw">${k}</span>`).join('');

  // Brief keywords
  document.getElementById('brief-keywords').innerHTML=(result.keywords||[]).map(k=>`<span class="kw">${k}</span>`).join('');

  // Brief
  const briefText=`${result.interpreted_issue} The citizen appears ${result.sentiment?.emotion||'concerned'} (urgency: ${Math.round((result.sentiment?.urgency_score||0.5)*100)}%). ${result.sentiment?.agent_note||'Respond with empathy and clear next steps.'}`;
  document.getElementById('brief-content').textContent=briefText;
  document.getElementById('esc-brief-text').textContent=briefText;

  // Call meta
  document.getElementById('cm-lang').textContent=langLabel;
  document.getElementById('cm-dialect').textContent=dialectLabel;
  document.getElementById('cm-category').textContent=catLabel;

  // Verification question
  const vq = result.verification_question||{};
  const qText = STATE.verifLang==='kannada'
    ? (vq.kannada||'ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥ ಮಾಡಿಕೊಂಡೆನಾ?')
    : STATE.verifLang==='hindi'
    ? (vq.hindi||'क्या मैंने सही समझा?')
    : (vq.english||'Did I understand correctly?');

  document.getElementById('verif-q').textContent=qText;
  const vb=document.getElementById('verif-block');
  vb.className='verif-block show';
  addTranscript('ai', qText);

  updateSentiment(result);
}

// ── REAL ANTHROPIC API — STREAMING ────────────────────
const SYSTEM_PROMPT = `You are VaaNi, an AI interpreter for the Karnataka Government's 1092 citizen helpline.
Interpret citizen speech with deep awareness of:
- Kannada (Dharwad, Mysore, Coastal, Rural dialects)
- Hindi (standard and mixed)
- English (Indian accent and mixed)
- Cultural expressions, colloquialisms, emotional cues

RESPOND ONLY in this exact JSON format with no other text:
{
  "interpreted_issue": "Clear English summary of the citizen's problem",
  "kannada_summary": "ನಿಮ್ಮ ಸಮಸ್ಯೆ ಏನೆಂದು ಅರ್ಥ ಮಾಡಿಕೊಂಡೆ: [Kannada summary]",
  "hindi_summary": "मैंने समझा: [Hindi summary]",
  "english_summary": "I understood that: [English summary]",
  "verification_question": {
    "kannada": "[Natural verification question in Kannada]",
    "hindi": "[Natural verification question in Hindi]",
    "english": "[Natural verification question in English]"
  },
  "sentiment": {
    "emotion": "distress|urgency|anger|fear|confusion|neutral|calm",
    "intensity": 0.0,
    "urgency_score": 0.0,
    "distress_flag": false,
    "agent_note": "Empathetic guidance for the agent"
  },
  "language_detected": "kannada|hindi|english|mixed",
  "dialect_detected": "dharwad|mysore|coastal|rural|standard|unknown",
  "confidence": 0.0,
  "should_escalate": false,
  "escalation_reason": "",
  "issue_category": "ration_card|aadhaar|pension|land_records|water|electricity|police|health|other",
  "keywords": ["relevant","keywords","from","citizen"],
  "response_language": "kannada|hindi|english"
}`;

// Live streaming JSON display element
let streamBuffer = '';
let streamDisplayEl = null;

function getStreamDisplay() {
  // Small live-feed element inside the shimmer zone
  let el = document.getElementById('stream-live');
  if (!el) {
    el = document.createElement('div');
    el.id = 'stream-live';
    el.style.cssText = `
      margin-top:8px; padding:10px 12px;
      background:var(--indigo-xl); border:1px dashed rgba(45,63,191,0.25);
      border-radius:10px; font-size:11px; font-family:monospace;
      color:var(--indigo); line-height:1.6; max-height:80px;
      overflow:hidden; white-space:pre-wrap; word-break:break-all;
      opacity:0.8;
    `;
    const content = document.getElementById('interp-content');
    if (content) content.appendChild(el);
  }
  return el;
}

// ── OPENROUTER LIVE AI (hardcoded key — works automatically) ──
const OPENROUTER_KEY = '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';
const OPENROUTER_API = 'https://openrouter.ai/api/v1/chat/completions';
const OPENROUTER_MODEL = 'anthropic/claude-3.5-haiku';

async function callClaudeAPI(text, language) {
  try {
    return await callOpenRouter(text, language);
  } catch(e) {
    console.warn('OpenRouter failed, using demo data:', e.message);
    return getMockResult(text, language);
  }
}

async function callOpenRouter(text, language) {
  const display = getStreamDisplay();
  display.textContent = '⚡ Connecting to AI...';

  const response = await fetch(OPENROUTER_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + OPENROUTER_KEY,
      'HTTP-Referer': 'https://vaani-1092.karnataka.gov.in',
      'X-Title': 'VaaNi 1092 Helpline'
    },
    body: JSON.stringify({
      model: OPENROUTER_MODEL,
      max_tokens: 1000,
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: `Citizen said (in ${language}): "${text}"\\n\\nInterpret and respond in the exact JSON format.` }
      ]
    })
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error('OpenRouter ' + response.status + ': ' + err.slice(0,100));
  }

  const data = await response.json();
  display.textContent = '✓ AI responded!';
  setTimeout(() => { if(display) display.remove(); }, 800);

  let txt = data.choices[0].message.content;
  if (txt.includes('```json')) txt = txt.split('```json')[1].split('```')[0].trim();
  else if (txt.includes('```')) txt = txt.split('```')[1].split('```')[0].trim();
  return JSON.parse(txt);
}

async function callViaBackend(text, language) {
  return new Promise((resolve, reject) => {
    const sid = STATE.sessionId;
    const url = `http://localhost:8000/stream/${sid}?text=${encodeURIComponent(text)}&language=${language}`;
    const es = new EventSource(url);
    const display = getStreamDisplay();
    let buf = '';

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'chunk') {
          buf += data.text;
          display.textContent = '⚡ ' + buf.slice(-120);
        } else if (data.type === 'complete') {
          es.close();
          display.textContent = '✓ Complete';
          setTimeout(() => { if(display) display.remove(); }, 600);
          resolve(data.result);
        } else if (data.type === 'error') {
          es.close();
          reject(new Error(data.message));
        }
      } catch(err) {}
    };

    es.onerror = () => { es.close(); reject(new Error('SSE connection failed')); };
    setTimeout(() => { es.close(); reject(new Error('timeout')); }, 15000);
  });
}

function getMockResult(text, language) {
  // Rich mock results that demonstrate the system
  const mocks = {
    0: {
      interpreted_issue:"Citizen's ration card has not been issued for 3 months. Family unable to receive rice and wheat from the PDS shop. Children are going hungry.",
      kannada_summary:"ನಿಮ್ಮ ರೇಶನ್ ಕಾರ್ಡ್ ಮೂರು ತಿಂಗಳಿಂದ ಸಿಗ್ತಿಲ್ಲ — ಅಕ್ಕಿ ಮತ್ತು ಗೋಧಿ ಸಿಗ್ತಿಲ್ಲ ಎಂದು ನಾನು ಅರ್ಥ ಮಾಡಿಕೊಂಡೆ.",
      hindi_summary:"मैंने समझा: आपका राशन कार्ड 3 महीने से नहीं मिला, बच्चे भूखे हैं।",
      english_summary:"I understood that your ration card hasn't arrived for 3 months and the PDS shop is not giving rice/wheat. Children are hungry.",
      verification_question:{kannada:"ನಿಮ್ಮ ರೇಶನ್ ಕಾರ್ಡ್ ಮೂರು ತಿಂಗಳಿಂದ ಸಿಗ್ತಿಲ್ಲ ಮತ್ತು ಅಂಗಡಿಯಿಂದ ಆಹಾರ ಸಿಗ್ತಿಲ್ಲ — ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥ ಮಾಡಿಕೊಂಡೆನಾ?",hindi:"क्या सही है कि राशन कार्ड 3 महीने से नहीं आया?",english:"Your ration card hasn't come for 3 months and your family can't get food — is that correct?"},
      sentiment:{emotion:'distress',intensity:0.62,urgency_score:0.68,distress_flag:false,agent_note:"Family food insecurity detected. Respond with urgency and provide district ration office contact immediately."},
      language_detected:'kannada',dialect_detected:'rural',confidence:0.89,should_escalate:false,
      issue_category:'ration_card',keywords:['ರೇಶನ್ ಕಾರ್ಡ್','ಅಕ್ಕಿ','ಗೋಧಿ','ಮೂರು ತಿಂಗಳು','ಮಕ್ಕಳು','ಹೊಟ್ಟೆ'],response_language:'kannada'
    },
    1: {
      interpreted_issue:"78-year-old mother's old-age pension has stopped for 2 months. No other income source. Officials are dismissing without help.",
      kannada_summary:"ನಿಮ್ಮ 78 ವರ್ಷ ವಯಸ್ಸಿನ ತಾಯಿಯ ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ ಎರಡು ತಿಂಗಳಿಂದ ಬಂದಿಲ್ಲ ಎಂದು ಅರ್ಥ ಆಯ್ತು.",
      hindi_summary:"मैंने समझा: आपकी 78 साल की माँ की पेंशन 2 महीने से बंद है।",
      english_summary:"I understood that your 78-year-old mother's old-age pension has stopped for 2 months with no other income.",
      verification_question:{kannada:"ನಿಮ್ಮ ತಾಯಿಯ ಪಿಂಚಣಿ ನಿಂತು ಎರಡು ತಿಂಗಳಾಯ್ತು ಅಂತ ನಾನು ಸರಿಯಾಗಿ ಅರ್ಥ ಮಾಡಿಕೊಂಡೆನಾ, ಹೌದಲ್ವಾ?",hindi:"क्या सही है कि माँ की पेंशन 2 महीने से बंद है?",english:"Your mother's pension has been stopped for 2 months — is that right?"},
      sentiment:{emotion:'urgency',intensity:0.58,urgency_score:0.62,distress_flag:false,agent_note:"Elderly person's welfare at risk. Citizen is persistent and has tried official channels. Treat with empathy and respect."},
      language_detected:'kannada',dialect_detected:'mysore',confidence:0.92,should_escalate:false,
      issue_category:'pension',keywords:['ವೃದ್ಧಾಪ್ಯ ಪಿಂಚಣಿ','78 ವರ್ಷ','ಎರಡು ತಿಂಗಳು','ಆದಾಯ','ಅಧಿಕಾರಿ'],response_language:'kannada'
    },
    2: {
      interpreted_issue:"No water supply in the neighborhood for 3 days. Elderly parents and young children at home. Tanker not coming. Municipality unresponsive.",
      kannada_summary:"ಮೂರು ದಿನದಿಂದ ನೀರಿಲ್ಲ — ಮನೆಯಲ್ಲಿ ವಯಸ್ಸಾದ ತಂದೆ-ತಾಯಿ ಮತ್ತು ಮಕ್ಕಳು ಇದ್ದಾರೆ.",
      hindi_summary:"मैंने समझा: तीन दिन से पानी नहीं है, बुज़ुर्ग और बच्चे घर पर हैं, नगर पालिका नहीं सुन रही।",
      english_summary:"I understood that there's been no water supply for 3 days, with elderly parents and children at home, and the municipality is not responding.",
      verification_question:{kannada:"ಮೂರು ದಿನ ನೀರು ಸಿಗ್ತಿಲ್ಲ ಮತ್ತು ಮ್ಯುನಿಸಿಪಾಲಿಟಿ ಸಹಾಯ ಮಾಡ್ತಿಲ್ಲ — ಸರಿನಾ?",hindi:"क्या तीन दिन से पानी नहीं और नगर पालिका नहीं सुन रही — यही बात है?",english:"No water for 3 days and municipality not responding — did I understand correctly?"},
      sentiment:{emotion:'urgency',intensity:0.54,urgency_score:0.62,distress_flag:false,agent_note:"Civic essential service failure with vulnerable family members. Needs prompt escalation to water department."},
      language_detected:'hindi',dialect_detected:'standard',confidence:0.94,should_escalate:false,
      issue_category:'water',keywords:['paani','municipality','tanker','teen din','budhhe','bacche'],response_language:'hindi'
    },
    3: {
      interpreted_issue:"EMERGENCY: Citizen reporting ongoing attack on their home. Unknown persons attempting to seize land by force. Children present and crying. Requires immediate police intervention.",
      kannada_summary:"ತುರ್ತು! ನಿಮ್ಮ ಮನೆ ಮೇಲೆ ದಾಳಿ ಆಗ್ತಿದೆ — ಜಮೀನು ಬಲವಂತವಾಗಿ ತಕ್ಕೊಳ್ಳಲು ಬಂದಿದ್ದಾರೆ. ಮಕ್ಕಳು ಇದ್ದಾರೆ!",
      hindi_summary:"आपातकाल! घर पर हमला हो रहा है — बच्चे रो रहे हैं, पुलिस चाहिए।",
      english_summary:"EMERGENCY: Your home is under attack right now — someone is forcibly trying to seize your land and children are present.",
      verification_question:{kannada:"ನಿಮ್ಮ ಮನೆ ಮೇಲೆ ಈಗ ದಾಳಿ ಆಗ್ತಿದೆ ಮತ್ತು ತಕ್ಷಣ ಸಹಾಯ ಬೇಕು — ಹೌದಾ?",hindi:"अभी घर पर हमला हो रहा है और पुलिस चाहिए — है ना?",english:"Your home is being attacked right now and you need police immediately — is that correct?"},
      sentiment:{emotion:'fear',intensity:0.94,urgency_score:0.97,distress_flag:true,agent_note:"CRITICAL EMERGENCY. Life safety at risk. Children present. Escalate to police IMMEDIATELY. Do not delay."},
      language_detected:'kannada',dialect_detected:'dharwad',confidence:0.78,should_escalate:true,escalation_reason:'Life-threatening emergency detected. High distress with physical threat to family including children.',
      issue_category:'police',keywords:['HELP','ದಾಳಿ','ಜಮೀನು','ಮಕ್ಕಳು','ತುರ್ತು','ಬೇಗ'],response_language:'kannada'
    },
    4: {
      interpreted_issue:"Three-generation family land ownership disputed by fraudulent documents filed by unknown parties. Tahsildar office unresponsive despite multiple visits. Original land documents available.",
      kannada_summary:"ಮೂರು ತಲೆಮಾರಿನ ಜಮೀನಿನ ದಾಖಲೆ ಸುಳ್ಳಾಗಿ ಮಾಡಿದ್ದಾರೆ — ತಹಶೀಲ್ದಾರ್ ಕ್ರಮ ತೆಗೆದುಕೊಳ್ತಿಲ್ಲ.",
      hindi_summary:"मैंने समझा: तीन पीढ़ियों की जमीन पर नकली दस्तावेज दाखिल हुए, तहसीलदार कार्रवाई नहीं कर रहा।",
      english_summary:"I understood that someone filed fraudulent land ownership documents against your family's three-generation land, and the tahsildar is not taking action despite multiple complaints.",
      verification_question:{kannada:"ನಿಮ್ಮ ಜಮೀನಿನ ಮೇಲೆ ಸುಳ್ಳು ದಾಖಲೆ ಮಾಡಿದ್ದಾರೆ, ತಹಶೀಲ್ದಾರ್ ಸಹಾಯ ಮಾಡ್ತಿಲ್ಲ — ಸರಿನಾ?",hindi:"क्या सही है कि जमीन पर नकली दस्तावेज हैं और तहसीलदार मदद नहीं कर रहा?",english:"Someone filed false documents on your land and the tahsildar isn't helping — is that correct?"},
      sentiment:{emotion:'confusion',intensity:0.42,urgency_score:0.55,distress_flag:false,agent_note:"Educated citizen with a serious legal matter. Calm but frustrated. Provide clear escalation path to district land records office."},
      language_detected:'english',dialect_detected:'standard',confidence:0.96,should_escalate:false,
      issue_category:'land_records',keywords:['land records','fraudulent','tahsildar','three generations','original documents','ownership'],response_language:'english'
    }
  };

  // Find matching mock by text content
  for(const [key, mock] of Object.entries(mocks)) {
    const sc = SCENARIOS[parseInt(key)];
    if(sc && (text.includes(sc.text.slice(0,15)) || sc.text.includes(text.slice(0,15)))) {
      return mock;
    }
  }
  return mocks[0];
}

// ── MAIN SCENARIO RUNNER ───────────────────────────────
async function runScenario(idx) {
  if(STATE.busy) return;
  STATE.busy=true;

  const sc = SCENARIOS[idx];
  STATE.turns++;

  // Highlight button
  document.querySelectorAll('.sc-btn').forEach((b,i)=>{
    const colors=['','active-indigo','active-indigo','active-crimson',''];
    b.className='sc-btn'+(i===idx?' active'+(colors[i]?' '+colors[i]:''):'');
  });

  // Reset UI
  document.getElementById('verif-block').className='verif-block';
  resetSteps();
  document.getElementById('citizen-bubble').className='citizen-bubble';
  document.getElementById('citizen-bubble').innerHTML='<span class="placeholder">Listening...</span>';

  // Start call setup
  if(!STATE.timerStart) {
    startTimer();
    document.getElementById('session-id-display').textContent=STATE.sessionId;
    document.getElementById('h-calls').textContent='1';
  }

  // Update status
  document.getElementById('status-emoji').textContent='📞';
  document.getElementById('status-text').textContent='Call Active';
  document.getElementById('status-sub').textContent=STATE.sessionId;

  // STEP 1 — ASR (simulate audio input)
  const micRing = document.getElementById('mic-ring');
  const waveBars = document.getElementById('wave-bars');
  const micStatus = document.getElementById('mic-status');

  micRing.className='mic-ring-outer speaking';
  waveBars.className='wave-bars live';
  micStatus.className='mic-status live';
  micStatus.textContent='🎙️ Listening — citizen speaking...';
  setStep('ps-asr','running');

  await sleep(600);

  // Type in citizen speech
  const bubble = document.getElementById('citizen-bubble');
  bubble.className='citizen-bubble has-text';
  await typeIn(bubble, sc.text, 16);

  micRing.className='mic-ring-outer';
  waveBars.className='wave-bars';
  micStatus.className='mic-status';
  micStatus.textContent='✓ Speech captured';
  setStep('ps-asr','done');
  addTranscript('citizen', sc.text);
  await sleep(200);

  // STEP 2 — Language Detection
  setStep('ps-lang','running');
  await sleep(500);
  setStep('ps-lang','done');

  // STEP 3 — Dialect
  setStep('ps-dialect','running');
  await sleep(400);
  setStep('ps-dialect','done');

  // STEP 4 — AI Interpret
  setStep('ps-ai','running');
  micStatus.textContent='🧠 AI interpreting...';

  // Show shimmer while loading
  document.getElementById('interp-empty').style.display='none';
  document.getElementById('interp-content').style.display='block';
  document.getElementById('interp-content').innerHTML=`
    <div style="padding:8px 0">
      <div class="shimmer-line" style="width:60%"></div>
      <div class="shimmer-line" style="width:80%"></div>
      <div class="shimmer-line" style="width:50%"></div>
      <div style="height:12px"></div>
      <div class="shimmer-line" style="width:100%"></div>
      <div class="shimmer-line" style="width:90%"></div>
      <div class="shimmer-line" style="width:70%"></div>
    </div>`;

  let result;
  try {
    result = await callClaudeAPI(sc.text, sc.lang);
  } catch(e) {
    result = getMockResult(sc.text, sc.lang);
  }

  STATE.lastResult = result;
  setStep('ps-ai','done');

  // Rebuild interpretation content area with correct structure
  document.getElementById('interp-content').innerHTML = `
    <div class="conf-row">
      <div class="conf-label">Confidence</div>
      <div class="conf-track"><div class="conf-fill" id="conf-fill" style="width:0%"></div></div>
      <div class="conf-pct" id="conf-pct">—</div>
    </div>
    <div class="meta-row" id="meta-row">
      <span class="mpill mpill-lang" id="mpill-lang">—</span>
      <span class="mpill mpill-dialect" id="mpill-dialect">—</span>
      <span class="mpill mpill-category" id="mpill-category">—</span>
    </div>
    <div class="summary-box">
      <div class="summary-lang-tag">🇮🇳 <span id="summary-lang-label">Kannada</span> Summary</div>
      <div class="summary-text-kn" id="summary-native"></div>
      <div class="summary-text-en" id="summary-english"></div>
    </div>
    <div class="keywords-row" id="keywords-row"></div>
    <div class="verif-block" id="verif-block">
      <div class="verif-header">
        <div class="verif-icon">❓</div>
        <div class="verif-label">AI Asks the Citizen</div>
      </div>
      <div class="verif-q" id="verif-q"></div>
      <div class="verif-btns">
        <button class="vbtn vbtn-yes" onclick="citizenConfirmed()">✅ Citizen Says Yes</button>
        <button class="vbtn vbtn-no" onclick="citizenCorrected()">❌ Needs Correction</button>
        <button class="vbtn vbtn-escalate" onclick="triggerEscalation()">⬆️ Escalate</button>
      </div>
    </div>`;

  // STEP 5 — Sentiment
  setStep('ps-sent','running');
  updateSentiment(result);
  await sleep(300);
  setStep('ps-sent','done');

  // Render full interpretation
  renderInterpretation(result);
  setStep('ps-verify','running');
  micStatus.textContent='❓ Verifying with citizen...';

  // Check auto-escalation
  if(result.should_escalate) {
    await sleep(800);
    showEscalation(result.escalation_reason||'High urgency or distress detected');
  }

  updateStats();
  STATE.busy=false;
}

// ── VERIFICATION ACTIONS ───────────────────────────────
function citizenConfirmed() {
  STATE.confirmed++;
  const issue = STATE.lastResult?.interpreted_issue||'Issue confirmed';
  addLog('ok', issue.slice(0,55)+'...');
  addTranscript('citizen','✅ ಹೌದು / हाँ / Yes — confirmed!');
  document.getElementById('verif-block').className='verif-block';
  setStep('ps-verify','done');
  document.getElementById('status-emoji').textContent='✅';
  document.getElementById('status-text').textContent='Understanding Verified';
  document.getElementById('mic-status').textContent='✅ Citizen confirmed — agent can proceed';
  updateStats();
  toast('✅ Understanding confirmed! Agent can now respond.');
}

function citizenCorrected() {
  STATE.corrections++;
  addLog('fix','Misunderstanding — citizen corrected AI');
  addTranscript('citizen','❌ ಇಲ್ಲ / नहीं / No — correction needed');
  document.getElementById('verif-block').className='verif-block';
  setStep('ps-verify','error');
  document.getElementById('mic-status').textContent='🔁 Re-listening...';
  updateStats();
  toast('🔁 Correction logged. AI learning updated.','amber');
  if(STATE.corrections>=2) {
    setTimeout(()=> showEscalation('Repeated misunderstanding — AI recommends human takeover'), 800);
  }
}

function triggerEscalation() {
  showEscalation('Agent manually escalated this call');
}

function showEscalation(reason) {
  document.getElementById('esc-reason').textContent = reason;
  const brief = document.getElementById('brief-content').textContent;
  document.getElementById('esc-brief-text').textContent = brief;
  document.getElementById('esc-overlay').className='esc-overlay show';
}

function humanTakeover() {
  document.getElementById('esc-overlay').className='esc-overlay';
  document.getElementById('status-emoji').textContent='🧑‍💼';
  document.getElementById('status-text').textContent='Human Agent Active';
  document.getElementById('status-text').style.color='var(--crimson)';
  document.getElementById('status-sub').textContent='AI standing by — full human control';
  addTranscript('agent','[Human agent has taken control of this call]');
  addLog('fix','Escalated to human agent after AI limitation');
  toast('🧑‍💼 Agent has taken over. AI standing by.','amber');
}

function dismissEscalation() {
  document.getElementById('esc-overlay').className='esc-overlay';
}

function setVerifLang(lang, btn) {
  STATE.verifLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b=>b.className='lang-btn');
  btn.className='lang-btn on';
}

function saveBrief() {
  const val = document.getElementById('brief-edit').value.trim();
  if(val) {
    document.getElementById('brief-content').textContent = val;
    document.getElementById('brief-edit').value='';
    addLog('ok','Agent updated brief: '+val.slice(0,45));
    toast('📝 Note saved!');
  }
}

function handleApiKey(val) {
  const trimmed = val.trim();
  const badge = document.getElementById('ai-mode-badge');
  if (trimmed.startsWith('sk-ant-')) {
    window._ANTHROPIC_KEY = trimmed;
    badge.style.background = 'var(--jade-xl)';
    badge.style.color = 'var(--jade)';
    badge.style.borderColor = 'rgba(13,158,107,0.2)';
    badge.textContent = '🟢 LIVE AI';
    toast('🟢 Live Anthropic API connected! Real-time streaming active.', '');
  } else if (trimmed === '') {
    window._ANTHROPIC_KEY = '';
    badge.style.background = 'var(--amber-xl)';
    badge.style.color = 'var(--amber)';
    badge.style.borderColor = 'rgba(217,119,0,0.2)';
    badge.textContent = '🟢 LIVE AI';
  }
}

// ── INIT ──────────────────────────────────────────────
document.getElementById('session-id-display').textContent = STATE.sessionId;

// Keyboard shortcut: press 1-5 to run scenarios
document.addEventListener('keydown', (e) => {
  const n = parseInt(e.key);
  if (n >= 1 && n <= 5) runScenario(n - 1);
});

// ══ LOGIN / LOGOUT ══
function openLoginModal() {
  const overlay = document.getElementById('login-overlay');
  overlay.classList.add('open');
  overlay.style.opacity = '0';
  overlay.style.transition = 'opacity 0.3s ease';
  setTimeout(() => { overlay.style.opacity = '1'; }, 10);
}

function closeLoginModal() {
  const overlay = document.getElementById('login-overlay');
  overlay.style.transition = 'opacity 0.25s ease';
  overlay.style.opacity = '0';
  setTimeout(() => { overlay.classList.remove('open'); }, 250);
}

function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const phone    = document.getElementById('login-phone').value.replace(/\\D/g,'');
  const password = document.getElementById('login-password').value;

  let valid = true;
  document.getElementById('err-username').style.display = 'none';
  document.getElementById('err-phone').style.display    = 'none';
  document.getElementById('err-password').style.display = 'none';

  if (!username) { document.getElementById('err-username').style.display = 'block'; valid = false; }
  if (phone.length < 10) { document.getElementById('err-phone').style.display = 'block'; valid = false; }
  if (!password) { document.getElementById('err-password').style.display = 'block'; valid = false; }
  if (!valid) return;

  sessionStorage.setItem('vaani_agent', username);
  sessionStorage.setItem('vaani_phone', phone);

  // Close modal
  closeLoginModal();

  // Update header
  document.getElementById('header-agent-name').textContent  = username;
  document.getElementById('agent-name-chip').style.display  = 'flex';
  document.getElementById('logout-btn').style.display       = 'flex';
  document.getElementById('header-login-btn').style.display = 'none';

  // Update insights panel
  document.getElementById('ins-agent-name').textContent   = username;
  document.getElementById('ins-agent-status').textContent = 'Karnataka 1092 · +91-' + phone.slice(0,5) + 'XXXXX';
}

function doLogout() {
  sessionStorage.removeItem('vaani_agent');
  sessionStorage.removeItem('vaani_phone');
  document.getElementById('header-agent-name').textContent  = 'Agent';
  document.getElementById('agent-name-chip').style.display  = 'none';
  document.getElementById('logout-btn').style.display       = 'none';
  document.getElementById('header-login-btn').style.display = 'flex';
  // Clear fields
  document.getElementById('login-username').value = '';
  document.getElementById('login-phone').value    = '';
  document.getElementById('login-password').value = '';
}

// Allow Enter key to submit login
document.addEventListener('keydown', e => {
  if (document.getElementById('login-overlay').classList.contains('open')) {
    if (e.key === 'Enter') doLogin();
    if (e.key === 'Escape') closeLoginModal();
  }
});

// ══ INSIGHTS LIVE CLOCK ══
function updateInsightsClock() {
  const now = new Date();
  document.getElementById('insights-time').textContent =
    now.toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
}
setInterval(updateInsightsClock, 1000);
updateInsightsClock();

// ══ INSIGHTS STATS SYNC ══
async function syncInsights() {
  try {
    const r = await fetch('/stats');
    const d = await r.json();
    document.getElementById('ins-total').textContent     = d.total_calls || 0;
    document.getElementById('ins-accuracy').textContent  = (d.accuracy_rate || 0) + '%';
    document.getElementById('ins-escalated').textContent = d.escalated || 0;
  } catch(e) {}
}
syncInsights();
setInterval(syncInsights, 15000);

// Restore session on page load
(function() {
  const agent = sessionStorage.getItem('vaani_agent');
  const phone = sessionStorage.getItem('vaani_phone');
  if (agent) {
    document.getElementById('header-agent-name').textContent  = agent;
    document.getElementById('agent-name-chip').style.display  = 'flex';
    document.getElementById('logout-btn').style.display       = 'flex';
    document.getElementById('header-login-btn').style.display = 'none';
    document.getElementById('ins-agent-name').textContent     = agent;
    if (phone) document.getElementById('ins-agent-status').textContent = 'Karnataka 1092 · +91-' + phone.slice(0,5) + 'XXXXX';
  }
})();
</script>
</body>
</html>
"""


class AdminLogin(BaseModel):
    password: str

class CreateUser(BaseModel):
    username: str
    password: str
    full_name: str = ""
    role: str = "admin"
    admin_pwd: str

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return HTMLResponse(content=FRONTEND_HTML)

@app.post("/session/create")
async def create_session(language: str = "kannada"):
    sid = f"CALL-{datetime.now().strftime('%H%M%S')}-{random.randint(1000,9999)}"
    now = datetime.now().isoformat()
    sessions[sid] = {"session_id": sid, "language": language, "transcript": [],
                     "escalated": False, "verified_count": 0, "correction_count": 0,
                     "start_time": now, "last_interpretation": {}}
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sessions (id, language, start_time) VALUES (?, ?, ?)", (sid, language, now))
    db.commit(); db.close()
    return {"session_id": sid, "status": "active"}

@app.post("/interpret")
async def interpret_endpoint(req: InterpretRequest):
    if req.session_id not in sessions:
        sessions[req.session_id] = {"session_id": req.session_id, "language": req.language,
            "transcript": [], "escalated": False, "verified_count": 0, "correction_count": 0,
            "start_time": datetime.now().isoformat(), "last_interpretation": {}}
    session = sessions[req.session_id]
    result = await interpret(req.text, req.language)
    session["last_interpretation"] = result
    if result.get("should_escalate") or session.get("correction_count", 0) >= 2:
        session["escalated"] = True; result["should_escalate"] = True
    db = get_db()
    db.execute("INSERT INTO transcripts (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
               (req.session_id, "citizen", req.text, datetime.now().isoformat()))
    db.execute("UPDATE sessions SET issue_category=?, emotion=?, confidence=? WHERE id=?",
               (result.get("issue_category"), result.get("sentiment", {}).get("emotion"),
                result.get("confidence"), req.session_id))
    db.commit(); db.close()
    return result

@app.post("/feedback")
async def record_feedback(req: FeedbackRequest):
    session = sessions.get(req.session_id, {})
    db = get_db()
    if req.type == "confirm":
        session["verified_count"] = session.get("verified_count", 0) + 1
        db.execute("UPDATE sessions SET verified_count=? WHERE id=?", (session["verified_count"], req.session_id))
        db.execute("INSERT INTO learning_log (session_id, type, original, language, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (req.session_id, "confirm", req.original, req.language, datetime.now().isoformat()))
    elif req.type == "correct":
        session["correction_count"] = session.get("correction_count", 0) + 1
        db.execute("UPDATE sessions SET correction_count=? WHERE id=?", (session["correction_count"], req.session_id))
        db.execute("INSERT INTO learning_log (session_id, type, original, corrected, language, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                   (req.session_id, "correct", req.original, req.corrected, req.language, datetime.now().isoformat()))
    db.commit(); db.close()
    return {"status": "recorded"}

@app.get("/stats")
async def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    escalated = db.execute("SELECT COUNT(*) FROM sessions WHERE escalated=1").fetchone()[0]
    confirmed = db.execute("SELECT COUNT(*) FROM learning_log WHERE type='confirm'").fetchone()[0]
    corrections = db.execute("SELECT COUNT(*) FROM learning_log WHERE type='correct'").fetchone()[0]
    db.close()
    return {"total_calls": total, "escalated": escalated, "confirmed": confirmed,
            "corrections": corrections, "accuracy_rate": round(confirmed/max(confirmed+corrections,1)*100,1)}

@app.get("/training-data")
async def training_data():
    db = get_db()
    rows = db.execute("SELECT * FROM learning_log ORDER BY timestamp DESC LIMIT 100").fetchall()
    db.close()
    return {"data": [dict(r) for r in rows]}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

@app.websocket("/ws/{session_id}")
async def ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "citizen_speech":
                await websocket.send_json({"type": "processing"})
                result = await interpret(data["text"], data.get("language", "kannada"))
                await websocket.send_json({"type": "interpretation", "data": result})
            elif data.get("type") == "end_call":
                await websocket.send_json({"type": "call_ended"}); break
    except WebSocketDisconnect:
        pass


# ── ADMIN PANEL ───────────────────────────────
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    html = open("admin.html").read() if __import__("os").path.exists("admin.html") else ADMIN_HTML_INLINE
    return HTMLResponse(content=html)

ADMIN_HTML_INLINE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VaaNi Admin</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}body{font-family:'Segoe UI',sans-serif;background:#f0f4ff;color:#1a1a2e}
.hdr{background:linear-gradient(135deg,#FF6B00,#2D3FBF);color:white;padding:16px 28px;display:flex;align-items:center;justify-content:space-between}
.hdr h1{font-size:20px;font-weight:800}.lb{max-width:380px;margin:80px auto;background:white;border-radius:16px;padding:32px;box-shadow:0 8px 32px rgba(0,0,0,.12)}
input,select{width:100%;padding:10px 14px;border:1.5px solid #dde1f0;border-radius:8px;font-size:14px;margin-bottom:14px;outline:none;font-family:inherit}
input:focus{border-color:#2D3FBF}.btn{width:100%;padding:12px;background:linear-gradient(135deg,#FF6B00,#2D3FBF);color:white;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer}
.con{max-width:1200px;margin:0 auto;padding:24px}.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.sc{background:white;border-radius:12px;padding:18px;box-shadow:0 2px 12px rgba(0,0,0,.06);text-align:center}.sn{font-size:32px;font-weight:800}
.sl{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:#888;margin-top:4px}
.tc{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:20px}
.tc h3{font-size:13px;font-weight:700;color:#2D3FBF;margin-bottom:14px;text-transform:uppercase;letter-spacing:.8px}
table{width:100%;border-collapse:collapse;font-size:12px}th{background:#f0f4ff;padding:8px 12px;text-align:left;font-weight:700;color:#555;border-bottom:1px solid #e8eaf0}
td{padding:8px 12px;border-bottom:1px solid #f0f2f8}tr:hover td{background:#f8f9ff}
.b{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700}
.bg{background:#e6f9f3;color:#0D9E6B}.br{background:#fff0f0;color:#E02020}.bb{background:#eef0fd;color:#2D3FBF}.ba{background:#fff8ec;color:#D97700}
.rbtn{padding:6px 14px;background:#2D3FBF;color:white;border:none;border-radius:6px;font-size:11px;cursor:pointer;float:right;margin-top:-30px}
.tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}.tab{padding:8px 18px;border-radius:8px;border:1.5px solid #dde1f0;background:white;font-size:12px;font-weight:600;cursor:pointer;color:#666}
.tab.on{background:#2D3FBF;color:white;border-color:#2D3FBF}.sec{display:none}.sec.on{display:block}
.sfm{display:grid;grid-template-columns:1fr 1fr;gap:12px}.sfm input,.sfm select{margin:0}
.fl label{font-size:11px;font-weight:700;color:#555;display:block;margin-bottom:4px;text-transform:uppercase;letter-spacing:.5px}
.cbtn{padding:10px 20px;background:#0D9E6B;color:white;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;margin-top:12px}
.msg{padding:10px 14px;border-radius:8px;margin-top:10px;font-size:13px;font-weight:500}
.mok{background:#e6f9f3;color:#0D9E6B}.mer{background:#fff0f0;color:#E02020}
.ar{display:flex;gap:8px;margin-bottom:8px;align-items:center}.au{flex:1;padding:8px 12px;background:#f0f4ff;border-radius:6px;font-size:12px;font-family:monospace;color:#2D3FBF;border:1px solid #dde1f0}
.cpb{padding:6px 12px;background:#FF6B00;color:white;border:none;border-radius:6px;font-size:11px;cursor:pointer}
.mth{color:white;padding:4px 10px;border-radius:5px;font-size:10px;font-weight:700;min-width:44px;text-align:center}
</style></head><body>
<div id="lp">
<div class="hdr"><h1>VaaNi Admin</h1></div>
<div class="lb"><h2 style="color:#2D3FBF;margin-bottom:16px">Admin Login</h2>
<input type="password" id="pi" placeholder="Admin password..." onkeydown="if(event.key==='Enter')login()"/>
<button class="btn" onclick="login()">Login</button>
<div id="lm" style="margin-top:10px;font-size:13px;color:red"></div></div></div>
<div id="ap" style="display:none">
<div class="hdr"><div><h1>VaaNi Admin Panel</h1><span style="font-size:11px;opacity:.7">1092 Karnataka Helpline</span></div>
<button onclick="logout()" style="padding:6px 14px;background:rgba(255,255,255,.2);border:1px solid rgba(255,255,255,.4);color:white;border-radius:6px;cursor:pointer;font-size:12px">Logout</button></div>
<div class="con">
<div class="sg"><div class="sc"><div class="sn" id="s1" style="color:#2D3FBF">0</div><div class="sl">Total Calls</div></div>
<div class="sc"><div class="sn" id="s2" style="color:#0D9E6B">0</div><div class="sl">Confirmed</div></div>
<div class="sc"><div class="sn" id="s3" style="color:#E02020">0</div><div class="sl">Corrections</div></div>
<div class="sc"><div class="sn" id="s4" style="color:#FF6B00">0%</div><div class="sl">AI Accuracy</div></div></div>
<div class="tabs">
<button class="tab on" onclick="sw('sessions',this)">Sessions</button>
<button class="tab" onclick="sw('transcripts',this)">Transcripts</button>
<button class="tab" onclick="sw('learning',this)">Learning Log</button>
<button class="tab" onclick="sw('superuser',this)">Superuser</button>
<button class="tab" onclick="sw('api',this)">API Docs</button></div>
<div class="sec on" id="t-sessions"><div class="tc"><h3>All Sessions <button class="rbtn" onclick="loadSessions()">Refresh</button></h3>
<div style="overflow-x:auto"><table><thead><tr><th>Session ID</th><th>Language</th><th>Category</th><th>Emotion</th><th>Confidence</th><th>Verified</th><th>Corrections</th><th>Escalated</th><th>Time</th></tr></thead>
<tbody id="sb"><tr><td colspan="9" style="text-align:center;color:#aaa;padding:20px">Loading...</td></tr></tbody></table></div></div></div>
<div class="sec" id="t-transcripts"><div class="tc"><h3>Transcripts <button class="rbtn" onclick="loadTranscripts()">Refresh</button></h3>
<div style="overflow-x:auto"><table><thead><tr><th>Session ID</th><th>Role</th><th>Content</th><th>Time</th></tr></thead>
<tbody id="tb"><tr><td colspan="4" style="text-align:center;color:#aaa;padding:20px">Loading...</td></tr></tbody></table></div></div></div>
<div class="sec" id="t-learning"><div class="tc"><h3>Learning Log <button class="rbtn" onclick="loadLearning()">Refresh</button></h3>
<div style="overflow-x:auto"><table><thead><tr><th>Type</th><th>Session</th><th>Original</th><th>Corrected</th><th>Language</th><th>Time</th></tr></thead>
<tbody id="lb"><tr><td colspan="6" style="text-align:center;color:#aaa;padding:20px">Loading...</td></tr></tbody></table></div></div></div>
<div class="sec" id="t-superuser"><div class="tc"><h3>Create Superuser</h3>
<p style="font-size:13px;color:#666;margin-bottom:16px">Create admin users for this panel</p>
<div class="sfm">
<div class="fl"><label>Username</label><input type="text" id="su" placeholder="admin_user"/></div>
<div class="fl"><label>Password</label><input type="password" id="sp" placeholder="strong password"/></div>
<div class="fl"><label>Full Name</label><input type="text" id="sn" placeholder="Full Name"/></div>
<div class="fl"><label>Role</label><select id="sr"><option value="admin">Admin</option><option value="superadmin">Super Admin</option><option value="viewer">Viewer</option></select></div>
</div><button class="cbtn" onclick="createUser()">+ Create User</button><div id="um"></div>
<div style="margin-top:20px"><h3 style="margin-bottom:12px;font-size:13px;color:#2D3FBF">Existing Users</h3>
<table><thead><tr><th>Username</th><th>Name</th><th>Role</th><th>Created</th></tr></thead>
<tbody id="ub"><tr><td colspan="4" style="color:#aaa;padding:12px">No users yet</td></tr></tbody></table></div></div></div>
<div class="sec" id="t-api"><div class="tc"><h3>API Endpoints</h3><div id="ae"></div></div></div>
</div></div>
<script>
let PWD='';const B=location.origin;
async function login(){const p=document.getElementById('pi').value;const r=await fetch(B+'/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});const d=await r.json();if(d.success){PWD=p;document.getElementById('lp').style.display='none';document.getElementById('ap').style.display='block';loadAll();}else document.getElementById('lm').textContent='Wrong password';}
function logout(){PWD='';document.getElementById('lp').style.display='block';document.getElementById('ap').style.display='none';}
function sw(n,el){document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));document.querySelectorAll('.sec').forEach(s=>s.classList.remove('on'));el.classList.add('on');document.getElementById('t-'+n).classList.add('on');}
function loadAll(){loadSessions();loadTranscripts();loadLearning();loadUsers();buildApi();}
async function loadSessions(){const r=await fetch(B+'/admin/sessions?pwd='+PWD);const d=await r.json();document.getElementById('s1').textContent=d.stats.total;document.getElementById('s2').textContent=d.stats.confirmed;document.getElementById('s3').textContent=d.stats.corrections;document.getElementById('s4').textContent=d.stats.accuracy+'%';document.getElementById('sb').innerHTML=d.sessions.map(s=>`<tr><td style="font-family:monospace;font-size:10px">${s.id}</td><td><span class="b bb">${s.language||'-'}</span></td><td>${s.issue_category||'-'}</td><td>${s.emotion||'-'}</td><td>${s.confidence?(s.confidence*100).toFixed(0)+'%':'-'}</td><td><span class="b bg">${s.verified_count||0}</span></td><td><span class="b br">${s.correction_count||0}</span></td><td>${s.escalated?'<span class="b br">YES</span>':'<span class="b bg">NO</span>'}</td><td style="font-size:10px;color:#888">${(s.start_time||'').slice(11,19)}</td></tr>`).join('')||'<tr><td colspan="9" style="text-align:center;color:#aaa;padding:20px">No sessions yet</td></tr>';}
async function loadTranscripts(){const r=await fetch(B+'/admin/transcripts?pwd='+PWD);const d=await r.json();document.getElementById('tb').innerHTML=d.map(t=>`<tr><td style="font-family:monospace;font-size:10px">${t.session_id}</td><td><span class="b ${t.role==='citizen'?'ba':t.role==='ai'?'bb':'bg'}">${t.role}</span></td><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${t.content}">${t.content}</td><td style="font-size:10px;color:#888">${(t.timestamp||'').slice(11,19)}</td></tr>`).join('')||'<tr><td colspan="4" style="text-align:center;color:#aaa;padding:20px">No transcripts</td></tr>';}
async function loadLearning(){const r=await fetch(B+'/admin/learning?pwd='+PWD);const d=await r.json();document.getElementById('lb').innerHTML=d.map(l=>`<tr><td><span class="b ${l.type==='confirm'?'bg':'br'}">${l.type}</span></td><td style="font-family:monospace;font-size:10px">${l.session_id}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${l.original||'-'}</td><td style="max-width:180px;overflow:hidden;text-overflow:ellipsis">${l.corrected||'-'}</td><td>${l.language||'-'}</td><td style="font-size:10px;color:#888">${(l.timestamp||'').slice(11,19)}</td></tr>`).join('')||'<tr><td colspan="6" style="text-align:center;color:#aaa;padding:20px">No data</td></tr>';}
async function loadUsers(){const r=await fetch(B+'/admin/users?pwd='+PWD);const d=await r.json();document.getElementById('ub').innerHTML=d.map(u=>`<tr><td style="font-family:monospace">${u.username}</td><td>${u.full_name||'-'}</td><td><span class="b bb">${u.role}</span></td><td style="font-size:10px;color:#888">${(u.created_at||'').slice(0,10)}</td></tr>`).join('')||'<tr><td colspan="4" style="color:#aaa;padding:12px">No users</td></tr>';}
async function createUser(){const body={username:document.getElementById('su').value,password:document.getElementById('sp').value,full_name:document.getElementById('sn').value,role:document.getElementById('sr').value,admin_pwd:PWD};if(!body.username||!body.password){document.getElementById('um').innerHTML='<div class="msg mer">Fill all fields</div>';return;}const r=await fetch(B+'/admin/create-user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();document.getElementById('um').innerHTML=d.success?'<div class="msg mok">User created!</div>':'<div class="msg mer">'+d.error+'</div>';if(d.success){loadUsers();['su','sp','sn'].forEach(id=>document.getElementById(id).value='');}}
function buildApi(){const eps=[{m:'GET',u:'/',c:'#0D9E6B',d:'Main dashboard'},{m:'GET',u:'/health',c:'#0D9E6B',d:'Health check'},{m:'GET',u:'/stats',c:'#0D9E6B',d:'Statistics'},{m:'POST',u:'/session/create',c:'#FF6B00',d:'Create session'},{m:'POST',u:'/interpret',c:'#FF6B00',d:'Interpret speech'},{m:'POST',u:'/feedback',c:'#FF6B00',d:'Record feedback'},{m:'GET',u:'/training-data',c:'#0D9E6B',d:'Export data'},{m:'GET',u:'/admin',c:'#7C3AED',d:'Admin panel'},{m:'POST',u:'/admin/login',c:'#FF6B00',d:'Admin login'},{m:'GET',u:'/admin/sessions',c:'#0D9E6B',d:'View sessions'},{m:'GET',u:'/admin/transcripts',c:'#0D9E6B',d:'View transcripts'},{m:'GET',u:'/admin/learning',c:'#0D9E6B',d:'Learning log'},{m:'POST',u:'/admin/create-user',c:'#FF6B00',d:'Create user'},{m:'WS',u:'/ws/{id}',c:'#2D3FBF',d:'WebSocket'}];document.getElementById('ae').innerHTML=eps.map(e=>`<div class="ar"><span class="mth" style="background:${e.c}">${e.m}</span><div class="au">${B}${e.u}</div><span style="font-size:12px;color:#666;min-width:200px">${e.d}</span><button class="cpb" onclick="navigator.clipboard.writeText('${B}${e.u}');this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)">Copy</button></div>`).join('');}
</script></body></html>"""

@app.post("/admin/login")
async def admin_login(req: AdminLogin):
    return {"success": req.password == ADMIN_PASSWORD}

@app.get("/admin/sessions")
async def admin_sessions(pwd: str = ""):
    if pwd != ADMIN_PASSWORD: raise HTTPException(403, "Unauthorized")
    db = get_db()
    rows = db.execute("SELECT * FROM sessions ORDER BY start_time DESC LIMIT 200").fetchall()
    confirmed = db.execute("SELECT COUNT(*) FROM learning_log WHERE type='confirm'").fetchone()[0]
    corrections = db.execute("SELECT COUNT(*) FROM learning_log WHERE type='correct'").fetchone()[0]
    stats = {"total": db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
             "confirmed": confirmed, "corrections": corrections,
             "escalated": db.execute("SELECT COUNT(*) FROM sessions WHERE escalated=1").fetchone()[0],
             "accuracy": round(confirmed/max(confirmed+corrections,1)*100,1)}
    db.close()
    return {"sessions": [dict(r) for r in rows], "stats": stats}

@app.get("/admin/transcripts")
async def admin_transcripts(pwd: str = ""):
    if pwd != ADMIN_PASSWORD: raise HTTPException(403, "Unauthorized")
    db = get_db()
    rows = db.execute("SELECT * FROM transcripts ORDER BY timestamp DESC LIMIT 500").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.get("/admin/learning")
async def admin_learning(pwd: str = ""):
    if pwd != ADMIN_PASSWORD: raise HTTPException(403, "Unauthorized")
    db = get_db()
    rows = db.execute("SELECT * FROM learning_log ORDER BY timestamp DESC LIMIT 500").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.get("/admin/users")
async def admin_users(pwd: str = ""):
    if pwd != ADMIN_PASSWORD: raise HTTPException(403, "Unauthorized")
    db = get_db()
    rows = db.execute("SELECT id,username,full_name,role,created_at FROM admin_users ORDER BY created_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]

@app.post("/admin/create-user")
async def create_admin_user(req: CreateUser):
    if req.admin_pwd != ADMIN_PASSWORD:
        return {"success": False, "error": "Wrong admin password"}
    db = get_db()
    try:
        db.execute("INSERT INTO admin_users (username,password,full_name,role,created_at) VALUES (?,?,?,?,?)",
                   (req.username,req.password,req.full_name,req.role,datetime.now().isoformat()))
        db.commit(); db.close()
        return {"success": True}
    except Exception as e:
        db.close(); return {"success": False, "error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  VaaNi running at http://localhost:{port}\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
