"""Source, Snapshot, Record, FieldValue, DatasetVersion, DedupeCluster, Export, LLMCall models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_id

# pgvector is optional; degrade gracefully if not available
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore
    VECTOR_AVAILABLE = False


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    domain: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(Text)
    robots_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    robots_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_yielded: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped[any] = relationship("Run", back_populates="sources")
    snapshots: Mapped[list[Snapshot]] = relationship(back_populates="source")


class Snapshot(Base, TimestampMixin):
    __tablename__ = "snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(Text)  # local path or s3 key
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int] = mapped_column(Integer, default=200)
    content_type: Mapped[str] = mapped_column(String(128), default="text/html")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    source: Mapped[Source] = relationship(back_populates="snapshots")


class Record(Base, TimestampMixin):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    data: Mapped[dict] = mapped_column(JSON)           # normalized field values
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    quality_flags: Mapped[list] = mapped_column(JSON, default=list)
    is_quarantined: Mapped[bool] = mapped_column(Boolean, default=False)
    quarantine_reasons: Mapped[list] = mapped_column(JSON, default=list)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    corroboration_count: Mapped[int] = mapped_column(Integer, default=1)
    pii_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    entity_type: Mapped[str] = mapped_column(String(64), default="")

    run: Mapped[any] = relationship("Run", back_populates="records")
    field_values: Mapped[list[FieldValue]] = relationship(back_populates="record")


class FieldValue(Base, TimestampMixin):
    __tablename__ = "field_values"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    record_id: Mapped[str] = mapped_column(ForeignKey("records.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(128))
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(32), default="unknown")  # json_ld|selector|llm
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    snapshot_id: Mapped[Optional[str]] = mapped_column(ForeignKey("snapshots.id"), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)  # snippet verified in source

    record: Mapped[Record] = relationship(back_populates="field_values")


class DatasetVersion(Base, TimestampMixin):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    version_number: Mapped[int] = mapped_column(Integer)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    diff_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # added/removed/changed
    previous_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)


class DedupeCluster(Base, TimestampMixin):
    __tablename__ = "dedupe_clusters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    canonical_record_id: Mapped[str] = mapped_column(ForeignKey("records.id"))
    member_record_ids: Mapped[list] = mapped_column(JSON, default=list)
    merge_method: Mapped[str] = mapped_column(String(32))  # exact|fuzzy|embedding|llm
    confidence: Mapped[float] = mapped_column(Float, default=1.0)


class Export(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    format: Mapped[str] = mapped_column(String(16))  # csv|xlsx|json|parquet
    storage_path: Mapped[str] = mapped_column(Text)
    include_provenance: Mapped[bool] = mapped_column(Boolean, default=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)


class LLMCall(Base, TimestampMixin):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("runs.id"), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[str] = mapped_column(String(128))  # plan|extract|dedupe|normalize|safety
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
