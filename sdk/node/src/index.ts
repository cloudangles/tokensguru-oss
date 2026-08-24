/**
 * TokenSight OSS Node.js SDK
 *
 * Drop-in wrapper for OpenAI and Anthropic clients that automatically
 * tracks every LLM call and ships events to your TokenSight OSS backend.
 * Pure observation -- no optimization/privacy/governance runtime.
 *
 * Usage:
 *   import { TokenSight } from "tokensight-oss";
 *   const ts = new TokenSight({ apiKey: "tsk_...", baseUrl: "http://localhost:8000" });
 *   const openai = ts.wrapOpenAI(new OpenAI());
 *   // Use `openai` exactly as you'd use the native SDK.
 */

import crypto from "crypto";

// ── Types ────────────────────────────────────────────────────────────────────

export interface TokenSightConfig {
  apiKey: string;
  baseUrl?: string;
  tenantId?: string;
  projectId?: string;
  featureId?: string;
  userId?: string;
  flushIntervalMs?: number;
  batchSize?: number;
  debug?: boolean;
}

export interface TraceEvent {
  trace_id: string;
  span_id: string;
  tenant_id: string;
  project_id: string;
  feature_id: string;
  user_id?: string;
  provider: string;
  model: string;
  request_type: "chat" | "embedding" | "completion" | "tool_call";
  input_tokens: number;
  output_tokens: number;
  input_cost_usd: string;
  output_cost_usd: string;
  latency_ms: number;
  ttft_ms?: number;
  finish_reason: string;
  status: "success" | "error" | "timeout";
  error_message?: string;
  request_timestamp: string;
}

export interface TraceContext {
  traceId?: string;
  spanId?: string;
  projectId?: string;
  featureId?: string;
  userId?: string;
}

const DEFAULT_BASE_URL = "http://localhost:8000";

// ── Pricing (fallback estimate -- kept in sync by hand with sdk/python's
// pricing.json and api/pricing.py; not a shared file across languages) ──────

const PRICING: Record<string, [number, number]> = {
  "gpt-4o": [2.5, 10.0],
  "gpt-4o-mini": [0.15, 0.6],
  "gpt-4-turbo": [10.0, 30.0],
  "gpt-3.5-turbo": [0.5, 1.5],
  "o4-mini": [1.1, 4.4],
  "claude-opus-4": [15.0, 75.0],
  "claude-sonnet-4": [3.0, 15.0],
  "claude-sonnet-4-5": [3.0, 15.0],
  "claude-haiku-4": [0.8, 4.0],
  "claude-haiku-4-5": [0.8, 4.0],
  "gemini-2.5-pro": [1.25, 10.0],
  "gemini-2.5-flash": [0.15, 0.6],
  "llama-3.3-70b-versatile": [0.05, 0.08],
  "llama-3.1-8b-instant": [0.01, 0.01],
  "deepseek-chat": [0.27, 1.1],
  "deepseek-reasoner": [0.55, 2.19],
};

function calculateCost(model: string, inputTokens: number, outputTokens: number): [string, string] {
  const [inPrice, outPrice] = PRICING[model] ?? [0.15, 0.6];
  const inCost = (inputTokens / 1_000_000) * inPrice;
  const outCost = (outputTokens / 1_000_000) * outPrice;
  return [inCost.toFixed(8), outCost.toFixed(8)];
}

function generateId(): string {
  return crypto.randomUUID();
}

// ── Event Exporter (batched HTTP) ────────────────────────────────────────────

class EventExporter {
  private queue: TraceEvent[] = [];
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly config: Required<Pick<TokenSightConfig, "apiKey" | "baseUrl" | "batchSize" | "flushIntervalMs" | "debug">>;

  constructor(config: TokenSightConfig) {
    this.config = {
      apiKey: config.apiKey,
      baseUrl: config.baseUrl ?? DEFAULT_BASE_URL,
      batchSize: config.batchSize ?? 50,
      flushIntervalMs: config.flushIntervalMs ?? 5000,
      debug: config.debug ?? false,
    };
    this.startTimer();
  }

  emit(event: TraceEvent): void {
    this.queue.push(event);
    if (this.queue.length >= this.config.batchSize) {
      this.flush();
    }
  }

  async flush(): Promise<void> {
    if (this.queue.length === 0) return;
    const batch = this.queue.splice(0, this.config.batchSize);
    try {
      await this.send(batch);
    } catch (err) {
      if (this.config.debug) console.error("[TokenSight] flush error:", err);
      this.queue.unshift(...batch);
    }
  }

  private async send(events: TraceEvent[]): Promise<void> {
    const url = `${this.config.baseUrl}/api/ingest/batch`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": this.config.apiKey,
      },
      body: JSON.stringify({ events }),
    });
    if (!response.ok) {
      throw new Error(`TokenSight ingest failed: ${response.status}`);
    }
    if (this.config.debug) console.debug(`[TokenSight] flushed ${events.length} events`);
  }

  private startTimer(): void {
    this.timer = setInterval(() => this.flush(), this.config.flushIntervalMs);
    if (typeof this.timer.unref === "function") this.timer.unref();
  }

  async shutdown(): Promise<void> {
    if (this.timer) clearInterval(this.timer);
    await this.flush();
  }
}

// ── Main SDK Client ──────────────────────────────────────────────────────────

export class TokenSight {
  private readonly exporter: EventExporter;
  private readonly defaultContext: Required<Pick<TokenSightConfig, "tenantId" | "projectId" | "featureId">>;

  constructor(private readonly config: TokenSightConfig) {
    this.exporter = new EventExporter(config);
    this.defaultContext = {
      tenantId: config.tenantId ?? "default",
      projectId: config.projectId ?? "",
      featureId: config.featureId ?? "",
    };
  }

  wrapOpenAI<T extends OpenAILike>(client: T, ctx?: TraceContext): T {
    const exporter = this.exporter;
    const defaultCtx = this.defaultContext;
    const userId = this.config.userId;

    const originalCreate = client.chat.completions.create.bind(client.chat.completions);

    client.chat.completions.create = async function (params: any, options?: any): Promise<any> {
      const startMs = Date.now();
      const traceId = ctx?.traceId ?? generateId();
      const spanId = ctx?.spanId ?? generateId();

      try {
        const response = await originalCreate(params, options);
        const latencyMs = Date.now() - startMs;
        const model = response?.model ?? params.model ?? "unknown";
        const usage = response?.usage ?? {};
        const inputTokens = usage.prompt_tokens ?? 0;
        const outputTokens = usage.completion_tokens ?? 0;
        const [inCost, outCost] = calculateCost(model, inputTokens, outputTokens);
        const finishReason = response?.choices?.[0]?.finish_reason ?? "stop";

        exporter.emit({
          trace_id: traceId,
          span_id: spanId,
          tenant_id: defaultCtx.tenantId,
          project_id: ctx?.projectId ?? defaultCtx.projectId,
          feature_id: ctx?.featureId ?? defaultCtx.featureId,
          user_id: ctx?.userId ?? userId,
          provider: "openai",
          model,
          request_type: "chat",
          input_tokens: inputTokens,
          output_tokens: outputTokens,
          input_cost_usd: inCost,
          output_cost_usd: outCost,
          latency_ms: latencyMs,
          finish_reason: finishReason,
          status: "success",
          request_timestamp: new Date().toISOString(),
        });

        return response;
      } catch (err: any) {
        exporter.emit({
          trace_id: traceId,
          span_id: spanId,
          tenant_id: defaultCtx.tenantId,
          project_id: ctx?.projectId ?? defaultCtx.projectId,
          feature_id: ctx?.featureId ?? defaultCtx.featureId,
          user_id: ctx?.userId ?? userId,
          provider: "openai",
          model: params.model ?? "unknown",
          request_type: "chat",
          input_tokens: 0,
          output_tokens: 0,
          input_cost_usd: "0",
          output_cost_usd: "0",
          latency_ms: Date.now() - startMs,
          finish_reason: "error",
          status: "error",
          error_message: err?.message ?? String(err),
          request_timestamp: new Date().toISOString(),
        });
        throw err;
      }
    } as any;

    return client;
  }

  wrapAnthropic<T extends AnthropicLike>(client: T, ctx?: TraceContext): T {
    const exporter = this.exporter;
    const defaultCtx = this.defaultContext;
    const userId = this.config.userId;

    const originalCreate = client.messages.create.bind(client.messages);

    client.messages.create = async function (params: any, options?: any): Promise<any> {
      const startMs = Date.now();
      const traceId = ctx?.traceId ?? generateId();
      const spanId = ctx?.spanId ?? generateId();

      try {
        const response = await originalCreate(params, options);
        const latencyMs = Date.now() - startMs;
        const model = response?.model ?? params.model ?? "unknown";
        const inputTokens = response?.usage?.input_tokens ?? 0;
        const outputTokens = response?.usage?.output_tokens ?? 0;
        const [inCost, outCost] = calculateCost(model, inputTokens, outputTokens);

        exporter.emit({
          trace_id: traceId,
          span_id: spanId,
          tenant_id: defaultCtx.tenantId,
          project_id: ctx?.projectId ?? defaultCtx.projectId,
          feature_id: ctx?.featureId ?? defaultCtx.featureId,
          user_id: ctx?.userId ?? userId,
          provider: "anthropic",
          model,
          request_type: "chat",
          input_tokens: inputTokens,
          output_tokens: outputTokens,
          input_cost_usd: inCost,
          output_cost_usd: outCost,
          latency_ms: latencyMs,
          finish_reason: response?.stop_reason ?? "stop",
          status: "success",
          request_timestamp: new Date().toISOString(),
        });

        return response;
      } catch (err: any) {
        exporter.emit({
          trace_id: traceId,
          span_id: spanId,
          tenant_id: defaultCtx.tenantId,
          project_id: ctx?.projectId ?? defaultCtx.projectId,
          feature_id: ctx?.featureId ?? defaultCtx.featureId,
          user_id: ctx?.userId ?? userId,
          provider: "anthropic",
          model: params.model ?? "unknown",
          request_type: "chat",
          input_tokens: 0,
          output_tokens: 0,
          input_cost_usd: "0",
          output_cost_usd: "0",
          latency_ms: Date.now() - startMs,
          finish_reason: "error",
          status: "error",
          error_message: err?.message ?? String(err),
          request_timestamp: new Date().toISOString(),
        });
        throw err;
      }
    } as any;

    return client;
  }

  startSpan(name: string, ctx?: TraceContext): SpanRecorder {
    return new SpanRecorder(name, ctx ?? {}, this.exporter, this.defaultContext, this.config.userId);
  }

  async track(
    fn: () => Promise<any>,
    meta: { model: string; provider?: string; featureId?: string; ctx?: TraceContext }
  ): Promise<any> {
    const traceId = meta.ctx?.traceId ?? generateId();
    const spanId = generateId();
    const startMs = Date.now();

    try {
      const result = await fn();
      this.exporter.emit({
        trace_id: traceId,
        span_id: spanId,
        tenant_id: this.defaultContext.tenantId,
        project_id: this.defaultContext.projectId,
        feature_id: meta.featureId ?? this.defaultContext.featureId,
        provider: meta.provider ?? "unknown",
        model: meta.model,
        request_type: "chat",
        input_tokens: 0,
        output_tokens: 0,
        input_cost_usd: "0",
        output_cost_usd: "0",
        latency_ms: Date.now() - startMs,
        finish_reason: "stop",
        status: "success",
        request_timestamp: new Date().toISOString(),
      });
      return result;
    } catch (err: any) {
      this.exporter.emit({
        trace_id: traceId,
        span_id: spanId,
        tenant_id: this.defaultContext.tenantId,
        project_id: this.defaultContext.projectId,
        feature_id: meta.featureId ?? this.defaultContext.featureId,
        provider: meta.provider ?? "unknown",
        model: meta.model,
        request_type: "chat",
        input_tokens: 0,
        output_tokens: 0,
        input_cost_usd: "0",
        output_cost_usd: "0",
        latency_ms: Date.now() - startMs,
        finish_reason: "error",
        status: "error",
        error_message: err?.message,
        request_timestamp: new Date().toISOString(),
      });
      throw err;
    }
  }

  async shutdown(): Promise<void> {
    await this.exporter.shutdown();
  }
}

// ── Span Recorder (manual instrumentation) ──────────────────────────────────

export class SpanRecorder {
  private readonly startMs: number;
  private readonly traceId: string;
  private readonly spanId: string;

  constructor(
    private readonly name: string,
    private readonly ctx: TraceContext,
    private readonly exporter: EventExporter,
    private readonly defaults: Record<string, string>,
    private readonly userId?: string
  ) {
    this.startMs = Date.now();
    this.traceId = ctx.traceId ?? generateId();
    this.spanId = ctx.spanId ?? generateId();
  }

  end(result: {
    model: string;
    provider?: string;
    inputTokens?: number;
    outputTokens?: number;
    finishReason?: string;
    status?: "success" | "error";
    errorMessage?: string;
  }): void {
    const [inCost, outCost] = calculateCost(result.model, result.inputTokens ?? 0, result.outputTokens ?? 0);
    this.exporter.emit({
      trace_id: this.traceId,
      span_id: this.spanId,
      tenant_id: this.defaults.tenantId,
      project_id: this.ctx.projectId ?? this.defaults.projectId,
      feature_id: this.ctx.featureId ?? this.defaults.featureId,
      user_id: this.ctx.userId ?? this.userId,
      provider: result.provider ?? "unknown",
      model: result.model,
      request_type: "chat",
      input_tokens: result.inputTokens ?? 0,
      output_tokens: result.outputTokens ?? 0,
      input_cost_usd: inCost,
      output_cost_usd: outCost,
      latency_ms: Date.now() - this.startMs,
      finish_reason: result.finishReason ?? "stop",
      status: result.status ?? "success",
      error_message: result.errorMessage,
      request_timestamp: new Date().toISOString(),
    });
  }
}

// ── Interface stubs (duck-typed) ─────────────────────────────────────────────

interface OpenAILike {
  chat: {
    completions: {
      create: (params: any, options?: any) => Promise<any>;
    };
  };
}

interface AnthropicLike {
  messages: {
    create: (params: any, options?: any) => Promise<any>;
  };
}

export default TokenSight;

// ── Control-plane headers for external agent frameworks ─────────────────────

export const HEADER_SESSION_ID = "X-TokenSight-Session-ID";
export const HEADER_AGENT_ID = "X-TokenSight-Agent-ID";
export const HEADER_PARENT_TRACE_ID = "X-TokenSight-Parent-Trace-ID";
export const HEADER_PARENT_SPAN_ID = "X-TokenSight-Parent-Span-ID";

export function agentHeaders(opts: {
  sessionId?: string;
  agentId?: string;
  parentTraceId?: string;
  parentSpanId?: string;
}): Record<string, string> {
  const out: Record<string, string> = {};
  if (opts.sessionId) out[HEADER_SESSION_ID] = opts.sessionId;
  if (opts.agentId) out[HEADER_AGENT_ID] = opts.agentId;
  if (opts.parentTraceId) out[HEADER_PARENT_TRACE_ID] = opts.parentTraceId;
  if (opts.parentSpanId) out[HEADER_PARENT_SPAN_ID] = opts.parentSpanId;
  return out;
}
