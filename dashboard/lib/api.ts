const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TraceEvent {
  event_id: string;
  trace_id: string;
  span_id: string;
  tenant_id: string;
  project_id: string;
  feature_id: string;
  user_id: string;
  provider: string;
  model: string;
  request_type: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_tokens_before: number;
  input_tokens_saved: number;
  input_cost_usd: number;
  output_cost_usd: number;
  total_cost_usd: number;
  latency_ms: number;
  ttft_ms: number;
  finish_reason: string;
  status: string;
  error_message: string;
  request_timestamp: string;
  ingestion_timestamp: string;
  prompt_text: string;
  completion_text: string;
  agent_name: string;
  parent_span_id: string;
}

export interface SpendSummary {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
}

export interface PlaygroundRunResult {
  trace_id: string;
  span_id: string;
  provider: string;
  model: string;
  status: string;
  error_message: string;
  original_prompt: string;
  optimized_prompt: string;
  completion_text: string;
  input_tokens_before: number;
  input_tokens: number;
  tokens_saved: number;
  output_tokens: number;
  input_cost_usd: number;
  output_cost_usd: number;
  latency_ms: number;
}

export interface AgentSpan {
  span_id: string;
  trace_id: string;
  parent_span_id: string;
  agent_id: string;
  agent_name: string;
  step_type: string;
  step_name: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  status: string;
  error_message: string;
  started_at: string;
  finished_at: string;
}

function authHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("ts_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

export function fetchTraces(limit = 50): Promise<TraceEvent[]> {
  return apiFetch(`/api/traces?limit=${limit}`);
}

export function fetchTrace(traceId: string): Promise<TraceEvent> {
  return apiFetch(`/api/traces/${traceId}`);
}

export function fetchSpendSummary(): Promise<SpendSummary> {
  return apiFetch(`/api/spend/summary`);
}

export function runPlayground(body: {
  provider: string;
  model: string;
  prompt: string;
  invoke_provider: boolean;
}): Promise<PlaygroundRunResult> {
  return apiFetch(`/v1/playground/run`, { method: "POST", body: JSON.stringify(body) });
}

export function fetchAgentSpans(traceId: string): Promise<AgentSpan[]> {
  return apiFetch(`/api/agents/spans/${traceId}`);
}

export function login(email: string, password: string): Promise<{ access_token: string; email: string }> {
  return apiFetch(`/api/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) });
}

export function register(
  email: string,
  password: string
): Promise<{ access_token: string; api_key: string; email: string }> {
  return apiFetch(`/api/auth/register`, { method: "POST", body: JSON.stringify({ email, password }) });
}

export interface ProviderKey {
  provider: string;
  masked_key: string;
  updated_at: string;
}

export const PROVIDERS = [
  "openai", "anthropic", "groq", "deepseek", "google", "ollama", "openrouter", "together",
] as const;

export function fetchProviderKeys(): Promise<ProviderKey[]> {
  return apiFetch(`/api/settings/provider-keys`);
}

export function saveProviderKey(provider: string, apiKey: string): Promise<{ ok: boolean }> {
  return apiFetch(`/api/settings/provider-keys`, {
    method: "PUT",
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
}

export function deleteProviderKey(provider: string): Promise<{ ok: boolean }> {
  return apiFetch(`/api/settings/provider-keys/${provider}`, { method: "DELETE" });
}
