"""Together AI provider adapter (OpenAI-compatible). Forwards to https://api.together.xyz/v1/.

Simplified from Enterprise's version: plain TOGETHER_API_KEY env var, no
vault-JSON credential blob.
"""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_TOGETHER_BASE = "https://api.together.xyz"


class TogetherAdapter(ProviderAdapter):
    name = "together"

    def base_url(self) -> str:
        return _TOGETHER_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        key = os.getenv("TOGETHER_API_KEY") or api_key or ""
        return {"Authorization": f"Bearer {key}"} if key else {}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("TOGETHER_API_KEY")), "provider": self.name}


def resolve_upstream_model(model: str) -> str:
    raw = (model or "").strip()
    if raw.lower().startswith("together/"):
        return raw[len("together/"):]
    return raw
