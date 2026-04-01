from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="backend/.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

# Existing collections
profiles_collection = db["profiles"]
analysis_collection = db["analysis"]


# New collections
profile_history_collection = db["profile_history"]
session_memory_collection = db["session_memory"]
daily_summary_collection = db["daily_summary"]
payments_collection = db["payments"]
async def ping_db():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected successfully")
        # Build RAG knowledge base if not exists
        from backend.services.rag import get_vectorstore
        get_vectorstore()
        print("✅ Ayurveda knowledge base ready")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")