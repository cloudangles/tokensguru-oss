"""Tiny MLflow-style client: point it at a server URL, then call functions.

    import tokenguru_client as ts

    ts.connect("http://localhost", "tsg_...")   # one line: server URL + your access token
    print(ts.me())
"""
import contextvars
import json
import os
import re
import threading
import time
import uuid
from types import SimpleNamespace
import urllib.error
import urllib.request
from typing import Any, Optional

from .tool_cache import ReadOnlyToolCache

__version__ = "0.1.0"

__all__ = ["__version__", "TokenGuruError", "ReadOnlyToolCache", "set_tracking_uri", "get_tracking_uri", "set_api_key", "request", "health", "me", "connect", "chat", "models", "prompts", "span", "trace", "session", "current_trace_id"]

_tracking_uri: Optional[str] = None
_api_key: Optional[str] = None
_session_token: Optional[str] = None
_identity: Optional[dict] = None
_token: Optional[str] = None
_optimize_tool_outputs_default = False
_active_prompt: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("tg_active_prompt", default=None)


class TokenGuruError(Exception):
    """Raised when the server is unreachable or returns an error status."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


def _format_http_error(status: int, message: str) -> str:
    """Turn common provider permission failures into actionable SDK errors."""
    if status == 403 and "bedrock:InvokeModel" in message and (
        "not authorized" in message.lower() or "no identity-based policy" in message.lower()
    ):
        action = re.search(r"perform:\s*(bedrock:[A-Za-z]+)", message)
        target = re.search(
            r"arn:aws:bedrock:([a-z0-9-]+):\d+:(inference-profile|foundation-model)/([^\s]+)",
            message,
        )
        permission = action.group(1) if action else "bedrock:InvokeModel"
        resource_type, resource, region = "model", "the requested model", "the configured region"
        if target:
            region, resource_type, resource = target.groups()
        return (
            f"Amazon Bedrock denied this request: the AWS role configured in TokenSight is missing "
            f"{permission} permission for {resource_type} {resource} in {region}. "
            f"Ask your AWS administrator to grant {permission} access to this resource, then retry."
        )
    return f"Request failed ({status}): {message}"


def set_tracking_uri(uri: str) -> None:
    global _tracking_uri
    _tracking_uri = uri.strip().rstrip("/")


def get_tracking_uri() -> str:
    uri = _tracking_uri or os.environ.get("TOKENGURU_TRACKING_URI", "").strip().rstrip("/")
    if not uri:
        raise TokenGuruError("No server URL. Call set_tracking_uri(url) or set TOKENGURU_TRACKING_URI.")
    return uri


def set_api_key(key: str) -> None:
    global _api_key
    _api_key = key.strip()


def request(method: str, path: str, body: Optional[dict] = None, timeout: float = 10.0, token: Optional[str] = None, headers_extra: Optional[dict] = None) -> Any:
    """Send a request to the server and return the decoded JSON response."""
    headers = {"Accept": "application/json"}
    key = _api_key or os.environ.get("TOKENGURU_API_KEY", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif _session_token:
        headers["Authorization"] = f"Bearer {_session_token}"
    elif key:
        headers["X-API-Key"] = key
    headers.update(headers_extra or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(get_tracking_uri() + path, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            body = json.loads(raw)
            err = body.get("error") if isinstance(body.get("error"), dict) else {}
            message = err.get("message") or body.get("detail") or raw
        except ValueError:
            message = raw
        raise TokenGuruError(_format_http_error(exc.code, message), exc.code) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TokenGuruError(f"Could not reach {get_tracking_uri()}: {exc}") from exc


def connect(url: str, token: str = "", trace_gap: Optional[float] = None, optimize_tool_outputs: bool = False) -> Any:
    """One-call setup: set the server URL, sign in with your access token (tsg_...), return your identity.

    Tracing is automatic: LangChain / LangGraph runs become one trace with every node, tool and LLM call,
    and tg.trace() / tg.span() group anything else. For hand-rolled agent loops with neither, pass
    trace_gap=<seconds> to treat LLM calls that follow each other within that gap as one trace.
    Set optimize_tool_outputs=True to opt in to exact-repeat cleanup for plain-text tool results on all
    model calls; an individual chat.completions.create() call can override this setting."""
    global _session_token, _identity, _token, _trace_gap, _optimize_tool_outputs_default
    _trace_gap = trace_gap
    _optimize_tool_outputs_default = optimize_tool_outputs
    set_tracking_uri(url)
    _install_langchain_hook()
    _propagate_context_to_threads()
    health()
    token = token or os.environ.get("TOKENGURU_API_KEY", "")
    if not token:
        return {"status": "connected"}
    _token = token
    data = request("POST", "/api/login/token", {"token": token})
    _session_token = data.get("access_token")
    _identity = {k: data.get(k) for k in ("user_id", "email", "name", "organization", "role", "allowed_models")}
    return _identity


def health() -> Any:
    """Check that the server is up."""
    return request("GET", "/api/health")


def me() -> Any:
    """Return who you are signed in as (from connect())."""
    if _identity is None:
        raise TokenGuruError("Not signed in. Call connect(url, token) first.")
    return _identity


def _wrap(value: Any) -> Any:
    """Dicts -> attribute access (resp.choices[0].message.content), like the OpenAI SDK."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _wrap(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_wrap(v) for v in value]
    return value


def _require_token() -> str:
    tok = _token or os.environ.get("TOKENGURU_API_KEY", "")
    if not tok:
        raise TokenGuruError("Not signed in. Call connect(url, token) first.")
    return tok


class _Completions:
    def create(
        self,
        model: str,
        messages: list,
        tg_span_id: Optional[str] = None,
        tg_parent_id: Optional[str] = None,
        optimize: bool = True,
        optimize_tool_outputs: Optional[bool] = None,
        active_tool_names: Optional[list[str]] = None,
        **params: Any,
    ) -> Any:
        """Same shape as openai.chat.completions.create(); runs through TokenGuru with your token.

        Inside tg.trace()/tg.span() (or a LangChain run with TokenGuruCallbackHandler) the call is linked
        into the surrounding trace automatically. tg_span_id / tg_parent_id override that link.

        ``optimize=True`` is the default and asks the gateway to optimize the prompt before it calls the
        provider. Set it to ``False`` for an intentional unoptimized baseline request. The response's
        ``tokensight.optimization`` object reports the measured before/after tokens and input cost.

        Tool outputs are preserved by default. Set ``optimize_tool_outputs=True`` to let the same
        conservative exact-repeat passes inspect plain-text ``role="tool"`` messages before the next
        model call. Pass ``active_tool_names=[...]`` only when the agent has already selected the
        tools available for this step; the gateway removes other tool schemas. For repeated pure
        read-only function calls within one agent run, ``ReadOnlyToolCache`` provides local memoization."""
        headers = {}
        active_prompt = _active_prompt.get()
        if active_prompt:
            headers["X-TG-Prompt-Id"] = str(active_prompt.get("prompt_id") or "")
            headers["X-TG-Prompt-Name"] = str(active_prompt.get("prompt_name") or "")
            headers["X-TG-Prompt-Version-Id"] = str(active_prompt.get("version_id") or "")
        session_id = _session_id.get()
        if session_id:
            headers["X-TG-Session-Id"] = session_id
        link = _llm_link.get()            # set by the LangChain hook for the model call in progress
        # A completion outside an explicit trace is its own one-step trace.
        # Always send an ID so repeated requests with identical prompts are not
        # collapsed by the server's legacy prompt-based fallback trace ID.
        trace_id = _trace_id.get() or (_auto_trace_id() if _trace_gap else str(uuid.uuid4()))
        if trace_id:
            headers["X-TG-Trace-Id"] = trace_id
            headers["X-TG-Span-Id"] = tg_span_id or (link[0] if link else str(uuid.uuid4()))
            parent = tg_parent_id or (link[1] if link else None) or _span_id.get()
            if parent:
                headers["X-TG-Parent-Span-Id"] = parent
        if "skip_token_optimizer" in params:
            raise TypeError("Use optimize=False instead of skip_token_optimizer")
        body = {
            "model": model,
            "messages": messages,
            "skip_token_optimizer": not optimize,
            "optimize_tool_outputs": _optimize_tool_outputs_default if optimize_tool_outputs is None else optimize_tool_outputs,
            **params,
        }
        if active_tool_names is not None:
            body["active_tool_names"] = active_tool_names
        try:
            data = request(
                "POST",
                "/api/v1/chat/completions",
                body,
                timeout=120.0,
                token=_require_token(),
                headers_extra=headers,
            )
        finally:
            global _last_call_end
            _last_call_end = time.time()
        if trace_id and isinstance(data, dict):
            data = dict(data)
            server_metadata = data.get("tokensight")
            tokensight = dict(server_metadata) if isinstance(server_metadata, dict) else {}
            tokensight["trace_id"] = trace_id
            data["tokensight"] = tokensight
        return _wrap(data)


class _Chat:
    completions = _Completions()


chat = _Chat()


def models() -> list:
    """Model ids your token may use."""
    data = request("GET", "/api/v1/models", token=_require_token())
    return [m["id"] for m in data["data"]]


class _Prompts:
    def list(self, tenant_id: Optional[str] = None) -> list:
        """Get all prompts for your organization or a specific tenant."""
        params = f"?tenant={tenant_id}" if tenant_id else ""
        data = request("GET", f"/api/prompts{params}", token=_require_token())
        return data if isinstance(data, list) else data.get("prompts", [])

    def get(self, prompt_id: str) -> Any:
        """Get a specific prompt by ID."""
        return request("GET", f"/api/prompts/{prompt_id}", token=_require_token())

    def get_active_version(self, prompt_id: str) -> dict:
        """Get the active version of a prompt with system and user prompts."""
        data = self.get(prompt_id)
        active_version = None
        versions = data.get("versions", [])
        active_id = data.get("active_version_id") or data.get("activeVersionId")

        if active_id:
            active_version = next((v for v in versions if v.get("id") == active_id), None)
        elif versions:
            active_version = versions[0]

        # The prompt's top-level fields are the latest saved state. If a legacy
        # or partially migrated document points at a missing version ID, use
        # those fields instead of silently returning an older version.
        selected = active_version or data

        prompt = {
            "prompt_id": prompt_id,
            "prompt_name": data.get("prompt_name") or data.get("name"),
            "system_prompt": selected.get("system_prompt", selected.get("systemPrompt", "")),
            "user_prompt": selected.get("user_prompt", selected.get("userPrompt", "")),
            "provider": selected.get("provider", ""),
            "model": selected.get("model", ""),
            "version_id": (active_version or {}).get("id") or active_id,
        }
        _active_prompt.set({key: prompt[key] for key in ("prompt_id", "prompt_name", "version_id")})
        return prompt


prompts = _Prompts()


# ── Tracing: group LLM calls, tools and agent steps into one trace ───────────────
_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tg_trace_id", default=None)
_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tg_span_id", default=None)


def current_trace_id() -> Optional[str]:
    return _trace_id.get()


def _send_span(span: dict) -> None:
    """Deliver a finished span without blocking the caller; tracing must never break the app."""
    def run() -> None:
        try:
            request("POST", "/api/v1/spans", {"spans": [span]}, timeout=10.0, token=_require_token())
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class span:
    """Record a step (agent, tool, chain …) as part of the current trace. Use as a context manager or decorator.

        with tg.span("search", kind="tool", input={"q": "x"}) as s:
            s.output = run_search()
    """

    def __init__(self, name: str, kind: str = "chain", input: Any = None, span_id: Optional[str] = None, parent_id: Optional[str] = None):
        self.name, self.kind, self.input, self.output = name, kind, input, None
        self.span_id = span_id or str(uuid.uuid4())
        self._parent_override = parent_id
        self._tokens: list = []

    def __enter__(self) -> "span":
        self._started = time.time()
        self.trace_id = _trace_id.get()
        self._own_trace = self.trace_id is None
        if self._own_trace:
            self.trace_id = str(uuid.uuid4())
            self._t_token = _trace_id.set(self.trace_id)
        self.parent_id = self._parent_override or _span_id.get()
        self._s_token = _span_id.set(self.span_id)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _span_id.reset(self._s_token)
        if self._own_trace:
            _trace_id.reset(self._t_token)
        _send_span({
            "span_id": self.span_id, "parent_id": self.parent_id, "trace_id": self.trace_id,
            "kind": self.kind, "name": self.name,
            "input": _jsonable(self.input), "output": _jsonable(self.output),
            "start_ms": int(self._started * 1000), "end_ms": int(time.time() * 1000),
            "status": "error" if exc_type else "ok", "error": str(exc) if exc else None,
        })

    def __call__(self, fn):
        import functools

        @functools.wraps(fn)
        def wrapper(*a, **kw):
            with span(self.name or fn.__name__, self.kind, input={"args": a, "kwargs": kw}) as s:
                s.output = fn(*a, **kw)
                return s.output
        return wrapper


def trace(name: str, input: Any = None):
    """Start a new trace (its root span is an agent run). Everything inside — LLM calls and tg.span() steps — belongs to it."""
    return span(name, kind="agent", input=input)


# ── Automatic grouping ──────────────────────────────────────────────────────────
_trace_gap: Optional[float] = None
_last_call_end = 0.0
_auto_id: Optional[str] = None
# (span id, parent span id) of the LangChain model call currently running — read by chat.completions.create
_llm_link: contextvars.ContextVar[Optional[tuple]] = contextvars.ContextVar("tg_llm_link", default=None)


def _auto_trace_id() -> str:
    """Heuristic for code with no tracing context: calls close together belong to one trace."""
    global _auto_id
    if _auto_id is None or time.time() - _last_call_end > (_trace_gap or 0):
        _auto_id = str(uuid.uuid4())
    return _auto_id


_hook_installed = False
_handler_var: contextvars.ContextVar = contextvars.ContextVar("tg_langchain_handler", default=None)


def _install_langchain_hook() -> None:
    """If LangChain is installed, attach the tracing handler to every run — no changes to user code."""
    global _hook_installed
    if _hook_installed:
        return
    try:
        from langchain_core.tracers.context import register_configure_hook
        from .langchain import TokenGuruCallbackHandler
    except Exception:
        return
    register_configure_hook(_handler_var, inheritable=True)
    _handler_var.set(TokenGuruCallbackHandler())
    _hook_installed = True


# ── Sessions: group several traces (e.g. the turns of one conversation) ─────────
_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tg_session_id", default=None)


class session:
    """Mark everything inside as part of one session (a conversation or user visit).

        with tg.session("chat-42"):
            tg.chat.completions.create(...)     # turn 1
            tg.chat.completions.create(...)     # turn 2 — same session

    Use a stable id you already have (conversation id, ticket id). Call tg.session("id").__enter__()
    once, or use it as a context manager per request in a server."""

    def __init__(self, session_id: str):
        self.session_id = str(session_id)[:64]

    def __enter__(self) -> "session":
        self._token = _session_id.set(self.session_id)
        return self

    def __exit__(self, *exc) -> None:
        _session_id.reset(self._token)


_threads_patched = False


def _propagate_context_to_threads() -> None:
    """Make worker threads inherit the caller's context.

    Python does not do this for ThreadPoolExecutor / Thread, so a step that fans work out to a pool would lose the
    trace, session and LangChain parent link and every pooled task would show up as a separate trace."""
    global _threads_patched
    if _threads_patched:
        return
    _threads_patched = True
    from concurrent.futures import ThreadPoolExecutor
    import threading

    orig_submit = ThreadPoolExecutor.submit

    def submit(self, fn, /, *args, **kwargs):
        ctx = contextvars.copy_context()
        return orig_submit(self, ctx.run, fn, *args, **kwargs)

    ThreadPoolExecutor.submit = submit  # type: ignore[method-assign]

    orig_init, orig_run = threading.Thread.__init__, threading.Thread.run

    def init(self, *a, **kw):
        orig_init(self, *a, **kw)
        self._tg_ctx = contextvars.copy_context()

    def run(self):
        ctx = getattr(self, "_tg_ctx", None)
        return ctx.run(orig_run, self) if ctx is not None else orig_run(self)

    threading.Thread.__init__ = init  # type: ignore[method-assign]
    threading.Thread.run = run  # type: ignore[method-assign]
