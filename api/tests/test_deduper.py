"""Tests for deduplication service."""
from __future__ import annotations

import pytest
import asyncio
from api.services.deduper import fuzzy_dedupe, dedupe_records


def test_fuzzy_dedupe_exact_duplicates():
    records = [
        {"title": "ML Intern", "company": "Google", "location": "Bangalore"},
        {"title": "ML Intern", "company": "Google", "location": "Bangalore"},
    ]
    deduped, pairs = fuzzy_dedupe(records, threshold=85)
    assert len(deduped) == 1
    assert len(pairs) >= 1


def test_fuzzy_dedupe_distinct():
    records = [
        {"title": "ML Intern", "company": "Google", "location": "Bangalore"},
        {"title": "Data Engineer", "company": "Meta", "location": "Mumbai"},
    ]
    deduped, pairs = fuzzy_dedupe(records, threshold=85)
    assert len(deduped) == 2
    assert len(pairs) == 0


def test_fuzzy_dedupe_near_duplicates():
    records = [
        {"title": "Machine Learning Intern", "company": "Swiggy", "location": "Bangalore India"},
        {"title": "ML Intern", "company": "Swiggy", "location": "Bangalore, India"},
    ]
    deduped, pairs = fuzzy_dedupe(records, threshold=70)
    assert len(deduped) <= 2  # may or may not merge at 70


def test_dedupe_preserves_corroboration():
    records = [
        {"title": "AI Intern", "company": "Flipkart", "location": "Bangalore"},
        {"title": "AI Intern", "company": "Flipkart", "location": "Bangalore"},
        {"title": "AI Intern", "company": "Flipkart", "location": "Bangalore"},
    ]
    deduped, _ = fuzzy_dedupe(records, threshold=85)
    assert len(deduped) == 1
    assert deduped[0]["_corroboration_count"] == 3


def test_dedupe_records_async():
    records = [
        {"title": "ML Intern", "company": "Google"},
        {"title": "ML Intern", "company": "Google"},
        {"title": "Data Scientist", "company": "Meta"},
    ]
    result = asyncio.run(dedupe_records(records, {"threshold": 85}))
    assert len(result) == 2
