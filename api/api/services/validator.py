"""Validator: type coercion, normalization, quality scoring, PII masking."""
from __future__ import annotations

import re
from urllib.parse import urlparse


# PII patterns to mask
_PERSONAL_EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@(?:gmail|yahoo|hotmail|outlook|protonmail|icloud)\.com',
    re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')


def mask_pii(value: str) -> tuple[str, bool]:
    """Mask personal email addresses. Return (masked_value, was_masked)."""
    if _PERSONAL_EMAIL_RE.search(value):
        masked = _PERSONAL_EMAIL_RE.sub('[REDACTED]', value)
        return masked, True
    return value, False


def normalize_url(url: str) -> str | None:
    """Normalize and validate a URL."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            return url
    except Exception:
        pass
    return None


def score_record(record: dict, required_fields: list[str]) -> tuple[float, list[str]]:
    """Compute quality score 0-100 and return flags."""
    flags = []
    score = 100.0

    # Required fields missing
    for f in required_fields:
        if not record.get(f):
            flags.append(f"missing_required:{f}")
            score -= 20

    # Low-confidence fields
    for k, v in record.items():
        if k.startswith('_confidence_') and isinstance(v, float) and v < 0.5:
            flags.append(f"low_confidence:{k[12:]}")
            score -= 5

    # Unverified evidence
    for k, v in record.items():
        if k.startswith('_verified_') and v is False:
            flags.append(f"unverified_evidence:{k[10:]}")
            score -= 10

    return max(0.0, min(100.0, score)), flags


async def validate_records(records: list[dict]) -> list[dict]:
    """Validate, normalize, and score all records."""
    validated = []
    for rec in records:
        cleaned = dict(rec)
        pii_flagged = False

        # Normalize URLs
        for k, v in cleaned.items():
            if isinstance(v, str) and ('url' in k.lower() or 'link' in k.lower()):
                cleaned[k] = normalize_url(v)

        # Mask PII
        for k, v in list(cleaned.items()):
            if isinstance(v, str):
                masked, was_masked = mask_pii(v)
                if was_masked:
                    cleaned[k] = masked
                    pii_flagged = True

        score, flags = score_record(cleaned, [])
        cleaned['_quality_score'] = score
        cleaned['_quality_flags'] = flags
        cleaned['_pii_flagged'] = pii_flagged
        cleaned['_is_quarantined'] = score < 40
        cleaned['_quarantine_reasons'] = [f for f in flags if 'missing_required' in f] if score < 40 else []
        validated.append(cleaned)
    return validated
