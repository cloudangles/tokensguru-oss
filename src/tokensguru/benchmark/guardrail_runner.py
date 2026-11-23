"""Scores a guardrail on its labelled examples: precision, recall and F1.

For every example the guardrail either reports something or not, and the label says
whether it should have. Counting right and wrong answers gives:

    precision   of everything it reported, how much was right
    recall      of everything it should have reported, how much it found
    f1          one number that balances the two

The report also lists the examples it got wrong, by position and a short label, so
the misses are visible instead of hidden inside an average.
"""

from __future__ import annotations

from typing import Any

from tokensguru.benchmark.guardrail_samples import LEAKAGE, SAMPLES
from tokensguru.governance.api_key_detection import ApiKeyDetector
from tokensguru.governance.base import Guardrail
from tokensguru.governance.email_detection import EmailDetector
from tokensguru.governance.models import DEFAULT_MODELS, enabled_and_saved
from tokensguru.governance.pii_detection import PiiDetector
from tokensguru.governance.pii_leakage_detection import PiiLeakageDetector
from tokensguru.governance.prompt_injection_detection import PromptInjectionDetector
from tokensguru.governance.toxicity_detection import ToxicityDetector

PREVIEW_CHARS = 60
DIGITS = 3
GUARDRAIL_KINDS: dict[str, type[Guardrail]] = {
    "email_detection": EmailDetector,
    "api_key_detection": ApiKeyDetector,
    "pii_detection": PiiDetector,
    "pii_leakage_detection": PiiLeakageDetector,
    "prompt_injection_detection": PromptInjectionDetector,
    "toxicity_detection": ToxicityDetector,
}
GUARDRAIL_BENCHMARK_IDS = tuple(GUARDRAIL_KINDS)


def _ratio(top: float, bottom: float) -> float:
    return round(top / bottom, DIGITS) if bottom else 0.0


def score(expected: list[bool], found: list[bool]) -> dict[str, Any]:
    pairs = list(zip(expected, found, strict=True))
    true_positive = sum(1 for want, got in pairs if want and got)
    false_positive = sum(1 for want, got in pairs if not want and got)
    false_negative = sum(1 for want, got in pairs if want and not got)
    true_negative = len(pairs) - true_positive - false_positive - false_negative
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    f1 = (
        _ratio(2 * precision * recall, precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "samples": len(pairs),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": _ratio(true_positive + true_negative, len(pairs)),
    }


def _examples(guardrail_id: str) -> list[tuple[str, bool, dict[str, object] | None]]:
    if guardrail_id == "pii_leakage_detection":
        return [(text, want, context) for text, want, context in LEAKAGE]
    return [(text, want, None) for text, want in SAMPLES[guardrail_id]]


def run_guardrail_benchmark(guardrail_id: str) -> dict[str, Any]:
    if guardrail_id not in GUARDRAIL_KINDS:
        raise KeyError(guardrail_id)
    model = DEFAULT_MODELS.get(guardrail_id)
    use_model = model is not None and enabled_and_saved(model[0])
    options: dict[str, Any] = {}
    if model is not None:
        options["backend"] = "auto" if use_model else None
    guardrail = GUARDRAIL_KINDS[guardrail_id](**options)
    expected: list[bool] = []
    found: list[bool] = []
    mistakes: list[dict[str, Any]] = []
    for number, (text, want, context) in enumerate(_examples(guardrail_id), start=1):
        got = guardrail.check(text, context).detected
        expected.append(want)
        found.append(got)
        if want != got:
            mistakes.append(
                {
                    "number": number,
                    "kind": "missed" if want else "false alarm",
                    "label": " ".join(text.split())[:PREVIEW_CHARS],
                }
            )
    return {
        "guardrail": guardrail_id,
        "model": model[0] if use_model and model else None,
        "summary": score(expected, found),
        "mistakes": mistakes,
    }
