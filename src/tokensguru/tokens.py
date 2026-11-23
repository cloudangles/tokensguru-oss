"""Token counter: tells you how many tokens a piece of text uses.

You do not need this to use the optimizers. Every optimizer already counts the
tokens before and after and puts the numbers in its result. Use TokenCounter on
its own only if you want to count some text yourself.

It wraps tiktoken (OpenAI's tokenizer), which is installed with tokensguru. The
first count downloads the tokenizer's vocabulary file once, so it needs the
internet the first time and is a few seconds slower. After that it is cached.

How to use it:
    from tokensguru import TokenCounter

    counter = TokenCounter()                 # default tokenizer: o200k_base
    counter.count("hello world")             # 2

    TokenCounter(model="gpt-4")              # pick the tokenizer by model name
    TokenCounter(encoding="cl100k_base")     # or by tokenizer name

Special words such as "<|endoftext|>" are counted as normal text, never as
control tokens, so any text is safe to count. Counts are exact for OpenAI models
and a close estimate for other models.
"""

from __future__ import annotations

from functools import cache
from importlib import import_module
from typing import Any

from tokensguru.utils.validation import require_text

DEFAULT_ENCODING = "o200k_base"


@cache
def _load_encoder(encoding: str, model: str | None) -> Any:
    tiktoken = import_module("tiktoken")
    if model is not None:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError as error:
            raise ValueError(f"Unknown model: {model!r}") from error
    try:
        return tiktoken.get_encoding(encoding)
    except ValueError as error:
        raise ValueError(f"Unknown encoding: {encoding!r}") from error


class TokenCounter:
    def __init__(
        self, encoding: str = DEFAULT_ENCODING, model: str | None = None
    ) -> None:
        self.encoding = encoding
        self.model = model

    @property
    def name(self) -> str:
        return self.model or self.encoding

    def count(self, text: str) -> int:
        require_text(text)
        if not text:
            return 0
        encoder = _load_encoder(self.encoding, self.model)
        return len(encoder.encode_ordinary(text))


@cache
def default_counter() -> TokenCounter:
    return TokenCounter()
