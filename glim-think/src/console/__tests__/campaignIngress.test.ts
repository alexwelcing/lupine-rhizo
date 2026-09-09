import { afterEach, describe, expect, it, vi } from "vitest";
import { handleBeatsPost } from "../../feed/beats";
import { checkAccess, isGatedRoute } from "../../middleware/access";
import { buildStubEnv } from "../../testing/envStub";

vi.mock("../../research/mlipCampaign", () => ({ recordMlipCampaignBeat: vi.fn() }));
vi.mock("../../research/mlipBaselineGrid", () => ({ recordMlipBaselineBeat: vi.fn() }));

afterEach(() => vi.restoreAllMocks());

function ingress(fetcher: (request: Request) => Promise<Response>) {
  const idFromName = vi.fn((name: string) => name);
  const env = buildStubEnv({
    DEV_MODE: "true",
    CAMPAIGN_CONSOLE: { idFromName, get: () => ({ fetch: fetcher }) } as unknown as DurableObjectNamespace,
  });
  const body = { beat_id: "beat-1", agent: "runner", summary: "finished", ts: 1788000000,
    metrics: { campaign_id: "github:27206839783", cell_id: "cell-1", accuracy_score: 0.9 } };
  return { env, body, idFromName, post: () => handleBeatsPost(
    new Request("https://worker.test/feed/beats", { method: "POST" }), env, JSON.stringify(body),
  ) };
}

describe("campaign console ingress and access", () => {
  it("fans in the original campaign identity and source observation time", async () => {
    const fetcher = vi.fn(async (_request: Request) => Response.json({ ok: true }));
    const run = ingress(fetcher);
    expect((await run.post()).status).toBe(200);
    expect(run.idFromName).toHaveBeenCalledWith(run.body.metrics.campaign_id);
    const request = fetcher.mock.calls[0][0];
    expect(new URL(request.url).pathname).toBe("/beat");
    expect(await request.json()).toEqual({ beat_id: run.body.beat_id, metrics: run.body.metrics,
      summary: run.body.summary, observedAt: new Date(run.body.ts * 1000).toISOString() });
  });

  it.each(["http", "throw"])("keeps %s console failures best-effort and observable", async (mode) => {
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});
    const run = ingress(async () => {
      if (mode === "throw") throw new Error("unavailable");
      return new Response("unavailable", { status: 503 });
    });
    expect((await run.post()).status).toBe(200);
    expect(logged).toHaveBeenCalledWith("campaign-console fan-in failed:", expect.any(Error));
  });

  it("does not fan in beats lacking a campaign", async () => {
    const fetcher = vi.fn(async () => Response.json({ ok: true }));
    const run = ingress(fetcher);
    run.body.metrics.campaign_id = "";
    expect((await run.post()).status).toBe(200);
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("gates writes while keeping state, live and preflight public", async () => {
    expect(isGatedRoute("/console/campaigns/c/lock", "POST")).toBe(true);
    expect(isGatedRoute("/console/campaigns/c/state", "GET")).toBe(false);
    expect(isGatedRoute("/console/campaigns/c/live", "GET")).toBe(false);
    expect(isGatedRoute("/console/campaigns/c/lock", "OPTIONS")).toBe(false);
    const denial = await checkAccess(new Request("https://worker.test/console/campaigns/c/lock", {
      method: "POST",
    }), buildStubEnv({ DEV_MODE: "false" }), []);
    expect(denial?.status).toBe(403);
  });
});
