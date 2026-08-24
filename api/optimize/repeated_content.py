"""Repeated-content collapse -- the one optimization stage in TokenSight OSS.

If the same line repeats 3+ times consecutively in a prompt (a common
accident: pasted logs, repeated boilerplate, a copy-paste mistake), keep one
copy and replace the redundant repeats with an explicit, honest marker
stating how many were removed. The model still sees the content in full at
least once -- this never changes meaning, only removes exact duplication.

This is a fresh, standalone implementation, not a copy of Enterprise's
_collapse_repeated_phrases (which is tightly coupled to its own pipeline's
message-mutation machinery) -- see docs/OSS_FEATURE_MATRIX.md for context on
why Enterprise's optimization stages aren't ported to OSS wholesale.

Safety: fenced code blocks (``` ... ```) are never touched -- repeated lines
inside code (e.g. a loop body, a table of test fixtures) are often
intentional, and OSS makes no attempt to distinguish "meaningful repeat"
from "redundant repeat" inside code the way it safely can for prose.
"""
from __future__ import annotations

import re

from tokens import estimate_tokens

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_MIN_REPEATS = 3


def _extract_fenced_code(text: str) -> tuple[str, list[str]]:
    """Replace fenced code blocks with placeholders; return (text, blocks)."""
    blocks: list[str] = []

    def _replace(match: re.Match) -> str:
        blocks.append(match.group(0))
        return f"\x00FENCE{len(blocks) - 1}\x00"

    return _FENCE_RE.sub(_replace, text), blocks


def _restore_fenced_code(text: str, blocks: list[str]) -> str:
    for i, block in enumerate(blocks):
        text = text.replace(f"\x00FENCE{i}\x00", block)
    return text


def _collapse_adjacent_repeated_lines(text: str, min_repeats: int) -> tuple[str, int]:
    lines = text.split("\n")
    out: list[str] = []
    saved_tokens = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == "":
            out.append(line)
            i += 1
            continue
        j = i + 1
        while j < n and lines[j] == line:
            j += 1
        run_length = j - i
        if run_length >= min_repeats:
            out.append(line)
            removed = run_length - 1
            out.append(f"[... previous line repeated {removed} more time(s), omitted ...]")
            saved_tokens += estimate_tokens(line) * removed
        else:
            out.extend(lines[i:j])
        i = j
    return "\n".join(out), saved_tokens


def collapse_repeated_content(
    text: str, *, min_repeats: int = _MIN_REPEATS,
) -> tuple[str, int]:
    """Collapse lines repeated >= min_repeats times consecutively.

    Returns (possibly-shorter text, estimated tokens saved). Fenced code
    blocks are protected from collapsing. Safe to call on any string,
    including one with no repetition (returns it unchanged, 0 saved).
    """
    if not text or min_repeats < 2:
        return text, 0
    protected, blocks = _extract_fenced_code(text)
    collapsed, saved = _collapse_adjacent_repeated_lines(protected, min_repeats)
    return _restore_fenced_code(collapsed, blocks), saved
