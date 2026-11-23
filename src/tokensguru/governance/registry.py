"""The list of built-in guardrails. Add a new guardrail here and it shows up in the
default GuardrailPipeline without any other change.

GUARDRAILS lists every guardrail. DEFAULT_PIPELINE is the set GuardrailPipeline runs
when you choose none; it leaves out the email detector (PII detection already finds
emails), the redactor and the leak check, which need their own options or context.
They run in the order listed. Secrets come first because they are the most serious.
"""

from __future__ import annotations

from tokensguru.governance.api_key_detection import ApiKeyDetector
from tokensguru.governance.base import Guardrail
from tokensguru.governance.email_detection import EmailDetector
from tokensguru.governance.pii_detection import PiiDetector
from tokensguru.governance.pii_leakage_detection import PiiLeakageDetector
from tokensguru.governance.pii_redaction import PiiRedactor
from tokensguru.governance.prompt_injection_detection import PromptInjectionDetector
from tokensguru.governance.toxicity_detection import ToxicityDetector

GUARDRAILS: tuple[type[Guardrail], ...] = (
    ApiKeyDetector,
    EmailDetector,
    PiiDetector,
    PiiRedactor,
    PiiLeakageDetector,
    PromptInjectionDetector,
    ToxicityDetector,
)
DEFAULT_PIPELINE: tuple[type[Guardrail], ...] = (
    ApiKeyDetector,
    PiiDetector,
    PromptInjectionDetector,
    ToxicityDetector,
)


def default_guardrails() -> tuple[Guardrail, ...]:
    return tuple(guardrail() for guardrail in DEFAULT_PIPELINE)
