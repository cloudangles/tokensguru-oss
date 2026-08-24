"""TokenSight tracking wrapper for `cohere.Client` -- pure observation."""
from __future__ import annotations

import time
import uuid
from typing import Any

from .context import get_current_context
from .cost import calculate_cost
from .exporter import HttpExporter


class _ChatWrapper:
    def __init__(self, client: Any, exporter: HttpExporter) -> None:
        self._client = client
        self._exporter = exporter

    def __call__(self, **kwargs: Any) -> Any:
        start_ns = time.perf_counter_ns()
        response = self._client.chat(**kwargs)
        latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

        ctx = get_current_context()
        meta = getattr(response, "meta", None)
        billed = getattr(meta, "billed_units", None)
        input_tokens = getattr(billed, "input_tokens", 0) or 0
        output_tokens = getattr(billed, "output_tokens", 0) or 0
        model = kwargs.get("model", "unknown")
        input_cost, output_cost = calculate_cost("cohere", model, input_tokens, output_tokens)
        finish_reason = getattr(response, "finish_reason", "COMPLETE") or "COMPLETE"

        self._exporter.emit({
            "trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4()),
            "tenant_id": ctx.tenant_id, "project_id": ctx.project_id,
            "feature_id": ctx.feature_id, "user_id": ctx.user_id,
            "provider": "cohere", "model": model, "request_type": "chat",
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "input_cost_usd": str(input_cost), "output_cost_usd": str(output_cost),
            "latency_ms": latency_ms, "ttft_ms": None,
            "finish_reason": finish_reason, "status": "success", "error_message": None,
        })
        return response


class Cohere:
    """Drop-in replacement for `cohere.Client` that automatically tracks
    every chat() call via the TokenSight exporter."""

    def __init__(self, exporter: HttpExporter, **kwargs: Any) -> None:
        import cohere as _cohere

        self._inner = _cohere.Client(**kwargs)
        self._exporter = exporter
        self.chat = _ChatWrapper(self._inner, exporter)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
