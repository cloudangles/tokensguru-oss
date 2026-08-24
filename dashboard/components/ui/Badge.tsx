"use client";

import React from "react";
import { cn } from "./cn";

/**
 * Badge / StatusPill — semantic status chips.
 *
 * Status is conveyed by BOTH color and text/icon (never color alone), meeting
 * WCAG `color-not-only`. Soft variants use tinted fills that keep ≥4.5:1 text
 * contrast in dark mode.
 */
export type BadgeTone =
  | "neutral"
  | "brand"
  | "success"
  | "warning"
  | "danger"
  | "info";

const TONE: Record<BadgeTone, string> = {
  neutral: "bg-surface-2 text-fg-muted ring-line",
  brand: "bg-brand/10 text-brand ring-brand/20",
  success: "bg-success/10 text-success ring-success/20",
  warning: "bg-warning/10 text-warning ring-warning/25",
  danger: "bg-danger/10 text-danger ring-danger/25",
  info: "bg-info/10 text-info ring-info/20",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  /** Show a leading status dot (uses currentColor). */
  dot?: boolean;
  /** Optional leading icon (overrides dot). */
  icon?: React.ReactNode;
  size?: "sm" | "md";
}

export function Badge({
  tone = "neutral",
  dot = false,
  icon,
  size = "md",
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium ring-1 ring-inset",
        size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
        TONE[tone],
        className
      )}
      {...rest}
    >
      {icon ? (
        <span className="flex-shrink-0">{icon}</span>
      ) : dot ? (
        <span className="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-current" aria-hidden />
      ) : null}
      {children}
    </span>
  );
}
