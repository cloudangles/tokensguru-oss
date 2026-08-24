"use client";

import React from "react";
import { cn } from "./cn";

/**
 * SectionHeading — the uppercase eyebrow label used above panels/sections.
 * Standardizes the repeated `text-xs font-semibold uppercase tracking-wider
 * text-slate-400` pattern into one token-driven, consistent element.
 */
export function SectionHeading({
  children,
  icon,
  actions,
  as: Tag = "h2",
  className,
}: {
  children: React.ReactNode;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  as?: "h2" | "h3" | "h4";
  className?: string;
}) {
  return (
    <div className={cn("mb-3 flex items-center justify-between gap-3", className)}>
      <Tag className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-fg-muted">
        {icon ? <span className="text-fg-faint">{icon}</span> : null}
        {children}
      </Tag>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
