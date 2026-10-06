import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error Node 22.18+ supplies SQLite; Worker tsconfig excludes Node types.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Test-only fixture loading; Worker tsconfig excludes Node types.
import { readFileSync } from "node:fs";
import { buildStubEnv } from "../../testing/envStub";
import { claimNextBridgeJob, enqueueBridgeJob, enqueueScientificJob, handleBridgeRoute, readBridgeJob, scientificDispatchEnabled, scientificReceiptSchema, STALE_CLAIM_SECONDS, type ScientificBridgeEnv, type ScientificReceipt } from "../jobs";

const databases: InstanceType<typeof DatabaseSync>[] = [];
afterEach(() => { for (const db of databases.splice(0)) db.close(); });
const fixtureBase = (import.meta as ImportMeta & { url: string }).url;
const migration17 = readFileSync(new URL("../../../migrations/0017_herdr_bridge_jobs.sql", fixtureBase), "utf8");
const migration19 = readFileSync(new URL("../../../migrations/0019_scientific_bridge_claims.sql", fixtureBase), "utf8");
function harness() {
  const db = new DatabaseSync(":memory:"); databases.push(db); db.exec(migration17); db.exec(migration19);
  const hooks: { beforeFirst?: (sql: string) => void } = {};
  function statement(sql: string, values: unknown[] = []): D1PreparedStatement {
    return {
      bind: (...bound: unknown[]) => statement(sql, [...values, ...bound]),
      first: async () => { hooks.beforeFirst?.(sql); return db.prepare(sql).get(...values) ?? null; },
      all: async () => ({ results: db.prepare(sql).all(...values), success: true, meta: {} }),
      run: async () => ({ results: [], success: true, meta: { changes: Number(db.prepare(sql).run(...values).changes) } }),
    } as unknown as D1PreparedStatement;
  }
  const env: ScientificBridgeEnv = buildStubEnv({ LEDGER: { prepare: (sql: string) => statement(sql) } as D1Database });
  const enqueue = () => enqueueBridgeJob(env, { machine_id: "aledev", agent_kind: "claude", prompt: "Inspect evidence", campaign_id: null });
  const claim = (machine = "aledev") => claimNextBridgeJob(env, machine);
  const call = (method: string, path: string, body?: unknown) => {
    const url = new URL(path, "https://worker.test");
    return handleBridgeRoute(new Request(url, { method }), env, url, body === undefined ? "" : JSON.stringify(body));
  };
  return { db, env, enqueue, claim, call, hooks };
}
const receipt: ScientificReceipt = {
  sources: [{ id: "paper-1", title: "Primary report", url: "https://example.org/paper", excerpt: "The reported measurement changed with size." }],
  question: "What explains the discrepancy?", hypothesis: "A finite-size effect may explain it.",
  competingExplanation: "Selection bias could also explain it.", falsifier: "Persistence at larger sizes would refute the size effect.",
  cheapestExperiment: { proposal: "Compare existing matched sizes.", successCriterion: "The effect decreases with size.", execution: "not_started" },
  critique: "The source does not establish causality.", decision: { recommendation: "investigate", reason: "A matched comparison can distinguish the explanations." },
};
const enable = (env: ScientificBridgeEnv) => { env.SCIENTIFIC_BRIDGE_ENABLED = "true"; env.SCIENTIFIC_BRIDGE_MAC_MACHINE_ID = "mac-controller"; };
async function scientific(h: ReturnType<typeof harness>) {
  enable(h.env); return enqueueScientificJob(h.env, { role: "codex_mac_discovery", question: receipt.question, agendaTaskId: "agenda-1", campaignId: "campaign-1" });
}
function result(job: NonNullable<Awaited<ReturnType<typeof claimNextBridgeJob>>>, extra: Record<string, unknown> = {}) {
  return { machine_id: job.machine_id, claim_token: job.claim_token, status: "done", output_excerpt: "Answer", ...extra };
}

describe("scientific bridge on real SQLite", () => {
  it.each(["scientific_role", "role", "scientific_request_json", "parent_job_id", "parentJobId", "unknown"])("rejects %s on generic enqueue without inserting a legacy job", async key => {
    const h = harness();
    const response = await h.call("POST", "/bridge/jobs", {
      machine_id: "aledev", agent_kind: "claude", prompt: "Critique this discovery.", campaign_id: "campaign-1",
      [key]: "claude_aledev_critique",
    });
    expect(response?.status).toBe(400);
    expect(h.db.prepare("SELECT COUNT(*) AS n FROM herdr_bridge_jobs").get()).toMatchObject({ n: 0 });
  });
  it("preserves all four valid generic enqueue fields", async () => {
    const h = harness();
    const response = await h.call("POST", "/bridge/jobs", {
      machine_id: "aledev", agent_kind: "claude", prompt: "A general task.", campaign_id: "campaign/with legacy spaces",
    });
    expect(response?.status).toBe(201);
    expect(h.db.prepare("SELECT machine_id,agent_kind,prompt,campaign_id,scientific_role FROM herdr_bridge_jobs").get()).toMatchObject({
      machine_id: "aledev", agent_kind: "claude", prompt: "A general task.", campaign_id: "campaign/with legacy spaces", scientific_role: null,
    });
  });
  it("migrates legacy active claims to uncertain without replay", () => {
    const db = new DatabaseSync(":memory:"); databases.push(db); db.exec(migration17);
    db.exec("INSERT INTO herdr_bridge_jobs(job_id,machine_id,prompt,status,attempts) VALUES ('legacy','aledev','x','claimed',1)"); db.exec(migration19);
    expect(db.prepare("SELECT status,result_uncertain,attempts FROM herdr_bridge_jobs").get()).toMatchObject({ status: "timeout", result_uncertain: 1, attempts: 1 });
  });
  it("atomically permits one claim per machine with a fresh bounded token", async () => {
    const h = harness(); await h.enqueue(); await h.enqueue();
    const claims = await Promise.all([h.claim(), h.claim()]); expect(claims.filter(Boolean)).toHaveLength(1);
    const job = claims.find(Boolean)!; expect(job.claim_token).toMatch(/^[a-f0-9-]{36}$/);
    expect(job.claim_expires_at! - job.claimed_at!).toBe(STALE_CLAIM_SECONDS); expect(await h.claim()).toBeNull();
  });
  it("never reruns expired work and rejects its late result", async () => {
    const h = harness(); await h.enqueue(); const job = (await h.claim())!;
    h.db.prepare("UPDATE herdr_bridge_jobs SET claim_expires_at = 1 WHERE job_id = ?").run(job.job_id);
    expect(await h.claim()).toBeNull(); expect(await h.claim()).toBeNull();
    expect(await readBridgeJob(h.env, job.job_id)).toMatchObject({ status: "timeout", result_uncertain: true, attempts: 1 });
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job)))?.status).toBe(409);
  });
  it("requires the matching machine and claim; unclaimed work cannot complete", async () => {
    const h = harness(); const pending = await h.enqueue();
    expect((await h.call("POST", `/bridge/jobs/${pending.job_id}/result`, { machine_id: "aledev", claim_token: crypto.randomUUID(), status: "done" }))?.status).toBe(409);
    const job = (await h.claim())!;
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, { status: "done" }))?.status).toBe(400);
    for (const fields of [{ machine_id: "mac-controller" }, { claim_token: crypto.randomUUID() }]) {
      expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job, fields)))?.status).toBe(409);
    }
    expect(await readBridgeJob(h.env, job.job_id)).toMatchObject({ status: "claimed" });
  });
  it("fences a changed claim between validation and commit", async () => {
    const h = harness(); await h.enqueue(); const job = (await h.claim())!;
    h.hooks.beforeFirst = sql => { if (sql.includes("SET status = ?2")) h.db.prepare("UPDATE herdr_bridge_jobs SET claim_token = ? WHERE job_id = ?").run(crypto.randomUUID(), job.job_id); };
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job)))?.status).toBe(409);
    expect(h.db.prepare("SELECT status FROM herdr_bridge_jobs").get()).toMatchObject({ status: "claimed" });
  });
  it("saves once, acknowledges identical retry and exposes a private read without claim token or prompt", async () => {
    const h = harness(); await h.enqueue(); const job = (await h.claim())!;
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job)))?.status).toBe(200);
    const duplicate = await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job)); expect(await duplicate!.json()).toMatchObject({ duplicate: true });
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job, { status: "failed" })))?.status).toBe(409);
    const read = await h.call("GET", `/bridge/jobs/${job.job_id}`); expect(read?.headers.get("Cache-Control")).toBe("private, no-store");
    const body = await read!.json() as { job: Record<string, unknown> }; expect(body.job).toMatchObject({ status: "done", output_excerpt: "Answer" });
    for (const field of ["claim_token", "prompt", "result_fingerprint"]) expect(body.job).not.toHaveProperty(field);
    expect((await h.call("GET", "/bridge/jobs/absent"))?.status).toBe(404);
  });
  it("stays disabled unless configured with a distinct Mac", async () => {
    const h = harness(); expect(scientificDispatchEnabled(h.env)).toBe(false);
    await expect(enqueueScientificJob(h.env, { role: "codex_mac_discovery", question: receipt.question })).rejects.toThrow("disabled");
    enable(h.env); h.env.SCIENTIFIC_BRIDGE_MAC_MACHINE_ID = "aledev"; expect(scientificDispatchEnabled(h.env)).toBe(false);
    expect(h.db.prepare("SELECT COUNT(*) AS n FROM herdr_bridge_jobs").get()).toMatchObject({ n: 0 });
  });
  it("fixes discovery's target and persists agenda/campaign; rejects extra execution options", async () => {
    const h = harness(); const job = await scientific(h);
    expect(job).toMatchObject({ machine_id: "mac-controller", agent_kind: "codex", agenda_task_id: "agenda-1", campaign_id: "campaign-1" });
    const claim = (await h.claim("mac-controller"))!; expect(claim.prompt).toContain("Do not run experiments, shell commands"); expect(claim.prompt).toContain("not_started");
    await expect(enqueueScientificJob(h.env, { role: "codex_mac_discovery", question: receipt.question, command: "run" } as never)).rejects.toThrow();
  });
  it("requires a receipt for scientific completion, matches its question, and disallows public beats", async () => {
    const h = harness(); await scientific(h); const job = (await h.claim("mac-controller"))!;
    for (const fields of [{}, { scientific_receipt: { ...receipt, question: "Unrelated" } }, { scientific_receipt: receipt, beat: { summary: "leak" } }]) {
      expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job, fields)))?.status).toBe(400);
    }
    expect((await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job, { scientific_receipt: receipt })))?.status).toBe(200);
    expect((await readBridgeJob(h.env, job.job_id))?.scientific_receipt).toEqual(receipt);
  });
  it("links Claude critique to a completed discovery, matching question and agenda", async () => {
    const h = harness(); const parent = await scientific(h); const input = { role: "claude_aledev_critique" as const, question: receipt.question, parentJobId: parent.job_id };
    await expect(enqueueScientificJob(h.env, input)).rejects.toThrow("completed discovery");
    const job = (await h.claim("mac-controller"))!; await h.call("POST", `/bridge/jobs/${job.job_id}/result`, result(job, { scientific_receipt: receipt }));
    const critique = await enqueueScientificJob(h.env, input);
    expect(critique).toMatchObject({ machine_id: "aledev", agent_kind: "claude", parent_job_id: parent.job_id, agenda_task_id: "agenda-1", campaign_id: "campaign-1" });
    const criticClaim = (await h.claim())!;
    expect(criticClaim.prompt).toContain("independently critique");
    expect(critique.parent_receipt_sha256).toMatch(/^[a-f0-9]{64}$/);
    for (const reviewedDiscovery of [undefined, { jobId: parent.job_id, receiptSha256: "0".repeat(64) },
      { jobId: "other-job", receiptSha256: critique.parent_receipt_sha256 }]) {
      expect((await h.call("POST", `/bridge/jobs/${criticClaim.job_id}/result`, result(criticClaim, {
        scientific_receipt: { ...receipt, reviewedDiscovery },
      })))?.status).toBe(400);
    }
    expect((await h.call("POST", `/bridge/jobs/${criticClaim.job_id}/result`, result(criticClaim, {
      scientific_receipt: { ...receipt, reviewedDiscovery: { jobId: parent.job_id, receiptSha256: critique.parent_receipt_sha256 } },
    })))?.status).toBe(200);
    await expect(enqueueScientificJob(h.env, { ...input, question: "Unrelated" })).rejects.toThrow("question must match");
    await expect(enqueueScientificJob(h.env, { ...input, agendaTaskId: "other" })).rejects.toThrow("agenda must match");
  });
  it.each([
    { ...receipt, sources: [{ ...receipt.sources[0], url: "http://example.org" }] },
    { ...receipt, sources: [{ ...receipt.sources[0], url: "https://user:secret@example.org" }] },
    { ...receipt, sources: [{ ...receipt.sources[0], url: "not a url" }] },
    { ...receipt, sources: [receipt.sources[0], receipt.sources[0]] },
    { ...receipt, hypothesis: "x".repeat(4001) },
    { ...receipt, cheapestExperiment: { ...receipt.cheapestExperiment, execution: "completed" } },
    { ...receipt, command: "execute" },
  ])("rejects invalid and execution-shaped receipts", value => { expect(scientificReceiptSchema.safeParse(value).success).toBe(false); });
  it("fails visibly on malformed stored data and caps incoming bodies", async () => {
    const h = harness(); const job = await scientific(h);
    h.db.prepare("UPDATE herdr_bridge_jobs SET scientific_receipt_json = ? WHERE job_id = ?").run('{"bad":true}', job.job_id);
    expect((await h.call("GET", `/bridge/jobs/${job.job_id}`))?.status).toBe(500);
    expect((await h.call("POST", "/bridge/jobs", { prompt: "x".repeat(100_000) }))?.status).toBe(413);
  });
});
