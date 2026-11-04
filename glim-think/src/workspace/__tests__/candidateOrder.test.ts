import { describe, expect, it } from "vitest";
// @ts-expect-error Test-only fixture access, excluded from Worker types.
import { readFileSync } from "node:fs";
import { assessCandidateOrder, candidateOrderInputSchema, validateCandidateOrderReport } from "../candidateOrderContracts";

const base = (import.meta as ImportMeta & { url: string }).url;
const fixture = JSON.parse(readFileSync(new URL(
  "../../../../atlas-distill/tests/fixtures/candidate_order.input.json", base), "utf8"));
const expected = JSON.parse(readFileSync(new URL(
  "../../../../atlas-distill/tests/fixtures/candidate_order.assessment.json", base), "utf8"));
const input = () => candidateOrderInputSchema.parse(structuredClone(fixture));
const report = () => ({ schema: "lupine.candidate_order.report.v1", input_sha256: "b".repeat(64),
  input: input(), assessment: structuredClone(expected) });

describe("finite candidate ordering", () => {
  it("matches the Rust shared fixture including source and physical limits", () => {
    expect(assessCandidateOrder(fixture)).toEqual(expected);
    expect(validateCandidateOrderReport(report()).assessment).toEqual(expected);
  });
  it("recomputes rather than trusting choices, gaps, limits or scientific claims", () => {
    const mutations = [
      (r: ReturnType<typeof report>) => { r.assessment.choice_relation = "same_unique_minimum"; },
      (r: ReturnType<typeof report>) => { r.assessment.issues = []; },
      (r: ReturnType<typeof report>) => { r.assessment.pairs[0].reference_gap_ev.lower.numerator = "0"; },
      (r: ReturnType<typeof report>) => { r.assessment.reference_minima.unique = "b"; },
      (r: ReturnType<typeof report>) => { r.assessment.scientific_validation = "validated"; },
    ];
    for (const mutate of mutations) { const r = report(); mutate(r); expect(() => validateCandidateOrderReport(r)).toThrow(); }
    const reordered = report(); reordered.assessment = Object.fromEntries(Object.entries(reordered.assessment).reverse());
    expect(validateCandidateOrderReport(reordered).assessment).toEqual(expected);
  });
  it("keeps endpoint ties distinct from a guaranteed unique choice", () => {
    const x = input(); x.bounds_kind = "declared_deterministic_bounds";
    x.rows[0].reference = { lower: "1", upper: "2" }; x.rows[1].reference = { lower: "2", upper: "3" };
    const a = assessCandidateOrder(x);
    expect(a.reference_minima).toEqual({ possible: ["a", "b"], guaranteed: ["a"], unique: null });
    expect(a.pairs[0].reference_order).toBe("unresolved");
    expect(a.choice_relation).toBe("not_unique_or_unresolved");
  });
  it("handles exact ties and overlapping boxes without selecting an arbitrary winner", () => {
    const x = input(); x.rows[1].reference = { ...x.rows[0].reference };
    expect(assessCandidateOrder(x).reference_minima).toEqual({ possible: ["a", "b"], guaranteed: ["a", "b"], unique: null });
    x.bounds_kind = "declared_deterministic_bounds";
    x.rows.forEach(r => { r.reference = { lower: "1", upper: "3" }; });
    expect(assessCandidateOrder(x).reference_minima).toEqual({ possible: ["a", "b"], guaranteed: [], unique: null });
  });
  it("preserves signed tiny gaps exactly", () => {
    const x = input(); x.rows[0].reference = { lower: "0", upper: "0" };
    x.rows[1].reference = { lower: "0.00000000000000000001", upper: "0.00000000000000000001" };
    const a = assessCandidateOrder(x);
    expect(a.pairs[0].reference_order).toBe("left_lower");
    expect(a.pairs[0].reference_gap_ev.lower).toEqual({ numerator: "1", denominator: "100000000000000000000" });
  });
  it("is invariant to candidate order and independent constant shifts of either method", () => {
    const x = input(); x.rows.reverse();
    x.rows.forEach(r => {
      r.prediction.lower = String(Number(r.prediction.lower) + 20);
      r.prediction.upper = String(Number(r.prediction.upper) + 20);
      r.reference.lower = String(Number(r.reference.lower) - 7);
      r.reference.upper = String(Number(r.reference.upper) - 7);
    });
    expect(assessCandidateOrder(x)).toEqual(expected);
  });
  it("matches exhaustive corner minima on 64 three-candidate boxes", () => {
    const boxes = [[0, 0], [0, 1], [1, 1], [1, 2]];
    for (let code = 0; code < 64; code++) {
      const x = input(); x.bounds_kind = "declared_deterministic_bounds";
      x.rows = [0, 1, 2].map(i => ({ ...x.rows[0], candidate_id: String.fromCharCode(97 + i),
        reference: { lower: String(boxes[(code >> (2 * i)) & 3][0]), upper: String(boxes[(code >> (2 * i)) & 3][1]) } }));
      const winners = Array.from({ length: 8 }, (_, mask) => {
        const values = x.rows.map((r, i) => Number(mask & (1 << i) ? r.reference.upper : r.reference.lower));
        return values.flatMap((v, i) => v === Math.min(...values) ? [x.rows[i].candidate_id] : []);
      });
      const possible = [...new Set(winners.flat())].sort();
      const guaranteed = x.rows.map(r => r.candidate_id).filter(id => winners.every(w => w.includes(id)));
      const unique = winners[0].length === 1 && winners.every(w => w.length === 1 && w[0] === winners[0][0]) ? winners[0][0] : null;
      expect(assessCandidateOrder(x).reference_minima).toEqual({ possible, guaranteed, unique });
    }
  });
  it("keeps unknown scope, assumed precision and unverified exhaustiveness visible", () => {
    const x = input(); x.context.comparability = "unknown"; x.context.protocol = null;
    x.context.fit_exposure = null; x.context.candidate_set_scope = "declared_exhaustive";
    x.bounds_kind = "assumed_printing_bounds";
    expect(assessCandidateOrder(x).issues).toEqual(expect.arrayContaining([
      "comparability_unknown", "reference_or_protocol_unknown", "fitting_exposure_unknown",
      "printing_bounds_are_assumptions", "exhaustiveness_declared_not_verified",
    ]));
    expect(assessCandidateOrder(x).global_minimum_claim).toBe("not_established");
  });
  it("rejects malformed, duplicate, mixed-unit or oversized candidate declarations", () => {
    for (const value of ["NaN", "Infinity", "1e-3", ".1", "1.", "+1", "1".repeat(65)]) {
      const x = input(); x.rows[0].reference.lower = value;
      expect(() => assessCandidateOrder(x)).toThrow();
    }
    const wrongUnits = { ...input(), unit: "eV_per_vacancy" }; expect(() => assessCandidateOrder(wrongUnits)).toThrow();
    const x = input(); x.rows[1].candidate_id = "a"; expect(() => assessCandidateOrder(x)).toThrow();
    x.rows = input().rows.slice(0, 1); expect(() => assessCandidateOrder(x)).toThrow();
    x.rows = Array.from({ length: 33 }, (_, i) => ({ ...input().rows[0], candidate_id: "c" + i }));
    expect(() => assessCandidateOrder(x)).toThrow();
    const unicode = input(); unicode.context.material = "é".repeat(129);
    expect(() => assessCandidateOrder(unicode)).toThrow();
    const width = input(); width.rows[0].reference.upper = "2"; expect(() => assessCandidateOrder(width)).toThrow();
    width.bounds_kind = "declared_deterministic_bounds"; width.rows[0].reference.lower = "3";
    expect(() => assessCandidateOrder(width)).toThrow();
  });
});
