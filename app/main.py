# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime
import os
from pathlib import Path

from app.api.endpoints import router as api_router
from app.api.auth_routes import router as auth_router
from app.core.config import settings
from app.models.database import init_db, engine

# Create necessary directories
Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/cache").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    # Startup: Initialize database
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        print("Make sure PostgreSQL is running (docker-compose up -d db)")
    yield
    # Shutdown: Clean up resources
    engine.dispose()


app = FastAPI(
    title="Temporal Network Analysis API",
    description="Backend for processing and analyzing temporal network data",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Temporal Network Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "upload": "/api/upload",
            "analyze": "/api/analyze",
            "health": "/health"
        }
    }

@app.get("/health")
async def root_health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )