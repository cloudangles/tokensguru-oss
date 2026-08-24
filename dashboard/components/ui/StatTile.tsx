"use client";

import React from "react";
import { cn } from "./cn";
import { Card } from "./Card";

/**
 * StatTile — KPI card. Standardizes the ExecutiveKPIs pattern:
 * uppercase label + icon, a large tabular-nums value, sub-caption, an optional
 * signed trend delta (with semantic direction color), and an optional progress
 * meter. Values use font-mono tabular figures to prevent layout shift.
 */
export type StatTone = "brand" | "success" | "warning" | "danger" | "info" | "neutral";

const ACCENT_TEXT: Record<StatTone, string> = {
  brand: "text-brand",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  info: "text-info",
  neutral: "text-fg-muted",
};

const METER_BG: Record<StatTone, string> = {
  brand: "bg-brand",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  neutral: "bg-fg-faint",
};

export interface StatTileProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  tone?: StatTone;
  /** Color the value itself (e.g. a signed trend metric). Defaults to strong fg. */
  valueTone?: StatTone;
  caption?: React.ReactNode;
  /** Signed % or value change. `goodDirection` sets which sign is "good". */
  delta?: { value: number; suffix?: string; goodDirection?: "up" | "down" };
  /** 0–100 progress meter. */
  meter?: { pct: number; tone?: StatTone };
  className?: string;
}

function TrendArrow({ up }: { up: boolean }) {
  return (
    <svg
      className={cn("h-4 w-4", !up && "rotate-180")}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
    </svg>
  );
}

export function StatTile({
  label,
  value,
  icon,
  tone = "brand",
  valueTone,
  caption,
  delta,
  meter,
  className,
}: StatTileProps) {
  // Resolve trend color from whether the delta moved in the "good" direction.
  let deltaNode: React.ReactNode = null;
  if (delta) {
    const up = delta.value > 0;
    const good =
      (delta.goodDirection ?? "up") === "up" ? delta.value >= 0 : delta.value <= 0;
    deltaNode = (
      <span
        className={cn(
          "inline-flex items-center gap-1 text-sm font-semibold tabular-nums",
          good ? "text-success" : "text-danger"
        )}
      >
        <TrendArrow up={up} />
        {delta.value > 0 ? "+" : ""}
        {delta.value.toFixed(1)}
        {delta.suffix ?? "%"}
      </span>
    );
  }

  const meterTone = meter?.tone ?? tone;

  return (
    <Card padding="md" className={cn("flex flex-col", className)}>
      <div className="mb-1 flex items-center gap-2">
        {icon ? <span className={ACCENT_TEXT[tone]}>{icon}</span> : null}
        <span className="text-xs font-semibold uppercase tracking-wider text-fg-muted">
          {label}
        </span>
      </div>

      <div className="flex items-baseline gap-2">
        <p
          className={cn(
            "font-mono text-3xl font-bold tabular-nums",
            valueTone ? ACCENT_TEXT[valueTone] : "text-fg-strong"
          )}
        >
          {value}
        </p>
        {deltaNode}
      </div>

      {meter ? (
        <div
          className="mt-2 h-2 w-full overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-valuenow={Math.round(meter.pct)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={cn("h-full rounded-full transition-all duration-500", METER_BG[meterTone])}
            style={{ width: `${Math.min(Math.max(meter.pct, 0), 100)}%` }}
          />
        </div>
      ) : null}

      {caption ? <p className="mt-1 text-xs text-fg-subtle">{caption}</p> : null}
    </Card>
  );
}
