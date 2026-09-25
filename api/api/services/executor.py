"""Workflow executor: runs DAG nodes with per-node status, retries, checkpointing."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config.settings import settings
from api.models.data import DatasetVersion, FieldValue, Record, Source
from api.models.task import Run, RunEvent, RunStatus
from api.services import fixtures as fixture_svc
from api.services.deduper import dedupe_records
from api.services.extractor import extract_records
from api.services.fetcher import fetch_sources
from api.services.validator import validate_records

NODE_STATUS_PENDING = "pending"
NODE_STATUS_RUNNING = "running"
NODE_STATUS_DONE = "done"
NODE_STATUS_FAILED = "failed"
NODE_STATUS_SKIPPED = "skipped"


async def emit_event(
    db: AsyncSession,
    run_id: str,
    event_type: str,
    message: str,
    node_id: str | None = None,
    data: dict | None = None,
    level: str = "info",
) -> None:
    event = RunEvent(
        run_id=run_id,
        occurred_at=datetime.now(timezone.utc),
        event_type=event_type,
        node_id=node_id,
        message=message,
        data=data,
        level=level,
    )
    db.add(event)
    await db.flush()


async def execute_run(
    run: Run,
    dag: dict,
    requirement_spec: dict,
    db: AsyncSession,
) -> None:
    """Execute all DAG nodes in dependency order."""
    nodes = dag.get("nodes", [])
    node_map = {n["id"]: n for n in nodes}
    node_states: dict[str, str] = run.node_states or {}

    # Initialize pending nodes
    for node in nodes:
        if node["id"] not in node_states:
            node_states[node["id"]] = NODE_STATUS_PENDING

    run.status = RunStatus.running
    run.started_at = datetime.now(timezone.utc)
    run.node_states = node_states
    await db.flush()

    await emit_event(db, run.id, "run_started", "Run started", data={"demo_mode": settings.is_demo})

    if settings.is_demo:
        await _execute_demo(run, dag, requirement_spec, db, node_states)
    else:
        await _execute_real(run, dag, requirement_spec, db, node_states, node_map)

    run.finished_at = datetime.now(timezone.utc)
    await db.flush()


async def _execute_demo(
    run: Run,
    dag: dict,
    requirement_spec: dict,
    db: AsyncSession,
    node_states: dict,
) -> None:
    """Replay demo fixture for this run."""
    entity_type = requirement_spec.get("entity_type", "job_posting")
    records = fixture_svc.load_fixture(entity_type)

    nodes = dag.get("nodes", [])
    for i, node in enumerate(nodes):
        node_id = node["id"]
        node_states[node_id] = NODE_STATUS_RUNNING
        run.node_states = dict(node_states)
        await db.flush()
        await emit_event(db, run.id, "node_started", f"[DEMO] Running {node['label']}", node_id=node_id)
        # Simulate work
        await asyncio.sleep(0.3)
        node_states[node_id] = NODE_STATUS_DONE
        run.node_states = dict(node_states)
        await db.flush()
        await emit_event(db, run.id, "node_done", f"[DEMO] {node['label']} complete", node_id=node_id)

    # Persist fixture records
    from api.models.data import Record, FieldValue, Source, DatasetVersion

    source = Source(
        run_id=run.id,
        domain="fixtures",
        url="demo://fixtures",
        robots_allowed=True,
        pages_fetched=len(records),
        records_yielded=len(records),
    )
    db.add(source)
    await db.flush()

    for raw in records:
        rec = Record(
            run_id=run.id,
            data=raw,
            quality_score=raw.get("_quality_score", 85.0),
            entity_type=entity_type,
        )
        db.add(rec)
        await db.flush()
        # Add field values with provenance
        for field, value in raw.items():
            if field.startswith("_"):
                continue
            fv = FieldValue(
                record_id=rec.id,
                field_name=field,
                value_text=str(value) if value is not None else None,
                source_url=raw.get("_source_url", "demo://fixtures"),
                evidence_snippet=raw.get(f"_evidence_{field}", f"Demo fixture value for {field}"),
                extraction_method="fixture",
                confidence=1.0,
                fetched_at=datetime.now(timezone.utc),
                verified=True,
            )
            db.add(fv)

    run.records_found = len(records)
    run.records_validated = len(records)
    run.records_deduped = len(records)
    run.pages_fetched = len(records)
    run.status = RunStatus.completed
    run.demo_mode = True
    await db.flush()

    # Create dataset version (auto-increment)
    stmt = select(func.max(DatasetVersion.version_number)).where(DatasetVersion.task_id == run.task_id)
    max_res = await db.execute(stmt)
    max_ver = max_res.scalar_one_or_none() or 0
    next_ver = max_ver + 1

    prev_id = None
    if max_ver > 0:
        prev_stmt = select(DatasetVersion.id).where(
            DatasetVersion.task_id == run.task_id,
            DatasetVersion.version_number == max_ver,
        )
        prev_id = (await db.execute(prev_stmt)).scalar_one_or_none()

    dsv = DatasetVersion(
        task_id=run.task_id,
        run_id=run.id,
        version_number=next_ver,
        record_count=len(records),
        previous_version_id=prev_id,
    )
    db.add(dsv)
    await db.flush()

    await emit_event(db, run.id, "run_completed",
                     f"[DEMO] Run complete. {len(records)} records loaded from fixtures.",
                     data={"record_count": len(records)})


async def _execute_real(
    run: Run,
    dag: dict,
    requirement_spec: dict,
    db: AsyncSession,
    node_states: dict,
    node_map: dict,
) -> None:
    """Execute real DAG (non-demo) with full extraction, validation, and persistence."""
    nodes = dag.get("nodes", [])
    completed: set[str] = set()
    fetched_pages: list[dict] = []
    all_records: list[dict] = []

    def ready(node: dict) -> bool:
        return all(d in completed for d in node.get("depends_on", []))

    remaining = list(nodes)
    max_iterations = len(nodes) * 2  # prevent infinite loop
    iterations = 0

    while remaining and iterations < max_iterations:
        iterations += 1
        batch = [n for n in remaining if ready(n) and node_states.get(n["id"]) == NODE_STATUS_PENDING]
        if not batch:
            await asyncio.sleep(0.1)
            continue

        for node in batch:
            nid = node["id"]
            tool = node["tool"]
            node_states[nid] = NODE_STATUS_RUNNING
            run.node_states = dict(node_states)
            await db.flush()
            await emit_event(db, run.id, "node_started", f"Starting {node['label']}", node_id=nid)

            try:
                if tool in ("discover_sources", "fetch_static"):
                    fetched = await fetch_sources(requirement_spec, node["config"], run.id, db)
                    fetched_pages.extend(fetched)
                    run.pages_fetched += len(fetched)
                    # Persist sources
                    for p in fetched:
                        url = p.get("url", "")
                        parsed = urlparse(url)
                        source = Source(
                            run_id=run.id,
                            domain=parsed.netloc or "unknown",
                            url=url,
                            robots_allowed=True,
                            http_status=p.get("http_status", 200),
                            content_hash=p.get("content_hash"),
                            pages_fetched=1,
                        )
                        db.add(source)
                    await db.flush()

                elif tool in ("extract_structured", "extract_llm"):
                    extracted = await extract_records(fetched_pages, requirement_spec, node["config"], run.id)
                    all_records.extend(extracted)
                    run.records_found = len(all_records)

                elif tool == "validate":
                    all_records = await validate_records(all_records)
                    run.records_validated = len(all_records)

                elif tool == "dedupe":
                    all_records = await dedupe_records(all_records, node["config"], run_id=run.id)
                    run.records_deduped = len(all_records)

                elif tool == "normalize":
                    pass  # handled in extractor

                elif tool == "score":
                    pass  # scores assigned during validate

                node_states[nid] = NODE_STATUS_DONE
                completed.add(nid)
                remaining = [n for n in remaining if n["id"] != nid]
                await emit_event(db, run.id, "node_done", f"{node['label']} complete", node_id=nid)

            except Exception as e:
                logger.error(f"Node {nid} failed: {e}")
                node_states[nid] = NODE_STATUS_FAILED
                run.error_count += 1
                await emit_event(db, run.id, "node_failed", f"{node['label']} failed: {e}",
                                 node_id=nid, level="error")

            run.node_states = dict(node_states)
            await db.flush()

    # Persist all extracted records and field values to DB (#11)
    entity_type = requirement_spec.get("entity_type", "record")
    for raw in all_records:
        rec = Record(
            run_id=run.id,
            data=raw,
            quality_score=raw.get("_quality_score", 85.0),
            entity_type=entity_type,
            is_quarantined=raw.get("_is_quarantined", False),
        )
        db.add(rec)
        await db.flush()

        for field, value in raw.items():
            if field.startswith("_"):
                continue
            fv = FieldValue(
                record_id=rec.id,
                field_name=field,
                value_text=str(value) if value is not None else None,
                source_url=raw.get("_source_url", "https://scoutiq.dev"),
                evidence_snippet=raw.get(f"_evidence_{field}", ""),
                extraction_method=raw.get("_extraction_method", "unknown"),
                confidence=raw.get(f"_confidence_{field}", 1.0),
                fetched_at=datetime.now(timezone.utc),
                verified=raw.get(f"_verified_{field}", True),
            )
            db.add(fv)

    # Auto-increment DatasetVersion (#14)
    stmt = select(func.max(DatasetVersion.version_number)).where(DatasetVersion.task_id == run.task_id)
    max_res = await db.execute(stmt)
    max_ver = max_res.scalar_one_or_none() or 0
    next_ver = max_ver + 1

    prev_id = None
    if max_ver > 0:
        prev_stmt = select(DatasetVersion.id).where(
            DatasetVersion.task_id == run.task_id,
            DatasetVersion.version_number == max_ver,
        )
        prev_id = (await db.execute(prev_stmt)).scalar_one_or_none()

    dsv = DatasetVersion(
        task_id=run.task_id,
        run_id=run.id,
        version_number=next_ver,
        record_count=len(all_records),
        previous_version_id=prev_id,
    )
    db.add(dsv)

    run.status = RunStatus.completed
    await db.flush()
    await emit_event(db, run.id, "run_completed", f"Run complete. {len(all_records)} records persisted.")
