"""TokenSight tracking wrapper for `anthropic.Anthropic` -- pure observation,
no optimization/privacy/governance, no gateway routing."""
from __future__ import annotations

import time
import uuid
from typing import Any

from .context import get_current_context
from .cost import calculate_cost
from .exporter import HttpExporter


class _MessagesWrapper:
    def __init__(self, original: Any, exporter: HttpExporter) -> None:
        self._original = original
        self._exporter = exporter

    def create(self, **kwargs: Any) -> Any:
        start_ns = time.perf_counter_ns()
        response = self._original.create(**kwargs)
        latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

        ctx = get_current_context()
        model = getattr(response, "model", kwargs.get("model", "unknown"))
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        input_cost, output_cost = calculate_cost("anthropic", model, input_tokens, output_tokens)

        stop_reason = getattr(response, "stop_reason", "end_turn") or "end_turn"
        finish_reason = "stop" if stop_reason == "end_turn" else stop_reason

        self._exporter.emit({
            "trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4()),
            "tenant_id": ctx.tenant_id, "project_id": ctx.project_id,
            "feature_id": ctx.feature_id, "user_id": ctx.user_id,
            "provider": "anthropic", "model": model, "request_type": "chat",
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "input_cost_usd": str(input_cost), "output_cost_usd": str(output_cost),
            "latency_ms": latency_ms, "ttft_ms": None,
            "finish_reason": finish_reason, "status": "success", "error_message": None,
        })
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class Anthropic:
    """Tracking-only wrapper around `anthropic.Anthropic` -- records token
    usage without changing where the request goes."""

    def __init__(self, exporter: HttpExporter, **kwargs: Any) -> None:
        import anthropic as _anthropic

        self._inner = _anthropic.Anthropic(**kwargs)
        self._exporter = exporter
        self.messages = _MessagesWrapper(self._inner.messages, exporter)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
