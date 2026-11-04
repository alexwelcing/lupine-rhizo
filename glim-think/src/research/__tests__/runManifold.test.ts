import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DatabaseSync } from "node:sqlite";
import { analyzeRunManifold } from "../runManifold";

type Row = { element: string; potential_id: string; potential_label: string; property: string; reference: number; predicted: number; unit: string; pair_style: string };
const common: Row[] = [-0.1, 0, 0.1].flatMap((error, i) =>
  ["C11", "C12", "C44"].map(property => ({
    element: "Cu", potential_id: "p" + i, potential_label: "p" + i,
    property, reference: 100, predicted: 100 * (1 + error), unit: "GPa", pair_style: "fixture",
  })));
let sqlite: DatabaseSync;
let ledger: D1Database;
beforeEach(() => {
  sqlite = new DatabaseSync(":memory:");
  sqlite.exec("CREATE TABLE records (element TEXT,potential_id TEXT,potential_label TEXT,property TEXT,reference REAL,predicted REAL,unit TEXT,pair_style TEXT)");
  ledger = { prepare(sql: string) { return { bind(...bindings: string[]) { return {
    async all() { return { results: sqlite.prepare(sql).all(...bindings) }; },
  }; } }; } } as unknown as D1Database;
});
afterEach(() => sqlite.close());
function insert(rows: Row[]) {
  const statement = sqlite.prepare("INSERT INTO records VALUES (?,?,?,?,?,?,?,?)");
  for (const r of rows) statement.run(r.element, r.potential_id, r.potential_label, r.property, r.reference, r.predicted, r.unit, r.pair_style);
}
describe("POST /run manifold calculation with actual SQLite queries", () => {
  it("reports one mode for perfectly correlated observations", async () => {
    insert(common);
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      vectorCount: 3, participationRatio: 1, descriptiveOnly: true,
      matrix: { complete_row_count: 3, properties: ["C11", "C12", "C44"] },
    });
  });
  it("does not assemble one tensor from different elements sharing an ID", async () => {
    insert(common.map(r => ({ ...r, element: r.property === "C11" ? "Cu" : r.property === "C12" ? "Al" : "Fe" })));
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      error: "insufficient_complete_observations", vectorCount: 0,
      matrix: { input_row_count: 9, complete_row_count: 0 },
    });
  });
  it("keeps the full declared elastic basis when C44 is absent", async () => {
    insert(common.filter(r => r.property !== "C44"));
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      error: "insufficient_complete_observations",
      matrix: { complete_row_count: 0, missing_cell_count: 3, properties: ["C11", "C12", "C44"] },
    });
  });
  it("does not add a sample for an identical repeated cell", async () => {
    insert([...common, common[0]]);
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      vectorCount: 3, participationRatio: 1,
      matrix: { duplicate_record_count: 1, complete_row_count: 3 },
    });
  });
  it("excludes a conflicting cell and retains the route's three-row minimum", async () => {
    insert([...common, { ...common[0], predicted: 105 }]);
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      error: "Insufficient complete vectors", vectorCount: 2,
      matrix: { conflicting_cell_count: 1, excluded_row_count: 1 },
    });
  });
  it("abstains on zero observed variance", async () => {
    insert(common.map(r => ({ ...r, predicted: 100 })));
    expect(await analyzeRunManifold(ledger)).toMatchObject({ error: "no_observed_variation" });
  });
  it("binds a literal element filter instead of interpreting it as SQL", async () => {
    insert(common);
    expect(await analyzeRunManifold(ledger, { element: "Cu' OR 1=1 --" })).toMatchObject({
      error: "insufficient_complete_observations", matrix: { input_record_count: 0 },
    });
  });
  it("does not manufacture a principal direction when the legacy seed is orthogonal to the observed mode", async () => {
    insert(common.map(r => ({
      ...r,
      predicted: r.property === "C12" ? 200 - r.predicted : r.property === "C44" ? 100 : r.predicted,
    })));
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      participationRatio: 1, topEigenvalue: null, principalDirection: null,
    });
  });
  it("retains finite signed observations without imposing a stability filter", async () => {
    insert(common.map(r => r.property === "C44" ? { ...r, reference: -r.reference, predicted: -r.predicted } : r));
    expect(await analyzeRunManifold(ledger)).toMatchObject({
      participationRatio: 1, matrix: { complete_row_count: 3, excluded_row_count: 0 },
    });
  });
});
