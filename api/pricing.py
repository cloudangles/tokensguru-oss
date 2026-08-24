"""Static per-model pricing for basic cost estimation.

Not a billing engine -- a rough USD estimate for observability, same
philosophy as Enterprise's pricing_manager.py (whose docstring calls it
exactly that). OSS drops the ClickHouse-backed dynamic refresh (no DB
dependency needed for a static table) but keeps the same fuzzy-matching
fallback logic, since that's genuinely useful and provider-agnostic.
"""
from __future__ import annotations

from decimal import Decimal

# Prices are USD per 1M tokens (input, output). Update as providers change
# pricing -- these are estimates, not a source of truth for billing.
PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o": (Decimal("2.50"), Decimal("10.00")),
    "gpt-4o-mini": (Decimal("0.15"), Decimal("0.60")),
    "gpt-4-turbo": (Decimal("10.00"), Decimal("30.00")),
    "gpt-3.5-turbo": (Decimal("0.50"), Decimal("1.50")),
    "o4-mini": (Decimal("1.10"), Decimal("4.40")),
    "o3": (Decimal("2.00"), Decimal("8.00")),
    "claude-sonnet-4": (Decimal("3.00"), Decimal("15.00")),
    "claude-sonnet-4-5": (Decimal("3.00"), Decimal("15.00")),
    "claude-haiku-4": (Decimal("0.80"), Decimal("4.00")),
    "claude-haiku-4-5": (Decimal("0.80"), Decimal("4.00")),
    "claude-opus-4": (Decimal("15.00"), Decimal("75.00")),
    "gemini-2.5-pro": (Decimal("1.25"), Decimal("10.00")),
    "gemini-2.5-flash": (Decimal("0.15"), Decimal("0.60")),
    "llama-3.3-70b-versatile": (Decimal("0.05"), Decimal("0.08")),
    "llama-3.1-70b-versatile": (Decimal("0.05"), Decimal("0.08")),
    "llama-3.1-8b-instant": (Decimal("0.01"), Decimal("0.01")),
    "gemma2-9b-it": (Decimal("0.02"), Decimal("0.02")),
    "mixtral-8x7b-32768": (Decimal("0.05"), Decimal("0.08")),
    "deepseek-chat": (Decimal("0.27"), Decimal("1.10")),
    "deepseek-reasoner": (Decimal("0.55"), Decimal("2.19")),
}

_FALLBACK_MODEL = "gpt-4o-mini"


def get_pricing(model: str) -> tuple[Decimal, Decimal]:
    """Return (input_price, output_price) per 1M tokens for `model`.

    Strips OpenAI-style version date suffixes (gpt-4o-mini-2024-07-18 ->
    gpt-4o-mini) and fuzzy-matches Claude/Ollama-prefixed family names
    before falling back to a conservative default, so an unrecognized but
    plausible model id doesn't silently look free.
    """
    hit = PRICING.get(model)
    if hit:
        return hit

    parts = model.rsplit("-", 3)
    for n in (3, 2, 1):
        stripped = "-".join(parts[:-n])
        if stripped and stripped in PRICING:
            return PRICING[stripped]

    lower = (model or "").lower()
    if "claude-opus" in lower:
        return PRICING["claude-opus-4"]
    if "claude-sonnet" in lower:
        return PRICING["claude-sonnet-4-5"]
    if "claude-haiku" in lower:
        return PRICING["claude-haiku-4"]
    return PRICING[_FALLBACK_MODEL]


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, float]:
    """Return (input_cost_usd, output_cost_usd) for the given token counts."""
    in_price, out_price = get_pricing(model)
    input_cost = (input_tokens / 1_000_000) * float(in_price)
    output_cost = (output_tokens / 1_000_000) * float(out_price)
    return input_cost, output_cost
