"""Trace ingestion: SDKs POST events here.

Modeled on Enterprise's api/batch_ingest.py (the closest-to-OSS-shaped
existing path), trimmed to base-observation fields only. Deliberately does
NOT call anything like Enterprise's waste_engine/cache_simulator/audit_trail
(those ran inline on every request in Enterprise's legacy /ingest handler --
excluded here on purpose, not an oversight).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from auth import require_auth
from db import get_client
from pricing import estimate_cost

router = APIRouter(prefix="/api", tags=["ingest"])


def _row_from_event(event: dict, tenant_id: str) -> list:
    trace_id = event.get("trace_id") or f"tr-{uuid.uuid4().hex[:16]}"
    span_id = event.get("span_id") or f"sp-{uuid.uuid4().hex[:12]}"
    model = event.get("model", "")
    input_tokens = int(event.get("input_tokens", 0) or 0)
    output_tokens = int(event.get("output_tokens", 0) or 0)
    input_cost, output_cost = estimate_cost(model, input_tokens, output_tokens)

    return [
        trace_id,
        span_id,
        tenant_id,
        event.get("project_id", "") or "",
        event.get("feature_id", "") or "",
        event.get("user_id", "") or "",
        event.get("provider", "") or "",
        model,
        event.get("request_type", "chat") or "chat",
        input_tokens,
        output_tokens,
        int(event.get("input_tokens_before", 0) or 0),
        int(event.get("input_tokens_saved", 0) or 0),
        input_cost,
        output_cost,
        float(event.get("latency_ms", 0) or 0),
        float(event.get("ttft_ms", 0) or 0),
        event.get("finish_reason", "") or "",
        event.get("status", "success") or "success",
        event.get("error_message", "") or "",
        (event.get("prompt_text") or "")[:8000],
        (event.get("completion_text") or "")[:8000],
        event.get("agent_name", "") or "",
        event.get("parent_span_id", "") or "",
        datetime.now(timezone.utc),
    ]


_COLUMNS = [
    "trace_id", "span_id", "tenant_id", "project_id", "feature_id", "user_id",
    "provider", "model", "request_type", "input_tokens", "output_tokens",
    "input_tokens_before", "input_tokens_saved", "input_cost_usd",
    "output_cost_usd", "latency_ms", "ttft_ms", "finish_reason", "status",
    "error_message", "prompt_text", "completion_text", "agent_name",
    "parent_span_id", "request_timestamp",
]


@router.post("/ingest")
def ingest_single(event: dict, auth=Depends(require_auth)) -> dict:
    row = _row_from_event(event, auth["tenant_id"])
    get_client().insert("tokensight.llm_events", [row], column_names=_COLUMNS)
    return {"ok": True, "trace_id": row[0]}


@router.post("/ingest/batch")
def ingest_batch(body: dict, auth=Depends(require_auth)) -> dict:
    events = body.get("events", [])
    rows = [_row_from_event(e, auth["tenant_id"]) for e in events]
    if rows:
        get_client().insert("tokensight.llm_events", rows, column_names=_COLUMNS)
    return {"ok": True, "count": len(rows)}
