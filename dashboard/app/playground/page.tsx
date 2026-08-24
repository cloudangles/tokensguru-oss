"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { runPlayground, type PlaygroundRunResult } from "@/lib/api";
import { Button, Card, SectionHeading } from "@/components/ui";
import { TraceSummary } from "@/components/ui/runtime/TraceSummary";
import { BeforeAfterRequest } from "@/components/ui/runtime/BeforeAfterRequest";
import { TokenTransformation } from "@/components/ui/runtime/TokenTransformation";
import { ProviderInfo } from "@/components/ui/runtime/ProviderInfo";
import { fmtCost, fmtLatency } from "@/lib/format";

const PROVIDERS = [
  { id: "openai", label: "OpenAI", defaultModel: "gpt-4o-mini" },
  { id: "anthropic", label: "Anthropic", defaultModel: "claude-haiku-4-5" },
  { id: "groq", label: "Groq", defaultModel: "llama-3.1-8b-instant" },
  { id: "deepseek", label: "DeepSeek", defaultModel: "deepseek-chat" },
  { id: "google", label: "Google Gemini", defaultModel: "gemini-2.5-flash" },
  { id: "openrouter", label: "OpenRouter", defaultModel: "anthropic/claude-3.5-sonnet" },
  { id: "together", label: "Together AI", defaultModel: "meta-llama/Llama-3-70b-chat-hf" },
  { id: "ollama", label: "Ollama (self-hosted)", defaultModel: "llama3.1" },
];

export default function PlaygroundPage() {
  return (
    <RequireAuth>
      <Playground />
    </RequireAuth>
  );
}

function Playground() {
  const [provider, setProvider] = useState(PROVIDERS[0].id);
  const [model, setModel] = useState(PROVIDERS[0].defaultModel);
  const [prompt, setPrompt] = useState("");
  const [invokeProvider, setInvokeProvider] = useState(true);
  const [result, setResult] = useState<PlaygroundRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await runPlayground({ provider, model, prompt, invoke_provider: invokeProvider });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div>
        <SectionHeading>Playground</SectionHeading>
        <Card className="flex flex-col gap-4">
          <div className="flex gap-3">
            <select
              value={provider}
              onChange={(e) => {
                const p = PROVIDERS.find((x) => x.id === e.target.value)!;
                setProvider(p.id);
                setModel(p.defaultModel);
              }}
              className="h-10 flex-1 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg"
            >
              {PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="model"
              className="h-10 flex-1 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg"
            />
          </div>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter a prompt…"
            rows={10}
            className="rounded-lg border border-line bg-surface-2 p-3 font-mono text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />

          <label className="flex items-center gap-2 text-sm text-fg-muted">
            <input
              type="checkbox"
              checked={invokeProvider}
              onChange={(e) => setInvokeProvider(e.target.checked)}
            />
            Invoke provider (real, billed call)
          </label>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button variant="primary" loading={busy} disabled={!prompt} onClick={run}>
            Run TokenSight
          </Button>
        </Card>
      </div>

      <div>
        <SectionHeading>Result</SectionHeading>
        {!result ? (
          <Card>
            <p className="p-4 text-center text-sm text-fg-muted">
              Run a request to see tokens, cost, latency, and the trace.
            </p>
          </Card>
        ) : (
          <div className="flex flex-col gap-4">
            <Card>
              <TraceSummary
                traceId={result.trace_id}
                spanId={result.span_id}
                provider={result.provider}
                model={result.model}
                latencyMs={result.latency_ms}
                persisted
              />
            </Card>

            <Card>
              <TokenTransformation
                original={result.input_tokens_before}
                steps={
                  result.tokens_saved > 0
                    ? [{ label: "Repeated content collapsed", saved: result.tokens_saved }]
                    : []
                }
                final={result.input_tokens}
                outputTokens={result.output_tokens}
              />
            </Card>

            <Card>
              <BeforeAfterRequest
                rows={[
                  {
                    label: "Prompt",
                    before: { value: result.original_prompt },
                    after: { value: result.optimized_prompt },
                  },
                ]}
              />
            </Card>

            <Card>
              <ProviderInfo
                provider={result.provider}
                model={result.model}
                latencyMs={result.latency_ms}
                inputTokens={result.input_tokens}
                outputTokens={result.output_tokens}
                responseText={result.completion_text}
                finishReason={result.status === "success" ? "stop" : "error"}
              />
            </Card>

            <Card>
              <div className="flex justify-between text-sm">
                <span className="text-fg-muted">Cost</span>
                <span className="font-mono text-fg-strong">
                  {fmtCost(result.input_cost_usd + result.output_cost_usd)}
                </span>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
