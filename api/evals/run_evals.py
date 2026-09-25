"""Evaluation harness for Scenarios A, B, C."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.fixtures import _jobs_fixture, _sponsors_fixture, _pricing_fixture
from api.services.deduper import fuzzy_dedupe


# Golden sets: minimum expected values for field coverage
GOLDEN_A = {
    "min_records": 50,
    "required_fields": ["title", "company", "location", "apply_link"],
    "quality_threshold": 70.0,
}
GOLDEN_B = {
    "min_records": 50,
    "required_fields": ["company_name", "event_name", "sponsorship_tier"],
    "quality_threshold": 65.0,
}
GOLDEN_C = {
    "min_records": 50,
    "required_fields": ["product_name", "plan_name", "price_monthly"],
    "quality_threshold": 75.0,
}


def evaluate_scenario(name: str, records: list[dict], golden: dict) -> dict:
    total = len(records)
    required = golden["required_fields"]
    threshold = golden["quality_threshold"]
    min_records = golden["min_records"]

    # Field coverage
    field_coverage: dict[str, float] = {}
    for field in required:
        filled = sum(1 for r in records if r.get(field))
        field_coverage[field] = filled / total if total > 0 else 0

    # Quality distribution
    scores = [r.get("_quality_score", 0) for r in records]
    avg_quality = sum(scores) / len(scores) if scores else 0
    above_threshold = sum(1 for s in scores if s >= threshold)

    # Dedupe precision
    deduped, pairs = fuzzy_dedupe(records, threshold=85)
    dedupe_ratio = len(deduped) / total if total > 0 else 1.0

    # Source coverage
    sources = set(r.get("_source_url", "") for r in records)

    passed = (
        total >= min_records
        and avg_quality >= threshold
        and all(v >= 0.8 for v in field_coverage.values())
    )

    return {
        "scenario": name,
        "total_records": total,
        "min_records_required": min_records,
        "field_coverage": {k: f"{v:.1%}" for k, v in field_coverage.items()},
        "avg_quality_score": round(avg_quality, 1),
        "quality_threshold": threshold,
        "records_above_threshold": above_threshold,
        "dedupe_ratio": round(dedupe_ratio, 3),
        "unique_sources": len(sources),
        "passed": passed,
    }


def main():
    print("=" * 60)
    print("ScoutIQ Evaluation Harness")
    print("=" * 60)

    scenarios = [
        ("A: AI/ML Internships India", _jobs_fixture(), GOLDEN_A),
        ("B: Delhi NCR Hackathon Sponsors", _sponsors_fixture(), GOLDEN_B),
        ("C: PM SaaS Pricing Plans", _pricing_fixture(), GOLDEN_C),
    ]

    results = []
    all_passed = True

    for name, records, golden in scenarios:
        result = evaluate_scenario(name, records, golden)
        results.append(result)
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"\n{status} {name}")
        print(f"  Records: {result['total_records']} (min: {result['min_records_required']})")
        print(f"  Avg Quality: {result['avg_quality_score']} (threshold: {result['quality_threshold']})")
        print(f"  Field Coverage: {result['field_coverage']}")
        print(f"  Dedupe Ratio: {result['dedupe_ratio']} ({result['unique_sources']} unique sources)")
        if not result["passed"]:
            all_passed = False

    # Save results
    output_path = Path(__file__).parent / "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL SCENARIOS PASSED")
    else:
        print("❌ SOME SCENARIOS FAILED")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
