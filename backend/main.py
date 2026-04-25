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
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    try:
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except:
        return HTMLResponse("<h1>VaaNi API v2.0 Running ✅</h1>")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n  VaaNi running at http://localhost:{port}\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
