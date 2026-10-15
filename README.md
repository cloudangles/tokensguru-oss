<p align="center">
  <img src="media/tokenguru-logo.svg" alt="TokensGuru logo" />
</p>

<p align="center">
  <a href="https://github.com/cloudangles/tokensguru-oss"><img src="https://img.shields.io/badge/version-0.1.0-6f42c1?style=for-the-badge" alt="Version 0.1.0" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9 and later" /></a>
  <img src="https://img.shields.io/badge/runtime_dependencies-none-2ea44f?style=for-the-badge" alt="No required runtime dependencies" />
  <img src="https://img.shields.io/badge/status-beta-orange?style=for-the-badge" alt="Beta" />
</p>

<p align="center">
  <strong>Observe LLM calls. Optimize prompts safely. Understand agent behavior.</strong>
</p>

TokensGuru is an open-source Python client for sending model requests through a TokensGuru service. The service can optimize eligible prompt content before forwarding a request to its configured model provider, then record the request, optimization results, token and cost measurements, and trace information for inspection.

The SDK is intentionally lightweight and has no required runtime dependencies. It provides a familiar chat-completions interface, connects agent and tool activity into traces, and returns optimization details with the model response.

> **Current package version: `0.1.0`** — this is an early beta release. The version shown here matches `tokenguru-client/pyproject.toml` and the SDK. The repository does not currently declare a `1.0.0` release.

## Contents

- [What you get](#what-you-get)
- [How it works](#how-it-works)
- [Install](#install)
- [Connect and make a request](#connect-and-make-a-request)
- [Inspect optimization and traces](#inspect-optimization-and-traces)
- [Trace agent workflows](#trace-agent-workflows)
- [Optional tool-output optimization](#optional-tool-output-optimization)
- [Architecture direction](#architecture-direction)
- [Who TokensGuru is for](#who-tokenguru-is-for)
- [Development](#development)
- [License](#license)

## What you get

- **A simple Python client:** connect to your TokensGuru service and make chat-completion requests using `tokenguru_client`.
- **Gateway-backed prompt optimization:** requests are evaluated by the service before the provider call. The response reports before-and-after token and input-cost measurements when available.
- **Trace visibility:** associate model calls, application spans, tools, and agent runs with trace and span identifiers. LangChain and LangGraph integrations can attach model and tool activity to a shared trace.
- **Conservative tool-output handling:** plain-text tool results are preserved by default. You can explicitly opt in to exact-repeat cleanup when your workflow allows it.
- **Prompt attribution:** load an active prompt version and associate subsequent calls with that prompt in trace data.
- **Read-only tool-call caching:** optionally memoize repeated calls to explicitly selected read-only tools during an agent run.
- **Self-hosted service connection:** point the SDK at the TokensGuru service URL configured for your environment.

TokensGuru measures optimization results rather than promising a fixed savings rate. If a request has no safe, useful reduction, the service can leave it unchanged and report that no safe reduction was found.

## How it works

```text
Your Python app or agent
          │
          ▼
   tokenguru-client ───────► TokensGuru service ───────► Configured model provider
          │                          │
          │                          ├─ evaluates eligible prompt optimizations
          │                          ├─ records usage, cost, and latency data
          │                          └─ stores trace and optimization details
          │
          └──────── response with model output and TokensGuru measurements
```

The client sends requests to the TokensGuru service, which handles the provider request and optimization. Your application uses the returned model response as usual and can inspect the accompanying `tokensight` metadata. A running TokensGuru service and a valid developer API key are required; installing this Python package alone does not provide a model gateway or provider credentials.

## Install

Install the package directly from this repository's `main` branch:

```bash
python -m pip install --upgrade \
  "tokenguru-client @ git+https://github.com/cloudangles/tokensguru-oss.git@main#subdirectory=tokenguru-client"
```

Set the service URL and developer API key in your environment. Use the URL and key provided for your TokensGuru deployment:

```bash
export TOKENGURU_TRACKING_URI="http://localhost"
export TOKENGURU_API_KEY="tsg_your_token"
```

Check the installed version:

```bash
python -c "import tokenguru_client as tg; print(tg.__version__)"
```

The command currently prints `0.1.0`. For a repeatable production install, pin the Git dependency to a release tag once you have selected or published one. Do not put private access tokens in install commands, source files, or committed requirements files.

## Connect and make a request

```python
import os
import tokenguru_client as tg

# Connect to your TokensGuru service and authenticate with your developer key.
tg.connect(
    os.environ.get("TOKENGURU_TRACKING_URI", "http://localhost"),
    os.environ["TOKENGURU_API_KEY"],
)

response = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Explain prompt caching in two sentences."},
    ],
)

print(response.choices[0].message.content)
print("Trace:", response.tokensight.trace_id)
print("Optimization status:", response.tokensight.optimization.status)
print(
    "Input tokens:",
    response.tokensight.optimization.tokens_before,
    "→",
    response.tokensight.optimization.tokens_after,
)
print("Input cost saved:", response.tokensight.optimization.input_cost_saved_usd)
```

The chat-completions call uses the gateway configured for your TokensGuru service. The service must have access to the selected provider and model. The SDK accepts the regular `model` and `messages` arguments plus provider parameters supported by the service.

## Inspect optimization and traces

A response can include:

- A trace ID for finding the request in your TokensGuru dashboard.
- The optimization status and applied techniques.
- Input token counts before and after optimization.
- Estimated input cost before and after optimization, and the difference.
- Per-message transformation steps, where available.
- Provider usage, model, latency, and trace hierarchy recorded by the service.

Use the trace ID in the dashboard to review the request and its optimization details. Token counts are estimates and may differ from provider-reported tokenizer counts. Savings depend on the request and the enabled service configuration; the SDK does not promise that every request will be shortened.

### Prompt versions

You can load an active prompt version for attribution in subsequent request traces:

```python
prompt = tg.prompts.get_active_version("your-prompt-id")
print(prompt["name"], prompt["version_id"])

# Render any template variables in your application, then send the messages.
response = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "Your rendered prompt text"},
        {"role": "user", "content": "A user request"},
    ],
)
```

Prompt loading associates the prompt and version with later traces; it does not render template variables or replace message content for you.

## Trace agent workflows

Use `tg.trace()` and `tg.span()` to group application steps and model calls. The SDK can also attach LangChain and LangGraph activity automatically after `tg.connect()` when the relevant integration is installed in your application.

```python
import tokenguru_client as tg

tg.connect("http://localhost", "tsg_your_token")

with tg.trace("support-agent", input={"question": "Where is my order?"}) as run:
    with tg.span("retrieve-order"):
        order = lookup_order("order-123")

    response = tg.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": f"Summarize this order: {order}"},
        ],
    )

print("Trace:", run.trace_id)
print(response.choices[0].message.content)
```

For custom agent loops, use explicit spans to describe tool and application work. See [`tokenguru-client/README.md`](tokenguru-client/README.md) for LangChain/LangGraph setup, tool-output options, prompt templates, and complete examples.

### Optional tool-output optimization

Tool results are preserved by default. If repeated plain-text tool output is safe to deduplicate in your application, opt in for all calls after connecting:

```python
tg.connect(
    "http://localhost",
    "tsg_your_token",
    optimize_tool_outputs=True,
)
```

Or enable it for one request with `optimize_tool_outputs=True`. Structured results, assistant tool-call arguments, and tool schemas are not generally rewritten by this option. Only provide `active_tool_names` when your agent has already chosen the tools allowed for that request.

For repeated pure read-only tool calls, `tg.ReadOnlyToolCache` offers local memoization. Use a new cache for each agent run, and do not cache tools that write data, depend on changing state, or have side effects.

## Architecture direction

The attached Intelligent Layer design describes how TokensGuru can grow into a decision engine that coordinates request analysis and optimizer plugins. Its guiding flow is:

```text
Normalize request
  → extract content and task signals
  → combine evidence and apply policy
  → select eligible optimizers
  → plan dependencies
  → validate transformations
  → measure results and forward the request
```

The design calls for structured parsing of messages and content blocks; deterministic signals for code, errors, repeated content, and oversized context; optional semantic analysis for ambiguous cases; policy-aware optimizer selection; dependency-aware execution; and validation with rollback or fallback when a transformation is unsafe.

The document also discusses techniques such as hashing for exact duplicates, MinHash or SimHash for near-duplicates, BM25 or embeddings for relevance, Tree-sitter for code structure, and optional prompt-compression components. These are architecture options, not a claim that every technique or optimizer is implemented in this client release. The current package exposes the client, tracing, prompt attribution, and gateway optimization controls described above; the service determines which optimization stages are available and enabled.

## Who TokensGuru is for

TokensGuru is for developers and teams who want to:

- See how LLM requests affect token usage, input cost, and latency.
- Inspect individual requests and agent traces during development and operations.
- Put a consistent service boundary between application code and configured model providers.
- Evaluate prompt optimization with before-and-after measurements.
- Add observability to Python, LangChain, or LangGraph workflows without wiring every trace field by hand.
- Operate the service in an environment they control.

For production deployments, configure authentication, provider access, data retention, and network controls in the TokensGuru service and its hosting environment. The SDK does not replace those deployment responsibilities.

## Development

Clone the repository and install the client in editable mode:

```bash
git clone https://github.com/cloudangles/tokensguru-oss.git
cd tokensguru-oss
python -m pip install -e ./tokenguru-client
```

Examples are available in [`tokenguru-client/`](tokenguru-client/), including a basic request, an agent workflow, and prompt-template usage. For package-specific configuration and local development notes, see the [client README](tokenguru-client/README.md).

## License

This checkout does not currently include a `LICENSE` file. Add the project's license terms before redistributing the code.
