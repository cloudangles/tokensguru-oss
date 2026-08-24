# TokensGuru OSS

Open-source observability for LLM applications: instrument your calls, track tokens/cost/latency per request, and inspect traces in a self-hosted dashboard.

TokensGuru OSS is the open-core subset of TokensGuru: a self-hosted, single-tenant way to see exactly what your LLM calls cost, in tokens and dollars, without sending your traffic through anyone else's service.

## What it does

- **SDKs** (Python, Node) wrap your LLM client calls, time each request, and export a trace event — no code changes to your prompts or logic.
- **API** (FastAPI) ingests those events, runs one lightweight optimization stage (repeated-content collapse), and stores them in ClickHouse.
- **Dashboard** (Next.js) shows traces, cost, and token usage across providers, plus a request playground.

```
Your app -> SDK -> API (ingest) -> ClickHouse -> Dashboard
```

## Scope

This is the OSS edition: single-tenant, self-hosted, focused on observation (traces, tokens, cost, latency). It does not include multi-tenant org/team management, RBAC/SSO, budget approvals, or the advanced prompt-optimization/caching pipeline — those are part of TokensGuru's hosted/enterprise offering.

## Supported providers

OpenAI, Anthropic, Groq, DeepSeek, Gemini, Ollama, OpenRouter, Together.

## Repo layout

| Path | Contents |
|---|---|
| `sdk/python`, `sdk/node` | Instrumentation SDKs (`tokensight-oss` on PyPI/npm) |
| `api` | FastAPI ingest/auth/traces/playground service |
| `dashboard` | Next.js dashboard |
| `clickhouse` | Schema (`init.sql`) for the events table |
| `tests`, `examples` | Test suite and usage examples |

## Quick start

Create a `.env` file in the repo root with at least:

```
CLICKHOUSE_PASSWORD=changeme
JWT_SECRET=changeme
# plus whichever provider keys you use, e.g.:
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
```

Then:

```bash
docker compose up --build
```

- API: http://localhost:8000
- Dashboard: http://localhost:3000

## License

TBD.
