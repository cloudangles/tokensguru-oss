"""Runs an optimizer over its sample inputs and summarizes the token savings."""

from __future__ import annotations

from typing import Any

from tokensguru.benchmark.samples import MESSAGE_SAMPLES, TEXT_SAMPLES
from tokensguru.optimizers.pipeline import Pipeline
from tokensguru.optimizers.registry import MESSAGE_OPTIMIZERS, TEXT_OPTIMIZERS
from tokensguru.tokens import TokenCounter

BENCHMARK_IDS = tuple(TEXT_SAMPLES) + tuple(MESSAGE_SAMPLES)


def _percent(saved: int, original: int) -> float:
    return round(100 * saved / original, 2) if original else 0.0


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    percents = [sample["saved_percent"] for sample in samples]
    original = sum(sample["original_tokens"] for sample in samples)
    optimized = sum(sample["optimized_tokens"] for sample in samples)
    return {
        "samples": len(samples),
        "changed": sum(1 for sample in samples if sample["saved_tokens"] > 0),
        "average_percent": round(sum(percents) / len(percents), 2) if percents else 0.0,
        "min_percent": min(percents) if percents else 0.0,
        "max_percent": max(percents) if percents else 0.0,
        "total_original_tokens": original,
        "total_optimized_tokens": optimized,
        "overall_percent": _percent(original - optimized, original),
    }


def _entry(name: str, result: Any) -> dict[str, Any]:
    return {
        "name": name,
        "original_tokens": result.original_tokens,
        "optimized_tokens": result.optimized_tokens,
        "saved_tokens": result.saved_tokens,
        "saved_percent": result.saved_tokens_percent,
    }


def _runner(optimizer_id: str, counter: TokenCounter) -> Any:
    if optimizer_id == "pipeline":
        return Pipeline(*[kind(counter=counter) for kind in TEXT_OPTIMIZERS]).optimize
    for text_kind in TEXT_OPTIMIZERS:
        if text_kind.id == optimizer_id:
            return text_kind(counter=counter).optimize
    for message_kind in MESSAGE_OPTIMIZERS:
        if message_kind.id == optimizer_id:
            return message_kind(counter).optimize
    raise KeyError(optimizer_id)


def run_benchmark(
    optimizer_id: str, counter: TokenCounter | None = None
) -> dict[str, Any]:
    if optimizer_id not in BENCHMARK_IDS:
        raise KeyError(optimizer_id)
    counter = counter or TokenCounter()
    run = _runner(optimizer_id, counter)
    inputs: dict[str, Any] = (
        TEXT_SAMPLES.get(optimizer_id) or MESSAGE_SAMPLES[optimizer_id]
    )
    report: dict[str, Any] = {
        "optimizer": optimizer_id,
        "tokenizer": counter.name,
        "error": None,
        "samples": [],
        "summary": None,
    }
    for name, data in inputs.items():
        result = run(data)
        if result.token_error:
            report["error"] = result.token_error
            report["samples"] = []
            return report
        report["samples"].append(_entry(name, result))
    report["summary"] = summarize(report["samples"])
    return report
