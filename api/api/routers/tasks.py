"""Tasks router: CRUD, plan, run, SSE, records, export, refine, chat."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import current_user
from api.db import get_db, AsyncSessionLocal
from api.models.task import Run, RunEvent, RunStatus, Task, TaskStatus, Workflow
from api.models.data import DatasetVersion, Export, Record, FieldValue, Source
from api.models.workspace import User
from api.schemas.task import (
    ChatRequest, ExportRequest, RecordOut, RefineRequest,
    RunOut, TaskCreate, TaskOut, WorkflowApprove, WorkflowOut,
)
from api.services.compliance import screen_prompt, generate_compliance_report
from api.services.executor import execute_run
from api.services.exporter import export_csv, export_xlsx, export_json, export_parquet
from api.services.planner import plan_workflow
from api.config.settings import settings

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── List Tasks ──────────────────────────────────────────────────────────────
@router.get("", response_model=list[TaskOut])
async def list_tasks(
    archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(
        Task.workspace_id == user.workspace_id,
        Task.is_archived == archived,
    ).order_by(desc(Task.created_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


# ── Create Task ──────────────────────────────────────────────────────────────
@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # Safety screen
    is_safe, reason = await screen_prompt(body.prompt)
    if not is_safe:
        raise HTTPException(status_code=422, detail=f"Request refused: {reason}")

    task = Task(
        workspace_id=user.workspace_id,
        created_by=user.id,
        title=body.prompt[:120],
        prompt=body.prompt,
        status=TaskStatus.pending,
    )
    db.add(task)
    await db.flush()
    return task


# ── Get Task ──────────────────────────────────────────────────────────────
@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    return task


# ── Plan Workflow ──────────────────────────────────────────────────────────
@router.post("/{task_id}/plan", response_model=WorkflowOut)
async def plan_task(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)

    spec, dag, assumptions = await plan_workflow(task.prompt)

    # Compute totals
    dag_dict = dag.model_dump()
    nodes = dag_dict.get("nodes", [])
    est_time = sum(n.get("estimated_time_s", 0) for n in nodes)
    est_cost = sum(n.get("estimated_cost_usd", 0) for n in nodes)

    # Get next version
    existing = await db.execute(
        select(func.max(Workflow.version)).where(Workflow.task_id == task_id)
    )
    max_ver = existing.scalar() or 0

    wf = Workflow(
        task_id=task.id,
        version=max_ver + 1,
        requirement_spec=spec.model_dump(),
        dag=dag_dict,
        assumptions=assumptions,
        estimated_time_s=est_time,
        estimated_cost_usd=est_cost,
        approved=False,
    )
    db.add(wf)
    await db.flush()

    task.status = TaskStatus.pending
    await db.flush()
    return wf


# ── Approve & Run ──────────────────────────────────────────────────────────
@router.post("/{task_id}/workflows/{workflow_id}/approve", response_model=RunOut)
async def approve_workflow(
    task_id: str,
    workflow_id: str,
    body: WorkflowApprove,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    result = await db.execute(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.task_id == task_id)
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(404, "Workflow not found")

    wf.approved = True
    task.status = TaskStatus.running

    run = Run(
        task_id=task.id,
        workflow_id=wf.id,
        status=RunStatus.queued,
        node_states={},
        demo_mode=settings.is_demo,
    )
    db.add(run)
    await db.flush()

    task.latest_run_id = run.id
    await db.flush()

    if body.auto_run:
        run_id = run.id
        dag = wf.dag
        spec = wf.requirement_spec
        background_tasks.add_task(_bg_run, run_id, dag, spec)

    return run


async def _bg_run(run_id: str, dag: dict, spec: dict) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            return
        try:
            await execute_run(run, dag, spec, db)
        except Exception as e:
            run.status = RunStatus.failed
            run.finished_at = datetime.now(timezone.utc)
        await db.commit()


# ── SSE: stream run events ──────────────────────────────────────────────────
@router.get("/{task_id}/runs/{run_id}/events")
async def stream_run_events(
    task_id: str,
    run_id: str,
    since_id: str = Query(default=""),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    async def generator() -> AsyncGenerator[str, None]:
        last_id = since_id
        while True:
            async with AsyncSessionLocal() as session:
                q = select(RunEvent).where(
                    RunEvent.run_id == run_id
                ).order_by(RunEvent.occurred_at)
                result = await session.execute(q)
                events = result.scalars().all()

            for ev in events:
                if last_id and ev.id <= last_id:
                    continue
                payload = json.dumps({
                    "id": ev.id,
                    "type": ev.event_type,
                    "node_id": ev.node_id,
                    "message": ev.message,
                    "level": ev.level,
                    "data": ev.data,
                    "occurred_at": ev.occurred_at.isoformat(),
                })
                yield f"data: {payload}\n\n"
                last_id = ev.id

            # Check if run is done
            async with AsyncSessionLocal() as session:
                r = await session.execute(select(Run).where(Run.id == run_id))
                run = r.scalar_one_or_none()
                if run and run.status in (RunStatus.completed, RunStatus.failed, RunStatus.cancelled):
                    yield "data: {\"type\": \"done\"}\n\n"
                    return

            await asyncio.sleep(1)

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Get Run ──────────────────────────────────────────────────────────────
@router.get("/{task_id}/runs/{run_id}", response_model=RunOut)
async def get_run(
    task_id: str,
    run_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Run).where(Run.id == run_id, Run.task_id == task_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


# ── List Runs for Task ────────────────────────────────────────────────────
@router.get("/{task_id}/runs", response_model=list[RunOut])
async def list_runs(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Run).where(Run.task_id == task_id).order_by(desc(Run.created_at))
    )
    return result.scalars().all()


# ── Records ──────────────────────────────────────────────────────────────
@router.get("/{task_id}/runs/{run_id}/records")
async def list_records(
    task_id: str,
    run_id: str,
    search: str = "",
    quarantined: bool = False,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Record).where(
        Record.run_id == run_id,
        Record.is_quarantined == quarantined,
    ).order_by(Record.created_at).limit(limit).offset(offset)
    result = await db.execute(q)
    records = result.scalars().all()

    # Attach field values
    out = []
    for rec in records:
        fv_result = await db.execute(
            select(FieldValue).where(FieldValue.record_id == rec.id)
        )
        fvs = fv_result.scalars().all()
        out.append({
            "id": rec.id,
            "data": rec.data,
            "quality_score": rec.quality_score,
            "quality_flags": rec.quality_flags,
            "is_quarantined": rec.is_quarantined,
            "quarantine_reasons": rec.quarantine_reasons,
            "corroboration_count": rec.corroboration_count,
            "pii_flagged": rec.pii_flagged,
            "entity_type": rec.entity_type,
            "field_values": [
                {
                    "field_name": fv.field_name,
                    "value_text": fv.value_text,
                    "source_url": fv.source_url,
                    "evidence_snippet": fv.evidence_snippet,
                    "extraction_method": fv.extraction_method,
                    "confidence": fv.confidence,
                    "verified": fv.verified,
                }
                for fv in fvs
            ],
        })
    return out


# ── Sources ──────────────────────────────────────────────────────────────
@router.get("/{task_id}/runs/{run_id}/sources")
async def list_sources(
    task_id: str,
    run_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Source).where(Source.run_id == run_id))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "domain": s.domain,
            "url": s.url,
            "robots_allowed": s.robots_allowed,
            "pages_fetched": s.pages_fetched,
            "records_yielded": s.records_yielded,
            "error_count": s.error_count,
            "skipped_reason": s.skipped_reason,
        }
        for s in sources
    ]


# ── Export ──────────────────────────────────────────────────────────────
@router.post("/{task_id}/runs/{run_id}/export")
async def export_run(
    task_id: str,
    run_id: str,
    body: ExportRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Record).where(Record.run_id == run_id, Record.is_quarantined == False)
    )
    records = result.scalars().all()
    raw = [r.data for r in records]

    # Add provenance from field_values
    for rec_obj, raw_rec in zip(records, raw):
        fv_result = await db.execute(
            select(FieldValue).where(FieldValue.record_id == rec_obj.id)
        )
        fvs = fv_result.scalars().all()
        if fvs:
            raw_rec["_source_url"] = fvs[0].source_url
            raw_rec["_extraction_method"] = fvs[0].extraction_method
            raw_rec["_quality_score"] = rec_obj.quality_score

    fmt = body.format
    if fmt == "csv":
        content = export_csv(raw, body.include_provenance)
        media = "text/csv"
        filename = f"scoutiq_{run_id[:8]}.csv"
    elif fmt == "xlsx":
        content = export_xlsx(raw, body.include_provenance)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"scoutiq_{run_id[:8]}.xlsx"
    elif fmt == "parquet":
        content = export_parquet(raw, body.include_provenance)
        media = "application/octet-stream"
        filename = f"scoutiq_{run_id[:8]}.parquet"
    else:
        content = export_json(raw, body.include_provenance)
        media = "application/json"
        filename = f"scoutiq_{run_id[:8]}.json"

    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Refine ──────────────────────────────────────────────────────────────
@router.post("/{task_id}/refine", response_model=WorkflowOut)
async def refine_task(
    task_id: str,
    body: RefineRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    new_prompt = f"{task.prompt}. Additional refinement: {body.refinement}"
    spec, dag, assumptions = await plan_workflow(new_prompt)

    existing = await db.execute(
        select(func.max(Workflow.version)).where(Workflow.task_id == task_id)
    )
    max_ver = existing.scalar() or 0

    dag_dict = dag.model_dump()
    nodes = dag_dict.get("nodes", [])
    wf = Workflow(
        task_id=task.id,
        version=max_ver + 1,
        requirement_spec=spec.model_dump(),
        dag=dag_dict,
        assumptions=assumptions,
        estimated_time_s=sum(n.get("estimated_time_s", 0) for n in nodes),
        estimated_cost_usd=sum(n.get("estimated_cost_usd", 0) for n in nodes),
        approved=False,
    )
    db.add(wf)
    await db.flush()
    return wf


# ── Chat with Dataset (text-to-SQL) ────────────────────────────────────────
@router.post("/{task_id}/runs/{run_id}/chat")
async def chat_with_dataset(
    task_id: str,
    run_id: str,
    body: ChatRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if settings.is_demo:
        return {
            "answer": "[DEMO MODE] Chat with dataset requires a live OpenAI API key.",
            "sql": None,
            "rows": [],
        }

    import json
    from api.services.llm import llm_call

    schema = {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
            "explanation": {"type": "string"},
        },
        "required": ["sql", "explanation"],
        "additionalProperties": False,
    }
    messages = [
        {"role": "system", "content": """Generate a read-only SQL SELECT query for the records table.
Table: records (id TEXT, run_id TEXT, data JSONB, quality_score REAL, entity_type TEXT)
Rules: SELECT only, no subqueries that write, LIMIT 1000, use json_extract for data fields.
Only query the allowed table: records."""},
        {"role": "user", "content": f"Run ID: {run_id}\nQuestion: {body.question}"},
    ]
    result = await llm_call(
        model=settings.model_fast,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"name": "sql_gen", "strict": True, "schema": schema}},
        purpose="chat_sql",
    )
    try:
        data = json.loads(result)
        sql = data["sql"]
        # Safety: ensure SELECT only
        if not sql.strip().upper().startswith("SELECT"):
            return {"answer": "Only SELECT queries are allowed.", "sql": sql, "rows": []}
        # Execute with row limit
        from sqlalchemy import text
        rows_result = await db.execute(text(sql + " LIMIT 100"))
        rows = [dict(r._mapping) for r in rows_result]
        return {"answer": data["explanation"], "sql": sql, "rows": rows}
    except Exception as e:
        return {"answer": f"Query failed: {e}", "sql": None, "rows": []}


# ── Dataset Versions / Diff ────────────────────────────────────────────────
@router.get("/{task_id}/versions")
async def list_versions(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DatasetVersion).where(DatasetVersion.task_id == task_id)
        .order_by(desc(DatasetVersion.version_number))
    )
    versions = result.scalars().all()
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "run_id": v.run_id,
            "record_count": v.record_count,
            "diff_summary": v.diff_summary,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


# ── Task Actions ──────────────────────────────────────────────────────────
@router.patch("/{task_id}/archive")
async def archive_task(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    task.is_archived = True
    task.status = TaskStatus.archived
    await db.flush()
    return {"ok": True}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    await db.delete(task)
    return {"ok": True}


@router.post("/{task_id}/clone", response_model=TaskOut, status_code=201)
async def clone_task(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task(task_id, user, db)
    new_task = Task(
        workspace_id=user.workspace_id,
        created_by=user.id,
        title=f"[Clone] {task.title}",
        prompt=task.prompt,
        status=TaskStatus.draft,
    )
    db.add(new_task)
    await db.flush()
    return new_task


@router.patch("/{task_id}/runs/{run_id}/cancel")
async def cancel_run(
    task_id: str,
    run_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run:
        run.status = RunStatus.cancelled
        run.finished_at = datetime.now(timezone.utc)
    return {"ok": True}


# ── KPIs ──────────────────────────────────────────────────────────────
@router.get("/kpis/summary")
async def kpis(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    total_tasks = await db.execute(
        select(func.count(Task.id)).where(Task.workspace_id == user.workspace_id)
    )
    total_runs = await db.execute(select(func.count(Run.id)))
    total_records = await db.execute(select(func.count(Record.id)))
    return {
        "total_tasks": total_tasks.scalar() or 0,
        "total_runs": total_runs.scalar() or 0,
        "total_records": total_records.scalar() or 0,
        "demo_mode": settings.is_demo,
    }


# ── Workflows ──────────────────────────────────────────────────────────────
@router.get("/{task_id}/workflows", response_model=list[WorkflowOut])
async def list_workflows(
    task_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workflow).where(Workflow.task_id == task_id).order_by(desc(Workflow.version))
    )
    return result.scalars().all()


# ── Helper ──────────────────────────────────────────────────────────────
async def _get_task(task_id: str, user: User, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.workspace_id == user.workspace_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Task not found")
    return task
