"""Task, Workflow, Run, and related models."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_id


class TaskStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    archived = "archived"
    cancelled = "cancelled"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus), default=TaskStatus.draft
    )
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    latest_run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    latest_dataset_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    workspace: Mapped[Any] = relationship("Workspace", back_populates="tasks")
    workflows: Mapped[list[Workflow]] = relationship(back_populates="task", order_by="Workflow.version.desc()")
    runs: Mapped[list[Run]] = relationship(back_populates="task")


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    requirement_spec: Mapped[dict] = mapped_column(JSON)  # RequirementSpec
    dag: Mapped[dict] = mapped_column(JSON)               # WorkflowDAG
    assumptions: Mapped[list] = mapped_column(JSON, default=list)
    estimated_time_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    estimated_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)

    task: Mapped[Task] = relationship(back_populates="workflows")
    runs: Mapped[list[Run]] = relationship(back_populates="workflow")


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus), default=RunStatus.queued, index=True
    )
    node_states: Mapped[dict] = mapped_column(JSON, default=dict)  # {node_id: NodeState}
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_found: Mapped[int] = mapped_column(Integer, default=0)
    records_validated: Mapped[int] = mapped_column(Integer, default=0)
    records_deduped: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    compliance_report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    task: Mapped[Task] = relationship(back_populates="runs")
    workflow: Mapped[Workflow] = relationship(back_populates="runs")
    events: Mapped[list[RunEvent]] = relationship(back_populates="run")
    records: Mapped[list[Record]] = relationship(back_populates="run")
    sources: Mapped[list[Source]] = relationship(back_populates="run")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String(64))
    node_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="info")  # info|warn|error

    run: Mapped[Run] = relationship(back_populates="events")
