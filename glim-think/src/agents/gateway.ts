/**
 * Cloudflare AI Gateway integration for glim-think.
 *
 * Provides unified routing, caching, retries, and cost tracking for
 * OpenAI, Anthropic, and Google model calls through Cloudflare AI Gateway.
 *
 * URL format:
 *   https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/{provider}
 *
 * Supported providers: openai, anthropic, google-vertex-ai, workers-ai
 * The gateway exposes provider-native endpoints (e.g. /v1/chat/completions
 * for OpenAI, /v1/messages for Anthropic).
 */
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { createOpenAI } from "@ai-sdk/openai";
import { createAnthropic } from "@ai-sdk/anthropic";
import type { LanguageModel } from "ai";
import type { Env } from "../types";

const GATEWAY_BASE = "https://gateway.ai.cloudflare.com/v1";

export type GatewayProvider = "openai" | "anthropic" | "google-vertex-ai" | "workers-ai";

function gatewayBaseURL(env: Env, provider: GatewayProvider): string | undefined {
  const accountId = env.AI_GATEWAY_ACCOUNT_ID?.trim();
  const gatewayId = env.AI_GATEWAY_ID?.trim();
  if (!accountId || !gatewayId) return undefined;
  return `${GATEWAY_BASE}/${accountId}/${gatewayId}/${provider}`;
}

export function gatewayEnabled(env: Env): boolean {
  return !!(env.AI_GATEWAY_ACCOUNT_ID?.trim() && env.AI_GATEWAY_ID?.trim());
}

/** Build headers for authenticated gateway (cf-aig-authorization). */
function gatewayHeaders(env: Env): Record<string, string> | undefined {
  const token = env.AI_GATEWAY_TOKEN?.trim();
  if (!token) return undefined;
  return { "cf-aig-authorization": `Bearer ${token}` };
}

// ---------------------------------------------------------------------------
// Provider-specific gateway wrappers
// ---------------------------------------------------------------------------

/** OpenAI via AI Gateway. */
export function openaiViaGateway(env: Env): LanguageModel | undefined {
  const baseURL = gatewayBaseURL(env, "openai");
  if (!baseURL || !env.OPENAI_API_KEY) return undefined;
  const headers = gatewayHeaders(env);
  return createOpenAI({
    apiKey: env.OPENAI_API_KEY,
    baseURL,
    ...(headers ? { headers } : {}),
  })(env.OPENAI_MODEL?.trim() || "gpt-5.5");
}

/** Anthropic via AI Gateway. */
export function anthropicViaGateway(env: Env): LanguageModel | undefined {
  const baseURL = gatewayBaseURL(env, "anthropic");
  if (!baseURL || !env.ANTHROPIC_API_KEY) return undefined;
  const headers = gatewayHeaders(env);
  return createAnthropic({
    apiKey: env.ANTHROPIC_API_KEY,
    baseURL,
    ...(headers ? { headers } : {}),
  }).languageModel(env.ANTHROPIC_MODEL?.trim() || "claude-sonnet-4-20250514");
}

/** Google Vertex AI via AI Gateway. */
export function googleViaGateway(env: Env): LanguageModel | undefined {
  const baseURL = gatewayBaseURL(env, "google-vertex-ai");
  if (!baseURL || !env.GOOGLE_API_KEY) return undefined;
  const headers = gatewayHeaders(env);
  // Google Vertex AI exposes an OpenAI-compatible chat completions endpoint
  // through AI Gateway, so we drive it via @ai-sdk/openai-compatible.
  return createOpenAICompatible({
    name: "google-vertex-ai",
    apiKey: env.GOOGLE_API_KEY,
    baseURL,
    ...(headers ? { headers } : {}),
  }).chatModel(env.GOOGLE_MODEL?.trim() || "gemini-2.5-pro");
}

/** Workers AI via AI Gateway (unified compat endpoint). */
export function workersAiViaGateway(env: Env): LanguageModel | undefined {
  const baseURL = gatewayBaseURL(env, "workers-ai");
  if (!baseURL) return undefined;
  const headers = gatewayHeaders(env);
  return createOpenAICompatible({
    name: "workers-ai",
    apiKey: "", // Workers AI binding auth is handled by gateway
    baseURL,
    ...(headers ? { headers } : {}),
  }).chatModel(env.WORKERS_AI_MODEL?.trim() || "@cf/meta/llama-4-scout-17b-16e-instruct");
}

// ---------------------------------------------------------------------------
// Unified gateway model resolver
// ---------------------------------------------------------------------------

export interface GatewayRoute {
  model: LanguageModel;
  provider: GatewayProvider | "direct";
  modelId: string;
}

/**
 * Resolve a model through AI Gateway when credentials and gateway config
 * are present. Falls back to `undefined` so the caller can use the direct
 * provider path.
 */
export function gatewayModel(
  env: Env,
  provider: GatewayProvider,
  modelId?: string,
): GatewayRoute | undefined {
  if (!gatewayEnabled(env)) return undefined;

  switch (provider) {
    case "openai": {
      const m = openaiViaGateway(env);
      if (!m) return undefined;
      return { model: m, provider: "openai", modelId: modelId || env.OPENAI_MODEL?.trim() || "gpt-5.5" };
    }
    case "anthropic": {
      const m = anthropicViaGateway(env);
      if (!m) return undefined;
      return { model: m, provider: "anthropic", modelId: modelId || env.ANTHROPIC_MODEL?.trim() || "claude-sonnet-4-20250514" };
    }
    case "google-vertex-ai": {
      const m = googleViaGateway(env);
      if (!m) return undefined;
      return { model: m, provider: "google-vertex-ai", modelId: modelId || env.GOOGLE_MODEL?.trim() || "gemini-2.5-pro" };
    }
    case "workers-ai": {
      const m = workersAiViaGateway(env);
      if (!m) return undefined;
      return { model: m, provider: "workers-ai", modelId: modelId || env.WORKERS_AI_MODEL?.trim() || "@cf/meta/llama-4-scout-17b-16e-instruct" };
    }
    default:
      return undefined;
  }
}

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

export interface GatewayProbeResult {
  ok: boolean;
  provider: GatewayProvider;
  base_url: string;
  latency_ms: number;
  status?: number;
  error?: string;
}

/**
 * Probe a single provider through AI Gateway with a minimal request.
 * Uses the provider's native health/model-list endpoint where possible.
 */
export async function probeGatewayProvider(
  env: Env,
  provider: GatewayProvider,
): Promise<GatewayProbeResult> {
  const baseURL = gatewayBaseURL(env, provider);
  if (!baseURL) {
    return { ok: false, provider, base_url: "", latency_ms: 0, error: "AI Gateway not configured (missing AI_GATEWAY_ACCOUNT_ID or AI_GATEWAY_ID)" };
  }

  const start = Date.now();
  try {
    // Use the provider's models endpoint as a lightweight probe
    const probeURL = `${baseURL}/v1/models`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Attach provider API key
    if (provider === "openai" && env.OPENAI_API_KEY) {
      headers["Authorization"] = `Bearer ${env.OPENAI_API_KEY}`;
    } else if (provider === "anthropic" && env.ANTHROPIC_API_KEY) {
      headers["x-api-key"] = env.ANTHROPIC_API_KEY;
      headers["anthropic-version"] = "2023-06-01";
    } else if (provider === "google-vertex-ai" && env.GOOGLE_API_KEY) {
      headers["Authorization"] = `Bearer ${env.GOOGLE_API_KEY}`;
    }

    const gatewayHeaders_ = gatewayHeaders(env);
    if (gatewayHeaders_) {
      Object.assign(headers, gatewayHeaders_);
    }

    const res = await fetch(probeURL, { method: "GET", headers });
    const latency = Date.now() - start;

    // 200 = models list available; 404 = routed correctly but no models endpoint
    // Both indicate the gateway is reachable and routing.
    if (res.ok || res.status === 404) {
      return {
        ok: true,
        provider,
        base_url: baseURL,
        latency_ms: latency,
        status: res.status,
      };
    }

    const text = await res.text().catch(() => "");
    return {
      ok: false,
      provider,
      base_url: baseURL,
      latency_ms: latency,
      status: res.status,
      error: `HTTP ${res.status}: ${text.slice(0, 500)}`,
    };
  } catch (e) {
    return {
      ok: false,
      provider,
      base_url: baseURL,
      latency_ms: Date.now() - start,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

/**
 * Probe all configured gateway providers and return a summary.
 */
export async function probeGateway(env: Env): Promise<{
  gateway_enabled: boolean;
  account_id?: string;
  gateway_id?: string;
  results: GatewayProbeResult[];
}> {
  const enabled = gatewayEnabled(env);
  const providers: GatewayProvider[] = ["openai", "anthropic", "google-vertex-ai", "workers-ai"];
  const results = await Promise.all(
    providers.map((p) => probeGatewayProvider(env, p)),
  );
  return {
    gateway_enabled: enabled,
    account_id: env.AI_GATEWAY_ACCOUNT_ID?.trim(),
    gateway_id: env.AI_GATEWAY_ID?.trim(),
    results,
  };
}
