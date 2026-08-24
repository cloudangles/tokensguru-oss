export function fmtTokens(n: number, precise = false): string {
  if (precise || n < 1000) return Math.round(n).toLocaleString("en-US");
  if (n >= 10_000) return `${(n / 1000).toFixed(1)}k`;
  return `${(n / 1000).toFixed(2)}k`;
}

/** Positive savings display -- never prefixes with minus; em-dash when zero. */
export function fmtSavedTokens(n: number, precise = true): string {
  if (!n || n <= 0) return "—";
  return fmtTokens(n, precise);
}

/** Parse an API/ClickHouse naive UTC timestamp to epoch milliseconds. */
export function parseUtcTimestamp(ts: string): number {
  if (!ts) return 0;
  const normalized = ts.includes("T") || ts.endsWith("Z") ? ts : ts.replace(" ", "T");
  const utc = normalized.endsWith("Z") ? normalized : `${normalized}Z`;
  const ms = new Date(utc).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

export function relativeTime(ts: string): string {
  const diff = Date.now() - parseUtcTimestamp(ts);
  const s = Math.floor(diff / 1000);
  if (s < 0) return "just now";
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export function fmtCost(usd?: number | null): string {
  const n = usd ?? 0;
  if (!n || Number.isNaN(n)) return "$0.00";
  const abs = Math.abs(n);
  if (abs >= 1000) return `$${(n / 1000).toFixed(1)}K`;
  if (abs >= 1) return `$${n.toFixed(2)}`;
  if (abs >= 0.0001) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(6)}`;
}

export function fmtLatency(ms?: number | null): string {
  const n = ms ?? 0;
  if (n >= 1000) return `${(n / 1000).toFixed(2)}s`;
  return `${Math.round(n)}ms`;
}
