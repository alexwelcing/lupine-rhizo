import { describe, expect, it } from "vitest";
import { addTaskEdge, agendaTaskId, bootstrapAgenda, LEAN_GATE_THEOREM_TARGETS } from "../agenda";
import { buildStubEnv, stubLedger } from "../testing/envStub";

interface Captured {
  sql: string;
  bindings: readonly unknown[];
}

describe("agenda lean-formalization template", () => {
  it("seeds tasks carrying theorem/module identity and formalizes completion edges", async () => {
    const captured: Captured[] = [];
    const env = buildStubEnv({
      LEDGER: stubLedger({ onPrepare: (sql, bindings) => captured.push({ sql, bindings }) }),
    });

    await bootstrapAgenda(env, { targetTaskCount: 1, cycleKind: "test" });

    const taskInserts = captured.filter(
      (c) => c.sql.includes("INSERT OR IGNORE INTO intelligence_tasks") && c.bindings[2] === "lean-formalization",
    );
    expect(taskInserts.length).toBeGreaterThan(0);

    const payload = JSON.parse(String(taskInserts[0].bindings[6])) as {
      gates: string[];
      theorem_targets: Array<{ gate: string; theorem: string; module: string; facet: string }>;
      completion_edge: { kind: string; to_domain: string };
    };
    // Theorem/module identity — not generic gates.
    expect(payload.theorem_targets).toEqual(LEAN_GATE_THEOREM_TARGETS);
    for (const target of payload.theorem_targets) {
      expect(target.theorem).toContain("OpenDistillationFactory.");
      expect(target.module).toContain("OpenDistillationFactory.");
      expect(["causal", "experiment", "manifold", "theorist"]).toContain(target.facet);
    }
    expect(payload.gates).toEqual(payload.theorem_targets.map((t) => t.gate));
    expect(payload.completion_edge).toEqual({ kind: "formalizes", to_domain: "verification" });

    // Completion edges land in task_edges: lean task → verification task, same element+horizon.
    const edgeInserts = captured.filter((c) => c.sql.includes("INSERT OR IGNORE INTO task_edges"));
    expect(edgeInserts.length).toBeGreaterThan(0);
    const cuNow = edgeInserts.find((c) => c.bindings[0] === agendaTaskId("lean-formalization", "Cu", "now"));
    expect(cuNow?.bindings).toEqual([
      agendaTaskId("lean-formalization", "Cu", "now"),
      agendaTaskId("verification", "Cu", "now"),
      "formalizes",
    ]);
  });
});

describe("addTaskEdge", () => {
  it("writes an idempotent edge row", async () => {
    const captured: Captured[] = [];
    const env = buildStubEnv({
      LEDGER: stubLedger({ onPrepare: (sql, bindings) => captured.push({ sql, bindings }) }),
    });

    await addTaskEdge(env, "a", "b", "formalizes");
    await addTaskEdge(env, "a", "b", "formalizes");

    const inserts = captured.filter((c) => c.sql.includes("INSERT OR IGNORE INTO task_edges"));
    expect(inserts).toHaveLength(2);
    expect(inserts[0].bindings).toEqual(["a", "b", "formalizes"]);
  });
});
