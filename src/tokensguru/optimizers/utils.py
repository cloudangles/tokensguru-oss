"""Small helpers shared by the text optimizers: split text into lines, spot JSON,
front matter and code blocks that must not be touched."""

from __future__ import annotations

import json
import re

_LINES = re.compile(r"[^\r\n]*(?:\r\n|\n|\r)|[^\r\n]+")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
_RAW_HTML_OPEN = re.compile(r"<(pre|script|style|textarea)\b", re.IGNORECASE)
_FRONT_MATTER_FENCES = ("---", "...")


def split_lines(text: str) -> list[str]:
    return _LINES.findall(text)


def split_line_ending(line: str) -> tuple[str, str]:
    for ending in ("\r\n", "\n", "\r"):
        if line.endswith(ending):
            return line[: -len(ending)], ending
    return line, ""


def is_json_document(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return False
    try:
        json.loads(stripped)
    except ValueError:
        return False
    return True


def front_matter_length(lines: list[str]) -> int:
    if not lines or split_line_ending(lines[0])[0].lstrip("﻿") != "---":
        return 0
    for index in range(1, len(lines)):
        if split_line_ending(lines[index])[0].rstrip() in _FRONT_MATTER_FENCES:
            return index + 1
    return 0


class BlockTracker:
    def __init__(self) -> None:
        self._fence: tuple[str, int] | None = None
        self._raw_tag: str | None = None

    def protects(self, line: str) -> bool:
        if self.in_block(line):
            return True
        return bool(line.strip(" \t")) and _is_code_or_table_line(line)

    def in_block(self, line: str) -> bool:
        if self._fence is not None:
            self._close_fence(line)
            return True
        if self._raw_tag is not None:
            if f"</{self._raw_tag}" in line.lower():
                self._raw_tag = None
            return True
        if not line.strip(" \t"):
            return False
        return self._opens_block(line)

    def _close_fence(self, line: str) -> None:
        match = _FENCE_CLOSE.match(line)
        if match and self._fence:
            marker = match.group(1)
            if marker[0] == self._fence[0] and len(marker) >= self._fence[1]:
                self._fence = None

    def _opens_block(self, line: str) -> bool:
        fence = _FENCE_OPEN.match(line)
        if fence:
            marker, info = fence.groups()
            if not (marker[0] == "`" and "`" in info):
                self._fence = (marker[0], len(marker))
                return True
        raw = _RAW_HTML_OPEN.search(line)
        if raw:
            tag = raw.group(1).lower()
            if f"</{tag}" not in line[raw.end() :].lower():
                self._raw_tag = tag
            return True
        return False


def _is_code_or_table_line(line: str) -> bool:
    return (
        "`" in line
        or line.startswith(("    ", "\t"))
        or line.lstrip(" \t").startswith("|")
    )
