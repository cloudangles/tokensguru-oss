"use client";

import { fmtTokens } from "@/lib/format";

export interface ProviderInfoProps {
  provider?: string;
  model?: string;
  method?: string;
  requestId?: string;
  latencyMs?: number;
  inputTokens?: number;
  outputTokens?: number;
  responseText?: string;
  finishReason?: string;
  /** Set when no real call happened — renders the honest skipped state
   * instead of anything invoked-looking. */
  skipReason?: string | null;
}

function fmtMs(ms: number | undefined): string {
  if (ms == null) return "—";
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`;
}

export function ProviderInfo(props: ProviderInfoProps) {
  if (props.skipReason || !props.provider) {
    return (
      <div className="rounded-lg border border-line bg-surface/40 p-3 text-[11px] text-fg-faint">
        Provider not invoked — {props.skipReason || "no provider call was made"}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-success/25 bg-success/5 p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-fg-muted">
        <span>
          <span className="text-fg-faint">Provider </span>
          <span className="font-mono font-semibold text-fg">{props.provider}</span>
        </span>
        <span>
          <span className="text-fg-faint">Model </span>
          <span className="font-mono font-semibold text-fg">{props.model || "—"}</span>
        </span>
        {props.method && (
          <span>
            <span className="text-fg-faint">Method </span>
            <span className="font-mono text-fg">{props.method}</span>
          </span>
        )}
        <span>
          <span className="text-fg-faint">Latency </span>
          <span className="font-mono text-fg">{fmtMs(props.latencyMs)}</span>
        </span>
        {(props.inputTokens != null || props.outputTokens != null) && (
          <span className="font-mono text-fg">
            {fmtTokens(props.inputTokens ?? 0, true)} in / {fmtTokens(props.outputTokens ?? 0, true)} out
          </span>
        )}
      </div>
      {props.requestId && (
        <span className="truncate font-mono text-[10px] text-fg-faint" title={props.requestId}>
          request_id: {props.requestId}
        </span>
      )}
      {/* Response kept visually secondary — the differentiator here is what
       * happened before the model, not the chat reply itself. */}
      {props.responseText && (
        <details className="mt-1">
          <summary className="cursor-pointer text-[10px] font-semibold uppercase tracking-wider text-fg-faint">
            Response
          </summary>
          <p className="mt-1.5 whitespace-pre-wrap text-[11px] text-fg-muted">{props.responseText}</p>
        </details>
      )}
    </div>
  );
}
