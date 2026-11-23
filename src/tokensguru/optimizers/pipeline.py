"""Pipeline: runs several optimizers one after another and reports on all of them.

Use it when you want more than one optimizer at a time. Each optimizer gets the
text the previous one produced. You get one combined result, with the details of
every step inside it, so you never chain optimizers by hand.

How to use it:
    from tokensguru.optimizers import Pipeline

    result = Pipeline().optimize(text)       # runs every built-in optimizer

    # or choose the optimizers, and their order:
    from tokensguru.optimizers import BulletDeduplicator, WhitespaceCleaner
    result = Pipeline(WhitespaceCleaner(), BulletDeduplicator()).optimize(text)

    result.optimized_text                    # the final text
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    result.steps                             # one OptimizationResult per optimizer
    print(result)                            # overall summary plus every step

The result has all the fields of a normal optimizer result (id, tokens, characters,
reason, timing...), counted from the original text to the final text.

The built-in order is: JSON minifier first (so JSON is compact before anything else
looks at it), then the whitespace cleaner (so lines that only differ by extra spaces
become identical), then the paragraph deduplicator, then the bullet deduplicator.
"""

from __future__ import annotations

from dataclasses import dataclass

from tokensguru.optimizers.base import OptimizationResult, Optimizer
from tokensguru.optimizers.registry import default_optimizers
from tokensguru.utils.validation import require_text


@dataclass(frozen=True)
class PipelineResult(OptimizationResult):
    steps: tuple[OptimizationResult, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data["steps"] = [step.to_dict() for step in self.steps]
        return data

    def __str__(self) -> str:
        lines = [super().__str__(), "", "steps"]
        for number, step in enumerate(self.steps, start=1):
            tokens = (
                "tokens unavailable"
                if step.saved_tokens is None
                else f"tokens {step.original_tokens} -> {step.optimized_tokens} "
                f"(saved {step.saved_tokens})"
            )
            status = "changed" if step.changed else "unchanged"
            lines.append(
                f"  {number}. {step.optimizer_id}: {status}, {tokens}, "
                f"chars saved {step.saved_chars}"
            )
        return "\n".join(lines)


class Pipeline:
    def __init__(self, *optimizers: Optimizer) -> None:
        chosen = optimizers or default_optimizers()
        for optimizer in chosen:
            if not isinstance(optimizer, Optimizer):
                raise TypeError(
                    f"Pipeline takes optimizers, not {type(optimizer).__name__}"
                )
        self.optimizers = tuple(chosen)

    def optimize(
        self, text: str, context: dict[str, object] | None = None
    ) -> PipelineResult:
        require_text(text)
        steps: list[OptimizationResult] = []
        current = text
        for optimizer in self.optimizers:
            step = optimizer.optimize(current, context)
            steps.append(step)
            current = step.optimized_text

        first, last = steps[0], steps[-1]
        applied = [step.optimizer_name for step in steps if step.changed]
        reason = (
            "Applied: " + ", ".join(applied)
            if applied
            else "No optimizer found a safe change."
        )
        counted = (
            first.original_tokens is not None and last.optimized_tokens is not None
        )
        return PipelineResult(
            optimizer_id="pipeline",
            optimizer_name="Pipeline: " + ", ".join(s.optimizer_name for s in steps),
            original_text=text,
            optimized_text=current,
            reason=reason,
            tokenizer=first.tokenizer,
            original_tokens=first.original_tokens if counted else None,
            optimized_tokens=last.optimized_tokens if counted else None,
            duration_ms=round(sum(step.duration_ms for step in steps), 3),
            token_error=next((s.token_error for s in steps if s.token_error), None),
            steps=tuple(steps),
        )

    def __call__(
        self, text: str, context: dict[str, object] | None = None
    ) -> PipelineResult:
        return self.optimize(text, context)
