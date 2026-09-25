"""ScoutIQ FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.config.settings import settings
from api.routers import auth, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"ScoutIQ API starting. Demo mode: {settings.is_demo}")
    # Probe AI models at startup
    if settings.openai_api_key:
        try:
            from api.services.llm import probe_models
            await probe_models()
        except Exception as e:
            logger.warning(f"Model probe failed: {e}")
    yield
    logger.info("ScoutIQ API shutting down")


app = FastAPI(
    title="ScoutIQ API",
    version="1.0.0",
    description="AI data-intelligence platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://web:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "demo_mode": settings.is_demo,
        "model_planner": settings.model_planner,
        "model_extract": settings.model_extract,
        "model_fast": settings.model_fast,
    }
