from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.mongo import analysis_collection
from services.groq_client import call_groq
from services.memory import load_past_sessions, save_interaction
import json

router = APIRouter()


class DietRequest(BaseModel):
    meal_description: str
    meal_type: str


from utils.auth import get_current_user
from fastapi import Depends

@router.post("/diet")
async def analyze_meal(
    request: DietRequest,
    user_id: str = Depends(get_current_user)
):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Run POST /analyze/{user_id} first")

    past_meals = await load_past_sessions(user_id, module="diet", limit=3)

    past_context = ""
    if past_meals:
        past_context = "\nPAST MEALS LOGGED:\n"
        for s in past_meals:
            meal = s.get("user_input", {}).get("meal_description", "unknown")
            score = s.get("ai_output", {}).get("alignment_score", "unknown")
            past_context += f"- {meal} → Alignment: {score}\n"

    prompt = f"""
You are a certified nutritionist with memory of this user's eating patterns.

User context:
- Primary concern: {analysis.get('primary_concern')}
- Dietary direction: {analysis.get('diet_guidance')}
- Foods to prefer: {', '.join(analysis.get('foods_to_prefer', []))}
- Foods to avoid: {', '.join(analysis.get('foods_to_avoid', []))}
- Meal type: {request.meal_type}
- Current meal: {request.meal_description}
{past_context}

Analyze with awareness of their eating history if available.

Respond ONLY with valid JSON, no extra text:
{{
  "meal_type": "{request.meal_type}",
  "meal_described": "{request.meal_description}",
  "estimated_calories": "e.g. 450-500 kcal",
  "alignment_score": "Good / Moderate / Poor",
  "alignment_reason": "why this does or doesn't align with goal",
  "pattern_note": "observation about their eating pattern over time, or 'First meal logged'",
  "positive_aspects": ["aspect 1", "aspect 2"],
  "improvements": ["suggestion 1", "suggestion 2"],
  "better_alternative": "simple swap that would improve this meal",
  "hydration_tip": "water or drink tip relevant to their concern"
}}
"""

    try:
        raw = call_groq(prompt)
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
        module="diet",
        user_input={"meal_description": request.meal_description, "meal_type": request.meal_type},
        ai_output=result
    )

    return {"status": "success", "meal_analysis": result}