"use client";

import React from "react";
import { cn } from "./cn";

/**
 * EmptyState — standardizes the "no data / coming soon / error" panels that
 * currently vary component-to-component. Provides a consistent icon + message
 * + optional recovery action (error-recovery / empty-states).
 */
export function EmptyState({
  icon,
  title,
  description,
  action,
  tone = "neutral",
  className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  tone?: "neutral" | "danger";
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-2 px-4 py-10 text-center",
        className
      )}
      role={tone === "danger" ? "alert" : undefined}
    >
      {icon ? (
        <span className={cn("h-8 w-8", tone === "danger" ? "text-danger" : "text-fg-faint")}>
          {icon}
        </span>
      ) : null}
      <p className="text-sm font-medium text-fg-muted">{title}</p>
      {description ? <p className="max-w-sm text-xs text-fg-subtle">{description}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

/** Default info glyph for empty states. */
export function InfoGlyph() {
  return (
    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" className="h-full w-full">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
