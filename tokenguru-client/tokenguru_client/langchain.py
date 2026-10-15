"""LangChain / LangGraph integration: every chain, graph node, tool and LLM call shows up as a span in one trace.

    from tokenguru_client.langchain import TokenGuruCallbackHandler
    app.invoke(state, config={"callbacks": [TokenGuruCallbackHandler("supervisor")]})

Inside a custom chat model, pass the run ids so the gateway call joins the tree:

    resp = tg.chat.completions.create(model=..., messages=...,
        tg_span_id=str(run_manager.run_id), tg_parent_id=handler_parent(run_manager))
"""
import time
from typing import Any, Dict, Optional

from langchain_core.callbacks import BaseCallbackHandler

import tokenguru_client as _tg

from . import _auto_trace_id, _jsonable, _llm_link, _send_span, _span_id, _trace_id
import uuid


_LLM_PARENT: Dict[str, Optional[str]] = {}


def handler_parent(run_manager: Any) -> Optional[str]:
    """Span id to use as parent for an LLM call made inside a chat model's _generate (nearest recorded ancestor)."""
    run_id = str(getattr(run_manager, "run_id", ""))
    if run_id in _LLM_PARENT:
        return _LLM_PARENT.pop(run_id)
    parent = getattr(run_manager, "parent_run_id", None)
    return str(parent) if parent else None


class TokenGuruCallbackHandler(BaseCallbackHandler):
    """Records chains / LangGraph nodes / tools as spans. LLM calls are recorded by the gateway itself.

    Installed automatically by tg.connect() when LangChain is present; add it to a run's callbacks only to name the trace."""

    run_inline = True   # run in the caller's context so the trace id reaches nested calls

    def __init__(self, name: str = ""):
        self.name = name
        self._open: Dict[str, dict] = {}            # run_id -> span being recorded
        self._alias: Dict[str, Optional[str]] = {}  # run_id -> nearest recorded ancestor span id
        self._trace_tokens: Dict[str, Any] = {}     # root run_id -> contextvar token

    def _nearest(self, parent_run_id) -> Optional[str]:
        return self._alias.get(str(parent_run_id)) if parent_run_id else None

    def _start(self, run_id, parent_run_id, kind: str, name: str, inp: Any) -> None:
        rid = str(run_id)
        if _trace_id.get() is None:
            # No enclosing trace: with trace_gap set, runs that follow each other closely share one trace.
            self._trace_tokens[rid] = _trace_id.set(_auto_trace_id() if _tg._trace_gap else str(uuid.uuid4()))
        self._alias[rid] = rid
        # A run started inside tg.trace()/tg.span() (and not inside another LangChain run) hangs under that span.
        parent = self._nearest(parent_run_id) or (None if parent_run_id else _span_id.get())
        self._open[rid] = {"span_id": rid, "parent_id": parent, "trace_id": _trace_id.get(), "kind": kind, "name": name, "input": _jsonable(inp), "start_ms": int(time.time() * 1000)}

    def _end(self, run_id, output: Any = None, error: Optional[BaseException] = None) -> None:
        rid = str(run_id)
        sp = self._open.pop(rid, None)
        self._alias.pop(rid, None)
        if sp:
            sp.update(output=_jsonable(output), end_ms=int(time.time() * 1000), status="error" if error else "ok", error=str(error) if error else None)
            _send_span(sp)
            _tg._last_call_end = time.time()   # keeps trace_gap grouping measuring from the latest activity
        token = self._trace_tokens.pop(rid, None)
        if token is not None:
            try:
                _trace_id.reset(token)
            except ValueError:   # ended in a different context than it started
                _trace_id.set(None)

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, metadata=None, name=None, **kw):
        node = (metadata or {}).get("langgraph_node")
        if parent_run_id is None:
            self._start(run_id, parent_run_id, "agent", self.name or name or "run", inputs)
        elif node and name == node:
            self._start(run_id, parent_run_id, "chain", name, inputs)
        elif name == "LangGraph":   # a graph invoked inside a node (sub-agent)
            self._start(run_id, parent_run_id, "agent", "sub-agent", inputs)
        else:                        # internal runnable: skip, children attach to the nearest recorded ancestor
            self._alias[str(run_id)] = self._nearest(parent_run_id)

    def on_chain_end(self, outputs, *, run_id, **kw):
        self._end(run_id, outputs)

    def on_chain_error(self, error, *, run_id, **kw):
        self._end(run_id, error=error)

    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, name=None, **kw):
        self._start(run_id, parent_run_id, "tool", name or (serialized or {}).get("name", "tool"), input_str)

    def on_tool_end(self, output, *, run_id, **kw):
        self._end(run_id, getattr(output, "content", output))

    def on_tool_error(self, error, *, run_id, **kw):
        self._end(run_id, error=error)

    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kw):
        # The gateway records the LLM span itself; tell chat.completions.create which span this call is.
        rid = str(run_id)
        parent = self._nearest(parent_run_id)
        _LLM_PARENT[rid] = parent
        _llm_link.set((rid, parent))

    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id=None, **kw):
        rid = str(run_id)
        parent = self._nearest(parent_run_id)
        _LLM_PARENT[rid] = parent
        _llm_link.set((rid, parent))

    def on_llm_end(self, response, *, run_id=None, **kw):
        if run_id:
            _LLM_PARENT.pop(str(run_id), None)
        _llm_link.set(None)

    def on_llm_error(self, error, *, run_id=None, **kw):
        if run_id:
            _LLM_PARENT.pop(str(run_id), None)
        _llm_link.set(None)
