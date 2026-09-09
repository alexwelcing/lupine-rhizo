import { afterEach, describe, expect, it, vi } from "vitest";
import { handleBridgeRoute, claimNextBridgeJob, MAX_ATTEMPTS, STALE_CLAIM_SECONDS } from "../jobs";
import { handleBeatsPost } from "../../feed/beats";
import { checkAccess, isGatedRoute } from "../../middleware/access";
import { buildStubEnv, stubLedger, type D1Row } from "../../testing/envStub";

vi.mock("../../research/mlipCampaign", () => ({ recordMlipCampaignBeat: vi.fn() }));
vi.mock("../../research/mlipBaselineGrid", () => ({ recordMlipBaselineBeat: vi.fn() }));

afterEach(() => vi.restoreAllMocks());

const WORKER = "https://worker.test";

interface Prepared {
  sql: string;
  bindings: readonly unknown[];
}

function bridgeEnv(rows: { claim?: D1Row | null; existing?: D1Row | null } = {}, prepared: Prepared[] = []) {
  const consoleFetch = vi.fn(async () => Response.json({ ok: true }));
  const env = buildStubEnv({
    DEV_MODE: "true",
    LEDGER: stubLedger({
      queries: [
        { match: "SET status = 'claimed'", first: rows.claim ?? null },
        { match: "FROM herdr_bridge_jobs WHERE job_id", first: rows.existing ?? null },
      ],
      onPrepare: (sql, bindings) => prepared.push({ sql, bindings }),
    }),
    CAMPAIGN_CONSOLE: {
      idFromName: (name: string) => name,
      get: () => ({ fetch: consoleFetch }),
    } as unknown as DurableObjectNamespace,
  });
  return { env, prepared, consoleFetch };
}

function call(env: ReturnType<typeof bridgeEnv>["env"], method: string, path: string, body?: unknown) {
  const url = new URL(path, WORKER);
  const request = new Request(url, { method });
  return handleBridgeRoute(request, env, url, body === undefined ? "" : JSON.stringify(body));
}

const claimedRow: D1Row = {
  job_id: "job-1",
  machine_id: "aledev",
  agent_kind: "hermes",
  prompt: "Summarise the Z2 abstention panel.",
  campaign_id: "github:1",
  status: "claimed",
  attempts: 1,
  created_at: 1_788_000_000,
  claimed_at: 1_788_000_100,
};

describe("bridge job routes", () => {
  it("ignores non-bridge paths", async () => {
    const { env } = bridgeEnv();
    expect(await call(env, "GET", "/feed/beats")).toBeNull();
  });

  it("enqueues a job with defaults and returns the pending row", async () => {
    const { env, prepared } = bridgeEnv();
    const response = await call(env, "POST", "/bridge/jobs", {
      machine_id: "aledev",
      prompt: "  Run the lit cycle.  ",
    });
    expect(response?.status).toBe(201);
    const body = (await response!.json()) as { job: Record<string, unknown> };
    expect(body.job).toMatchObject({
      machine_id: "aledev",
      agent_kind: "hermes",
      prompt: "Run the lit cycle.",
      campaign_id: null,
      status: "pending",
      attempts: 0,
    });
    expect(typeof body.job.job_id).toBe("string");
    const insert = prepared.find((p) => p.sql.includes("INSERT INTO herdr_bridge_jobs"));
    expect(insert?.bindings.slice(1, 5)).toEqual(["aledev", "hermes", "Run the lit cycle.", null]);
  });

  it.each([
    [{ prompt: "x" }, "machine_id"],
    [{ machine_id: "bad id", prompt: "x" }, "machine_id"],
    [{ machine_id: "aledev" }, "prompt"],
    [{ machine_id: "aledev", prompt: "x", agent_kind: "Not Valid" }, "agent_kind"],
    [{ machine_id: "aledev", prompt: "x", campaign_id: "" }, "campaign_id"],
  ])("rejects invalid enqueue body %j", async (body, field) => {
    const { env, prepared } = bridgeEnv();
    const response = await call(env, "POST", "/bridge/jobs", body);
    expect(response?.status).toBe(400);
    expect(((await response!.json()) as { error: string }).error).toContain(field);
    expect(prepared).toHaveLength(0);
  });

  it("claims the oldest dispatchable job atomically with stale-claim recovery bounds", async () => {
    const { env, prepared } = bridgeEnv({ claim: claimedRow });
    const now = Math.floor(Date.now() / 1000);
    const response = await call(env, "GET", "/bridge/jobs/next?machine_id=aledev");
    expect(response?.status).toBe(200);
    expect(((await response!.json()) as { job: D1Row }).job.job_id).toBe("job-1");
    const claim = prepared.find((p) => p.sql.includes("SET status = 'claimed'"));
    expect(claim?.sql).toContain("ORDER BY created_at ASC");
    expect(claim?.sql).toContain("RETURNING");
    expect(claim?.bindings[0]).toBe("aledev");
    expect(Math.abs((claim?.bindings[1] as number) - now)).toBeLessThan(5);
    expect((claim?.bindings[2] as number)).toBe((claim?.bindings[1] as number) - STALE_CLAIM_SECONDS);
    expect(claim?.bindings[3]).toBe(MAX_ATTEMPTS);
  });

  it("returns 204 when nothing is pending and 400 without a machine id", async () => {
    const { env } = bridgeEnv();
    expect((await call(env, "GET", "/bridge/jobs/next?machine_id=aledev"))?.status).toBe(204);
    expect((await call(env, "GET", "/bridge/jobs/next"))?.status).toBe(400);
    expect(await claimNextBridgeJob(env, "aledev")).toBeNull();
  });

  it("closes a job, stamps the result beat with bridge provenance, and fans it in to the console", async () => {
    const { env, prepared, consoleFetch } = bridgeEnv({ existing: claimedRow });
    const response = await call(env, "POST", "/bridge/jobs/job-1/result", {
      status: "done",
      output_excerpt: "PONG",
      beat: { beat_id: "beat-job-1", agent: "herdr-bridge", summary: "job done", metrics: { transition: "done" } },
    });
    expect(response?.status).toBe(200);
    expect(await response!.json()).toEqual({ ok: true, job_id: "job-1", status: "done", beat_id: "beat-job-1" });

    const beatInsert = prepared.find((p) => p.sql.includes("INSERT INTO lab_beats"));
    expect(beatInsert?.bindings[0]).toBe("beat-job-1");
    expect(JSON.parse(beatInsert?.bindings[3] as string)).toEqual({
      transition: "done",
      job_id: "job-1",
      machine_id: "aledev",
      campaign_id: "github:1",
      source: "herdr-bridge",
    });
    expect(consoleFetch).toHaveBeenCalledTimes(1);

    const update = prepared.find((p) => p.sql.includes("SET status = ?2"));
    expect(update?.bindings.slice(0, 4)).toEqual(["job-1", "done", "PONG", "beat-job-1"]);
  });

  it("closes a job without a beat", async () => {
    const { env, prepared } = bridgeEnv({ existing: claimedRow });
    const response = await call(env, "POST", "/bridge/jobs/job-1/result", { status: "timeout" });
    expect(response?.status).toBe(200);
    expect(prepared.some((p) => p.sql.includes("INSERT INTO lab_beats"))).toBe(false);
    const update = prepared.find((p) => p.sql.includes("SET status = ?2"));
    expect(update?.bindings.slice(0, 4)).toEqual(["job-1", "timeout", null, null]);
  });

  it("leaves the job claimed when the result beat is rejected", async () => {
    const { env, prepared } = bridgeEnv({ existing: claimedRow });
    const response = await call(env, "POST", "/bridge/jobs/job-1/result", {
      status: "done",
      beat: { beat_id: "", agent: "herdr-bridge", summary: "x" },
    });
    expect(response?.status).toBe(400);
    expect(prepared.some((p) => p.sql.includes("SET status = ?2"))).toBe(false);
  });

  it("rejects unknown, terminal, and malformed results", async () => {
    const missing = bridgeEnv();
    expect((await call(missing.env, "POST", "/bridge/jobs/nope/result", { status: "done" }))?.status).toBe(404);

    const terminal = bridgeEnv({ existing: { ...claimedRow, status: "done" } });
    expect((await call(terminal.env, "POST", "/bridge/jobs/job-1/result", { status: "failed" }))?.status).toBe(409);

    const bad = bridgeEnv({ existing: claimedRow });
    expect((await call(bad.env, "POST", "/bridge/jobs/job-1/result", { status: "pending" }))?.status).toBe(400);
    expect((await call(bad.env, "POST", "/bridge/jobs/job-1/result", "not-json"))?.status).toBe(400);
  });

  it("404s unknown bridge routes", async () => {
    const { env } = bridgeEnv();
    expect((await call(env, "DELETE", "/bridge/jobs"))?.status).toBe(404);
  });
});

describe("bridge access policy", () => {
  it("gates every bridge method except preflight", () => {
    expect(isGatedRoute("/bridge/jobs", "POST")).toBe(true);
    expect(isGatedRoute("/bridge/jobs/next", "GET")).toBe(true);
    expect(isGatedRoute("/bridge/jobs/j/result", "POST")).toBe(true);
    expect(isGatedRoute("/bridge/jobs", "OPTIONS")).toBe(false);
  });

  it("accepts the HERDR_BRIDGE_TOKEN bearer on bridge routes only", async () => {
    const env = buildStubEnv({ HERDR_BRIDGE_TOKEN: "bridge-secret" });
    const headers = { Authorization: "Bearer bridge-secret" };
    await expect(checkAccess(new Request(`${WORKER}/bridge/jobs/next?machine_id=a`, { headers }), env, [])).resolves.toBeNull();
    await expect(checkAccess(new Request(`${WORKER}/bridge/jobs`, { method: "POST", headers }), env, [])).resolves.toBeNull();
    const elsewhere = await checkAccess(new Request(`${WORKER}/admin/run`, { method: "POST", headers }), env, []);
    expect(elsewhere?.status).toBe(403);
    const wrong = await checkAccess(
      new Request(`${WORKER}/bridge/jobs`, { method: "POST", headers: { Authorization: "Bearer nope" } }),
      env,
      [],
    );
    expect(wrong?.status).toBe(403);
  });

  it("still honours the global X-Internal-Token on bridge routes", async () => {
    const env = buildStubEnv({ INTERNAL_TASK_TOKEN: "internal-secret" });
    await expect(checkAccess(
      new Request(`${WORKER}/bridge/jobs`, { method: "POST", headers: { "X-Internal-Token": "internal-secret" } }),
      env,
      [],
    )).resolves.toBeNull();
  });

  it("denies unauthenticated bridge requests outside dev mode", async () => {
    const denial = await checkAccess(new Request(`${WORKER}/bridge/jobs/next?machine_id=a`), buildStubEnv({ DEV_MODE: "false" }), []);
    expect(denial?.status).toBe(403);
  });
});

describe("beats producer auth for the bridge", () => {
  const beat = JSON.stringify({ beat_id: "b-1", agent: "herdr-bridge", summary: "idle -> working" });

  function beatsEnv(overrides: Record<string, unknown>) {
    return buildStubEnv({
      DEV_MODE: "false",
      TASKS_CONSUMER_INVOKER_SA: "runner@example.iam.gserviceaccount.com",
      LEDGER: stubLedger(),
      CAMPAIGN_CONSOLE: { idFromName: (n: string) => n, get: () => ({ fetch: async () => Response.json({}) }) } as unknown as DurableObjectNamespace,
      ...overrides,
    });
  }

  it("accepts the HERDR_BRIDGE_TOKEN bearer without an OIDC round-trip", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const response = await handleBeatsPost(
      new Request(`${WORKER}/feed/beats`, { method: "POST", headers: { Authorization: "Bearer bridge-secret" } }),
      beatsEnv({ HERDR_BRIDGE_TOKEN: "bridge-secret" }),
      beat,
    );
    expect(response.status).toBe(200);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("falls through to OIDC verification for any other bearer", async () => {
    const response = await handleBeatsPost(
      new Request(`${WORKER}/feed/beats`, { method: "POST", headers: { Authorization: "Bearer not-a-jwt" } }),
      beatsEnv({ HERDR_BRIDGE_TOKEN: "bridge-secret" }),
      beat,
    );
    expect(response.status).toBe(401);
    expect(((await response.json()) as { error: string }).error).toContain("jwt verify failed");
  });

  it("does not treat the bridge bearer as valid when the secret is unset", async () => {
    const response = await handleBeatsPost(
      new Request(`${WORKER}/feed/beats`, { method: "POST", headers: { Authorization: "Bearer bridge-secret" } }),
      beatsEnv({}),
      beat,
    );
    expect(response.status).toBe(401);
  });
});
