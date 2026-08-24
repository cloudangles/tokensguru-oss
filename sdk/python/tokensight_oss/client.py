"""TokenSight tracking wrapper for `openai.OpenAI` -- pure observation, no
optimization/privacy/governance."""
from __future__ import annotations

import time
import uuid
from typing import Any

from .context import get_current_context
from .cost import calculate_cost
from .exporter import HttpExporter


class _ChatCompletionsWrapper:
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
        input_tokens = getattr(usage, "prompt_tokens", 0) or 0
        output_tokens = getattr(usage, "completion_tokens", 0) or 0
        input_cost, output_cost = calculate_cost("openai", model, input_tokens, output_tokens)

        finish_reason = "stop"
        if response.choices:
            finish_reason = getattr(response.choices[0], "finish_reason", "stop") or "stop"

        self._exporter.emit({
            "trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4()),
            "tenant_id": ctx.tenant_id, "project_id": ctx.project_id,
            "feature_id": ctx.feature_id, "user_id": ctx.user_id,
            "provider": "openai", "model": model, "request_type": "chat",
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "input_cost_usd": str(input_cost), "output_cost_usd": str(output_cost),
            "latency_ms": latency_ms, "ttft_ms": None,
            "finish_reason": finish_reason, "status": "success", "error_message": None,
        })
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class _ChatWrapper:
    def __init__(self, original: Any, exporter: HttpExporter) -> None:
        self._original = original
        self.completions = _ChatCompletionsWrapper(original.completions, exporter)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class _EmbeddingsWrapper:
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
        input_tokens = getattr(usage, "total_tokens", 0) or getattr(usage, "prompt_tokens", 0) or 0
        input_cost, output_cost = calculate_cost("openai", model, input_tokens, 0)

        self._exporter.emit({
            "trace_id": str(uuid.uuid4()), "span_id": str(uuid.uuid4()),
            "tenant_id": ctx.tenant_id, "project_id": ctx.project_id,
            "feature_id": ctx.feature_id, "user_id": ctx.user_id,
            "provider": "openai", "model": model, "request_type": "embedding",
            "input_tokens": input_tokens, "output_tokens": 0,
            "input_cost_usd": str(input_cost), "output_cost_usd": str(output_cost),
            "latency_ms": latency_ms, "ttft_ms": None,
            "finish_reason": "stop", "status": "success", "error_message": None,
        })
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class OpenAI:
    """Drop-in replacement for `openai.OpenAI` that automatically tracks
    every chat completion and embedding call via the TokenSight exporter."""

    def __init__(self, exporter: HttpExporter, **kwargs: Any) -> None:
        import openai as _openai

        self._inner = _openai.OpenAI(**kwargs)
        self._exporter = exporter
        self.chat = _ChatWrapper(self._inner.chat, exporter)
        self.embeddings = _EmbeddingsWrapper(self._inner.embeddings, exporter)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
