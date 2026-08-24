"""Provider adapter base class.

Each provider adapter handles:
  - Building the correct upstream URL for a given endpoint
  - Injecting provider-specific auth headers
  - Normalizing the request body if needed
  - Extracting token usage from provider-specific response shapes

Adding a new provider = subclass ProviderAdapter and register in REGISTRY.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ProviderError(Exception):
    """Raised when a provider call fails or a provider is unavailable."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int = 0,
        provider_code: str = "",
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.provider_code = provider_code


class ProviderAdapter(ABC):
    """Adapter interface for a single AI provider."""

    name: str = ""

    @abstractmethod
    def base_url(self) -> str:
        """Root URL of the provider API, no trailing slash."""

    @abstractmethod
    def auth_headers(self, api_key: str) -> dict[str, str]:
        """Auth headers to inject for every request."""

    def extra_headers(self) -> dict[str, str]:
        """Provider-specific non-auth headers (e.g. anthropic-version)."""
        return {}

    def adapt_request_body(self, endpoint: str, body: dict) -> dict:
        """Transform the canonical request body for this provider if needed.

        Default: pass through unchanged (OpenAI-compatible providers need no
        transformation since the request is already OpenAI-format).
        """
        return body

    def extract_usage(self, endpoint: str, response: dict) -> dict[str, int]:
        """Extract token counts from a provider response.

        Returns a dict with at least: prompt_tokens, completion_tokens,
        total_tokens.
        """
        usage = response.get("usage", {})
        return {
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }

    def health(self) -> dict[str, Any]:
        """Cheap readiness signal (key-presence only, no live call)."""
        return {"ok": True, "provider": self.name}

    def endpoint_url(self, path: str) -> str:
        """Full URL for a given API path (e.g. '/v1/embeddings')."""
        return self.base_url().rstrip("/") + "/" + path.lstrip("/")
