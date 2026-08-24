"use client";

export interface TraceSummaryProps {
  traceId: string;
  sessionId?: string;
  spanId?: string;
  eventId?: string;
  tenantId?: string;
  timestamp?: string;
  provider?: string;
  model?: string;
  latencyMs?: number;
  /** Real trace only once actually written — never claim persistence that
   * didn't happen (e.g. a Playground dry run). */
  persisted?: boolean;
}

function Field({ label, value, mono = true }: { label: string; value?: string | number; mono?: boolean }) {
  if (value == null || value === "") return null;
  return (
    <span className="flex items-baseline gap-1">
      <span className="text-fg-faint">{label}</span>
      <span className={mono ? "truncate font-mono text-fg" : "truncate text-fg"} title={String(value)}>
        {value}
      </span>
    </span>
  );
}

export function TraceSummary(props: TraceSummaryProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-line bg-surface/40 px-3 py-2 text-[11px] text-fg-muted">
      <Field label="trace" value={props.traceId.length > 20 ? `${props.traceId.slice(0, 16)}…` : props.traceId} />
      {props.sessionId && <Field label="session" value={props.sessionId.slice(0, 16)} />}
      {props.spanId && <Field label="span" value={props.spanId.slice(0, 12)} />}
      {(props.provider || props.model) && (
        <Field label="" mono={false} value={[props.provider, props.model].filter(Boolean).join(" / ")} />
      )}
      {props.latencyMs != null && <Field label="" value={`${props.latencyMs.toFixed(0)}ms`} />}
      {props.timestamp && <Field label="" mono={false} value={props.timestamp} />}
      {props.tenantId && <Field label="tenant" value={props.tenantId} />}
      {props.persisted && <span className="font-semibold text-brand">Persisted — real trace recorded</span>}
    </div>
  );
}
