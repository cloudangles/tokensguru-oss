"""Finds the text inside a chat messages list, so guardrails can check whole chats.

A messages list looks like:

    [{"role": "system", "content": "Be brief."},
     {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
     {"role": "assistant", "tool_calls": [{"function": {"arguments": "{...}"}}]}]

The text can be a plain content string, the text parts of a content list, or the
JSON arguments of a tool call. Images and other non-text parts are skipped. Each
piece of text has a path such as messages[1].content[0].text, so a finding can say
exactly where it was found.

Messages that are not dictionaries are skipped. The list you pass in is never
changed. To rewrite text (for redaction) use rewrite_texts(), which works on a copy.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

TEXT = "text"
JSON = "json"
_TEXT_PART_KEYS = ("text",)


@dataclass(frozen=True)
class TextSlot:
    path: str
    role: str | None
    kind: str
    text: str
    container: Any
    key: Any


def iter_slots(messages: list[Any]) -> Iterator[TextSlot]:
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        role = message.get("role") if isinstance(message.get("role"), str) else None
        base = f"messages[{index}]"
        yield from _content_slots(message, base, role)
        yield from _tool_call_slots(message, base, role)


def _content_slots(
    message: dict[str, Any], base: str, role: str | None
) -> Iterator[TextSlot]:
    content = message.get("content")
    if isinstance(content, str):
        yield TextSlot(f"{base}.content", role, TEXT, content, message, "content")
    elif isinstance(content, list):
        for part_index, part in enumerate(content):
            if not isinstance(part, dict):
                continue
            for key in _TEXT_PART_KEYS:
                if isinstance(part.get(key), str):
                    path = f"{base}.content[{part_index}].{key}"
                    yield TextSlot(path, role, TEXT, part[key], part, key)


def _tool_call_slots(
    message: dict[str, Any], base: str, role: str | None
) -> Iterator[TextSlot]:
    calls = message.get("tool_calls")
    if isinstance(calls, list):
        for call_index, call in enumerate(calls):
            function = call.get("function") if isinstance(call, dict) else None
            if isinstance(function, dict) and isinstance(
                function.get("arguments"), str
            ):
                path = f"{base}.tool_calls[{call_index}].function.arguments"
                yield TextSlot(
                    path, role, JSON, function["arguments"], function, "arguments"
                )
    legacy = message.get("function_call")
    if isinstance(legacy, dict) and isinstance(legacy.get("arguments"), str):
        path = f"{base}.function_call.arguments"
        yield TextSlot(path, role, JSON, legacy["arguments"], legacy, "arguments")


def rewrite_texts(messages: list[Any], rewrite: Callable[[TextSlot], str]) -> list[Any]:
    copied = copy.deepcopy(messages)
    for slot in list(iter_slots(copied)):
        slot.container[slot.key] = rewrite(slot)
    return copied
