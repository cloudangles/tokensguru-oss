"""Prepares text for detection so simple tricks do not hide what is in it.

People (and attackers) hide emails and keys by adding invisible characters inside
them or by typing full-width look-alike characters. fold() undoes both:

    - invisible characters (zero-width spaces and joiners, soft hyphens, byte-order
      marks) are removed
    - full-width letters, digits and symbols (the wide at sign and the wide full
      stop, for example) become the normal ASCII ones, and the ideographic full
      stops become "."

It remembers where every kept character came from, so a match found in the folded
text can be mapped back to the exact span in the original text.
"""

from __future__ import annotations

import re

_NEEDS_FOLDING = re.compile(
    r"[\u00ad\u200b-\u200f\u2060\ufeff\uff01-\uff5e\ufe6b\u3002\uff61]"
)
_INVISIBLE = frozenset(
    map(chr, (0x00AD, 0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF))
)
_SINGLE = {chr(0xFE6B): "@", chr(0x3002): ".", chr(0xFF61): "."}
_FULLWIDTH_FIRST = 0xFF01
_FULLWIDTH_LAST = 0xFF5E
_FULLWIDTH_SHIFT = 0xFEE0


class Folded:
    __slots__ = ("offsets", "text")

    def __init__(self, text: str, offsets: list[int] | None) -> None:
        self.text = text
        self.offsets = offsets

    def span(self, start: int, end: int) -> tuple[int, int]:
        if self.offsets is None:
            return start, end
        return self.offsets[start], self.offsets[end - 1] + 1


def _fold_char(char: str) -> str:
    code = ord(char)
    if _FULLWIDTH_FIRST <= code <= _FULLWIDTH_LAST:
        return chr(code - _FULLWIDTH_SHIFT)
    return _SINGLE.get(char, char)


def fold(text: str) -> Folded:
    if not _NEEDS_FOLDING.search(text):
        return Folded(text, None)
    kept: list[str] = []
    offsets: list[int] = []
    for index, char in enumerate(text):
        if char not in _INVISIBLE:
            kept.append(_fold_char(char))
            offsets.append(index)
    return Folded("".join(kept), offsets)
