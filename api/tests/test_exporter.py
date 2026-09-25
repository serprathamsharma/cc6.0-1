"""Tests for exporter service."""
from __future__ import annotations

import json
import pytest
from api.services.exporter import export_json, export_csv, export_xlsx, export_parquet


SAMPLE_RECORDS = [
    {
        "title": "ML Intern",
        "company": "Google",
        "location": "Bangalore, India",
        "_source_url": "https://example.com/job/1",
        "_quality_score": 90.0,
        "_extraction_method": "fixture",
    },
    {
        "title": "Data Scientist",
        "company": "Meta",
        "location": "Mumbai, India",
        "_source_url": "https://example.com/job/2",
        "_quality_score": 85.0,
        "_extraction_method": "json_ld",
    },
]


def test_export_json():
    data = export_json(SAMPLE_RECORDS, include_provenance=True)
    parsed = json.loads(data)
    assert len(parsed) == 2
    assert parsed[0]["title"] == "ML Intern"


def test_export_json_no_provenance():
    data = export_json(SAMPLE_RECORDS, include_provenance=False)
    parsed = json.loads(data)
    # Should not have prov: keys
    for rec in parsed:
        for key in rec:
            assert not key.startswith("prov:"), f"Unexpected provenance key: {key}"


def test_export_csv():
    data = export_csv(SAMPLE_RECORDS, include_provenance=True)
    assert len(data) > 0
    lines = data.decode().split("\n")
    assert len(lines) >= 3  # header + 2 rows + optional blank
    assert "ML Intern" in data.decode()


def test_export_xlsx():
    data = export_xlsx(SAMPLE_RECORDS, include_provenance=True)
    assert len(data) > 0
    # Check it's a valid XLSX (starts with PK zip header)
    assert data[:4] == b'PK\x03\x04', "XLSX should start with PK header"


def test_export_parquet():
    data = export_parquet(SAMPLE_RECORDS, include_provenance=True)
    assert len(data) > 0
    # Parquet magic bytes: PAR1 at start and end
    assert data[:4] == b'PAR1', "Parquet should start with PAR1"


def test_export_empty_records():
    assert export_csv([], True) == b""
    assert export_json([], True) == b"[]"
    assert export_xlsx([], True) == b""
    assert export_parquet([], True) == b""
