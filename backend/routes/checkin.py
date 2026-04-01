from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.mongo import profiles_collection, session_memory_collection
from services.memory import save_interaction
from bson import ObjectId
from datetime import datetime

router = APIRouter()


class CheckinRequest(BaseModel):
    mood: str          # e.g. "anxious", "calm", "tired", "happy"
    energy_level: int  # 1-10
    stress_level: int  # 1-10


from utils.auth import get_current_user
from fastapi import Depends

@router.post("/checkin")
async def daily_checkin(
    request: CheckinRequest,
    user_id: str = Depends(get_current_user)
):
    # Verify user exists
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    checkin_data = {
        "user_id": user_id,
        "mood": request.mood,
        "energy_level": request.energy_level,
        "stress_level": request.stress_level,
        "timestamp": datetime.utcnow()
    }

    # Save to session memory collection
    await save_interaction(
        user_id=user_id,
        module="checkin",
        user_input={
            "mood": request.mood,
            "energy_level": request.energy_level,
            "stress_level": request.stress_level
        },
        ai_output={"recorded": True}
    )

    # Auto-update stress in profile if significantly different
    current_stress = profile.get("stress_level", 5)
    if abs(request.stress_level - current_stress) >= 2:
        await profiles_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "stress_level": request.stress_level,
                "updated_at": datetime.utcnow()
            }}
        )
        stress_updated = True
    else:
        stress_updated = False

    # Load past checkins for pattern detection
    past_checkins = []
    cursor = session_memory_collection.find(
        {"user_id": user_id, "module": "checkin"}
    ).sort("timestamp", -1).limit(5)
    async for doc in cursor:
        past_checkins.append(doc.get("user_input", {}))

    # Detect mood pattern
    if len(past_checkins) >= 3:
        moods = [c.get("mood", "") for c in past_checkins]
        stress_levels = [c.get("stress_level", 5) for c in past_checkins]
        avg_stress = sum(stress_levels) / len(stress_levels)

        if avg_stress >= 7:
            pattern = "Your stress has been consistently high. Consider a longer meditation session today."
        elif avg_stress <= 4:
            pattern = "You've been managing stress well lately. Keep it up!"
        else:
            pattern = "Your stress levels are moderate. Small daily practices will help."
    else:
        pattern = "Keep checking in daily — patterns will emerge after a few days."

    # Quick recommendation based on current state
    if request.energy_level <= 3:
        quick_tip = "Low energy detected. Try Child's Pose + 5 min calming meditation."
    elif request.stress_level >= 7:
        quick_tip = "High stress detected. Legs Up The Wall pose + box breathing recommended."
    elif request.mood in ["sad", "anxious", "overwhelmed"]:
        quick_tip = "Try a 10-minute guided meditation focusing on breath awareness."
    else:
        quick_tip = "You're doing well. A light yoga flow will keep the momentum going."

    return {
        "status": "success",
        "checkin": {
            "recorded_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "mood": request.mood,
            "energy_level": request.energy_level,
            "stress_level": request.stress_level,
            "stress_profile_updated": stress_updated,
            "pattern_observation": pattern,
            "quick_tip": quick_tip,
            "total_checkins": len(past_checkins) + 1
        }
    }


@router.get("/checkin/history")
async def get_checkin_history(user_id: str = Depends(get_current_user)):
    """Return all past checkins for trend visualization."""
    cursor = session_memory_collection.find(
        {"user_id": user_id, "module": "checkin"}
    ).sort("timestamp", -1).limit(30)  # last 30 checkins

    checkins = []
    async for doc in cursor:
        entry = doc.get("user_input", {})
        entry["timestamp"] = doc.get("timestamp").strftime("%Y-%m-%d %H:%M") \
            if doc.get("timestamp") else "unknown"
        checkins.append(entry)

    if not checkins:
        return {"user_id": user_id, "checkins": [], "message": "No checkins yet"}

    # Calculate averages for graph data
    avg_stress = sum(c.get("stress_level", 0) for c in checkins) / len(checkins)
    avg_energy = sum(c.get("energy_level", 0) for c in checkins) / len(checkins)
    mood_list = [c.get("mood") for c in checkins]
    most_common_mood = max(set(mood_list), key=mood_list.count)

    return {
        "user_id": user_id,
        "total_checkins": len(checkins),
        "averages": {
            "avg_stress": round(avg_stress, 1),
            "avg_energy": round(avg_energy, 1),
            "most_common_mood": most_common_mood
        },
        "checkins": checkins  # frontend feeds this to Recharts
    }