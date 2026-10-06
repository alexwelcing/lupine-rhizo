import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Env } from "../../types";

const mocks = vi.hoisted(() => ({
  generate: vi.fn(), quality: vi.fn(),
  factory: vi.fn((provider: string, config: unknown, modelId: string, settings?: unknown) => ({
    provider, config, modelId, settings,
  })),
}));
vi.mock("workers-ai-provider", () => ({ createWorkersAI: (config: unknown) =>
  (id: string, settings: unknown) => mocks.factory("workers-ai", config, id, settings) }));
vi.mock("@ai-sdk/openai", () => ({ createOpenAI: (config: unknown) => ({
  responses: (id: string) => mocks.factory("openai.responses", config, id),
}) }));
vi.mock("@ai-sdk/anthropic", () => ({ createAnthropic: (config: unknown) => ({
  languageModel: (id: string) => mocks.factory("anthropic", config, id),
}) }));
vi.mock("@ai-sdk/google", () => ({ createGoogleGenerativeAI: (config: unknown) => ({
  languageModel: (id: string) => mocks.factory("google", config, id),
}) }));
vi.mock("@ai-sdk/openai-compatible", () => ({ createOpenAICompatible: (config: unknown) => ({
  chatModel: (id: string) => mocks.factory("compatible", config, id),
}) }));
vi.mock("ai", () => ({ generateText: mocks.generate, wrapLanguageModel: ({ model }: { model: unknown }) => model }));
vi.mock("../../evals/store", () => ({ getModelQualityTrend: mocks.quality }));

import { getModelCatalog, MODEL_DEFAULTS, WORKERS_FAST_PROFILE, WORKERS_DEEP_PROFILE } from "../modelProfiles";
import { fastModel, generateForProvider, generateResearchText, selectDeepRoute, selectModel, selectModelProfile } from "../models";
import { gatewayModel } from "../gateway";

function env(overrides: Partial<Env> = {}): Env {
  return { AI: {}, CONFIG: { get: vi.fn().mockResolvedValue(null), put: vi.fn() }, ...overrides } as unknown as Env;
}
const modelIdentity = (model: unknown) => model as { modelId: string; provider: string; config: { baseURL?: string }; settings?: unknown };
const exhausted = () => ({ get: vi.fn(async (key: string) => key.startsWith("budget:") ? JSON.stringify({ tokens: 500_000_000 }) : null), put: vi.fn() }) as unknown as KVNamespace;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.quality.mockResolvedValue({});
  mocks.generate.mockResolvedValue({ text: "answer", finishReason: "stop", usage: {} });
});

describe("safe model catalog", () => {
  it("exposes modern generation choices and a separate decision-only Clef role", () => {
    const catalog = getModelCatalog(env());
    expect(catalog.accountAvailability).toBe("unverified");
    expect(catalog.profiles.find(p => p.id === "workers-flash")).toMatchObject({ modelId: WORKERS_FAST_PROFILE, role: "fast", availability: "configured-unverified" });
    expect(catalog.profiles.find(p => p.id === "workers-deep")).toMatchObject({ modelId: WORKERS_DEEP_PROFILE, role: "deep" });
    expect(catalog.profiles.find(p => p.id === "clef")?.role).toBe("decision");
    expect(MODEL_DEFAULTS).toMatchObject({ minimax: "MiniMax-M3", openai: "gpt-6.1-sol", anthropic: "claude-sonnet-5-5", zai: "glm-5.3", google: "gemini-3.8-flash" });
  });

  it("reports credential presence without returning secrets or account metadata", () => {
    const catalog = getModelCatalog(env({ OPENAI_API_KEY: "test-private-key", AI_GATEWAY_TOKEN: "test-private-gateway", AI_GATEWAY_ACCOUNT_ID: "private-account", ZAI_API_KEY: "  " }));
    const serialized = JSON.stringify(catalog);
    expect(serialized).not.toMatch(/test-private|private-account/);
    expect(catalog.profiles.find(p => p.id === "openai")?.configured).toBe(true);
    expect(catalog.profiles.find(p => p.id === "zai")?.configured).toBe(false);
    expect(mocks.generate).not.toHaveBeenCalled();
  });
});

describe("model selection identity and policy", () => {
  it("honors Workers overrides in fast, fallback and coordinator identities", async () => {
    const configured = env({ WORKERS_AI_MODEL: "@cf/custom/model" });
    expect(modelIdentity(fastModel(configured)).modelId).toBe("@cf/custom/model");
    expect(await selectDeepRoute(configured)).toMatchObject({ provider: "workers-ai", modelId: "@cf/custom/model", reason: "no-deep-provider-configured" });
    expect(await generateForProvider(configured, "workers-ai", { prompt: "test", agentClass: "Test" })).toMatchObject({ model: "@cf/custom/model" });
  });

  it("uses an OpenAI-only credential in synchronous and async deep paths via Responses", async () => {
    const configured = env({ OPENAI_API_KEY: "test" });
    expect(modelIdentity(selectModel(configured, "deep"))).toMatchObject({ provider: "openai.responses", modelId: MODEL_DEFAULTS.openai });
    expect(await selectDeepRoute(configured)).toMatchObject({ provider: "openai", modelId: MODEL_DEFAULTS.openai });
  });

  it("honors a configured preferred provider and never grants missing credentials", async () => {
    const configured = env({ MINIMAX_API_KEY: "test", ANTHROPIC_API_KEY: "test", DEEP_PROVIDER: "anthropic", ANTHROPIC_MODEL: "custom-sonnet" });
    expect(modelIdentity(selectModel(configured, "deep")).modelId).toBe("custom-sonnet");
    expect(await selectDeepRoute(configured)).toMatchObject({ provider: "anthropic", modelId: "custom-sonnet", reason: "preferred-provider" });
    expect(await selectDeepRoute(env({ DEEP_PROVIDER: "openai" }))).toMatchObject({ provider: "workers-ai", reason: "preferred-provider-unavailable" });
  });

  it("guards a preferred MiniMax budget and preserves explicit experiment pins", async () => {
    const configured = env({ MINIMAX_API_KEY: "test", DEEP_PROVIDER: "minimax", CONFIG: exhausted() });
    expect(await selectDeepRoute(configured)).toMatchObject({ provider: "workers-ai", reason: "minimax-budget-exhausted" });
    expect(await selectDeepRoute(configured, { modelOverride: "MiniMax-M2.7" })).toMatchObject({ provider: "minimax", modelId: "MiniMax-M2.7", reason: "experiment-model-override" });
    await expect(selectModelProfile(configured, "minimax")).rejects.toThrow("budget is exhausted");
  });

  it("keeps scorecard routing and reports its reason", async () => {
    mocks.quality.mockResolvedValue({ openai: { score: 0.95, n: 10 }, zai: { score: 0.7, n: 10 } });
    expect(await selectDeepRoute(env({ OPENAI_API_KEY: "test", ZAI_API_KEY: "test" }))).toMatchObject({ provider: "openai", reason: "quality-scorecard" });
  });

  it("keeps modern Workers profiles explicit and chooses low reasoning for Flash", async () => {
    const flash = await selectModelProfile(env(), "workers-flash");
    expect(flash).toMatchObject({ provider: "workers-ai", modelId: WORKERS_FAST_PROFILE, reason: "selected-profile" });
    expect(modelIdentity(flash.model).settings).toEqual({ reasoning_effort: "low" });
    expect(await selectDeepRoute(env({ DEEP_PROVIDER: "workers-ai", WORKERS_AI_DEEP_MODEL: "@cf/custom/deep" }))).toMatchObject({ modelId: "@cf/custom/deep" });
    await expect(selectModelProfile(env(), "clef")).rejects.toThrow("Decision profiles");
    await expect(selectModelProfile(env(), "openai")).rejects.toThrow("not configured");
    await expect(selectModelProfile(env(), "invented")).rejects.toThrow("Unknown");
  });
});

describe("runtime fallback", () => {
  it("does not reopen an exhausted MiniMax budget after another provider fails", async () => {
    mocks.generate.mockRejectedValue(new Error("primary failed"));
    await expect(generateResearchText(env({ OPENAI_API_KEY: "test", MINIMAX_API_KEY: "test", CONFIG: exhausted() }), { prompt: "test", agentClass: "Test" })).rejects.toThrow("primary failed");
    expect(mocks.generate).toHaveBeenCalledTimes(1);
  });

  it("reports the actual fallback provider and model when a budgeted fallback succeeds", async () => {
    mocks.generate.mockRejectedValueOnce(new Error("primary failed")).mockResolvedValueOnce({ text: "fallback", usage: {} });
    expect(await generateResearchText(env({ OPENAI_API_KEY: "test", MINIMAX_API_KEY: "test", MINIMAX_MODEL: "MiniMax-M2.7", DEEP_PROVIDER: "openai" }), { prompt: "test", agentClass: "Test" })).toMatchObject({ provider: "minimax", model: "MiniMax-M2.7", routing: { reason: "provider-failure", fallbackFrom: "openai" } });
    expect(mocks.generate).toHaveBeenCalledTimes(2);
  });
});

describe("gateway model identity", () => {
  it("passes an explicit model to the SDK as well as route metadata", () => {
    const route = gatewayModel(env({ OPENAI_API_KEY: "test", AI_GATEWAY_ACCOUNT_ID: "test-account", AI_GATEWAY_ID: "test-gateway" }), "openai", "custom-openai");
    expect(route?.modelId).toBe("custom-openai");
    expect(modelIdentity(route?.model)).toMatchObject({ provider: "openai.responses", modelId: "custom-openai", config: { baseURL: "https://gateway.ai.cloudflare.com/v1/test-account/test-gateway/openai" } });
  });

  it("keeps Google and Anthropic native endpoints while honoring configured models", () => {
    const configured = env({ GOOGLE_API_KEY: "test", ANTHROPIC_API_KEY: "test", AI_GATEWAY_ACCOUNT_ID: "account", AI_GATEWAY_ID: "gateway" });
    const google = gatewayModel(configured, "google-ai-studio", "custom-gemini");
    expect(google).toMatchObject({ provider: "google-ai-studio", modelId: "custom-gemini" });
    expect(modelIdentity(google?.model)).toMatchObject({ provider: "google", modelId: "custom-gemini", config: { baseURL: "https://gateway.ai.cloudflare.com/v1/account/gateway/google-ai-studio/v1beta" } });
    const anthropic = gatewayModel(configured, "anthropic");
    expect(modelIdentity(anthropic?.model).config.baseURL).toBe("https://gateway.ai.cloudflare.com/v1/account/gateway/anthropic/v1");
    expect(gatewayModel(configured, "google-vertex-ai")?.provider).toBe("google-ai-studio");
  });
});
