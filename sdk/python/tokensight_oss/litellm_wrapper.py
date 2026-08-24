"""TokenSight tracking wrapper for `litellm.completion` -- pure observation.

The `litellm` package is an optional dependency; the wrapper raises a clear
ImportError on instantiation (not at import time) if it isn't installed.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from .context import get_current_context
from .cost import calculate_cost
from .exporter import HttpExporter


class LiteLLMWrapper:
    def __init__(self, exporter: HttpExporter, **kwargs: Any) -> None:
        import litellm as _litellm

        self._litellm = _litellm
        self._exporter = exporter
        self._kwargs = kwargs

    def completion(self, **kwargs: Any) -> Any:
        start_ns = time.perf_counter_ns()
        merged = {**self._kwargs, **kwargs}
        response = self._litellm.completion(**merged)
        latency_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)

        ctx = get_current_context()
        model_str = merged.get("model", "unknown")
        provider = model_str.split("/", 1)[0] if "/" in model_str else "litellm"
        model = model_str.split("/", 1)[1] if "/" in model_str else model_str

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        input_cost, output_cost = calculate_cost(provider, model, input_tokens, output_tokens)

        finish_reason = "stop"
        choices = getattr(response, "choices", None)
        if choices:
            finish_reason = getattr(choices[0], "finish_reason", "stop") or "stop"

        self._exporter.emit({
            "trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4()),
            "tenant_id": ctx.tenant_id, "project_id": ctx.project_id,
            "feature_id": ctx.feature_id, "user_id": ctx.user_id,
            "provider": provider, "model": model, "request_type": "chat",
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "input_cost_usd": str(input_cost), "output_cost_usd": str(output_cost),
            "latency_ms": latency_ms, "ttft_ms": None,
            "finish_reason": finish_reason, "status": "success", "error_message": None,
        })
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._litellm, name)
