from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import random

router = APIRouter(prefix="/api/phase1")
DB_PATH = "scout.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- API Models ---
class PactCreateReq(BaseModel):
    intent_raw: str

class TrackModel(BaseModel):
    id: int
    title: str
    artist: str
    genre: str
    cover_image_url: str
    is_pact_track: bool = False
    scout_explanation: Optional[str] = None

# --- API Endpoints ---
@router.post("/pacts")
def create_pact(req: PactCreateReq):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Mocking the LLM intent extraction for Phase 1
    intent = req.intent_raw.lower()
    target_genre = "Ambient" 
    all_genres = [
        "Pop", "Indie Pop", "J-pop", "K-pop", "Rock", "Indie Rock", "Hip Hop", "R&B", 
        "Electronic", "Ambient", "Jazz", "Classical", "Metal", "Folk", "Punk", "Blues", 
        "Latin", "Afrobeats"
    ]
    for genre in all_genres:
        if genre.lower() in intent:
            target_genre = genre
            break
    
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1 AND status = 'active'")
    
    c.execute("""
        INSERT INTO exploration_pacts 
        (user_id, raw_conversation_log, target_genre_or_artist, breadth, intensity, user_motivation, window_days, target_share, status)
        VALUES (1, ?, ?, 'broad', 'casual', 'Testing phase 1', 21, 0.3, 'active')
    """, (f"User: {req.intent_raw}", target_genre))
    
    conn.commit()
    conn.close()
    return {"status": "success", "target": target_genre}

@router.post("/pacts/clear")
def clear_pacts():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.get("/recommendations/{surface_id}", response_model=List[TrackModel])
def get_recommendations(surface_id: str):
    """
    Core Blending Logic: Guarantees `target_share` of pact content is injected into EACH surface.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    total_tracks = 20
    
    # 1. Fetch Baseline Tastes
    c.execute("SELECT genre FROM user_baseline_tastes WHERE user_id = 1")
    baseline_genres = [row['genre'] for row in c.fetchall()]
    placeholders = ','.join('?' * len(baseline_genres))
    
    # 2. Check for Active Pact
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 AND status = 'active' ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    
    results = []
    
    if pact:
        target_share = pact['target_share']
        num_exploration = int(total_tracks * target_share)
        num_baseline = total_tracks - num_exploration
        target_genre = pact['target_genre_or_artist']
        
        # 3a. Fetch Exploration Tracks
        c.execute("SELECT * FROM tracks WHERE genre = ? ORDER BY RANDOM() LIMIT ?", (target_genre, num_exploration))
        for row in c.fetchall():
            track = dict(row)
            track['is_pact_track'] = True
            # The Phase 1 mocked explanation (Phase 2 uses LLM)
            track['scout_explanation'] = f"Scout's pick — Day 1 of your {target_genre.lower()} pact."
            results.append(track)
            
        # 3b. Fetch Baseline Tracks
        c.execute(f"SELECT * FROM tracks WHERE genre IN ({placeholders}) ORDER BY RANDOM() LIMIT ?", (*baseline_genres, num_baseline))
        for row in c.fetchall():
            track = dict(row)
            track['is_pact_track'] = False
            results.append(track)
    else:
        # 100% Baseline
        c.execute(f"SELECT * FROM tracks WHERE genre IN ({placeholders}) ORDER BY RANDOM() LIMIT ?", (*baseline_genres, total_tracks))
        for row in c.fetchall():
            track = dict(row)
            track['is_pact_track'] = False
            results.append(track)
            
    conn.close()
    
    # 4. Shuffle tracks to naturally distribute the injected pact content
    random.shuffle(results)
    
    return results

@router.get("/state")
def get_debug_state():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 AND status = 'active' ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    conn.close()
    
    return {
        "active_pact": dict(pact) if pact else None
    }
