"""
Scout Unified API — single router combining auth, chat, recommendations, taste map, and pacts.
"""

import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel

from unified_app.db import get_db, init_and_seed_db, GENRE_ARTISTS
from unified_app.llm import (
    chat_with_scout,
    extract_pact_intent,
    generate_drift_nudge,
    generate_recap_story,
    generate_midpoint_checkin,
)
from unified_app.spotify_auth import (
    get_auth_url,
    exchange_code,
    get_user_profile,
)

# ---------------------------------------------------------------------------
# Ensure DB is seeded on import
# ---------------------------------------------------------------------------
init_and_seed_db()

router = APIRouter(prefix="/api")

USER_ID = 1  # Default user for MVP


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] | None = None


class DriftRequest(BaseModel):
    drift_genre: str | None = None


class RecapRequest(BaseModel):
    target: str | None = None
    motivation: str | None = None
    days_active: int | None = None


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@router.get("/auth/login")
def auth_login():
    """Return the Spotify OAuth authorization URL."""
    return {"auth_url": get_auth_url()}


@router.get("/auth/callback")
def auth_callback(code: str = Query(...)):
    """Exchange the Spotify auth code for tokens and save to DB."""
    token_data = exchange_code(code)

    if "error" in token_data:
        return {"error": token_data["error"], "detail": token_data.get("detail")}

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

    # Fetch profile
    profile = get_user_profile(access_token)
    spotify_id = profile.get("id", "")
    display_name = profile.get("display_name", "")

    # Upsert into spotify_auth
    conn = get_db()
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM spotify_auth WHERE user_id = ?", (USER_ID,)
    ).fetchone()

    if existing:
        cur.execute(
            """UPDATE spotify_auth
               SET spotify_id = ?, display_name = ?, access_token = ?,
                   refresh_token = ?, token_expiry = ?, updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?""",
            (spotify_id, display_name, access_token, refresh_token, str(token_expiry), USER_ID),
        )
    else:
        cur.execute(
            """INSERT INTO spotify_auth
               (user_id, spotify_id, display_name, access_token, refresh_token, token_expiry)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (USER_ID, spotify_id, display_name, access_token, refresh_token, str(token_expiry)),
        )

    conn.commit()
    conn.close()

    return {
        "status": "connected",
        "spotify_id": spotify_id,
        "display_name": display_name,
    }


@router.get("/auth/status")
def auth_status():
    """Check if the user has a valid Spotify auth record."""
    conn = get_db()
    row = conn.execute(
        "SELECT spotify_id, display_name, token_expiry FROM spotify_auth WHERE user_id = ?",
        (USER_ID,),
    ).fetchone()
    conn.close()

    if not row:
        return {"connected": False}

    # Check if token is expired
    expiry_str = row["token_expiry"]
    is_expired = False
    if expiry_str:
        try:
            expiry = datetime.fromisoformat(expiry_str)
            is_expired = datetime.utcnow() > expiry
        except ValueError:
            is_expired = True

    return {
        "connected": True,
        "spotify_id": row["spotify_id"],
        "display_name": row["display_name"],
        "token_expired": is_expired,
    }


# ---------------------------------------------------------------------------
# State endpoint
# ---------------------------------------------------------------------------
@router.get("/state")
def get_state():
    """Return active pact, baseline tastes, and Spotify connection status."""
    conn = get_db()

    # Active pact
    pact_row = conn.execute(
        "SELECT * FROM exploration_pacts WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (USER_ID,),
    ).fetchone()

    active_pact = None
    if pact_row:
        active_pact = {
            "id": pact_row["id"],
            "target_genre": pact_row["target_genre"],
            "motivation": pact_row["motivation"],
            "status": pact_row["status"],
            "duration_days": pact_row["duration_days"],
            "started_at": pact_row["started_at"],
        }

    # Baseline tastes
    taste_rows = conn.execute(
        "SELECT genre, affinity FROM user_baseline_tastes WHERE user_id = ?",
        (USER_ID,),
    ).fetchall()
    baseline_tastes = {r["genre"]: r["affinity"] for r in taste_rows}

    # Spotify connected?
    spotify_row = conn.execute(
        "SELECT spotify_id FROM spotify_auth WHERE user_id = ?", (USER_ID,)
    ).fetchone()
    spotify_connected = spotify_row is not None

    conn.close()

    return {
        "active_pact": active_pact,
        "baseline_tastes": baseline_tastes,
        "spotify_connected": spotify_connected,
    }


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------
@router.post("/chat")
def chat(req: ChatRequest):
    """Chat with Scout. May also detect and create exploration pacts."""
    conn = get_db()

    # Get baseline tastes for context
    taste_rows = conn.execute(
        "SELECT genre, affinity FROM user_baseline_tastes WHERE user_id = ?",
        (USER_ID,),
    ).fetchall()
    baseline = {r["genre"]: r["affinity"] for r in taste_rows}

    # Get Scout's reply
    reply = chat_with_scout(req.message, req.conversation_history, baseline)

    # Build full conversation for pact extraction
    history = list(req.conversation_history or [])
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})

    # Check for pact intent
    pact_intent = extract_pact_intent(history)
    pact_created = None

    if pact_intent.get("has_intent") and pact_intent.get("target_genre"):
        # Check no active pact already
        existing = conn.execute(
            "SELECT id FROM exploration_pacts WHERE user_id = ? AND status = 'active'",
            (USER_ID,),
        ).fetchone()

        if not existing:
            target = pact_intent["target_genre"]
            motivation = pact_intent.get("motivation", "Curiosity")
            conn.execute(
                "INSERT INTO exploration_pacts (user_id, target_genre, motivation) VALUES (?, ?, ?)",
                (USER_ID, target, motivation),
            )
            conn.commit()
            pact_created = {"target_genre": target, "motivation": motivation}

    conn.close()

    return {
        "reply": reply,
        "pact_created": pact_created,
        "pact_intent": pact_intent,
    }


# ---------------------------------------------------------------------------
# Recommendations endpoint
# ---------------------------------------------------------------------------
@router.get("/recommendations/{surface_id}")
def get_recommendations(surface_id: str):
    """
    Blended recommendations.
    surface_id can be 'home', 'explore', 'pact', or a genre name.
    """
    conn = get_db()

    # Get baseline tastes
    taste_rows = conn.execute(
        "SELECT genre, affinity FROM user_baseline_tastes WHERE user_id = ?",
        (USER_ID,),
    ).fetchall()
    baseline = {r["genre"]: r["affinity"] for r in taste_rows}

    # Get active pact
    pact_row = conn.execute(
        "SELECT target_genre FROM exploration_pacts WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (USER_ID,),
    ).fetchone()
    pact_genre = pact_row["target_genre"] if pact_row else None

    # Determine blend weights based on surface
    all_genres = list(GENRE_ARTISTS.keys())

    if surface_id == "pact" and pact_genre:
        # Heavy on pact genre + some baseline comfort
        weights = {g: 0.05 for g in all_genres}
        weights[pact_genre] = 0.5
        for g, a in baseline.items():
            weights[g] = max(weights.get(g, 0), a * 0.3)
    elif surface_id == "explore":
        # Emphasize genres NOT in baseline
        weights = {}
        for g in all_genres:
            if g in baseline:
                weights[g] = 0.1
            else:
                weights[g] = 0.3
        if pact_genre:
            weights[pact_genre] = 0.5
    elif surface_id == "home":
        # Comfort-heavy with sprinkles
        weights = {g: 0.05 for g in all_genres}
        for g, a in baseline.items():
            weights[g] = a
        if pact_genre:
            weights[pact_genre] = max(weights.get(pact_genre, 0), 0.35)
    else:
        # Treat surface_id as a genre name
        weights = {g: 0.05 for g in all_genres}
        if surface_id in all_genres:
            weights[surface_id] = 0.8

    # Weighted random selection of tracks
    tracks = []
    for genre, weight in weights.items():
        count = max(1, int(weight * 15))
        rows = conn.execute(
            "SELECT id, title, artist, genre, cover_url FROM tracks WHERE genre = ? ORDER BY RANDOM() LIMIT ?",
            (genre, count),
        ).fetchall()
        tracks.extend([dict(r) for r in rows])

    conn.close()

    # Shuffle and limit
    random.shuffle(tracks)
    tracks = tracks[:20]

    return {
        "surface_id": surface_id,
        "pact_genre": pact_genre,
        "track_count": len(tracks),
        "tracks": tracks,
    }


# ---------------------------------------------------------------------------
# Simulate drift
# ---------------------------------------------------------------------------
@router.post("/simulate_drift")
def simulate_drift(req: DriftRequest):
    """Simulate a drift event — nudge user toward an adjacent genre."""
    conn = get_db()

    pact_row = conn.execute(
        "SELECT target_genre FROM exploration_pacts WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (USER_ID,),
    ).fetchone()

    if not pact_row:
        conn.close()
        return {"error": "No active pact. Start an expedition first."}

    target = pact_row["target_genre"]

    # Pick a drift genre (not the target, not in baseline)
    taste_rows = conn.execute(
        "SELECT genre FROM user_baseline_tastes WHERE user_id = ?", (USER_ID,)
    ).fetchall()
    baseline_genres = {r["genre"] for r in taste_rows}

    all_genres = list(GENRE_ARTISTS.keys())
    drift_candidates = [g for g in all_genres if g != target and g not in baseline_genres]

    if req.drift_genre and req.drift_genre in all_genres:
        drift_genre = req.drift_genre
    elif drift_candidates:
        drift_genre = random.choice(drift_candidates)
    else:
        drift_genre = random.choice([g for g in all_genres if g != target])

    # Generate nudge
    nudge = generate_drift_nudge(target, drift_genre)

    # Get drift tracks
    drift_tracks = conn.execute(
        "SELECT id, title, artist, genre, cover_url FROM tracks WHERE genre = ? ORDER BY RANDOM() LIMIT 5",
        (drift_genre,),
    ).fetchall()

    conn.close()

    return {
        "pact_target": target,
        "drift_genre": drift_genre,
        "nudge_message": nudge,
        "drift_tracks": [dict(t) for t in drift_tracks],
    }


# ---------------------------------------------------------------------------
# Taste map
# ---------------------------------------------------------------------------
@router.get("/taste_map")
def taste_map():
    """Return the full taste map across all genres with listening activity."""
    conn = get_db()

    # Baseline tastes
    taste_rows = conn.execute(
        "SELECT genre, affinity FROM user_baseline_tastes WHERE user_id = ?",
        (USER_ID,),
    ).fetchall()
    baseline = {r["genre"]: r["affinity"] for r in taste_rows}

    # Listening counts by genre
    listen_rows = conn.execute(
        "SELECT genre, COUNT(*) as cnt FROM listening_events WHERE user_id = ? GROUP BY genre",
        (USER_ID,),
    ).fetchall()
    listen_counts = {r["genre"]: r["cnt"] for r in listen_rows}

    # Active pact
    pact_row = conn.execute(
        "SELECT target_genre FROM exploration_pacts WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (USER_ID,),
    ).fetchone()
    pact_genre = pact_row["target_genre"] if pact_row else None

    conn.close()

    # Build full map
    all_genres = list(GENRE_ARTISTS.keys())
    taste_data = []
    for genre in all_genres:
        affinity = baseline.get(genre, 0.0)
        listens = listen_counts.get(genre, 0)

        # Classify zone
        if affinity >= 0.6:
            zone = "comfort"
        elif affinity >= 0.3:
            zone = "familiar"
        elif listens > 0:
            zone = "explored"
        else:
            zone = "uncharted"

        # Override if it's the active pact target
        if genre == pact_genre:
            zone = "exploring"

        taste_data.append(
            {
                "genre": genre,
                "affinity": round(affinity, 2),
                "listens": listens,
                "zone": zone,
                "is_pact_target": genre == pact_genre,
            }
        )

    return {
        "genres": taste_data,
        "total_genres": len(taste_data),
        "pact_genre": pact_genre,
    }


# ---------------------------------------------------------------------------
# Generate recap
# ---------------------------------------------------------------------------
@router.post("/generate_recap")
def generate_recap(req: RecapRequest):
    """Generate a Wrapped-style recap for the current or specified pact."""
    conn = get_db()

    if req.target:
        target = req.target
        motivation = req.motivation or "Pure curiosity"
        days_active = req.days_active or 7
    else:
        pact_row = conn.execute(
            "SELECT target_genre, motivation, started_at FROM exploration_pacts WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (USER_ID,),
        ).fetchone()

        if not pact_row:
            conn.close()
            return {"error": "No pact found for recap."}

        target = pact_row["target_genre"]
        motivation = pact_row["motivation"] or "Pure curiosity"

        # Calculate days active
        try:
            started = datetime.fromisoformat(pact_row["started_at"])
            days_active = max(1, (datetime.utcnow() - started).days)
        except (ValueError, TypeError):
            days_active = 7

    conn.close()

    story = generate_recap_story(target, motivation, days_active)

    return {
        "target": target,
        "motivation": motivation,
        "days_active": days_active,
        "story": story,
    }


# ---------------------------------------------------------------------------
# Clear pacts
# ---------------------------------------------------------------------------
@router.post("/pacts/clear")
def clear_pacts():
    """Clear all active pacts for the user."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE exploration_pacts SET status = 'cleared', completed_at = CURRENT_TIMESTAMP WHERE user_id = ? AND status = 'active'",
        (USER_ID,),
    )
    affected = cur.rowcount
    conn.commit()
    conn.close()

    return {"cleared": affected, "message": f"Cleared {affected} active pact(s)."}
