"""DeepSeek provider adapter (OpenAI-compatible). Forwards to https://api.deepseek.com/v1/."""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_DEEPSEEK_BASE = "https://api.deepseek.com"


class DeepSeekAdapter(ProviderAdapter):
    name = "deepseek"

    def base_url(self) -> str:
        return _DEEPSEEK_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("DEEPSEEK_API_KEY")), "provider": self.name}
