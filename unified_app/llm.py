"""
Scout LLM - Refined personality layer powered by Groq (Llama 3 70B).
"""

import os
import json

from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Groq client (graceful if key is missing)
# ---------------------------------------------------------------------------
try:
    from groq import Groq

    _api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=_api_key) if _api_key else None
    if not client:
        print("WARNING: GROQ_API_KEY not set. LLM calls will use fallbacks.")
except ImportError:
    client = None
    print("WARNING: groq package not installed. LLM calls will use fallbacks.")

# ---------------------------------------------------------------------------
# System prompt for chat
# ---------------------------------------------------------------------------
SCOUT_SYSTEM_PROMPT = """You are Scout — a witty, irreverent music expedition guide. You talk like a best friend who also happens to be an obsessive music nerd.

PERSONALITY RULES:
- Use metaphors about exploration, maps, fog, uncharted territory, compass needles, and sonic landscapes.
- Reference the user's known taste when provided — acknowledge their comfort zone before gently nudging them toward the edges.
- Ask about mood, memories, or what sparked their curiosity. "What's pulling you in that direction?" > "What would you like to explore?"
- NEVER sound corporate, formal, or like a product assistant. No "I'd be happy to help." No "Great choice!"
- Use casual language, occasional slang, short punchy sentences. You can be playful, sarcastic, or dramatic.
- Keep responses to 3 sentences MAX. Punch hard, get out.

{baseline_context}
"""


def _baseline_context_block(baseline_tastes: dict | None) -> str:
    if not baseline_tastes:
        return "You don't know the user's taste yet — feel free to probe."
    lines = ", ".join(f"{g} ({a:.0%})" for g, a in baseline_tastes.items())
    return f"The user's current taste map: {lines}. Use this to ground your suggestions."


# ---------------------------------------------------------------------------
# Chat with Scout
# ---------------------------------------------------------------------------
def chat_with_scout(
    user_message: str,
    conversation_history: list[dict] | None = None,
    baseline_tastes: dict | None = None,
) -> str:
    """Main conversational endpoint — Scout replies to the user."""
    if not client:
        return (
            "🗺️ Your map's looking a little familiar. "
            "Tell me — what sound have you been circling but never stepped into?"
        )

    system = SCOUT_SYSTEM_PROMPT.format(
        baseline_context=_baseline_context_block(baseline_tastes)
    )
    messages = [{"role": "system", "content": system}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.85,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM chat error: {e}")
        return (
            "🧭 My compass is spinning right now — give me a sec. "
            "In the meantime, what genre have you been secretly curious about?"
        )


# ---------------------------------------------------------------------------
# Extract pact intent from conversation
# ---------------------------------------------------------------------------
PACT_EXTRACTION_PROMPT = """You are a JSON extraction assistant. Analyze the conversation and determine if the user wants to commit to exploring a specific music genre or artist's world.

RULES:
- Look for explicit or implicit intent to explore something new.
- The target can be a GENRE (e.g. "jazz", "metal", "ambient") or an ARTIST (e.g. "Radiohead" — map to their primary genre).
- If the user mentions an artist, map them to the most fitting genre from this list: Pop, Indie Pop, Rock, Indie Rock, Hip Hop, R&B, Electronic, Ambient, Jazz, Classical, Metal, Folk, Punk, Blues, Latin, Afrobeats.
- Extract their motivation if stated (e.g. "I've always wanted to understand jazz").
- Return ONLY valid JSON with keys: "has_intent" (bool), "target_genre" (str or null), "motivation" (str or null).
- If no clear intent, return {"has_intent": false, "target_genre": null, "motivation": null}.
"""


def extract_pact_intent(conversation_history: list[dict]) -> dict:
    """Pull structured pact intent from a conversation."""
    fallback = {"has_intent": False, "target_genre": None, "motivation": None}

    if not client:
        return fallback

    messages = [{"role": "system", "content": PACT_EXTRACTION_PROMPT}]

    # Flatten conversation into a single user message for extraction
    convo_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in conversation_history
    )
    messages.append(
        {"role": "user", "content": f"Analyze this conversation:\n\n{convo_text}"}
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        # Try to parse JSON from the response
        if "{" in raw:
            json_str = raw[raw.index("{") : raw.rindex("}") + 1]
            return json.loads(json_str)
        return fallback
    except Exception as e:
        print(f"Pact extraction error: {e}")
        return fallback


# ---------------------------------------------------------------------------
# Drift nudge — personality-driven push toward adjacent genres
# ---------------------------------------------------------------------------
DRIFT_NUDGE_PROMPT = """You are Scout, the music expedition guide. The user made a pact to explore {target_genre}.

Now you're nudging them toward a DRIFT — a brief detour into {drift_genre}, which is adjacent territory.

Write a single short, punchy notification (2 sentences max). Be playful and specific. Reference both genres. Use a metaphor about wandering off the trail, taking a side path, or hearing something in the fog. Make them CURIOUS.

Do NOT use emojis. Do NOT be generic."""


def generate_drift_nudge(target_genre: str, drift_genre: str) -> str:
    """Generate a personality-driven drift nudge notification."""
    if not client:
        return (
            f"You came for {target_genre}, but I keep hearing {drift_genre} echoes "
            f"in the fog. Wanna take a detour?"
        )

    prompt = DRIFT_NUDGE_PROMPT.format(
        target_genre=target_genre, drift_genre=drift_genre
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Generate a drift nudge."},
            ],
            temperature=0.9,
            max_tokens=120,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Drift nudge error: {e}")
        return (
            f"Your {target_genre} expedition just brushed against {drift_genre} territory. "
            f"Curious what lives there?"
        )


# ---------------------------------------------------------------------------
# Recap story — Wrapped-style summary of an exploration pact
# ---------------------------------------------------------------------------
RECAP_PROMPT = """You are Scout. Write a short, dramatic "expedition recap" for a user who just finished (or is deep into) a music exploration pact.

Details:
- Target genre: {target}
- Their original motivation: "{motivation}"
- Days active: {days_active}

Write it like a dramatic expedition journal entry. 3-4 sentences. Reference the genre, the journey, and what they might have discovered. Be poetic but not cheesy. No emojis."""


def generate_recap_story(
    target: str, motivation: str, days_active: int
) -> str:
    """Generate a Wrapped-style recap story for a completed/active pact."""
    if not client:
        return (
            f"Day {days_active} of your {target} expedition. You came because '{motivation}' "
            f"— and the territory has changed you. The map looks different now."
        )

    prompt = RECAP_PROMPT.format(
        target=target, motivation=motivation, days_active=days_active
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Write the recap."},
            ],
            temperature=0.85,
            max_tokens=250,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Recap story error: {e}")
        return (
            f"Day {days_active} in {target} territory. You said '{motivation}' — "
            f"and the landscape answered. Some paths you won't forget."
        )


# ---------------------------------------------------------------------------
# Midpoint check-in — halfway through a pact
# ---------------------------------------------------------------------------
MIDPOINT_PROMPT = """You are Scout. The user is at the midpoint of their exploration pact.

Details:
- Target genre: {target}
- Days elapsed: {days_elapsed}
- Days remaining: {days_remaining}

Write a short midpoint check-in (2-3 sentences). Ask how the terrain feels. Reference the halfway mark. Be encouraging but not saccharine. No emojis. Sound like a trail companion, not a life coach."""


def generate_midpoint_checkin(
    target: str, days_elapsed: int, days_remaining: int
) -> str:
    """Generate a midpoint check-in message for an active pact."""
    if not client:
        return (
            f"Halfway through your {target} expedition — {days_elapsed} days in, "
            f"{days_remaining} to go. How's the terrain feel? Finding anything that sticks?"
        )

    prompt = MIDPOINT_PROMPT.format(
        target=target, days_elapsed=days_elapsed, days_remaining=days_remaining
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Write the check-in."},
            ],
            temperature=0.8,
            max_tokens=180,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Midpoint check-in error: {e}")
        return (
            f"You're {days_elapsed} days into {target} with {days_remaining} left. "
            f"Halfway mark. What's landed so far?"
        )
