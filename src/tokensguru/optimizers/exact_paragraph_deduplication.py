"""Paragraph deduplicator: removes a paragraph that already appeared earlier.

A paragraph is a group of lines with blank lines (or only spaces) before and after.

What it does:
    - Finds paragraphs that are exactly the same as an earlier paragraph and removes
      the later copies. The first copy is kept.
    - "Exactly the same" means the same text. Spaces around the paragraph and the
      type of line ending do not matter.
    - It removes the duplicate and the blank lines after it, so the spacing of the
      rest of the text stays as it was.

Options:
    min_length: paragraphs shorter than this many characters are never removed
        (default 40). Short repeats like "Thank you." or "Customer:" usually carry
        meaning at each position. Use 0 to remove repeats of any length.
    adjacent_only: only remove a paragraph that repeats the paragraph right above
        it (default False, which removes repeats anywhere in the text).

What it never removes, even when repeated (the meaning depends on where it is):
    - Headings, horizontal rules, tables, lists, quotes, indented code, HTML,
      link definitions, and paragraphs with no letters or digits.
    - A paragraph that ends with ":" (it introduces what comes next).
    - Fenced code, HTML <pre>/<script>/<style>/<textarea> blocks and YAML front
      matter. These also split text into separate runs of paragraphs.
    - Every other line. Lines are only ever removed, so the result is never longer
      than the input, every distinct line still appears at least once, and running
      it twice changes nothing.

How to use it:
    from tokensguru.optimizers import ParagraphDeduplicator

    result = ParagraphDeduplicator().optimize(text)
    result.optimized_text
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    print(result)                # id, tokens, characters, reason and more
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tokensguru.optimizers.base import Optimizer
from tokensguru.optimizers.utils import (
    BlockTracker,
    front_matter_length,
    split_line_ending,
    split_lines,
)
from tokensguru.tokens import TokenCounter
from tokensguru.utils.validation import require_text

_STRUCTURE = re.compile(
    r"""^(?:
        [ ]{0,3}\#{1,6}(?:[ \t]|$)
      | [ ]{0,3}(?:=+|-+|(?:[-*_][ \t]*){3,})[ \t]*$
      | [ \t]*\|
      | [ \t]*:?-+:?(?:[ \t]*\|[ \t]*:?-+:?)+[ \t]*\|?[ \t]*$
      | [ \t]*(?:>|(?:[-+*•‣◦▪]|\d{1,9}[.)])(?:[ \t]|$))
      | [ ]{0,3}\[[^\]]+\]:
      | [ ]{0,3}<
      | [ ]{4}
      | \t
    )""",
    re.VERBOSE,
)
_HAS_LETTER_OR_DIGIT = re.compile(r"\w")
_LEAD_IN_ENDINGS = (":", "\N{FULLWIDTH COLON}")


@dataclass
class _Element:
    kind: str
    lines: list[str] = field(default_factory=list)


class ParagraphDeduplicator(Optimizer):
    id = "exact_paragraph_deduplication"
    name = "Exact paragraph deduplication"
    applied_reason = "Removed exact repeated paragraphs; the first copy was preserved."
    skipped_reason = "No exact repeated paragraph was found in eligible prose."

    def __init__(
        self,
        min_length: int = 40,
        adjacent_only: bool = False,
        counter: TokenCounter | None = None,
    ) -> None:
        super().__init__(counter)
        if isinstance(min_length, bool) or not isinstance(min_length, int):
            raise TypeError("min_length must be an int")
        if min_length < 0:
            raise ValueError("min_length must be 0 or more")
        self.min_length = min_length
        self.adjacent_only = adjacent_only

    def transform(self, text: str, context: dict[str, object] | None = None) -> str:
        del context
        require_text(text)

        elements = _split_elements(split_lines(text))
        output: list[_Element] = []
        seen: set[str] = set()
        previous_key: str | None = None
        lost_final_ending = False
        position = 0
        while position < len(elements):
            element = elements[position]
            position += 1
            if element.kind != "text":
                previous_key = None if element.kind == "protected" else previous_key
                output.append(element)
                continue

            key = self._key(element.lines)
            repeated = key is not None and (
                key == previous_key if self.adjacent_only else key in seen
            )
            if not repeated:
                if key is not None:
                    seen.add(key)
                previous_key = key
                output.append(element)
                continue

            if position < len(elements) and elements[position].kind == "blank":
                position += 1
            elif position == len(elements):
                if output and output[-1].kind == "blank":
                    output.pop()
                lost_final_ending = not split_line_ending(element.lines[-1])[1]

        lines = [line for element in output for line in element.lines]
        if lost_final_ending and lines:
            lines[-1] = split_line_ending(lines[-1])[0]
        return "".join(lines)

    def _key(self, lines: list[str]) -> str | None:
        bodies = [split_line_ending(line)[0] for line in lines]
        if any(_STRUCTURE.match(body) for body in bodies):
            return None
        key = "\n".join(bodies).strip()
        if len(key) < self.min_length or not _HAS_LETTER_OR_DIGIT.search(key):
            return None
        if key.endswith(_LEAD_IN_ENDINGS):
            return None
        return key


def _split_elements(lines: list[str]) -> list[_Element]:
    protected_lines = front_matter_length(lines)
    blocks = BlockTracker()
    elements: list[_Element] = []
    for index, line in enumerate(lines):
        body = split_line_ending(line)[0]
        if index < protected_lines or blocks.in_block(body):
            kind = "protected"
        elif not body.strip(" \t"):
            kind = "blank"
        else:
            kind = "text"
        if elements and elements[-1].kind == kind:
            elements[-1].lines.append(line)
        else:
            elements.append(_Element(kind, [line]))
    return elements
