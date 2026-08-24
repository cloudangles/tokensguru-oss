"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RequireAuth } from "@/components/RequireAuth";
import { fetchTraces, fetchTrace, type TraceEvent } from "@/lib/api";
import { fmtTokens, fmtCost, fmtLatency, relativeTime } from "@/lib/format";
import { Card, SectionHeading, Badge, EmptyState } from "@/components/ui";
import { TraceSummary } from "@/components/ui/runtime/TraceSummary";
import { BeforeAfterRequest } from "@/components/ui/runtime/BeforeAfterRequest";
import { TokenTransformation } from "@/components/ui/runtime/TokenTransformation";

export default function TracesPage() {
  return (
    <RequireAuth>
      <Traces />
    </RequireAuth>
  );
}

function Traces() {
  const [selected, setSelected] = useState<string | null>(null);
  const traces = useQuery({ queryKey: ["traces", 100], queryFn: () => fetchTraces(100) });
  const detail = useQuery({
    queryKey: ["trace", selected],
    queryFn: () => fetchTrace(selected as string),
    enabled: !!selected,
  });

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_3fr]">
      <div>
        <SectionHeading>Traces</SectionHeading>
        <Card padding="none">
          {traces.isLoading ? (
            <div className="p-6 text-sm text-fg-muted">Loading…</div>
          ) : !traces.data || traces.data.length === 0 ? (
            <EmptyState title="No traces yet" description="Traces appear here as your app makes LLM calls." />
          ) : (
            <div className="divide-y divide-line">
              {traces.data.map((t) => (
                <button
                  key={t.event_id}
                  onClick={() => setSelected(t.trace_id)}
                  className={`w-full px-4 py-3 text-left text-sm transition-colors hover:bg-surface-2 ${
                    selected === t.trace_id ? "bg-surface-2" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-fg-muted">{t.trace_id}</span>
                    <Badge tone={t.status === "success" ? "success" : "danger"} size="sm">
                      {t.status}
                    </Badge>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-fg-subtle">
                    <span>
                      {t.provider} / {t.model}
                    </span>
                    <span>{relativeTime(t.request_timestamp)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      <div>
        <SectionHeading>Trace detail</SectionHeading>
        {!selected ? (
          <Card>
            <EmptyState title="Select a trace" description="Pick a trace on the left to see its full detail." />
          </Card>
        ) : detail.isLoading || !detail.data ? (
          <Card>
            <div className="p-6 text-sm text-fg-muted">Loading…</div>
          </Card>
        ) : (
          <TraceDetail trace={detail.data} />
        )}
      </div>
    </div>
  );
}

function TraceDetail({ trace }: { trace: TraceEvent }) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <TraceSummary
          traceId={trace.trace_id}
          spanId={trace.span_id}
          eventId={trace.event_id}
          tenantId={trace.tenant_id}
          timestamp={trace.request_timestamp}
          provider={trace.provider}
          model={trace.model}
          latencyMs={trace.latency_ms}
          persisted
        />
      </Card>

      {trace.input_tokens_before > trace.input_tokens && (
        <Card>
          <TokenTransformation
            original={trace.input_tokens_before}
            steps={[{ label: "Repeated content collapsed", saved: trace.input_tokens_saved }]}
            final={trace.input_tokens}
          />
        </Card>
      )}

      <Card>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-fg-muted">Tokens</p>
            <p className="font-mono text-lg text-fg-strong">{fmtTokens(trace.total_tokens, true)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-fg-muted">Cost</p>
            <p className="font-mono text-lg text-fg-strong">{fmtCost(trace.total_cost_usd)}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider text-fg-muted">Latency</p>
            <p className="font-mono text-lg text-fg-strong">{fmtLatency(trace.latency_ms)}</p>
          </div>
        </div>
      </Card>

      {trace.prompt_text && (
        <Card>
          <p className="mb-2 text-xs uppercase tracking-wider text-fg-muted">Prompt</p>
          <pre className="whitespace-pre-wrap break-words font-mono text-xs text-fg">{trace.prompt_text}</pre>
        </Card>
      )}
      {trace.completion_text && (
        <Card>
          <p className="mb-2 text-xs uppercase tracking-wider text-fg-muted">Completion</p>
          <pre className="whitespace-pre-wrap break-words font-mono text-xs text-fg">{trace.completion_text}</pre>
        </Card>
      )}
      {trace.error_message && (
        <Card tone="danger">
          <p className="mb-2 text-xs uppercase tracking-wider text-danger">Error</p>
          <p className="font-mono text-xs text-fg">{trace.error_message}</p>
        </Card>
      )}
    </div>
  );
}
