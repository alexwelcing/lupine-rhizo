import { describe, expect, it } from "vitest";
import { handleResearchWorkflowRoute } from "../workflows";
import {
  createLeanProofCampaign,
  evaluateLeanProofUnit,
  getLeanProofCampaign,
  recordLeanProofUnitResult,
  verdictForTheoremRow,
  LEAN_PROOF_WORKFLOW_ID,
  type LeanProofUnitRecord,
} from "../leanProofWorkflow";
import { buildStubEnv, stubLedger, type D1Row } from "../../testing/envStub";

const THEOREM = "OpenDistillationFactory.Materials.Theory.HyperRibbon.hyper_ribbon_bound_4d";
const MODULE = "OpenDistillationFactory.Materials.Theory.HyperRibbon";
const COMMIT = "8c0ccf7b31ad54d6beb3363698750d9a081cb796";

interface Captured {
  sql: string;
  bindings: readonly unknown[];
}

function capture(): { captured: Captured[]; onPrepare: (sql: string, bindings: readonly unknown[]) => void } {
  const captured: Captured[] = [];
  return { captured, onPrepare: (sql, bindings) => captured.push({ sql, bindings }) };
}

function unitRow(overrides: Partial<LeanProofUnitRecord> = {}): LeanProofUnitRecord & D1Row {
  return {
    unit_id: `lean-proof:manifold:8c0ccf7b31ad:hyper_ribbon_bound_4d`,
    campaign_id: "lean-proof:manifold:8c0ccf7b31ad",
    theorem_name: THEOREM,
    module: MODULE,
    facet: "manifold",
    source_commit: COMMIT,
    build_artifact: "artifacts/lean-spec/8c0ccf7.tar.gz",
    build_manifest_hash: "a".repeat(64),
    status: "enqueued",
    verdict: "pending",
    agenda_task_id: "lean-proof:lean-proof:manifold:8c0ccf7b31ad:hyper_ribbon_bound_4d",
    completion_target_task_id: "agenda:verification:cu:now",
    sync_status: "upserted",
    sync_detail: null,
    trace_ids_json: JSON.stringify(["trace-1"]),
    created_at: "2026-07-15T00:00:00Z",
    updated_at: "2026-07-15T00:00:00Z",
    ...overrides,
  };
}

describe("lean-proof-promotion registration", () => {
  it("is listed as a first-class workflow descriptor", async () => {
    const response = await handleResearchWorkflowRoute(
      buildStubEnv(),
      new URL("https://worker.test/research/workflows"),
      "GET",
      "",
    );
    const body = await response?.json() as { workflows: Array<{ workflow_id: string }> };
    expect(body.workflows.map((w) => w.workflow_id)).toContain(LEAN_PROOF_WORKFLOW_ID);
  });

  it("describes the promotion unit contract", async () => {
    const response = await handleResearchWorkflowRoute(
      buildStubEnv(),
      new URL(`https://worker.test/research/workflows/${LEAN_PROOF_WORKFLOW_ID}`),
      "GET",
      "",
    );
    const body = await response?.json() as {
      workflow: { unit_kind: string; extension_contract: { evidence_required: string[] } };
    };
    expect(body.workflow.unit_kind).toBe("lean_proof_unit");
    const evidence = body.workflow.extension_contract.evidence_required.join("\n");
    for (const needle of ["theorem_name", "module", "source_commit", "build_manifest_hash", "agenda task id", "inventory sync", "trace_ids"]) {
      expect(evidence).toContain(needle);
    }
  });
});

describe("createLeanProofCampaign — workflow-to-agenda wiring", () => {
  it("stamps agenda tasks carrying theorem/module identity and writes the completion edge", async () => {
    const { captured, onPrepare } = capture();
    const env = buildStubEnv({ LEDGER: stubLedger({ onPrepare }) });

    const result = await createLeanProofCampaign(env, {
      facet: "manifold",
      proof_revision: COMMIT,
      units: [
        {
          theorem_name: THEOREM,
          build_artifact: "artifacts/lean-spec/8c0ccf7.tar.gz",
          build_manifest_hash: "a".repeat(64),
          agenda_task_id: "agenda:verification:cu:now",
          trace_ids: ["trace-1"],
        },
      ],
    });

    expect(result.units_created).toBe(1);
    const [unitId] = result.unit_ids;
    expect(unitId).toContain("lean-proof:manifold:8c0ccf7b31ad");

    // Unit row carries theorem identity + source commit + build hash.
    const unitInsert = captured.find((c) => c.sql.includes("INSERT INTO lean_proof_units"));
    expect(unitInsert).toBeDefined();
    expect(unitInsert?.bindings).toContain(THEOREM);
    expect(unitInsert?.bindings).toContain(MODULE);
    expect(unitInsert?.bindings).toContain("manifold");
    expect(unitInsert?.bindings).toContain(COMMIT);
    expect(unitInsert?.bindings).toContain("a".repeat(64));

    // Agenda task carries theorem/module identity + completion edge in its payload.
    const taskInsert = captured.find((c) => c.sql.includes("INSERT OR IGNORE INTO intelligence_tasks"));
    expect(taskInsert).toBeDefined();
    expect(String(taskInsert?.bindings[0])).toBe(`lean-proof:${unitId}`);
    const payload = JSON.parse(String(taskInsert?.bindings[2])) as {
      workflow_id: string;
      campaign_id: string;
      unit_id: string;
      theorem: { name: string; module: string; facet: string };
      source_commit: string;
      completion_edge: { kind: string; to_task_id: string } | null;
    };
    expect(payload.workflow_id).toBe(LEAN_PROOF_WORKFLOW_ID);
    expect(payload.theorem).toEqual({ name: THEOREM, module: MODULE, facet: "manifold" });
    expect(payload.source_commit).toBe(COMMIT);
    expect(payload.completion_edge).toEqual({ kind: "formalizes", to_task_id: "agenda:verification:cu:now" });

    // The formalizes edge is written into task_edges.
    const edgeInsert = captured.find((c) => c.sql.includes("INSERT OR IGNORE INTO task_edges"));
    expect(edgeInsert?.bindings).toEqual([
      `lean-proof:${unitId}`,
      "agenda:verification:cu:now",
      "formalizes",
    ]);

    // The unit back-references its agenda task.
    const backref = captured.find((c) => c.sql.includes("SET agenda_task_id"));
    expect(backref?.bindings).toEqual([unitId, `lean-proof:${unitId}`]);
  });

  it("rejects facets outside the ATLAS-managed set", async () => {
    const env = buildStubEnv({ LEDGER: stubLedger() });
    await expect(
      createLeanProofCampaign(env, {
        facet: "orchestrator",
        proof_revision: COMMIT,
        units: [{ theorem_name: THEOREM }],
      }),
    ).rejects.toThrow(/not an ATLAS-managed facet/);
  });
});

describe("verdictForTheoremRow — promotion gate", () => {
  const unit = unitRow();

  it("promotes verified rows", () => {
    expect(verdictForTheoremRow({ status: "verified", lifecycle_status: "active" }, unit).verdict).toBe("promote");
  });

  it("rejects failed or missing rows", () => {
    expect(verdictForTheoremRow({ status: "failed", lifecycle_status: "active" }, unit).verdict).toBe("reject");
    expect(verdictForTheoremRow(null, unit).verdict).toBe("reject");
  });

  it("holds imported rows and unapproved extensions for review", () => {
    expect(verdictForTheoremRow({ status: "imported", lifecycle_status: "active" }, unit).verdict).toBe("review");
    // manifold is not in the extension policy, so an extended manifold row is not approved.
    expect(verdictForTheoremRow({ status: "extended", lifecycle_status: "active" }, unit).verdict).toBe("review");
  });

  it("promotes approved extensions and flags build hash drift", () => {
    const expUnit = unitRow({ facet: "experiment", module: "OpenDistillationFactory.Materials.RegimeGate.T" });
    expect(verdictForTheoremRow({ status: "extended", lifecycle_status: "active" }, expUnit).verdict).toBe("promote");
    expect(
      verdictForTheoremRow(
        { status: "verified", lifecycle_status: "active", build_manifest_hash: "b".repeat(64) },
        unit,
      ).verdict,
    ).toBe("review");
  });
});

describe("evaluateLeanProofUnit", () => {
  function envWithTheoremRow(theoremRow: Record<string, unknown> | null) {
    const { captured, onPrepare } = capture();
    const env = buildStubEnv({
      LEDGER: stubLedger({
        onPrepare,
        queries: [
          { match: "FROM lean_proof_units", first: unitRow() },
          { match: "FROM atlas_theorems", first: theoremRow },
        ],
      }),
    });
    return { env, captured };
  }

  it("promotes on a verified inventory row and completes the agenda task + edge", async () => {
    const { env, captured } = envWithTheoremRow({
      status: "verified",
      lifecycle_status: "active",
      build_manifest_hash: "a".repeat(64),
    });

    const result = await evaluateLeanProofUnit(env, "lean-proof:manifold:8c0ccf7b31ad", unitRow().unit_id);

    expect(result.verdict).toBe("promote");
    const done = captured.find((c) => c.sql.includes("UPDATE intelligence_tasks") && c.sql.includes("status = 'done'"));
    expect(done?.bindings[0]).toBe(unitRow().agenda_task_id);
    const edge = captured.find((c) => c.sql.includes("INSERT OR IGNORE INTO task_edges"));
    expect(edge?.bindings).toEqual([unitRow().agenda_task_id, "agenda:verification:cu:now", "formalizes"]);
  });

  it("rejects on a failed inventory row and blocks the agenda task", async () => {
    const { env, captured } = envWithTheoremRow({
      status: "failed",
      lifecycle_status: "active",
      build_manifest_hash: null,
    });

    const result = await evaluateLeanProofUnit(env, "lean-proof:manifold:8c0ccf7b31ad", unitRow().unit_id);

    expect(result.verdict).toBe("reject");
    const blocked = captured.find(
      (c) => c.sql.includes("UPDATE intelligence_tasks") && c.bindings.includes("blocked"),
    );
    expect(blocked?.bindings[0]).toBe(unitRow().agenda_task_id);
  });

  it("rejects when the inventory row is absent (sync never landed)", async () => {
    const { env } = envWithTheoremRow(null);
    const result = await evaluateLeanProofUnit(env, "lean-proof:manifold:8c0ccf7b31ad", unitRow().unit_id);
    expect(result.verdict).toBe("reject");
    expect(result.explanation).toContain("absent");
  });
});

describe("recordUnitResult route", () => {
  it("persists verdict, sync result, and trace IDs on the unit", async () => {
    const { captured, onPrepare } = capture();
    const env = buildStubEnv({
      LEDGER: stubLedger({
        onPrepare,
        queries: [{ match: "FROM lean_proof_units", first: unitRow({ verdict: "pending" }) }],
      }),
    });

    const response = await handleResearchWorkflowRoute(
      env,
      new URL(
        `https://worker.test/research/workflows/${LEAN_PROOF_WORKFLOW_ID}/campaigns/lean-proof:manifold:8c0ccf7b31ad/units/${encodeURIComponent(unitRow().unit_id)}/result`,
      ),
      "POST",
      JSON.stringify({
        verdict: "promote",
        status: "completed",
        sync_status: "upserted",
        sync_detail: "row upserted by atlas_theorem_sync",
        trace_ids: ["trace-9", "trace-10"],
      }),
    );

    expect(response?.status).toBe(200);
    const body = await response?.json() as { verdict: string; agenda: string };
    expect(body.verdict).toBe("promote");
    expect(body.agenda).toBe("completed");
    const update = captured.find((c) => c.sql.includes("UPDATE lean_proof_units"));
    expect(update?.bindings).toContain("upserted");
    expect(update?.bindings).toContain(JSON.stringify(["trace-9", "trace-10"]));
  });
});

describe("getLeanProofCampaign", () => {
  it("returns null for unknown campaigns", async () => {
    const env = buildStubEnv({ LEDGER: stubLedger({ queries: [{ match: "FROM lean_proof_campaigns", first: null }] }) });
    expect(await getLeanProofCampaign(env, "nope")).toBeNull();
  });
});
