"""Dataset Version Diff and Lineage Service.

Compares two dataset versions/runs to compute record-level changes, field updates,
and data quality evolution.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.data import DatasetVersion, Record


async def compute_version_diff(
    current_version_id: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Compute structural and record-level diff between a version and its predecessor."""
    curr_res = await db.execute(select(DatasetVersion).where(DatasetVersion.id == current_version_id))
    curr_ver = curr_res.scalar_one_or_none()
    if not curr_ver:
        return {"error": "Dataset version not found"}

    # Fetch current records
    curr_rec_stmt = (
        select(Record)
        .where(Record.run_id == curr_ver.run_id)
        .options(selectinload(Record.field_values))
    )
    curr_records = list((await db.execute(curr_rec_stmt)).scalars().all())

    # If no previous version, all records are added
    if not curr_ver.previous_version_id:
        return {
            "current_version": curr_ver.version_number,
            "previous_version": None,
            "summary": f"Initial version {curr_ver.version_number} established with {len(curr_records)} records.",
            "added_count": len(curr_records),
            "removed_count": 0,
            "modified_count": 0,
            "unchanged_count": 0,
            "quality_delta": 0.0,
            "changes": [
                {"type": "added", "record_id": r.id, "preview": {k: v for k, v in r.data.items() if not k.startswith("_")}}
                for r in curr_records[:20]
            ],
        }

    # Fetch predecessor version
    prev_res = await db.execute(select(DatasetVersion).where(DatasetVersion.id == curr_ver.previous_version_id))
    prev_ver = prev_res.scalar_one_or_none()
    if not prev_ver:
        return {"error": "Previous version not found"}

    prev_rec_stmt = (
        select(Record)
        .where(Record.run_id == prev_ver.run_id)
        .options(selectinload(Record.field_values))
    )
    prev_records = list((await db.execute(prev_rec_stmt)).scalars().all())

    # Map records by primary identifying key
    def get_identifying_key(rec: Record) -> str:
        d = rec.data
        for candidate in ["name", "title", "company_name", "id", "url", "domain"]:
            if candidate in d and d[candidate]:
                return str(d[candidate]).strip().lower()
        # Fallback to hash of cleaned data
        clean = {k: v for k, v in d.items() if not k.startswith("_")}
        return str(sorted(clean.items()))

    prev_map = {get_identifying_key(r): r for r in prev_records}
    curr_map = {get_identifying_key(r): r for r in curr_records}

    added = []
    modified = []
    unchanged = []
    removed = []

    for key, c_rec in curr_map.items():
        if key not in prev_map:
            added.append({
                "type": "added",
                "record_id": c_rec.id,
                "preview": {k: v for k, v in c_rec.data.items() if not k.startswith("_")},
            })
        else:
            p_rec = prev_map[key]
            # Compare field values
            c_clean = {k: v for k, v in c_rec.data.items() if not k.startswith("_")}
            p_clean = {k: v for k, v in p_rec.data.items() if not k.startswith("_")}
            field_diffs = {}
            for f in set(c_clean.keys()) | set(p_clean.keys()):
                if c_clean.get(f) != p_clean.get(f):
                    field_diffs[f] = {"old": p_clean.get(f), "new": c_clean.get(f)}

            if field_diffs:
                modified.append({
                    "type": "modified",
                    "record_id": c_rec.id,
                    "key": key,
                    "field_diffs": field_diffs,
                })
            else:
                unchanged.append(c_rec.id)

    for key, p_rec in prev_map.items():
        if key not in curr_map:
            removed.append({
                "type": "removed",
                "record_id": p_rec.id,
                "preview": {k: v for k, v in p_rec.data.items() if not k.startswith("_")},
            })

    curr_avg_q = (sum(r.quality_score for r in curr_records) / max(len(curr_records), 1)) if curr_records else 0
    prev_avg_q = (sum(r.quality_score for r in prev_records) / max(len(prev_records), 1)) if prev_records else 0
    q_delta = round(curr_avg_q - prev_avg_q, 2)

    summary = (
        f"Version {curr_ver.version_number} vs {prev_ver.version_number}: "
        f"{len(added)} added, {len(modified)} modified, {len(removed)} removed. "
        f"Quality score delta: {'+' if q_delta >= 0 else ''}{q_delta}%."
    )

    return {
        "current_version": curr_ver.version_number,
        "previous_version": prev_ver.version_number,
        "summary": summary,
        "added_count": len(added),
        "removed_count": len(removed),
        "modified_count": len(modified),
        "unchanged_count": len(unchanged),
        "quality_delta": q_delta,
        "changes": (added + modified + removed)[:50],
    }
