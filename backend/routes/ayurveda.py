from fastapi import APIRouter, HTTPException, Depends
from db.mongo import profiles_collection, analysis_collection
from services.rag import retrieve_ayurveda_context, generate_with_hf
from bson import ObjectId
import json

from utils.auth import get_current_user

router = APIRouter()


# 🌿 Ayurveda Insights
@router.get("/ayurveda")
async def get_ayurveda_insights(user_id: str = Depends(get_current_user)):
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis = await analysis_collection.find_one({"user_id": user_id})

    # 🔍 Build RAG query
    rag_query = f"""
    {profile.get('fitness_goal')} 
    {' '.join(profile.get('health_conditions', []))}
    stress sleep anxiety wellness
    """

    # 📚 Retrieve context
    ayurveda_context = retrieve_ayurveda_context(rag_query)

    # 🧠 Prompt
    prompt = f"""
You are an expert Ayurvedic wellness advisor.

USER PROFILE:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Goal: {profile.get('fitness_goal')}
- Health conditions: {', '.join(profile.get('health_conditions', []))}
- Sleep quality: {profile.get('sleep_quality')}/10
- Stress level: {profile.get('stress_level')}/10
- Primary concern: {analysis.get('primary_concern', 'general wellness') if analysis else 'general wellness'}

AYURVEDIC CONTEXT:
{ayurveda_context}

Respond ONLY in JSON:

{{
  "likely_dosha_imbalance": "...",
  "ayurvedic_insight": "...",
  "recommended_herbs": [],
  "dietary_recommendations": [],
  "foods_to_avoid": [],
  "daily_routine": {{
    "morning": "",
    "afternoon": "",
    "evening": ""
  }},
  "pranayama": {{
    "name": "",
    "instruction": "",
    "duration": ""
  }},
  "seasonal_tip": ""
}}
"""

    try:
        raw = generate_with_hf(prompt)

        # 🔥 SAFE JSON PARSING
        cleaned = raw.strip()

        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]

        result = json.loads(cleaned.strip())

    except Exception as e:
        print("❌ Ayurveda Parsing Error:", raw)
        raise HTTPException(status_code=500, detail="AI response parsing failed")

    return {
        "status": "success",
        "ayurveda": result,
        "note": "Generated using HF + Ayurveda knowledge base"
    }


# 🌿 Dosha Quiz
@router.get("/ayurveda/dosha-quiz")
async def dosha_assessment(user_id: str = Depends(get_current_user)):
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    dosha_context = retrieve_ayurveda_context("vata pitta kapha dosha")

    prompt = f"""
You are an Ayurvedic doctor.

User:
- Goal: {profile.get('fitness_goal')}
- Conditions: {', '.join(profile.get('health_conditions', []))}
- Sleep: {profile.get('sleep_quality')}/10
- Stress: {profile.get('stress_level')}/10

Context:
{dosha_context}

Respond ONLY JSON:

{{
  "primary_dosha": "",
  "secondary_dosha": "",
  "why": "",
  "top_3_recommendations": []
}}
"""

    try:
        raw = generate_with_hf(prompt)

        cleaned = raw.strip()

        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]

        result = json.loads(cleaned.strip())

    except Exception as e:
        print("❌ Dosha Parsing Error:", raw)
        raise HTTPException(status_code=500, detail="AI response parsing failed")

    return {
        "status": "success",
        "dosha_assessment": result
    }
