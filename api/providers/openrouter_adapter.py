"""OpenRouter provider adapter (OpenAI-compatible). Forwards to https://openrouter.ai/api/v1/.

Simplified from Enterprise's version: plain OPENROUTER_API_KEY env var, no
vault-JSON credential blob (that was a multi-tenant/BYO-key concept not
needed for a single-tenant self-host).
"""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


class OpenRouterAdapter(ProviderAdapter):
    name = "openrouter"

    def base_url(self) -> str:
        return _OPENROUTER_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        key = os.getenv("OPENROUTER_API_KEY") or api_key or ""
        return {"Authorization": f"Bearer {key}"} if key else {}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("OPENROUTER_API_KEY")), "provider": self.name}


def resolve_upstream_model(model: str) -> str:
    """Strip a leading `openrouter/` prefix only -- OpenRouter's catalog ids
    are already vendor/model-namespaced (e.g. anthropic/claude-3.5-sonnet),
    so a naive first-slash strip would mangle them."""
    raw = (model or "").strip()
    if raw.lower().startswith("openrouter/"):
        return raw[len("openrouter/"):]
    return raw
