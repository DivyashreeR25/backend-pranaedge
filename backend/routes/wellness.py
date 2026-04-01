from fastapi import APIRouter, HTTPException
from db.mongo import profiles_collection, analysis_collection, session_memory_collection
from bson import ObjectId
from datetime import datetime, timedelta

router = APIRouter()


from utils.auth import get_current_user
from fastapi import Depends

@router.get("/wellness-score")
async def get_wellness_score(user_id: str = Depends(get_current_user)):
    # Fetch profile
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Fetch latest analysis
    analysis = await analysis_collection.find_one({"user_id": user_id})

    # --- COMPONENT 1: Sleep Score (0-25 points) ---
    sleep_quality = profile.get("sleep_quality", 5)
    sleep_score = (sleep_quality / 10) * 25

    # --- COMPONENT 2: Stress Score (0-25 points, inverted) ---
    stress_level = profile.get("stress_level", 5)
    stress_score = ((10 - stress_level) / 10) * 25

    # --- COMPONENT 3: Activity Score (0-25 points) ---
    # Based on how many modules used in last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)
    recent_cursor = session_memory_collection.find({
        "user_id": user_id,
        "timestamp": {"$gte": since}
    })
    recent_modules = set()
    async for doc in recent_cursor:
        recent_modules.add(doc.get("module"))

    # Remove checkin from count — only count actual wellness activities
    activity_modules = recent_modules - {"checkin", "analysis"}
    activity_score = min(len(activity_modules) * 8, 25)
    # 1 module = 8pts, 2 = 16pts, 3+ = 25pts (capped)

    # --- COMPONENT 4: Consistency Score (0-25 points) ---
    # Based on total checkins — more consistent = higher score
    total_checkins_cursor = session_memory_collection.find({
        "user_id": user_id,
        "module": "checkin"
    })
    total_checkins = 0
    async for _ in total_checkins_cursor:
        total_checkins += 1

    if total_checkins >= 7:
        consistency_score = 25
    elif total_checkins >= 5:
        consistency_score = 20
    elif total_checkins >= 3:
        consistency_score = 15
    elif total_checkins >= 1:
        consistency_score = 10
    else:
        consistency_score = 0

    # --- TOTAL SCORE ---
    total_score = round(sleep_score + stress_score + activity_score + consistency_score)
    total_score = max(0, min(100, total_score))  # clamp 0-100

    # --- SCORE LABEL ---
    if total_score >= 80:
        label = "Thriving 🌟"
        message = "You're in excellent wellness shape. Keep this momentum going!"
    elif total_score >= 60:
        label = "Progressing 🌱"
        message = "Good progress. A little more consistency will take you far."
    elif total_score >= 40:
        label = "Developing 🌿"
        message = "You're building healthy habits. Small daily steps matter."
    elif total_score >= 20:
        label = "Starting Out 🌸"
        message = "Every journey starts somewhere. You're on the right path."
    else:
        label = "Just Beginning 🌾"
        message = "Welcome! Start with a daily check-in and one yoga session."

    # --- BREAKDOWN ---
    breakdown = {
        "sleep": {
            "score": round(sleep_score),
            "out_of": 25,
            "detail": f"Sleep quality {sleep_quality}/10"
        },
        "stress_management": {
            "score": round(stress_score),
            "out_of": 25,
            "detail": f"Stress level {stress_level}/10 (lower is better)"
        },
        "activity": {
            "score": round(activity_score),
            "out_of": 25,
            "detail": f"{len(activity_modules)} wellness module(s) used today"
                      f" ({', '.join(activity_modules) if activity_modules else 'none yet'})"
        },
        "consistency": {
            "score": round(consistency_score),
            "out_of": 25,
            "detail": f"{total_checkins} total check-in(s) recorded"
        }
    }

    # --- WHAT TO IMPROVE ---
    improvements = []
    if sleep_score < 15:
        improvements.append("Improve sleep quality — try the bedtime meditation module")
    if stress_score < 15:
        improvements.append("Reduce stress — a daily yoga sequence is recommended")
    if activity_score < 15:
        improvements.append("Use more modules today — try yoga or meditation")
    if consistency_score < 15:
        improvements.append("Check in more regularly to build your consistency score")

    return {
        "status": "success",
        "wellness_score": {
            "total": total_score,
            "label": label,
            "message": message,
            "breakdown": breakdown,
            "improvements": improvements,
            "primary_concern": analysis.get("primary_concern", "general wellness")
                               if analysis else "Run /analyze first",
            "calculated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        }
    }