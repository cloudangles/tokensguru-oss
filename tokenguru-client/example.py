import os

import tokenguru_client as tg

tg.connect(os.environ.get("TOKENGURU_URL", "http://localhost"), os.environ["TOKENGURU_API_KEY"])
resp = tg.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful, concise assistant. Preserve every deployment requirement exactly as supplied. Preserve every deployment requirement exactly as supplied."},
        {"role": "user", "content": "Please explain what token optimization is in a short and concise way."},
    ],
    optimize=True,
)
print(resp.choices[0].message.content)

opt = resp.tokensight.optimization
print(f"input tokens: {opt.tokens_before} -> {opt.tokens_after}; saved={opt.tokens_saved}")
print(f"trace id: {resp.tokensight.trace_id}")
print("Open Observability → Traces and search for this trace ID to inspect Optimization flow.")
for step in resp.tokensight.prompt_optimizer.steps:
    print(f"[{step.role}] {step.tokens_before} -> {step.tokens_after}: {', '.join(step.techniques)}")
    print("before:", step.input)
    print("after: ", step.output)
