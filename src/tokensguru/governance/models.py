"""The models the guardrails use by themselves, so you do not set anything up.

Prompt injection detection and toxicity detection are much more accurate with a
trained model than with rules alone, so tokensguru installs the libraries it needs
and uses a model for each of them automatically:

    toxicity_detection          unitary/toxic-bert                                  (Apache 2.0)
    prompt_injection_detection  protectai/deberta-v3-base-prompt-injection-v2      (Apache 2.0)

How it works:
    - A model is downloaded the first time a guardrail needs it, about a few hundred
      megabytes, and kept in the Hugging Face cache on your machine. Later runs use
      the saved copy and work offline. A package install cannot fetch it earlier
      than that, so to get it ahead of time run:  tokensguru models download
    - It then runs on your computer. Your text is never sent anywhere.
    - The built-in rules always run too. If the model cannot be loaded (no internet
      on the first run, not enough memory) the guardrail keeps working with the rules
      alone, and detector.backend.error says why.
    - To turn models off for a guardrail pass backend=None. To turn them off for
      everything set the environment variable TOKENSGURU_MODELS=off.
    - To use another model pass backend=HuggingFaceClassifier("model/name").

tokensguru models status    shows which models are saved on this machine
tokensguru models download  saves them now
"""

# ruff: noqa: E501
from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable
from typing import Any

from tokensguru.governance.backends import HuggingFaceClassifier, TextClassifier
from tokensguru.governance.base import Finding

ENV_SWITCH = "TOKENSGURU_MODELS"
OFF_VALUES = frozenset({"off", "0", "false", "no", "none"})
DEFAULT_MODELS: dict[str, tuple[str, str | None]] = {
    "toxicity_detection": ("unitary/toxic-bert", "sigmoid"),
    "prompt_injection_detection": (
        "protectai/deberta-v3-base-prompt-injection-v2",
        None,
    ),
}
_lock = threading.Lock()
_shared: dict[str, AutoClassifier] = {}


def models_enabled() -> bool:
    return os.environ.get(ENV_SWITCH, "").strip().lower() not in OFF_VALUES


def _say(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


class AutoClassifier:
    def __init__(self, guardrail_id: str) -> None:
        model_id, function = DEFAULT_MODELS[guardrail_id]
        self.name = model_id
        self.error: str | None = None
        self._inner = HuggingFaceClassifier(model_id, function_to_apply=function)
        self._loaded = False
        self._failed = False
        self._lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._loaded

    def load(self) -> bool:
        with self._lock:
            if self._loaded:
                return True
            if self._failed:
                return False
            try:
                _say(
                    f"tokensguru: loading model {self.name} (the first time it is downloaded)..."
                )
                self._inner._load()
            except Exception as error:
                self._failed = True
                self.error = f"{type(error).__name__}: {error}"[:300]
                _say(
                    f"tokensguru: model {self.name} is not available, using the rules only. {self.error}"
                )
                return False
            self._loaded = True
            return True

    def score_spans(
        self, text: str, keep: Callable[[int, int, str], bool] | None = None
    ) -> list[tuple[int, int, dict[str, float]]]:
        if not self.load():
            return []
        try:
            return self._inner.score_spans(text, keep)
        except Exception as error:
            self.error = f"{type(error).__name__}: {error}"[:300]
            return []

    def scores(self, text: str) -> dict[str, float]:
        if not self.load():
            return {}
        try:
            return self._inner.scores(text)
        except Exception as error:
            self.error = f"{type(error).__name__}: {error}"[:300]
            return {}


def shared_classifier(guardrail_id: str) -> AutoClassifier:
    with _lock:
        if guardrail_id not in _shared:
            _shared[guardrail_id] = AutoClassifier(guardrail_id)
        return _shared[guardrail_id]


def resolve_backend(backend: Any, guardrail_id: str) -> TextClassifier | None:
    if backend == "auto":
        return shared_classifier(guardrail_id) if models_enabled() else None
    return backend  # type: ignore[no-any-return]


def is_saved(model_id: str) -> bool:
    try:
        from huggingface_hub import try_to_load_from_cache  # noqa: PLC0415

        return isinstance(try_to_load_from_cache(model_id, "config.json"), str)
    except Exception:
        return False


def enabled_and_saved(model_id: str) -> bool:
    return models_enabled() and is_saved(model_id)


def status() -> list[dict[str, object]]:
    return [
        {"guardrail": guardrail, "model": model_id, "saved": is_saved(model_id)}
        for guardrail, (model_id, _) in DEFAULT_MODELS.items()
    ]


def download() -> list[dict[str, object]]:
    results = []
    for guardrail in DEFAULT_MODELS:
        classifier = AutoClassifier(guardrail)
        ok = classifier.load()
        results.append(
            {
                "guardrail": guardrail,
                "model": classifier.name,
                "saved": ok,
                "error": classifier.error,
            }
        )
    return results


def model_hits(  # noqa: PLR0913, PLR0917
    backend: TextClassifier,
    text: str,
    covered: list[Finding],
    kind_of: Callable[[str], str | None],
    threshold: float,
    worth_checking: Callable[[str], bool] | None = None,
) -> list[tuple[int, int, str, float]]:
    def keep(start: int, end: int, piece: str) -> bool:
        if any(f.start < end and start < f.end for f in covered):
            return False
        return worth_checking is None or worth_checking(piece)

    spans_of = getattr(backend, "score_spans", None)
    spans = (
        spans_of(text, keep)
        if spans_of is not None
        else [(0, len(text), backend.scores(text))]
    )
    hits = []
    for start, end, scores in spans:
        best: tuple[str, float] | None = None
        for label, score in scores.items():
            kind = kind_of(label)
            if kind and score >= threshold and (best is None or score > best[1]):
                best = (kind, score)
        if best:
            hits.append((start, end, best[0], best[1]))
    return hits
