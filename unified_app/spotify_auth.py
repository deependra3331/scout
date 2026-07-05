"""
Spotify OAuth2 helper — handles auth URL generation, code exchange, and profile/genre fetching.
"""

import os
from urllib.parse import urlencode
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:5173/callback")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

SCOPES = "user-read-private user-top-read user-read-recently-played"


def get_auth_url() -> str:
    """Build the Spotify authorization URL with required scopes."""
    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES,
        "show_dialog": "true",
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for access and refresh tokens."""
    try:
        resp = httpx.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
                "client_id": SPOTIFY_CLIENT_ID,
                "client_secret": SPOTIFY_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"Spotify token exchange HTTP error: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        print(f"Spotify token exchange error: {e}")
        return {"error": str(e)}


def get_user_profile(access_token: str) -> dict:
    """Fetch the authenticated user's Spotify profile."""
    try:
        resp = httpx.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"Spotify profile HTTP error: {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        print(f"Spotify profile error: {e}")
        return {"error": str(e)}


def get_user_top_genres(access_token: str) -> list[str]:
    """Fetch the user's top artists and extract the top 5 genres."""
    try:
        resp = httpx.get(
            "https://api.spotify.com/v1/me/top/artists",
            params={"limit": 20, "time_range": "medium_term"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()

        genre_counter: Counter = Counter()
        for artist in data.get("items", []):
            for genre in artist.get("genres", []):
                genre_counter[genre] += 1

        # Return top 5 genres sorted by frequency
        return [genre for genre, _ in genre_counter.most_common(5)]
    except httpx.HTTPStatusError as e:
        print(f"Spotify top genres HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"Spotify top genres error: {e}")
        return []
