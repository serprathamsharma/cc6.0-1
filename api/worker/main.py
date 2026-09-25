"""ARQ worker entrypoint."""
from __future__ import annotations

import asyncio
from loguru import logger
from arq import run_worker
from arq.connections import RedisSettings

from api.config.settings import settings


async def startup(ctx: dict) -> None:
    logger.info("Worker starting up")


async def shutdown(ctx: dict) -> None:
    logger.info("Worker shutting down")


class WorkerSettings:
    functions = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 3600


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))  # type: ignore
