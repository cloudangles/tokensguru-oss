"""Gemini provider adapter. Forwards to https://generativelanguage.googleapis.com/v1beta/."""
from __future__ import annotations

from providers.base import ProviderAdapter

_GEMINI_BASE = "https://generativelanguage.googleapis.com"


class GeminiAdapter(ProviderAdapter):
    name = "google"

    def base_url(self) -> str:
        return _GEMINI_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        return {"x-goog-api-key": api_key}

    def extract_usage(self, endpoint: str, response: dict) -> dict[str, int]:
        usage = response.get("usageMetadata", {})
        prompt = int(usage.get("promptTokenCount", 0))
        complete = int(usage.get("candidatesTokenCount", 0))
        return {
            "prompt_tokens": prompt,
            "completion_tokens": complete,
            "total_tokens": int(usage.get("totalTokenCount", prompt + complete)),
        }
