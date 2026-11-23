"""Bullet deduplicator: removes a bullet item that repeats the one right above it.

What it does:
    - Finds bullet lists (-, +, *, or the glyphs • ‣ ◦ ▪) and removes a bullet that
      is exactly the same as the bullet just above it. The first copy is kept.
    - "Exactly the same" means the same indentation, the same marker and the same
      text. Spaces and tabs at the end of the text are ignored.

When it keeps a repeated bullet on purpose (removing it could change the meaning):
    - The repeated bullet has sub-bullets, an indented follow-on line, or a plain
      line right under it that would continue it.
    - The bullet is in an indented code block (indented 4+ spaces, not inside a list).

What it leaves alone:
    - Bullets that are not next to each other, or have a blank line or any other
      line between them.
    - Bullets that differ in text, indentation or marker. Numbered lists, bullets
      inside quotes ("> - a") and lines like "- - -" (horizontal rules).
    - Fenced code, HTML <pre>/<script>/<style>/<textarea> blocks and YAML front
      matter.
    - Line endings, and every other line. Lines are only ever removed, so the
      result is never longer than the input, and running it twice changes nothing.

How to use it:
    from tokensguru.optimizers import BulletDeduplicator

    result = BulletDeduplicator().optimize("- a\\n- a\\n- b\\n")
    result.optimized_text        # "- a\\n- b\\n"
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    print(result)                # id, tokens, characters, reason and more
"""

from __future__ import annotations

import re

from tokensguru.optimizers.base import Optimizer
from tokensguru.optimizers.utils import (
    BlockTracker,
    front_matter_length,
    split_line_ending,
    split_lines,
)
from tokensguru.utils.validation import require_text

_MARKERS = "-+*•‣◦▪"
_BULLET = re.compile(
    rf"^(?P<indent>[ \t]*)(?P<marker>[{_MARKERS}])[ \t]+(?P<item>\S.*)$"
)
_LIST_ITEM = re.compile(rf"^[ \t]*(?:[{_MARKERS}]|\d{{1,9}}[.)])[ \t]+\S")
_ENDS_ITEM = re.compile(
    r"^ {0,3}(?:#{1,6}(?:[ \t]|$)|>|`{3,}|~{3,}|(?:[-*_][ \t]*){3,}$)"
)
_RULE_CHARACTERS = set("-+*_ \t")
_TAB_WIDTH = 4
_CODE_INDENT = 4


class BulletDeduplicator(Optimizer):
    id = "exact_bullet_item_deduplication"
    name = "Exact repeated bullet cleanup"
    applied_reason = (
        "Removed an adjacent, exact duplicate Markdown bullet item; "
        "the first copy was preserved."
    )
    skipped_reason = "No adjacent exact duplicate bullet item was found."

    def transform(self, text: str, context: dict[str, object] | None = None) -> str:
        del context
        require_text(text)

        lines = split_lines(text)
        protected_lines = front_matter_length(lines)
        blocks = BlockTracker()
        output: list[str] = []
        previous: tuple[str, str, str] | None = None
        list_open = False
        for index, line in enumerate(lines):
            body, ending = split_line_ending(line)
            if index < protected_lines or blocks.in_block(body):
                output.append(line)
                previous = None
                list_open = False
                continue

            width = _indent_width(body)
            key = _bullet_key(body)
            if key is not None and width >= _CODE_INDENT and not list_open:
                key = None
            list_open = _list_still_open(body, width, list_open)

            following = lines[index + 1] if index + 1 < len(lines) else None
            if key is None:
                output.append(line)
                previous = None
            elif key == previous and not _continues_item(following, width):
                if not ending:
                    output[-1] = split_line_ending(output[-1])[0]
            else:
                output.append(line)
                previous = key
        return "".join(output)


def _indent_width(body: str) -> int:
    indent = body[: len(body) - len(body.lstrip(" \t"))]
    return len(indent.replace("\t", " " * _TAB_WIDTH))


def _list_still_open(body: str, width: int, was_open: bool) -> bool:
    if _LIST_ITEM.match(body):
        return width < _CODE_INDENT or was_open
    if body.strip(" \t") and width == 0:
        return False
    return was_open


def _continues_item(following: str | None, width: int) -> bool:
    if following is None:
        return False
    body = split_line_ending(following)[0]
    if not body.strip(" \t") or _ENDS_ITEM.match(body):
        return False
    if _LIST_ITEM.match(body):
        return _indent_width(body) > width
    return True


def _bullet_key(body: str) -> tuple[str, str, str] | None:
    match = _BULLET.match(body)
    if match is None:
        return None
    item = match.group("item").rstrip(" \t")
    if set(item) <= _RULE_CHARACTERS:
        return None
    return match.group("indent"), match.group("marker"), item
