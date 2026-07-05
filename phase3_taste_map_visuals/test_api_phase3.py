import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from phase3_taste_map_visuals.api import router
from fastapi import FastAPI
import sqlite3

# Setup a test FastAPI app
app = FastAPI()
app.include_router(router)
client = TestClient(app)

DB_PATH = "scout.db"

def set_test_state():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Ensure baseline is set
    c.execute("DELETE FROM user_baseline_tastes WHERE user_id = 1")
    c.execute("INSERT INTO user_baseline_tastes (user_id, genre, affinity_score) VALUES (1, 'Pop', 0.8)")
    
    # Ensure pact is set
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
    c.execute("""
        INSERT INTO exploration_pacts 
        (user_id, target_genre_or_artist, user_motivation, status) 
        VALUES (1, 'Jazz', 'Friend recommendation', 'active')
    """)
    conn.commit()
    conn.close()

def test_taste_map_nodes():
    """
    Test TC-3.1: Taste Map Territory Claiming / State rendering.
    Verifies that the graph nodes correctly reflect familiar vs active vs fog.
    """
    set_test_state()
    response = client.get("/api/phase3/taste_map")
    assert response.status_code == 200
    
    data = response.json()
    assert "nodes" in data
    
    pop_node = next(n for n in data["nodes"] if n["id"] == "Pop")
    jazz_node = next(n for n in data["nodes"] if n["id"] == "Jazz")
    metal_node = next(n for n in data["nodes"] if n["id"] == "Metal")
    
    # Pop is in baseline, should be familiar
    assert pop_node["state"] == "familiar"
    
    # Jazz is active pact, should be active_pact
    assert jazz_node["state"] == "active_pact"
    
    # Metal is completely unexplored, should be fog
    assert metal_node["state"] == "fog"

@patch('phase3_taste_map_visuals.api.Groq')
def test_generate_recap(mock_groq):
    """
    Test TC-3.2: Recap Generation using mocked LLM.
    """
    set_test_state()
    
    # Setup mock LLM response
    mock_client = MagicMock()
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices[0].message.content = "You conquered the Jazz territory, proving your friend right!"
    mock_client.chat.completions.create.return_value = mock_chat_completion
    mock_groq.return_value = mock_client
    
    response = client.post("/api/phase3/generate_recap")
    assert response.status_code == 200
    
    data = response.json()
    assert "story" in data
    assert data["story"] == "You conquered the Jazz territory, proving your friend right!"
