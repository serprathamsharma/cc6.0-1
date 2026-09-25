"""Deduper: rapidfuzz + embedding similarity + LLM adjudication."""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from api.config.settings import settings
from api.services.llm import llm_call


def _key_fields(record: dict, key_fields: list[str] | None = None) -> str:
    """Build a normalized key string from key fields."""
    fields = key_fields or [k for k in record if not k.startswith('_')]
    parts = []
    for f in fields[:5]:
        v = record.get(f, '')
        if isinstance(v, str):
            parts.append(v.lower().strip())
    return ' | '.join(parts)


def fuzzy_dedupe(
    records: list[dict],
    threshold: int = 85,
) -> tuple[list[dict], list[tuple[int, int, float]]]:
    """Dedupe using rapidfuzz. Return (deduped, pairs_above_threshold)."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not available, skipping fuzzy dedupe")
        return records, []

    keys = [_key_fields(r) for r in records]
    merged_indices: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    clusters: dict[int, list[int]] = {}  # canonical_idx -> [member_indices]

    for i in range(len(records)):
        if i in merged_indices:
            continue
        clusters[i] = [i]
        for j in range(i + 1, len(records)):
            if j in merged_indices:
                continue
            score = fuzz.token_sort_ratio(keys[i], keys[j])
            if score >= threshold:
                pairs.append((i, j, score))
                merged_indices.add(j)
                clusters[i].append(j)

    deduped = []
    for canonical_idx, members in clusters.items():
        rec = dict(records[canonical_idx])
        rec['_corroboration_count'] = len(members)
        rec['_cluster_members'] = members
        deduped.append(rec)

    logger.info(f"Fuzzy dedupe: {len(records)} -> {len(deduped)} records")
    return deduped, pairs


async def llm_adjudicate_pair(
    rec_a: dict,
    rec_b: dict,
    run_id: str | None = None,
) -> bool:
    """Use LLM to decide if two borderline records are duplicates."""
    if settings.is_demo:
        return False  # conservative in demo

    schema = {
        "type": "object",
        "properties": {
            "are_duplicates": {"type": "boolean"},
            "reasoning": {"type": "string"},
        },
        "required": ["are_duplicates", "reasoning"],
        "additionalProperties": False,
    }

    def _slim(r: dict) -> dict:
        return {k: v for k, v in r.items() if not k.startswith('_')}

    messages = [
        {"role": "system", "content": "Determine if two records refer to the same real-world entity."},
        {"role": "user", "content": f"Record A:\n{json.dumps(_slim(rec_a), indent=2)}\n\nRecord B:\n{json.dumps(_slim(rec_b), indent=2)}"},
    ]
    result = await llm_call(
        model=settings.model_fast,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"name": "dedupe", "strict": True, "schema": schema}},
        purpose="dedupe",
        run_id=run_id,
    )
    try:
        data = json.loads(result)
        return data.get("are_duplicates", False)
    except Exception:
        return False


async def dedupe_records(
    records: list[dict],
    config: dict,
    run_id: str | None = None,
) -> list[dict]:
    """Full dedup pipeline."""
    threshold = config.get("threshold", 85)
    deduped, borderline_pairs = fuzzy_dedupe(records, threshold=threshold)

    # LLM adjudication for borderline pairs (70-threshold range)
    if not settings.is_demo:
        try:
            from rapidfuzz import fuzz
            keys = [_key_fields(r) for r in deduped]
            llm_dupes: set[int] = set()
            for i in range(len(deduped)):
                if i in llm_dupes:
                    continue
                for j in range(i + 1, len(deduped)):
                    if j in llm_dupes:
                        continue
                    score = fuzz.token_sort_ratio(keys[i], keys[j])
                    if 70 <= score < threshold:
                        is_dup = await llm_adjudicate_pair(deduped[i], deduped[j], run_id)
                        if is_dup:
                            logger.info(f"LLM adjudicated duplicate: records {i} and {j}")
                            llm_dupes.add(j)
                    if len(llm_dupes) >= 20:  # limit LLM calls
                        break
                if len(llm_dupes) >= 20:
                    break
            if llm_dupes:
                deduped = [r for idx, r in enumerate(deduped) if idx not in llm_dupes]
                logger.info(f"LLM adjudication removed {len(llm_dupes)} additional duplicates")
        except Exception as e:
            logger.warning(f"LLM adjudication failed: {e}")

    return deduped
