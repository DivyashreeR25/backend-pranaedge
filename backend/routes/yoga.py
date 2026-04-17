from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.mongo import analysis_collection
from services.groq_client import call_groq
from services.memory import load_past_sessions, save_interaction
import json

router = APIRouter()


class YogaRequest(BaseModel):
    pose_name: str


from utils.auth import get_current_user
from fastapi import Depends

@router.post("/yoga")
async def get_yoga_guidance(
    request: YogaRequest,
    user_id: str = Depends(get_current_user)
):
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Run POST /analyze/{user_id} first")

    past_yoga = await load_past_sessions(user_id, module="yoga", limit=3)
    poses_to_avoid = [p["pose"] for p in analysis.get("poses_to_avoid", [])]

    past_context = ""
    if past_yoga:
        past_context = "\nPAST YOGA SESSIONS:\n"
        for s in past_yoga:
            pose = s.get("user_input", {}).get("pose_name", "unknown")
            past_context += f"- Previously practiced: {pose}\n"

    is_risky = any(request.pose_name.lower() in p.lower() for p in poses_to_avoid)

    prompt = f"""
You are a professional yoga instructor with memory of this user's practice history.

User context:
- Primary concern: {analysis.get('primary_concern')}
- Poses to avoid: {', '.join(poses_to_avoid)}
- Requested pose: {request.pose_name}
- Is risky for user: {is_risky}
{past_context}

{"⚠️ This pose is flagged risky. Give strong warning and suggest safer alternative." if is_risky else "This pose is safe. Build on their past practice if history exists."}

Respond ONLY with valid JSON, no extra text:
{{
  "pose_name": "{request.pose_name}",
  "is_safe_for_user": {str(not is_risky).lower()},
  "safety_note": "specific to this user's conditions",
  "progress_note": "how this builds on their past practice or 'First time' if new",
  "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
  "common_mistakes": ["mistake 1", "mistake 2", "mistake 3"],
  "corrections": ["correction 1", "correction 2", "correction 3"],
  "hold_duration": "e.g. 30 seconds or 5 breaths",
  "safer_alternative": "alternative pose name if risky, else null"
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
        module="yoga",
        user_input={"pose_name": request.pose_name},
        ai_output=result
    )

    return {"status": "success", "guidance": result}


@router.get("/yoga/sequence")
async def get_yoga_sequence(user_id: str = Depends(get_current_user)):
    """Generate a full personalized 5-6 pose sequence."""
    analysis = await analysis_collection.find_one({"user_id": user_id})
    if not analysis:
        raise HTTPException(status_code=404, detail="Run POST /analyze/{user_id} first")

    past_yoga = await load_past_sessions(user_id, module="yoga", limit=5)
    recommended = [
    p.get("pose")
    for p in analysis.get("recommended_yoga_poses", [])
    if p.get("pose")
]

    poses_to_avoid = [
    p.get("pose")
    for p in analysis.get("poses_to_avoid", [])
    if p.get("pose")
]
    past_poses = [
    str(s.get("user_input", {}).get("pose_name"))
    for s in past_yoga
    if s.get("user_input", {}).get("pose_name") is not None
]

    past_context = (
    f"Previously practiced: {', '.join(past_poses)}"
    if past_poses else "No past practice recorded")
    
    prompt = f"""
You are a professional yoga instructor designing a complete session.

User context:
- Primary concern: {analysis.get('primary_concern')}
- Recommended poses: {', '.join(recommended)}
- Poses to avoid: {', '.join(poses_to_avoid)}
- Past practice: {past_context}
- Meditation type suggested: {analysis.get('meditation_type')}

Design a complete 20-minute yoga sequence of 5-6 poses that flows naturally,
builds progressively, avoids risky poses, and suits this user's current state.

Respond ONLY with valid JSON, no extra text:
{{
  "session_title": "descriptive title e.g. Morning Calm Flow for Stress Relief",
  "total_duration": "20 minutes",
  "sequence": [
    {{
      "order": 1,
      "pose_name": "pose name",
      "duration": "e.g. 2 minutes",
      "instruction": "brief key instruction",
      "transition": "how to move into next pose"
    }}
  ],
  "session_note": "overall note about why this sequence suits this user today",
  "builds_on_past": "how this session builds on their history or 'Fresh start' if new"
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
        module="yoga",
        user_input={"type": "full_sequence"},
        ai_output=result
    )

    return {"status": "success", "sequence": result}
