from langchain_community.chat_message_histories import ChatMessageHistory
from backend.db.mongo import session_memory_collection, profile_history_collection
from datetime import datetime

# In-memory store: one history object per user
_memory_store: dict = {}


def get_memory(user_id: str) -> ChatMessageHistory:
    if user_id not in _memory_store:
        _memory_store[user_id] = ChatMessageHistory()
    return _memory_store[user_id]


async def save_interaction(
    user_id: str,
    module: str,
    user_input: dict,
    ai_output: dict
):
    record = {
        "user_id": user_id,
        "module": module,
        "user_input": user_input,
        "ai_output": ai_output,
        "timestamp": datetime.utcnow()
    }
    await session_memory_collection.insert_one(record)

    # Add to in-memory LangChain buffer — correct API for new LangChain
    memory = get_memory(user_id)
    memory.add_user_message(f"[{module.upper()}] {str(user_input)}")
    memory.add_ai_message(f"[{module.upper()} RESPONSE] {str(ai_output)}")


async def load_past_sessions(
    user_id: str,
    module: str = None,
    limit: int = 3
) -> list:
    query = {"user_id": user_id}
    if module:
        query["module"] = module

    cursor = session_memory_collection.find(query).sort(
        "timestamp", -1
    ).limit(limit)

    sessions = []
    async for doc in cursor:
        doc.pop("_id", None)
        if "timestamp" in doc:
            doc["timestamp"] = doc["timestamp"].strftime("%Y-%m-%d %H:%M")
        sessions.append(doc)

    return list(reversed(sessions))


async def get_trend_summary(user_id: str) -> dict:
    cursor = profile_history_collection.find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(7)

    history = []
    async for doc in cursor:
        history.append({
            "stress_level": doc.get("stress_level"),
            "sleep_quality": doc.get("sleep_quality"),
            "timestamp": doc.get("timestamp").strftime("%Y-%m-%d %H:%M")
            if doc.get("timestamp") else "unknown"
        })

    if not history:
        return {"trend": "no history yet", "entries": []}

    if len(history) >= 2:
        latest_stress = history[0]["stress_level"]
        oldest_stress = history[-1]["stress_level"]
        stress_trend = (
            "improving" if latest_stress < oldest_stress else
            "worsening" if latest_stress > oldest_stress else
            "stable"
        )
        latest_sleep = history[0]["sleep_quality"]
        oldest_sleep = history[-1]["sleep_quality"]
        sleep_trend = (
            "improving" if latest_sleep > oldest_sleep else
            "worsening" if latest_sleep < oldest_sleep else
            "stable"
        )
    else:
        stress_trend = "insufficient data"
        sleep_trend = "insufficient data"

    return {
        "stress_trend": stress_trend,
        "sleep_trend": sleep_trend,
        "entries": history
    }