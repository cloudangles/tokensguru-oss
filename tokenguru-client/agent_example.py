"""Exercise tool-result optimization in a small, observable agent turn."""

import os

import tokenguru_client as tg


tg.connect(os.environ.get("TOKENGURU_URL", "http://localhost"), os.environ["TOKENGURU_API_KEY"])

tool_result = "The deployment target is the staging cluster and the release window is Tuesday morning."

with tg.trace("tool-output-optimizer-demo", input="Summarize the deployment lookup"):
    with tg.span("deployment_lookup", kind="tool", input={"query": "deployment target and release window"}) as tool:
        # Repeated paragraphs make the safe, exact-repeat pass visible in the trace.
        tool.output = f"{tool_result}\n\n{tool_result}"

    response = tg.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize tool results accurately and concisely."},
            {"role": "user", "content": "What is the deployment target and release window?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "lookup-1",
                    "type": "function",
                    "function": {"name": "deployment_lookup", "arguments": "{}"},
                }],
            },
            {"role": "tool", "tool_call_id": "lookup-1", "content": tool.output},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": "deployment_lookup",
                "description": "Look up deployment details.",
                "parameters": {"type": "object", "properties": {}},
            },
        }],
        optimize_tool_outputs=True,
    )

print(response.choices[0].message.content)
print(f"trace id: {response.tokensight.trace_id}")
for step in response.tokensight.prompt_optimizer.steps:
    print(f"[{step.role}] {step.tokens_before} -> {step.tokens_after}: {', '.join(step.techniques)}")
