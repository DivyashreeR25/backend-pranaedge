from fastapi import APIRouter, HTTPException
from backend.db.mongo import (
    profiles_collection,
    analysis_collection,
    session_memory_collection,
    profile_history_collection
)
from backend.services.groq_client import call_groq
from bson import ObjectId
from datetime import datetime, timedelta
import json

router = APIRouter()


from backend.utils.auth import get_current_user
from fastapi import Depends

@router.get("/report/weekly")
async def get_weekly_report(user_id: str = Depends(get_current_user)):
    # Verify user
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis = await analysis_collection.find_one({"user_id": user_id})
    since = datetime.utcnow() - timedelta(days=7)

    # --- Collect this week's activity ---
    all_sessions = []
    cursor = session_memory_collection.find({
        "user_id": user_id,
        "timestamp": {"$gte": since}
    }).sort("timestamp", -1)
    async for doc in cursor:
        all_sessions.append(doc)

    # Separate by module
    checkins = [s for s in all_sessions if s.get("module") == "checkin"]
    yoga_sessions = [s for s in all_sessions if s.get("module") == "yoga"]
    meditation_sessions = [s for s in all_sessions if s.get("module") == "meditation"]
    diet_sessions = [s for s in all_sessions if s.get("module") == "diet"]

    # --- Checkin trends ---
    stress_values = [
        s.get("user_input", {}).get("stress_level", 0)
        for s in checkins
    ]
    energy_values = [
        s.get("user_input", {}).get("energy_level", 0)
        for s in checkins
    ]
    moods = [
        s.get("user_input", {}).get("mood", "")
        for s in checkins
    ]

    avg_stress = round(sum(stress_values) / len(stress_values), 1) if stress_values else None
    avg_energy = round(sum(energy_values) / len(energy_values), 1) if energy_values else None
    dominant_mood = max(set(moods), key=moods.count) if moods else "not recorded"

    # Stress trend direction
    if len(stress_values) >= 2:
        stress_direction = (
            "improving ↓" if stress_values[0] < stress_values[-1]
            else "worsening ↑" if stress_values[0] > stress_values[-1]
            else "stable →"
        )
    else:
        stress_direction = "insufficient data"

    # --- Diet alignment ---
    diet_scores = [
        s.get("ai_output", {}).get("alignment_score", "")
        for s in diet_sessions
    ]
    good_meals = diet_scores.count("Good")
    moderate_meals = diet_scores.count("Moderate")
    poor_meals = diet_scores.count("Poor")

    # --- Yoga poses practiced ---
    yoga_poses = [
        s.get("user_input", {}).get("pose_name", "sequence")
        for s in yoga_sessions
    ]

    # --- Meditation sessions ---
    meditation_titles = [
        s.get("ai_output", {}).get("session_title", "session")
        for s in meditation_sessions
    ]

    # --- Profile history this week ---
    history_cursor = profile_history_collection.find({
        "user_id": user_id,
        "timestamp": {"$gte": since}
    }).sort("timestamp", 1)

    profile_changes = []
    async for doc in history_cursor:
        profile_changes.append({
            "stress_level": doc.get("stress_level"),
            "sleep_quality": doc.get("sleep_quality"),
            "timestamp": doc.get("timestamp").strftime("%Y-%m-%d")
            if doc.get("timestamp") else "unknown"
        })

    # --- Build summary stats ---
    weekly_stats = {
        "checkins": len(checkins),
        "yoga_sessions": len(yoga_sessions),
        "meditation_sessions": len(meditation_sessions),
        "meals_logged": len(diet_sessions),
        "avg_stress": avg_stress,
        "avg_energy": avg_energy,
        "dominant_mood": dominant_mood,
        "stress_direction": stress_direction,
        "diet_breakdown": {
            "good": good_meals,
            "moderate": moderate_meals,
            "poor": poor_meals
        },
        "yoga_poses_practiced": yoga_poses,
        "meditation_sessions_list": meditation_titles,
        "profile_changes": profile_changes
    }

    # --- Generate AI narrative ---
    prompt = f"""
You are PranaEdge generating a warm, insightful weekly wellness report.

User: {profile.get('name')}
Goal: {profile.get('fitness_goal')}
Primary concern: {analysis.get('primary_concern', 'general wellness') if analysis else 'general wellness'}

This week's data:
- Check-ins: {len(checkins)}
- Yoga sessions: {len(yoga_sessions)} ({', '.join(yoga_poses) if yoga_poses else 'none'})
- Meditation sessions: {len(meditation_sessions)}
- Meals logged: {len(diet_sessions)} (Good: {good_meals}, Moderate: {moderate_meals}, Poor: {poor_meals})
- Average stress: {avg_stress}/10
- Average energy: {avg_energy}/10
- Dominant mood: {dominant_mood}
- Stress trend: {stress_direction}

Write a personalized weekly report in this exact JSON format, no extra text:
{{
  "headline": "5-7 word punchy headline for their week e.g. 'A Week of Steady, Mindful Progress'",
  "week_summary": "2-3 warm sentences summarizing their week overall",
  "biggest_win": "the single most impressive thing they did this week",
  "biggest_challenge": "the area that needs most attention next week",
  "yoga_insight": "one sentence about their yoga practice this week",
  "meditation_insight": "one sentence about their meditation practice",
  "diet_insight": "one sentence about their eating patterns",
  "stress_insight": "one sentence interpreting their stress trend",
  "next_week_focus": [
    "specific goal 1 for next week",
    "specific goal 2 for next week",
    "specific goal 3 for next week"
  ],
  "motivational_close": "one powerful closing sentence personalized to their goal"
}}
"""

    try:
        raw = call_groq(prompt, max_tokens=1500)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        narrative = json.loads(cleaned.strip())
    except Exception:
        narrative = {
            "headline": "Your Wellness Journey This Week",
            "week_summary": f"{profile.get('name')} made efforts toward their wellness goals this week.",
            "biggest_win": f"Completed {len(yoga_sessions) + len(meditation_sessions)} wellness sessions",
            "biggest_challenge": "Building more consistency across all modules",
            "yoga_insight": f"Practiced {len(yoga_sessions)} yoga session(s) this week.",
            "meditation_insight": f"Completed {len(meditation_sessions)} meditation session(s).",
            "diet_insight": f"Logged {len(diet_sessions)} meal(s) with {good_meals} good alignment.",
            "stress_insight": f"Stress trend is {stress_direction}.",
            "next_week_focus": [
                "Complete a daily check-in",
                "Try one new yoga pose",
                "Log at least 2 meals per day"
            ],
            "motivational_close": "Every step forward counts. Keep going."
        }

    return {
        "status": "success",
        "report": {
            "period": f"{(datetime.utcnow() - timedelta(days=7)).strftime('%b %d')} — {datetime.utcnow().strftime('%b %d, %Y')}",
            "generated_for": profile.get("name"),
            "narrative": narrative,
            "stats": weekly_stats,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }
    }