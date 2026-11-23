"""API key detector: finds API keys, tokens and other secrets in text.

What it does:
    - Finds credentials from many providers by their documented format: OpenAI,
      Anthropic, AWS, GitHub (classic and fine-grained), GitLab, Slack, Google,
      Stripe, SendGrid, Twilio, Mailgun, npm, PyPI, Hugging Face and Azure.
    - Finds private key blocks (the whole BEGIN to END block), JSON Web Tokens,
      passwords inside web addresses (postgres://user:password@host), Authorization
      headers, AWS secret keys next to their name, and "password=..." style lines
      whose value looks random.
    - Sees through simple hiding tricks: invisible zero-width characters inside a
      key and full-width look-alike characters.
    - Reports the type, the position and a short masked preview. The secret itself
      is never stored in the result. Only the provider's own fixed prefix (for
      example "ghp_") can appear in the preview.

What it does not report:
    - Obvious placeholders such as sk-your-api-key-here, tokens made of repeated
      characters, or values containing words like "example" and "dummy".
    - Random-looking words that are too short, or too regular, to be a secret.

Options:
    action: "block" (default) tells the caller to stop, "flag" only reports.
    include_generic: also find "password=..." style lines (default True). These are
        the weakest matches, so each one has a lower confidence.
    ignore_placeholders: skip obvious placeholders (default True).

How to use it:
    from tokensguru.governance import ApiKeyDetector

    result = ApiKeyDetector().check(prompt)
    result.decision, result.count, result.types
    print(result)

It is safe on any input: every pattern has bounded repeats, so a huge or hostile
text cannot make it slow.
"""

from __future__ import annotations

from tokensguru.governance.base import Finding, Guardrail
from tokensguru.governance.masking import looks_like_placeholder, mask_secret
from tokensguru.governance.normalize import Folded, fold
from tokensguru.governance.secret_patterns import (
    CONTEXT_PATTERNS,
    PRIVATE_KEY_END,
    PRIVATE_KEY_HEADER,
    PRIVATE_KEY_MAX,
    SUPPORTED_TYPES,
    VENDOR_PATTERNS,
    SecretPattern,
)
from tokensguru.governance.spans import SpanSet

PRIVATE_KEY_CONFIDENCE = 0.99
FOOTER_CLOSE = "-----"


def _private_key_span(text: str, header_start: int, header_end: int) -> tuple[int, int]:
    footer = text.find(PRIVATE_KEY_END, header_end, header_end + PRIVATE_KEY_MAX)
    if footer == -1:
        return header_start, header_end
    close = text.find(FOOTER_CLOSE, footer + len(PRIVATE_KEY_END), footer + 80)
    if close == -1:
        return header_start, header_end
    return header_start, close + len(FOOTER_CLOSE)


class ApiKeyDetector(Guardrail):
    id = "api_key_detection"
    name = "API key detection"
    default_action = "block"
    supported_types = SUPPORTED_TYPES

    def __init__(
        self,
        action: str | None = None,
        include_generic: bool = True,
        ignore_placeholders: bool = True,
    ) -> None:
        super().__init__(action)
        self.include_generic = include_generic
        self.ignore_placeholders = ignore_placeholders

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "No API key or secret found"
        count = len(findings)
        return f"Found {count} secret{'s' if count != 1 else ''}"

    def find(self, text: str) -> list[Finding]:
        folded = fold(text)
        spans = SpanSet()
        findings: list[Finding] = []
        self._private_keys(folded, spans, findings)
        patterns = VENDOR_PATTERNS[:-1] + CONTEXT_PATTERNS[:1] + VENDOR_PATTERNS[-1:]
        for pattern in patterns + CONTEXT_PATTERNS[1:]:
            if pattern.type == "generic_secret" and not self.include_generic:
                continue
            self._scan(pattern, folded, spans, findings)
        return findings

    def _private_keys(
        self, folded: Folded, spans: SpanSet, findings: list[Finding]
    ) -> None:
        for header in PRIVATE_KEY_HEADER.finditer(folded.text):
            start, end = _private_key_span(folded.text, header.start(), header.end())
            if spans.add(start, end):
                first, last = folded.span(start, end)
                preview = f"{header.group(0)} *** ({end - start} chars)"
                findings.append(
                    Finding(
                        "private_key",
                        "secret",
                        first,
                        last,
                        PRIVATE_KEY_CONFIDENCE,
                        preview,
                    )
                )

    def _scan(
        self,
        pattern: SecretPattern,
        folded: Folded,
        spans: SpanSet,
        findings: list[Finding],
    ) -> None:
        for match in pattern.regex.finditer(folded.text):
            group = "value" if "value" in pattern.regex.groupindex else 0
            value = match.group(group)
            if not self._is_secret(pattern, value):
                continue
            start, end = match.start(group), match.end(group)
            if not spans.add(start, end):
                continue
            first, last = folded.span(start, end)
            preview = mask_secret(value, pattern.keep)
            findings.append(
                Finding(
                    pattern.type, "secret", first, last, pattern.confidence, preview
                )
            )

    def _is_secret(self, pattern: SecretPattern, value: str) -> bool:
        if self.ignore_placeholders and looks_like_placeholder(value):
            return False
        return pattern.check is None or pattern.check(value)
