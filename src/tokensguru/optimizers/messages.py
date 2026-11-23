"""Base class for optimizers that work on a list of chat messages.

Most optimizers take one string. These take the "messages" list you send to a chat
model, for example:

    [{"role": "system", "content": "Be concise."},
     {"role": "user", "content": "Hello"}]

Calling optimize() returns a MessageOptimizationResult. It has everything a normal
result has (id, tokens before and after, characters, reason, timing, ...) plus the
messages themselves: original_messages, optimized_messages, removed_count and
removed_indexes (the positions of the removed messages in the original list).

The tokens are counted on the whole message list, written as compact JSON, so the
saving includes the role and field names of every removed message.

Your input list and its messages are never changed. optimized_messages is a new
list that holds the same message objects.

To write a new one, extend MessageOptimizer, set id, name, applied_reason and
skipped_reason, and write keep(), which returns the positions of the messages to keep.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from tokensguru.optimizers.base import OptimizationResult, measure_tokens
from tokensguru.tokens import TokenCounter, default_counter


def render_messages(messages: list[Any]) -> str:
    try:
        return json.dumps(
            messages, ensure_ascii=False, separators=(",", ":"), default=str
        )
    except (TypeError, ValueError):
        return repr(messages)


@dataclass(frozen=True)
class MessageOptimizationResult(OptimizationResult):
    original_messages: list[Any] = field(default_factory=list)
    optimized_messages: list[Any] = field(default_factory=list)
    removed_indexes: tuple[int, ...] = ()

    @property
    def removed_count(self) -> int:
        return len(self.removed_indexes)

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data["original_messages"] = self.original_messages
        data["optimized_messages"] = self.optimized_messages
        data["removed_count"] = self.removed_count
        data["removed_indexes"] = list(self.removed_indexes)
        return data

    def __str__(self) -> str:
        removed = f"{self.removed_count} of {len(self.original_messages)}"
        if self.removed_indexes:
            removed += f" (positions {list(self.removed_indexes)})"
        return f"{super().__str__()}\nmessages removed : {removed}"


class MessageOptimizer(ABC):
    id: str
    name: str
    applied_reason: str
    skipped_reason: str

    def __init__(self, counter: TokenCounter | None = None) -> None:
        self.counter = counter if counter is not None else default_counter()

    @abstractmethod
    def keep(
        self, messages: list[Any], context: dict[str, object] | None = None
    ) -> list[int]:
        raise NotImplementedError

    def optimize(
        self, messages: list[Any], context: dict[str, object] | None = None
    ) -> MessageOptimizationResult:
        if not isinstance(messages, (list, tuple)):
            raise TypeError(
                f"messages must be a list of messages, not {type(messages).__name__}"
            )
        original = list(messages)
        started = perf_counter()
        kept = self.keep(original, context)
        duration_ms = round((perf_counter() - started) * 1000, 3)

        kept_set = set(kept)
        optimized = [original[index] for index in kept]
        removed = tuple(i for i in range(len(original)) if i not in kept_set)
        before, after = render_messages(original), render_messages(optimized)
        original_tokens, optimized_tokens, token_error = measure_tokens(
            self.counter, before, after
        )
        return MessageOptimizationResult(
            optimizer_id=self.id,
            optimizer_name=self.name,
            original_text=before,
            optimized_text=after,
            reason=self.applied_reason if removed else self.skipped_reason,
            tokenizer=self.counter.name,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            duration_ms=duration_ms,
            token_error=token_error,
            original_messages=original,
            optimized_messages=optimized,
            removed_indexes=removed,
        )

    def __call__(
        self, messages: list[Any], context: dict[str, object] | None = None
    ) -> MessageOptimizationResult:
        return self.optimize(messages, context)
