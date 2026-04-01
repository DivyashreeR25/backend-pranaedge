from fastapi import APIRouter, HTTPException, Depends
from models.user import HealthProfile, ProfileResponse, LoginRequest, LoginResponse
from db.mongo import profiles_collection, profile_history_collection
from services.memory import get_trend_summary
from bson import ObjectId
from datetime import datetime

# ✅ NEW IMPORTS
from utils.security import hash_password, verify_password
from utils.jwt_handler import create_token
from utils.auth import get_current_user

router = APIRouter()


@router.post("/profile", response_model=ProfileResponse)
async def create_profile(profile: HealthProfile):
    # Check if email already exists
    if profile.email:
        existing = await profiles_collection.find_one({"email": profile.email})
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already registered. Use POST /login to retrieve your account."
            )

    profile_dict = profile.model_dump()

    # 🔐 HASH PASSWORD BEFORE SAVING
    profile_dict["password"] = hash_password(profile_dict["password"])

    profile_dict["created_at"] = datetime.utcnow()
    result = await profiles_collection.insert_one(profile_dict)
    user_id = str(result.inserted_id)

    # Save to history
    history_entry = profile_dict.copy()
    history_entry["user_id"] = user_id
    history_entry["timestamp"] = datetime.utcnow()
    await profile_history_collection.insert_one(history_entry)

    return ProfileResponse(
        user_id=user_id,
        message="Profile created successfully"
    )


@router.post("/login")
async def login(request: LoginRequest):
    profile = await profiles_collection.find_one({"email": request.email})
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email. Please create a profile first."
        )

    # 🔐 VERIFY PASSWORD
    if not verify_password(request.password, profile["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")

    # 🔐 CREATE JWT TOKEN
    token = create_token({"user_id": str(profile["_id"])})

    return {
        "access_token": token,
        "token_type": "bearer",
        "name": profile["name"]
    }


# 🔐 PROTECTED ROUTE (JWT)
@router.get("/profile")
async def get_profile(user_id: str = Depends(get_current_user)):
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile["_id"] = str(profile["_id"])

        # ❗ REMOVE PASSWORD FROM RESPONSE (IMPORTANT)
        profile.pop("password", None)

        return profile
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🔐 PROTECTED ROUTE (JWT)
@router.put("/profile")
async def update_profile(
    profile: HealthProfile,
    user_id: str = Depends(get_current_user)
):
    try:
        profile_dict = profile.model_dump()

        # 🔐 HASH PASSWORD AGAIN IF UPDATED
        profile_dict["password"] = hash_password(profile_dict["password"])

        profile_dict["updated_at"] = datetime.utcnow()

        result = await profiles_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": profile_dict}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")

        history_entry = profile_dict.copy()
        history_entry["user_id"] = user_id
        history_entry["timestamp"] = datetime.utcnow()
        await profile_history_collection.insert_one(history_entry)

        from routes.analyze import run_analysis
        analysis = await run_analysis(user_id)

        return {
            "message": "Profile updated and re-analyzed successfully",
            "user_id": user_id,
            "new_analysis_summary": {
                "primary_concern": analysis.get("primary_concern"),
                "meditation_type": analysis.get("meditation_type"),
                "wellness_insight": analysis.get("wellness_insight")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🔐 PROTECTED ROUTE (JWT)
@router.get("/profile/history")
async def get_profile_history(user_id: str = Depends(get_current_user)):
    trend = await get_trend_summary(user_id)
    cursor = profile_history_collection.find(
        {"user_id": user_id}
    ).sort("timestamp", -1)

    history = []
    async for doc in cursor:
        doc.pop("_id", None)
        if "timestamp" in doc and not isinstance(doc["timestamp"], str):
            doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M")

        # ❗ REMOVE PASSWORD FROM HISTORY ALSO
        doc.pop("password", None)

        history.append(doc)

    return {
        "user_id": user_id,
        "total_entries": len(history),
        "trends": trend,
        "history": history
    }