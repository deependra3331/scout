import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Initialize Groq client
# The user needs to set GROQ_API_KEY in their .env file
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    client = None
    print(f"Warning: Could not initialize Groq client. Is GROQ_API_KEY set? Error: {e}")

MODEL_NAME = "llama-3.3-70b-versatile" # Current supported model

def chat_with_scout(conversation_history: list) -> str:
    """
    Takes the conversation history and returns Scout's next response.
    Scout's personality: An enthusiastic, slightly witty expedition guide for music.
    """
    if not client: return "I'm offline! Please set your GROQ_API_KEY in the .env file."
    
    system_prompt = """
    You are Scout, an AI music co-pilot. Your job is to help the user explore new music genres or artists.
    You frame these explorations as "pacts" or "expeditions". 
    You are witty, encouraging, and conversational. Do NOT talk like a corporate assistant.
    Ask clarifying questions if their intent is vague (e.g. "What kind of vibe are you looking for?").
    If they are ready to commit, acknowledge it enthusiastically and say you'll lock in the pact.
    Keep your responses under 3 sentences.
    """
    
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=150,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Whoops, my comms are down. (Groq API Error: {str(e)})"

def extract_pact_intent(conversation_history: list) -> dict:
    """
    Analyzes the chat log and extracts a structured JSON pact if the user has agreed to one.
    """
    if not client: return None
    
    system_prompt = """
    Analyze the conversation history. If the user has clearly stated a genre or artist they want to explore, 
    extract the intent into the following JSON format ONLY:
    {
        "is_ready": true/false,
        "target_genre_or_artist": "genre or artist name (e.g. 'Ambient', 'Jazz', 'Aphex Twin')",
        "breadth": "broad" or "narrow",
        "intensity": "casual" or "aggressive",
        "user_motivation": "A short summary of why they want to explore this"
    }
    If they are still just chatting and haven't settled on a specific target, return {"is_ready": false}.
    Respond ONLY with valid JSON.
    """
    
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=MODEL_NAME,
            temperature=0.1, # Low temp for structured output
            response_format={"type": "json_object"},
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error extracting intent: {e}")
        return {"is_ready": False}

def generate_drift_nudge(target: str, drift_genre: str) -> str:
    """
    Generates a proactive in-character nudge when the user drifts back to old habits.
    """
    if not client: return f"You're drifting back to {drift_genre}. Stick to the {target} pact!"
    
    system_prompt = f"""
    You are Scout, the user's music co-pilot. They made a pact to explore '{target}'.
    However, you've noticed they are drifting back to their old habit: '{drift_genre}'.
    Write a 1-2 sentence proactive nudge. Be witty, specific, and ask if they want to ease off or recommit.
    Example: "You've played a lot of Pop today — should I ease off the Ambient pact, or are we still in this?"
    """
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}],
            model=MODEL_NAME,
            temperature=0.8,
            max_tokens=100,
        )
        return chat_completion.choices[0].message.content
    except Exception:
        return f"You've played a lot of {drift_genre} today — should I ease off the {target} pact, or are we still in this?"
