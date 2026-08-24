"""W3C TraceContext (``traceparent`` / ``tracestate``) propagation helpers.

Implements generation and parsing of trace identifiers following the
W3C Trace Context specification (https://www.w3.org/TR/trace-context/).
"""
from __future__ import annotations

import os
from typing import Any

_TRACEPARENT_VERSION = "00"


def generate_trace_id() -> str:
    """Generate a random 32-hex-character trace ID."""
    return os.urandom(16).hex()


def generate_span_id() -> str:
    """Generate a random 16-hex-character span ID."""
    return os.urandom(8).hex()


def generate_traceparent(
    trace_id: str,
    span_id: str,
    sampled: bool = True,
) -> str:
    """Build a ``traceparent`` header value.

    Format: ``{version}-{trace_id}-{span_id}-{trace_flags}``
    """
    flags = "01" if sampled else "00"
    return f"{_TRACEPARENT_VERSION}-{trace_id}-{span_id}-{flags}"


def generate_tracestate(vendor_entries: dict[str, str]) -> str:
    """Build a ``tracestate`` header value from *vendor_entries*.

    Format: ``key=value,key=value``
    """
    return ",".join(f"{k}={v}" for k, v in vendor_entries.items())


def inject_trace_headers(
    headers: dict[str, str],
    trace_id: str,
    span_id: str,
    *,
    sampled: bool = True,
    vendor_entries: dict[str, str] | None = None,
) -> dict[str, str]:
    """Add ``traceparent`` (and optionally ``tracestate``) to *headers*.

    Returns the mutated *headers* dict for convenience.
    """
    headers["traceparent"] = generate_traceparent(trace_id, span_id, sampled)
    if vendor_entries:
        headers["tracestate"] = generate_tracestate(vendor_entries)
    return headers


def parse_traceparent(header: str) -> tuple[str, str, bool]:
    """Parse a ``traceparent`` header and return ``(trace_id, span_id, sampled)``.

    Raises ``ValueError`` for malformed headers.
    """
    parts = header.split("-")
    if len(parts) < 4:
        raise ValueError(f"Invalid traceparent header: expected 4 parts, got {len(parts)}")

    _version, trace_id, span_id, flags = parts[0], parts[1], parts[2], parts[3]

    if len(trace_id) != 32:
        raise ValueError(f"Invalid trace_id length: expected 32, got {len(trace_id)}")
    if len(span_id) != 16:
        raise ValueError(f"Invalid span_id length: expected 16, got {len(span_id)}")

    sampled = (int(flags, 16) & 0x01) == 1
    return trace_id, span_id, sampled
