from fastapi import APIRouter, HTTPException
from db.mongo import profiles_collection
from services.groq_client import call_groq
from bson import ObjectId
from utils.auth import get_current_user
from fastapi import Depends

router = APIRouter()

@router.get("/affirmation")
async def get_affirmation(user_id: str = Depends(get_current_user)):
    """
    Generate a personalized affirmation based on user's profile.
    Uses minimal LLM call (Oxlo).
    """

    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Extract useful fields (adjust based on your schema)
    stress = profile.get("stress_level", "moderate")
    sleep = profile.get("sleep_quality", "average")
    goal = profile.get("goal", "wellness")
    mood = profile.get("mood", "neutral")

    # Prompt for LLM
    prompt = f"""
    You are an Ayurveda wellness coach.

    Based on the user's current state:
    - Stress Level: {stress}
    - Sleep Quality: {sleep}
    - Mood: {mood}
    - Goal: {goal}

    Generate ONE short, powerful, positive affirmation (1-2 lines max).
    It should feel calming, grounding, and motivating.

    Do NOT explain anything. Only return the affirmation.
    """

    try:
        response = call_groq(prompt)

        return {
            "status": "success",
            "affirmation": response.strip()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")