"""System message deduplicator: removes a system message that repeats the one above.

Chat requests often grow a repeated system message, for example when an agent loop
adds the same instructions again on every step. This removes the repeats.

What it does:
    - Looks at the list of chat messages you send to a model.
    - Removes a system message that is exactly the same as the message right before
      it, if that message is also a system message. The first copy is kept.
    - "Exactly the same" means every field is equal (role, content, and any extra
      field such as "name"). The order of the fields does not matter.

What it leaves alone:
    - Repeats that are not next to each other. If a user, assistant or tool message
      sits between two identical system messages, both are kept.
    - System messages that differ in any way, even by one space.
    - Messages from any other role, and messages that are not dictionaries.
    - System messages whose content is not plain text (for example a list of parts),
      because those can carry settings such as cache markers.
    - The order of the remaining messages. Messages are only ever removed.

How to use it:
    from tokensguru.optimizers import SystemMessageDeduplicator

    messages = [
        {"role": "system", "content": "Be concise."},
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Hello"},
    ]
    result = SystemMessageDeduplicator().optimize(messages)
    result.optimized_messages    # the list to send to the model
    result.removed_count, result.removed_indexes
    result.original_tokens, result.optimized_tokens, result.saved_tokens
    print(result)                # id, tokens, reason and more

This works on the OpenAI-style messages list. A system prompt that is passed as a
separate parameter is not part of the list and is not touched.
"""

from __future__ import annotations

import json
from typing import Any

from tokensguru.optimizers.messages import MessageOptimizer


class SystemMessageDeduplicator(MessageOptimizer):
    id = "exact_duplicate_system_messages"
    name = "Exact duplicate system messages"
    applied_reason = (
        "Removed a system message identical to the system message right before it; "
        "the first copy was kept."
    )
    skipped_reason = "No system message repeats the system message right before it."

    def keep(
        self, messages: list[Any], context: dict[str, object] | None = None
    ) -> list[int]:
        del context
        kept: list[int] = []
        previous: str | None = None
        for index, message in enumerate(messages):
            identity = _system_identity(message)
            if identity is not None and identity == previous:
                continue
            kept.append(index)
            previous = identity
        return kept


def _system_identity(message: Any) -> str | None:
    if not isinstance(message, dict):
        return None
    if message.get("role") != "system" or not isinstance(message.get("content"), str):
        return None
    try:
        return json.dumps(message, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return None
