from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.api import health

app = FastAPI(
    title="LipiLens API",
    description="AI-assisted Modi manuscript transcription and preservation system",
    version="0.1.0",
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

@app.get("/")
def root():
    return {"message": "LipiLens API is running. Visit /docs for API documentation."}
