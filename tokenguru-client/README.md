# tokenguru-client

Python client for TokenGuru chat, automatic prompt optimization, cost telemetry,
and LangChain/LangGraph tracing. The package has no required runtime dependencies.

## Install from the source repository

Users do not need to clone the complete repository. Install the SDK directly
from the public TokensGuru OSS repository:

```bash
python -m pip install --upgrade \
  "tokenguru-client @ git+https://github.com/cloudangles/tokensguru-oss.git@main#subdirectory=tokenguru-client"
```

The repository must be public, or the developer must have Git credentials for
it. Avoid putting a personal access token directly in the command or saving it
in requirements files.

The command above installs from the public `main` branch. After publishing a
release tag, replace `main` with that tag so every developer installs the same
immutable SDK source.

Verify the installation:

```bash
python -c "import tokenguru_client as tg; print(tg.__version__)"
```

The command should print `0.1.0`.

Projects can pin the same Git release in `requirements.txt`:

```text
tokenguru-client @ git+https://github.com/cloudangles/tokensguru-oss.git@main#subdirectory=tokenguru-client
```

## Install from a local checkout

```bash
pip install --upgrade ./tokenguru-client
python -c "import tokenguru_client as tg; print(tg.__version__)"
```

Once this release is published to PyPI or a private Python package registry,
the shorter installation command will be
`pip install --upgrade tokenguru-client==0.1.0`.

## Connect and chat

```python
import tokenguru_client as tg

tg.connect("http://localhost", "tsg_your_token")

response = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Summarize the deployment plan."},
    ],
)

print(response.choices[0].message.content)
print(response.tokensight.optimization.tokens_before)
print(response.tokensight.optimization.tokens_after)
print(response.tokensight.optimization.input_cost_before_usd)
print(response.tokensight.optimization.input_cost_after_usd)
print(response.tokensight.optimization.input_cost_saved_usd)
print(response.tokensight.optimization.status)
print(response.tokensight.trace_id)
print(response.tokensight.prompt_optimizer.techniques_applied)
for step in response.tokensight.prompt_optimizer.steps:
    print(step.role, step.tokens_before, "->", step.tokens_after)
    print(step.input)
    print(step.output)
```

## Saved prompts and template variables

Use `tg.prompts.list()` to browse accessible prompts or
`tg.prompts.get_active_version(prompt_id)` to load the selected version. The
SDK associates later calls with that prompt/version for trace attribution, but
does not add the prompt text to `messages` or replace `{{variable}}` values for
you. Render placeholders in your application, then pass the rendered system
and user messages to `tg.chat.completions.create()`.

[`prompt_template_example.py`](prompt_template_example.py) is a complete example
with a missing-variable check and an actual gateway call. For authoring advice,
optimizer choices, and extension points, see the
[prompt templates and optimizers guide](https://gitlab.cloudangles.com/tokensguru/TokenSight/-/blob/main/docs/prompt-templates-and-optimizers.md).

`optimization.status == "no_safe_reduction"` means the optimizer ran but the
prompt was already compact. It is different from `enabled == false`; TokenGuru
does not invent savings or shorten tool/JSON contracts when no safe reduction
is available.

Input optimization is enabled by default. The gateway optimizes the messages
before calling the selected LLM and stores the measured values with the trace:

- input tokens before and after optimization
- input tokens saved and savings percentage
- input cost before and after optimization
- input cost saved
- optimization stages that produced savings
- exact per-message before/after transformations, stored in MongoDB as
  `prompt_optimization.steps` and shown under Observability → Traces → Optimization flow
- the `trace_id`, so you can search for this exact run in Observability → Traces
- provider input/output tokens, cost, latency, model, and trace hierarchy

For tool-using agents, plain-text tool results are preserved by default because
repeated output can represent repeated events or evidence. If your agent's tool
outputs are safe to deduplicate, opt in globally with
`tg.connect(url, token, optimize_tool_outputs=True)` or override the setting on
an individual model call with `optimize_tool_outputs=True`. This applies the same exact-repeat checks to
string-valued `role="tool"` messages before the next model request. Assistant
tool-call arguments and structured/non-string outputs remain unchanged. Tool
schemas remain unchanged unless `active_tool_names` is explicitly supplied.
The optimization step appears in the trace with role `tool`.

```python
response = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=agent_history,  # includes the latest tool result
    optimize_tool_outputs=True,
)
```

### Multi-step agent optimizers

The gateway reports an estimated token breakdown by message role, repeated
tool-call signatures, and whether safe reductions reached the target of at
least 10 tokens and 50% of estimated request tokens. Token counts are estimates
and provider tokenizers can differ. Requests without enough exact redundancy
remain mostly unchanged. The SDK does not summarize or remove unique history to
force the target because that can change agent behavior.

If your agent has already selected the tools available for its current step,
pass that explicit allowlist to omit unrelated schemas from this request:

```python
response = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=agent_history,
    tools=all_tool_schemas,
    active_tool_names=["search_docs", "read_file"],
)
```

Only pass names that are valid for the current agent step. The selected list is
what the model receives, so an incomplete list can prevent a tool call.

For repeat calls to deterministic, read-only tools during one agent run, use a
per-run cache in the tool dispatcher:

```python
tool_cache = tg.ReadOnlyToolCache({"search_docs", "read_file"})
result = tool_cache.call(
    "search_docs",
    {"query": query},
    lambda: search_docs(query),
)
```

Do not include tools that write data, depend on changing state, or have side
effects. Create a new cache per agent run and call `tool_cache.clear()` when its
underlying data changes. Repeated tool-call diagnostics appear in
`response.tokensight.prompt_optimizer.agent_optimizers`; they do not suppress
calls automatically.

Use `optimize=False` only when you intentionally need an unoptimized input
baseline:

```python
baseline = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    optimize=False,
)
```

`optimize=False` disables the input token optimizer for that call. Tenant
runtime policy still controls security, routing, caching, and output handling.

## Run the package example and inspect its trace

From the repository root, install the local package in editable mode and run
the example with your TokenGuru URL and developer token:

```bash
python -m pip install -e ./tokenguru-client
TOKENGURU_URL=http://localhost TOKENGURU_API_KEY=tsg_your_token python tokenguru-client/example.py
```

The example includes an exact repeated system-prompt sentence so the local
optimizer can demonstrate a safe reduction. It prints the resulting `trace_id`
and token savings. In TokenGuru, open **Observability → Traces**, search for
that ID, open the trace, then inspect **Optimization flow** for each
system/user message's before-and-after text and applied techniques. If the
trace reports `no_safe_reduction`, the call is still recorded; it means the
optimizer found no safe exact-repeat reduction.

To exercise a model call that follows a tool result, run the agent example:

```bash
TOKENGURU_URL=http://localhost TOKENGURU_API_KEY=tsg_your_token python tokenguru-client/agent_example.py
```

It records one tool step and one model call. The synthetic tool result repeats
an exact paragraph so the `tool` optimization step should show a reduction.
Search the printed trace ID in **Observability → Traces** to inspect it.

## LangChain and LangGraph

`tg.connect()` installs the LangChain callback hook automatically. Set
`optimize_tool_outputs=True` in `tg.connect()` to enable tool-result checks on
all calls made through the SDK. In a custom
`BaseChatModel`, pass the LangChain run identifiers so the gateway LLM span is
attached to the correct graph node:

```python
from tokenguru_client.langchain import handler_parent

trace_ids = {}
if run_manager is not None:
    trace_ids = {
        "tg_span_id": str(run_manager.run_id),
        "tg_parent_id": handler_parent(run_manager),
    }

response = tg.chat.completions.create(
    model=model,
    messages=payload,
    temperature=0.2,
    max_tokens=500,
    optimize_tool_outputs=True,
    **trace_ids,
)
```

No additional optimizer call is needed. Calling the optimizer separately would
optimize the same prompt twice; `chat.completions.create()` sends one request to
the gateway, which optimizes, calls the LLM, and records the result.

## Configuration

Use `tg.connect(url, token)`, or set `TOKENGURU_TRACKING_URI` and
`TOKENGURU_API_KEY`. The lower-level `request(method, path, body)` helper can
call other TokenGuru endpoints.

## Local development

```bash
pip install -e ./tokenguru-client
python -m unittest discover -s tokenguru-client/tests -v
```
