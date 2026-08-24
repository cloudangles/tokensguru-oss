import type { Config } from "tailwindcss";

/**
 * Semantic tokens are defined as RGB channels in app/globals.css and mapped
 * here through rgb(var(--token) / <alpha-value>) so opacity modifiers work,
 * e.g. bg-surface/60, text-brand/80, border-line.
 *
 * Tailwind's stock palettes (slate, cyan, emerald, …) are intentionally left
 * intact so components not yet migrated to tokens keep rendering unchanged.
 */
const token = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        // Headings/hero numbers only — restrained use, not body text.
        display: ["Space Grotesk", "Inter", "system-ui", "sans-serif"],
        // Tabular numerics for token counts, costs, IDs — prevents layout shift.
        mono: [
          "IBM Plex Mono",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
      colors: {
        // Runtime Control Plane palette — overrides Tailwind's stock slate/cyan
        // scales directly so the ~90% of files still on raw Tailwind classes
        // (bg-slate-950, text-cyan-400, etc.) repaint without per-file edits.
        // Every other stock scale (emerald/amber/rose/violet/...) is untouched,
        // so semantic status colors stay distinct from this remap.
        slate: {
          50: "#f4f5f6", 100: "#e7e9eb", 200: "#c9cdd2", 300: "#a3a9b1",
          400: "#7a828c", 500: "#5c6470", 600: "#454c57", 700: "#333941",
          800: "#20242b", 900: "#151820", 950: "#0B0D10",
        },
        cyan: {
          50: "#eafdff", 100: "#c9f7fa", 200: "#9aeef2", 300: "#6ee7ec",
          400: "#5CE1E6", 500: "#2fd1d8", 600: "#1fa8ae", 700: "#1a8489",
          800: "#166a6e", 900: "#134f52", 950: "#0a2f31",
        },
        // ── Surfaces ──
        bg: token("--bg"),
        surface: {
          DEFAULT: token("--surface"),
          2: token("--surface-2"),
          3: token("--surface-3"),
          hover: token("--surface-hover"),
        },
        // ── Lines / borders ──
        line: {
          DEFAULT: token("--line"),
          strong: token("--line-strong"),
        },
        // ── Foreground / text ──
        fg: {
          DEFAULT: token("--fg"),
          strong: token("--fg-strong"),
          muted: token("--fg-muted"),
          subtle: token("--fg-subtle"),
          faint: token("--fg-faint"),
        },
        // ── Brand (runtime accent — cyan, used intentionally, not everywhere) ──
        brand: {
          DEFAULT: token("--brand"),
          hover: token("--brand-hover"),
          strong: token("--brand-strong"),
        },
        "on-brand": token("--on-brand"),
        // ── Semantic status ──
        success: {
          DEFAULT: token("--success"),
          solid: token("--success-solid"),
        },
        warning: {
          DEFAULT: token("--warning"),
          solid: token("--warning-solid"),
        },
        danger: {
          DEFAULT: token("--danger"),
          solid: token("--danger-solid"),
        },
        info: {
          DEFAULT: token("--info"),
          solid: token("--info-solid"),
        },
      },
      borderColor: {
        DEFAULT: token("--line"),
      },
      ringColor: {
        DEFAULT: token("--ring"),
      },
      borderRadius: {
        // New, non-colliding key — leaves Tailwind's default rounded / rounded-sm
        // / rounded-lg (used 125+ times on skeletons & badges) untouched.
        card: "var(--radius)",
      },
      boxShadow: {
        // Disciplined elevation scale for dark surfaces (elevation-consistent).
        card: "0 1px 2px 0 rgb(0 0 0 / 0.25)",
        raised: "0 4px 16px -2px rgb(0 0 0 / 0.35)",
        overlay: "0 12px 40px -8px rgb(0 0 0 / 0.55)",
        "glow-brand": "0 0 0 1px rgb(var(--brand) / 0.18), 0 4px 24px rgb(var(--brand) / 0.08)",
      },
      keyframes: {
        "slide-in": {
          "0%": { transform: "translateX(100%)" },
          "100%": { transform: "translateX(0)" },
        },
        "slide-out": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(100%)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "slide-in": "slide-in 0.3s ease-out forwards",
        "slide-out": "slide-out 0.2s ease-in forwards",
        "fade-in": "fade-in 0.2s ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
