"""Workflow executor: runs DAG nodes with per-node status, retries, checkpointing."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from api.config.settings import settings
from api.models.task import Run, RunEvent, RunStatus
from api.services import fixtures as fixture_svc
from api.services.fetcher import fetch_sources
from api.services.extractor import extract_records
from api.services.validator import validate_records
from api.services.deduper import dedupe_records

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
    from api.models.task import Task
    import uuid

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

    # Create dataset version
    dsv = DatasetVersion(
        task_id=run.task_id,
        run_id=run.id,
        version_number=1,
        record_count=len(records),
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
    """Execute real DAG (non-demo)."""
    nodes = dag.get("nodes", [])
    completed: set[str] = set()
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
                    run.pages_fetched += len(fetched)
                elif tool in ("extract_structured", "extract_llm"):
                    extracted = await extract_records(all_records, requirement_spec, node["config"], run.id)
                    all_records.extend(extracted)
                    run.records_found = len(all_records)
                elif tool == "validate":
                    all_records = await validate_records(all_records)
                    run.records_validated = len(all_records)
                elif tool == "dedupe":
                    all_records = await dedupe_records(all_records, node["config"])
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

    run.status = RunStatus.completed
    await emit_event(db, run.id, "run_completed", f"Run complete. {run.records_deduped} records.")
