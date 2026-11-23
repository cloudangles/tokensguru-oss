"""Guardrail pipeline: runs several guardrails on the same text and combines them.

Use it when you want more than one check at a time. You get one combined result,
with the full result of every guardrail inside it, and an overall decision: the
strictest one among them ("block" beats "flag", and "flag" beats "pass").

How to use it:
    from tokensguru.governance import GuardrailPipeline

    result = GuardrailPipeline().check(text)        # every built-in guardrail
    result.decision                                   # the strictest decision
    result.results                                    # one result per guardrail
    print(result)

    # or choose the guardrails:
    from tokensguru.governance import ApiKeyDetector, EmailDetector
    pipeline = GuardrailPipeline(ApiKeyDetector(), EmailDetector(action="block"))
    result = pipeline.check(text)

    # a chat messages list:
    result = GuardrailPipeline().check_messages(messages)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from tokensguru.governance.base import (
    Finding,
    Guardrail,
    GuardrailResult,
    strictest,
)
from tokensguru.governance.registry import default_guardrails
from tokensguru.utils.validation import require_text


@dataclass(frozen=True)
class PipelineResult(GuardrailResult):
    results: tuple[GuardrailResult, ...] = ()

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data["results"] = [result.to_dict() for result in self.results]
        return data

    def __str__(self) -> str:
        lines = [super().__str__(), "", "guardrails"]
        for number, result in enumerate(self.results, start=1):
            lines.append(
                f"  {number}. {result.guardrail_id}: {result.decision}, "
                f"{result.count} found"
            )
        return "\n".join(lines)


class GuardrailPipeline:
    def __init__(self, *guardrails: Guardrail) -> None:
        chosen = guardrails or default_guardrails()
        for guardrail in chosen:
            if not isinstance(guardrail, Guardrail):
                raise TypeError(
                    "GuardrailPipeline takes guardrails, "
                    f"not {type(guardrail).__name__}"
                )
        self.guardrails = tuple(chosen)

    def check(
        self, text: str, context: dict[str, object] | None = None
    ) -> PipelineResult:
        require_text(text)
        started = perf_counter()
        results = tuple(guardrail.check(text, context) for guardrail in self.guardrails)
        return self._combine(results, len(text), started)

    def check_messages(
        self,
        messages: list[Any],
        context: dict[str, object] | None = None,
        roles: Iterable[str] | None = None,
    ) -> PipelineResult:
        started = perf_counter()
        results = tuple(
            guardrail.check_messages(messages, context, roles)
            for guardrail in self.guardrails
        )
        length = max((result.input_length for result in results), default=0)
        return self._combine(results, length, started)

    @staticmethod
    def _combine(
        results: tuple[GuardrailResult, ...], input_length: int, started: float
    ) -> PipelineResult:
        duration_ms = round((perf_counter() - started) * 1000, 3)
        findings: list[Finding] = sorted(
            (finding for result in results for finding in result.findings),
            key=lambda item: (item.path or "", item.start, item.end),
        )
        decision = strictest([result.decision for result in results])
        flagged = [result.guardrail_name for result in results if result.detected]
        reason = (
            "Found something: " + ", ".join(flagged)
            if flagged
            else "No guardrail found anything"
        )
        return PipelineResult(
            guardrail_id="pipeline",
            guardrail_name="Pipeline: " + ", ".join(r.guardrail_name for r in results),
            decision=decision,
            reason=reason,
            findings=tuple(findings),
            input_length=input_length,
            duration_ms=duration_ms,
            results=results,
        )

    def __call__(
        self, text: str, context: dict[str, object] | None = None
    ) -> PipelineResult:
        return self.check(text, context)
