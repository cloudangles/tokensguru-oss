"use client";

import { fmtSavedTokens, fmtTokens } from "@/lib/format";

export interface TokenTransformationStep {
  label: string;
  saved: number;
}

export interface TokenTransformationProps {
  original: number;
  /** Only stages that actually ran and actually saved something — callers
   * filter to saved > 0 before passing in. Never fabricated/estimated. */
  steps: TokenTransformationStep[];
  final: number;
  outputTokens?: number;
}

function Arrow() {
  return (
    <div className="flex justify-center py-1" aria-hidden="true">
      <svg className="h-4 w-4 text-fg-faint" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    </div>
  );
}

export function TokenTransformation({ original, steps, final, outputTokens }: TokenTransformationProps) {
  return (
    <div className="flex flex-col items-stretch gap-0 rounded-xl border border-line bg-surface/40 p-4">
      <div className="rounded-lg border border-line-strong bg-bg/60 px-4 py-3 text-center">
        <p className="text-[10px] font-bold uppercase tracking-widest text-fg-faint">Original Request</p>
        <p className="mt-1 font-mono text-2xl font-bold tabular-nums text-fg-strong">{fmtTokens(original, true)}</p>
      </div>

      <Arrow />

      <div className="rounded-lg border border-brand/20 bg-brand/5 px-4 py-3">
        <p className="mb-2 text-center text-[10px] font-bold uppercase tracking-widest text-brand">TokenSight</p>
        {steps.length === 0 ? (
          <p className="text-center text-[11px] text-fg-faint">No stage produced a real reduction on this request.</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {steps.map((s) => (
              <div key={s.label} className="flex items-center justify-between gap-3 text-[11px]">
                <span className="text-fg-muted">{s.label}</span>
                <span className="font-mono font-semibold text-success">−{fmtSavedTokens(s.saved, true)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <Arrow />

      <div className="rounded-lg border border-success/25 bg-success/5 px-4 py-3 text-center">
        <p className="text-[10px] font-bold uppercase tracking-widest text-fg-faint">Final Request</p>
        <p className="mt-1 font-mono text-2xl font-bold tabular-nums text-success">{fmtTokens(final, true)}</p>
      </div>

      {outputTokens != null && (
        <>
          <Arrow />
          <div className="rounded-lg border border-line px-4 py-2.5 text-center">
            <p className="text-[10px] font-bold uppercase tracking-widest text-fg-faint">LLM Provider</p>
            <p className="mt-1 font-mono text-sm font-semibold text-fg-muted">{fmtTokens(outputTokens, true)} output</p>
          </div>
        </>
      )}
    </div>
  );
}
