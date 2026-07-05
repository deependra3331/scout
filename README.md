# Spotify Scout

A witty, irreverent music expedition guide that helps you explore new genres and artists.

## Project Structure

- `phase1_core_logic/`: Initial core logic phase
- `phase2_scout_conversation/`: Scout conversation logic
- `phase3_taste_map_visuals/`: Taste map visualizations
- `unified_app/`: Unified application combining all features
- `main.py`: FastAPI entry point

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

3. Add your API keys to `.env`:
   - `GROQ_API_KEY`: Your Groq API key for LLM functionality
   - `SPOTIFY_CLIENT_ID`: Spotify app client ID
   - `SPOTIFY_CLIENT_SECRET`: Spotify app client secret
   - `SPOTIFY_REDIRECT_URI`: Redirect URI for Spotify OAuth

## Run

```bash
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## Features

- Scout personality with witty conversational responses
- Spotify integration for taste mapping
- Genre exploration pacts
- Taste map visualizations
