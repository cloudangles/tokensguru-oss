"""Email detector: finds email addresses in text.

What it does:
    - Finds email addresses such as jane.doe+news@mail.example.com, including
      addresses with accented or non-Latin letters (josé@exemple.fr).
    - Also finds emails that were disguised: typed with full-width characters,
      split with invisible zero-width characters, or written as jane[at]example[dot]com.
    - Reports where each one is, with a masked preview (j***@example.com). The
      address itself is never stored in the result.

What it does not report (these only look like emails):
    - Image and file names such as logo@2x.png, and git addresses such as
      git@github.com:user/repo.
    - The password part of a web address with a login, such as
      https://user:secret@host.com.
    - Handles such as @jane, text without a real domain (jane@localhost), and
      addresses with a local part over 64 characters or a domain over 253.

Where an address starts: the characters / ? & = # are treated as the end of
whatever came before, so ?to=jane@example.com and //jane@example.com are reported
as jane@example.com.

Options:
    action: "flag" (default) reports a finding, "block" tells the caller to stop.
    detect_obfuscated: also find the disguised forms with [at] and [dot] (default True).
    allowed_domains: domains to ignore, including their subdomains, for example your
        own company domain.

How to use it:
    from tokensguru.governance import EmailDetector

    result = EmailDetector().check("Write to jane@example.com")
    result.decision, result.count, result.findings
    print(result)

It is safe on any input: it never scans more than a fixed window around each "@",
so a huge or hostile text cannot make it slow.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from tokensguru.governance.base import Finding, Guardrail
from tokensguru.governance.masking import mask_email
from tokensguru.governance.normalize import fold
from tokensguru.governance.spans import SpanSet

MAX_LOCAL = 64
MAX_DOMAIN = 253
MAX_LABEL = 63
MIN_LABELS = 2
MIN_TLD = 2
PUNYCODE_PREFIX = "xn--"
NORMAL_CONFIDENCE = 0.95
OBFUSCATED_CONFIDENCE = 0.8
URL_LOOKBACK = 256
LOCAL_START_MARKS = "/?&=#"
DISGUISE_MARKS = "[({"
MASK_MARK = "***"

_LOCAL_CHAR = r"(?:[^\W_]|[.!#$%&'*+/=?^_`{|}~-])"
_LOCAL_RUN = re.compile(f"{_LOCAL_CHAR}*")
_DOMAIN_RUN = re.compile(r"(?:[^\W_]|[.-])*")
_LOCAL_SYMBOLS = frozenset(".!#$%&'*+/=?^_`{|}~-")
_FILE_EXTENSIONS = frozenset(
    [
        "png",
        "jpg",
        "jpeg",
        "gif",
        "svg",
        "webp",
        "bmp",
        "ico",
        "css",
        "js",
        "json",
        "html",
        "htm",
        "xml",
        "woff",
        "woff2",
        "ttf",
        "map",
    ]
)
_GIT_HOSTS = frozenset({"github.com", "gitlab.com", "bitbucket.org"})
_AT = r"\s{0,3}[\[\(\{]\s{0,3}at\s{0,3}[\]\)\}]\s{0,3}"
_DOT = r"(?:\.|\s{0,3}[\[\(\{]\s{0,3}dot\s{0,3}[\]\)\}]\s{0,3})"
_LABEL = r"[A-Za-z0-9-]{1,63}"
_ANCHOR = re.compile(r"@|[\[\(\{]\s{0,3}at\s{0,3}[\]\)\}]", re.IGNORECASE)
_DISGUISED_DOMAIN = re.compile(
    rf"\s{{0,3}}(?P<domain>{_LABEL}(?:{_DOT}{_LABEL}){{1,6}})", re.IGNORECASE
)
_ASCII_LOCAL_RUN = re.compile(r"[A-Za-z0-9._%+-]*")
_DOT_WORD = re.compile(_DOT, re.IGNORECASE)
SPACES_AROUND_AT = 3


def _is_local(char: str) -> bool:
    if char < "\x80":
        return char.isalnum() or char in _LOCAL_SYMBOLS
    return char.isalnum()


def _scan_left(text: str, at: int) -> int | None:
    floor = max(0, at - (MAX_LOCAL + 1))
    reversed_window = text[floor:at][::-1]
    run = _LOCAL_RUN.match(reversed_window)
    length = run.end() if run else 0
    start = at - length
    if start == floor and start > 0 and _is_local(text[start - 1]):
        return None
    mark = max((text.rfind(char, start, at) for char in LOCAL_START_MARKS), default=-1)
    return mark + 1 if mark >= start else start


def _scan_right(text: str, at: int) -> int | None:
    ceiling = min(len(text), at + MAX_DOMAIN + 2)
    run = _DOMAIN_RUN.match(text, at + 1, ceiling)
    end = run.end() if run else at + 1
    if end == ceiling and end < len(text) and text[end] not in " \n\t":
        following = _DOMAIN_RUN.match(text, end, end + 1)
        if following and following.end() > end:
            return None
    return end


def _valid_local(local: str) -> bool:
    return (
        0 < len(local) <= MAX_LOCAL
        and not local.endswith(".")
        and ".." not in local
        and all(_is_local(char) for char in local)
    )


def _valid_label(label: str) -> bool:
    return (
        0 < len(label) <= MAX_LABEL
        and not label.startswith("-")
        and not label.endswith("-")
        and all(char.isalnum() or char == "-" for char in label)
    )


def _valid_domain(domain: str) -> bool:
    labels = domain.split(".")
    if len(domain) > MAX_DOMAIN or len(labels) < MIN_LABELS:
        return False
    if not all(_valid_label(label) for label in labels):
        return False
    tld = labels[-1].lower()
    is_name = tld.isalpha() and len(tld) >= MIN_TLD
    is_punycode = tld.startswith(PUNYCODE_PREFIX) and len(tld) > len(PUNYCODE_PREFIX)
    return (is_name or is_punycode) and tld not in _FILE_EXTENSIONS


def _is_url_password(text: str, local_start: int) -> bool:
    if local_start == 0 or text[local_start - 1] != ":":
        return False
    scheme = text.rfind("://", max(0, local_start - URL_LOOKBACK), local_start)
    if scheme == -1:
        return False
    between = text[scheme + 3 : local_start]
    return not any(char.isspace() or char in "/?#" for char in between)


def _is_git_address(text: str, local: str, domain: str, domain_end: int) -> bool:
    if local.lower() != "git" and domain.lower() not in _GIT_HOSTS:
        return False
    colon = text[domain_end : domain_end + 1]
    after = text[domain_end + 1 : domain_end + 2]
    return colon == ":" and (after.isalpha() or after == "/")


class EmailDetector(Guardrail):
    id = "email_detection"
    name = "Email detection"
    default_action = "flag"

    def __init__(
        self,
        action: str | None = None,
        detect_obfuscated: bool = True,
        allowed_domains: Iterable[str] = (),
    ) -> None:
        super().__init__(action)
        self.detect_obfuscated = detect_obfuscated
        cleaned = (domain.strip().lstrip("@.").lower() for domain in allowed_domains)
        self.allowed_domains = frozenset(domain for domain in cleaned if domain)

    def describe(self, findings: list[Finding]) -> str:
        if not findings:
            return "No email address found"
        count = len(findings)
        return f"Found {count} email address{'es' if count != 1 else ''}"

    def find(self, text: str) -> list[Finding]:
        folded = fold(text)
        spans = SpanSet()
        found: list[tuple[int, int, str, str, float]] = []
        for start, end, local, domain in self._plain(folded.text):
            if self._accept(spans, start, end, domain):
                found.append((start, end, local, domain, NORMAL_CONFIDENCE))
        if self.detect_obfuscated:
            for start, end, local, domain in self._disguised(folded.text):
                if self._accept(spans, start, end, domain):
                    found.append((start, end, local, domain, OBFUSCATED_CONFIDENCE))
        findings = []
        for start, end, local, domain, confidence in found:
            first, last = folded.span(start, end)
            preview = mask_email(local, domain)
            findings.append(Finding("email", "pii", first, last, confidence, preview))
        return findings

    def _accept(self, spans: SpanSet, start: int, end: int, domain: str) -> bool:
        if self._is_allowed(domain):
            return False
        return spans.add(start, end)

    def _is_allowed(self, domain: str) -> bool:
        lowered = domain.lower()
        return any(
            lowered == allowed or lowered.endswith("." + allowed)
            for allowed in self.allowed_domains
        )

    def _plain(self, text: str) -> Iterable[tuple[int, int, str, str]]:
        at = text.find("@")
        while at != -1:
            candidate = self._candidate(text, at)
            if candidate:
                yield candidate
            at = text.find("@", at + 1)

    def _candidate(self, text: str, at: int) -> tuple[int, int, str, str] | None:
        start = _scan_left(text, at)
        end = _scan_right(text, at)
        if start is None or end is None:
            return None
        while start < at and text[start] == ".":
            start += 1
        while end > at + 1 and text[end - 1] in ".-":
            end -= 1
        local, domain = text[start:at], text[at + 1 : end]
        if not (_valid_local(local) and _valid_domain(domain)):
            return None
        if MASK_MARK in local:
            return None
        if _is_url_password(text, start) or _is_git_address(text, local, domain, end):
            return None
        return start, end, local, domain

    def _disguised(self, text: str) -> Iterable[tuple[int, int, str, str]]:
        for anchor in _ANCHOR.finditer(text):
            candidate = self._disguised_at(text, anchor)
            if candidate:
                yield candidate

    def _disguised_at(
        self, text: str, anchor: re.Match[str]
    ) -> tuple[int, int, str, str] | None:
        left = anchor.start()
        for _ in range(SPACES_AROUND_AT):
            if left > 0 and text[left - 1] in " \t":
                left -= 1
        window = text[max(0, left - (MAX_LOCAL + 1)) : left][::-1]
        run = _ASCII_LOCAL_RUN.match(window)
        length = run.end() if run else 0
        domain_match = _DISGUISED_DOMAIN.match(text, anchor.end())
        if length == 0 or length > MAX_LOCAL or not domain_match:
            return None
        end = domain_match.end()
        if not any(char in DISGUISE_MARKS for char in text[anchor.start() : end]):
            return None
        raw = text[left - length : left]
        local = raw.lstrip(".")
        domain = _DOT_WORD.sub(".", domain_match.group("domain"))
        if not (_valid_local(local) and _valid_domain(domain)):
            return None
        return left - len(local), end, local, domain
