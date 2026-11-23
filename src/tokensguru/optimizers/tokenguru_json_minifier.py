"""JSON minifier: removes the spaces, tabs and line breaks around JSON values.

What it does:
    - If the whole text is one valid JSON document (an object, an array, or a
      single value), it removes the whitespace that is only there for looks:
      indentation, line breaks and spaces after "," and ":".
    - It removes whitespace and nothing else. Strings, numbers, key order, escapes
      like \\u0061 and number formats like 1.00 or 1e5 are kept exactly as written,
      so the parsed data is identical.

What it leaves alone (returns the text unchanged):
    - Text that is not one complete, valid JSON document: plain text, JSON with
      comments or trailing commas, several JSON documents in one text, text with a
      byte-order mark, and the non-standard values NaN, Infinity and -Infinity.
    - JSON that is already compact.
    - Whitespace inside strings.

How to use it:
    from tokensguru.optimizers import JsonMinifier

    result = JsonMinifier().optimize('{\\n  "a": 1,\\n  "b": [1, 2]\\n}')
    result.optimized_text        # '{"a":1,"b":[1,2]}'
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    print(result)                # id, tokens, characters, reason and more

Lines of text that merely contain JSON are not touched. Pass the JSON by itself.
"""

from __future__ import annotations

import json
import re

from tokensguru.optimizers.base import Optimizer
from tokensguru.utils.validation import require_text

_STRING_OR_WHITESPACE = re.compile(r'("[^"\\]*(?:\\.[^"\\]*)*")|[ \t\r\n]+')


def _reject_constant(name: str) -> None:
    raise ValueError(f"nonstandard JSON constant: {name}")


def _is_json_document(text: str) -> bool:
    try:
        json.loads(
            text, parse_constant=_reject_constant, parse_int=str, parse_float=str
        )
    except (ValueError, RecursionError):
        return False
    return True


class JsonMinifier(Optimizer):
    id = "tokenguru_json_minifier"
    name = "JSON minifier"
    applied_reason = (
        "Removed JSON formatting whitespace without changing any value, "
        "key order or number."
    )
    skipped_reason = (
        "The input is not one complete JSON document, or it is already compact."
    )

    def transform(self, text: str, context: dict[str, object] | None = None) -> str:
        del context
        require_text(text)
        if not _is_json_document(text):
            return text
        compact = _STRING_OR_WHITESPACE.sub(lambda m: m.group(1) or "", text)
        return compact if len(compact) < len(text) else text
