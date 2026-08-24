"use client";

import { useState } from "react";

export interface BeforeAfterRow {
  label: string;
  before: { value: string; sub?: string };
  after: { value: string; sub?: string };
}

export interface BeforeAfterRequestProps {
  rows: BeforeAfterRow[];
  /** Only pass when the caller has the real message arrays to show — e.g.
   * Playground's original_request/final_request. TraceDetail has no
   * persisted final-request messages, so it omits this rather than
   * fabricating a diff it can't produce. */
  diff?: {
    beforeMessages: unknown;
    afterMessages: unknown;
    beforeLabel: string;
    afterLabel: string;
  };
}

/** Plain text (e.g. a trace's original/optimized prompt) renders directly —
 * JSON.stringify-ing a string would show literal `\n` escapes and wrapping
 * quotes instead of readable text. Message arrays/objects (the Playground
 * dry-run case this was originally built for) keep the JSON.stringify path. */
function renderDiffContent(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        });
      }}
      className="rounded border border-line px-1.5 py-0.5 text-[10px] font-medium text-fg-faint hover:text-fg-muted"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function BeforeAfterRequest({ rows, diff }: BeforeAfterRequestProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-danger/15 bg-danger/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-danger-solid" aria-hidden="true" />
            <span className="text-xs font-bold uppercase tracking-wider text-fg-muted">Before</span>
          </div>
          <div className="flex flex-col gap-2">
            {rows.map((r) => (
              <div key={r.label} className="flex items-baseline justify-between gap-2">
                <span className="text-[11px] text-fg-faint">{r.label}</span>
                <span className="text-right font-mono text-sm font-bold text-fg-muted line-through decoration-danger/50">
                  {r.before.value}
                  {r.before.sub && <span className="ml-1 text-[10px] font-normal text-fg-faint no-underline">{r.before.sub}</span>}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-success/20 bg-success/5 p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-success-solid" aria-hidden="true" />
            <span className="text-xs font-bold uppercase tracking-wider text-success">After</span>
          </div>
          <div className="flex flex-col gap-2">
            {rows.map((r) => (
              <div key={r.label} className="flex items-baseline justify-between gap-2">
                <span className="text-[11px] text-fg-faint">{r.label}</span>
                <span className="text-right font-mono text-sm font-bold text-success">
                  {r.after.value}
                  {r.after.sub && <span className="ml-1 text-[10px] font-normal text-fg-faint">{r.after.sub}</span>}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {diff && (
        <details className="rounded-lg border border-line bg-surface/40 p-3 text-xs text-fg-muted">
          <summary className="cursor-pointer text-fg-faint">Expand {diff.beforeLabel} / {diff.afterLabel} (immutable)</summary>
          <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div>
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-fg-faint">{diff.beforeLabel}</p>
                <CopyButton text={renderDiffContent(diff.beforeMessages)} />
              </div>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-bg/60 p-2 font-mono text-[10px] text-fg-muted">
                {renderDiffContent(diff.beforeMessages)}
              </pre>
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-[10px] font-bold uppercase tracking-wider text-fg-faint">{diff.afterLabel}</p>
                <CopyButton text={renderDiffContent(diff.afterMessages)} />
              </div>
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded bg-bg/60 p-2 font-mono text-[10px] text-fg-muted">
                {renderDiffContent(diff.afterMessages)}
              </pre>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}
