"""Provider API keys: per-tenant, bring-your-own-key storage for the
Playground/SDK, managed from the dashboard Settings page.

Deliberately simple -- one plaintext key per provider per tenant, no vault,
no OAuth. Enterprise's provider_keys.py uses a per-tenant credential vault
and (for Anthropic) subscription OAuth with token refresh; neither fits
OSS's single-tenant, bring-your-own-key model (see docs/OSS_FEATURE_MATRIX.md).
Storing the raw key in ClickHouse is an accepted OSS-scope tradeoff for a
self-hosted deployment -- document this in the README as a known limitation,
same posture as prompt/completion text already being stored unencrypted.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_auth
from db import get_client
from providers import REGISTRY

router = APIRouter(prefix="/api/settings/provider-keys", tags=["settings"])

_VALID_PROVIDERS = set(REGISTRY.keys()) - {"self-hosted"}  # alias of ollama


class ProviderKeyUpsert(BaseModel):
    provider: str
    api_key: str


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "•" * len(key)
    return f"{key[:4]}…{key[-4:]}"


@router.get("")
def list_provider_keys(auth=Depends(require_auth)) -> list[dict]:
    ch = get_client()
    result = ch.query(
        "SELECT provider, api_key, toString(updated_at) AS updated_at "
        "FROM tokensight.provider_keys FINAL "
        "WHERE tenant_id = {tenant_id:String} AND api_key != '' "
        "ORDER BY provider",
        parameters={"tenant_id": auth["tenant_id"]},
    )
    return [
        {"provider": row[0], "masked_key": _mask(row[1]), "updated_at": row[2]}
        for row in result.result_rows
    ]


@router.put("")
def upsert_provider_key(body: ProviderKeyUpsert, auth=Depends(require_auth)) -> dict:
    provider = body.provider.strip().lower()
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider}'. Valid: {sorted(_VALID_PROVIDERS)}",
        )
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key must not be empty")

    get_client().insert(
        "tokensight.provider_keys",
        [[auth["tenant_id"], provider, body.api_key.strip()]],
        column_names=["tenant_id", "provider", "api_key"],
    )
    return {"ok": True, "provider": provider}


@router.delete("/{provider}")
def delete_provider_key(provider: str, auth=Depends(require_auth)) -> dict:
    # ReplacingMergeTree has no direct DELETE; storing an empty key means
    # "unset" and get_provider_key() below treats empty as absent.
    get_client().insert(
        "tokensight.provider_keys",
        [[auth["tenant_id"], provider.strip().lower(), ""]],
        column_names=["tenant_id", "provider", "api_key"],
    )
    return {"ok": True}


def get_provider_key(tenant_id: str, provider: str) -> str:
    """Look up a saved key for (tenant_id, provider). Returns "" if unset."""
    ch = get_client()
    result = ch.query(
        "SELECT api_key FROM tokensight.provider_keys FINAL "
        "WHERE tenant_id = {tenant_id:String} AND provider = {provider:String} "
        "LIMIT 1",
        parameters={"tenant_id": tenant_id, "provider": provider},
    )
    if not result.result_rows:
        return ""
    return result.result_rows[0][0]
