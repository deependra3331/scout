import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from phase2_scout_conversation.api import router
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

@patch('phase2_scout_conversation.api.extract_pact_intent')
@patch('phase2_scout_conversation.api.chat_with_scout')
def test_chat_no_intent_yet(mock_chat, mock_extract):
    """
    Test TC-2.1: User is just chatting, no pact formed yet.
    """
    clear_pacts()
    mock_extract.return_value = {"is_ready": False}
    mock_chat.return_value = "What specific vibe are you going for?"
    
    payload = {
        "messages": [{"role": "user", "content": "I want to hear some electronic music."}]
    }
    
    response = client.post("/api/phase2/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["pact_created"] is False
    assert data["reply"] == "What specific vibe are you going for?"
    assert data["intent"] is None

@patch('phase2_scout_conversation.api.extract_pact_intent')
def test_chat_forms_pact(mock_extract):
    """
    Test TC-2.1: User provides clear intent, pact is formed and saved to DB.
    """
    clear_pacts()
    # Mock the LLM extracting a valid intent
    mock_extract.return_value = {
        "is_ready": True,
        "target_genre_or_artist": "Aphex Twin",
        "breadth": "narrow",
        "intensity": "aggressive",
        "user_motivation": "Friend recommended it"
    }
    
    payload = {
        "messages": [
            {"role": "user", "content": "I want to hear some electronic music."},
            {"role": "assistant", "content": "What specific vibe?"},
            {"role": "user", "content": "Like Aphex Twin"}
        ]
    }
    
    response = client.post("/api/phase2/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["pact_created"] is True
    assert "Pact locked in!" in data["reply"]
    assert data["intent"]["target_genre_or_artist"] == "Aphex Twin"
    
    # Verify DB state was actually updated
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM exploration_pacts WHERE user_id = 1 AND status = 'active' ORDER BY id DESC LIMIT 1")
    pact = c.fetchone()
    conn.close()
    
    assert pact is not None
    assert pact["target_genre_or_artist"] == "Aphex Twin"
    assert pact["breadth"] == "narrow"
    assert pact["intensity"] == "aggressive"

@patch('phase2_scout_conversation.api.generate_drift_nudge')
def test_simulate_drift_with_active_pact(mock_nudge):
    """
    Test TC-2.2: User drifts back to old habits, Scout intervenes.
    """
    # Ensure there is an active pact (relies on previous test or we can insert one)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
    c.execute("""
        INSERT INTO exploration_pacts 
        (user_id, target_genre_or_artist, status) VALUES (1, 'Jazz', 'active')
    """)
    conn.commit()
    conn.close()
    
    mock_nudge.return_value = "I see you playing Pop! Should we pause the Jazz expedition?"
    
    response = client.post("/api/phase2/simulate_drift", json={"genre": "Pop"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["nudge"] == "I see you playing Pop! Should we pause the Jazz expedition?"
    
    # Verify mock was called with correct arguments
    mock_nudge.assert_called_once_with("Jazz", "Pop")
