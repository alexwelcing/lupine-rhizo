import { describe, expect, it } from "vitest";
import { checkAccess, isGatedRoute } from "../access";
import { checkWorkspaceRequest, isWorkspaceRoute } from "../workspaceAccess";
import { buildStubEnv } from "../../testing/envStub";

describe("private research workspace access", () => {
  it.each([
    "/workspace", "/workspace/app.js", "/workspace/models", "/workspace/conversations", "/workspace/progress",
    "/agents/research-workspace/research-one",
    "/agents/research-workspace/research-one/get-messages",
    "/agents//research-workspace//research-one/get-messages",
  ])("gates all methods and history for %s", async path => {
    for (const method of ["GET", "POST", "OPTIONS"]) {
      expect(isGatedRoute(path, method)).toBe(true);
    }
    const denial = await checkAccess(new Request(`https://worker.test${path}`), buildStubEnv(), []);
    expect(denial?.status).toBe(403);
  });

  it("preserves public research reading routes", () => {
    expect(isWorkspaceRoute("/workspace-other")).toBe(false);
    expect(isGatedRoute("/research/hits", "GET")).toBe(false);
    expect(isGatedRoute("/live", "GET")).toBe(false);
  });

  it.each(["", "Bad-ID", "bad%2Fid", "bad%20id", "-leading", "x".repeat(65)])(
    "rejects invalid conversation IDs before DO allocation: %s", id => {
      const denial = checkWorkspaceRequest(new Request(`https://worker.test/agents/research-workspace/${id}`));
      expect(denial?.status).toBe(400);
    },
  );

  it("accepts a stable conversation and history path", () => {
    expect(checkWorkspaceRequest(new Request("https://worker.test/agents/research-workspace/1234-abcd/get-messages"))).toBeNull();
  });

  it("rejects cross-origin websocket handshakes even with browser credentials", () => {
    const request = new Request("https://worker.test/agents/research-workspace/research-one", {
      headers: { Origin: "https://other.test", Upgrade: "websocket", Cookie: "CF_Authorization=example" },
    });
    expect(checkWorkspaceRequest(request)?.status).toBe(403);
  });

  it("accepts same-origin browser requests and token-authenticated machine requests", async () => {
    const request = new Request("https://worker.test/workspace/conversations", {
      headers: { Origin: "https://worker.test", "X-Internal-Token": "test-token" },
    });
    expect(checkWorkspaceRequest(request)).toBeNull();
    await expect(checkAccess(request, buildStubEnv({ INTERNAL_TASK_TOKEN: "test-token" }), [])).resolves.toBeNull();
  });
});
