from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from unified_app.api import router as unified_router

app = FastAPI(title="Spotify Scout — Unified")

# API routes
app.include_router(unified_router)

# Serve static frontend (must be last — catch-all)
app.mount("/", StaticFiles(directory="unified_app/static", html=True), name="static")
