"""What the docs UI shows about each optimizer, and how it runs one on request.

The list of optimizers comes from tokensguru.optimizers.registry, so a new
optimizer appears in the UI as soon as it is registered there. The name, id,
summary and long description are read from the optimizer itself. Only the sample
inputs are written here.
"""

from __future__ import annotations

import inspect
import sys
import threading
from typing import Any

from tokensguru.benchmark import BENCHMARK_IDS, run_benchmark
from tokensguru.optimizers.base import Optimizer
from tokensguru.optimizers.messages import MessageOptimizer
from tokensguru.optimizers.pipeline import Pipeline
from tokensguru.optimizers.registry import MESSAGE_OPTIMIZERS, TEXT_OPTIMIZERS

PIPELINE_ID = "pipeline"

PROSE_EXAMPLE = (
    "Meeting notes   for the product launch.                    Please read.   \n"
    "\n\n\n\n"
    "The launch date is set for the first week of March, pending approval.\n"
    "\n\n"
    "The launch date is set for the first week of March, pending approval.\n"
    "\n\n\n"
    "Rules:\n"
    "- Be concise and polite\n"
    "- Be concise and polite\n"
    "- Never share customer passwords\n"
)

EXAMPLES: dict[str, Any] = {
    "tokenguru_json_minifier": (
        '{\n    "status": "ok",\n    "items": [\n'
        '        {"id": 1, "name": "Item  1"},\n'
        '        {"id": 2, "name": "Item 2"}\n    ]\n}\n'
    ),
    "prose_whitespace_cleanup": (
        "Hello     world.   \n\n\n\n\nThis  text   has   extra   spaces.  \n"
    ),
    "exact_paragraph_deduplication": (
        "The customer asked to update his residential address.\n\n\n"
        "The customer asked to update his residential address.\n\n"
        "Thanks.\n\n"
        "The customer asked to update his residential address.\n"
    ),
    "exact_bullet_item_deduplication": (
        "Rules:\n- Be concise\n- Be concise\n- Be concise\n- Cite sources\n"
    ),
    "exact_duplicate_system_messages": [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": "Hello!"},
    ],
    PIPELINE_ID: PROSE_EXAMPLE,
}


class RequestError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _module_doc(owner: Any) -> str:
    return inspect.cleandoc(sys.modules[owner.__module__].__doc__ or "")


def _summary(description: str, fallback: str) -> str:
    first = description.splitlines()[0] if description else fallback
    _, _, after = first.partition(": ")
    text = after or first
    return text[:1].upper() + text[1:]


def _entry(owner: Any, kind: str) -> dict[str, object]:
    description = _module_doc(owner)
    return {
        "id": owner.id,
        "name": owner.name,
        "kind": kind,
        "class_name": owner.__name__,
        "summary": _summary(description, owner.name),
        "description": description,
        "applied_reason": owner.applied_reason,
        "skipped_reason": owner.skipped_reason,
        "example": EXAMPLES.get(owner.id, "" if kind == "text" else []),
    }


def describe_optimizers() -> list[dict[str, object]]:
    pipeline_doc = _module_doc(Pipeline)
    pipeline = {
        "id": PIPELINE_ID,
        "name": "Pipeline",
        "kind": "pipeline",
        "class_name": "Pipeline",
        "summary": _summary(pipeline_doc, "Pipeline"),
        "description": pipeline_doc,
        "applied_reason": "Applied the optimizers that found something to change.",
        "skipped_reason": "No optimizer found a safe change.",
        "example": EXAMPLES[PIPELINE_ID],
    }
    entries = [pipeline]
    entries += [_entry(optimizer, "text") for optimizer in TEXT_OPTIMIZERS]
    entries += [_entry(optimizer, "messages") for optimizer in MESSAGE_OPTIMIZERS]
    return entries


def run_optimization(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RequestError(400, "The request body must be a JSON object.")
    identifier = payload.get("optimizer")
    if not isinstance(identifier, str):
        raise RequestError(400, 'Missing "optimizer".')

    if identifier == PIPELINE_ID:
        return _run_text(Pipeline().optimize, payload)
    for text_optimizer in TEXT_OPTIMIZERS:
        if text_optimizer.id == identifier:
            return _run_text(_text_runner(text_optimizer), payload)
    for message_optimizer in MESSAGE_OPTIMIZERS:
        if message_optimizer.id == identifier:
            return _run_messages(message_optimizer(), payload)
    raise RequestError(404, f"Unknown optimizer: {identifier}")


def _text_runner(optimizer: type[Optimizer]) -> Any:
    return optimizer().optimize


def _run_text(run: Any, payload: dict[str, Any]) -> dict[str, object]:
    text = payload.get("text")
    if not isinstance(text, str):
        raise RequestError(400, 'This optimizer needs "text" as a string.')
    result: dict[str, object] = run(text).to_dict()
    return result


def _run_messages(
    optimizer: MessageOptimizer, payload: dict[str, Any]
) -> dict[str, object]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise RequestError(400, 'This optimizer needs "messages" as a list.')
    result: dict[str, object] = optimizer.optimize(messages).to_dict()
    return result


_BENCHMARKS: dict[str, dict[str, Any]] = {}
_BENCHMARK_LOCK = threading.Lock()


def benchmark_for(identifier: str) -> dict[str, Any]:
    if identifier not in BENCHMARK_IDS:
        raise RequestError(404, f"Unknown optimizer: {identifier}")
    with _BENCHMARK_LOCK:
        cached = _BENCHMARKS.get(identifier)
        if cached is None:
            cached = run_benchmark(identifier)
            if not cached["error"]:
                _BENCHMARKS[identifier] = cached
        return cached
