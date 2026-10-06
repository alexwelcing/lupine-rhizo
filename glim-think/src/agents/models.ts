/**
 * Tiered model selection for GLIM agents.
 *
 * - `fast` uses WORKERS_AI_MODEL, with Scout as its compatibility default.
 * - `deep` honors a configured DEEP_PROVIDER preference, otherwise consulting
 *   the quality scorecard and then balancing available providers.
 * - The workspace can explicitly choose generation profiles from the shared
 *   modelProfiles catalog. Clef is a decision model, never a chat generator.
 *
 * Provider model overrides remain deployment settings. Explicit experiment
 * pins preserve the existing A/B behavior. Credential or binding presence is
 * configuration evidence only; account access has not been verified here.
 *
 * Automatic deep selection falls back to the configured fast tier when no
 * eligible deep provider remains. MiniMax's monthly token guard applies to
 * ordinary routing and provider-failure fallback, and explicit workspace
 * selections reject an exhausted budget instead of substituting a model.
 *
 * Spend tracking: KV-backed monthly counter under
 *   `budget:YYYY-MM:minimax` → { tokens, calls, last_at }
 */
import { createWorkersAI } from "workers-ai-provider";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { generateText, wrapLanguageModel, type LanguageModel, type LanguageModelMiddleware } from "ai";
import type { Env } from "../types";
import { getModelQualityTrend } from "../evals/store";
import { openaiViaGateway, anthropicViaGateway, googleViaGateway } from "./gateway";
import {
  MODEL_DEFAULTS, DEEP_PROVIDERS, WORKERS_FAST_PROFILE, WORKERS_DEEP_PROFILE,
  configuredProvider, resolveModelId, preferredDeepProvider, getInteractiveDeepSelection,
  getModelCatalog, type DeepProviderId,
} from "./modelProfiles";

export type ReasoningTier = "fast" | "deep";

// Verified on 2026-05-02: api.minimax.io/v1 exposes the full MiniMax
// model line for our Max-plan key (api.minimax.chat/v1 and api.minimaxi.com/v1
// returned authentication-success but empty model lists).
//
// 2026-06-02 upgrade — MiniMax-M3 (released 2026-06-01) is the new deep-tier
// default for hypothesis generation. It serves on the SAME OpenAI-compatible
// route (api.minimax.io/v1, POST /chat/completions), so the swap is a model-id
// change only — no endpoint, auth, or adapter change. M3 vs M2.7 (per the
// public release notes + model catalog; confirm on THIS key before trusting):
//   - 1M-token context (vs 256K) → whole-corpus + literature in one turn
//   - MiniMax Sparse Attention (MSA): ~1/20 per-token cost at long context
//   - ~$0.60 / 1M input tokens under the 512K tier (cheaper deep reasoning)
// Pre-deploy check: GET /v1/models (admin route → listMiniMaxModels) must list
// "MiniMax-M3" for this account. Until the M2.7→M3 A/B has signal, pin either
// id per call via the model axis (selectDeepRoute modelOverride / ab-oracle
// --axis model) so quality is measured, not assumed.
//
// Models on this route (GET /v1/models, 2026-06-02):
//   MiniMax-M3                                  (latest, top-tier — DEFAULT)
//   MiniMax-M2.7, MiniMax-M2.7-highspeed        (prior top-tier — A/B baseline)
//   MiniMax-M2.5, MiniMax-M2.5-highspeed        (previous gen)
//   MiniMax-M2.1, MiniMax-M2.1-highspeed
//   MiniMax-M2                                  (legacy)
//
// `-highspeed` variants trade ~10% quality for ~3× throughput. Use them
// for the Orchestrator (many short dispatch calls); use the base variant
// for Theorist + Causal (one-shot deep reasoning per turn).
const MINIMAX_DEFAULT_BASE_URL = "https://api.minimax.io/v1";
// Anthropic-compatible endpoint (Messages API). M3 is an agentic reasoning model;
// the Messages API gives native thinking blocks + tool use, so the deep tier drives
// MiniMax through @ai-sdk/anthropic pointed here — instead of the OpenAI-chat shape,
// which forced the <think>…</think> regex band-aid scattered across the agents.
// Per-deployment override: MINIMAX_ANTHROPIC_BASE_URL.
// NOTE: must include the /v1 — @ai-sdk/anthropic POSTs to `${baseURL}/messages`
// (its default baseURL is https://api.anthropic.com/v1). Without /v1 the request
// 404s at api.minimax.io/anthropic/messages.
const MINIMAX_ANTHROPIC_DEFAULT_BASE_URL = "https://api.minimax.io/anthropic/v1";
// Deep-tier hypothesis-generation model. Per-deployment override: MINIMAX_MODEL
// secret. Per-call override: selectDeepRoute({ modelOverride }). The documented
// pre-upgrade baseline (for A/B comparison) is MINIMAX_BASELINE_MODEL below.
const MINIMAX_DEFAULT_MODEL = MODEL_DEFAULTS.minimax;
/** The pre-upgrade deep-tier model, kept as the canonical A/B baseline id so the
 * eval harness and docs reference one source of truth. */
export const MINIMAX_BASELINE_MODEL = "MiniMax-M2.7";
// 500M tokens/month for the Max plan. Budget guard kicks in once monthly
// usage exceeds it and falls back to Workers AI.
const MINIMAX_MONTHLY_TOKEN_BUDGET = 500_000_000;

export const FAST_MODEL = MODEL_DEFAULTS["workers-ai"];

function miniMaxConfig(env: Env): { baseURL: string; model: string } {
  return {
    baseURL: env.MINIMAX_BASE_URL?.trim() || MINIMAX_DEFAULT_BASE_URL,
    model: env.MINIMAX_MODEL?.trim() || MINIMAX_DEFAULT_MODEL,
  };
}

// Note: -highspeed model variants are NOT exposed on this account's
// Max plan (every "*-highspeed" returns 2061 "current token plan not
// support model"). The earlier "fast-deep" tier has been removed.
// If MiniMax later exposes -highspeed, re-add by setting MINIMAX_MODEL
// secret to e.g. "MiniMax-M2.7-highspeed".

function monthKey(): string {
  return new Date().toISOString().slice(0, 7);
}

export async function hasMiniMaxBudget(env: Env): Promise<boolean> {
  if (!configuredProvider(env, "minimax")) return false;
  try {
    const raw = await env.CONFIG.get(`budget:${monthKey()}:minimax`);
    if (!raw) return true;
    const stats = JSON.parse(raw) as { tokens?: number };
    return (stats.tokens ?? 0) < MINIMAX_MONTHLY_TOKEN_BUDGET;
  } catch {
    return true;
  }
}

export async function recordMiniMaxSpend(
  env: Env,
  tokens: number,
): Promise<void> {
  try {
    const key = `budget:${monthKey()}:minimax`;
    const raw = await env.CONFIG.get(key);
    const stats = raw
      ? (JSON.parse(raw) as { tokens: number; calls: number })
      : { tokens: 0, calls: 0 };
    stats.tokens += tokens;
    stats.calls += 1;
    await env.CONFIG.put(
      key,
      JSON.stringify({ ...stats, last_at: new Date().toISOString() }),
    );
  } catch (e) {
    console.warn("recordMiniMaxSpend failed:", e);
  }
}

export function fastModel(env: Env) {
  return workersModel(env, resolveModelId(env, "workers-ai"));
}

function workersModel(env: Env, modelId: string) {
  // GLM Flash defaults to max reasoning; the interactive fast profile uses low.
  return createWorkersAI({ binding: env.AI })(modelId,
    modelId === WORKERS_FAST_PROFILE ? { reasoning_effort: "low" } : {});
}

function usageTotal(usage: unknown): number {
  if (!usage || typeof usage !== "object") return 0;
  const u = usage as Record<string, unknown>;
  const numericOrZero = (v: unknown): number =>
    typeof v === "number" && Number.isFinite(v) ? v : 0;
  const direct =
    numericOrZero(u.inputTokens) +
    numericOrZero(u.outputTokens) +
    numericOrZero(u.reasoningTokens);
  if (direct > 0) return direct;
  return numericOrZero(u.totalTokens);
}

function emptyModelOutputError(provider: string, model: string, finishReason: unknown, usage: unknown): Error {
  const finish = typeof finishReason === "string" ? finishReason : "unknown";
  return new Error(`empty model output from ${provider}/${model}; finish=${finish}; tokens=${usageTotal(usage)}`);
}

function coordinationOutputBudget(provider: DeepProvider | "workers-ai", requested?: number): number {
  const cleanRequested =
    typeof requested === "number" && Number.isFinite(requested) && requested > 0
      ? Math.trunc(requested)
      : undefined;
  const floors: Record<DeepProvider | "workers-ai", number> = {
    "workers-ai": 256,
    minimax: 512,
    zai: 2048,
    openai: 512,
    anthropic: 512,
    google: 512,
  };
  const defaults: Record<DeepProvider | "workers-ai", number> = {
    "workers-ai": 768,
    minimax: 2048,
    zai: 2048,
    openai: 2048,
    anthropic: 2048,
    google: 2048,
  };
  return Math.max(cleanRequested ?? defaults[provider], floors[provider]);
}

/**
 * Extract a usable token count from any of the usage shapes the
 * OpenAI-compatible adapter returns. Empirically (verified via
 * /admin/diag-do):
 *
 *   - generateText returns `{inputTokens, outputTokens, reasoningTokens,
 *     totalTokens, raw, ...}` — v6 shape with numeric fields
 *   - streamText's `finish` chunk often returns `{inputTokens: {},
 *     outputTokens: {}}` — empty objects (a bug in the adapter or in
 *     how MiniMax M2.7 reports streaming usage)
 *   - The raw passthrough (`usage.raw`) consistently has the OpenAI
 *     shape `{prompt_tokens, completion_tokens, total_tokens,
 *     completion_tokens_details: {reasoning_tokens}, ...}`
 *
 * We try the v6 shape first; if that yields zero AND raw has numbers,
 * we use raw. This makes spend tracking work whether the model is
 * called via generate or stream.
 */
export function extractMiniMaxTokens(usage: unknown): number {
  if (!usage || typeof usage !== "object") return 0;
  const u = usage as Record<string, unknown>;

  const numericOrZero = (v: unknown): number =>
    typeof v === "number" && Number.isFinite(v) ? v : 0;

  const v6 =
    numericOrZero(u.inputTokens) +
    numericOrZero(u.outputTokens) +
    numericOrZero(u.reasoningTokens);
  if (v6 > 0) return v6;

  const raw = u.raw as Record<string, unknown> | undefined;
  if (raw) {
    const rawTotal =
      numericOrZero(raw.prompt_tokens) + numericOrZero(raw.completion_tokens);
    if (rawTotal > 0) return rawTotal;
    const rawTotalDirect = numericOrZero(raw.total_tokens);
    if (rawTotalDirect > 0) return rawTotalDirect;
  }

  return numericOrZero(u.totalTokens);
}

function spendMiddleware(env: Env): LanguageModelMiddleware {
  return {
    specificationVersion: "v3",
    wrapGenerate: async ({ doGenerate }) => {
      const result = await doGenerate();
      const tokens = extractMiniMaxTokens(result.usage);
      if (tokens > 0) {
        await recordMiniMaxSpend(env, tokens);
      }
      return result;
    },
    wrapStream: async ({ doStream }) => {
      const { stream, ...rest } = await doStream();
      let lastFinishUsage: unknown = null;
      const wrappedStream = stream.pipeThrough(
        new TransformStream({
          transform(chunk, controller) {
            if (chunk.type === "finish") {
              lastFinishUsage = chunk.usage;
            }
            controller.enqueue(chunk);
          },
          async flush() {
            const tokens = extractMiniMaxTokens(lastFinishUsage);
            if (tokens > 0) {
              await recordMiniMaxSpend(env, tokens);
            }
          },
        }),
      );
      return { stream: wrappedStream, ...rest };
    },
  };
}

export function miniMaxModel(env: Env, modelOverride?: string) {
  const model = modelOverride ?? miniMaxConfig(env).model;
  // Drive MiniMax via the Anthropic Messages API (native thinking + tool use)
  // through the AI SDK's anthropic provider, so the spend middleware, Phoenix
  // spans, and the eval scorecard all keep working — only the wire format changes.
  const baseURL =
    env.MINIMAX_ANTHROPIC_BASE_URL?.trim() || MINIMAX_ANTHROPIC_DEFAULT_BASE_URL;
  const base = createAnthropic({
    baseURL,
    apiKey: env.MINIMAX_API_KEY!,
  }).languageModel(model);
  return wrapLanguageModel({
    model: base,
    middleware: spendMiddleware(env),
  });
}

/**
 * Fire a minimal "say OK" call to verify that the configured (or
 * ad-hoc) MiniMax model + base URL + key work. Caller can override
 * baseURL and model per-call via the optional `overrides` arg —
 * useful for probing different endpoints from /admin/test-minimax
 * without changing secrets.
 */
export async function testMiniMaxCall(
  env: Env,
  overrides?: { baseURL?: string; model?: string },
): Promise<{
  ok: boolean;
  model: string;
  base_url: string;
  latency_ms: number;
  status?: number;
  response_text?: string;
  reasoning?: string;
  usage?: { promptTokens?: number; completionTokens?: number; totalTokens?: number };
  error?: string;
}> {
  const cfg = miniMaxConfig(env);
  const baseURL = overrides?.baseURL?.trim() || cfg.baseURL;
  const model = overrides?.model?.trim() || cfg.model;
  if (!env.MINIMAX_API_KEY) {
    return { ok: false, model, base_url: baseURL, latency_ms: 0, error: "MINIMAX_API_KEY is unset" };
  }
  const start = Date.now();
  try {
    const res = await fetch(`${baseURL}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.MINIMAX_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: "Reply with the single word OK." },
          { role: "user", content: "ping" },
        ],
        // M3 is a reasoning model — use the modern ("3.0") request shape every
        // current reasoning API expects: max_completion_tokens (not max_tokens)
        // and reasoning_split, so thinking returns in a separate `reasoning`
        // field instead of inline <think>…</think>. Non-reasoning ids ignore these.
        max_completion_tokens: 64,
        reasoning_split: true,
        temperature: 0,
      }),
    });
    const latency = Date.now() - start;
    const text = await res.text();
    if (!res.ok) {
      return {
        ok: false,
        model,
        base_url: baseURL,
        latency_ms: latency,
        status: res.status,
        error: `HTTP ${res.status}: ${text.slice(0, 500)}`,
      };
    }
    const json = JSON.parse(text) as {
      choices?: Array<{
        message?: { content?: string; reasoning_details?: unknown; reasoning_content?: unknown };
      }>;
      usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
    };
    const msg = json.choices?.[0]?.message;
    const rawReasoning = msg?.reasoning_details ?? msg?.reasoning_content;
    const reasoning =
      typeof rawReasoning === "string"
        ? rawReasoning.slice(0, 200)
        : rawReasoning
          ? JSON.stringify(rawReasoning).slice(0, 200)
          : undefined;
    return {
      ok: true,
      model,
      base_url: baseURL,
      latency_ms: latency,
      status: res.status,
      response_text: msg?.content?.trim(),
      reasoning,
      usage: {
        promptTokens: json.usage?.prompt_tokens,
        completionTokens: json.usage?.completion_tokens,
        totalTokens: json.usage?.total_tokens,
      },
    };
  } catch (e) {
    return {
      ok: false,
      model,
      base_url: baseURL,
      latency_ms: Date.now() - start,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

/**
 * GET /v1/models against a candidate base URL. Returns the parsed
 * list (OpenAI-compat shape: { data: [{id, ...}, ...] }) or an error.
 */
export async function listMiniMaxModels(
  env: Env,
  overrides?: { baseURL?: string },
): Promise<{
  ok: boolean;
  base_url: string;
  status?: number;
  models?: Array<{ id: string; object?: string; owned_by?: string }>;
  count?: number;
  error?: string;
}> {
  const baseURL = overrides?.baseURL?.trim() || miniMaxConfig(env).baseURL;
  if (!env.MINIMAX_API_KEY) {
    return { ok: false, base_url: baseURL, error: "MINIMAX_API_KEY is unset" };
  }
  try {
    const res = await fetch(`${baseURL}/models`, {
      method: "GET",
      headers: { Authorization: `Bearer ${env.MINIMAX_API_KEY}` },
    });
    const text = await res.text();
    if (!res.ok) {
      return {
        ok: false,
        base_url: baseURL,
        status: res.status,
        error: `HTTP ${res.status}: ${text.slice(0, 500)}`,
      };
    }
    const json = JSON.parse(text) as {
      data?: Array<{ id: string; object?: string; owned_by?: string }>;
    };
    return {
      ok: true,
      base_url: baseURL,
      status: res.status,
      models: json.data ?? [],
      count: (json.data ?? []).length,
    };
  } catch (e) {
    return {
      ok: false,
      base_url: baseURL,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

/**
 * Sweep a list of candidate base URLs and report which accept the
 * current MINIMAX_API_KEY. Used to discover the correct endpoint
 * for an unfamiliar key prefix (e.g. sk-cp-..., sk-or-..., sk-ant-...).
 */
const CANDIDATE_BASE_URLS = [
  "https://api.minimax.chat/v1",
  "https://api.minimaxi.com/v1",
  "https://api.minimax.io/v1",
  "https://openrouter.ai/api/v1",
  "https://api.cometapi.com/v1",
  "https://api.openai-compatible.com/v1",
  "https://api.deepseek.com/v1",
  "https://aihubmix.com/v1",
  "https://api.zhizengzeng.com/v1",
  "https://api.gptsapi.net/v1",
];

/**
 * Exercise the FULL deep-tier pipeline: selectModel → wrapLanguageModel
 * (with spendMiddleware) → AI SDK generateText. Verifies that
 * MiniMax-via-AI-SDK works and that the spend middleware records tokens
 * to KV (you can re-check /budget afterwards to see the increment).
 */
export async function exerciseDeepTier(env: Env): Promise<{
  ok: boolean;
  model_route: { base_url: string; model: string };
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  latency_ms?: number;
  text?: string;
  error?: string;
}> {
  const cfg = miniMaxConfig(env);
  if (!env.MINIMAX_API_KEY) {
    return { ok: false, model_route: { base_url: cfg.baseURL, model: cfg.model }, error: "MINIMAX_API_KEY is unset" };
  }
  const start = Date.now();
  try {
    const model = selectModel(env, "deep");
    const result = await generateText({
      model,
      maxOutputTokens: 64,
      prompt: "In one sentence, what is a hyper-ribbon error manifold?",
      experimental_telemetry: { isEnabled: true, functionId: "models.health-check" },
    });
    const totalTokens =
      (result.usage?.inputTokens ?? 0) +
      (result.usage?.outputTokens ?? 0) +
      (result.usage?.reasoningTokens ?? 0);
    // Direct spend record so the test endpoint always increments /budget
    // even if the wrapLanguageModel middleware didn't fire (which would
    // be a separate bug we'd need to track down — but the /admin probe
    // should never silently lose spend).
    if (totalTokens > 0) {
      await recordMiniMaxSpend(env, totalTokens);
    }
    return {
      ok: true,
      model_route: { base_url: cfg.baseURL, model: cfg.model },
      prompt_tokens: result.usage?.inputTokens,
      completion_tokens: result.usage?.outputTokens,
      total_tokens: totalTokens,
      latency_ms: Date.now() - start,
      text: result.text,
    };
  } catch (e) {
    return {
      ok: false,
      model_route: { base_url: cfg.baseURL, model: cfg.model },
      latency_ms: Date.now() - start,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

export async function sweepMiniMaxEndpoints(
  env: Env,
  extraUrls?: string[],
): Promise<Array<{
  base_url: string;
  models_ok: boolean;
  models_status?: number;
  models_count?: number;
  models_error?: string;
}>> {
  const urls = [...CANDIDATE_BASE_URLS, ...(extraUrls ?? [])];
  return Promise.all(
    urls.map(async (baseURL) => {
      const result = await listMiniMaxModels(env, { baseURL });
      return {
        base_url: baseURL,
        models_ok: result.ok,
        models_status: result.status,
        models_count: result.count,
        models_error: result.error,
      };
    }),
  );
}

/**
 * Synchronous selector. Use when the caller can't await
 * (e.g. inside @cloudflare/think `getModel()`).
 *
 * Async beforeTurn hooks enforce the budget/eval decision for actual turns.
 * The synchronous path honors configured credentials and DEEP_PROVIDER.
 */
export function selectModel(env: Env, tier: ReasoningTier) {
  if (tier !== "deep") return fastModel(env);
  const selected = getInteractiveDeepSelection(env);
  return selected.provider === "workers-ai"
    ? workersModel(env, selected.modelId)
    : buildDeepRoute(env, selected.provider).model;
}

/**
 * Async selector with full budget check. Prefer this when the caller
 * is in async code (cron handlers, queue consumers) — it falls back
 * to fast tier when the monthly MiniMax budget is exhausted.
 */
export async function selectModelChecked(
  env: Env,
  tier: ReasoningTier,
): Promise<ReturnType<typeof selectModel>> {
  return tier === "deep" ? (await selectDeepRoute(env)).model : fastModel(env);
}

// ---------------------------------------------------------------------------
// Canonical deep-tier model layer (replaces the deleted src/gateway/ stack).
//
// One path for every research LLM call: AI-SDK-native, so each call emits an
// `ai.generateText` span the OpenInference projector + eval scorecard can see
// and steer. The legacy hand-rolled gateway (ModelRouter/providers) was 0/300
// spans in Phoenix — unobservable and unsteerable. This is its replacement.
//
// Current model identities live in modelProfiles.ts. Configuration indicates
// credential/binding presence; account entitlement requires separate validation.
// ---------------------------------------------------------------------------

export type DeepProvider = DeepProviderId;

/** A resolved deep route: the AI-SDK model plus its identity for spans/scorecard. */
export interface DeepRoute {
  model: LanguageModel;
  provider: DeepProvider | "workers-ai";
  modelId: string;
  /** Safe routing explanation; never includes provider error bodies or secrets. */
  reason: string;
}

// Minimum scorecard sample size before a measured pass-rate is allowed to
// steer routing (mirrors the conservative gate in evals/store.ts).
const MODEL_SCORE_MIN_N = 8;

// Round-robin counter for the un-scored MiniMax/GLM balance (the "get better
// at the science" intent: spread deep load until the scorecard has signal).
// Durable via KV (env.CONFIG `rr:deep`) so break-in survives Worker isolate
// restarts — otherwise an unsampled provider can be starved indefinitely.
// The in-memory value is a best-effort fallback when KV is unavailable.
let rrCounter = 0;

async function nextRoundRobin(env: Env, mod: number): Promise<number> {
  if (mod <= 0) return 0;
  try {
    const raw = await env.CONFIG.get("rr:deep");
    const cur = raw ? parseInt(raw, 10) || 0 : 0;
    const next = (cur + 1) % 1_000_000;
    await env.CONFIG.put("rr:deep", String(next));
    return cur % mod;
  } catch {
    return rrCounter++ % mod;
  }
}

function zaiModel(env: Env) {
  return createOpenAICompatible({
    baseURL: env.ZAI_BASE_URL?.trim() || "https://api.z.ai/api/coding/paas/v4",
    apiKey: env.ZAI_API_KEY!,
    name: "zai",
  }).chatModel(resolveModelId(env, "zai"));
}

function openaiModel(env: Env) {
  // Prefer AI Gateway when configured
  const gateway = openaiViaGateway(env);
  if (gateway) return gateway;
  return createOpenAI({ apiKey: env.OPENAI_API_KEY! }).responses(resolveModelId(env, "openai"));
}

function anthropicModel(env: Env) {
  // Prefer AI Gateway when configured
  const gateway = anthropicViaGateway(env);
  if (gateway) return gateway;
  return createAnthropic({ apiKey: env.ANTHROPIC_API_KEY! }).languageModel(
    resolveModelId(env, "anthropic"),
  );
}

function googleModel(env: Env) {
  // Prefer AI Gateway when configured
  const gateway = googleViaGateway(env);
  if (gateway) return gateway;
  return createGoogleGenerativeAI({ apiKey: env.GOOGLE_API_KEY! })
    .languageModel(resolveModelId(env, "google"));
}

/** Deep providers whose credentials are present, in safe-default order. */
export function availableDeepProviders(env: Env): DeepProvider[] {
  return DEEP_PROVIDERS.filter((p) => configuredProvider(env, p));
}

function buildDeepRoute(env: Env, p: DeepProvider, modelOverride?: string, reason = "configured-provider"): DeepRoute {
  switch (p) {
    case "zai":
      return { model: zaiModel(env), provider: "zai", modelId: resolveModelId(env, "zai"), reason };
    case "openai":
      return { model: openaiModel(env), provider: "openai", modelId: resolveModelId(env, "openai"), reason };
    case "anthropic":
      return { model: anthropicModel(env), provider: "anthropic", modelId: resolveModelId(env, "anthropic"), reason };
    case "google":
      return { model: googleModel(env), provider: "google", modelId: resolveModelId(env, "google"), reason };
    default: {
      // modelOverride pins a specific MiniMax id (e.g. the M2.7→M3 A/B). Model
      // ids are provider-specific, so the override only applies to MiniMax.
      const modelId = modelOverride?.trim() || miniMaxConfig(env).model;
      return { model: miniMaxModel(env, modelId), provider: "minimax", modelId, reason };
    }
  }
}

function fastRoute(env: Env, reason: string): DeepRoute {
  return { model: fastModel(env), provider: "workers-ai", modelId: resolveModelId(env, "workers-ai"), reason };
}

/** Explicit workspace choice: reject unavailable/decision profiles rather than
 * silently substituting a different model. No model calls or metadata probes. */
export async function selectModelProfile(env: Env, profileId: string): Promise<DeepRoute> {
  const profile = getModelCatalog(env).profiles.find((p) => p.id === profileId);
  if (!profile) throw new Error("Unknown model profile.");
  if (profile.role === "decision") throw new Error("Decision profiles cannot generate chat replies.");
  if (!profile.configured) throw new Error("This model provider is not configured.");
  if (profile.provider === "minimax" && !(await hasMiniMaxBudget(env))) {
    throw new Error("The MiniMax monthly token budget is exhausted.");
  }
  return profile.provider === "workers-ai"
    ? { model: workersModel(env, profile.modelId), provider: "workers-ai", modelId: profile.modelId, reason: "selected-profile" }
    : buildDeepRoute(env, profile.provider, undefined, "selected-profile");
}

/**
 * Eval-aware deep-tier selection. Consults the latest ModelScorecard
 * (written hourly by the eval harness) and routes to the highest-scoring
 * well-sampled provider. Until the scorecard has signal, balances
 * configured providers round-robin and reserves OpenAI as the explicit
 * last decider (used when it is the only credentialed provider or when it
 * measurably wins). Always budget-guards MiniMax → Workers AI.
 */
export async function selectDeepRoute(
  env: Env,
  opts?: { force?: DeepProvider; modelOverride?: string },
): Promise<DeepRoute> {
  const selected = await selectDeepIdentity(env, opts);
  return selected.provider === "workers-ai"
    ? { ...selected, model: workersModel(env, selected.modelId) }
    : buildDeepRoute(env, selected.provider, selected.modelId, selected.reason);
}

async function selectDeepIdentity(env: Env, opts?: { force?: DeepProvider; modelOverride?: string }) {
  const candidates = availableDeepProviders(env);
  const modelOverride = opts?.modelOverride?.trim();
  const identity = (provider: DeepProvider | "workers-ai", reason: string, modelId?: string) => ({
    provider, modelId: modelId ?? resolveModelId(env, provider), reason,
  });
  // Explicit experiment pins retain the existing A/B semantics.
  if (modelOverride && candidates.includes("minimax") && (!opts?.force || opts.force === "minimax")) {
    return identity("minimax", "experiment-model-override", modelOverride);
  }
  if (opts?.force && candidates.includes(opts.force)) return identity(opts.force, "experiment-provider-override");

  const preferred = preferredDeepProvider(env);
  if (preferred === "workers-ai") {
    return identity("workers-ai", "preferred-provider", env.WORKERS_AI_DEEP_MODEL?.trim() || WORKERS_DEEP_PROFILE);
  }
  const missingPreference = Boolean(env.DEEP_PROVIDER?.trim()) && !preferred;
  if (candidates.length === 0) {
    return identity("workers-ai", missingPreference ? "preferred-provider-unavailable" : "no-deep-provider-configured");
  }
  let pool = candidates;
  const budgetExhausted = pool.includes("minimax") && !(await hasMiniMaxBudget(env));
  if (budgetExhausted) pool = pool.filter((p) => p !== "minimax");
  if (pool.length === 0) return identity("workers-ai", "minimax-budget-exhausted");
  if (preferred && pool.includes(preferred)) return identity(preferred, "preferred-provider");

  const fallbackReason = preferred === "minimax" && budgetExhausted ? "minimax-budget-exhausted"
    : missingPreference ? "preferred-provider-unavailable" : null;
  const trend = await getModelQualityTrend(env);
  const scored = pool.map((p) => ({ p, s: trend[p] }))
    .filter((x): x is { p: DeepProvider; s: { score: number; n: number } } => !!x.s && x.s.n >= MODEL_SCORE_MIN_N)
    .sort((a, b) => b.s.score - a.s.score);
  if (scored.length > 0) return identity(scored[0].p, fallbackReason ?? "quality-scorecard");
  const balance = pool.filter((p) => p !== "openai");
  const ring = balance.length > 0 ? balance : pool;
  return identity(ring[await nextRoundRobin(env, ring.length)], fallbackReason ?? "round-robin");
}

export interface ResearchTextOpts {
  prompt: string;
  system?: string;
  /** OpenInference functionId — the model×agent scorecard buckets on this. */
  agentClass: string;
  tier?: ReasoningTier;
  maxOutputTokens?: number;
  temperature?: number;
  /** Controlled A/B: pin the deep-tier provider (bypasses scorecard). */
  forceProvider?: DeepProvider;
  /** Controlled A/B: pin a specific MiniMax model id (e.g. "MiniMax-M2.7" vs
   * "MiniMax-M3"). Implies the minimax provider; bypasses scorecard/budget so
   * the M2.7→M3 quality delta is measured on exactly the requested id. */
  modelOverride?: string;
  /** Opt into multi-model coordination (Omnigents) instead of single-model
   * selection. When set, the call fans out across the provider pool and
   * reconciles per the resolved strategy (see src/agents/coordinator.ts).
   * Costs more tokens; reserve for high-stakes reasoning. */
  coordination?: {
    intent?: "trivial" | "reasoning" | "expert" | "classified" | "unknown";
    priority?: "low" | "normal" | "high";
    strategy?: "race" | "fan_out_merge" | "ensemble_of_experts" | "waterfall" | "specialist";
    confidenceThreshold?: number;
  };
}

/**
 * The single entry point for research narrative / hypothesis text. Replaces
 * `new ModelRouter(env).complete(...)`. Returns `{ text, provider, model }`
 * so existing call sites swap with no shape change, and every call lands as
 * an `ai.generateText` span attributed to `agentClass` (functionId) — which
 * is exactly what the OpenInference projector and eval scorecard consume.
 */
export async function generateResearchText(
  env: Env,
  opts: ResearchTextOpts,
): Promise<{ text: string; provider: string; model: string; routing?: { reason: string; fallbackFrom?: string } }> {
  const tier = opts.tier ?? "deep";

  // Opt-in multi-model coordination (Omnigents). Loaded lazily via dynamic
  // import to avoid a static models↔coordinator cycle. When requested, the
  // call fans out across the provider pool and reconciles per the resolved
  // strategy, then returns in the same {text, provider, model} shape so call
  // sites need no change. The coordination trace is persisted by coordinate().
  if (opts.coordination) {
    const { coordinate } = await import("./coordinator");
    const result = await coordinate(env, {
      prompt: opts.prompt,
      system: opts.system,
      agentClass: opts.agentClass,
      maxOutputTokens: opts.maxOutputTokens,
      temperature: opts.temperature,
      intent: opts.coordination.intent,
      priority: opts.coordination.priority,
      strategy: opts.coordination.strategy,
      confidenceThreshold: opts.coordination.confidenceThreshold,
    });
    return { text: result.text, provider: result.provider, model: result.model, routing: { reason: "coordination" } };
  }

  const route: DeepRoute =
    tier === "deep"
      ? await selectDeepRoute(env, { force: opts.forceProvider, modelOverride: opts.modelOverride })
      : fastRoute(env, "fast-tier");

  try {
    const result = await generateText({
      model: route.model,
      system: opts.system,
      prompt: opts.prompt,
      maxOutputTokens: opts.maxOutputTokens ?? 2048,
      // Reasoning models may reject sampling settings; omit for OpenAI.
      ...(route.provider === "openai" || opts.temperature === undefined
        ? {}
        : { temperature: opts.temperature }),
      experimental_telemetry: { isEnabled: true, functionId: opts.agentClass },
    });
    const text = (result.text ?? "").trim();
    if (!text) {
      throw emptyModelOutputError(route.provider, route.modelId, result.finishReason, result.usage);
    }
    return {
      text,
      provider: route.provider,
      model: route.modelId,
      routing: { reason: route.reason },
    };
  } catch (e) {
    // Merciless-but-safe: if a non-MiniMax route fails, fall back to the
    // proven MiniMax path once before surfacing the error.
    if (route.provider !== "minimax" && (await hasMiniMaxBudget(env))) {
      const fb = await generateText({
        model: miniMaxModel(env, opts.modelOverride),
        system: opts.system,
        prompt: opts.prompt,
        maxOutputTokens: opts.maxOutputTokens ?? 2048,
        ...(opts.temperature === undefined ? {} : { temperature: opts.temperature }),
        experimental_telemetry: { isEnabled: true, functionId: opts.agentClass },
      });
      const text = (fb.text ?? "").trim();
      if (!text) {
        throw emptyModelOutputError("minimax", opts.modelOverride?.trim() || miniMaxConfig(env).model, fb.finishReason, fb.usage);
      }
      return {
        text,
        provider: "minimax",
        model: opts.modelOverride?.trim() || miniMaxConfig(env).model,
        routing: { reason: "provider-failure", fallbackFrom: route.provider },
      };
    }
    throw e;
  }
}

// ---------------------------------------------------------------------------
// Per-provider primitive for the Omnigents coordinator
// (src/agents/coordinator.ts).
//
// Pins a SINGLE provider, calls it through the AI SDK with telemetry + spend
// recording, and returns the raw result WITHOUT generateResearchText's
// minimax fallback. The coordinator needs clean per-provider outcomes
// (succeeded / failed / timed_out) to score coordination effectiveness — a
// masked failure would corrupt that signal.
// ---------------------------------------------------------------------------

export interface ProviderCallOpts {
  prompt: string;
  system?: string;
  /** OpenInference functionId — the model×agent scorecard buckets on this. */
  agentClass: string;
  maxOutputTokens?: number;
  temperature?: number;
  /** Hard wall-clock budget per provider call (ms). */
  timeoutMs?: number;
}

export interface ProviderCallResult {
  text: string;
  provider: DeepProvider | "workers-ai";
  model: string;
  tokens: number;
  latencyMs: number;
  finishReason?: string;
}

/** The credentialed deep providers plus the always-on Workers AI fast tier. */
export function coordinatorPool(env: Env): Array<DeepProvider | "workers-ai"> {
  const pool: Array<DeepProvider | "workers-ai"> = ["workers-ai"];
  for (const p of availableDeepProviders(env)) {
    if (!pool.includes(p)) pool.push(p);
  }
  return pool;
}

/**
 * Call exactly one provider through the AI SDK. Used by the Omnigents
 * coordinator to fan out across the pool and reconcile. Throws on failure
 * (coordinator records the outcome); never silently falls back to another
 * provider.
 */
export async function generateForProvider(
  env: Env,
  provider: DeepProvider | "workers-ai",
  opts: ProviderCallOpts,
): Promise<ProviderCallResult> {
  const start = Date.now();
  const route: DeepRoute =
    provider === "workers-ai"
      ? fastRoute(env, "explicit-provider")
      : buildDeepRoute(env, provider);
  const result = await generateText({
    model: route.model,
    system: opts.system,
    prompt: opts.prompt,
    maxOutputTokens: coordinationOutputBudget(route.provider, opts.maxOutputTokens),
    ...(route.provider === "openai" || opts.temperature === undefined
      ? {}
      : { temperature: opts.temperature }),
    experimental_telemetry: { isEnabled: true, functionId: opts.agentClass },
    ...(opts.timeoutMs ? { abortSignal: AbortSignal.timeout(opts.timeoutMs) } : {}),
  });
  const usage = result.usage as {
    inputTokens?: number;
    outputTokens?: number;
    reasoningTokens?: number;
  } | undefined;
  const tokens =
    (usage?.inputTokens ?? 0) + (usage?.outputTokens ?? 0) + (usage?.reasoningTokens ?? 0);
  // Record spend directly (the DO-context middleware write is unreliable;
  // mirror the belt-and-braces approach in base.ts synthesize()).
  if (tokens > 0 && route.provider === "minimax") {
    try {
      await recordMiniMaxSpend(env, tokens);
    } catch {
      /* spend recording must never break a coordination call */
    }
  }
  return {
    text: (result.text ?? "").trim(),
    provider: route.provider,
    model: route.modelId,
    tokens,
    latencyMs: Date.now() - start,
    finishReason: result.finishReason,
  };
}

/** Resolve the single "strongest" provider for judge/critic roles. */
export function pickStrongProvider(env: Env): DeepProvider | "workers-ai" {
  const pool = availableDeepProviders(env);
  // Prefer the strength-first last decider (OpenAI), then Anthropic, then MiniMax, then GLM, then Google.
  if (pool.includes("openai")) return "openai";
  if (pool.includes("anthropic")) return "anthropic";
  if (pool.includes("minimax")) return "minimax";
  if (pool.includes("zai")) return "zai";
  if (pool.includes("google")) return "google";
  return "workers-ai";
}

/**
 * The scorecard-aware routing DECISION without the (eager) model construction
 * that selectDeepRoute performs. Used by the coordinator's specialist strategy
 * so it can pick a provider identity and then call it through the injected
 * callProvider (which builds the model once) instead of building it twice.
 * Shares the same decision implementation as selectDeepRoute.
 */
export async function selectDeepProviderId(
  env: Env,
  opts?: { force?: DeepProvider; modelOverride?: string },
): Promise<DeepProvider | "workers-ai"> {
  return (await selectDeepIdentity(env, opts)).provider;
}
