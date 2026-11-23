"""Text optimizers that make text shorter without changing its meaning."""

from tokensguru.optimizers.base import OptimizationResult, Optimizer
from tokensguru.optimizers.exact_bullet_item_deduplication import BulletDeduplicator
from tokensguru.optimizers.exact_duplicate_system_messages import (
    SystemMessageDeduplicator,
)
from tokensguru.optimizers.exact_paragraph_deduplication import ParagraphDeduplicator
from tokensguru.optimizers.messages import MessageOptimizationResult, MessageOptimizer
from tokensguru.optimizers.pipeline import Pipeline, PipelineResult
from tokensguru.optimizers.prose_whitespace_cleanup import WhitespaceCleaner
from tokensguru.optimizers.tokenguru_json_minifier import JsonMinifier

__all__ = [
    "BulletDeduplicator",
    "JsonMinifier",
    "MessageOptimizationResult",
    "MessageOptimizer",
    "OptimizationResult",
    "Optimizer",
    "ParagraphDeduplicator",
    "Pipeline",
    "PipelineResult",
    "SystemMessageDeduplicator",
    "WhitespaceCleaner",
]
