"""The list of built-in optimizers. Add a new optimizer here and it shows up in the
default Pipeline and in the docs UI without any other change.

Text optimizers take one string. They run in the order listed when you use
Pipeline(): JSON is made compact first, then whitespace is cleaned, then repeated
paragraphs and bullets are removed.

Message optimizers take a chat messages list and are used on their own.
"""

from __future__ import annotations

from tokensguru.optimizers.base import Optimizer
from tokensguru.optimizers.exact_bullet_item_deduplication import BulletDeduplicator
from tokensguru.optimizers.exact_duplicate_system_messages import (
    SystemMessageDeduplicator,
)
from tokensguru.optimizers.exact_paragraph_deduplication import ParagraphDeduplicator
from tokensguru.optimizers.messages import MessageOptimizer
from tokensguru.optimizers.prose_whitespace_cleanup import WhitespaceCleaner
from tokensguru.optimizers.tokenguru_json_minifier import JsonMinifier

TEXT_OPTIMIZERS: tuple[type[Optimizer], ...] = (
    JsonMinifier,
    WhitespaceCleaner,
    ParagraphDeduplicator,
    BulletDeduplicator,
)

MESSAGE_OPTIMIZERS: tuple[type[MessageOptimizer], ...] = (SystemMessageDeduplicator,)


def default_optimizers() -> tuple[Optimizer, ...]:
    return tuple(optimizer() for optimizer in TEXT_OPTIMIZERS)
