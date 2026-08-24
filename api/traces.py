"""Traces read API -- GET /api/traces, GET /api/traces/{trace_id}.

Modeled on Enterprise's _query_traces/get_trace query shape (api/main.py),
reading only the OSS column set: no team/tenant-attribution rows beyond the
single implicit tenant, no optimization-stage-report/reuse-score columns.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_auth
from db import get_client

router = APIRouter(prefix="/api", tags=["traces"])

_COLUMNS = """
    toString(event_id) AS event_id, trace_id, span_id, tenant_id, project_id,
    feature_id, user_id, provider, model, request_type,
    input_tokens, output_tokens, total_tokens,
    input_tokens_before, input_tokens_saved,
    input_cost_usd, output_cost_usd, total_cost_usd,
    latency_ms, ttft_ms, finish_reason, status, error_message,
    toString(request_timestamp) AS request_timestamp,
    toString(ingestion_timestamp) AS ingestion_timestamp,
    prompt_text, completion_text, agent_name, parent_span_id
"""


@router.get("/traces")
def list_traces(
    limit: int = Query(50, le=500),
    offset: int = 0,
    auth=Depends(require_auth),
) -> list[dict]:
    ch = get_client()
    result = ch.query(
        f"SELECT {_COLUMNS} FROM tokensight.llm_events "
        "WHERE tenant_id = {tenant_id:String} "
        "ORDER BY request_timestamp DESC "
        "LIMIT {limit:UInt32} OFFSET {offset:UInt32}",
        parameters={
            "tenant_id": auth["tenant_id"],
            "limit": limit,
            "offset": offset,
        },
    )
    return [dict(zip(result.column_names, row)) for row in result.result_rows]


@router.get("/traces/{trace_id}")
def get_trace(trace_id: str, auth=Depends(require_auth)) -> dict:
    ch = get_client()
    result = ch.query(
        f"SELECT {_COLUMNS} FROM tokensight.llm_events "
        "WHERE trace_id = {trace_id:String} AND tenant_id = {tenant_id:String} "
        "ORDER BY request_timestamp",
        parameters={"trace_id": trace_id, "tenant_id": auth["tenant_id"]},
    )
    if not result.result_rows:
        raise HTTPException(status_code=404, detail="Trace not found")
    rows = [dict(zip(result.column_names, row)) for row in result.result_rows]
    return rows[0] if len(rows) == 1 else {"trace_id": trace_id, "events": rows}


@router.get("/spend/summary")
def spend_summary(auth=Depends(require_auth)) -> dict:
    """Basic aggregate KPIs for the Overview dashboard: requests, tokens,
    cost, average latency. No team/org attribution, no forecasting."""
    ch = get_client()
    result = ch.query(
        "SELECT count() AS requests, sum(input_tokens) AS input_tokens, "
        "sum(output_tokens) AS output_tokens, sum(total_cost_usd) AS total_cost_usd, "
        "avg(latency_ms) AS avg_latency_ms "
        "FROM tokensight.llm_events WHERE tenant_id = {tenant_id:String}",
        parameters={"tenant_id": auth["tenant_id"]},
    )
    row = result.result_rows[0] if result.result_rows else (0, 0, 0, 0.0, 0.0)
    return dict(zip(result.column_names, row))
