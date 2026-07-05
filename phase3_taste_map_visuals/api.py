from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3
import os
from groq import Groq

router = APIRouter(prefix="/api/phase3")
DB_PATH = "scout.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class RecapResponse(BaseModel):
    story: str

@router.get("/taste_map")
def get_taste_map():
    """
    Returns the node graph data for the Taste Map UI.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Get Baseline Tastes (Claimed Territories)
    c.execute("SELECT genre FROM user_baseline_tastes WHERE user_id = 1")
    familiar = [row['genre'] for row in c.fetchall()]
    
    # Get Active Pact (Active Expedition)
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 AND status = 'active' ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    
    # Get all distinct genres from catalog
    c.execute("SELECT DISTINCT genre FROM tracks")
    all_genres = [row['genre'] for row in c.fetchall()]
    conn.close()
    
    nodes = []
    for g in all_genres:
        state = "fog" # Default unexplored
        if g in familiar:
            state = "familiar"
        elif pact and pact['target_genre_or_artist'] == g:
            state = "active_pact"
            
        nodes.append({
            "id": g,
            "label": g,
            "state": state
        })
        
    return {"nodes": nodes}

@router.post("/generate_recap", response_model=RecapResponse)
def generate_recap():
    """
    Simulates the end of a pact by generating a Wrapped-style recap story using the LLM.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    conn.close()
    
    if not pact:
        return {"story": "You haven't completed any expeditions yet. Talk to Scout to start one!"}
        
    target = pact['target_genre_or_artist']
    motivation = pact['user_motivation']
    
    client = None
    try:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    except Exception:
        pass
        
    if not client:
        # Fallback if API key is not set
        return {"story": f"Your expedition into {target} is complete! You originally set out because '{motivation}'. The territory has been officially claimed on your Taste Map."}

    system_prompt = f"""
    You are generating a short "Spotify Wrapped" style recap story for a user's music exploration.
    The user completed an expedition into the genre/artist: "{target}".
    Their original motivation was: "{motivation}".
    Write a fun, punchy, slightly poetic paragraph (3 sentences max) summarizing their journey. 
    Use words like "territory", "claimed", or "expedition".
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=150,
        )
        return {"story": chat_completion.choices[0].message.content}
    except Exception as e:
        return {"story": f"Error generating recap: {str(e)}"}
