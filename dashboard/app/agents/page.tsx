"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RequireAuth } from "@/components/RequireAuth";
import { fetchTraces, fetchAgentSpans } from "@/lib/api";
import { fmtTokens, fmtCost, fmtLatency } from "@/lib/format";
import { Card, SectionHeading, Badge, EmptyState } from "@/components/ui";

export default function AgentsPage() {
  return (
    <RequireAuth>
      <Agents />
    </RequireAuth>
  );
}

function Agents() {
  const [traceId, setTraceId] = useState("");
  const [lookupId, setLookupId] = useState<string | null>(null);
  const traces = useQuery({ queryKey: ["traces", 20], queryFn: () => fetchTraces(20) });
  const spans = useQuery({
    queryKey: ["agent-spans", lookupId],
    queryFn: () => fetchAgentSpans(lookupId as string),
    enabled: !!lookupId,
  });

  return (
    <div>
      <SectionHeading>Agent tracing</SectionHeading>
      <p className="mb-4 text-sm text-fg-muted">
        Basic agent visibility: request → model → tokens → latency → result, with
        parent/child span linkage. POST spans to{" "}
        <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">/api/agents/spans</code>.
      </p>

      <div className="mb-6 flex gap-2">
        <input
          value={traceId}
          onChange={(e) => setTraceId(e.target.value)}
          placeholder="Enter a trace_id to view its agent spans…"
          className="h-10 flex-1 rounded-lg border border-line bg-surface-2 px-3 text-sm text-fg"
        />
        <button
          onClick={() => setLookupId(traceId)}
          className="rounded-lg border border-line bg-surface-2 px-4 text-sm text-fg hover:bg-surface-3"
        >
          Look up
        </button>
      </div>

      {lookupId && (
        <Card padding="none" className="mb-6">
          {spans.isLoading ? (
            <div className="p-6 text-sm text-fg-muted">Loading…</div>
          ) : !spans.data || spans.data.length === 0 ? (
            <EmptyState title="No spans found" description="No agent spans recorded for this trace_id." />
          ) : (
            <div className="divide-y divide-line">
              {spans.data.map((s) => (
                <div key={s.span_id} className="flex items-center justify-between px-4 py-3 text-sm">
                  <div>
                    <p className="font-medium text-fg">{s.agent_name || s.agent_id || "agent"}</p>
                    <p className="text-xs text-fg-subtle">
                      {s.step_type} {s.step_name && `· ${s.step_name}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-fg-muted">
                    <span className="font-mono">{fmtTokens(s.input_tokens + s.output_tokens, true)} tok</span>
                    <span className="font-mono">{fmtCost(s.cost_usd)}</span>
                    <span className="font-mono">{fmtLatency(s.latency_ms)}</span>
                    <Badge tone={s.status === "success" ? "success" : "danger"} size="sm">
                      {s.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      <SectionHeading>Recent traces (click to look up)</SectionHeading>
      <Card padding="none">
        {traces.isLoading ? (
          <div className="p-6 text-sm text-fg-muted">Loading…</div>
        ) : !traces.data || traces.data.length === 0 ? (
          <EmptyState title="No traces yet" />
        ) : (
          <div className="divide-y divide-line">
            {traces.data.map((t) => (
              <button
                key={t.event_id}
                onClick={() => {
                  setTraceId(t.trace_id);
                  setLookupId(t.trace_id);
                }}
                className="block w-full px-4 py-2 text-left font-mono text-xs text-fg-muted hover:bg-surface-2"
              >
                {t.trace_id}
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
