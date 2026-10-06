import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { readPreviewSettings } from "../../../hosted-preview/settings";
import { workspacePreviewEnv } from "../../../hosted-preview/environment";
import { getModelCatalog } from "../../agents/modelProfiles";
import type { Env } from "../../types";

const doubles = vi.hoisted(() => ({ route: vi.fn() }));
vi.mock("agents", () => ({ routeAgentRequest: doubles.route }));
vi.mock("../html", () => ({ workspaceHtml: () => "<html><body>Workspace</body></html>", workspaceJavaScript: "// preview test" }));
import { previewFetch } from "../../../hosted-preview/handler";

const inputs = {
  CLOUDFLARE_ACCOUNT_ID: "a".repeat(32), PREVIEW_CONFIG_KV_ID: "b".repeat(32),
  PREVIEW_LEDGER_D1_ID: "11111111-1111-1111-1111-111111111111",
  PREVIEW_ACCESS_TEAM_DOMAIN: "preview-test.cloudflareaccess.com", PREVIEW_ACCESS_AUD: "test-preview-audience",
  PREVIEW_ADMIN_EMAIL: "Operator@example.test",
};
const env = {
  AI: {}, CONFIG: { list: vi.fn().mockResolvedValue({ keys: [], list_complete: true }) }, LEDGER: {}, RESEARCH_WORKSPACE: {},
  CF_ACCESS_TEAM_DOMAIN: "preview-test", CF_ACCESS_AUD: inputs.PREVIEW_ACCESS_AUD, ADMIN_EMAIL: "operator@example.test",
} as unknown as Env;

let token: string;
let jwk: JsonWebKey;
beforeAll(async () => {
  const pair = await crypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]) as CryptoKeyPair;
  jwk = await crypto.subtle.exportKey("jwk", pair.publicKey) as JsonWebKey;
  const encode = (value: unknown) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const data = `${encode({ alg: "RS256", kid: "preview-key" })}.${encode({ email: env.ADMIN_EMAIL, aud: env.CF_ACCESS_AUD,
    iss: "https://preview-test.cloudflareaccess.com", exp: Math.floor(Date.now() / 1000) + 300 })}`;
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(data));
  token = `${data}.${btoa(String.fromCharCode(...new Uint8Array(signature))).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_")}`;
});
beforeEach(() => {
  doubles.route.mockReset().mockResolvedValue(new Response("private history"));
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    expect(input).toBe("https://preview-test.cloudflareaccess.com/cdn-cgi/access/certs");
    return Response.json({ keys: [{ ...jwk, kid: "preview-key" }] });
  }));
});
afterEach(() => vi.unstubAllGlobals());
const request = (path: string, headers: Record<string, string> = {}) => new Request(`https://preview.example.test${path}`, {
  headers: { "Cf-Access-Jwt-Assertion": token, ...headers },
});

describe("hosted preview isolation", () => {
  it("requires explicit resource and Access inputs without baking identities into source", () => {
    expect(readPreviewSettings(inputs)).toMatchObject({ team: "preview-test", adminEmail: "operator@example.test" });
    for (const key of Object.keys(inputs)) expect(() => readPreviewSettings({ ...inputs, [key]: undefined })).toThrow(key);
    expect(() => readPreviewSettings({ ...inputs, PREVIEW_ACCESS_TEAM_DOMAIN: "https://other.test" })).toThrow("PREVIEW_ACCESS_TEAM_DOMAIN");
  });
  it("discards accidentally supplied bypass flags, production providers and telemetry", () => {
    const isolated = workspacePreviewEnv({ ...env, DEV_MODE: "true", INTERNAL_TASK_TOKEN: "private", OPENAI_API_KEY: "private", PHOENIX_API_KEY: "private", CLEF_ROUTER_MODE: "disabled", CLEF_ROUTER_TASK_PROFILES: '{"research":"openai-deep"}', CLEF_ROUTER_MIN_CONFIDENCE: "0" } as Env);
    expect(Object.keys(isolated).sort()).toEqual(["AI", "CONFIG", "LEDGER", "RESEARCH_WORKSPACE", "CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD", "ADMIN_EMAIL", "CLEF_ROUTER_MODE", "CLEF_ROUTER_TASK_PROFILES", "CLEF_ROUTER_MIN_CONFIDENCE", "CLEF_ROUTER_MIN_MARGIN", "CLEF_ROUTER_TIMEOUT_MS"].sort());
    expect(isolated).toMatchObject({ CLEF_ROUTER_MODE: "auto", CLEF_ROUTER_MIN_CONFIDENCE: "0.7", CLEF_ROUTER_MIN_MARGIN: "0.15", CLEF_ROUTER_TIMEOUT_MS: "1500" });
    expect(JSON.parse(isolated.CLEF_ROUTER_TASK_PROFILES!)).toEqual({ fast: "workers-flash", deep: "workers-deep", code: "workers-deep", research: "workers-deep" });
    expect(getModelCatalog(isolated).profiles.filter(profile => profile.configured).every(profile => profile.provider === "workers-ai")).toBe(true);
  });
  it.each(["/workspace", "/workspace/app.js", "/workspace/models", "/workspace/progress", "/workspace/research-runs", "/workspace/research-runs/example", "/workspace/research-runs/import", "/agents/research-workspace/test/get-messages", "/agents//research-workspace//test", "/live"])(
    "rejects unauthenticated %s before touching agent storage", async path => {
      const response = await previewFetch(new Request(`https://preview.example.test${path}`, { headers: { "X-Internal-Token": "private" } }), { ...env, DEV_MODE: "true", INTERNAL_TASK_TOKEN: "private" } as Env);
      expect(response.status).toBe(403);
      expect(response.headers.get("Cache-Control")).toBe("private, no-store");
      expect(doubles.route).not.toHaveBeenCalled();
    },
  );
  it("serves the real catalog only after verified Access and identifies the preview", async () => {
    const page = await previewFetch(request("/workspace"), env);
    expect(page.status).toBe(200);
    expect(await page.text()).toContain("PRIVATE PREVIEW");
    expect(page.headers.get("Content-Security-Policy")).toContain("connect-src 'self'");
    const catalog = await previewFetch(request("/workspace/models"), env);
    expect((await catalog.json() as { accountAvailability: string }).accountAvailability).toBe("unverified");
  });
  it("fails closed when the operator setting is removed", async () => {
    expect((await previewFetch(request("/workspace"), { ...env, ADMIN_EMAIL: undefined })).status).toBe(403);
  });
  it("reads progress only after Access, preserves private headers, and has no generation endpoint", async () => {
    const all = vi.fn().mockResolvedValue({ success: true, results: [] });
    const prepare = vi.fn(() => ({ all }));
    const progressEnv = { ...env, LEDGER: { prepare } } as unknown as Env;
    const denied = await previewFetch(new Request("https://preview.example.test/workspace/progress"), progressEnv);
    expect(denied.status).toBe(403);
    expect(prepare).not.toHaveBeenCalled();
    const response = await previewFetch(request("/workspace/progress"), progressEnv);
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
    expect(await response.json()).toEqual({ clips: [], truncated: false });
    expect(prepare).toHaveBeenCalledOnce();
    const post = new Request(request("/workspace/progress"), { method: "POST" });
    expect((await previewFetch(post, progressEnv)).status).toBe(404);
    expect(prepare).toHaveBeenCalledOnce();
  });
  it("authenticates imports before body parsing and requires same-origin JSON", async () => {
    const unauthenticated = new Request("https://preview.example.test/workspace/research-runs/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    expect((await previewFetch(unauthenticated, env)).status).toBe(403);
    const authenticated = new Request(request("/workspace/research-runs/import"), { method: "POST", headers: { "Cf-Access-Jwt-Assertion": token, "Content-Type": "application/json" }, body: "{}" });
    expect((await previewFetch(authenticated, env)).status).toBe(400);
    const crossOrigin = new Request(request("/workspace/research-runs/import"), { method: "POST", headers: { "Cf-Access-Jwt-Assertion": token, "Content-Type": "application/json", Origin: "https://other.test" }, body: "{}" });
    expect((await previewFetch(crossOrigin, env)).status).toBe(403);
  });
  it("authenticates history and rejects cross-origin WebSockets", async () => {
    const history = await previewFetch(request("/agents/research-workspace/test/get-messages"), env);
    expect(history.status).toBe(200);
    expect(doubles.route).toHaveBeenCalledOnce();
    doubles.route.mockClear();
    const denied = await previewFetch(request("/agents/research-workspace/test", { Origin: "https://other.test", Upgrade: "websocket" }), env);
    expect(denied.status).toBe(403);
    expect(doubles.route).not.toHaveBeenCalled();
  });
  it.each(["/agents/orchestrator/default", "/run", "/fleet/run", "/research/workflows/mlip-5x5x3/campaigns"])(
    "has no research dispatch route at %s", async path => {
      const result = await previewFetch(request(path), env);
      expect(result.status).toBe(404);
      expect(doubles.route).not.toHaveBeenCalled();
    },
  );
});
