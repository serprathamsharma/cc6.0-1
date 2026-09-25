"""ARQ worker entrypoint."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from arq import run_worker
from arq.connections import RedisSettings
from loguru import logger
from sqlalchemy import select

from api.config.settings import settings
from api.db import AsyncSessionLocal
from api.models.task import Run, RunStatus
from api.services.executor import execute_workflow


async def execute_run_job(ctx: dict, run_id: str, dag: dict, requirement_spec: dict) -> None:
    """Execute a task run via ARQ worker."""
    logger.info(f"Worker processing run {run_id}")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Run).where(Run.id == run_id))
        run = res.scalar_one_or_none()
        if not run:
            logger.error(f"Run {run_id} not found in worker")
            return
        run.status = RunStatus.running
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            await execute_workflow(run, dag, requirement_spec, db)
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info(f"Worker completed run {run_id}")
        except Exception as e:
            logger.error(f"Worker run {run_id} failed: {e}")
            run.status = RunStatus.failed
            run.finished_at = datetime.now(timezone.utc)
            await db.commit()


async def startup(ctx: dict) -> None:
    logger.info("Worker starting up")


async def shutdown(ctx: dict) -> None:
    logger.info("Worker shutting down")


class WorkerSettings:
    functions = [execute_run_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 3600


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))  # type: ignore

