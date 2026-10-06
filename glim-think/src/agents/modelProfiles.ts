/** Model identities shared by runtime routing, Gateway and the operator UI.
 * This module never constructs clients, exposes credentials, or makes requests.
 * `configured` checks presence only; provider account entitlement is unverified.
 */
import type { Env } from "../types";

export const DEEP_PROVIDERS = ["minimax", "zai", "openai", "anthropic", "google"] as const;
export type DeepProviderId = typeof DEEP_PROVIDERS[number];
export type ModelProviderId = DeepProviderId | "workers-ai";
export type ModelRole = "fast" | "deep" | "decision";

export const MODEL_DEFAULTS = {
  "workers-ai": "@cf/meta/llama-4-scout-17b-16e-instruct",
  minimax: "MiniMax-M3",
  zai: "glm-5.3",
  openai: "gpt-6.1-sol",
  anthropic: "claude-sonnet-5-5",
  google: "gemini-3.8-flash",
} as const;
export const WORKERS_FAST_PROFILE = "@cf/zai-org/glm-5.3-flash";
export const WORKERS_DEEP_PROFILE = "@cf/moonshotai/kimi-k2.6";
export const CLEF_DECISION_MODEL = "@cf/cloudflare/clef-flash";

const MODEL_ENV = {
  "workers-ai": "WORKERS_AI_MODEL", minimax: "MINIMAX_MODEL", zai: "ZAI_MODEL",
  openai: "OPENAI_MODEL", anthropic: "ANTHROPIC_MODEL", google: "GOOGLE_MODEL",
} as const;
const KEY_ENV = {
  minimax: "MINIMAX_API_KEY", zai: "ZAI_API_KEY", openai: "OPENAI_API_KEY",
  anthropic: "ANTHROPIC_API_KEY", google: "GOOGLE_API_KEY",
} as const;
const SOURCES = {
  "workers-ai": "https://developers.cloudflare.com/workers-ai/models/llama-4-scout-17b-16e-instruct/",
  minimax: "https://platform.minimax.io/docs/guides/text-generation",
  zai: "https://docs.z.ai/guides/llm/glm-5.3",
  openai: "https://developers.openai.com/api/docs/guides/latest-model",
  anthropic: "https://platform.claude.com/docs/en/models/overview",
  google: "https://ai.google.dev/gemini-api/docs/models",
} as const;

export function configuredProvider(env: Env, provider: ModelProviderId): boolean {
  return provider === "workers-ai" ? Boolean(env.AI) : Boolean(env[KEY_ENV[provider]]?.trim());
}

export function resolveModelId(env: Env, provider: ModelProviderId): string {
  return env[MODEL_ENV[provider]]?.trim() || MODEL_DEFAULTS[provider];
}

/** A preference never grants access to a provider or changes its credentials. */
export function preferredDeepProvider(env: Env): ModelProviderId | null {
  const value = env.DEEP_PROVIDER?.trim();
  if (value === "workers-ai" || DEEP_PROVIDERS.some((p) => p === value)) {
    return configuredProvider(env, value as ModelProviderId) ? value as ModelProviderId : null;
  }
  return null;
}

export interface ModelSelection {
  provider: ModelProviderId;
  modelId: string;
  reason: string;
}

/** Synchronous Think getModel selection; async turns additionally check budget/evals. */
export function getInteractiveDeepSelection(env: Env): ModelSelection {
  const preferred = preferredDeepProvider(env);
  const provider = preferred ?? DEEP_PROVIDERS.find((p) => configuredProvider(env, p)) ?? "workers-ai";
  return {
    provider,
    modelId: preferred === "workers-ai"
      ? env.WORKERS_AI_DEEP_MODEL?.trim() || WORKERS_DEEP_PROFILE
      : resolveModelId(env, provider),
    reason: preferred ? "preferred-provider" : env.DEEP_PROVIDER?.trim()
      ? "preferred-provider-unavailable" : provider === "workers-ai" ? "no-deep-provider-configured" : "configured-provider",
  };
}

export interface ModelProfile {
  id: string;
  label: string;
  role: ModelRole;
  provider: ModelProviderId;
  modelId: string;
  defaultModelId: string;
  configured: boolean;
  availability: "configured-unverified" | "not-configured";
  sourceUrl: string;
}

export function getModelCatalog(env: Env) {
  const profile = (id: string, label: string, role: ModelRole, provider: ModelProviderId,
    modelId: string, defaultModelId: string, sourceUrl: string): ModelProfile => {
    const configured = configuredProvider(env, provider);
    return { id, label, role, provider, modelId, defaultModelId, configured,
      availability: configured ? "configured-unverified" : "not-configured", sourceUrl };
  };
  return {
    catalogVersion: "2026-10-05",
    accountAvailability: "unverified" as const,
    preferredDeepProvider: preferredDeepProvider(env),
    selectionStrategy: preferredDeepProvider(env) ? "preferred-provider" : "eval-aware" as const,
    interactiveDeep: getInteractiveDeepSelection(env),
    profiles: [
      profile("fast", "Configured fast model", "fast", "workers-ai", resolveModelId(env, "workers-ai"), MODEL_DEFAULTS["workers-ai"], SOURCES["workers-ai"]),
      profile("workers-flash", "GLM 5.3 Flash · fast", "fast", "workers-ai", WORKERS_FAST_PROFILE, WORKERS_FAST_PROFILE, "https://developers.cloudflare.com/workers-ai/models/glm-5.3-flash/"),
      profile("workers-deep", "Kimi K2.6 · deep", "deep", "workers-ai", env.WORKERS_AI_DEEP_MODEL?.trim() || WORKERS_DEEP_PROFILE, WORKERS_DEEP_PROFILE, "https://developers.cloudflare.com/workers-ai/models/kimi-k2.6/"),
      ...DEEP_PROVIDERS.map((p) => profile(p, p, "deep", p, resolveModelId(env, p), MODEL_DEFAULTS[p], SOURCES[p])),
      profile("clef", "Clef Flash · decisions only", "decision", "workers-ai", CLEF_DECISION_MODEL, CLEF_DECISION_MODEL, "https://developers.cloudflare.com/workers-ai/models/clef-flash/"),
    ],
  };
}
