"""Plug-in models for the guardrails that need a language model.

The prompt injection and toxicity detectors use a trained model automatically (see
models.py). This file holds the pieces behind that, and lets you plug in a different
model of your own. A classifier is anything with a name and a
scores(text) method that returns a probability for each label:

    classifier.scores("some text")      # {"toxic": 0.93, "insult": 0.12, ...}

HuggingFaceClassifier wraps a Hugging Face model. The libraries it needs are installed
with tokensguru:

    pip install --upgrade tokensguru

and downloads the model the first time it is used, so that first call needs the
internet and takes a while. Nothing is downloaded or imported until you use it.
Long text is split into overlapping pieces, and each label keeps its highest score.

    from tokensguru.governance import HuggingFaceClassifier, ToxicityDetector

    classifier = HuggingFaceClassifier(
        "unitary/toxic-bert", function_to_apply="sigmoid"
    )
    detector = ToxicityDetector(backend=classifier)

Check each model's license before you use it. The package does not include any model.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from importlib import import_module
from typing import Any, Protocol

ML_HINT = (
    "The model libraries are missing. Install it with: pip install --upgrade tokensguru"
)
DEFAULT_CHUNK_CHARS = 2000
DEFAULT_OVERLAP_CHARS = 200
SEGMENT_CHARS = 500
SEGMENT_MAX_TOKENS = 256
BATCH_SIZE = 16
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


class TextClassifier(Protocol):
    name: str

    def scores(self, text: str) -> dict[str, float]: ...


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    step = max(size - overlap, 1)
    return [text[start : start + size] for start in range(0, len(text), step)]


def split_segments(text: str, size: int = SEGMENT_CHARS) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in [*_SENTENCE_END.finditer(text), None]:
        end = match.start() if match else len(text)
        piece = text[start:end]
        stripped = piece.strip()
        if stripped:
            first = start + len(piece) - len(piece.lstrip())
            last = first + len(stripped)
            for offset in range(first, last, size):
                spans.append((offset, min(offset + size, last)))
        if match:
            start = match.end()
    return spans


def _flatten(output: Any) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for item in output if isinstance(output, list) else [output]:
        if isinstance(item, list):
            flat.extend(_flatten(item))
        elif isinstance(item, dict):
            flat.append(item)
    return flat


class HuggingFaceClassifier:
    def __init__(
        self,
        model_id: str,
        *,
        function_to_apply: str | None = None,
        max_chars: int = DEFAULT_CHUNK_CHARS,
        overlap: int = DEFAULT_OVERLAP_CHARS,
        pipeline: Callable[..., Any] | None = None,
    ) -> None:
        if max_chars < 1 or overlap < 0 or overlap >= max_chars:
            raise ValueError("max_chars must be positive and overlap smaller than it")
        self.name = model_id
        self.function_to_apply = function_to_apply
        self.max_chars = max_chars
        self.overlap = overlap
        self._pipeline = pipeline

    def _load(self) -> Callable[..., Any]:
        if self._pipeline is None:
            try:
                transformers = import_module("transformers")
            except ImportError as error:
                raise ImportError(ML_HINT) from error
            self._pipeline = transformers.pipeline(
                "text-classification", model=self.name
            )
        return self._pipeline

    def score_spans(
        self, text: str, keep: Callable[[int, int, str], bool] | None = None
    ) -> list[tuple[int, int, dict[str, float]]]:
        classify = self._load()
        options: dict[str, Any] = {
            "top_k": None,
            "truncation": True,
            "max_length": SEGMENT_MAX_TOKENS,
            "batch_size": BATCH_SIZE,
        }
        if self.function_to_apply:
            options["function_to_apply"] = self.function_to_apply
        spans = [
            (a, z)
            for a, z in split_segments(text)
            if keep is None or keep(a, z, text[a:z])
        ]
        if not spans:
            return []
        outputs = classify([text[a:b] for a, b in spans], **options)
        result = []
        for (start, end), output in zip(spans, outputs, strict=True):
            best: dict[str, float] = {}
            for entry in _flatten(output):
                label = str(entry["label"]).lower()
                best[label] = max(best.get(label, 0.0), float(entry["score"]))
            result.append((start, end, best))
        return result

    def scores(self, text: str) -> dict[str, float]:
        classify = self._load()
        options: dict[str, Any] = {
            "top_k": None,
            "truncation": True,
            "max_length": SEGMENT_MAX_TOKENS,
        }
        if self.function_to_apply:
            options["function_to_apply"] = self.function_to_apply
        best: dict[str, float] = {}
        for piece in chunk_text(text, self.max_chars, self.overlap):
            for entry in _flatten(classify(piece, **options)):
                label = str(entry["label"]).lower()
                best[label] = max(best.get(label, 0.0), float(entry["score"]))
        return best
