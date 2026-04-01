from fastapi import APIRouter, HTTPException
from backend.db.mongo import profiles_collection, analysis_collection
from backend.services.groq_client import call_groq
from backend.services.rag import retrieve_ayurveda_context
from bson import ObjectId
import json

router = APIRouter()


from backend.utils.auth import get_current_user
from fastapi import Depends

@router.get("/ayurveda")
async def get_ayurveda_insights(user_id: str = Depends(get_current_user)):
    """Get personalized Ayurvedic recommendations using RAG."""
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis = await analysis_collection.find_one({"user_id": user_id})

    # Build RAG query from user profile
    rag_query = f"""
    {profile.get('fitness_goal')} 
    {' '.join(profile.get('health_conditions', []))}
    stress sleep anxiety wellness
    """

    # Retrieve relevant Ayurveda knowledge
    ayurveda_context = retrieve_ayurveda_context(rag_query, k=4)

    prompt = f"""
You are an expert Ayurvedic wellness advisor for PranaEdge.

USER PROFILE:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Goal: {profile.get('fitness_goal')}
- Health conditions: {', '.join(profile.get('health_conditions', []))}
- Sleep quality: {profile.get('sleep_quality')}/10
- Stress level: {profile.get('stress_level')}/10
- Primary concern: {analysis.get('primary_concern', 'general wellness') if analysis else 'general wellness'}

RELEVANT AYURVEDIC KNOWLEDGE (use this to ground your response):
{ayurveda_context}

Based on this user's profile AND the Ayurvedic knowledge above, provide 
deeply personalized Ayurvedic insights. Respond ONLY with valid JSON:
{{
  "likely_dosha_imbalance": "Vata / Pitta / Kapha or combination — explain why",
  "ayurvedic_insight": "2-3 sentences connecting their symptoms to Ayurvedic principles",
  "recommended_herbs": [
    {{"herb": "herb name", "benefit": "specific benefit for this user", "how_to_use": "practical usage"}}
  ],
  "dietary_recommendations": [
    {{"food": "food name", "reason": "why this helps this specific user"}}
  ],
  "foods_to_avoid": [
    {{"food": "food name", "reason": "why this worsens their condition"}}
  ],
  "daily_routine": {{
    "morning": "Ayurvedic morning routine for this user",
    "afternoon": "midday practice",
    "evening": "evening wind-down routine"
  }},
  "pranayama": {{
    "name": "recommended breathing technique",
    "instruction": "how to practice",
    "duration": "how long"
  }},
  "seasonal_tip": "one Ayurvedic seasonal tip relevant to current conditions"
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

    return {
        "status": "success",
        "ayurveda": result,
        "knowledge_sources": len(ayurveda_context.split("\n\n")),
        "note": "Recommendations grounded in Ayurvedic knowledge base via RAG"
    }


@router.get("/ayurveda/dosha-quiz")
async def dosha_assessment(user_id: str = Depends(get_current_user)):
    """Quick dosha assessment based on user profile."""
    try:
        profile = await profiles_collection.find_one({"_id": ObjectId(user_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Retrieve dosha knowledge
    dosha_context = retrieve_ayurveda_context("vata pitta kapha dosha", k=3)

    prompt = f"""
You are an Ayurvedic practitioner assessing a user's dosha type.

User profile:
- Goal: {profile.get('fitness_goal')}
- Health conditions: {', '.join(profile.get('health_conditions', []))}
- Sleep: {profile.get('sleep_quality')}/10
- Stress: {profile.get('stress_level')}/10

Ayurvedic dosha knowledge:
{dosha_context}

Assess their dosha and respond ONLY with valid JSON:
{{
  "primary_dosha": "Vata / Pitta / Kapha",
  "secondary_dosha": "Vata / Pitta / Kapha or None",
  "dosha_percentage": {{"vata": 0, "pitta": 0, "kapha": 0}},
  "why": "2 sentences explaining why based on their symptoms",
  "key_imbalances": ["imbalance 1", "imbalance 2", "imbalance 3"],
  "top_3_recommendations": [
    "recommendation 1",
    "recommendation 2", 
    "recommendation 3"
  ]
}}
"""

    try:
        raw = call_groq(prompt, max_tokens=800)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        result = json.loads(cleaned.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "success",
        "dosha_assessment": result
    }