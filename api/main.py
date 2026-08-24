"""TokenSight OSS API.

Application -> SDK/ingest -> Request Observation -> Basic Runtime
(repeated-content collapse) -> Provider -> Response -> Trace/Metrics ->
Dashboard. See docs/OSS_FEATURE_MATRIX.md for what's deliberately not here.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import agent_tracing
import auth
import ingest
import playground
import provider_keys
import traces
from db import get_client

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("tokensight.main")

app = FastAPI(title="TokenSight OSS API", version="0.1.0")

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(traces.router)
app.include_router(agent_tracing.router)
app.include_router(playground.router)
app.include_router(provider_keys.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/ready")
def ready() -> dict:
    try:
        get_client().command("SELECT 1")
        return {"ok": True, "clickhouse": "ok"}
    except Exception as exc:
        logger.warning("readiness check failed: %s", exc)
        return {"ok": False, "clickhouse": "unreachable"}
