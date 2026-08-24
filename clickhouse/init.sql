-- TokenSight OSS schema.
--
-- llm_events is a strict column projection of Enterprise's table: base
-- observation columns only (trace/span/tenant/project/feature/user,
-- provider, model, tokens, cost, latency, status, timestamps) plus
-- prompt/completion text and the one OSS optimization stage's before/saved
-- pair. No waste_categories, cache_*, context-window/dedup, compression-
-- pipeline, or image-optimization columns -- those are Enterprise-only.

CREATE DATABASE IF NOT EXISTS tokensight;

CREATE TABLE IF NOT EXISTS tokensight.llm_events (
    event_id UUID DEFAULT generateUUIDv4(),
    trace_id String,
    span_id String,
    tenant_id String DEFAULT 'default',
    project_id String DEFAULT '',
    feature_id String DEFAULT '',
    user_id String DEFAULT '',
    provider String,
    model String,
    request_type String DEFAULT 'chat',
    input_tokens UInt32 DEFAULT 0,
    output_tokens UInt32 DEFAULT 0,
    total_tokens UInt32 MATERIALIZED input_tokens + output_tokens,
    input_tokens_before UInt32 DEFAULT 0,
    input_tokens_saved UInt32 DEFAULT 0,
    input_cost_usd Float64 DEFAULT 0,
    output_cost_usd Float64 DEFAULT 0,
    total_cost_usd Float64 MATERIALIZED input_cost_usd + output_cost_usd,
    latency_ms Float64 DEFAULT 0,
    ttft_ms Float64 DEFAULT 0,
    finish_reason String DEFAULT '',
    status String DEFAULT 'success',
    error_message String DEFAULT '',
    prompt_text String DEFAULT '',
    completion_text String DEFAULT '',
    agent_name String DEFAULT '',
    parent_span_id String DEFAULT '',
    request_timestamp DateTime64(3) DEFAULT now64(3),
    ingestion_timestamp DateTime64(3) DEFAULT now64(3)
) ENGINE = MergeTree()
ORDER BY (tenant_id, request_timestamp, trace_id, span_id);

-- Basic agent tracing: request -> model -> tokens -> latency -> result,
-- with parent/child span linkage. No OTel ingestion, no session-graph, no
-- cost-breakdown/failure-point/tool-usage analytics tables -- those are
-- Enterprise "advanced observability" and "agent-to-agent tracking".
CREATE TABLE IF NOT EXISTS tokensight.agent_spans (
    span_id String,
    trace_id String,
    parent_span_id String DEFAULT '',
    tenant_id String DEFAULT 'default',
    agent_id String DEFAULT '',
    agent_name String DEFAULT '',
    step_type String DEFAULT 'llm_call',
    step_name String DEFAULT '',
    input_tokens UInt32 DEFAULT 0,
    output_tokens UInt32 DEFAULT 0,
    cost_usd Float64 DEFAULT 0,
    latency_ms Float64 DEFAULT 0,
    status String DEFAULT 'success',
    error_message String DEFAULT '',
    started_at DateTime64(3) DEFAULT now64(3),
    finished_at DateTime64(3) DEFAULT now64(3)
) ENGINE = MergeTree()
ORDER BY (tenant_id, trace_id, started_at, span_id);

-- Simple auth: register/login/logout + API keys. No RBAC rank system, no
-- org/team/workspace ids -- one implicit tenant per deployment.
CREATE TABLE IF NOT EXISTS tokensight.users (
    user_id UUID DEFAULT generateUUIDv4(),
    email String,
    password_hash String,
    tenant_id String DEFAULT 'default',
    created_at DateTime64(3) DEFAULT now64(3)
) ENGINE = MergeTree()
ORDER BY (email);

CREATE TABLE IF NOT EXISTS tokensight.api_keys (
    api_key String,
    user_id String,
    tenant_id String DEFAULT 'default',
    label String DEFAULT '',
    created_at DateTime64(3) DEFAULT now64(3),
    revoked UInt8 DEFAULT 0
) ENGINE = MergeTree()
ORDER BY (api_key);

-- Per-tenant, per-provider LLM API keys entered via the dashboard Settings
-- page (bring-your-own-key -- no OAuth/vault, one plaintext key per
-- provider per tenant; that's a deliberate OSS simplification, not the
-- Enterprise credential-vault model). ReplacingMergeTree so re-saving a
-- provider's key upserts instead of accumulating history.
CREATE TABLE IF NOT EXISTS tokensight.provider_keys (
    tenant_id String DEFAULT 'default',
    provider String,
    api_key String,
    updated_at DateTime64(3) DEFAULT now64(3)
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (tenant_id, provider);
