from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.db.mongo import ping_db
from backend.routes import profile, analyze, yoga, meditation, diet, mindmap, summary, checkin, wellness, report, ayurveda, affirmation, payment

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ping_db()
    yield

app = FastAPI(
    title="PranaEdge API",
    description="AI-powered wellness intelligence system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, tags=["Profile"])
app.include_router(analyze.router, tags=["Analysis"]) 
app.include_router(profile.router, tags=["Profile"])
app.include_router(analyze.router, tags=["Analysis"])
app.include_router(yoga.router, tags=["Yoga"])
app.include_router(meditation.router, tags=["Meditation"])
app.include_router(diet.router, tags=["Diet"])
app.include_router(mindmap.router, tags=["Mindmap"])
app.include_router(summary.router, tags=["Summary"])
app.include_router(checkin.router, tags=["Checkin"])
app.include_router(wellness.router, tags=["Wellness Score"])
app.include_router(report.router, tags=["Weekly Report"])
app.include_router(ayurveda.router, tags=["Ayurveda RAG"])
app.include_router(affirmation.router, tags=["Affirmation"])
app.include_router(payment.router, tags=["Premium Payment"])

@app.get("/")
async def root():
    return {"message": "PranaEdge API is running.."}