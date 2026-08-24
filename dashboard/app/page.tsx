"use client";

import { useQuery } from "@tanstack/react-query";
import { RequireAuth } from "@/components/RequireAuth";
import { fetchSpendSummary, fetchTraces } from "@/lib/api";
import { fmtTokens, fmtCost, fmtLatency, relativeTime } from "@/lib/format";
import { Card, CardHeader, StatTile, EmptyState, SectionHeading, Badge } from "@/components/ui";

export default function OverviewPage() {
  return (
    <RequireAuth>
      <Overview />
    </RequireAuth>
  );
}

function Overview() {
  const summary = useQuery({ queryKey: ["spend-summary"], queryFn: fetchSpendSummary });
  const traces = useQuery({ queryKey: ["traces", 10], queryFn: () => fetchTraces(10) });

  return (
    <div className="flex flex-col gap-8">
      <div>
        <SectionHeading>Overview</SectionHeading>
        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatTile
            label="Requests"
            value={fmtTokens(summary.data?.requests ?? 0, true)}
            tone="brand"
          />
          <StatTile
            label="Input Tokens"
            value={fmtTokens(summary.data?.input_tokens ?? 0)}
            tone="info"
          />
          <StatTile
            label="Output Tokens"
            value={fmtTokens(summary.data?.output_tokens ?? 0)}
            tone="info"
          />
          <StatTile
            label="Est. Cost"
            value={fmtCost(summary.data?.total_cost_usd)}
            tone="success"
          />
        </div>
      </div>

      <div>
        <CardHeader title="Recent traces" description="Latest LLM requests across all providers." />
        <Card padding="none">
          {traces.isLoading ? (
            <div className="p-6 text-sm text-fg-muted">Loading…</div>
          ) : !traces.data || traces.data.length === 0 ? (
            <EmptyState
              title="No traces yet"
              description="Send a request via the SDK or try the Playground."
            />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-fg-muted">
                  <th className="px-4 py-3">Trace</th>
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Tokens</th>
                  <th className="px-4 py-3">Cost</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">When</th>
                </tr>
              </thead>
              <tbody>
                {traces.data.map((t) => (
                  <tr key={t.event_id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-mono text-xs text-fg-muted">{t.trace_id}</td>
                    <td className="px-4 py-3">
                      <Badge tone="neutral">{t.provider}</Badge> {t.model}
                    </td>
                    <td className="px-4 py-3 font-mono">{fmtTokens(t.total_tokens, true)}</td>
                    <td className="px-4 py-3 font-mono">{fmtCost(t.total_cost_usd)}</td>
                    <td className="px-4 py-3 font-mono">{fmtLatency(t.latency_ms)}</td>
                    <td className="px-4 py-3">
                      <Badge tone={t.status === "success" ? "success" : "danger"}>{t.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-fg-subtle">{relativeTime(t.request_timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
