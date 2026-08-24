# TokenSight OSS Feature Matrix

This matrix is the record of what was audited in the Enterprise implementation
before any OSS code was written, and the classification each component received.
Classifications: **OSS** (ships as-is or near-verbatim), **ENTERPRISE**
(Enterprise-only, not in OSS), **PARTIAL** (some sub-piece is OSS-appropriate, rest
is not), **INTERNAL** (tooling/infra, not product-facing), **NOT VERIFIED** (named
in scope but not code-audited this pass).

Every row below is backed by a file:line citation into `tokensight-enterprise/`
gathered during this audit — see the linked session notes for the full detail;
this document is the condensed, durable reference.

## 1. SDKs

| Component | Classification | Notes |
|---|---|---|
| Python: tracking-only wrappers (`client.py`, basic `Anthropic`/`_MessagesWrapper` in `anthropic_wrapper.py`, `cohere_wrapper.py`, `litellm_wrapper.py`, `cost.py`, `exporter.py`, `context.py`, `config.py`, `agent_headers.py`, `trace_context.py`) | **OSS** | Pure observation: time the call, read usage, POST a flat event. No optimization/privacy/governance. |
| Python: `tokensight.instrument()` pipeline (`instrument.py`, `client_proxy.py`, `pipeline.py`, `runtime/`, `plugins/`, `knowledge/`, `policy_engine.py`, `subscription_wrapper.py`, `TokenSightAnthropic`) | **ENTERPRISE** | The SDK's *recommended* top-level integration path, but it's the full Enterprise Runtime (privacy engine, governance plugins, caching, memory/knowledge injection) wearing an SDK-shaped API. Not ported to OSS. |
| Node SDK (`sdk-node/src/index.ts`) | **OSS** (minus gateway classes) | Verified clean — no privacy/optimization/governance code. `TokenSightAnthropic`/`TokenSightOpenAI` gateway-routing classes excluded. |
| Go SDK (`sdk-go/`) | **OSS** (not built this milestone) | Equally clean; not requested for this milestone, easy follow-on. |
| Bedrock Python wrapper (`bedrock_wrapper.py`) | **PARTIAL/deprecated** | Explicitly documented in its own docstring as a stub bypassing the full pipeline — not carried into OSS. |

## 2. Provider Adapters

| Adapter | Classification | Notes |
|---|---|---|
| OpenAI, Anthropic, Groq, DeepSeek, Gemini | **OSS** | Simple pass-through: base URL + auth header + usage-field extraction. Copied near-verbatim. |
| Ollama, OpenRouter, Together | **OSS (reworked)** | Copied, with "vault JSON credential" parsing replaced by plain env-var config (that parsing was a multi-tenant/BYO-key concept, not needed for a single-tenant self-host). |
| Azure OpenAI, Vertex, Bedrock | **ENTERPRISE (deferred)** | Deep multi-tenant infra: STS cross-account role assumption (Bedrock), ADC/service-account token minting (Vertex), credential-vault decoding (Azure). Out of scope for this milestone; candidates for a later OSS release. |

## 3. Instrumentation / Ingestion

| Component | Classification | Notes |
|---|---|---|
| `api/batch_ingest.py`'s `IngestEventV2`/`_build_row()` shape | **OSS (trimmed)** | Closest-to-OSS-shaped existing path. OSS keeps only: trace/span/tenant/project/feature/user, provider, model, request_type, tokens, costs, latency_ms, ttft_ms, finish_reason, status, error_message, timestamps, prompt/completion text, agent_name, parent_span_id. Drops org/workspace/api_key_id vault resolution, IDE-metadata detection, KMS field encryption. |
| Legacy `POST /ingest` in `api/main.py` | **ENTERPRISE** | Calls `waste_engine`, `cache_simulator`, `audit_trail` inline on every request — not used as the OSS reference. |

## 4. API / Backend Routes

| Component | Classification | Notes |
|---|---|---|
| Auth (register/login/logout, API keys) | **OSS (simplified)** | Enterprise's `AuthState`/`roles.py` carries a 7-value role enum + org/team/tenant/workspace ids baked in from the start — not ported. OSS auth is plain email/password + JWT/API-key, one implicit tenant. |
| Traces read API (`/api/traces`, `/api/traces/{id}`) | **OSS** | Same query shape, OSS column set only. |
| Playground (`/v1/playground/run`) | **OSS (trimmed)** | Provider/model/prompt in, tokens/cost/latency/trace out. Drops the 11-pipeline "Optimization Summary" breakdown (product IP). |
| Basic agent tracing (`AgentSpanIngest`/`AgentSpan` shape from `agent_observability.py`) | **OSS (trimmed)** | Keeps span_id/trace_id/parent_span_id/agent_id/agent_name/step_type/tokens/cost/latency/status. Drops OTel ingestion, session-graph, cost-breakdown/failure-point/tool-usage analytics. |
| Cost estimation (`pricing_manager.py`'s `_DEFAULTS`/`get()`) | **OSS (trimmed)** | Already degrades cleanly with no ClickHouse dependency — copied as the OSS cost-estimation utility. `finops_engine.py`/`quota_engine.py`/`cost_predictor_v2.py` (advanced recs/budgets/prediction) not ported. |
| Governance/RBAC/SSO/orgs (`policy_engine.py`, `sso_oidc.py`, `roles.py`, `orgs.py`, `org_admin.py`, `org_policy.py`, `approvals.py`, `quota_engine.py`, `invites.py`, `webhooks.py`, `audit.py`) | **ENTERPRISE** | No core-observation logic found buried in any of these — clean boundary. |
| Token lineage (`token_lineage.py`), agent registry/budgets (`agent_registry.py`), RAG observability (`rag_observability.py`) | **ENTERPRISE** | Explicitly framed (in Enterprise's own docstrings) as proving cost reductions to enterprise customers / budget-and-approval governance / advanced retrieval analytics. No basic subset worth carving out. |
| Security scan-and-mask (`SecretsScanner`+`AnonymizeScanner`, `sanitize_for_persist` shape) | **PARTIAL** | The narrow "mask secrets/PII before writing a trace" behavior is a reasonable OSS candidate (reimplemented simply); the tenant-policy/block/allow decision engine and ClickHouse-backed stats dashboard are Enterprise. |
| Encryption at rest (`encryption.py`), traffic guard (`anthropic_traffic_guard.py`) | **ENTERPRISE** | Multi-tenant KMS key management and shared-egress-IP cooldown logic — not applicable to single-tenant OSS. |

## 5. Optimization

| Component | Classification | Notes |
|---|---|---|
| All 18 stages in `compression_features.py` (delta_mode, structure_map, smart_crusher, code_compressor, tool_output_overflow, ccr, image_optimization, etc.) | **ENTERPRISE** | Core product IP. None ported. |
| Repeated-content collapse | **OSS (new, standalone)** | The one optimization stage in OSS, per product decision. Reimplemented from scratch as a small pure function — not copied from Enterprise's coupled `_collapse_repeated_phrases`. |
| Runtime modes (bypass/observe/optimize) | **Historical reference only** | Enterprise built this (commit `3cc2dae`) and deliberately deleted it (commit `da0ef21`) — "the source of the 0%-savings confusion" for paying customers. Confirms OSS should default to near-zero optimization rather than a togglable mode. |

## 6. Dashboard

| Component | Classification | Notes |
|---|---|---|
| `components/ui/` design system, `components/ui/runtime/` (BeforeAfterRequest, TokenTransformation, TraceSummary, RuntimeJourney, ProviderInfo, PrivacySummary) | **OSS (verbatim)** | Verified zero enterprise coupling — the answer to "same visual quality, not a lite demo." |
| `TraceTable.tsx` | **OSS (verbatim)** | Already basic-observation only. |
| `TraceDetail.tsx` | **OSS (trimmed)** | Keeps Execution Trace, Cost Summary, Prompt/Completion. Drops `Tenant`/`Team`/`Developer` rows and optimization-breakdown/pipeline-stage-report sections (replaced with one "Repeated Content Collapsed: N tokens" line). |
| `RequestJourneyPlayground.tsx` | **OSS (trimmed)** | Keeps provider/model picker, prompt input, Trace Summary, Before/After, Cost & Savings, Provider Info. Drops the 11-pipeline Optimization Summary section. |
| Overview/dashboard tab | **PARTIAL** | Core KPIs/spend chart/recent traces are OSS; `EnterpriseOptimizationPanel` and "Team Spend" block are not. |
| Sessions, RAG, Prompts, Executive, Governance, Reports, Projects, Infrastructure, VS Code, Teams & Integrations tabs | **ENTERPRISE** | Already gated behind `EnterpriseGate`/`isEnterprise()` in the current code. |
| FinOps, Optimization, Intelligence, Quality, Runtime, Context Engineering tabs | **ENTERPRISE (gap noted)** | Not UI-gated today despite depending on enterprise-only-registered backend routers — a real inconsistency in Enterprise's own code, irrelevant to OSS since none of this is ported. |
| Auth pages (login/register) | **OSS (simplified)** | No SSO button, no org/team selection branch, no role-based tab filtering. |

## 7. Deployment

| Component | Classification | Notes |
|---|---|---|
| ClickHouse schema (`clickhouse/init.sql`) | **OSS (column projection)** | Base `llm_events` columns only (trace/span/tenant/project/feature/user, provider, model, request_type, tokens, costs, latency, finish_reason, status, error, timestamps) + prompt/completion text + agent_name/parent_span_id. All later-added optimization/governance columns excluded. |
| AWS Secrets Manager dependency, hardcoded `cloudangles`/`brewcontent`/`codebenders` tenant defaults, `tokensguru.ai`/`tokensight.ai` domain fallbacks | **Excluded from OSS** | Found hardcoded across API/dashboard/middleware/VS Code extension in Enterprise. OSS `.env.example` uses generic placeholders only. |
| Postgres, Redis | **Not in OSS stack** | No RBAC/orgs/teams/approvals/quotas to justify them — ClickHouse only. |

## 8–20 (Governance, Security, Privacy, FinOps, Agent tracing, Token lineage, Integrations, Tests, etc.)

Covered inline within sections above per the actual audit scope — see sections
2–7. No additional OSS-appropriate subset was found in Governance, Token Lineage,
or Agent Registry beyond what's listed.
