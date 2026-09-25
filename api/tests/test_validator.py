"""Tests for validator service."""
from __future__ import annotations

import pytest
import asyncio
from api.services.validator import (
    mask_pii,
    normalize_url,
    score_record,
    validate_records,
)


def test_mask_personal_email():
    value = "Contact john.doe@gmail.com for more info"
    masked, was_masked = mask_pii(value)
    assert was_masked
    assert "[REDACTED]" in masked
    assert "@gmail.com" not in masked


def test_keep_business_email():
    value = "Contact hr@swiggy.com for inquiries"
    masked, was_masked = mask_pii(value)
    assert not was_masked
    assert masked == value


def test_normalize_url_adds_https():
    url = normalize_url("example.com/jobs")
    assert url and url.startswith("https://")


def test_normalize_url_keeps_existing():
    url = normalize_url("https://example.com/jobs")
    assert url == "https://example.com/jobs"


def test_normalize_url_empty():
    assert normalize_url("") is None
    assert normalize_url(None) is None


def test_score_record_full():
    rec = {"title": "Engineer", "company": "ACME", "location": "India"}
    score, flags = score_record(rec, required_fields=["title", "company", "location"])
    assert score == 100.0
    assert flags == []


def test_score_record_missing_required():
    rec = {"title": "Engineer"}
    score, flags = score_record(rec, required_fields=["title", "company", "location"])
    assert score < 100.0
    assert any("missing_required" in f for f in flags)


def test_score_record_low_confidence():
    rec = {"title": "Engineer", "_confidence_title": 0.3}
    score, flags = score_record(rec, required_fields=[])
    assert score < 100.0
    assert any("low_confidence" in f for f in flags)


def test_validate_records_async():
    records = [
        {"title": "ML Intern", "company": "Google", "email": "john@gmail.com"},
    ]
    result = asyncio.run(validate_records(records))
    assert len(result) == 1
    rec = result[0]
    assert rec["_pii_flagged"] is True
    assert "[REDACTED]" in rec["email"]
    assert "_quality_score" in rec
