"use client";

import React from "react";
import { cn } from "./cn";

/**
 * Button — the single interactive button primitive.
 *
 * Enforces the professional-UI baseline: ≥44px tap target on md/lg, visible
 * focus ring (from global focus-visible), disabled semantics with reduced
 * emphasis, loading state that disables + shows a spinner, and one primary
 * emphasis per screen (variant="primary").
 */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "bg-brand text-on-brand hover:bg-brand-hover active:brightness-95 shadow-card",
  secondary:
    "bg-surface-2 text-fg hover:bg-surface-3 border border-line hover:border-line-strong",
  ghost: "text-fg-muted hover:bg-surface-2 hover:text-fg",
  danger:
    "bg-danger-solid text-white hover:brightness-110 active:brightness-95 shadow-card",
};

const SIZE: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5 rounded-md",
  md: "h-10 px-4 text-sm gap-2 rounded-lg", // 40px; hit area extended by tap padding
  lg: "h-11 px-5 text-sm gap-2 rounded-lg", // 44px — touch-target-size
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-90"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "secondary",
      size = "md",
      loading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      disabled,
      className,
      children,
      type = "button",
      ...rest
    },
    ref
  ) {
    const isDisabled = disabled || loading;
    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        className={cn(
          "inline-flex select-none items-center justify-center font-medium transition-all duration-150",
          "focus-visible:outline-none", // global focus-visible ring handles the outline
          "disabled:cursor-not-allowed disabled:opacity-50",
          "[touch-action:manipulation]",
          VARIANT[variant],
          SIZE[size],
          fullWidth && "w-full",
          className
        )}
        {...rest}
      >
        {loading ? <Spinner /> : leftIcon ? <span className="flex-shrink-0">{leftIcon}</span> : null}
        {children}
        {!loading && rightIcon ? <span className="flex-shrink-0">{rightIcon}</span> : null}
      </button>
    );
  }
);
