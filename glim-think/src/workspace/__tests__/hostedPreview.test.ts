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
    const isolated = workspacePreviewEnv({ ...env, DEV_MODE: "true", INTERNAL_TASK_TOKEN: "private", OPENAI_API_KEY: "private", PHOENIX_API_KEY: "private", CLEF_ROUTER_MODE: "auto" } as Env);
    expect(Object.keys(isolated).sort()).toEqual(["AI", "CONFIG", "LEDGER", "RESEARCH_WORKSPACE", "CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD", "ADMIN_EMAIL", "CLEF_ROUTER_MODE"].sort());
    expect(isolated.CLEF_ROUTER_MODE).toBe("disabled");
    expect(getModelCatalog(isolated).profiles.filter(profile => profile.configured).every(profile => profile.provider === "workers-ai")).toBe(true);
  });
  it.each(["/workspace", "/workspace/app.js", "/workspace/models", "/agents/research-workspace/test/get-messages", "/agents//research-workspace//test", "/live"])(
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
    expect(await page.text()).toContain("HOSTED PREVIEW");
    expect(page.headers.get("Content-Security-Policy")).toContain("connect-src 'self'");
    const catalog = await previewFetch(request("/workspace/models"), env);
    expect((await catalog.json() as { accountAvailability: string }).accountAvailability).toBe("unverified");
  });
  it("fails closed when the operator setting is removed", async () => {
    expect((await previewFetch(request("/workspace"), { ...env, ADMIN_EMAIL: undefined })).status).toBe(403);
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
