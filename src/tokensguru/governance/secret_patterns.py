"""The patterns that recognize API keys, tokens and other secrets.

Each pattern is built from the format its provider documents: a fixed prefix
followed by a body of a known length and alphabet. A strong prefix means a match
is almost certainly a real credential, so these have high confidence. The general
patterns at the end (a "password=" line, a bearer header) are weaker, so they also
need a value that looks random enough to be a secret.

Patterns are ordered from most to least specific. When two overlap, the earlier
one wins, so a GitHub token inside an Authorization header is reported once, as a
GitHub token.

Every quantifier has an upper bound, so no input can make a pattern run slowly.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from tokensguru.governance.masking import has_digit_and_letter, shannon_entropy

MIN_GENERIC_ENTROPY = 3.3
MIN_BEARER_ENTROPY = 3.0
MIN_HEX_ENTROPY = 2.5


def _entropy_at_least(minimum: float) -> Callable[[str], bool]:
    return lambda value: shannon_entropy(value) >= minimum


@dataclass(frozen=True)
class SecretPattern:
    type: str
    regex: re.Pattern[str]
    confidence: float
    keep: int = 0
    check: Callable[[str], bool] | None = None


def _pattern(
    kind: str,
    expression: str,
    confidence: float,
    keep: int = 0,
    check: Callable[[str], bool] | None = None,
) -> SecretPattern:
    return SecretPattern(kind, re.compile(expression), confidence, keep, check)


_HEX = _entropy_at_least(MIN_HEX_ENTROPY)

VENDOR_PATTERNS: tuple[SecretPattern, ...] = (
    _pattern(
        "anthropic_api_key",
        r"\bsk-ant-(?:api|admin|sid)\d{2}-[A-Za-z0-9_-]{20,256}",
        0.99,
        7,
    ),
    _pattern(
        "openai_api_key",
        r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,256}",
        0.97,
        3,
        has_digit_and_letter,
    ),
    _pattern(
        "aws_access_key_id",
        r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ABIA|ACCA)[A-Z0-9]{16}\b",
        0.97,
        4,
    ),
    _pattern("github_token", r"\bgh[pousr]_[A-Za-z0-9]{36,255}\b", 0.99, 4),
    _pattern(
        "github_fine_grained_token", r"\bgithub_pat_[A-Za-z0-9_]{50,255}", 0.99, 11
    ),
    _pattern("gitlab_token", r"\bglpat-[A-Za-z0-9_-]{20,64}", 0.98, 6),
    _pattern("slack_token", r"\bxox[baprso]-[A-Za-z0-9-]{10,200}", 0.97, 5),
    _pattern(
        "slack_webhook",
        r"https://hooks\.slack\.com/services/T[A-Z0-9]{6,12}/B[A-Z0-9]{6,12}/[A-Za-z0-9]{20,30}",
        0.98,
    ),
    _pattern("google_api_key", r"\bAIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])", 0.97, 4),
    _pattern(
        "google_oauth_secret", r"\bGOCSPX-[A-Za-z0-9_-]{28}(?![0-9A-Za-z_-])", 0.98, 7
    ),
    _pattern(
        "stripe_secret_key", r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,99}\b", 0.97, 8
    ),
    _pattern(
        "sendgrid_api_key",
        r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}(?![0-9A-Za-z_-])",
        0.98,
        3,
    ),
    _pattern("twilio_api_key", r"\bSK[0-9a-f]{32}\b", 0.7, 2, _HEX),
    _pattern("mailgun_api_key", r"\bkey-[0-9a-f]{32}\b", 0.8, 4, _HEX),
    _pattern("npm_token", r"\bnpm_[A-Za-z0-9]{36}\b", 0.98, 4),
    _pattern("pypi_token", r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,500}", 0.99, 5),
    _pattern(
        "huggingface_token", r"\bhf_[A-Za-z0-9]{34,40}\b", 0.95, 3, has_digit_and_letter
    ),
    _pattern(
        "azure_storage_key",
        r"(?i)AccountKey=(?P<value>[A-Za-z0-9+/]{60,100}={0,2})",
        0.95,
    ),
)

CONTEXT_PATTERNS: tuple[SecretPattern, ...] = (
    _pattern(
        "jwt",
        r"\beyJ[A-Za-z0-9_-]{10,2000}\.eyJ[A-Za-z0-9_-]{10,4000}\.[A-Za-z0-9_-]{10,2000}",
        0.85,
        3,
    ),
    _pattern(
        "url_credentials",
        r"(?i)\b[a-z][a-z0-9+.-]{1,20}://[^\s/:@]{1,128}:(?P<value>[^\s/@]{3,256})@[^\s/]{1,255}",
        0.85,
    ),
    _pattern(
        "aws_secret_access_key",
        r"""(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key["']?\s{0,5}[:=]\s{0,5}["']?(?P<value>[A-Za-z0-9/+=]{40})(?![A-Za-z0-9/+=])""",
        0.9,
    ),
    _pattern(
        "bearer_credentials",
        r"""(?i)authorization["']?\s{0,5}[:=]\s{0,5}["']?(?:bearer|token|basic)\s{1,3}(?P<value>[A-Za-z0-9._~+/=-]{16,2048})""",
        0.75,
        0,
        _entropy_at_least(MIN_BEARER_ENTROPY),
    ),
    _pattern(
        "generic_secret",
        r"""(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|secret|token)["']?\s{0,5}[:=]\s{0,5}["']?(?P<value>[A-Za-z0-9_\-+/=.~]{16,128})""",
        0.6,
        0,
        _entropy_at_least(MIN_GENERIC_ENTROPY),
    ),
)

PRIVATE_KEY_HEADER = re.compile(
    r"-----BEGIN (?:[A-Z]{2,10} ){0,3}PRIVATE KEY(?: BLOCK)?-----"
)
PRIVATE_KEY_END = "-----END "
PRIVATE_KEY_MAX = 20_000

SUPPORTED_TYPES = (
    *(pattern.type for pattern in VENDOR_PATTERNS),
    "private_key",
    *(pattern.type for pattern in CONTEXT_PATTERNS),
)
