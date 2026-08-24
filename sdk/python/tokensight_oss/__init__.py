"""TokenSight OSS SDK -- core AI observation/instrumentation.

Customer integration::

    import tokensight_oss as tokensight
    tokensight.init(api_key="tsk_...")
    client = tokensight.openai.OpenAI(api_key="sk-...")
    client.chat.completions.create(...)  # tracked automatically

Pure observation: this SDK times calls, reads token usage, estimates cost,
and POSTs a flat event to your TokenSight OSS backend. It never patches
provider SDK internals, never mutates your request, and has no privacy/
optimization/governance runtime -- see docs/OSS_FEATURE_MATRIX.md for what
that means and where it lives (Enterprise only).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Optional

from .config import TokenSightConfig
from .context import set_global_tenant, set_global_project, span_context
from . import trace_context
from .agent_headers import agent_headers, merge_agent_headers

__all__ = [
    "init", "shutdown", "context", "set_tenant", "set_project",
    "openai", "anthropic", "cohere", "litellm",
    "trace_context", "agent_headers", "merge_agent_headers", "TokenSightConfig",
]

_exporter = None
_config: Optional[TokenSightConfig] = None


def init(
    *,
    api_endpoint: str = "",
    api_key: str = "",
    tenant_id: str = "",
    project_id: str = "",
    config: Optional[TokenSightConfig] = None,
) -> None:
    """Configure the SDK. Call once at startup before wrapping a client."""
    global _exporter, _config

    from .exporter import HttpExporter

    if _exporter is not None:
        _exporter.shutdown()

    if config is not None:
        _config = config
    else:
        _config = TokenSightConfig(
            api_endpoint=api_endpoint or TokenSightConfig().api_endpoint,
            api_key=api_key,
        )

    _config.validate()
    _exporter = HttpExporter(_config)

    if tenant_id:
        set_global_tenant(tenant_id)
    if project_id:
        set_global_project(project_id)


def set_tenant(tenant_id: str) -> None:
    set_global_tenant(tenant_id)


def set_project(project_id: str) -> None:
    set_global_project(project_id)


@contextmanager
def context(
    *,
    tenant_id: str = "",
    project_id: str = "",
    feature_id: str = "",
    user_id: Optional[str] = None,
) -> Generator[Any, None, None]:
    with span_context(
        tenant_id=tenant_id, project_id=project_id,
        feature_id=feature_id, user_id=user_id,
    ) as ctx:
        yield ctx


def shutdown() -> None:
    global _exporter
    if _exporter is not None:
        _exporter.flush()
        _exporter.shutdown()
        _exporter = None


class _OpenAINamespace:
    @staticmethod
    def OpenAI(**kwargs: Any) -> Any:
        from .client import OpenAI as _WrappedOpenAI
        if _exporter is None:
            raise RuntimeError("TokenSight not initialised. Call tokensight.init() first.")
        return _WrappedOpenAI(exporter=_exporter, **kwargs)


class _AnthropicNamespace:
    @staticmethod
    def Anthropic(**kwargs: Any) -> Any:
        from .anthropic_wrapper import Anthropic as _WrappedAnthropic
        if _exporter is None:
            raise RuntimeError("TokenSight not initialised. Call tokensight.init() first.")
        return _WrappedAnthropic(exporter=_exporter, **kwargs)


class _CohereNamespace:
    @staticmethod
    def Cohere(**kwargs: Any) -> Any:
        from .cohere_wrapper import Cohere as _WrappedCohere
        if _exporter is None:
            raise RuntimeError("TokenSight not initialised. Call tokensight.init() first.")
        return _WrappedCohere(exporter=_exporter, **kwargs)


class _LiteLLMNamespace:
    @staticmethod
    def LiteLLMWrapper(**kwargs: Any) -> Any:
        from .litellm_wrapper import LiteLLMWrapper as _WrappedLiteLLM
        if _exporter is None:
            raise RuntimeError("TokenSight not initialised. Call tokensight.init() first.")
        return _WrappedLiteLLM(exporter=_exporter, **kwargs)


openai = _OpenAINamespace()
anthropic = _AnthropicNamespace()
cohere = _CohereNamespace()
litellm = _LiteLLMNamespace()
