"""Tests for fixture loading and record counts."""
from __future__ import annotations

import pytest
from api.services.fixtures import load_fixture, _jobs_fixture, _sponsors_fixture, _pricing_fixture


def test_jobs_fixture_count():
    records = _jobs_fixture()
    assert len(records) >= 50, f"Expected >= 50 job records, got {len(records)}"


def test_sponsors_fixture_count():
    records = _sponsors_fixture()
    assert len(records) >= 50, f"Expected >= 50 sponsor records, got {len(records)}"


def test_pricing_fixture_count():
    records = _pricing_fixture()
    assert len(records) >= 50, f"Expected >= 50 pricing records, got {len(records)}"


def test_jobs_fixture_required_fields():
    records = _jobs_fixture()
    required = ["title", "company", "location", "apply_link"]
    for rec in records:
        for field in required:
            assert field in rec, f"Missing field {field} in job record"


def test_sponsors_fixture_required_fields():
    records = _sponsors_fixture()
    required = ["company_name", "event_name", "sponsorship_tier"]
    for rec in records:
        for field in required:
            assert field in rec, f"Missing field {field} in sponsor record"


def test_pricing_fixture_required_fields():
    records = _pricing_fixture()
    required = ["product_name", "plan_name", "price_monthly", "pricing_url"]
    for rec in records:
        for field in required:
            assert field in rec, f"Missing field {field} in pricing record"


def test_all_fixtures_have_provenance():
    """Every record must have source_url and quality_score for traceability."""
    for entity_type in ["job_posting", "sponsor", "pricing_plan"]:
        records = load_fixture(entity_type)
        for rec in records:
            assert "_source_url" in rec, f"Missing _source_url in {entity_type} record"
            assert "_quality_score" in rec, f"Missing _quality_score in {entity_type} record"
            assert "_extraction_method" in rec


def test_fixture_quality_scores_in_range():
    for entity_type in ["job_posting", "sponsor", "pricing_plan"]:
        records = load_fixture(entity_type)
        for rec in records:
            score = rec.get("_quality_score", 0)
            assert 0 <= score <= 100, f"Quality score out of range: {score}"
