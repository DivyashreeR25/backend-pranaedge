from fastapi import APIRouter, HTTPException
from db.mongo import analysis_collection, daily_summary_collection
from services.groq_client import call_groq
from services.memory import load_past_sessions, get_trend_summary
from datetime import datetime
import json

router = APIRouter()


from utils.auth import get_current_user
from fastapi import Depends

@router.get("/summary")
async def get_daily_summary(user_id: str = Depends(get_current_user)):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Run POST /analyze/{user_id} first")

    # Load recent activity across all modules
    yoga_sessions = await load_past_sessions(user_id, module="yoga", limit=2)
    meditation_sessions = await load_past_sessions(user_id, module="meditation", limit=2)
    diet_sessions = await load_past_sessions(user_id, module="diet", limit=3)
    trends = await get_trend_summary(user_id)

    # Build context
    yoga_context = ", ".join([
        s.get("user_input", {}).get("pose_name", "sequence")
        for s in yoga_sessions
    ]) or "No yoga logged today"

    meditation_context = ", ".join([
        s.get("ai_output", {}).get("session_title", "session")
        for s in meditation_sessions
    ]) or "No meditation logged today"

    diet_scores = [
        s.get("ai_output", {}).get("alignment_score", "")
        for s in diet_sessions
    ]
    diet_context = f"{len(diet_sessions)} meals logged. Scores: {', '.join(diet_scores)}" \
                   if diet_sessions else "No meals logged today"

    prompt = f"""
You are PranaEdge, generating a personalized daily wellness digest.

Today's activity:
- Yoga: {yoga_context}
- Meditation: {meditation_context}
- Diet: {diet_context}
- Current primary concern: {analysis.get('primary_concern')}
- Stress trend: {trends.get('stress_trend', 'unknown')}
- Sleep trend: {trends.get('sleep_trend', 'unknown')}
- Wellness insight: {analysis.get('wellness_insight')}

Generate a warm, encouraging daily summary. Respond ONLY with valid JSON:
{{
  "date": "{datetime.utcnow().strftime('%B %d, %Y')}",
  "greeting": "personalized warm greeting based on their state",
  "today_snapshot": {{
    "yoga": "one line summary of yoga activity",
    "meditation": "one line summary of meditation activity",
    "diet": "one line summary of diet activity"
  }},
  "top_win": "the best thing they did for their wellness today",
  "focus_for_tomorrow": "one specific actionable suggestion for tomorrow",
  "trend_message": "encouraging message about their progress trend",
  "closing_affirmation": "warm closing thought"
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

    # Store summary
    result["user_id"] = user_id
    result["generated_at"] = datetime.utcnow()
    await daily_summary_collection.insert_one(result)
    result.pop("_id", None)
    result["generated_at"] = str(result["generated_at"])

    return {"status": "success", "summary": result}