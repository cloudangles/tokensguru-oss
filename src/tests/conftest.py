import os
import re

import pytest

from tokensguru import tokens

os.environ["TOKENSGURU_MODELS"] = "off"


class WordEncoding:
    def encode_ordinary(self, text):
        return text.split()


class WhitespaceAwareEncoding:
    def encode_ordinary(self, text):
        tokens_found = []
        for piece in re.findall(r"\s+|\w+|[^\w\s]", text):
            count = max(1, len(piece) // 4) if piece.isspace() else 1
            tokens_found.extend([piece] * count)
        return tokens_found


@pytest.fixture
def whitespace_tokens(monkeypatch):
    monkeypatch.setattr(
        tokens, "_load_encoder", lambda encoding, model: WhitespaceAwareEncoding()
    )


@pytest.fixture(autouse=True)
def offline_tokenizer(request, monkeypatch):
    if "fake_tiktoken" in request.fixturenames or "real_tiktoken" in request.node.name:
        return
    monkeypatch.setattr(tokens, "_load_encoder", lambda encoding, model: WordEncoding())


@pytest.fixture(autouse=True)
def models_off(monkeypatch):
    monkeypatch.setenv("TOKENSGURU_MODELS", "off")
