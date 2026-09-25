"""ScoutIQ FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from loguru import logger

# Configure structured logging
logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
    level="INFO",
)

from api.config.settings import settings
from api.routers import auth, health, mcp, tasks

# Configurable CORS origins: defaults + CORS_ORIGINS env var (comma-separated)
_CORS_ORIGINS = ["http://localhost:3000", "http://web:3000"]
import os
_extra = os.environ.get("CORS_ORIGINS", "")
if _extra:
    _CORS_ORIGINS.extend(o.strip() for o in _extra.split(",") if o.strip())


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
    # Reject insecure default secret key in non-demo mode
    if not settings.is_demo and settings.app_secret_key == "changeme-32-char-secret-key-here":
        logger.error("FATAL: APP_SECRET_KEY is set to the insecure default. Set a unique key via .env")
        raise RuntimeError("Insecure default APP_SECRET_KEY — set a unique value in .env")
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
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(mcp.router)
app.include_router(mcp.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")


