# Spotify Scout

A witty, irreverent music expedition guide that helps you explore new genres and artists.

## Project Structure

- `phase1_core_logic/`: Initial core logic phase
- `phase2_scout_conversation/`: Scout conversation logic
- `phase3_taste_map_visuals/`: Taste map visualizations
- `unified_app/`: Unified application combining all features
- `main.py`: FastAPI entry point
- `vercel.json`: Vercel deployment configuration

## Local Setup

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

## Run Locally

```bash
uvicorn main:app --reload
```

Then open http://127.0.0.1:8000 in your browser.

## Deploy to Vercel

1. **Push your code to GitHub** (ensure all changes are committed)

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Sign in with your GitHub account
   - Click "New Project"
   - Select your `scout` repository

3. **Configure Environment Variables**:
   - In the Vercel project dashboard, go to "Settings" > "Environment Variables"
   - Add all variables from your `.env` file (GROQ_API_KEY, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI)
   - Make sure to update `SPOTIFY_REDIRECT_URI` to your Vercel app's URL (e.g., `https://your-scout-app.vercel.app/api/auth/callback`)

4. **Deploy**:
   - Click "Deploy"
   - Vercel will automatically detect the FastAPI app and deploy it using the `vercel.json` configuration

## Features

- Scout personality with witty conversational responses
- Spotify integration for taste mapping
- Genre exploration pacts
- Taste map visualizations
