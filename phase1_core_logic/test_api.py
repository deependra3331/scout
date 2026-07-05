import pytest
from fastapi.testclient import TestClient
from phase1_core_logic.api import router
from fastapi import FastAPI
import sqlite3

# Setup a test FastAPI app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

DB_PATH = "scout.db"

def clear_pacts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
    conn.commit()
    conn.close()

def test_initial_state_no_pact():
    clear_pacts()
    response = client.get("/api/phase1/state")
    assert response.status_code == 200
    assert response.json()["active_pact"] is None

def test_baseline_recommendations():
    clear_pacts()
    response = client.get("/api/phase1/recommendations/homepage")
    assert response.status_code == 200
    tracks = response.json()
    assert len(tracks) == 20
    # All tracks should be non-pact and baseline genres (Pop/Indie Pop)
    for track in tracks:
        assert track["is_pact_track"] is False
        assert track["genre"] in ["Pop", "Indie Pop"]

def test_create_pact():
    clear_pacts()
    response = client.post("/api/phase1/pacts", json={"intent_raw": "jazz"})
    assert response.status_code == 200
    assert response.json()["target"] == "Jazz"
    
    # Verify state
    state_res = client.get("/api/phase1/state")
    active_pact = state_res.json()["active_pact"]
    assert active_pact is not None
    assert active_pact["target_genre_or_artist"] == "Jazz"
    assert active_pact["target_share"] == 0.3
    assert active_pact["status"] == "active"

def test_blended_recommendations():
    # Assumes previous test created the Jazz pact successfully
    response = client.get("/api/phase1/recommendations/daily_mix")
    assert response.status_code == 200
    tracks = response.json()
    assert len(tracks) == 20
    
    pact_tracks = [t for t in tracks if t["is_pact_track"]]
    baseline_tracks = [t for t in tracks if not t["is_pact_track"]]
    
    # 30% of 20 = 6 tracks
    assert len(pact_tracks) == 6
    assert len(baseline_tracks) == 14
    
    for track in pact_tracks:
        assert track["genre"] == "Jazz"
        assert "Scout's pick" in track["scout_explanation"]
        
    for track in baseline_tracks:
        assert track["genre"] in ["Pop", "Indie Pop"]
        assert track["scout_explanation"] is None
