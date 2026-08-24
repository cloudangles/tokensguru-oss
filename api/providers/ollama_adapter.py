"""Ollama provider adapter (self-hosted, OpenAI-compatible endpoint).

Note (documented tradeoff, not an oversight): Enterprise's adapter targets
Ollama's native /api/chat endpoint for exact prompt_eval_count/eval_count
usage fields. This OSS adapter targets Ollama's OpenAI-compatible /v1
endpoint instead, to keep the provider layer uniform (declarative
base_url/auth_headers/extract_usage only, no provider-specific HTTP client)
-- token usage falls back to the same tiktoken-based estimate used when any
provider doesn't return exact counts.

Base URL: OLLAMA_BASE_URL env var, defaults to http://localhost:11434.
No API key required by default (self-hosted); set OLLAMA_API_KEY if running
behind a reverse proxy that expects a bearer token.
"""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaAdapter(ProviderAdapter):
    name = "ollama"

    def base_url(self) -> str:
        return (os.getenv("OLLAMA_BASE_URL") or "").rstrip("/") or _DEFAULT_BASE_URL

    def auth_headers(self, api_key: str) -> dict[str, str]:
        key = os.getenv("OLLAMA_API_KEY") or api_key or ""
        return {"Authorization": f"Bearer {key}"} if key else {}

    def health(self) -> dict:
        # Self-hosted infra has no assumed uptime, but a live probe needs an
        # HTTP client the base adapter interface doesn't carry -- report
        # config-presence only, matching every other adapter's health() shape.
        return {"ok": True, "provider": self.name, "base_url": self.base_url()}


def is_ollama_model(model: str) -> bool:
    m = (model or "").lower().strip()
    return m.startswith("ollama/") or m.startswith("self-hosted/")
