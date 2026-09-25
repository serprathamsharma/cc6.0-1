"""Unit tests for planner service."""
from __future__ import annotations

import pytest
from api.services.planner import (
    TOOL_REGISTRY,
    _plan_a,
    _plan_b,
    _plan_c,
    _demo_plan,
)


def test_tool_registry_contains_required_tools():
    required = [
        "discover_sources", "fetch_static", "fetch_dynamic",
        "extract_structured", "extract_llm", "paginate",
        "normalize", "validate", "dedupe", "enrich", "score",
    ]
    for tool in required:
        assert tool in TOOL_REGISTRY, f"{tool} missing from registry"


def test_plan_a_nodes_are_valid():
    spec, dag, assumptions = _plan_a()
    assert spec.entity_type == "job_posting"
    assert len(dag.nodes) >= 5
    for node in dag.nodes:
        assert node.tool in TOOL_REGISTRY, f"Invalid tool: {node.tool}"
    assert len(assumptions) > 0
    # Must end with score node
    assert dag.nodes[-1].tool == "score"


def test_plan_b_nodes_are_valid():
    spec, dag, _ = _plan_b()
    assert spec.entity_type == "sponsor"
    assert len(dag.nodes) >= 5
    for node in dag.nodes:
        assert node.tool in TOOL_REGISTRY


def test_plan_c_nodes_are_valid():
    spec, dag, _ = _plan_c()
    assert spec.entity_type == "pricing_plan"
    assert len(dag.nodes) >= 5
    for node in dag.nodes:
        assert node.tool in TOOL_REGISTRY


def test_demo_plan_routing():
    spec_a, _, _ = _demo_plan("Find AI/ML internships in India")
    assert spec_a.entity_type == "job_posting"

    spec_b, _, _ = _demo_plan("Find hackathon sponsors in Delhi")
    assert spec_b.entity_type == "sponsor"

    spec_c, _, _ = _demo_plan("Collect pricing plans for SaaS tools")
    assert spec_c.entity_type == "pricing_plan"


def test_dag_dependency_order():
    """Nodes that depend on others must come after them."""
    _, dag, _ = _plan_a()
    completed: set[str] = set()
    for node in dag.nodes:
        for dep in node.depends_on:
            assert dep in completed, f"{node.id} depends on {dep} which hasn't appeared yet"
        completed.add(node.id)
