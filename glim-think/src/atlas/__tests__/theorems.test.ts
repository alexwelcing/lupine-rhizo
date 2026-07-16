import { describe, expect, it } from "vitest";
import {
  groundableFormalBasis,
  isGroundableRef,
  loadFacetTheorems,
  type AtlasTheoremRef,
} from "../theorems";
import { buildStubEnv, stubLedger } from "../../testing/envStub";
import type { Env } from "../../types";

function row(overrides: Partial<AtlasTheoremRef>): AtlasTheoremRef {
  return {
    id: 1,
    facet: "experiment",
    theorem_name: "OpenDistillationFactory.Materials.Theory.T.t1",
    module: "OpenDistillationFactory.Materials.Theory.T",
    revision: "abc123",
    status: "verified",
    lifecycle_status: "active",
    used_in_hypotheses: 0,
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

describe("loadFacetTheorems", () => {
  it("issues a grounding-filtered, SQL-bounded query by default", async () => {
    const captured: Array<{ sql: string; bindings: readonly unknown[] }> = [];
    const env = buildStubEnv({
      LEDGER: stubLedger({
        onPrepare: (sql, bindings) => captured.push({ sql, bindings }),
        queries: [{ match: "FROM atlas_theorems", all: [] }],
      }),
    });

    const load = await loadFacetTheorems(env, "Experiment");

    expect(captured).toHaveLength(1);
    const { sql, bindings } = captured[0];
    expect(sql).toContain("status IN (?,?)");
    expect(sql).toContain("lifecycle_status = ?");
    expect(sql).toContain("LIMIT ?");
    // Canonical lowercase facet key + verified/extended statuses + active lifecycle + default limit.
    expect(bindings).toEqual(["experiment", "verified", "extended", "active", 128]);
    expect(load.facet).toBe("experiment");
    expect(load.error).toBeNull();
  });

  it("caps the limit at the hard maximum", async () => {
    const captured: Array<{ sql: string; bindings: readonly unknown[] }> = [];
    const env = buildStubEnv({
      LEDGER: stubLedger({
        onPrepare: (sql, bindings) => captured.push({ sql, bindings }),
        queries: [{ match: "FROM atlas_theorems", all: [] }],
      }),
    });

    await loadFacetTheorems(env, "manifold", { limit: 100_000 });

    expect(captured[0].bindings.at(-1)).toBe(512);
  });

  it("distinguishes an empty inventory from a failed inventory load", async () => {
    const emptyEnv = buildStubEnv({
      LEDGER: stubLedger({ queries: [{ match: "FROM atlas_theorems", all: [] }] }),
    });
    const empty = await loadFacetTheorems(emptyEnv, "causal");
    expect(empty.rows).toEqual([]);
    expect(empty.error).toBeNull();

    const failingLedger = {
      prepare: () => {
        throw new Error("no such table: atlas_theorems");
      },
    } as unknown as Env["LEDGER"];
    const failed = await loadFacetTheorems(buildStubEnv({ LEDGER: failingLedger }), "causal");
    expect(failed.rows).toEqual([]);
    expect(failed.error).toContain("no such table");
  });
});

describe("isGroundableRef", () => {
  it("grounds verified rows", () => {
    expect(isGroundableRef(row({ status: "verified" }))).toBe(true);
  });

  it("never grounds imported or failed rows", () => {
    expect(isGroundableRef(row({ status: "imported" }))).toBe(false);
    expect(isGroundableRef(row({ status: "failed" }))).toBe(false);
  });

  it("grounds extended rows only when the extension policy approves facet+module", () => {
    expect(
      isGroundableRef(
        row({
          status: "extended",
          module: "OpenDistillationFactory.Materials.DistillAtlas.Foo",
        }),
      ),
    ).toBe(true);
    expect(
      isGroundableRef(
        row({ status: "extended", module: "OpenDistillationFactory.Materials.Theory.T" }),
      ),
    ).toBe(false);
    expect(
      isGroundableRef(
        row({
          status: "extended",
          facet: "manifold",
          module: "OpenDistillationFactory.Materials.DistillAtlas.Foo",
        }),
      ),
    ).toBe(false);
  });

  it("never grounds retired or superseded rows", () => {
    expect(isGroundableRef(row({ status: "verified", lifecycle_status: "retired" }))).toBe(false);
    expect(isGroundableRef(row({ status: "verified", lifecycle_status: "superseded" }))).toBe(false);
  });
});

describe("groundableFormalBasis", () => {
  const mixed: AtlasTheoremRef[] = [
    row({ id: 1, theorem_name: "T.verified", status: "verified" }),
    row({ id: 2, theorem_name: "T.imported", status: "imported" }),
    row({ id: 3, theorem_name: "T.failed", status: "failed" }),
    row({
      id: 4,
      theorem_name: "T.extApproved",
      status: "extended",
      module: "OpenDistillationFactory.Materials.RegimeGate.T",
    }),
    row({ id: 5, theorem_name: "T.extUnapproved", status: "extended" }),
  ];

  it("excludes failed, imported, and unapproved-extended rows from the payload", () => {
    const basis = groundableFormalBasis(mixed);
    expect(basis.map((b) => b.theorem)).toEqual(["T.verified", "T.extApproved"]);
  });

  it("scopes to requested theorem names and attaches helpers", () => {
    const basis = groundableFormalBasis(mixed, {
      theoremNames: ["T.verified"],
      helpers: { "T.verified": "grounds the comparison" },
    });
    expect(basis).toHaveLength(1);
    expect(basis[0]).toMatchObject({
      theorem: "T.verified",
      status: "verified",
      helper: "grounds the comparison",
    });
  });

  it("bounds the payload even when many rows ground", () => {
    const many = Array.from({ length: 300 }, (_, i) =>
      row({ id: i, theorem_name: `T.v${i}`, status: "verified" }),
    );
    expect(groundableFormalBasis(many)).toHaveLength(64);
    expect(groundableFormalBasis(many, { maxRefs: 1000 })).toHaveLength(256);
  });
});
