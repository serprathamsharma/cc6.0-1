"""Model Context Protocol (MCP) Server Router for ScoutIQ.

Exposes ScoutIQ's autonomous data gathering, provenance verification,
and natural language query capabilities to external AI agents (Cursor, Claude Desktop, etc.).
"""
from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db import get_db
from api.models.data import Record
from api.models.task import Task
from api.services.insights import generate_dataset_insights
from api.services.diff import compute_version_diff

router = APIRouter(prefix="/mcp", tags=["mcp"])

MCP_TOOLS = [
    {
        "name": "scoutiq_list_tasks",
        "description": "List all active and completed ScoutIQ data gathering tasks and datasets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of tasks to return", "default": 10},
            },
        },
    },
    {
        "name": "scoutiq_get_dataset_insights",
        "description": "Retrieve autonomous executive intelligence, statistical distributions, and anomaly alerts for a dataset run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID"},
                "run_id": {"type": "string", "description": "The run ID"},
            },
            "required": ["task_id", "run_id"],
        },
    },
    {
        "name": "scoutiq_query_records",
        "description": "Query verified records with provenance from a dataset run.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "The run ID"},
                "limit": {"type": "integer", "description": "Max records to return", "default": 20},
                "min_quality": {"type": "number", "description": "Minimum quality score threshold (0-100)", "default": 70.0},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "scoutiq_verify_provenance",
        "description": "Inspect the cryptographic source provenance, verbatim quote, and confidence meter for an extracted record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string", "description": "The record ID to inspect"},
            },
            "required": ["record_id"],
        },
    },
    {
        "name": "scoutiq_get_version_diff",
        "description": "Inspect structural diffs and evolution between dataset versions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "version_id": {"type": "string", "description": "The dataset version ID to compare with its predecessor"},
            },
            "required": ["version_id"],
        },
    },
]


@router.get("")
async def mcp_info():
    """Information endpoint describing ScoutIQ MCP capabilities."""
    return {
        "name": "ScoutIQ MCP Server",
        "version": "1.0.0",
        "protocol_version": "2024-11-05",
        "capabilities": {"tools": {"listChanged": False}},
        "tools_count": len(MCP_TOOLS),
    }


@router.post("")
async def handle_mcp_request(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Model Context Protocol (MCP) JSON-RPC requests."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON payload")

    method = body.get("method")
    req_id = body.get("id")
    params = body.get("params", {})

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "scoutiq_list_tasks":
            limit = args.get("limit", 10)
            res = await db.execute(select(Task).order_by(desc(Task.created_at)).limit(limit))
            tasks = res.scalars().all()
            content = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "latest_run_id": t.latest_run_id,
                }
                for t in tasks
            ]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(content, indent=2)}]},
            }

        elif tool_name == "scoutiq_get_dataset_insights":
            task_id = args.get("task_id")
            run_id = args.get("run_id")
            insights = await generate_dataset_insights(task_id, run_id, db)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(insights, indent=2)}]},
            }

        elif tool_name == "scoutiq_query_records":
            run_id = args.get("run_id")
            limit = args.get("limit", 20)
            min_q = args.get("min_quality", 70.0)
            stmt = (
                select(Record)
                .where(Record.run_id == run_id, Record.quality_score >= min_q)
                .limit(limit)
            )
            records = (await db.execute(stmt)).scalars().all()
            clean = [
                {"id": r.id, "quality_score": r.quality_score, "data": {k: v for k, v in r.data.items() if not k.startswith("_")}}
                for r in records
            ]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(clean, indent=2)}]},
            }

        elif tool_name == "scoutiq_verify_provenance":
            rec_id = args.get("record_id")
            stmt = (
                select(Record)
                .where(Record.id == rec_id)
                .options(selectinload(Record.field_values))
            )
            rec = (await db.execute(stmt)).scalar_one_or_none()
            if not rec:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Record not found"},
                }
            provenance = {
                "record_id": rec.id,
                "entity_type": rec.entity_type,
                "quality_score": rec.quality_score,
                "provenance_fields": [
                    {
                        "field": fv.field_name,
                        "value": fv.value_text,
                        "verified": fv.verified,
                        "confidence": fv.confidence,
                        "source_url": fv.source_url,
                        "evidence_quote": fv.evidence_snippet,
                        "extraction_method": fv.extraction_method,
                    }
                    for fv in rec.field_values
                ],
            }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(provenance, indent=2)}]},
            }

        elif tool_name == "scoutiq_get_version_diff":
            ver_id = args.get("version_id")
            diff = await compute_version_diff(ver_id, db)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(diff, indent=2)}]},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32600, "message": f"Unsupported MCP method: {method}"},
    }
