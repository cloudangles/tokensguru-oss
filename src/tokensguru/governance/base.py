"""Base class for every guardrail, and the result a guardrail gives back.

A guardrail looks at text (a prompt, a message or a model answer) and reports what
it finds. Calling check() on any guardrail returns a GuardrailResult with the
decision, the findings, why it decided that, how long it took, a unique id and a
timestamp.

    result = SomeGuardrail().check(text)
    result.decision          # "pass", "flag" or "block"
    result.findings          # where things were found, and what kind
    print(result)            # a readable summary
    result.to_dict()         # the same details as a plain dictionary

A finding never contains the secret or the personal data it found. It holds the
type, the position, a confidence and a masked preview. The result does not keep
your text either, only its length.

What happens when something is found is set with action: "flag" reports it and
"block" tells the caller to stop the request. Nothing is blocked by the guardrail
itself. The caller decides what to do with the decision.

To write a new guardrail, extend Guardrail, set id, name and default_action, and
write find(), which returns the list of findings for a string.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Any

from tokensguru.governance.messages import iter_slots
from tokensguru.utils.helpers import new_id, timestamp
from tokensguru.utils.validation import require_text

PASS = "pass"  # noqa: S105
FLAG = "flag"
REDACT = "redact"
BLOCK = "block"
ACTIONS = (FLAG, BLOCK)
_SEVERITY = {PASS: 0, FLAG: 1, REDACT: 2, BLOCK: 3}


@dataclass(frozen=True)
class Finding:
    type: str
    category: str
    start: int
    end: int
    confidence: float
    preview: str
    path: str | None = None

    @property
    def length(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "type": self.type,
            "category": self.category,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "preview": self.preview,
        }
        if self.path is not None:
            data["path"] = self.path
        return data


@dataclass(frozen=True)
class GuardrailResult:
    guardrail_id: str
    guardrail_name: str
    decision: str
    reason: str
    findings: tuple[Finding, ...]
    input_length: int
    duration_ms: float
    id: str = field(default_factory=new_id)
    created_at: str = field(default_factory=timestamp)

    @property
    def detected(self) -> bool:
        return bool(self.findings)

    @property
    def count(self) -> int:
        return len(self.findings)

    @property
    def score(self) -> float:
        return max((finding.confidence for finding in self.findings), default=0.0)

    @property
    def types(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.type] = counts.get(finding.type, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "guardrail_id": self.guardrail_id,
            "guardrail_name": self.guardrail_name,
            "decision": self.decision,
            "detected": self.detected,
            "reason": self.reason,
            "count": self.count,
            "score": self.score,
            "types": self.types,
            "findings": [finding.to_dict() for finding in self.findings],
            "input_length": self.input_length,
            "duration_ms": self.duration_ms,
        }

    def __str__(self) -> str:
        rows = [
            ("id", self.id),
            ("created at", self.created_at),
            ("guardrail", f"{self.guardrail_id} ({self.guardrail_name})"),
            ("decision", self.decision),
            ("reason", self.reason),
            ("found", str(self.count)),
            ("score", str(self.score)),
            ("input length", f"{self.input_length} characters"),
            ("duration", f"{self.duration_ms} ms"),
        ]
        width = max(len(label) for label, _ in rows)
        lines = [f"{label:<{width}} : {value}" for label, value in rows]
        for finding in self.findings:
            where = f" in {finding.path}" if finding.path else ""
            lines.append(
                f"  - {finding.type} at {finding.start}-{finding.end}{where} "
                f"(confidence {finding.confidence}): {finding.preview}"
            )
        return "\n".join(lines)


class Guardrail(ABC):
    id: str
    name: str
    default_action: str

    def __init__(self, action: str | None = None) -> None:
        chosen = self.default_action if action is None else action
        if chosen not in ACTIONS:
            raise ValueError(f"action must be one of {ACTIONS}, not {chosen!r}")
        self.action = chosen

    @abstractmethod
    def find(self, text: str) -> list[Finding]:
        raise NotImplementedError

    def describe(self, findings: list[Finding]) -> str:
        count = len(findings)
        return (
            f"Found {count} item{'s' if count != 1 else ''}"
            if count
            else "Nothing found"
        )

    def find_in(self, text: str, context: dict[str, object] | None) -> list[Finding]:
        del context
        return self.find(text)

    def check(
        self, text: str, context: dict[str, object] | None = None
    ) -> GuardrailResult:
        require_text(text)
        started = perf_counter()
        findings = self.find_in(text, context)
        return self._result(findings, len(text), started)

    def check_messages(
        self,
        messages: list[Any],
        context: dict[str, object] | None = None,
        roles: Iterable[str] | None = None,
    ) -> GuardrailResult:
        if not isinstance(messages, (list, tuple)):
            raise TypeError(
                f"messages must be a list of messages, not {type(messages).__name__}"
            )
        wanted = None if roles is None else frozenset(roles)
        started = perf_counter()
        findings: list[Finding] = []
        total = 0
        for slot in iter_slots(list(messages)):
            if wanted is not None and slot.role not in wanted:
                continue
            total += len(slot.text)
            for finding in self.find_in(slot.text, context):
                findings.append(replace(finding, path=slot.path))
        return self._result(findings, total, started)

    def _result(
        self, findings: list[Finding], input_length: int, started: float
    ) -> GuardrailResult:
        ordered = sorted(
            findings, key=lambda item: (item.path or "", item.start, item.end)
        )
        duration_ms = round((perf_counter() - started) * 1000, 3)
        return GuardrailResult(
            guardrail_id=self.id,
            guardrail_name=self.name,
            decision=self.action if ordered else PASS,
            reason=self.describe(ordered),
            findings=tuple(ordered),
            input_length=input_length,
            duration_ms=duration_ms,
        )

    def __call__(
        self, text: str, context: dict[str, object] | None = None
    ) -> GuardrailResult:
        return self.check(text, context)


def strictest(decisions: list[str]) -> str:
    return max(decisions, key=_SEVERITY.__getitem__, default=PASS)
