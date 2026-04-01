from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.db.mongo import analysis_collection
from backend.services.groq_client import call_groq
from backend.services.memory import load_past_sessions, save_interaction
import json

router = APIRouter()


class MeditationRequest(BaseModel):
    current_mood: str
    duration_minutes: int

from backend.utils.auth import get_current_user
from fastapi import Depends

@router.post("/meditation")
async def generate_meditation(
    request: MeditationRequest,
    user_id: str = Depends(get_current_user)
):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Run POST /analyze/{user_id} first")

    past_sessions = await load_past_sessions(user_id, module="meditation", limit=3)

    past_context = ""
    if past_sessions:
        past_context = "\nPAST MEDITATION SESSIONS:\n"
        for s in past_sessions:
            mood = s.get("user_input", {}).get("current_mood", "unknown")
            title = s.get("ai_output", {}).get("session_title", "unknown session")
            past_context += f"- Mood: {mood} → Session: {title}\n"

    prompt = f"""
You are a mindfulness coach with memory of this user's meditation journey.

User context:
- Primary concern: {analysis.get('primary_concern')}
- Recommended meditation type: {analysis.get('meditation_type')}
- Focus area: {analysis.get('meditation_focus')}
- Current mood: {request.current_mood}
- Requested duration: {request.duration_minutes} minutes
{past_context}

Generate a personalized session that acknowledges their journey if past sessions exist.

Respond ONLY with valid JSON, no extra text:
{{
  "session_title": "descriptive title",
  "meditation_type": "{analysis.get('meditation_type')}",
  "duration_minutes": {request.duration_minutes},
  "mood_note": "acknowledge current mood and how this session addresses it",
  "progress_note": "how this builds on past sessions or 'Welcome to your first session'",
  "opening": "2-3 sentences to settle the user",
  "breathing_exercise": {{
    "name": "e.g. 4-7-8 breathing",
    "instruction": "step by step",
    "rounds": 3
  }},
  "main_script": "full meditation script 150-200 words, warm and calming",
  "closing": "2-3 sentences to bring user back gently",
  "affirmation": "one powerful closing affirmation personalized to their concern"
}}
"""

    try:
        raw = call_groq(prompt, max_tokens=2000)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        result = json.loads(cleaned.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    await save_interaction(
        user_id=user_id,
        module="meditation",
        user_input={"current_mood": request.current_mood, "duration": request.duration_minutes},
        ai_output=result
    )

    return {"status": "success", "session": result}