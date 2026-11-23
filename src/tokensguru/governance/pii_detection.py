"""PII detector: finds personal data in text.

PII means personally identifiable information. This detector looks for the kinds
that have a recognizable shape and can be checked:

    email         jane@example.com (also disguised ones, see EmailDetector)
    credit_card   a card number with a valid check digit and issuer
    iban          an international bank account number (mod-97 check)
    ssn           a US social security number (with the rules for a valid one)
    phone         +44 20 7946 0958, (212) 555-0147, or "phone: 0123 456 789"
    ip_address    an IPv4 or IPv6 address
    date_of_birth a real date written after "born", "DOB" or "date of birth"
    passport      a passport number written after the word "passport"

Each result has the type, the position, a confidence and a masked preview such as
**** **** **** 1111. The personal data itself is never stored in the result.

What it cannot find: names, postal addresses and anything else without a fixed
shape. That needs a language model (see ToxicityDetector and the backends for how
to plug one in). A number that fails its check (a card with a wrong check digit, an
impossible date) is not reported, which keeps false alarms low.

Options:
    action: "flag" (default) reports a finding, "block" tells the caller to stop.
    types: only look for these types (default: all of the above).
    allowed_domains: email domains to ignore, subdomains included.
    include_private_ips: also report private and loopback IP addresses (default True).

How to use it:
    from tokensguru.governance import PiiDetector

    result = PiiDetector().check("Call (212) 555-0147 or mail jane@example.com")
    result.decision, result.types
    print(result)

It is safe on any input: every pattern has bounded repeats.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable, Iterable

from tokensguru.governance.base import Finding, Guardrail
from tokensguru.governance.email_detection import EmailDetector
from tokensguru.governance.masking import mask_digits, mask_secret
from tokensguru.governance.normalize import fold
from tokensguru.governance.pii_validators import (
    MIN_INTL_DIGITS,
    credit_card_valid,
    date_valid,
    digits_only,
    iban_valid,
    ip_valid,
    phone_digits_valid,
    ssn_valid,
)
from tokensguru.governance.spans import SpanSet

TYPES = (
    "credit_card",
    "iban",
    "ssn",
    "email",
    "phone",
    "ip_address",
    "date_of_birth",
    "passport",
)

_CARD = re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")
_IBAN = re.compile(
    r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?"
    r"(?![A-Za-z0-9])"
)
_SSN = re.compile(r"(?<![\d-])(?P<a>\d{3})[- ](?P<g>\d{2})[- ](?P<s>\d{4})(?![\d-])")
_SSN_CONTEXT = re.compile(
    r"(?i)\b(?:ssn|social[ ]security(?:[ ]number)?)\W{0,3}(?P<v>\d{9})(?!\d)"
)
_PHONE_INTL = re.compile(r"(?<![\w+])\+(?P<v>\d[\d ().-]{6,20}\d)(?!\d)")
_PHONE_NANP = re.compile(
    r"(?<![\d+])(?:\+?1[ .-]?)?(?:\([2-9]\d{2}\)|[2-9]\d{2})[ .-]?"
    r"[2-9]\d{2}[ .-]?\d{4}(?!\d)"
)
_PHONE_CONTEXT = re.compile(
    r"(?i)\b(?:phone|tel|telephone|mobile|cell|fax|whatsapp)\b[^\S\n]{0,2}"
    r"[:#=-]?[^\S\n]{0,2}(?P<v>\+?\d[\d ().-]{5,16}\d)"
)
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_IPV6 = re.compile(r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}(?![\w:])")
_MONTH = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_DATE = (
    rf"(?:\d{{4}}-\d{{1,2}}-\d{{1,2}}|\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{2,4}}|"
    rf"\d{{1,2}}(?:st|nd|rd|th)?[ ]{_MONTH}\.?,?[ ]\d{{4}}|"
    rf"{_MONTH}\.?[ ]\d{{1,2}}(?:st|nd|rd|th)?,?[ ]\d{{4}})"
)
_DOB = re.compile(
    r"(?i)\b(?:d\.?o\.?b\.?|date[ ]of[ ]birth|birth[ ]?date|born(?:[ ]on)?|birthday)"
    rf"(?![A-Za-z0-9])[^\S\n]{{0,2}}[:\-]?[^\S\n]{{0,2}}(?P<v>{_DATE})\b"
)
_PASSPORT = re.compile(
    r"(?i)\bpassport(?:[ ](?:number|no\.?|#))?(?![A-Za-z0-9])"
    r"[^\S\n]{0,2}[:#=-]?[^\S\n]{0,2}"
    r"(?P<v>[A-Z0-9]{6,9})\b"
)
CARD_CONFIDENCE = 0.97
IBAN_CONFIDENCE = 0.95
SSN_CONFIDENCE = 0.85
SSN_CONTEXT_CONFIDENCE = 0.8
PHONE_INTL_CONFIDENCE = 0.8
PHONE_NANP_CONFIDENCE = 0.75
PHONE_CONTEXT_CONFIDENCE = 0.7
IP_CONFIDENCE = 0.7
DOB_CONFIDENCE = 0.8
PASSPORT_CONFIDENCE = 0.7

Hit = tuple[int, int, float, str]


def _group(match: re.Match[str], name: str) -> tuple[int, int, str]:
    return match.start(name), match.end(name), match.group(name)


_CARD_GROUPS = re.compile(r"\d+")
MAX_CARD_GROUPS = 6


def _card_window(
    candidate: str, groups: list[tuple[int, int]]
) -> tuple[int, int] | None:
    if len(groups) > MAX_CARD_GROUPS or len(set(digits_only(candidate))) == 1:
        return None
    for first in range(len(groups)):
        for last in range(len(groups) - 1, first - 1, -1):
            start, end = groups[first][0], groups[last][1]
            if credit_card_valid(candidate[start:end]):
                return start, end
    return None


def _cards(text: str) -> Iterable[Hit]:
    position = 0
    while True:
        match = _CARD.search(text, position)
        if match is None:
            return
        candidate = match.group(0)
        groups = [(m.start(), m.end()) for m in _CARD_GROUPS.finditer(candidate)]
        window = _card_window(candidate, groups)
        if window:
            start, end = match.start() + window[0], match.start() + window[1]
            yield start, end, CARD_CONFIDENCE, mask_digits(text[start:end], 4)
            position = end
        else:
            same = len(set(digits_only(candidate))) == 1
            offset = len(candidate) if same or len(groups) < 2 else groups[1][0]  # noqa: PLR2004
            position = match.start() + offset


def _ibans(text: str) -> Iterable[Hit]:
    for match in _IBAN.finditer(text):
        if iban_valid(match.group(0)):
            yield (
                match.start(),
                match.end(),
                IBAN_CONFIDENCE,
                mask_secret(match.group(0), 2),
            )


def _ssns(text: str) -> Iterable[Hit]:
    for match in _SSN.finditer(text):
        if ssn_valid(match.group("a"), match.group("g"), match.group("s")):
            preview = f"***-**-{match.group('s')}"
            yield match.start(), match.end(), SSN_CONFIDENCE, preview
    for match in _SSN_CONTEXT.finditer(text):
        start, end, value = _group(match, "v")
        if ssn_valid(value[:3], value[3:5], value[5:]):
            yield start, end, SSN_CONTEXT_CONFIDENCE, mask_digits(value, 4)


def _phones(text: str) -> Iterable[Hit]:
    for match in _PHONE_INTL.finditer(text):
        if phone_digits_valid(match.group("v"), MIN_INTL_DIGITS):
            yield (
                match.start(),
                match.end(),
                PHONE_INTL_CONFIDENCE,
                mask_digits(match.group(0), 4),
            )
    for match in _PHONE_NANP.finditer(text):
        value = match.group(0)
        if any(char in value for char in " .()-") and len(digits_only(value)) >= 10:  # noqa: PLR2004
            yield (
                match.start(),
                match.end(),
                PHONE_NANP_CONFIDENCE,
                mask_digits(value, 4),
            )
    for match in _PHONE_CONTEXT.finditer(text):
        start, end, value = _group(match, "v")
        if phone_digits_valid(value):
            yield start, end, PHONE_CONTEXT_CONFIDENCE, mask_digits(value, 4)


def _mask_ip(value: str) -> str:
    if ":" in value:
        return value.split(":", maxsplit=1)[0] + ":***"
    first, second, *_ = value.split(".")
    return f"{first}.{second}.*.*"


class PiiDetector(Guardrail):
    id = "pii_detection"
    name = "PII detection"
    default_action = "flag"
    supported_types = TYPES

    def __init__(
        self,
        action: str | None = None,
        types: Iterable[str] | None = None,
        allowed_domains: Iterable[str] = (),
        include_private_ips: bool = True,
    ) -> None:
        super().__init__(action)
        chosen = tuple(TYPES if types is None else types)
        unknown = [kind for kind in chosen if kind not in TYPES]
        if unknown:
            raise ValueError(f"unknown PII types {unknown}; choose from {TYPES}")
        self.types = frozenset(chosen)
        self.include_private_ips = include_private_ips
        self._email = EmailDetector(allowed_domains=allowed_domains)

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "No personal data found"
        count = len(findings)
        return f"Found {count} piece{'s' if count != 1 else ''} of personal data"

    def find(self, text: str) -> list[Finding]:
        folded = fold(text)
        candidates: list[Finding] = []
        scanners: list[tuple[str, Callable[[str], Iterable[Hit]]]] = [
            ("credit_card", _cards),
            ("iban", _ibans),
            ("ssn", _ssns),
            ("phone", _phones),
            ("ip_address", self._ips),
            ("date_of_birth", self._birth_dates),
            ("passport", self._passports),
        ]
        for kind, scanner in scanners:
            if kind not in self.types:
                continue
            for start, end, confidence, preview in scanner(folded.text):
                first, last = folded.span(start, end)
                candidates.append(
                    Finding(kind, "pii", first, last, confidence, preview)
                )
        if "email" in self.types:
            candidates.extend(self._email.find(text))
        return self._without_overlaps(candidates)

    @staticmethod
    def _without_overlaps(candidates: list[Finding]) -> list[Finding]:
        order = {kind: index for index, kind in enumerate(TYPES)}
        spans = SpanSet()
        kept = []
        for finding in sorted(
            candidates, key=lambda item: (order[item.type], item.start)
        ):
            if spans.add(finding.start, finding.end):
                kept.append(finding)
        return kept

    def _ips(self, text: str) -> Iterable[Hit]:
        for pattern in (_IPV4, _IPV6):
            for match in pattern.finditer(text):
                value = match.group(0)
                if len(value) < 3 or not ip_valid(value):  # noqa: PLR2004
                    continue
                if not self.include_private_ips and self._is_private(value):
                    continue
                yield match.start(), match.end(), IP_CONFIDENCE, _mask_ip(value)

    @staticmethod
    def _is_private(value: str) -> bool:
        address = ipaddress.ip_address(value)
        return address.is_private or address.is_loopback or address.is_link_local

    @staticmethod
    def _birth_dates(text: str) -> Iterable[Hit]:
        for match in _DOB.finditer(text):
            start, end, value = _group(match, "v")
            if date_valid(value):
                yield start, end, DOB_CONFIDENCE, mask_digits(value, 0)

    @staticmethod
    def _passports(text: str) -> Iterable[Hit]:
        for match in _PASSPORT.finditer(text):
            start, end, value = _group(match, "v")
            if any(char.isdigit() for char in value):
                yield start, end, PASSPORT_CONFIDENCE, mask_secret(value)
