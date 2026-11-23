"""Safe previews of what was found, and small checks that cut false alarms.

A finding must never carry the secret or the personal data itself. These helpers
build the masked preview that is stored in its place.
"""

from __future__ import annotations

import re
from collections import Counter
from math import log2

_REPEATED = re.compile(r"(.)\1{9,}")
_PLACEHOLDER_WORDS = (
    "example", "your_", "your-", "yourkey", "placeholder", "dummy", "changeme",
    "change_me", "redacted", "insert", "token_here", "key_here", "sample", "fake",
    "xxxxxxxx", "********", "<", ">",
)  # fmt: skip


def mask_email(local: str, domain: str) -> str:
    return f"{local[:1]}***@{domain}"


def mask_secret(value: str, keep: int = 0) -> str:
    shown = value[:keep] if keep and len(value) > keep + 4 else ""
    return f"{shown}*** ({len(value)} chars)"


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    size = len(value)
    return -sum((n / size) * log2(n / size) for n in counts.values())


def looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return bool(_REPEATED.search(lowered)) or any(
        word in lowered for word in _PLACEHOLDER_WORDS
    )


def has_digit_and_letter(value: str) -> bool:
    return any(c.isdigit() for c in value) and any(c.isalpha() for c in value)


def mask_digits(value: str, keep: int = 0) -> str:
    total = sum(char.isdigit() for char in value)
    seen = 0
    masked = []
    for char in value:
        if char.isdigit():
            seen += 1
            masked.append(char if seen > total - keep else "*")
        else:
            masked.append(char)
    return "".join(masked)
