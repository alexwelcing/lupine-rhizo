import { beforeEach, describe, expect, it, vi } from "vitest";
import { Manifold } from "../manifold";
import { buildObservedManifoldMatrix, type ManifoldRecord } from "../../research/observedManifoldMatrix";

vi.mock("../base", () => ({ GlimThinkAgent: class {} }));
const { persist } = vi.hoisted(() => ({ persist: vi.fn(async (_db: unknown, _data: unknown) => undefined) }));
vi.mock("../../research/recurringClaims", async importOriginal => ({
  ...await importOriginal<typeof import("../../research/recurringClaims")>(),
  upsertRecurringClaim: persist,
}));

function recordsFor(label: string, e11: number, e12?: number, element = "Cu") {
  const values = [{ property: "C11", reference: 200, predicted: 200 * (1 + e11) }];
  if (e12 !== undefined) values.push({ property: "C12", reference: 100, predicted: 100 * (1 + e12) });
  return values.map(v => ({
    ...v, element, potential_label: label, unit: "GPa",
    record_id: `${element}:${label}:${v.property}`,
    pair_style: "fixture", timestamp: "2026-11-04T00:00:00Z",
  }));
}
const incomplete = [
  ...recordsFor("a", 0.1),
  ...recordsFor("b", 0.1, 0.1).filter(r => r.property === "C12"),
  ...recordsFor("c", -0.1, -0.1),
];
const complete = [
  ...recordsFor("a", 0, 0), ...recordsFor("b", 0.1, 0),
  ...recordsFor("c", 0, 0.1), ...recordsFor("d", 0.1, 0.1),
];

function agentFor(records: ManifoldRecord[], cachedClaim?: Record<string, unknown>) {
  const agent = Object.create(Manifold.prototype) as Manifold;
  const sql = vi.fn((parts: TemplateStringsArray) =>
    parts.join("").includes("SELECT claim_id, pr") && cachedClaim
      ? [{ claim_id: "cached-claim", pr: 1.6 }] : []);
  const first = vi.fn(async () => ({ claim_data: JSON.stringify(cachedClaim) }));
  Object.assign(agent, {
    sql,
    queryLedger: vi.fn(async () => records),
    env: { LEDGER: { prepare: () => ({ bind: () => ({ first }) }) } },
  });
  return agent;
}
async function runTool(agent: Manifold, records: ManifoldRecord[]) {
  const execute = agent.getTools().compute_manifold.execute!;
  return execute({ records }, { toolCallId: "matrix-test", messages: [] });
}

beforeEach(() => persist.mockClear());

describe("observed manifold matrix in the actual consumer", () => {
  it("abstains in both entry points when only one row is fully observed", async () => {
    const agent = agentFor(incomplete);
    await expect(runTool(agent, incomplete)).resolves.toMatchObject({
      error: "insufficient_complete_observations",
      matrix: { input_row_count: 3, complete_row_count: 1, missing_cell_count: 2 },
    });
    await expect(agent.runAnalysis({ element: "Cu", force: true })).resolves.toMatchObject({
      ok: false, error: "insufficient_complete_observations",
      matrix: { excluded_row_count: 2 },
    });
    expect(persist).not.toHaveBeenCalled();
  });

  it("retains true zero residuals, excludes missing rows and attaches only used evidence", async () => {
    const records = [...complete, ...recordsFor("missing", 0.8)];
    const agent = agentFor(records);
    const toolResult = await runTool(agent, records);
    expect(toolResult).toMatchObject({
      participationRatio: 2, potentialCount: 4, propertyCount: 2,
      descriptiveOnly: true,
      matrix: { complete_row_count: 4, excluded_row_count: 1, centered_rank_ceiling: 2 },
    });
    const result = await agent.runAnalysis({ element: "Cu", force: true });
    expect(result).toMatchObject({
      ok: true, pr: 2, potential_count: 4, descriptive_only: true,
      matrix: { input_record_count: 9, complete_row_count: 4, missing_cell_count: 1 },
    });
    expect(persist).toHaveBeenCalledOnce();
    const saved = persist.mock.calls[0][1] as unknown as {
      claimData: Record<string, unknown>; evidenceIds: string[];
    };
    expect(saved.claimData).toMatchObject({ evidence_record_count: 8, descriptive_only: true });
    expect(saved.evidenceIds).toHaveLength(8);
    expect(saved.evidenceIds.some(id => id.includes("missing"))).toBe(false);
  });

  it("preserves identical repetitions without creating samples and excludes conflicting cells", () => {
    const duplicate = buildObservedManifoldMatrix([...complete, complete[0]]);
    expect(duplicate).toMatchObject({
      ok: true, selection: { complete_row_count: 4, duplicate_record_count: 1 },
    });
    const conflict = buildObservedManifoldMatrix([...complete, { ...complete[0], predicted: 210 }]);
    expect(conflict).toMatchObject({
      ok: true, selection: { complete_row_count: 3, excluded_row_count: 1, conflicting_cell_count: 1 },
    });
  });

  it("excludes zero-reference and nonfinite cells instead of inventing zero errors", () => {
    const extra = [
      ...recordsFor("zero-ref", 0, 0).map(r => r.property === "C11" ? { ...r, reference: 0 } : r),
      ...recordsFor("nonfinite", 0, 0).map(r => r.property === "C12" ? { ...r, predicted: NaN } : r),
    ];
    expect(buildObservedManifoldMatrix([...complete, ...extra])).toMatchObject({
      ok: true, selection: { complete_row_count: 4, excluded_row_count: 2, invalid_cell_count: 2 },
    });
  });

  it("keeps elements and supplied potential identities distinct", () => {
    const byElement = buildObservedManifoldMatrix([
      ...recordsFor("shared-label", 0, 0, "Cu"), ...recordsFor("shared-label", 0.1, 0.1, "Al"),
    ]);
    expect(byElement).toMatchObject({ ok: true, selection: { complete_row_count: 2 } });
    const byId = buildObservedManifoldMatrix([
      ...recordsFor("shared-label", 0, 0).map(r => ({ ...r, potential_id: "id-a" })),
      ...recordsFor("shared-label", 0.1, 0.1).map(r => ({ ...r, potential_id: "id-b" })),
    ]);
    expect(byId).toMatchObject({
      ok: true, selection: { complete_row_count: 2, label_identity_row_count: 0 },
    });
  });

  it("abstains without observed variation or when only a truncated spectrum would be available", async () => {
    const same = [...recordsFor("a", 0, 0), ...recordsFor("b", 0, 0)];
    const agent = agentFor(same);
    await expect(runTool(agent, same)).resolves.toMatchObject({ error: "no_observed_variation" });
    await expect(agent.runAnalysis({ element: "Cu", force: true })).resolves.toMatchObject({
      ok: false, error: "no_observed_variation",
    });
    const wide = Array.from({ length: 6 }, (_, i) => ({
      element: "Cu", potential_label: "a", property: `p${i}`, reference: 1, predicted: 2,
    }));
    expect(buildObservedManifoldMatrix(wide)).toMatchObject({ ok: false });
    expect(persist).not.toHaveBeenCalled();
  });

  it("does not relabel a legacy scalar cache as an observed-matrix result", async () => {
    const agent = agentFor(incomplete, { pr: 1.6, hyper_ribbon: true });
    const result = await agent.runAnalysis({ element: "Cu" });
    expect(result).toMatchObject({
      ok: false, cached: true, error: "legacy_matrix_contract: explicit force required",
    });
    expect(result).not.toHaveProperty("pr");
    expect(persist).not.toHaveBeenCalled();
  });
  it("rehydrates coverage for a current-contract cached result without recomputing", async () => {
    const firstAgent = agentFor(complete);
    await firstAgent.runAnalysis({ element: "Cu", force: true });
    const saved = persist.mock.calls[0][1] as { claimData: Record<string, unknown> };
    const cachedAgent = agentFor([], saved.claimData);
    persist.mockClear();
    await expect(cachedAgent.runAnalysis({ element: "Cu" })).resolves.toMatchObject({
      ok: true, cached: true, pr: 2, descriptive_only: true,
      matrix: { complete_row_count: 4, centered_rank_ceiling: 2 },
    });
    expect(persist).not.toHaveBeenCalled();
  });

});
