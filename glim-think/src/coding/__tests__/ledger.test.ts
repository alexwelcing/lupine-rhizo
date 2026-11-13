import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error Node fs is a test dependency, outside Worker types.
import { readFileSync } from "node:fs";
// @ts-expect-error Node SQLite is a test dependency, outside Worker types.
import { DatabaseSync } from "node:sqlite";
import { ensureAgendaSchema, completeAgendaTask, updateAgendaTaskStatus } from "../../agenda";
import { buildStubEnv } from "../../testing/envStub";
import {
  admitCodingAttempt, CODING_LEDGER_SCHEMA, ensureCodingLedgerSchema, getCodingAttempt,
  recordCodingAcceptance, recordCodingTerminal,
  type CodingAcceptance, type CodingAdmission, type CodingTerminal,
} from "../ledger";

const databases: InstanceType<typeof DatabaseSync>[] = [];
afterEach(() => { for (const db of databases.splice(0)) db.close(); });
const hash = async (text: string) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)))]
  .map(byte => byte.toString(16).padStart(2, "0")).join("");

async function fixture() {
  const sqlite = new DatabaseSync(":memory:"); databases.push(sqlite);
  const metadata = new WeakMap<object, { sql: string; values: unknown[] }>();
  let loseNextBatchAck = false;
  let failAtBatchStatement = -1;
  const execute = (sql: string, values: unknown[] = []) => {
    const statement = sqlite.prepare(sql);
    if (/^\s*SELECT/i.test(sql)) return { results: statement.all(...values), success: true, meta: { changes: 0 } };
    const result = statement.run(...values);
    return { results: [], success: true, meta: { changes: Number(result.changes) } };
  };
  function prepared(sql: string, values: unknown[] = []): D1PreparedStatement {
    const statement = {
      bind: (...bound: unknown[]) => prepared(sql, bound),
      first: async () => sqlite.prepare(sql).get(...values) ?? null,
      all: async () => execute(sql, values),
      run: async () => execute(sql, values),
    } as unknown as D1PreparedStatement;
    metadata.set(statement, { sql, values }); return statement;
  }
  const db = {
    prepare: prepared,
    batch: async (statements: D1PreparedStatement[]) => {
      sqlite.exec("BEGIN"); let results;
      try {
        results = statements.map((statement, index) => {
          if (index === failAtBatchStatement) { failAtBatchStatement = -1; throw new Error("injected transaction failure"); }
          const { sql, values } = metadata.get(statement)!; return execute(sql, values);
        });
        sqlite.exec("COMMIT");
      } catch (error) { sqlite.exec("ROLLBACK"); throw error; }
      if (loseNextBatchAck) { loseNextBatchAck = false; throw new Error("lost batch acknowledgement"); }
      return results;
    },
  } as unknown as D1Database;
  const env = buildStubEnv({ LEDGER: db });
  await ensureAgendaSchema(env); await ensureCodingLedgerSchema(db);
  async function input(taskId = "coding-task", attemptId = "attempt-one", ownerId = "runner") {
    const manifestJson = JSON.stringify({ schema: "lupine.coding-task.v1", taskId, attemptId,
      repository: { owner: "example", name: "repo", commit: "a".repeat(40) }, command: "npm test" });
    const inputSha256 = await hash(manifestJson);
    sqlite.prepare(`INSERT OR IGNORE INTO intelligence_tasks (task_id,title,domain,specialty,horizon,payload)
      VALUES (?, 'Bounded coding task', 'coding', 'coding', 'now', ?)`).run(taskId, JSON.stringify({ codingInputSha256: inputSha256 }));
    return { taskId, attemptId, ownerId, inputSha256, manifestJson };
  }
  const task = (taskId = "coding-task") => sqlite.prepare("SELECT * FROM intelligence_tasks WHERE task_id=?").get(taskId);
  return { sqlite, db, env, input, task,
    loseAck: () => { loseNextBatchAck = true; }, failBatch: (index: number) => { failAtBatchStatement = index; } };
}

async function terminal(admission: CodingAdmission, outcome: CodingTerminal["outcome"] = "succeeded"): Promise<CodingTerminal> {
  const receiptJson = JSON.stringify({ schema: "fixture.raw-coding-receipt.v1", taskId: admission.taskId,
    attemptId: admission.attemptId, inputSha256: admission.inputSha256, outcome });
  return { taskId: admission.taskId, attemptId: admission.attemptId, ownerId: admission.ownerId,
    inputSha256: admission.inputSha256, outcome, receiptJson, receiptSha256: await hash(receiptJson),
    executionExitCode: outcome === "succeeded" ? 0 : null,
    evidence: outcome === "succeeded" ? { artifactKey: "private/result.json", sha256: "b".repeat(64), bytes: 100 } : null,
    evidenceVerified: outcome === "succeeded", cleanupConfirmed: outcome === "succeeded" };
}
const acceptance = (t: CodingTerminal, decision: CodingAcceptance["decision"] = "accepted"): CodingAcceptance => ({
  taskId: t.taskId, attemptId: t.attemptId, ownerId: t.ownerId, inputSha256: t.inputSha256,
  terminalReceiptSha256: t.receiptSha256, decision, reviewerId: "separate-reviewer", reason: "Coding evidence inspected",
});

describe("coding attempt ledger on transactional SQLite", () => {
  it("atomically binds an authorized agenda input and returns only one fresh admission", async () => {
    const h = await fixture(); const i = await h.input();
    const results = await Promise.all([admitCodingAttempt(h.db, i), admitCodingAttempt(h.db, i)]);
    expect(results.map(r => r.admission).sort()).toEqual(["created", "replay"]);
    expect(h.task()).toMatchObject({ status: "running", claimed_by: "runner" });
    expect((await getCodingAttempt(h.db, i.attemptId))?.manifestJson).toBe(i.manifestJson);
  });

  it("admits a task already claimed by this owner, never another owner", async () => {
    const h = await fixture(); const i = await h.input();
    h.sqlite.prepare("UPDATE intelligence_tasks SET status='claimed',claimed_by='other'").run();
    await expect(admitCodingAttempt(h.db, i)).rejects.toMatchObject({ code: "conflict" });
    h.sqlite.prepare("UPDATE intelligence_tasks SET claimed_by='runner'").run();
    expect((await admitCodingAttempt(h.db, i)).admission).toBe("created");
  });

  it("rejects missing, noncoding and mismatched authorized-input tasks without creating attempts", async () => {
    const h = await fixture(); const i = await h.input();
    h.sqlite.prepare("UPDATE intelligence_tasks SET domain='science'").run();
    await expect(admitCodingAttempt(h.db, i)).rejects.toMatchObject({ code: "conflict" });
    h.sqlite.prepare("UPDATE intelligence_tasks SET domain='coding',payload='{}'").run();
    await expect(admitCodingAttempt(h.db, i)).rejects.toMatchObject({ code: "conflict" });
    h.sqlite.prepare("DELETE FROM intelligence_tasks").run();
    await expect(admitCodingAttempt(h.db, i)).rejects.toMatchObject({ code: "conflict" });
    expect(h.sqlite.prepare("SELECT count(*) n FROM coding_attempts").get().n).toBe(0);
  });

  it("rejects changed input, owner or a second attempt for the same task", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i);
    await expect(admitCodingAttempt(h.db, { ...i, ownerId: "other" })).rejects.toMatchObject({ code: "conflict" });
    const second = await h.input(i.taskId, "second-attempt");
    await expect(admitCodingAttempt(h.db, second)).rejects.toMatchObject({ code: "conflict" });
    const manifestJson = i.manifestJson.replace("npm test", "changed command");
    await expect(admitCodingAttempt(h.db, { ...i, manifestJson, inputSha256: await hash(manifestJson) })).rejects.toMatchObject({ code: "conflict" });
  });

  it("rolls back admission if the agenda projection fails", async () => {
    const h = await fixture(); const i = await h.input(); h.failBatch(1);
    await expect(admitCodingAttempt(h.db, i)).rejects.toThrow("injected transaction failure");
    expect(await getCodingAttempt(h.db, i.attemptId)).toBeNull(); expect(h.task().status).toBe("queued");
  });

  it("lost admission acknowledgement returns replay, never fresh dispatch authority", async () => {
    const h = await fixture(); const i = await h.input(); h.loseAck();
    await expect(admitCodingAttempt(h.db, i)).rejects.toThrow("lost batch acknowledgement");
    expect((await admitCodingAttempt(h.db, i)).admission).toBe("replay");
    expect(h.task().status).toBe("running");
  });

  it("keeps archived raw success separate from accepted coding evidence", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); const t = await terminal(i);
    const raw = await recordCodingTerminal(h.db, t);
    expect(raw.recording).toBe("created"); expect(raw.attempt.acceptance).toBeNull(); expect(h.task().status).toBe("blocked");
    const reviewed = await recordCodingAcceptance(h.db, acceptance(t));
    expect(reviewed.recording).toBe("created"); expect(h.task().status).toBe("done");
    expect(JSON.parse(h.task().result)).toMatchObject({ scientificAcceptance: false, publication: false });
    expect((await recordCodingTerminal(h.db, t)).recording).toBe("replay");
    expect((await recordCodingAcceptance(h.db, acceptance(t))).recording).toBe("replay");
  });

  it.each(["failed", "unknown"] as const)("preserves %s without success, automatic retry or new acceptance", async outcome => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); const t = await terminal(i, outcome);
    await recordCodingTerminal(h.db, t); expect(h.task().status).toBe("blocked");
    await expect(recordCodingAcceptance(h.db, acceptance(t))).rejects.toMatchObject({ code: "conflict" });
    await expect(recordCodingTerminal(h.db, await terminal(i))).rejects.toMatchObject({ code: "conflict" });
    await expect(admitCodingAttempt(h.db, await h.input(i.taskId, "retry"))).rejects.toMatchObject({ code: "conflict" });
    expect((await getCodingAttempt(h.db, i.attemptId))?.terminal?.outcome).toBe(outcome);
  });

  it("does not turn cleanup confirmation into a known result", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i);
    const t = await terminal(i, "unknown"); t.cleanupConfirmed = true; await recordCodingTerminal(h.db, t);
    expect((await getCodingAttempt(h.db, i.attemptId))?.terminal?.outcome).toBe("unknown");
  });

  it("rejects raw success unless exit, archive readback and cleanup gates all pass", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); const t = await terminal(i);
    for (const patch of [{ executionExitCode: 1 }, { executionExitCode: null }, { evidenceVerified: false }, { cleanupConfirmed: false }, { evidence: null }])
      await expect(recordCodingTerminal(h.db, { ...t, ...patch })).rejects.toMatchObject({ code: "invalid-input" });
    expect((await getCodingAttempt(h.db, i.attemptId))?.terminal).toBeNull();
  });

  it("rejects wrong owner, changed evidence and stale terminal hash", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); const t = await terminal(i);
    await expect(recordCodingTerminal(h.db, { ...t, ownerId: "old-owner" })).rejects.toMatchObject({ code: "conflict" });
    await recordCodingTerminal(h.db, t);
    await expect(recordCodingTerminal(h.db, { ...t, evidence: { ...t.evidence!, sha256: "c".repeat(64) } })).rejects.toMatchObject({ code: "conflict" });
    await expect(recordCodingAcceptance(h.db, { ...acceptance(t), terminalReceiptSha256: "d".repeat(64) })).rejects.toMatchObject({ code: "conflict" });
  });

  it("reconciles a lost terminal commit acknowledgement without executing or replacing evidence", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); const t = await terminal(i); h.loseAck();
    await expect(recordCodingTerminal(h.db, t)).rejects.toThrow("lost batch acknowledgement");
    expect((await recordCodingTerminal(h.db, t)).recording).toBe("replay"); expect(h.task().status).toBe("blocked");
    expect(h.sqlite.prepare("SELECT count(*) n FROM coding_terminal_receipts").get().n).toBe(1);
  });

  it("reconciles exact-owner terminal evidence after a generic pre-terminal block", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i);
    await updateAgendaTaskStatus(h.env, i.taskId, "blocked", "operator investigating");
    const t = await terminal(i, "unknown");
    expect((await recordCodingTerminal(h.db, t)).recording).toBe("created");
    expect(h.task().status).toBe("blocked");
    expect(JSON.parse(h.task().result)).toMatchObject({ outcome: "unknown", accepted: false });
    expect((await admitCodingAttempt(h.db, i)).admission).toBe("replay");
  });

  it.each(["accepted", "rejected"] as const)("preserves the %s review projection across generic writes and raw receipt replay", async decision => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i);
    const t = await terminal(i); await recordCodingTerminal(h.db, t);
    await recordCodingAcceptance(h.db, acceptance(t, decision)); const before = h.task();
    await expect(completeAgendaTask(h.env, i.taskId, "forged", "unrelated")).rejects.toThrow();
    await expect(updateAgendaTaskStatus(h.env, i.taskId, "running", "restart")).rejects.toThrow();
    await expect(updateAgendaTaskStatus(h.env, i.taskId, "blocked", "overwritten")).rejects.toThrow();
    expect((await recordCodingTerminal(h.db, t)).recording).toBe("replay");
    expect((await recordCodingAcceptance(h.db, acceptance(t, decision))).recording).toBe("replay");
    expect(h.task()).toEqual(before);
  });

  it("snapshots immutable manifest fields before asynchronous hashing", async () => {
    const h = await fixture(); const i = await h.input(); const expected = { ...i };
    const pending = admitCodingAttempt(h.db, i); i.ownerId = "changed-after-call"; i.manifestJson = "{}";
    const result = await pending;
    expect(result.attempt.ownerId).toBe(expected.ownerId); expect(result.attempt.manifestJson).toBe(expected.manifestJson);
  });

  it("rolls terminal append and task projection back together on failure", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); h.failBatch(1);
    await expect(recordCodingTerminal(h.db, await terminal(i))).rejects.toThrow("injected transaction failure");
    expect((await getCodingAttempt(h.db, i.attemptId))?.terminal).toBeNull(); expect(h.task().status).toBe("running");
  });

  it("fences generic agenda completion/requeue/owner/input mutation while preserving noncoding behavior", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i);
    await expect(completeAgendaTask(h.env, i.taskId, "unreviewed")).rejects.toThrow("fenced");
    await expect(updateAgendaTaskStatus(h.env, i.taskId, "queued")).rejects.toThrow("fenced");
    expect(() => h.sqlite.prepare("UPDATE intelligence_tasks SET claimed_by='other'").run()).toThrow("fenced");
    expect(() => h.sqlite.prepare("UPDATE intelligence_tasks SET payload='{}'").run()).toThrow("input is immutable");
    h.sqlite.prepare("INSERT INTO intelligence_tasks(task_id,title,domain,specialty,horizon) VALUES('normal','normal','science','test','now')").run();
    await completeAgendaTask(h.env, "normal", "normal result"); await updateAgendaTaskStatus(h.env, "normal", "queued");
    expect(h.task("normal").status).toBe("queued");
  });

  it("makes attempt and terminal rows append-only in SQLite itself", async () => {
    const h = await fixture(); const i = await h.input(); await admitCodingAttempt(h.db, i); await recordCodingTerminal(h.db, await terminal(i));
    expect(() => h.sqlite.prepare("UPDATE coding_attempts SET owner_id='other'").run()).toThrow("immutable");
    expect(() => h.sqlite.prepare("DELETE FROM coding_terminal_receipts").run()).toThrow("immutable");
    expect(() => h.sqlite.prepare("DELETE FROM intelligence_tasks").run()).toThrow("immutable");
  });

  it("checks manifest and raw receipt byte identities before mutation", async () => {
    const h = await fixture(); const i = await h.input();
    await expect(admitCodingAttempt(h.db, { ...i, inputSha256: "0".repeat(64) })).rejects.toMatchObject({ code: "invalid-input" });
    await admitCodingAttempt(h.db, i); const t = await terminal(i);
    await expect(recordCodingTerminal(h.db, { ...t, receiptSha256: "0".repeat(64) })).rejects.toMatchObject({ code: "invalid-input" });
    const receiptJson = JSON.stringify({ taskId: i.taskId, attemptId: "wrong", inputSha256: i.inputSha256 });
    await expect(recordCodingTerminal(h.db, { ...t, receiptJson, receiptSha256: await hash(receiptJson) })).rejects.toMatchObject({ code: "invalid-input" });
  });

  it("keeps the explicit migration synchronized with runtime schema initialization", () => {
    const migration: string = readFileSync("migrations/0026_coding_attempt_ledger.sql", "utf8");
    const normalized = migration.split("\n").filter((line: string) => !line.startsWith("--")).join("\n").trim();
    expect(normalized).toBe(CODING_LEDGER_SCHEMA.join(";\n\n") + ";");
  });
});
