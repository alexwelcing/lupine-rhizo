import { describe, it, expect } from "vitest";
import {
  gatewayEnabled,
  gatewayModel,
  openaiViaGateway,
  anthropicViaGateway,
  googleViaGateway,
  workersAiViaGateway,
  type GatewayProvider,
} from "../gateway";
import type { Env } from "../../types";

function mockEnv(overrides: Partial<Env> = {}): Env {
  return {
    AI: {} as Env["AI"],
    ARTIFACTS: {} as Env["ARTIFACTS"],
    CONFIG: {} as Env["CONFIG"],
    LEDGER: {} as Env["LEDGER"],
    RESEARCH_QUEUE: {} as Env["RESEARCH_QUEUE"],
    ORCHESTRATOR: {} as Env["ORCHESTRATOR"],
    MANIFOLD_AGENT: {} as Env["MANIFOLD_AGENT"],
    CAUSAL_AGENT: {} as Env["CAUSAL_AGENT"],
    THEORIST_AGENT: {} as Env["THEORIST_AGENT"],
    EXPERIMENT_AGENT: {} as Env["EXPERIMENT_AGENT"],
    FLEET_ORCHESTRATOR: {} as Env["FLEET_ORCHESTRATOR"],
    DASHBOARD: {} as Env["DASHBOARD"],
    EXTENSION_MANAGER: {} as Env["EXTENSION_MANAGER"],
    LITERATURIST_AGENT: {} as Env["LITERATURIST_AGENT"],
    ...overrides,
  } as Env;
}

describe("gatewayEnabled", () => {
  it("returns false when AI_GATEWAY_ACCOUNT_ID is missing", () => {
    const env = mockEnv({ AI_GATEWAY_ID: "gateway-1" });
    expect(gatewayEnabled(env)).toBe(false);
  });

  it("returns false when AI_GATEWAY_ID is missing", () => {
    const env = mockEnv({ AI_GATEWAY_ACCOUNT_ID: "account-1" });
    expect(gatewayEnabled(env)).toBe(false);
  });

  it("returns true when both AI_GATEWAY_ACCOUNT_ID and AI_GATEWAY_ID are present", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
    });
    expect(gatewayEnabled(env)).toBe(true);
  });

  it("returns false for whitespace-only values", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "   ",
      AI_GATEWAY_ID: "gateway-1",
    });
    expect(gatewayEnabled(env)).toBe(false);
  });
});

describe("openaiViaGateway", () => {
  it("returns undefined when gateway is not configured", () => {
    const env = mockEnv({ OPENAI_API_KEY: "sk-test" });
    expect(openaiViaGateway(env)).toBeUndefined();
  });

  it("returns undefined when OPENAI_API_KEY is missing", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
    });
    expect(openaiViaGateway(env)).toBeUndefined();
  });

  it("returns a model when gateway and API key are configured", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      OPENAI_API_KEY: "sk-test",
    });
    const model = openaiViaGateway(env);
    expect(model).toBeDefined();
  });
});

describe("anthropicViaGateway", () => {
  it("returns undefined when gateway is not configured", () => {
    const env = mockEnv({ ANTHROPIC_API_KEY: "sk-test" });
    expect(anthropicViaGateway(env)).toBeUndefined();
  });

  it("returns undefined when ANTHROPIC_API_KEY is missing", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
    });
    expect(anthropicViaGateway(env)).toBeUndefined();
  });

  it("returns a model when gateway and API key are configured", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      ANTHROPIC_API_KEY: "sk-test",
    });
    const model = anthropicViaGateway(env);
    expect(model).toBeDefined();
  });
});

describe("googleViaGateway", () => {
  it("returns undefined when gateway is not configured", () => {
    const env = mockEnv({ GOOGLE_API_KEY: "test-key" });
    expect(googleViaGateway(env)).toBeUndefined();
  });

  it("returns undefined when GOOGLE_API_KEY is missing", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
    });
    expect(googleViaGateway(env)).toBeUndefined();
  });

  it("returns a model when gateway and API key are configured", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      GOOGLE_API_KEY: "test-key",
    });
    const model = googleViaGateway(env);
    expect(model).toBeDefined();
  });
});

describe("workersAiViaGateway", () => {
  it("returns undefined when gateway is not configured", () => {
    const env = mockEnv({});
    expect(workersAiViaGateway(env)).toBeUndefined();
  });

  it("returns a model when gateway is configured (no API key needed)", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
    });
    const model = workersAiViaGateway(env);
    expect(model).toBeDefined();
  });
});

describe("gatewayModel", () => {
  it("returns undefined when gateway is not enabled", () => {
    const env = mockEnv({
      OPENAI_API_KEY: "sk-test",
      ANTHROPIC_API_KEY: "sk-test",
      GOOGLE_API_KEY: "test-key",
    });
    expect(gatewayModel(env, "openai")).toBeUndefined();
    expect(gatewayModel(env, "anthropic")).toBeUndefined();
    expect(gatewayModel(env, "google-vertex-ai")).toBeUndefined();
    expect(gatewayModel(env, "workers-ai")).toBeUndefined();
  });

  it("returns a route for each provider when configured", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      OPENAI_API_KEY: "sk-test",
      ANTHROPIC_API_KEY: "sk-test",
      GOOGLE_API_KEY: "test-key",
    });

    const openaiRoute = gatewayModel(env, "openai");
    expect(openaiRoute).toBeDefined();
    expect(openaiRoute?.provider).toBe("openai");
    expect(openaiRoute?.modelId).toBe("gpt-5.5");

    const anthropicRoute = gatewayModel(env, "anthropic");
    expect(anthropicRoute).toBeDefined();
    expect(anthropicRoute?.provider).toBe("anthropic");

    const googleRoute = gatewayModel(env, "google-vertex-ai");
    expect(googleRoute).toBeDefined();
    expect(googleRoute?.provider).toBe("google-vertex-ai");

    const workersRoute = gatewayModel(env, "workers-ai");
    expect(workersRoute).toBeDefined();
    expect(workersRoute?.provider).toBe("workers-ai");
  });

  it("uses custom model IDs when provided", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      OPENAI_API_KEY: "sk-test",
      OPENAI_MODEL: "gpt-5",
    });

    const route = gatewayModel(env, "openai");
    expect(route?.modelId).toBe("gpt-5");
  });

  it("uses env model IDs when no override is provided", () => {
    const env = mockEnv({
      AI_GATEWAY_ACCOUNT_ID: "account-1",
      AI_GATEWAY_ID: "gateway-1",
      OPENAI_API_KEY: "sk-test",
      OPENAI_MODEL: "custom-model",
    });

    const route = gatewayModel(env, "openai");
    expect(route?.modelId).toBe("custom-model");
  });
});
