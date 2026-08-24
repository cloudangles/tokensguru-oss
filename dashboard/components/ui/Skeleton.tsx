"use client";

import React from "react";
import { cn } from "./cn";

/**
 * Skeleton — tokenized loading placeholder. Uses the shimmer utility (respects
 * prefers-reduced-motion via the global media query) instead of raw
 * `animate-pulse bg-slate-800`.
 */
export function Skeleton({
  className,
  rounded = "rounded",
  style,
}: {
  className?: string;
  rounded?: string;
  style?: React.CSSProperties;
}) {
  return <div className={cn("shimmer", rounded, className)} style={style} aria-hidden />;
}

/** SkeletonText — n stacked lines, last one shorter. */
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)} aria-hidden>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn("h-3", i === lines - 1 ? "w-2/3" : "w-full")}
        />
      ))}
    </div>
  );
}
