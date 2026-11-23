"""Whitespace cleaner: removes extra spaces, tabs and blank lines from text.

What it does:
    - Turns many spaces or tabs in a row into one space.
    - Removes spaces and tabs at the end of a line.
    - Turns many blank lines in a row into one blank line.
    - Keeps indentation and line endings as they are.

What it leaves alone:
    - Code (fenced blocks, `inline code`, indented code), table rows, HTML
      <pre>/<script>/<style>/<textarea> blocks and YAML front matter.
    - Text that is a JSON document.
    - Words, punctuation and special Unicode spaces. Only plain spaces, tabs and
      blank lines are ever removed, so the result is never longer than the input.

How to use it:
    from tokensguru.optimizers import WhitespaceCleaner

    cleaner = WhitespaceCleaner()
    cleaner.optimize("hello    world  ")      # "hello world"
    cleaner.report("hello    world  ").saved_chars

Options:
    max_blank_lines: how many blank lines to keep in a row (default 1).
    keep_markdown_line_breaks: keep the two spaces that make a Markdown line
        break (default False).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tokensguru.optimizers.utils import (
    BlockTracker,
    front_matter_length,
    is_json_document,
    split_line_ending,
    split_lines,
)

_EXTRA_WHITESPACE = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True)
class CleanupResult:
    text: str
    original_length: int

    @property
    def cleaned_length(self) -> int:
        return len(self.text)

    @property
    def saved_chars(self) -> int:
        return self.original_length - self.cleaned_length

    @property
    def saved_percent(self) -> float:
        if not self.original_length:
            return 0.0
        return round(100 * self.saved_chars / self.original_length, 2)

    @property
    def changed(self) -> bool:
        return self.saved_chars > 0


class WhitespaceCleaner:
    id = "prose_whitespace_cleanup"
    name = "Prose whitespace cleanup"
    applied_reason = (
        "Collapsed repeated spaces and blank lines and removed trailing "
        "whitespace in prose."
    )
    skipped_reason = "No safe change was found in eligible prose."

    def __init__(
        self, max_blank_lines: int = 1, keep_markdown_line_breaks: bool = False
    ) -> None:
        if isinstance(max_blank_lines, bool) or not isinstance(max_blank_lines, int):
            raise TypeError("max_blank_lines must be an int")
        if max_blank_lines < 0:
            raise ValueError("max_blank_lines must be 0 or more")
        self.max_blank_lines = max_blank_lines
        self.keep_markdown_line_breaks = keep_markdown_line_breaks

    def optimize(self, text: str, context: dict[str, object] | None = None) -> str:
        del context
        if not isinstance(text, str):
            raise TypeError(f"text must be a str, not {type(text).__name__}")
        if is_json_document(text):
            return text

        lines = split_lines(text)
        protected_lines = front_matter_length(lines)
        blocks = BlockTracker()
        output: list[str] = []
        blank_run = 0
        for index, line in enumerate(lines):
            body, ending = split_line_ending(line)
            if blocks.protects(body) or index < protected_lines:
                output.append(line)
                blank_run = 0
            elif not body.strip(" \t"):
                blank_run += 1
                if blank_run <= self.max_blank_lines:
                    output.append(ending)
            else:
                output.append(self._clean_line(body, lines, index) + ending)
                blank_run = 0
        return "".join(output)

    def report(self, text: str) -> CleanupResult:
        return CleanupResult(self.optimize(text), len(text))

    def _clean_line(self, body: str, lines: list[str], index: int) -> str:
        indent = body[: len(body) - len(body.lstrip(" \t"))]
        words = _EXTRA_WHITESPACE.sub(" ", body[len(indent) :].rstrip(" \t"))
        if self._is_hard_break(body, lines, index):
            words += "  "
        return indent + words

    def _is_hard_break(self, body: str, lines: list[str], index: int) -> bool:
        if not (self.keep_markdown_line_breaks and body.endswith("  ")):
            return False
        following = lines[index + 1 :]
        return bool(following) and bool(following[0].strip(" \t\r\n"))

    def __call__(self, text: str, context: dict[str, object] | None = None) -> str:
        return self.optimize(text, context)
