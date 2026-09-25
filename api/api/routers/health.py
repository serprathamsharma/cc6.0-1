from __future__ import annotations

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config.settings import settings
from api.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    postgres_ok = False
    try:
        await db.execute(text("SELECT 1"))
        postgres_ok = True
    except Exception as e:
        logger.warning(f"Health check DB probe failed: {e}")

    redis_ok = False
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception as e:
        logger.warning(f"Health check Redis probe failed: {e}")

    is_healthy = postgres_ok or settings.is_demo
    return {
        "status": "ok" if is_healthy else "degraded",
        "database": "connected" if postgres_ok else "unreachable",
        "redis": "connected" if redis_ok else "unreachable",
        "demo_mode": settings.is_demo,
        "model_planner": settings.model_planner,
        "model_extract": settings.model_extract,
        "model_fast": settings.model_fast,
    }
