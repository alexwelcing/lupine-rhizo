import { afterEach, describe, expect, it, vi } from "vitest";
import { gatewayModel, type GatewayProvider } from "../gateway";
import type { Env } from "../../types";

afterEach(() => vi.unstubAllGlobals());

describe("native Gateway request formats (no network)", () => {
  it.each([
    ["openai", "/openai/responses", "authorization", "Bearer provider-test", "input"],
    ["anthropic", "/anthropic/v1/messages", "x-api-key", "provider-test", "messages"],
    ["google-ai-studio", "/google-ai-studio/v1beta/models/gemini-3.8-flash:generateContent", "x-goog-api-key", "provider-test", "contents"],
  ] as const)("uses the %s native wire format", async (provider, suffix, header, key, bodyField) => {
    const intercepted = vi.fn(async () => { throw new Error("intercepted before network"); });
    vi.stubGlobal("fetch", intercepted);
    const env = {
      OPENAI_API_KEY: "provider-test", ANTHROPIC_API_KEY: "provider-test", GOOGLE_API_KEY: "provider-test",
      AI_GATEWAY_ACCOUNT_ID: "account", AI_GATEWAY_ID: "gateway", AI_GATEWAY_TOKEN: "gateway-test",
    } as Env;
    const route = gatewayModel(env, provider as GatewayProvider)!;
    const model = route.model;
    if (typeof model === "string") throw new Error("Expected a constructed provider model");
    await expect(model.doGenerate({
      prompt: [{ role: "user", content: [{ type: "text", text: "test" }] }],
      maxOutputTokens: 32,
    })).rejects.toThrow();
    expect(intercepted).toHaveBeenCalledTimes(1);
    const [url, request] = intercepted.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`https://gateway.ai.cloudflare.com/v1/account/gateway${suffix}`);
    const headers = new Headers(request.headers);
    expect(headers.get(header)).toBe(key);
    expect(headers.get("cf-aig-authorization")).toBe("Bearer gateway-test");
    const body = JSON.parse(String(request.body));
    expect(body[bodyField]).toBeInstanceOf(Array);
    if (provider !== "google-ai-studio") expect(body.model).toBe(route.modelId);
  });
});
