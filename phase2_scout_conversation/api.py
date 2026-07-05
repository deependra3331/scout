from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import sqlite3
from datetime import datetime
from phase2_scout_conversation.llm import chat_with_scout, extract_pact_intent, generate_drift_nudge

router = APIRouter(prefix="/api/phase2")
DB_PATH = "scout.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API Models ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatReq(BaseModel):
    messages: List[ChatMessage]

class DriftReq(BaseModel):
    genre: str

# --- API Endpoints ---
@router.post("/chat")
def handle_chat(req: ChatReq):
    # 1. Check if the conversation has reached a pact intent
    # We send the history to the intent extractor
    history_dicts = [{"role": m.role, "content": m.content} for m in req.messages]
    
    intent = extract_pact_intent(history_dicts)
    pact_created = False
    
    if intent and intent.get("is_ready") and intent.get("target_genre_or_artist"):
        # The user has committed! Save to DB.
        conn = get_db_connection()
        c = conn.cursor()
        
        # Clear old pacts
        c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
        
        # Insert new pact
        log_text = "\n".join([f"{m.role}: {m.content}" for m in req.messages])
        c.execute("""
            INSERT INTO exploration_pacts 
            (user_id, raw_conversation_log, target_genre_or_artist, breadth, intensity, user_motivation, window_days, target_share, status)
            VALUES (1, ?, ?, ?, ?, ?, 21, 0.3, 'active')
        """, (
            log_text, 
            intent.get("target_genre_or_artist"), 
            intent.get("breadth", "broad"), 
            intent.get("intensity", "casual"), 
            intent.get("user_motivation", "Exploration")
        ))
        conn.commit()
        conn.close()
        pact_created = True
        
        # Have Scout acknowledge the pact creation
        scout_response = f"Pact locked in! We're officially exploring {intent.get('target_genre_or_artist')}. I'll make sure it surfaces across your feeds. Let's do this!"
    else:
        # 2. Normal conversational response
        scout_response = chat_with_scout(history_dicts)
        
    return {
        "reply": scout_response,
        "pact_created": pact_created,
        "intent": intent if pact_created else None
    }

@router.post("/simulate_drift")
def simulate_drift(req: DriftReq):
    """
    Simulates the user rapidly playing their baseline genre instead of their pact.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check for active pact
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 AND status = 'active' ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    conn.close()
    
    if not pact:
        return {"nudge": "No active pact to drift from!"}
        
    target = pact['target_genre_or_artist']
    
    # Generate the proactive nudge using LLM
    nudge = generate_drift_nudge(target, req.genre)
    
    return {"nudge": nudge}
