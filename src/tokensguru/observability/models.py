"""Plain data types for traces."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    name: str
    depth: int
    status: str  # "applied", "skipped", "ok", or "" when there is no status
    latency_ms: int

    @property
    def detail(self) -> str:
        return f"{self.status or 'ok'} · {self.latency_ms}ms"


@dataclass(frozen=True)
class Trace:
    id: str
    prompt: str
    model: str
    start: str
    latency_ms: int
    tokens: int
    cost: float
    saved_pct: float | None  # None means "not available"
    spans: tuple[Span, ...]
