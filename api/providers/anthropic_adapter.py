"""Anthropic provider adapter. Forwards requests to https://api.anthropic.com/v1/."""
from __future__ import annotations

import os
from typing import Any

from providers.base import ProviderAdapter

_ANTHROPIC_BASE = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"
_CLAUDE_PREFIXES = ("claude-",)


def _is_directive_only_system(message: dict[str, Any]) -> bool:
    """Anthropic allows role=system in messages only as directive-only:
    content: [] with output_config. Full system prompts must use the
    top-level `system` parameter instead."""
    if not isinstance(message, dict) or message.get("role") != "system":
        return False
    if message.get("content") != []:
        return False
    return isinstance(message.get("output_config"), dict)


def _system_parts_as_blocks(value: Any) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if isinstance(value, list):
        return [b for b in value if isinstance(b, dict)]
    return [{"type": "text", "text": str(value)}]


def _merge_system_field(existing: Any, lifted: list[Any]) -> Any:
    if not lifted:
        return existing
    existing_blocks = _system_parts_as_blocks(existing)
    lifted_blocks: list[dict[str, Any]] = []
    for part in lifted:
        lifted_blocks.extend(_system_parts_as_blocks(part))
    if not existing_blocks and not lifted_blocks:
        return existing
    all_blocks = existing_blocks + lifted_blocks
    simple = all(
        b.get("type") == "text" and set(b.keys()) <= {"type", "text"}
        for b in all_blocks
    )
    if simple:
        return "\n\n".join(str(b.get("text") or "") for b in all_blocks if b.get("text"))
    return all_blocks


def lift_system_messages_to_top_level(body: dict[str, Any]) -> dict[str, Any]:
    """Move full system prompts from messages[] to top-level `system` --
    Anthropic's Messages API rejects a leading full role=system turn in
    messages (400: use top-level `system`). Idempotent."""
    if not isinstance(body, dict):
        return body
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        return body
    lifted: list[Any] = []
    remaining: list[Any] = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "system" and not _is_directive_only_system(msg):
            lifted.append(msg.get("content"))
        else:
            remaining.append(msg)
    if not lifted:
        return body
    merged = _merge_system_field(body.get("system"), lifted)
    out = {**body, "messages": remaining}
    if merged is not None and merged != "":
        out["system"] = merged
    return out


class AnthropicAdapter(ProviderAdapter):
    name = "anthropic"

    def base_url(self) -> str:
        return _ANTHROPIC_BASE

    def auth_headers(self, api_key: str) -> dict[str, str]:
        return {"x-api-key": api_key}

    def extra_headers(self) -> dict[str, str]:
        return {"anthropic-version": _ANTHROPIC_VERSION}

    def health(self) -> dict:
        return {"ok": bool(os.getenv("ANTHROPIC_API_KEY")), "provider": self.name}

    def adapt_request_body(self, endpoint: str, body: dict) -> dict:
        if "max_completion_tokens" in body and "max_tokens" not in body:
            body = {**body, "max_tokens": body.pop("max_completion_tokens")}
        if "/messages" in endpoint:
            body = lift_system_messages_to_top_level(body)
        return body

    def extract_usage(self, endpoint: str, response: dict) -> dict[str, int]:
        usage = response.get("usage", {})
        prompt = int(usage.get("input_tokens", 0))
        complete = int(usage.get("output_tokens", 0))
        return {
            "prompt_tokens": prompt,
            "completion_tokens": complete,
            "total_tokens": prompt + complete,
            "cache_read_tokens": int(usage.get("cache_read_input_tokens", 0)),
            "cache_write_tokens": int(usage.get("cache_creation_input_tokens", 0)),
        }


def is_anthropic_model(model: str) -> bool:
    return model.lower().startswith(_CLAUDE_PREFIXES)
