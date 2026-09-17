from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import CORS_ORIGINS, DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR
from backend.api import health, manuscripts, transcriptions
from backend.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="LipiLens API",
    description="AI-assisted Modi manuscript transcription and preservation system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router, prefix="/api")
app.include_router(manuscripts.router, prefix="/api")
app.include_router(transcriptions.router, prefix="/api")

# Serve manuscript images (originals + restored) for the frontend.
app.mount("/files/raw", StaticFiles(directory=RAW_DATA_DIR), name="raw")
app.mount("/files/processed", StaticFiles(directory=PROCESSED_DATA_DIR),
          name="processed")

@app.get("/")
def root():
    return {"message": "LipiLens API is running. Visit /docs for API documentation."}
