"""Helpers to attach TokenSight control-plane headers for external agent
frameworks that want basic parent/child trace correlation."""
from __future__ import annotations

from typing import Optional

HEADER_SESSION_ID = "X-TokenSight-Session-ID"
HEADER_AGENT_ID = "X-TokenSight-Agent-ID"
HEADER_PARENT_TRACE_ID = "X-TokenSight-Parent-Trace-ID"
HEADER_PARENT_SPAN_ID = "X-TokenSight-Parent-Span-ID"


def agent_headers(
    *,
    session_id: str = "",
    agent_id: str = "",
    parent_trace_id: str = "",
    parent_span_id: str = "",
) -> dict[str, str]:
    out: dict[str, str] = {}
    if session_id:
        out[HEADER_SESSION_ID] = session_id
    if agent_id:
        out[HEADER_AGENT_ID] = agent_id
    if parent_trace_id:
        out[HEADER_PARENT_TRACE_ID] = parent_trace_id
    if parent_span_id:
        out[HEADER_PARENT_SPAN_ID] = parent_span_id
    return out


def merge_agent_headers(
    headers: Optional[dict[str, str]] = None,
    *,
    session_id: str = "",
    agent_id: str = "",
    parent_trace_id: str = "",
    parent_span_id: str = "",
) -> dict[str, str]:
    merged = dict(headers or {})
    merged.update(
        agent_headers(
            session_id=session_id, agent_id=agent_id,
            parent_trace_id=parent_trace_id, parent_span_id=parent_span_id,
        )
    )
    return merged
