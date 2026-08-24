"""Static per-model pricing lookup for client-side cost estimation."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

_PRICING: dict[str, dict[str, Any]] = json.loads(
    (Path(__file__).parent / "pricing.json").read_text()
)

_BY_PROVIDER: dict[str, dict[str, str]] = {}
for _key in _PRICING:
    _prov, _model = _key.split("/", 1)
    _BY_PROVIDER.setdefault(_prov, {})[_model] = _key


def _resolve_key(provider: str, model: str) -> str | None:
    """Exact match first, then strip a trailing OpenAI-style dated-snapshot
    suffix ("gpt-4o-mini-2024-07-18" -> "gpt-4o-mini" -- three hyphen-
    separated segments, not one contiguous digit run), then fall back to
    the LONGEST matching family-name prefix (checked longest-first, so
    "gpt-4o-mini-..." can't be mistakenly matched by the shorter "gpt-4o").
    """
    key = f"{provider}/{model}"
    if key in _PRICING:
        return key

    by_model = _BY_PROVIDER.get(provider, {})

    parts = model.rsplit("-", 3)
    for n in (3, 2, 1):
        if n >= len(parts):
            continue
        stripped = "-".join(parts[:-n])
        if stripped and stripped in by_model:
            return by_model[stripped]

    for name in sorted(by_model, key=len, reverse=True):
        if model == name or model.startswith(name + "-"):
            return by_model[name]
    return None


def calculate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> tuple[Decimal, Decimal]:
    key = _resolve_key(provider or "", model or "")
    if key is None:
        return Decimal("0"), Decimal("0")
    p = _PRICING[key]
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * Decimal(str(p["input"]))
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * Decimal(str(p["output"]))
    return input_cost, output_cost
