"""Small helpers shared across the package."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def new_id() -> str:
    return uuid4().hex


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
