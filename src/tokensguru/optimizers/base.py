"""Base class for every optimizer, and the result an optimizer gives back.

Calling optimize() on any optimizer returns an OptimizationResult. It already has
everything: the optimizer's id and name, the original and optimized text, the
tokens before and after (counted automatically with tiktoken), the characters and
tokens saved, why the text was or was not changed, how long it took, a unique id
and a timestamp. You never have to count tokens yourself.

    result = SomeOptimizer().optimize(text)
    result.optimized_text
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    print(result)          # a readable summary
    result.to_dict()       # the same details as a plain dictionary

If the tokenizer cannot be loaded (for example no internet the first time), the
text is still optimized, the token fields are None and token_error says why.

To write a new optimizer, extend Optimizer, set id, name, applied_reason and
skipped_reason, and write transform(), which turns a string into a string.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter

from tokensguru.tokens import TokenCounter, default_counter
from tokensguru.utils.helpers import new_id, timestamp
from tokensguru.utils.validation import require_text

PREVIEW_LENGTH = 120


def percent(part: int, whole: int) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


def _preview(text: str) -> str:
    shown = text if len(text) <= PREVIEW_LENGTH else text[:PREVIEW_LENGTH] + "..."
    return repr(shown)


@dataclass(frozen=True)
class OptimizationResult:
    optimizer_id: str
    optimizer_name: str
    original_text: str
    optimized_text: str
    reason: str
    tokenizer: str
    original_tokens: int | None
    optimized_tokens: int | None
    duration_ms: float
    token_error: str | None = None
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=timestamp)

    @property
    def changed(self) -> bool:
        return self.optimized_text != self.original_text

    @property
    def original_chars(self) -> int:
        return len(self.original_text)

    @property
    def optimized_chars(self) -> int:
        return len(self.optimized_text)

    @property
    def saved_chars(self) -> int:
        return self.original_chars - self.optimized_chars

    @property
    def saved_chars_percent(self) -> float:
        return percent(self.saved_chars, self.original_chars)

    @property
    def saved_tokens(self) -> int | None:
        if self.original_tokens is None or self.optimized_tokens is None:
            return None
        return self.original_tokens - self.optimized_tokens

    @property
    def saved_tokens_percent(self) -> float | None:
        if self.saved_tokens is None or self.original_tokens is None:
            return None
        return percent(self.saved_tokens, self.original_tokens)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "optimizer_id": self.optimizer_id,
            "optimizer_name": self.optimizer_name,
            "changed": self.changed,
            "reason": self.reason,
            "tokenizer": self.tokenizer,
            "original_text": self.original_text,
            "optimized_text": self.optimized_text,
            "original_tokens": self.original_tokens,
            "optimized_tokens": self.optimized_tokens,
            "saved_tokens": self.saved_tokens,
            "saved_tokens_percent": self.saved_tokens_percent,
            "original_chars": self.original_chars,
            "optimized_chars": self.optimized_chars,
            "saved_chars": self.saved_chars,
            "saved_chars_percent": self.saved_chars_percent,
            "duration_ms": self.duration_ms,
            "token_error": self.token_error,
        }

    def __str__(self) -> str:
        if self.saved_tokens is None:
            tokens = f"unavailable ({self.token_error})"
        else:
            tokens = (
                f"{self.original_tokens} -> {self.optimized_tokens}, "
                f"saved {self.saved_tokens} ({self.saved_tokens_percent}%)"
            )
        rows = [
            ("id", self.id),
            ("created at", self.created_at),
            ("optimizer", f"{self.optimizer_id} ({self.optimizer_name})"),
            ("changed", "yes" if self.changed else "no"),
            ("reason", self.reason),
            ("tokenizer", self.tokenizer),
            ("tokens", tokens),
            (
                "characters",
                f"{self.original_chars} -> {self.optimized_chars}, "
                f"saved {self.saved_chars} ({self.saved_chars_percent}%)",
            ),
            ("duration", f"{self.duration_ms} ms"),
            ("original text", _preview(self.original_text)),
            ("optimized text", _preview(self.optimized_text)),
        ]
        width = max(len(label) for label, _ in rows)
        lines = [f"{label:<{width}} : {value}" for label, value in rows]
        return "\n".join(lines)


def measure_tokens(
    counter: TokenCounter, before: str, after: str
) -> tuple[int | None, int | None, str | None]:
    try:
        return counter.count(before), counter.count(after), None
    except Exception as error:
        return None, None, f"{type(error).__name__}: {error}"


class Optimizer(ABC):
    id: str
    name: str
    applied_reason: str
    skipped_reason: str

    def __init__(self, counter: TokenCounter | None = None) -> None:
        self.counter = counter if counter is not None else default_counter()

    @abstractmethod
    def transform(self, text: str, context: dict[str, object] | None = None) -> str:
        raise NotImplementedError

    def optimize(
        self, text: str, context: dict[str, object] | None = None
    ) -> OptimizationResult:
        require_text(text)
        started = perf_counter()
        optimized = self.transform(text, context)
        duration_ms = round((perf_counter() - started) * 1000, 3)

        original_tokens, optimized_tokens, token_error = measure_tokens(
            self.counter, text, optimized
        )

        changed = optimized != text
        return OptimizationResult(
            optimizer_id=self.id,
            optimizer_name=self.name,
            original_text=text,
            optimized_text=optimized,
            reason=self.applied_reason if changed else self.skipped_reason,
            tokenizer=self.counter.name,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            duration_ms=duration_ms,
            token_error=token_error,
        )

    def __call__(
        self, text: str, context: dict[str, object] | None = None
    ) -> OptimizationResult:
        return self.optimize(text, context)
