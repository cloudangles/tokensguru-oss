"""Token counting utility.

Uses tiktoken (cl100k_base) for OpenAI/Anthropic/Groq/Together-routed models.
Falls back to a BPE-calibrated estimator (3.3 chars/token + CJK-aware) for
everything else -- adapted from Enterprise's api/utils/tokens.py, minus the
Bedrock-native CountTokens path (no Bedrock adapter in this OSS edition).
"""
from __future__ import annotations

import logging
from math import ceil

logger = logging.getLogger("tokensight.tokens")

_TIKTOKEN_PROVIDERS = frozenset({"openai", "anthropic", "groq", "together"})
_CODE_CHARS_PER_TOKEN = 3.3
_CJK_TOKENS_PER_CHAR = 1.0

_enc = None


def _get_enc():
    global _enc
    if _enc is None:
        try:
            import tiktoken
            _enc = tiktoken.get_encoding("cl100k_base")
        except Exception as exc:
            logger.warning("tiktoken unavailable, using BPE-calibrated fallback: %s", exc)
    return _enc


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x3040 <= o <= 0x30FF
        or 0x3400 <= o <= 0x4DBF
        or 0x4E00 <= o <= 0x9FFF
        or 0xAC00 <= o <= 0xD7A3
        or 0xF900 <= o <= 0xFAFF
        or 0xFF00 <= o <= 0xFFEF
        or 0x20000 <= o <= 0x2FA1F
    )


def _bpe_estimate(text: str) -> int:
    if text.isascii():
        return max(1, ceil(len(text) / _CODE_CHARS_PER_TOKEN))
    cjk = sum(1 for ch in text if _is_cjk(ch))
    other = len(text) - cjk
    return max(1, ceil(other / _CODE_CHARS_PER_TOKEN) + ceil(cjk * _CJK_TOKENS_PER_CHAR))


def estimate_tokens(text: str, provider: str = "openai") -> int:
    """Return token count for `text` given the target `provider`.

    Guarantees: at least 1 for any non-empty string; 0 for empty/None.
    """
    if not text:
        return 0
    if provider.lower() in _TIKTOKEN_PROVIDERS:
        enc = _get_enc()
        if enc is not None:
            return max(1, len(enc.encode(text, disallowed_special=())))
    return _bpe_estimate(text)


def estimate_content_tokens(content, provider: str = "openai") -> int:
    """Estimate tokens for str or Anthropic block-list message content."""
    if content is None:
        return 0
    if isinstance(content, str):
        return estimate_tokens(content, provider)
    if isinstance(content, list):
        total = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                total += estimate_tokens(str(block.get("text", "")), provider)
            elif btype == "image":
                total += 1000
        return total
    return estimate_tokens(str(content), provider)


def estimate_messages_tokens(messages, provider: str = "openai") -> int:
    """Sum estimated tokens across a chat/messages list."""
    if not messages:
        return 0
    return sum(
        estimate_content_tokens(m.get("content"), provider)
        for m in messages
        if isinstance(m, dict)
    )
