
import pytest
from fastapi.testclient import TestClient
from main import app
import sqlite3

client = TestClient(app)
DB_PATH = "scout.db"

def clear_pacts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE exploration_pacts SET status = 'abandoned' WHERE user_id = 1")
    conn.commit()
    conn.close()

def test_test_endpoint():
    """Test the /test endpoint in main.py"""
    response = client.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "pwd" in data
    assert "directories" in data

def test_phase1_state_main():
    """Test /api/phase1/state via main app"""
    clear_pacts()
    response = client.get("/api/phase1/state")
    assert response.status_code == 200

def test_phase2_chat_main_mocked():
    """Test /api/phase2/chat via main app (mock llm)"""
    from unittest.mock import patch
    clear_pacts()
    with patch('phase2_scout_conversation.api.extract_pact_intent') as mock_extract, patch('phase2_scout_conversation.api.chat_with_scout') as mock_chat:
        mock_extract.return_value = {"is_ready": False}
        mock_chat.return_value = "Hey there!"
        payload = {"messages": [{"role": "user", "content": "Hey"}]}
        response = client.post("/api/phase2/chat", json=payload)
        assert response.status_code == 200

def test_phase3_taste_map_main():
    """Test /api/phase3/taste_map via main app"""
    response = client.get("/api/phase3/taste_map")
    assert response.status_code == 200
