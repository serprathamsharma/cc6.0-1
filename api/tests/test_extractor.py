"""Tests for extractor service."""
from __future__ import annotations

import pytest
from api.services.extractor import verify_snippet, extract_jsonld


def test_verify_snippet_found():
    text = "This is a sample job posting at Google for ML Engineer role."
    snippet = "job posting at Google"
    assert verify_snippet(text, snippet) is True


def test_verify_snippet_not_found():
    text = "This is a sample job posting at Google."
    snippet = "Microsoft Senior Developer"
    assert verify_snippet(text, snippet) is False


def test_verify_snippet_case_insensitive():
    text = "ML INTERNSHIP AT SWIGGY"
    snippet = "ml internship at swiggy"
    assert verify_snippet(text, snippet) is True


def test_verify_snippet_empty():
    assert verify_snippet("", "something") is False
    assert verify_snippet("text", "") is False


def test_extract_jsonld_empty_html():
    results = extract_jsonld("", "JobPosting")
    assert results == []


def test_extract_jsonld_with_job_posting():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type": "JobPosting", "title": "ML Engineer", "hiringOrganization": {"name": "Google"}}
    </script>
    </head><body></body></html>
    """
    results = extract_jsonld(html, "JobPosting")
    assert len(results) >= 1
    assert results[0]["@type"] == "JobPosting"
