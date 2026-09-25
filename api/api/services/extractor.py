"""Extractor: JSON-LD, selector, LLM extraction with anti-hallucination."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from api.config.settings import settings
from api.services.llm import llm_call


def extract_jsonld(html: str, schema_type: str = "") -> list[dict]:
    """Extract JSON-LD structured data from HTML."""
    try:
        import extruct
        data = extruct.extract(html, uniform=True, syntaxes=["json-ld", "microdata", "opengraph"])
        results = []
        for item in data.get("json-ld", []):
            if not schema_type or item.get("@type", "") == schema_type:
                results.append(item)
        return results
    except Exception as e:
        logger.warning(f"JSON-LD extract failed: {e}")
        return []


def verify_snippet(text: str, snippet: str) -> bool:
    """Verify that a snippet exists in the source text (anti-hallucination)."""
    if not snippet or not text:
        return False
    # Normalize whitespace
    norm_text = re.sub(r'\s+', ' ', text).lower()
    norm_snippet = re.sub(r'\s+', ' ', snippet[:100]).lower()
    return norm_snippet in norm_text


async def extract_with_llm(
    text: str,
    fields: list[dict],
    source_url: str,
    run_id: str | None = None,
) -> list[dict]:
    """Use LLM to extract fields from text with anti-hallucination."""
    if settings.is_demo or not text:
        return []

    field_list = json.dumps(fields, indent=2)
    system = """You are a structured data extractor. Extract the requested fields from the source text.
For each field, return:
- value: the extracted value (null if not found)
- evidence: the verbatim quote from the source text that supports this value (max 150 chars)
- confidence: 0.0-1.0

Rules:
- Only return values you can find in the source text.
- The evidence MUST be a verbatim substring of the source text.
- Never invent or infer values not present in the text."""

    schema = {
        "type": "object",
        "properties": {
            "records": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "value": {},
                                    "evidence": {"type": "string"},
                                    "confidence": {"type": "number"},
                                },
                                "required": ["evidence", "confidence"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["fields"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["records"],
        "additionalProperties": False,
    }

    # Truncate text to avoid token limits
    chunk = text[:6000]
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Fields to extract:\n{field_list}\n\nSource text (from {source_url}):\n{chunk}"},
    ]

    result = await llm_call(
        model=settings.model_extract,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"name": "extraction", "strict": True, "schema": schema}},
        purpose="extract",
        run_id=run_id,
    )

    try:
        data = json.loads(result)
        extracted = []
        for record in data.get("records", []):
            rec: dict[str, Any] = {"_source_url": source_url, "_extraction_method": "llm"}
            for fname, fdata in record.get("fields", {}).items():
                value = fdata.get("value")
                evidence = fdata.get("evidence", "")
                confidence = fdata.get("confidence", 0.0)
                # Anti-hallucination check
                verified = verify_snippet(chunk, evidence) if evidence else False
                if not verified and evidence:
                    logger.warning(f"Evidence not verified for field {fname}: {evidence[:50]}")
                    confidence = 0.0  # flag but keep
                rec[fname] = value
                rec[f"_evidence_{fname}"] = evidence
                rec[f"_confidence_{fname}"] = confidence
                rec[f"_verified_{fname}"] = verified
            extracted.append(rec)
        return extracted
    except Exception as e:
        logger.error(f"LLM extract parse failed: {e}")
        return []


async def extract_records(
    existing: list[dict],
    requirement_spec: dict,
    config: dict,
    run_id: str | None = None,
) -> list[dict]:
    """Run extraction pipeline."""
    return existing  # real extraction happens in fetch+extract flow
