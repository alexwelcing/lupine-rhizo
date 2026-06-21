import { describe, expect, it } from "vitest";
import type { Env } from "../../types";
import { stubLedger, type D1Row } from "../../testing/envStub";
import {
  exportOkfBundle,
  listKnowledgeConcepts,
  upsertKnowledgeConcept,
  type KnowledgeConceptRow,
} from "../library";

function envForLedger(
  rows: KnowledgeConceptRow[],
  prepared: Array<{ sql: string; bindings: readonly unknown[] }> = [],
): Env {
  return {
    LEDGER: stubLedger({
      queries: [
        { match: "SELECT * FROM knowledge_documents WHERE concept_id", first: (rows[0] as unknown as D1Row) ?? null },
        { match: "FROM knowledge_documents", all: rows as unknown as D1Row[] },
        { match: "FROM knowledge_edges", all: [] },
      ],
      onPrepare: (sql, bindings) => prepared.push({ sql, bindings }),
    }),
  } as unknown as Env;
}

const row: KnowledgeConceptRow = {
  concept_id: "claims/w-elastic-sentinel",
  type: "Discovery Claim",
  title: "W elastic sentinel",
  description: "High-error tungsten C11 sentinel.",
  resource: "/claims/w-elastic-sentinel",
  tags_json: '["claim","mlip"]',
  timestamp: "2026-06-21T16:00:00.000Z",
  body_md: "# W elastic sentinel\n\nSee [Fe stability](/hypotheses/fe-stability.md).",
  source_kind: "claim",
  source_id: "w-elastic-sentinel",
  okf_version: "0.1",
  created_at: "2026-06-21T16:00:00.000Z",
  updated_at: "2026-06-21T16:01:00.000Z",
};

describe("knowledge library", () => {
  it("lists concepts with timestamp-first sorting and tag/search filters", async () => {
    const prepared: Array<{ sql: string; bindings: readonly unknown[] }> = [];
    const env = envForLedger([row], prepared);
    const result = await listKnowledgeConcepts(
      env,
      new URL("https://worker.test/knowledge/library?sort=timestamp&order=desc&tag=mlip&q=tungsten"),
    );

    expect(result.count).toBe(1);
    expect(result.concepts[0].tags).toEqual(["claim", "mlip"]);
    const sql = prepared.map((entry) => entry.sql).join("\n");
    expect(sql).toContain("ORDER BY COALESCE(timestamp, updated_at, created_at) DESC");
    expect(sql).toContain("tags_json LIKE");
    expect(sql).toContain("LOWER(title) LIKE");
  });

  it("exports OKF index, log, and concept markdown files", async () => {
    const env = envForLedger([row]);
    const bundle = await exportOkfBundle(env, 10);

    expect(bundle.okf_version).toBe("0.1");
    expect(bundle.files.map((file) => file.path)).toContain("index.md");
    expect(bundle.files.map((file) => file.path)).toContain("log.md");
    const concept = bundle.files.find((file) => file.path === "claims/w-elastic-sentinel.md");
    expect(concept?.content).toContain("---\ntype: \"Discovery Claim\"");
    expect(concept?.content).toContain("tags: [\"claim\", \"mlip\"]");
    expect(concept?.content).toContain("# W elastic sentinel");
    expect(bundle.files.find((file) => file.path === "log.md")?.content).toContain("## 2026-06-21");
  });

  it("upserts concepts and records markdown link edges/events", async () => {
    const prepared: Array<{ sql: string; bindings: readonly unknown[] }> = [];
    const env = envForLedger([row], prepared);
    const result = await upsertKnowledgeConcept(env, {
      concept_id: "claims/w-elastic-sentinel",
      type: "Discovery Claim",
      title: "W elastic sentinel",
      tags: ["MLIP", "claim", "MLIP"],
      body_md: "See [Fe stability](/hypotheses/fe-stability.md).",
    });

    expect(result.concept_id).toBe("claims/w-elastic-sentinel");
    expect(result.tags).toEqual(["claim", "mlip"]);
    const statements = prepared.map((entry) => entry.sql).join("\n");
    expect(statements).toContain("INSERT INTO knowledge_documents");
    expect(statements).toContain("INSERT OR IGNORE INTO knowledge_edges");
    expect(statements).toContain("INSERT OR REPLACE INTO knowledge_events");
    expect(prepared.some((entry) => entry.bindings.includes("hypotheses/fe-stability"))).toBe(true);
  });
});
