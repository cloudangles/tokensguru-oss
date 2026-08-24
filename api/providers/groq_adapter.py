"""Groq provider adapter (OpenAI-compatible). Forwards to https://api.groq.com/openai/v1/."""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_GROQ_BASE = "https://api.groq.com/openai"


class GroqAdapter(ProviderAdapter):
    name = "groq"

    def base_url(self) -> str:
        return _GROQ_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("GROQ_API_KEY")), "provider": self.name}
