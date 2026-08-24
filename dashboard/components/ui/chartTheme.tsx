"use client";

import React from "react";

/**
 * chartTheme — one source of truth for Recharts across the dashboard.
 *
 * Recharts sets fills/strokes as SVG attributes (not CSS), so var(--token)
 * can't resolve there; these are explicit hex values tuned for the dark theme
 * and chosen to be colorblind-distinguishable with ≥3:1 contrast vs the
 * slate-900 surface (chart contrast-data). Phase 4 adds light-theme values.
 */

// Categorical palette — distinct hues, safe for deuteranopia/protanopia.
export const CHART_COLORS = [
  "#5CE1E6", // cyan   (brand)
  "#34d399", // emerald(savings/positive)
  "#a78bfa", // violet
  "#fbbf24", // amber
  "#f472b6", // pink
  "#60a5fa", // blue
  "#fb923c", // orange
  "#2dd4bf", // teal
] as const;

// Semantic series colors (use where a series has fixed meaning).
export const SERIES = {
  cost: "#5CE1E6",
  savings: "#34d399",
  warning: "#fbbf24",
  danger: "#fb7185",
  neutral: "#7a828c",
} as const;

// Shared axis / grid props — spread onto <XAxis/>, <YAxis/>, <CartesianGrid/>.
export const axisProps = {
  tick: { fill: "#5c6470", fontSize: 11 },
  axisLine: false as const,
  tickLine: false as const,
};

export const gridProps = {
  strokeDasharray: "3 3",
  vertical: false as const,
  stroke: "#20242b",
};

export const cursorFill = { fill: "rgba(122,130,140,0.06)" };

/** Vertical gradient <defs> for bars/areas. Render inside the chart. */
export function ChartGradient({
  id,
  color,
  from = 0.9,
  to = 0.15,
}: {
  id: string;
  color: string;
  from?: number;
  to?: number;
}) {
  return (
    <defs>
      <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity={from} />
        <stop offset="100%" stopColor={color} stopOpacity={to} />
      </linearGradient>
    </defs>
  );
}

/**
 * ChartTooltip — token-styled tooltip. Pass a `rows` renderer that maps the
 * hovered payload to label/value pairs. Keeps every chart's tooltip identical.
 */
export function ChartTooltip({
  active,
  payload,
  title,
  rows,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name?: string; payload: Record<string, unknown> }>;
  title?: (p: Record<string, unknown>) => React.ReactNode;
  rows?: (p: Record<string, unknown>) => React.ReactNode;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 shadow-overlay">
      {title ? <p className="text-xs text-fg-subtle">{title(point)}</p> : null}
      <div className="mt-1 space-y-0.5">
        {rows ? (
          rows(point)
        ) : (
          <p className="font-mono text-sm font-semibold tabular-nums text-fg">
            {payload[0].value}
          </p>
        )}
      </div>
    </div>
  );
}
