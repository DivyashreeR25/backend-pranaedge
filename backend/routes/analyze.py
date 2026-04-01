from fastapi import APIRouter, HTTPException
from backend.db.mongo import profiles_collection, analysis_collection
from backend.services.groq_client import call_groq
from backend.services.memory import load_past_sessions, save_interaction, get_trend_summary
from bson import ObjectId
import json

router = APIRouter()

from backend.utils.auth import get_current_user
from fastapi import Depends

async def run_analysis(user_id: str = Depends(get_current_user)):
    """Core analysis logic — callable from other routes too."""
    profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Load past analysis sessions for context
    past_sessions = await load_past_sessions(user_id, module="analysis", limit=3)
    trends = await get_trend_summary(user_id)

    # Build history context string
    history_context = ""
    if past_sessions:
        history_context = "\nPAST SESSION CONTEXT:\n"
        for s in past_sessions:
            ts = s.get("timestamp", "unknown time")
            concern = s.get("ai_output", {}).get("primary_concern", "unknown")
            insight = s.get("ai_output", {}).get("wellness_insight", "")
            history_context += f"- [{ts}] Concern: {concern}. Insight: {insight}\n"

    trend_context = ""
    if trends.get("stress_trend") and trends.get("stress_trend") != "insufficient data":
        trend_context = f"""
TREND ANALYSIS (last {len(trends['entries'])} check-ins):
- Stress trend: {trends['stress_trend']}
- Sleep trend: {trends['sleep_trend']}
"""

    prompt = f"""
You are PranaEdge, an expert AI wellness advisor with memory of this user's journey.

USER PROFILE:
- Name: {profile['name']}
- Age: {profile['age']}
- Weight: {profile['weight']} kg
- Fitness Goal: {profile['fitness_goal']}
- Health Conditions: {', '.join(profile['health_conditions'])}
- Sleep Quality: {profile['sleep_quality']}/10
- Stress Level: {profile['stress_level']}/10
{history_context}
{trend_context}

REASONING STEPS:
Step 1 - Compare current state with past sessions. Has anything improved or worsened?
Step 2 - Identify the user's primary concern right now.
Step 3 - Identify conflicts or risks given their conditions.
Step 4 - Generate personalized recommendations that build on past sessions.
Step 5 - Note any meaningful trend patterns worth highlighting.

Respond ONLY with valid JSON, no extra text:
{{
  "primary_concern": "string",
  "progress_note": "string - how user has changed since last session, or 'First session' if new",
  "recommended_yoga_poses": [
    {{"pose": "name", "reason": "why this suits this user right now"}}
  ],
  "poses_to_avoid": [
    {{"pose": "name", "reason": "why risky for this user"}}
  ],
  "meditation_type": "calming or energizing or focus or grief-relief",
  "meditation_focus": "string",
  "diet_guidance": "string",
  "foods_to_prefer": ["food1", "food2", "food3"],
  "foods_to_avoid": ["food1", "food2", "food3"],
  "wellness_insight": "string - key pattern connecting stress, sleep, goal",
  "trend_observation": "string - what the data trend shows over time",
  "mindmap_connections": [
    {{"from": "node1", "to": "node2", "label": "relationship"}}
  ]
}}
"""

    raw = call_groq(prompt)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    analysis = json.loads(cleaned.strip())

    # Store analysis
    analysis["user_id"] = user_id
    await analysis_collection.delete_many({"user_id": user_id})
    await analysis_collection.insert_one(analysis)
    analysis.pop("_id", None)

    # Save to session memory
    await save_interaction(
        user_id=user_id,
        module="analysis",
        user_input={"stress": profile["stress_level"], "sleep": profile["sleep_quality"]},
        ai_output=analysis
    )

    return analysis


@router.post("/analyze")
async def analyze_profile(user_id: str = Depends(get_current_user)):
    try:
        analysis = await run_analysis(user_id)
        return {"status": "success", "analysis": analysis}
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI returned malformed JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze")
async def get_analysis(user_id: str = Depends(get_current_user)):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found.")
    analysis.pop("_id", None)
    return {"status": "success", "analysis": analysis}