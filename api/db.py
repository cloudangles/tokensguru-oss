"""ClickHouse client -- the only data store in TokenSight OSS.

No Postgres, no Redis: OSS has no RBAC/orgs/teams/approvals/quotas to
justify them. A small `users`/`api_keys` table lives in the same
ClickHouse database as `llm_events`.
"""
from __future__ import annotations

import logging
import os
import threading

import clickhouse_connect
from clickhouse_connect.driver.client import Client

logger = logging.getLogger("tokensight.db")

_lock = threading.Lock()
_client: Client | None = None


def get_client() -> Client:
    """Return a shared ClickHouse client, connecting lazily on first use."""
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        _client = clickhouse_connect.get_client(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            username=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            database=os.getenv("CLICKHOUSE_DATABASE", "tokensight"),
        )
        return _client


def reset_client() -> None:
    """Drop the cached client (tests only)."""
    global _client
    _client = None
