import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
// @ts-expect-error Test-only Node 22 SQLite; Worker types exclude Node.
import { DatabaseSync } from "node:sqlite";
// @ts-expect-error Test-only VM for the unchanged graph panel; Worker types exclude Node.
import { runInNewContext } from "node:vm";
import { Manifold } from "../../agents/manifold";
import type { Env } from "../../types";
import { buildGraphSnapshot, type GraphNode } from "../snapshot";
import { GRAPH_HTML } from "../page";

vi.mock("../../agents/base", () => ({ GlimThinkAgent: class {} }));

let sqlite: DatabaseSync;
let ledger: D1Database;
beforeEach(() => {
  sqlite = new DatabaseSync(":memory:");
  sqlite.exec(`
    CREATE TABLE records (
      record_id TEXT, element TEXT, potential_id TEXT, potential_label TEXT,
      property TEXT, reference REAL, predicted REAL, unit TEXT, pair_style TEXT, timestamp TEXT
    );
    CREATE TABLE claims (
      claim_id TEXT PRIMARY KEY, agent_id TEXT, claim_type TEXT, claim_data TEXT,
      evidence_ids TEXT, confidence REAL, status TEXT, description TEXT, created_at TEXT, timestamp TEXT
    );
    CREATE TABLE hypotheses (
      id TEXT, title TEXT, status TEXT, confidence REAL, evidence_ids TEXT, created_at TEXT
    );
  `);
  ledger = { prepare(sql: string) {
    let bindings: unknown[] = [];
    return {
      bind(...values: unknown[]) { bindings = values; return this; },
      async all() { return { results: sqlite.prepare(sql).all(...bindings) }; },
      async first() { return sqlite.prepare(sql).get(...bindings); },
      async run() { return sqlite.prepare(sql).run(...bindings); },
    };
  } } as unknown as D1Database;
});
afterEach(() => sqlite.close());

function agent() {
  const instance = Object.create(Manifold.prototype) as Manifold;
  Object.assign(instance, {
    // Durable Object cache is a transport double; ledger queries/upsert use real SQLite.
    sql: () => [],
    queryLedger: async (sql: string, ...bindings: unknown[]) => sqlite.prepare(sql).all(...bindings),
    env: { LEDGER: ledger },
  });
  return instance;
}
function insertRows() {
  const stmt = sqlite.prepare("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)");
  const errors = [[0, 0], [0.1, 0], [0, 0.1], [0.1, 0.1]];
  errors.forEach((row, i) => row.forEach((error, j) => {
    const reference = j === 0 ? 200 : 100;
    stmt.run(`record:${i}:${j}`, "Cu", null, `model-${i}`, j === 0 ? "C11" : "C12",
      reference, reference * (1 + error), "GPa", "fixture", "2026-11-04T00:00:00Z");
  }));
  stmt.run("excluded", "Cu", null, "missing", "C11", 200, 210, "GPa", "fixture", "2026-11-04T00:00:00Z");
}
function claim(id: string, data: unknown, type = "ManifoldAnalysis", description = "Legacy claim") {
  sqlite.prepare("INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?,?)").run(
    id, "fixture", type, typeof data === "string" ? data : JSON.stringify(data),
    "[]", 0.85, "proposed", description, "2026-11-04T00:00:00Z", "2026-11-04T00:00:00Z",
  );
}
async function snapshot() {
  // Other optional graph tables are absent, exercising the existing best-effort reads.
  return JSON.parse(JSON.stringify(await buildGraphSnapshot({ LEDGER: ledger } as Env))) as
    Awaited<ReturnType<typeof buildGraphSnapshot>>;
}
function panelFor(data: GraphNode): string {
  // Execute the actual inline panel renderer and escaping helper. No browser/network claim.
  const panelStart = GRAPH_HTML.indexOf("  function showPanel(data)");
  const escapeStart = GRAPH_HTML.indexOf("  function escapeHtml(s)");
  const escapeEnd = GRAPH_HTML.indexOf("\n  }", escapeStart) + 4;
  expect(panelStart).toBeGreaterThan(0);
  expect(escapeStart).toBeGreaterThan(panelStart);
  expect(escapeEnd).toBeGreaterThan(escapeStart);
  const panel = { innerHTML: "", querySelectorAll: () => [] };
  runInNewContext(GRAPH_HTML.slice(panelStart, escapeStart) +
    GRAPH_HTML.slice(escapeStart, escapeEnd) + "\nshowPanel(data);", {
    data, TYPE_COLORS: { claim: "#c084fc" },
    document: { getElementById: () => panel },
    cy: { getElementById: () => ({ outgoers: () => [], incomers: () => [] }) },
  }, { timeout: 1000 });
  return panel.innerHTML;
}

describe("Manifold evidence through the knowledge graph", () => {
  it("preserves actual producer qualifications through claim SQL, JSON and the graph panel", async () => {
    insertRows();
    await expect(agent().runAnalysis({ element: "Cu", force: true })).resolves.toMatchObject({ ok: true, pr: 2 });
    const saved = sqlite.prepare("SELECT * FROM claims").get();
    const stored = JSON.parse(saved.claim_data);
    expect(stored.descriptive_only).toBe(true);
    expect(JSON.parse(saved.evidence_ids)).toHaveLength(8);
    sqlite.prepare("INSERT INTO hypotheses VALUES (?,?,?,?,?,?)").run(
      "h1", "Fixture hypothesis", "open", null, JSON.stringify([saved.claim_id]), saved.created_at,
    );
    const graph = await snapshot();
    const node = graph.nodes.find(n => n.id === saved.claim_id)!;
    expect(node).toMatchObject({
      type: "claim", status: "proposed", confidence: 0.6,
      description: saved.description, analysis_scope: "descriptive only",
      confidence_basis: "legacy heuristic, not a calibrated probability",
      matrix_contract: "observed-complete-cases-v1",
      row_unit: "element-and-potential-identity", scaling: "relative-error-by-reference",
      matrix_properties: "C11, C12", complete_row_count: 4, excluded_row_count: 1,
      missing_cell_count: 1, invalid_cell_count: 0, conflicting_cell_count: 0,
      duplicate_record_count: 0, centered_rank_ceiling: 2,
    });
    expect(node.label).toMatch(/^Descriptive:/);
    expect(graph.edges).toContainEqual(expect.objectContaining({
      source: "h1", target: saved.claim_id, kind: "evidenced_by",
    }));
    const panel = panelFor(node);
    expect(panel).toContain("descriptive only");
    expect(panel).toContain("not a calibrated probability");
    expect(panel).toContain("<dt>complete_row_count</dt><dd>4</dd>");
    expect(panel).toContain("<dt>excluded_row_count</dt><dd>1</dd>");
    expect(panel).toContain("<dt>invalid_cell_count</dt><dd>0</dd>");
    expect(panel).toContain("<dt>confidence</dt><dd>0.6</dd>");
    expect(panel).toContain("/claims/" + encodeURIComponent(saved.claim_id));
    expect(node).not.toHaveProperty("claim_data");
    expect(node).not.toHaveProperty("scientific_validation");
  });

  it("does not create a graph claim when the actual producer abstains", async () => {
    insertRows();
    sqlite.exec("DELETE FROM records WHERE potential_label != 'model-0'");
    await expect(agent().runAnalysis({ element: "Cu", force: true })).resolves.toMatchObject({
      ok: false, error: "insufficient_complete_observations",
    });
    expect((await snapshot()).nodes).toHaveLength(0);
  });

  it("keeps absent, malformed and legacy qualifications explicitly unknown", async () => {
    for (const [i, data] of [null, "{bad", [], { pr: 1.6, hyper_ribbon: true },
      { descriptive_only: "true", confidence_basis: 1, matrix: { complete_row_count: -1, excluded_row_count: 0.5 } },
    ].entries()) claim("legacy-" + i, data);
    for (const node of (await snapshot()).nodes) {
      expect(node).toMatchObject({
        analysis_scope: "not recorded", confidence_basis: "not recorded",
        matrix_contract: "not recorded", complete_row_count: "not recorded",
        excluded_row_count: "not recorded", confidence: 0.85,
      });
      expect(node.label).toMatch(/^Scope unknown:/);
      expect(panelFor(node)).toContain("<dt>analysis_scope</dt><dd>not recorded</dd>");
    }
  });

  it("allows only display fields and escapes recorded text in the actual panel", async () => {
    const unsafe = "<img src=x onerror=alert(1)>";
    claim("text", {
      descriptive_only: true, confidence_basis: unsafe, secret_fixture: "DO_NOT_EXPOSE",
      matrix: { contract: unsafe, properties: ["C11", unsafe], complete_row_count: 2,
        excluded_row_count: 0, centered_rank_ceiling: 1, private_fixture: "DO_NOT_EXPOSE" },
    }, "ManifoldAnalysis", unsafe);
    const node = (await snapshot()).nodes[0];
    expect(JSON.stringify(node)).not.toContain("DO_NOT_EXPOSE");
    expect(panelFor(node)).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(panelFor(node)).not.toContain("<img");
  });

  it("does not assign Manifold qualifications to unrelated claims", async () => {
    claim("other", { descriptive_only: true, confidence_basis: "invented" }, "Other", "Ordinary claim");
    const node = (await snapshot()).nodes[0];
    expect(node).toMatchObject({ label: "Ordinary claim", description: "Ordinary claim", confidence: 0.85 });
    expect(node).not.toHaveProperty("analysis_scope");
    expect(node).not.toHaveProperty("confidence_basis");
  });
});
