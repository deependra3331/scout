
import requests

def test_endpoint(url, method='GET', data=None):
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {'error': str(e)}

# Test phase1 state
print("=== Phase1 State ===")
state = test_endpoint("http://localhost:3001/api/phase1/state")
print(state)

# Test phase1 recommendations
print("\n=== Phase1 Recommendations (homepage) ===")
recs = test_endpoint("http://localhost:3001/api/phase1/recommendations/homepage")
print(f"Got {len(recs) if isinstance(recs, list) else 'error'} recommendations")

# Test phase3 taste map
print("\n=== Phase3 Taste Map ===")
taste_map = test_endpoint("http://localhost:3001/api/phase3/taste_map")
print(taste_map)

# Test phase2 chat (just to see if endpoint exists)
print("\n=== Phase2 Chat ===")
chat_response = test_endpoint(
    "http://localhost:3001/api/phase2/chat",
    method='POST',
    data={'messages': [{'role': 'user', 'content': 'Hello'}]}
)
print(chat_response)
