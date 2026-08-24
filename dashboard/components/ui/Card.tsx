"use client";

import React from "react";
import { cn } from "./cn";

/**
 * Card — the canonical panel surface across the dashboard.
 *
 * Replaces the ad-hoc `rounded-xl border border-slate-800 bg-slate-900 p-5`
 * pattern repeated across 85+ components with a single token-driven surface.
 *
 *   tone="glow"    → subtle brand ring on hover (for interactive/hero cards)
 *   interactive    → adds hover elevation + pointer affordance
 *   padding="none" → for cards that manage their own inner padding (tables, charts)
 */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: "default" | "glow" | "success" | "warning" | "danger";
  padding?: "none" | "sm" | "md" | "lg";
  interactive?: boolean;
  as?: "div" | "section" | "article";
}

const PADDING: Record<NonNullable<CardProps["padding"]>, string> = {
  none: "",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

const TONE_RING: Record<NonNullable<CardProps["tone"]>, string> = {
  default: "",
  glow: "hover:shadow-glow-brand",
  success: "ring-1 ring-inset ring-success/20",
  warning: "ring-1 ring-inset ring-warning/25",
  danger: "ring-1 ring-inset ring-danger/25",
};

export function Card({
  tone = "default",
  padding = "md",
  interactive = false,
  as: Tag = "div",
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <Tag
      className={cn(
        "rounded-card border border-line bg-surface text-fg shadow-card transition-all duration-200",
        PADDING[padding],
        TONE_RING[tone],
        interactive &&
          "cursor-pointer hover:border-line-strong hover:shadow-raised focus-within:border-line-strong",
        className
      )}
      {...rest}
    >
      {children}
    </Tag>
  );
}

/** CardHeader — title + optional description + trailing actions slot. */
export function CardHeader({
  title,
  description,
  actions,
  className,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-4 flex items-start justify-between gap-4", className)}>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-fg">{title}</h3>
        {description ? (
          <p className="mt-0.5 text-xs text-fg-subtle">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}
