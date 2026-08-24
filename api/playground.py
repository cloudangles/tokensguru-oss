"""Playground: POST /v1/playground/run.

Provider/model + prompt in; runs the one OSS optimization stage (repeated-
content collapse), calls the real provider, returns tokens/cost/latency/
trace. Modeled on Enterprise's /v1/playground/run contract, without the
11-pipeline "Optimization Summary" breakdown (that's product IP -- see
docs/OSS_FEATURE_MATRIX.md).
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_auth
from db import get_client
from optimize.repeated_content import collapse_repeated_content
from pricing import estimate_cost
from provider_keys import get_provider_key
from providers import get_adapter
from tokens import estimate_tokens

router = APIRouter(prefix="/v1/playground", tags=["playground"])

_PROVIDER_ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "google": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together": "TOGETHER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
}

_INGEST_COLUMNS = [
    "trace_id", "span_id", "tenant_id", "project_id", "feature_id", "user_id",
    "provider", "model", "request_type", "input_tokens", "output_tokens",
    "input_tokens_before", "input_tokens_saved", "input_cost_usd",
    "output_cost_usd", "latency_ms", "ttft_ms", "finish_reason", "status",
    "error_message", "prompt_text", "completion_text", "agent_name",
    "parent_span_id", "request_timestamp",
]


class PlaygroundRunRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    invoke_provider: bool = True


def _anthropic_body(model: str, prompt: str) -> dict:
    return {"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}


def _openai_style_body(model: str, prompt: str) -> dict:
    return {"model": model, "messages": [{"role": "user", "content": prompt}]}


def _completion_text(provider: str, response: dict) -> str:
    if provider == "anthropic":
        blocks = response.get("content") or []
        return "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    if provider == "google":
        candidates = response.get("candidates") or []
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    choices = response.get("choices") or []
    if choices:
        return choices[0].get("message", {}).get("content", "") or ""
    return ""


@router.post("/run")
def run_playground(body: PlaygroundRunRequest, auth=Depends(require_auth)) -> dict:
    trace_id = f"tr-{uuid.uuid4().hex[:16]}"
    span_id = f"sp-{uuid.uuid4().hex[:12]}"

    original_prompt = body.prompt
    optimized_prompt, tokens_saved = collapse_repeated_content(original_prompt)
    input_tokens_before = estimate_tokens(original_prompt, body.provider)

    adapter = get_adapter(body.provider)
    completion_text = ""
    output_tokens = 0
    status = "success"
    error_message = ""
    latency_ms = 0.0
    finish_reason = ""

    if body.invoke_provider:
        # Saved key (Settings page) takes priority over .env -- lets a
        # deployment run with no provider keys baked into the container at
        # all, and lets a user test a provider without restarting anything.
        api_key = get_provider_key(auth["tenant_id"], body.provider)
        if not api_key:
            api_key = os.getenv(_PROVIDER_ENV_KEYS.get(body.provider, ""), "")
        if not api_key and body.provider != "ollama":
            raise HTTPException(
                status_code=400,
                detail=f"No API key configured for provider '{body.provider}'. "
                f"Add one on the Settings page, or set "
                f"{_PROVIDER_ENV_KEYS.get(body.provider, '<PROVIDER>_API_KEY')} in your .env.",
            )
        if body.provider == "anthropic":
            url = adapter.endpoint_url("/v1/messages")
            req_body = adapter.adapt_request_body("/v1/messages", _anthropic_body(body.model, optimized_prompt))
        elif body.provider == "google":
            url = adapter.endpoint_url(f"/v1beta/models/{body.model}:generateContent")
            req_body = {"contents": [{"parts": [{"text": optimized_prompt}]}]}
        else:
            url = adapter.endpoint_url("/v1/chat/completions" if body.provider != "ollama" else "/v1/chat/completions")
            req_body = adapter.adapt_request_body("/v1/chat/completions", _openai_style_body(body.model, optimized_prompt))

        headers = {**adapter.auth_headers(api_key), **adapter.extra_headers(), "Content-Type": "application/json"}

        start = time.monotonic()
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, headers=headers, json=req_body)
            latency_ms = (time.monotonic() - start) * 1000
            if resp.status_code >= 400:
                status = "error"
                error_message = f"{body.provider} http {resp.status_code}: {resp.text[:300]}"
            else:
                data = resp.json()
                usage = adapter.extract_usage("/v1/chat/completions", data)
                output_tokens = usage.get("completion_tokens", 0)
                completion_text = _completion_text(body.provider, data)
                finish_reason = "stop"
        except httpx.HTTPError as exc:
            latency_ms = (time.monotonic() - start) * 1000
            status = "error"
            error_message = str(exc)
    else:
        output_tokens = estimate_tokens("(provider not invoked -- estimate only)")

    input_tokens = estimate_tokens(optimized_prompt, body.provider)
    input_cost, output_cost = estimate_cost(body.model, input_tokens, output_tokens)

    row = [
        trace_id, span_id, auth["tenant_id"], "", "playground", auth["user_id"],
        body.provider, body.model, "chat", input_tokens, output_tokens,
        input_tokens_before, tokens_saved, input_cost, output_cost,
        latency_ms, 0.0, finish_reason, status, error_message,
        original_prompt[:8000], completion_text[:8000], "", "",
        datetime.now(timezone.utc),
    ]
    get_client().insert("tokensight.llm_events", [row], column_names=_INGEST_COLUMNS)

    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "provider": body.provider,
        "model": body.model,
        "status": status,
        "error_message": error_message,
        "original_prompt": original_prompt,
        "optimized_prompt": optimized_prompt,
        "completion_text": completion_text,
        "input_tokens_before": input_tokens_before,
        "input_tokens": input_tokens,
        "tokens_saved": tokens_saved,
        "output_tokens": output_tokens,
        "input_cost_usd": input_cost,
        "output_cost_usd": output_cost,
        "latency_ms": latency_ms,
    }
