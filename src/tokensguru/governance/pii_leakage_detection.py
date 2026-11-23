"""PII leakage detector: checks a model's answer for data it should not reveal.

Run it on the model's output. It reports four kinds of leak:

    leaked_<type>          personal data or a secret in the answer that the user did
                           not provide, such as leaked_email or leaked_openai_api_key.
                           Data the user themselves typed (given as context["input"])
                           is not a leak, so it is not reported unless you ask.
    canary_leak            a secret canary string you planted in the system prompt
                           showed up in the answer. This is proof the system prompt
                           leaked. Make one with make_canary().
    system_prompt_leak     the answer repeats a run of words from your system prompt
                           word for word (8 words or more by default).
    protected_text_leak    the answer contains one of your own protected strings,
                           for example an internal project name.

Context you can pass (all optional):

    context = {
        "input": "what the user sent",            # a string or a messages list
        "system_prompt": "your system prompt",
        "canaries": [make_canary()],
        "protected": ["Project Falcon"],
    }
    result = PiiLeakageDetector().check(answer, context)

Without any context it still reports every piece of personal data and every secret
in the answer. Like the other guardrails, the result never contains the leaked data
itself. It holds the type, position, confidence and a masked preview.

Options:
    action: "block" (default) or "flag".
    report_echoed: also report personal data that came from the user's own input
        (default False).
    include_secrets: also look for API keys and tokens in the answer (default True).
    min_words: how many words in a row count as a system prompt leak (default 8).

Limits: leakage is found by matching, so a paraphrase of the system prompt is not
caught, and personal data that has no fixed shape (names) is not found without a
model.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from tokensguru.governance.api_key_detection import ApiKeyDetector
from tokensguru.governance.base import Finding, Guardrail
from tokensguru.governance.messages import iter_slots
from tokensguru.governance.normalize import fold
from tokensguru.governance.pii_detection import PiiDetector
from tokensguru.governance.pii_redaction import _normalize

CANARY_CONFIDENCE = 1.0
PROTECTED_CONFIDENCE = 0.95
PROMPT_LEAK_CONFIDENCE = 0.9
MIN_PROTECTED_CHARS = 4
MIN_WHOLE_PROMPT_CHARS = 30
MAX_REPEATS = 20
_WORD = re.compile(r"\w+")


def make_canary(prefix: str = "tg-canary") -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _input_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(slot.text for slot in iter_slots(list(value)))
    return ""


def _words(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0).lower(), m.start(), m.end()) for m in _WORD.finditer(text)]


MIN_WORDS_LIMIT = 2


class PiiLeakageDetector(Guardrail):
    id = "pii_leakage_detection"
    name = "PII leakage detection"
    default_action = "block"

    def __init__(
        self,
        action: str | None = None,
        report_echoed: bool = False,
        include_secrets: bool = True,
        min_words: int = 8,
    ) -> None:
        super().__init__(action)
        if (
            not isinstance(min_words, int)
            or isinstance(min_words, bool)
            or min_words < MIN_WORDS_LIMIT
        ):
            raise ValueError("min_words must be a whole number of 2 or more")
        self.report_echoed = report_echoed
        self.min_words = min_words
        self._pii = PiiDetector()
        self._secrets = ApiKeyDetector(action="flag") if include_secrets else None

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "No leak found"
        count = len(findings)
        return f"Found {count} possible leak{'s' if count != 1 else ''}"

    def find(self, text: str) -> list[Finding]:
        return self.find_in(text, None)

    def find_in(self, text: str, context: dict[str, object] | None) -> list[Finding]:
        context = context or {}
        findings = self._leaked_data(text, _input_text(context.get("input")))
        findings += self._literal_leaks(
            text, _strings(context.get("canaries")), "canary_leak", CANARY_CONFIDENCE
        )
        findings += self._literal_leaks(
            text,
            _strings(context.get("protected")),
            "protected_text_leak",
            PROTECTED_CONFIDENCE,
        )
        prompt = context.get("system_prompt")
        if isinstance(prompt, str) and prompt.strip():
            findings += self._prompt_leaks(text, prompt)
        return findings

    def _detectors(self) -> list[Guardrail]:
        return [self._pii] + ([self._secrets] if self._secrets else [])

    def _leaked_data(self, text: str, source: str) -> list[Finding]:
        known = set()
        if source and not self.report_echoed:
            for detector in self._detectors():
                for found in detector.find(source):
                    known.add(
                        (
                            found.type,
                            _normalize(found.type, source[found.start : found.end]),
                        )
                    )
        leaks = []
        for detector in self._detectors():
            for found in detector.find(text):
                value = _normalize(found.type, text[found.start : found.end])
                if (found.type, value) in known:
                    continue
                leaks.append(
                    Finding(
                        f"leaked_{found.type}",
                        "leak",
                        found.start,
                        found.end,
                        found.confidence,
                        found.preview,
                    )
                )
        return leaks

    @staticmethod
    def _literal_leaks(
        text: str, needles: Iterable[str], kind: str, confidence: float
    ) -> list[Finding]:
        folded = fold(text)
        haystack = folded.text.lower()
        if len(haystack) != len(folded.text):
            haystack = folded.text
        findings = []
        for raw in needles:
            needle = raw.lower()
            if len(needle) < MIN_PROTECTED_CHARS:
                continue
            start = haystack.find(needle)
            count = 0
            while start != -1 and count < MAX_REPEATS:
                first, last = folded.span(start, start + len(needle))
                findings.append(
                    Finding(
                        kind,
                        "leak",
                        first,
                        last,
                        confidence,
                        f"*** ({len(needle)} chars)",
                    )
                )
                start = haystack.find(needle, start + len(needle))
                count += 1
        return findings

    def _prompt_leaks(self, text: str, prompt: str) -> list[Finding]:
        prompt_words = [word for word, _, _ in _words(prompt)]
        if len(prompt_words) < self.min_words:
            return self._whole_prompt(text, prompt_words)
        size = self.min_words
        shingles = {
            tuple(prompt_words[i : i + size])
            for i in range(len(prompt_words) - size + 1)
        }
        output = _words(text)
        spans: list[tuple[int, int]] = []
        for index in range(len(output) - size + 1):
            window = tuple(word for word, _, _ in output[index : index + size])
            if window in shingles:
                start, end = output[index][1], output[index + size - 1][2]
                if spans and start <= spans[-1][1]:
                    spans[-1] = (spans[-1][0], max(spans[-1][1], end))
                else:
                    spans.append((start, end))
        return [
            Finding(
                "system_prompt_leak",
                "leak",
                start,
                end,
                PROMPT_LEAK_CONFIDENCE,
                f"{len(_WORD.findall(text[start:end]))} words from the system prompt",
            )
            for start, end in spans
        ]

    @staticmethod
    def _whole_prompt(text: str, prompt_words: list[str]) -> list[Finding]:
        phrase = " ".join(prompt_words)
        if len(phrase) < MIN_WHOLE_PROMPT_CHARS:
            return []
        output = _words(text)
        joined = " ".join(word for word, _, _ in output)
        at = joined.find(phrase)
        if at == -1:
            return []
        first_word = joined[:at].count(" ")
        last_word = first_word + len(prompt_words) - 1
        start, end = output[first_word][1], output[last_word][2]
        return [
            Finding(
                "system_prompt_leak",
                "leak",
                start,
                end,
                PROMPT_LEAK_CONFIDENCE,
                f"{len(prompt_words)} words from the system prompt",
            )
        ]


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if isinstance(item, str)]
    return []
