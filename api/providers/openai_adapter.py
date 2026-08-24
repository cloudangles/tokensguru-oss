"""OpenAI provider adapter. Forwards requests to https://api.openai.com/v1/."""
from __future__ import annotations

import os

from providers.base import ProviderAdapter

_OPENAI_BASE = "https://api.openai.com"
_OPENAI_PREFIXES = ("gpt-", "o1", "o3", "o4", "text-embedding-", "dall-e", "whisper-", "tts-")


class OpenAIAdapter(ProviderAdapter):
    name = "openai"

    def base_url(self) -> str:
        return _OPENAI_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}"}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("OPENAI_API_KEY")), "provider": self.name}

    def extract_usage(self, endpoint: str, response: dict) -> dict[str, int]:
        usage = response.get("usage", {})
        prompt = int(usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0))
        complete = int(usage.get("completion_tokens", 0) or usage.get("output_tokens", 0))
        return {
            "prompt_tokens": prompt,
            "completion_tokens": complete,
            "total_tokens": int(usage.get("total_tokens", prompt + complete)),
        }


def is_openai_model(model: str) -> bool:
    m = model.lower()
    return any(m.startswith(pfx) for pfx in _OPENAI_PREFIXES)
