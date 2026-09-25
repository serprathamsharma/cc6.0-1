from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from api.models.task import TaskStatus, RunStatus


class TaskCreate(BaseModel):
    prompt: str


class TaskOut(BaseModel):
    id: str
    title: str
    prompt: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    latest_run_id: Optional[str] = None
    latest_dataset_version_id: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkflowOut(BaseModel):
    id: str
    task_id: str
    version: int
    requirement_spec: dict
    dag: dict
    assumptions: list
    estimated_time_s: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowApprove(BaseModel):
    auto_run: bool = True


class RunOut(BaseModel):
    id: str
    task_id: str
    workflow_id: str
    status: RunStatus
    node_states: dict
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    pages_fetched: int
    records_found: int
    records_validated: int
    records_deduped: int
    error_count: int
    total_cost_usd: float
    compliance_report: Optional[dict] = None
    demo_mode: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordOut(BaseModel):
    id: str
    cluster_id: Optional[str] = None
    data: dict
    quality_score: float
    quality_flags: list
    is_quarantined: bool
    quarantine_reasons: list
    corroboration_count: int
    pii_flagged: bool
    entity_type: str
    field_values: list[dict] = []

    model_config = {"from_attributes": True}


class RefineRequest(BaseModel):
    refinement: str


class ChatRequest(BaseModel):
    question: str


class ExportRequest(BaseModel):
    format: str  # csv|xlsx|json|parquet
    include_provenance: bool = True
