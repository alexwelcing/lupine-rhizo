import { describe, expect, it } from "vitest";
import { checkAccess } from "../access";
import { buildStubEnv } from "../../testing/envStub";

describe("service-token access", () => {
  it("accepts the configured Lupine app token as an Authorization bearer", async () => {
    const request = new Request(
      "https://worker.test/research/workflows/mlip-5x5x3/campaigns",
      { method: "POST", headers: { Authorization: "Bearer dispatch-secret" } },
    );

    await expect(
      checkAccess(request, buildStubEnv({ LUPINE_APP_TOKEN: "dispatch-secret" }), []),
    ).resolves.toBeNull();
  });

  it("rejects an incorrect Authorization bearer", async () => {
    const request = new Request(
      "https://worker.test/research/workflows/mlip-5x5x3/campaigns",
      { method: "POST", headers: { Authorization: "Bearer wrong" } },
    );

    const denial = await checkAccess(
      request,
      buildStubEnv({ LUPINE_APP_TOKEN: "dispatch-secret" }),
      [],
    );

    expect(denial?.status).toBe(403);
  });

  it.each([
    ["POST", "/research/workflows/other/campaigns"],
    ["GET", "/research/workflows/mlip-5x5x3/campaigns"],
    ["POST", "/admin/run"],
  ])("does not accept an Authorization bearer for %s %s", async (method, pathname) => {
    const denial = await checkAccess(
      new Request(`https://worker.test${pathname}`, {
        method,
        headers: { Authorization: "Bearer dispatch-secret" },
      }),
      buildStubEnv({ LUPINE_APP_TOKEN: "dispatch-secret" }),
      [],
    );

    expect(denial?.status).toBe(403);
  });

  it("preserves the global X-Internal-Token bypass", async () => {
    await expect(checkAccess(
      new Request("https://worker.test/admin/run", {
        method: "POST",
        headers: { "X-Internal-Token": "dispatch-secret" },
      }),
      buildStubEnv({ INTERNAL_TASK_TOKEN: "dispatch-secret" }),
      [],
    )).resolves.toBeNull();
  });

  it("never accepts INTERNAL_TASK_TOKEN as the Lupine app bearer", async () => {
    const denial = await checkAccess(
      new Request("https://worker.test/research/workflows/mlip-5x5x3/campaigns", {
        method: "POST",
        headers: { Authorization: "Bearer internal-secret" },
      }),
      buildStubEnv({
        INTERNAL_TASK_TOKEN: "internal-secret",
        LUPINE_APP_TOKEN: "lupine-secret",
      }),
      [],
    );

    expect(denial?.status).toBe(403);
  });
});
