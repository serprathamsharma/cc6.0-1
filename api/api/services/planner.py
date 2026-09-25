"""AI Planner: prompt -> RequirementSpec -> WorkflowDAG."""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from api.config.settings import settings
from api.services.llm import llm_call


TOOL_REGISTRY = [
    "discover_sources",
    "fetch_static",
    "fetch_dynamic",
    "extract_structured",
    "extract_llm",
    "paginate",
    "normalize",
    "validate",
    "dedupe",
    "enrich",
    "score",
]


class FieldSpec(BaseModel):
    name: str
    type: str  # string|number|date|url|boolean
    required: bool = True
    description: str = ""


class RequirementSpec(BaseModel):
    entity_type: str
    target_fields: list[FieldSpec]
    filters: dict[str, Any] = {}
    target_volume: int = 50
    freshness_days: int = 30
    preferred_sources: list[str] = []
    output_schema: dict = {}
    clarifying_questions: list[str] = []
    assumptions: list[str] = []


class DAGNode(BaseModel):
    id: str
    tool: str
    label: str
    config: dict = {}
    depends_on: list[str] = []
    estimated_time_s: float = 10.0
    estimated_cost_usd: float = 0.0


class WorkflowDAG(BaseModel):
    nodes: list[DAGNode]
    title: str = ""
    description: str = ""


PLANNER_SYSTEM = """You are ScoutIQ's workflow planner.
Your job:
1. Parse the user prompt into a RequirementSpec.
2. Build a WorkflowDAG using ONLY tools from the registry.
3. List any assumptions you made.
4. Return structured JSON.

Tool registry (you CANNOT invent tools outside this list):
discover_sources, fetch_static, fetch_dynamic, extract_structured, extract_llm,
paginate, normalize, validate, dedupe, enrich, score

Rules:
- Prefer structured/API sources over scraping.
- Always end with: normalize -> validate -> dedupe -> score
- Never fabricate data. Never plan to access paywalled/login-walled content.
- If the request asks for illegal or private data, set entity_type="REFUSED" and explain."""


async def plan_workflow(
    prompt: str,
    run_id: str | None = None,
) -> tuple[RequirementSpec, WorkflowDAG, list[str]]:
    """Return (RequirementSpec, WorkflowDAG, assumptions)."""

    if settings.is_demo:
        return _demo_plan(prompt)

    schema = {
        "type": "object",
        "properties": {
            "requirement_spec": {
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string"},
                    "target_fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "required": {"type": "boolean"},
                                "description": {"type": "string"},
                            },
                            "required": ["name", "type", "required", "description"],
                            "additionalProperties": False,
                        },
                    },
                    "filters": {"type": "object"},
                    "target_volume": {"type": "integer"},
                    "freshness_days": {"type": "integer"},
                    "preferred_sources": {"type": "array", "items": {"type": "string"}},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                    "clarifying_questions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["entity_type", "target_fields", "filters", "target_volume",
                             "freshness_days", "preferred_sources", "assumptions",
                             "clarifying_questions"],
                "additionalProperties": False,
            },
            "dag": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "nodes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "tool": {"type": "string"},
                                "label": {"type": "string"},
                                "config": {"type": "object"},
                                "depends_on": {"type": "array", "items": {"type": "string"}},
                                "estimated_time_s": {"type": "number"},
                                "estimated_cost_usd": {"type": "number"},
                            },
                            "required": ["id", "tool", "label", "config", "depends_on",
                                        "estimated_time_s", "estimated_cost_usd"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "description", "nodes"],
                "additionalProperties": False,
            },
        },
        "required": ["requirement_spec", "dag"],
        "additionalProperties": False,
    }

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"User prompt: {prompt}"},
    ]

    result = await llm_call(
        model=settings.model_planner,
        messages=messages,
        response_format={"type": "json_schema", "json_schema": {"name": "plan", "strict": True, "schema": schema}},
        purpose="plan",
        run_id=run_id,
    )

    data = json.loads(result)
    spec = RequirementSpec(**data["requirement_spec"])
    dag = WorkflowDAG(**data["dag"])
    # Validate all tools are in registry
    for node in dag.nodes:
        if node.tool not in TOOL_REGISTRY:
            node.tool = "fetch_static"  # safe fallback
    return spec, dag, spec.assumptions


def _demo_plan(prompt: str) -> tuple[RequirementSpec, WorkflowDAG, list[str]]:
    """Return a canned plan based on prompt keywords for demo mode."""
    p = prompt.lower()

    if "intern" in p or "job" in p or "ml" in p or "ai" in p:
        return _plan_a()
    elif "sponsor" in p or "hackathon" in p or "event" in p:
        return _plan_b()
    else:
        return _plan_c()


def _plan_a() -> tuple[RequirementSpec, WorkflowDAG, list[str]]:
    spec = RequirementSpec(
        entity_type="job_posting",
        target_fields=[
            FieldSpec(name="title", type="string", required=True, description="Job title"),
            FieldSpec(name="company", type="string", required=True, description="Company name"),
            FieldSpec(name="location", type="string", required=True, description="Location"),
            FieldSpec(name="stipend", type="string", required=False, description="Stipend/salary"),
            FieldSpec(name="skills", type="string", required=False, description="Required skills"),
            FieldSpec(name="apply_link", type="url", required=True, description="Apply URL"),
            FieldSpec(name="posted_at", type="date", required=False, description="Posted date"),
        ],
        filters={"location": "India", "type": "internship", "domains": ["AI", "ML"], "freshness_days": 30},
        target_volume=60,
        freshness_days=30,
        preferred_sources=["linkedin.com", "internshala.com", "unstop.com", "wellfound.com"],
        assumptions=[
            "Targeting internship roles in AI/ML domain",
            "Location filter: India (any city)",
            "Product companies preferred over service companies",
            "Running in DEMO MODE with fixture data",
        ],
    )
    dag = WorkflowDAG(
        title="AI/ML Internships India",
        description="Discover and extract AI/ML internship postings in India from job boards",
        nodes=[
            DAGNode(id="n1", tool="discover_sources", label="Discover Job Boards", config={"query": "AI ML internship India product company 2024", "sources": ["internshala", "linkedin", "unstop"]}, depends_on=[], estimated_time_s=5, estimated_cost_usd=0.01),
            DAGNode(id="n2", tool="fetch_static", label="Fetch Listings", config={"max_pages": 10}, depends_on=["n1"], estimated_time_s=20, estimated_cost_usd=0.0),
            DAGNode(id="n3", tool="extract_structured", label="Extract JSON-LD", config={"schema": "JobPosting"}, depends_on=["n2"], estimated_time_s=10, estimated_cost_usd=0.0),
            DAGNode(id="n4", tool="extract_llm", label="LLM Extract Fields", config={"fields": ["stipend", "skills", "apply_link"]}, depends_on=["n3"], estimated_time_s=30, estimated_cost_usd=0.05),
            DAGNode(id="n5", tool="normalize", label="Normalize", config={}, depends_on=["n4"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n6", tool="validate", label="Validate", config={}, depends_on=["n5"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n7", tool="dedupe", label="Deduplicate", config={"threshold": 85}, depends_on=["n6"], estimated_time_s=10, estimated_cost_usd=0.02),
            DAGNode(id="n8", tool="score", label="Quality Score", config={}, depends_on=["n7"], estimated_time_s=3, estimated_cost_usd=0.0),
        ],
    )
    return spec, dag, spec.assumptions


def _plan_b() -> tuple[RequirementSpec, WorkflowDAG, list[str]]:
    spec = RequirementSpec(
        entity_type="sponsor",
        target_fields=[
            FieldSpec(name="company_name", type="string", required=True, description="Sponsor company"),
            FieldSpec(name="event_name", type="string", required=True, description="Event sponsored"),
            FieldSpec(name="sponsorship_tier", type="string", required=False, description="Gold/Silver/Bronze etc."),
            FieldSpec(name="contact_page", type="url", required=False, description="Contact URL"),
            FieldSpec(name="event_date", type="date", required=False, description="Event date"),
            FieldSpec(name="location", type="string", required=True, description="Event location"),
        ],
        filters={"location": "Delhi/NCR", "category": "tech hackathon developer event"},
        target_volume=60,
        freshness_days=365,
        preferred_sources=["devfolio.co", "unstop.com", "mlh.io", "meetup.com"],
        assumptions=[
            "Targeting sponsor companies at tech/dev events in Delhi NCR",
            "Events from last 1 year considered",
            "Running in DEMO MODE with fixture data",
        ],
    )
    dag = WorkflowDAG(
        title="Delhi NCR Hackathon Sponsors",
        description="Find companies that sponsored tech hackathons in Delhi/NCR",
        nodes=[
            DAGNode(id="n1", tool="discover_sources", label="Discover Event Platforms", config={"query": "hackathon developer event sponsor Delhi NCR"}, depends_on=[], estimated_time_s=5, estimated_cost_usd=0.01),
            DAGNode(id="n2", tool="fetch_static", label="Fetch Event Pages", config={"max_pages": 15}, depends_on=["n1"], estimated_time_s=25, estimated_cost_usd=0.0),
            DAGNode(id="n3", tool="extract_llm", label="Extract Sponsor Info", config={"fields": ["company_name", "sponsorship_tier", "contact_page"]}, depends_on=["n2"], estimated_time_s=40, estimated_cost_usd=0.08),
            DAGNode(id="n4", tool="enrich", label="Enrich Contact Pages", config={}, depends_on=["n3"], estimated_time_s=20, estimated_cost_usd=0.0),
            DAGNode(id="n5", tool="normalize", label="Normalize", config={}, depends_on=["n4"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n6", tool="validate", label="Validate", config={}, depends_on=["n5"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n7", tool="dedupe", label="Deduplicate", config={"threshold": 80}, depends_on=["n6"], estimated_time_s=10, estimated_cost_usd=0.02),
            DAGNode(id="n8", tool="score", label="Quality Score", config={}, depends_on=["n7"], estimated_time_s=3, estimated_cost_usd=0.0),
        ],
    )
    return spec, dag, spec.assumptions


def _plan_c() -> tuple[RequirementSpec, WorkflowDAG, list[str]]:
    spec = RequirementSpec(
        entity_type="pricing_plan",
        target_fields=[
            FieldSpec(name="product_name", type="string", required=True, description="SaaS product name"),
            FieldSpec(name="plan_name", type="string", required=True, description="Plan tier name"),
            FieldSpec(name="price_monthly", type="string", required=True, description="Monthly price"),
            FieldSpec(name="price_annual", type="string", required=False, description="Annual price"),
            FieldSpec(name="features", type="string", required=False, description="Key features"),
            FieldSpec(name="pricing_url", type="url", required=True, description="Pricing page URL"),
            FieldSpec(name="currency", type="string", required=False, description="Currency"),
        ],
        filters={"category": "project management SaaS", "top_n": 20},
        target_volume=60,
        freshness_days=7,
        preferred_sources=["asana.com", "notion.so", "monday.com", "clickup.com", "linear.app", "trello.com", "basecamp.com", "jira.atlassian.com"],
        assumptions=[
            "Top 20 project management SaaS tools by market share",
            "All pricing tiers extracted per product",
            "Running in DEMO MODE with fixture data",
        ],
    )
    dag = WorkflowDAG(
        title="PM SaaS Pricing Plans",
        description="Collect pricing plans from top 20 project-management SaaS tools",
        nodes=[
            DAGNode(id="n1", tool="discover_sources", label="List Top 20 PM Tools", config={"query": "top project management SaaS pricing plans 2024"}, depends_on=[], estimated_time_s=5, estimated_cost_usd=0.01),
            DAGNode(id="n2", tool="fetch_static", label="Fetch Pricing Pages", config={"max_pages": 20, "url_pattern": "/pricing"}, depends_on=["n1"], estimated_time_s=30, estimated_cost_usd=0.0),
            DAGNode(id="n3", tool="extract_structured", label="Extract JSON-LD Prices", config={"schema": "Offer"}, depends_on=["n2"], estimated_time_s=10, estimated_cost_usd=0.0),
            DAGNode(id="n4", tool="extract_llm", label="LLM Extract Pricing Table", config={"fields": ["plan_name", "price_monthly", "price_annual", "features"]}, depends_on=["n3"], estimated_time_s=60, estimated_cost_usd=0.12),
            DAGNode(id="n5", tool="normalize", label="Normalize Prices", config={"currency": "USD"}, depends_on=["n4"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n6", tool="validate", label="Validate", config={}, depends_on=["n5"], estimated_time_s=5, estimated_cost_usd=0.0),
            DAGNode(id="n7", tool="dedupe", label="Deduplicate", config={"threshold": 90}, depends_on=["n6"], estimated_time_s=8, estimated_cost_usd=0.01),
            DAGNode(id="n8", tool="score", label="Quality Score", config={}, depends_on=["n7"], estimated_time_s=3, estimated_cost_usd=0.0),
        ],
    )
    return spec, dag, spec.assumptions
