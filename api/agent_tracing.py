"""Basic agent tracing: request -> model -> tokens -> latency -> result,
with parent/child span linkage.

Modeled on Enterprise's AgentSpanIngest/AgentSpan shape
(api/agent_observability.py), trimmed: no OTel span ingestion, no
session-graph (agent-to-agent tracking), no cost-breakdown/failure-point/
tool-usage analytics endpoints -- those are Enterprise "advanced
observability".
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_auth
from db import get_client

router = APIRouter(prefix="/api/agents", tags=["agents"])

StepType = Literal[
    "reasoning", "tool_call", "llm_call", "api_call", "db_query", "final",
]


class AgentSpanIngest(BaseModel):
    trace_id: str
    span_id: Optional[str] = None
    parent_span_id: str = ""
    agent_id: str = ""
    agent_name: str = ""
    step_type: StepType = "llm_call"
    step_name: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "success"
    error_message: str = ""


_COLUMNS = [
    "span_id", "trace_id", "parent_span_id", "tenant_id", "agent_id",
    "agent_name", "step_type", "step_name", "input_tokens", "output_tokens",
    "cost_usd", "latency_ms", "status", "error_message", "started_at",
    "finished_at",
]


@router.post("/spans")
def ingest_span(span: AgentSpanIngest, auth=Depends(require_auth)) -> dict:
    span_id = span.span_id or f"span-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    get_client().insert(
        "tokensight.agent_spans",
        [[
            span_id, span.trace_id, span.parent_span_id, auth["tenant_id"],
            span.agent_id, span.agent_name, span.step_type, span.step_name,
            span.input_tokens, span.output_tokens, span.cost_usd,
            span.latency_ms, span.status, span.error_message, now, now,
        ]],
        column_names=_COLUMNS,
    )
    return {"ok": True, "span_id": span_id}


@router.get("/spans/{trace_id}")
def list_spans(trace_id: str, auth=Depends(require_auth)) -> list[dict]:
    ch = get_client()
    result = ch.query(
        "SELECT span_id, trace_id, parent_span_id, agent_id, agent_name, "
        "step_type, step_name, input_tokens, output_tokens, cost_usd, "
        "latency_ms, status, error_message, "
        "toString(started_at) AS started_at, toString(finished_at) AS finished_at "
        "FROM tokensight.agent_spans "
        "WHERE trace_id = {trace_id:String} AND tenant_id = {tenant_id:String} "
        "ORDER BY started_at",
        parameters={"trace_id": trace_id, "tenant_id": auth["tenant_id"]},
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]
