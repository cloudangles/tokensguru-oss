"""Tenant/project/feature/user span context, propagated via contextvars."""
from __future__ import annotations

from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, Optional


@dataclass(slots=True)
class _SpanContext:
    tenant_id: str = ""
    project_id: str = ""
    feature_id: str = ""
    user_id: Optional[str] = None


_ctx_var: ContextVar[_SpanContext] = ContextVar("tokensight_ctx", default=_SpanContext())

_global_tenant: str = ""
_global_project: str = ""


def set_global_tenant(tenant_id: str) -> None:
    global _global_tenant
    _global_tenant = tenant_id


def set_global_project(project_id: str) -> None:
    global _global_project
    _global_project = project_id


def get_current_context() -> _SpanContext:
    ctx = _ctx_var.get()
    return _SpanContext(
        tenant_id=ctx.tenant_id or _global_tenant,
        project_id=ctx.project_id or _global_project,
        feature_id=ctx.feature_id,
        user_id=ctx.user_id,
    )


@contextmanager
def span_context(
    *,
    tenant_id: str = "",
    project_id: str = "",
    feature_id: str = "",
    user_id: Optional[str] = None,
) -> Generator[_SpanContext, None, None]:
    parent = _ctx_var.get()
    child = _SpanContext(
        tenant_id=tenant_id or parent.tenant_id or _global_tenant,
        project_id=project_id or parent.project_id or _global_project,
        feature_id=feature_id or parent.feature_id,
        user_id=user_id if user_id is not None else parent.user_id,
    )
    token = _ctx_var.set(child)
    try:
        yield child
    finally:
        _ctx_var.reset(token)
