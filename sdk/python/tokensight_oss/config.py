"""SDK configuration: resolves the TokenSight OSS API endpoint and key from env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(*keys: str) -> str:
    for key in keys:
        val = os.environ.get(key, "").strip()
        if val:
            return val.rstrip("/")
    return ""


def default_api_url() -> str:
    return _env("TOKENSIGHT_API_URL", "TOKENSIGHT_API_ENDPOINT") or "http://localhost:8000"


@dataclass
class TokenSightConfig:
    api_endpoint: str = field(default_factory=default_api_url)
    api_key: str = field(default_factory=lambda: os.environ.get("TOKENSIGHT_API_KEY", "").strip())
    batch_size: int = 50
    flush_interval_seconds: float = 1.0
    queue_max_size: int = 10_000
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_seconds: float = 30.0

    def validate(self) -> None:
        if not self.api_key:
            self.api_key = os.environ.get("TOKENSIGHT_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError(
                "Missing required environment variable TOKENSIGHT_API_KEY "
                "(or pass api_key to TokenSightConfig). Get one from your "
                "TokenSight dashboard's Settings page."
            )
