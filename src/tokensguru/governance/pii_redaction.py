"""PII redactor: replaces personal data and (optionally) secrets with safe text.

It runs the PII detector, and optionally the API key detector, and rewrites each
thing it finds. Three modes decide what the replacement looks like:

    placeholder   [EMAIL], [PHONE], [CREDIT_CARD], [SSN], [SECRET] ... (default)
    mask          a partial mask that keeps a little context: j***@example.com,
                  **** **** **** 1111, +X-XXX-XXX-0147, 192.168.*.*
    pseudonym     <EMAIL_1>, <PHONE_2> ... The same value always gets the same
                  number within one call, so the text still reads sensibly
                  ("<EMAIL_1> wrote to <EMAIL_2>, then <EMAIL_1> replied").

Redacting twice changes nothing more: the replacements are never detected again.
The text around what was found is kept exactly as it was.

For chat messages, redact_messages() rewrites the text of every message and keeps
the structure. The JSON arguments of a tool call stay valid JSON: only the text
values inside are changed, never the keys or the shape. Your list is not changed;
you get a redacted copy.

Options:
    mode: "placeholder" (default), "mask" or "pseudonym".
    types: only redact these PII types (default: all, see PiiDetector).
    include_secrets: also redact API keys and tokens (default False).
    allowed_domains: email domains to leave alone, subdomains included.
    include_private_ips: also redact private and loopback IP addresses (default True).

How to use it:
    from tokensguru.governance import PiiRedactor

    result = PiiRedactor().check("Mail jane@example.com or call (212) 555-0147")
    result.redacted_text      # "Mail [EMAIL] or call [PHONE]"
    result.decision           # "redact" (or "pass" when nothing was found)
    print(result)

    clean = PiiRedactor().redact_messages(messages).redacted_messages
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from tokensguru.governance.api_key_detection import ApiKeyDetector
from tokensguru.governance.base import REDACT, Finding, Guardrail, GuardrailResult
from tokensguru.governance.masking import mask_digits, mask_email
from tokensguru.governance.messages import JSON, TextSlot, iter_slots, rewrite_texts
from tokensguru.governance.pii_detection import PiiDetector
from tokensguru.governance.pii_validators import digits_only
from tokensguru.governance.spans import SpanSet
from tokensguru.utils.validation import require_text

MODES = ("placeholder", "mask", "pseudonym")
IBAN_KEEP_START = 2
IBAN_KEEP_END = 4
PASSPORT_KEEP = 2
PLACEHOLDERS = {
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "credit_card": "[CREDIT_CARD]",
    "ssn": "[SSN]",
    "iban": "[IBAN]",
    "ip_address": "[IP_ADDRESS]",
    "date_of_birth": "[DATE_OF_BIRTH]",
    "passport": "[PASSPORT]",
    "private_key": "[PRIVATE_KEY]",
}
SECRET_PLACEHOLDER = "[SECRET]"  # noqa: S105
_EMAIL_PARTS = re.compile(r"^(?P<local>.+?)@(?P<domain>[^@\s]+)$")


@dataclass(frozen=True)
class RedactionResult(GuardrailResult):
    redacted_text: str = ""
    redacted_messages: list[Any] | None = None
    mode: str = "placeholder"
    replacements: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        data = super().to_dict()
        data["mode"] = self.mode
        data["redacted_text"] = self.redacted_text
        data["replacements"] = self.replacements
        if self.redacted_messages is not None:
            data["redacted_messages"] = self.redacted_messages
        return data

    def __str__(self) -> str:
        return f"{super().__str__()}\nmode         : {self.mode}"


class _State:
    def __init__(self) -> None:
        self.numbers: dict[tuple[str, str], int] = {}
        self.counts: dict[str, int] = {}


def _normalize(finding_type: str, value: str) -> str:
    if finding_type in {"phone", "credit_card", "ssn"}:
        return digits_only(value)
    return value.replace(" ", "").lower()


def _mask_iban(value: str) -> str:
    compact = len(value.replace(" ", ""))
    seen = 0
    out = []
    for char in value:
        if char == " ":
            out.append(char)
            continue
        seen += 1
        keep = seen <= IBAN_KEEP_START or seen > compact - IBAN_KEEP_END
        out.append(char if keep else "*")
    return "".join(out)


def _mask_ip(value: str) -> str:
    if ":" in value:
        return value.split(":", maxsplit=1)[0] + ":***"
    first, second, *_ = value.split(".")
    return f"{first}.{second}.*.*"


def _mask_passport(value: str) -> str:
    return "*" * max(len(value) - PASSPORT_KEEP, 1) + value[-PASSPORT_KEEP:]


_MASKERS: dict[str, Callable[[str], str]] = {
    "phone": lambda value: mask_digits(value, 4).replace("*", "X"),
    "credit_card": lambda value: mask_digits(value, 4),
    "ssn": lambda value: mask_digits(value, 4),
    "iban": _mask_iban,
    "ip_address": _mask_ip,
    "date_of_birth": lambda value: mask_digits(value, 0),
    "passport": _mask_passport,
}


def _mask(finding: Finding, value: str) -> str:
    if finding.category == "secret":
        prefix = finding.preview.split("***")[0]
        return f"{prefix}{PLACEHOLDERS.get(finding.type, SECRET_PLACEHOLDER)}"
    email = _EMAIL_PARTS.match(value) if finding.type == "email" else None
    if email:
        return mask_email(email.group("local"), email.group("domain"))
    masker = _MASKERS.get(finding.type)
    return (
        masker(value) if masker else PLACEHOLDERS.get(finding.type, SECRET_PLACEHOLDER)
    )


class PiiRedactor(Guardrail):
    id = "pii_redaction"
    name = "PII redaction"
    default_action = "flag"

    def __init__(
        self,
        mode: str = "placeholder",
        types: Iterable[str] | None = None,
        include_secrets: bool = False,
        allowed_domains: Iterable[str] = (),
        include_private_ips: bool = True,
    ) -> None:
        super().__init__()
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.mode = mode
        self._pii = PiiDetector(
            types=types,
            allowed_domains=allowed_domains,
            include_private_ips=include_private_ips,
        )
        self._secrets = ApiKeyDetector(action="flag") if include_secrets else None

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "Nothing to redact"
        count = len(findings)
        return f"Redacted {count} item{'s' if count != 1 else ''}"

    def find(self, text: str) -> list[Finding]:
        spans = SpanSet()
        kept: list[Finding] = []
        detectors: list[Guardrail] = [self._pii]
        if self._secrets is not None:
            detectors.insert(0, self._secrets)
        for detector in detectors:
            for finding in detector.find(text):
                if spans.add(finding.start, finding.end):
                    kept.append(finding)
        return sorted(kept, key=lambda item: item.start)

    def check(
        self, text: str, context: dict[str, object] | None = None
    ) -> RedactionResult:
        del context
        require_text(text)
        started = perf_counter()
        state = _State()
        findings = self.find(text)
        redacted = self._apply(text, findings, state)
        return self._build(findings, len(text), started, redacted, None, state)

    def redact(self, text: str) -> str:
        return self.check(text).redacted_text

    def redact_messages(
        self, messages: list[Any], roles: Iterable[str] | None = None
    ) -> RedactionResult:
        if not isinstance(messages, (list, tuple)):
            raise TypeError(
                f"messages must be a list of messages, not {type(messages).__name__}"
            )
        wanted = None if roles is None else frozenset(roles)
        started = perf_counter()
        state = _State()
        findings: list[Finding] = []
        total = sum(
            len(slot.text)
            for slot in iter_slots(list(messages))
            if wanted is None or slot.role in wanted
        )

        def rewrite(slot: TextSlot) -> str:
            if wanted is not None and slot.role not in wanted:
                return slot.text
            if slot.kind == JSON:
                return self._redact_json(slot, findings, state)
            return self._redact_text(slot, slot.text, findings, state)

        redacted = rewrite_texts(list(messages), rewrite)
        return self._build(findings, total, started, "", redacted, state)

    def _redact_text(
        self, slot: TextSlot, text: str, found: list[Finding], state: _State
    ) -> str:
        findings = self.find(text)
        found.extend(_with_path(finding, slot.path) for finding in findings)
        return self._apply(text, findings, state)

    def _redact_json(self, slot: TextSlot, found: list[Finding], state: _State) -> str:
        try:
            data = json.loads(slot.text)
        except ValueError:
            return self._redact_text(slot, slot.text, found, state)

        def walk(value: Any) -> Any:
            if isinstance(value, str):
                return self._redact_text(slot, value, found, state)
            if isinstance(value, list):
                return [walk(item) for item in value]
            if isinstance(value, dict):
                return {key: walk(item) for key, item in value.items()}
            return value

        return json.dumps(walk(data), ensure_ascii=False)

    def _apply(self, text: str, findings: list[Finding], state: _State) -> str:
        pieces: list[str] = []
        cursor = 0
        for finding in findings:
            value = text[finding.start : finding.end]
            pieces.append(text[cursor : finding.start])
            pieces.append(self._replacement(finding, value, state))
            cursor = finding.end
        pieces.append(text[cursor:])
        return "".join(pieces)

    def _replacement(self, finding: Finding, value: str, state: _State) -> str:
        label = "SECRET" if finding.category == "secret" else finding.type.upper()
        state.counts[label] = state.counts.get(label, 0) + 1
        if self.mode == "mask":
            return _mask(finding, value)
        if self.mode == "pseudonym":
            key = (label, _normalize(finding.type, value))
            number = state.numbers.setdefault(
                key, 1 + sum(1 for seen in state.numbers if seen[0] == label)
            )
            return f"<{label}_{number}>"
        if finding.category == "secret":
            return PLACEHOLDERS.get(finding.type, SECRET_PLACEHOLDER)
        return PLACEHOLDERS[finding.type]

    def _build(  # noqa: PLR0913, PLR0917
        self,
        findings: list[Finding],
        length: int,
        started: float,
        text: str,
        messages: list[Any] | None,
        state: _State,
    ) -> RedactionResult:
        ordered = sorted(findings, key=lambda f: (f.path or "", f.start, f.end))
        return RedactionResult(
            guardrail_id=self.id,
            guardrail_name=self.name,
            decision=REDACT if ordered else "pass",
            reason=self.describe(ordered),
            findings=tuple(ordered),
            input_length=length,
            duration_ms=round((perf_counter() - started) * 1000, 3),
            redacted_text=text,
            redacted_messages=messages,
            mode=self.mode,
            replacements=dict(state.counts),
        )


def _with_path(finding: Finding, path: str) -> Finding:
    return Finding(
        finding.type,
        finding.category,
        finding.start,
        finding.end,
        finding.confidence,
        finding.preview,
        path,
    )
