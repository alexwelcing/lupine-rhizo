import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error Test-only SQLite, excluded from Worker types.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Test-only fixtures, excluded from Worker types.
import { readFileSync } from "node:fs";
import type { Env } from "../../types";
import { decodeResearchRun, sha256, type ResearchRunImport } from "../researchRunContracts";
import { importResearchRun, listResearchRuns, readResearchRuns, researchRunsResponse } from "../researchRuns";

const base = (import.meta as ImportMeta & { url: string }).url;
const migration = readFileSync(new URL("../../../migrations/0020_workspace_research_runs.sql", base), "utf8");
const proposal = JSON.parse(readFileSync(new URL("../../../../tools/scientific-pi/tests/fixtures/proposal.json", base), "utf8"));
const databases: InstanceType<typeof DatabaseSync>[] = [];
afterEach(() => { for (const db of databases.splice(0)) db.close(); });
function harness() {
  const db = new DatabaseSync(":memory:"); databases.push(db); db.exec(migration);
  const hooks: { beforeRun?: () => void } = {};
  function statement(sql: string, values: unknown[] = []): D1PreparedStatement {
    return { bind: (...bound: unknown[]) => statement(sql, [...values, ...bound]),
      first: async () => db.prepare(sql).get(...values) ?? null,
      all: async () => ({ results: db.prepare(sql).all(...values), success: true, meta: {} }),
      run: async () => { hooks.beforeRun?.(); return { results: [], success: true, meta: { changes: Number(db.prepare(sql).run(...values).changes) } }; },
    } as unknown as D1PreparedStatement;
  }
  const env = { LEDGER: { prepare: (sql: string) => statement(sql) } } as unknown as Env;
  const call = (value: unknown, headers: Record<string, string> = {}) => researchRunsResponse(new Request("http://localhost/workspace/research-runs/import", {
    method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(value),
  }), env, true);
  return { db, env, hooks, call };
}
async function snapshot(): Promise<ResearchRunImport> {
  const packetJson = JSON.stringify(proposal);
  return { schemaVersion: 1, id: "fixture-cycle", question: proposal.research_question, status: "running",
    startedAt: "2026-10-05T10:00:00.000Z", finishedAt: null, capturedAt: "2026-10-05T10:02:00.000Z", error: null,
    experiment: "not_started", publication: "held", stages: [
      { stage: "discovery", jobId: "fixture-discovery", provider: "codex", role: "proposer", machineId: "mac", status: "completed",
        receipt: { jobId: "fixture-discovery", jobSha256: "a".repeat(64), status: "completed", completionUnknown: false,
          automaticRetry: false, modelExecutionStarted: true, sessionId: "fixture-session", model: "fixture-model",
          startedAt: "2026-10-05T10:00:00.000Z", finishedAt: "2026-10-05T10:01:00.000Z", resultSha256: await sha256(packetJson), receiptOrigin: "local_cli" }, packetJson },
      { stage: "independent_critique", jobId: null, provider: "claude", role: "critic", machineId: null, status: "not_started", receipt: null, packetJson: null },
      { stage: "pi_decision", jobId: null, provider: "codex", role: "adjudicator", machineId: null, status: "not_started", receipt: null, packetJson: null },
    ] };
}
async function fullSnapshot() {
  const run = await snapshot();
  const critique = { role: "critic", reviewed_job_id: run.stages[0].jobId, reviewed_packet_sha256: run.stages[0].receipt!.resultSha256,
    verdict: "revise", source_checks: [{ source_id: "s1", status: "provided_only", reason: "Fixture" }],
    critiques: [{ proposal_id: "p1", prior_art_overlap: "Fixture", confounds: ["Fixture"], discriminating_experiment_assessment: "Fixture", decision: "revise", required_changes: [] }],
    strongest_alternative: "Fixture", next_step: "Fixture", execution: "not_started" };
  const critiqueJson = JSON.stringify(critique);
  run.stages[1] = { ...run.stages[1], jobId: "fixture-critique", machineId: "aledev", status: "completed", packetJson: critiqueJson,
    receipt: { ...run.stages[0].receipt!, jobId: "fixture-critique", jobSha256: "b".repeat(64), resultSha256: await sha256(critiqueJson) } };
  const decision = { role: "adjudicator", reviewed_job_id: run.stages[0].jobId, reviewed_packet_sha256: run.stages[0].receipt!.resultSha256,
    critique_job_id: run.stages[1].jobId, critique_packet_sha256: run.stages[1].receipt!.resultSha256, selected_proposal_id: "p1", recommendation: "revise",
    reason: "Fixture", response_to_critique: [{ critique_point: "Fixture", response: "Fixture", change: "Fixture" }], revised_hypothesis: "Fixture",
    closest_prior_art_boundary: "Fixture", novelty_status: "unverified", competing_explanation: "Fixture", falsifier: "Fixture", source_ids: ["s1"],
    cheap_discriminating_experiment: proposal.proposals[0].cheap_discriminating_experiment, publication: "held" };
  const decisionJson = JSON.stringify(decision);
  run.stages[2] = { ...run.stages[2], jobId: "fixture-decision", machineId: "mac", status: "completed", packetJson: decisionJson,
    receipt: { ...run.stages[0].receipt!, jobId: "fixture-decision", jobSha256: "c".repeat(64), resultSha256: await sha256(decisionJson) } };
  return { ...run, status: "completed" as const, finishedAt: "2026-10-05T10:02:00.000Z" };
}

describe("scientific research snapshot contract", () => {
  it("accepts exact complete packets while retaining unexecuted experiment and unverified novelty", async () => {
    const run = await decodeResearchRun(await fullSnapshot());
    expect(run.status).toBe("completed"); expect(run.stages[2].result).toMatchObject({ role: "adjudicator", publication: "held", novelty_status: "unverified" });
    expect(run.experiment).toBe("not_started");
  });
  it("preserves a refined scientific question separately from the operator's original question", async () => {
    const value = await snapshot(); value.question = "A broader operator research question";
    const run = await decodeResearchRun(value);
    expect(run.question).toBe(value.question);
    expect(run.stages[0].result).toMatchObject({ research_question: "Fixture research question" });
  });
  it("verifies exact Python-style numeric packet bytes before parsing", async () => {
    const value = await snapshot();
    value.stages[0].packetJson = value.stages[0].packetJson!.replace('"estimated_compute_minutes":1,', '"estimated_compute_minutes":1.0,');
    value.stages[0].receipt!.resultSha256 = await sha256(value.stages[0].packetJson);
    const run = await decodeResearchRun(value);
    expect(run.stages[0].result).toMatchObject({ proposals: [{ cheap_discriminating_experiment: { estimated_compute_minutes: 1 } }] });
  });
  it("rejects tampered packet bytes, forged completion and unknown/private metadata", async () => {
    const run = await snapshot(); run.stages[0].packetJson += " ";
    await expect(decodeResearchRun(run)).rejects.toThrow("fingerprint");
    for (const change of [{ completionUnknown: true }, { modelExecutionStarted: false }, { receiptOrigin: "controller_transport" }, { sessionId: null }]) {
      const value = await snapshot(); Object.assign(value.stages[0].receipt!, change);
      await expect(decodeResearchRun(value)).rejects.toThrow();
    }
    await expect(decodeResearchRun({ ...await snapshot(), credentials: "never saved" })).rejects.toThrow();
  });
  it("rejects false complete cycles, future-stage execution and invalid source links", async () => {
    await expect(decodeResearchRun({ ...await snapshot(), status: "completed", finishedAt: "2026-10-05T10:02:00Z" })).rejects.toThrow();
    const value = await snapshot(); value.stages[2] = { ...value.stages[2], jobId: "early", machineId: "mac", status: "pending" };
    await expect(decodeResearchRun(value)).rejects.toThrow("prerequisite");
    for (const url of ["http://example.test", "https://user:pass@example.test", "javascript:alert(1)"]) {
      const bad = await snapshot(); const packet = structuredClone(proposal); packet.sources[0].url = url;
      bad.stages[0].packetJson = JSON.stringify(packet); bad.stages[0].receipt!.resultSha256 = await sha256(bad.stages[0].packetJson);
      await expect(decodeResearchRun(bad)).rejects.toThrow();
    }
  });
  it("binds critique and PI decision to the exact earlier packet and complete proposal set", async () => {
    for (const index of [1, 2]) {
      const run = await fullSnapshot(); const packet = JSON.parse(run.stages[index].packetJson!); packet.reviewed_packet_sha256 = "f".repeat(64);
      run.stages[index].packetJson = JSON.stringify(packet); run.stages[index].receipt!.resultSha256 = await sha256(run.stages[index].packetJson!);
      await expect(decodeResearchRun(run)).rejects.toThrow("different");
    }
  });
});

describe("private D1 research imports and reads", () => {
  it("persists a verified snapshot idempotently, lists and reads it privately", async () => {
    const h = harness(), run = await snapshot();
    expect(await (await h.call(run))!.json()).toMatchObject({ id: run.id, duplicate: false });
    expect(await (await h.call(run))!.json()).toMatchObject({ duplicate: true });
    expect((await listResearchRuns(h.env)).runs[0].stages[0].result).toEqual(proposal);
    const detail = await researchRunsResponse(new Request(`http://localhost/workspace/research-runs/${run.id}`), h.env, true);
    expect(detail!.headers.get("Cache-Control")).toBe("private, no-store");
    expect(await detail!.json()).toMatchObject({ run: { id: run.id } });
  });
  it("imports and reads dotted cycle/job identities supported by the local runner", async () => {
    const h = harness(), run = await fullSnapshot(); run.id = "study.v1";
    for (const stage of run.stages) { stage.jobId = stage.jobId!.replace("fixture-", "fixture."); stage.receipt!.jobId = stage.jobId; }
    const critique = JSON.parse(run.stages[1].packetJson!);
    critique.reviewed_job_id = run.stages[0].jobId;
    run.stages[1].packetJson = JSON.stringify(critique);
    run.stages[1].receipt!.resultSha256 = await sha256(run.stages[1].packetJson);
    const decision = JSON.parse(run.stages[2].packetJson!);
    decision.reviewed_job_id = run.stages[0].jobId; decision.critique_job_id = run.stages[1].jobId;
    decision.critique_packet_sha256 = run.stages[1].receipt!.resultSha256;
    run.stages[2].packetJson = JSON.stringify(decision);
    run.stages[2].receipt!.resultSha256 = await sha256(run.stages[2].packetJson);
    expect((await h.call(run))!.status).toBe(200);
    const response = await researchRunsResponse(new Request("http://localhost/workspace/research-runs/study.v1"), h.env, true);
    expect(response!.status).toBe(200);
    expect(await readResearchRuns(h.env, { runId: "study.v1" })).toMatchObject({ id: "study.v1", status: "completed" });
    for (const invalid of ["../study.v1", "study/v1", "study%2Fv1", ".", ".."])
      await expect(decodeResearchRun({ ...run, id: invalid })).rejects.toThrow();
  });
  it("allows pending→complete and rejects terminal edits, replaced IDs, old snapshots and reopening", async () => {
    const h = harness(), run = await snapshot();
    run.stages[1] = { ...run.stages[1], jobId: "fixture-critique", machineId: "aledev", status: "pending" };
    await h.call(run);
    const wrong = structuredClone(run); wrong.stages[1].jobId = "replacement";
    expect((await h.call(wrong))!.status).toBe(409);
    const old = { ...run, capturedAt: "2026-10-05T10:01:00Z" }; expect((await h.call(old))!.status).toBe(409);
    const completed = await fullSnapshot(); expect((await h.call(completed))!.status).toBe(200);
    const changed = structuredClone(completed); changed.stages[0].receipt!.model = "replacement-model";
    expect((await h.call(changed))!.status).toBe(409);
    expect((await h.call(run))!.status).toBe(409);
  });
  it("fences concurrent edits with an atomic payload fingerprint condition", async () => {
    const h = harness(), run = await snapshot(); await h.call(run);
    h.hooks.beforeRun = () => h.db.prepare("UPDATE workspace_research_runs SET payload_sha256=? WHERE id=?").run("f".repeat(64), run.id);
    expect((await h.call({ ...run, capturedAt: "2026-10-05T10:03:00Z" }))!.status).toBe(409);
  });
  it("freezes pending and unstarted stages once the entire cycle stops", async () => {
    const h = harness(); const stopped = { ...await snapshot(), status: "stopped", finishedAt: "2026-10-05T10:02:00.000Z", error: "Stopped" };
    expect((await h.call(stopped))!.status).toBe(200);
    const resumed = structuredClone(stopped);
    Object.assign(resumed.stages[1], { jobId: "new-critique", machineId: "aledev", status: "pending" });
    expect((await h.call(resumed))!.status).toBe(409);
    expect((await listResearchRuns(h.env)).runs[0].stages[1].status).toBe("not_started");
  });
  it("rejects invalid/oversized imports before storage and never echoes diagnostic content", async () => {
    const h = harness();
    expect((await h.call({ bad: "private details" }))!.status).toBe(400);
    expect((await h.call({ bad: "x".repeat(196609) }))!.status).toBe(413);
    expect(h.db.prepare("SELECT COUNT(*) AS n FROM workspace_research_runs").get()).toMatchObject({ n: 0 });
    await h.call(await snapshot()); h.db.exec("UPDATE workspace_research_runs SET payload='private broken data'");
    const result = await researchRunsResponse(new Request("http://localhost/workspace/research-runs"), h.env, true);
    expect(result!.status).toBe(503); expect(await result!.text()).not.toContain("private broken");
  });
  it("blocks cross-origin, broad tokens and local-fixture use on a public hostname", async () => {
    const h = harness(), run = await snapshot();
    expect((await h.call(run, { Origin: "https://other.test" }))!.status).toBe(403);
    const req = new Request("https://worker.test/workspace/research-runs/import", { method: "POST", headers: { "Content-Type": "application/json", "X-Internal-Token": "secret" }, body: JSON.stringify(run) });
    expect((await researchRunsResponse(req.clone(), { ...h.env, INTERNAL_TASK_TOKEN: "secret", DEV_MODE: "true", ADMIN_EMAIL: "operator@example.test" }))!.status).toBe(403);
    expect((await researchRunsResponse(req.clone(), h.env, true))!.status).toBe(403);
    expect(h.db.prepare("SELECT COUNT(*) AS n FROM workspace_research_runs").get()).toMatchObject({ n: 0 });
  });
  it("bounds recent reads to20 with honest truncation", async () => {
    const h = harness();
    for (let i = 0; i < 21; i++) await importResearchRun(h.env, JSON.stringify({ ...await snapshot(), id: `fixture-${i}` }));
    const feed = await listResearchRuns(h.env); expect(feed.runs).toHaveLength(20); expect(feed.truncated).toBe(true);
  });
  it("lets chat list metadata and retrieve one explicitly attributed scientific packet only", async () => {
    const h = harness(); await h.call(await fullSnapshot());
    const list = await readResearchRuns(h.env, { limit: 1 });
    expect(JSON.stringify(list)).not.toContain("Fixture hypothesis");
    const detail = await readResearchRuns(h.env, { runId: "fixture-cycle", stage: "discovery" });
    expect(detail).toMatchObject({ stages: [{ result: proposal }, { result: null, resultOmitted: true }, { result: null, resultOmitted: true }] });
    for (const input of [{ limit: 100 }, { runId: "../secrets" }, { sql: "DELETE" }, { stage: "discovery" }]) await expect(readResearchRuns(h.env, input)).rejects.toThrow();
  });
});
