import { afterEach, describe, expect, it } from "vitest";
// @ts-expect-error Node 22.18+ SQLite is a test-only dependency, outside Worker types.
import { DatabaseSync } from "node:sqlite";
import { claimAgendaTasks, ensureAgendaSchema, updateAgendaTaskStatus } from "../agenda";
import { buildStubEnv } from "../testing/envStub";

const databases: InstanceType<typeof DatabaseSync>[] = [];
afterEach(() => { for (const db of databases.splice(0)) db.close(); });

function fixture() {
  const db = new DatabaseSync(":memory:");
  databases.push(db);
  // Gate both requests immediately before their candidate/claim SQL executes.
  // The old read-update-read sequence loses ownership despite a guarded UPDATE.
  let waiting = 0;
  let release: (() => void) | undefined;
  const barrier = new Promise<void>(resolve => { release = resolve; });
  let synchronize = false;
  function statement(sql: string, values: unknown[] = []): D1PreparedStatement {
    return {
      bind: (...bound: unknown[]) => statement(sql, bound),
      all: async () => {
        if (synchronize && sql.includes("intelligence_tasks") && (sql.includes("SELECT task_id") || sql.includes("RETURNING"))) {
          waiting += 1;
          if (waiting === 2) release!();
          await barrier;
        }
        return { results: db.prepare(sql).all(...values), success: true, meta: {} };
      },
      run: async () => ({ results: [], success: true, meta: { changes: Number(db.prepare(sql).run(...values).changes) } }),
    } as unknown as D1PreparedStatement;
  }
  const env = buildStubEnv({ LEDGER: { prepare: (sql: string) => statement(sql) } as D1Database });
  const insert = (id: string, specialty = "test", priority = 1) => db.prepare(`
    INSERT INTO intelligence_tasks (task_id, title, domain, specialty, horizon, priority)
    VALUES (?, 'fixture', 'test', ?, 'now', ?)
  `).run(id, specialty, priority);
  return { db, env, insert, synchronize: () => { synchronize = true; } };
}

describe("agenda claim ownership on real SQLite", () => {
  it("reserves coding tasks for their dedicated immutable-attempt ledger", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env);
    h.insert("coding", "coding", 0); h.insert("normal", "test", 1);
    h.db.prepare("UPDATE intelligence_tasks SET domain = 'coding' WHERE task_id = 'coding'").run();
    expect((await claimAgendaTasks(h.env, "general-agent", 10)).map(row => row.task_id)).toEqual(["normal"]);
    expect(await claimAgendaTasks(h.env, "general-agent", 10, "coding")).toEqual([]);
    expect(h.db.prepare("SELECT status, claimed_by FROM intelligence_tasks WHERE task_id='coding'").get())
      .toMatchObject({ status: "queued", claimed_by: null });
  });

  it("returns one dispatch-eligible owner when two claims interleave for one task", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env); h.insert("one"); h.synchronize();
    const results = await Promise.all([claimAgendaTasks(h.env, "worker-a", 1), claimAgendaTasks(h.env, "worker-b", 1)]);
    expect(results.flat()).toHaveLength(1);
    for (const [index, rows] of results.entries()) {
      for (const row of rows) expect(row.claimed_by).toBe(index === 0 ? "worker-a" : "worker-b");
    }
    expect(await claimAgendaTasks(h.env, "retry", 1)).toEqual([]);
  });

  it("gives concurrent batches disjoint IDs owned by their caller", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env);
    for (let n = 0; n < 7; n += 1) h.insert(`task-${n}`);
    h.synchronize();
    const [a, b] = await Promise.all([claimAgendaTasks(h.env, "a", 4), claimAgendaTasks(h.env, "b", 4)]);
    expect(a).toHaveLength(4); expect(b).toHaveLength(3);
    expect(new Set([...a, ...b].map(row => row.task_id)).size).toBe(7);
    expect(a.every(row => row.claimed_by === "a")).toBe(true);
    expect(b.every(row => row.claimed_by === "b")).toBe(true);
  });

  it("keeps simultaneous polls by the same worker disjoint", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env); h.insert("one"); h.insert("two"); h.synchronize();
    const [first, second] = await Promise.all([claimAgendaTasks(h.env, "same", 1), claimAgendaTasks(h.env, "same", 1)]);
    expect(first).toHaveLength(1); expect(second).toHaveLength(1);
    expect(first[0].task_id).not.toBe(second[0].task_id);
    expect([...first, ...second].every(row => row.claimed_by === "same")).toBe(true);
  });

  it("does not return a previous claim when the same worker polls again", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env); h.insert("one");
    expect(await claimAgendaTasks(h.env, "same", 1)).toHaveLength(1);
    expect(await claimAgendaTasks(h.env, "same", 1)).toEqual([]);
  });

  it("keeps aged claimed work ineligible until an explicit operator requeue", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env); h.insert("one");
    await claimAgendaTasks(h.env, "old", 1);
    h.db.prepare("UPDATE intelligence_tasks SET claimed_at = '2000-01-01 00:00:00'").run();
    expect(await claimAgendaTasks(h.env, "new", 1)).toEqual([]);
    // Expiry alone cannot prove that an executor stopped. No implicit replay.
    await updateAgendaTaskStatus(h.env, "one", "queued");
    const reclaimed = await claimAgendaTasks(h.env, "new", 1);
    expect(reclaimed).toHaveLength(1);
    expect(reclaimed[0]).toMatchObject({ task_id: "one", claimed_by: "new", status: "claimed" });
    expect(reclaimed[0].claimed_at).not.toBe("2000-01-01 00:00:00");
    expect(await claimAgendaTasks(h.env, "old", 1)).toEqual([]);
  });

  it("preserves the existing empty-specialty meaning of no filter", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env); h.insert("one", "nonempty");
    expect((await claimAgendaTasks(h.env, "worker", 1, "")).map(row => row.task_id)).toEqual(["one"]);
  });

  it("honors specialty and priority and leaves blocked/running/done rows ineligible", async () => {
    const h = fixture(); await ensureAgendaSchema(h.env);
    h.insert("later", "wanted", 3); h.insert("first", "wanted", 1); h.insert("other", "other", 0);
    for (const state of ["blocked", "running", "done"] as const) {
      h.insert(state, "wanted", 0); await updateAgendaTaskStatus(h.env, state, state);
    }
    expect((await claimAgendaTasks(h.env, "a", 1, "wanted")).map(row => row.task_id)).toEqual(["first"]);
    expect((await claimAgendaTasks(h.env, "a", 1, "wanted")).map(row => row.task_id)).toEqual(["later"]);
    expect(await claimAgendaTasks(h.env, "a", 1, "wanted")).toEqual([]);
  });
});
