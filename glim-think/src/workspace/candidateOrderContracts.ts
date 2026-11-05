import { z } from "zod";

const id = z.string().regex(/^[A-Za-z0-9_.:-]{1,96}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const text = z.string().refine(s => s.trim().length > 0 && new TextEncoder().encode(s).length <= 256);
const decimal = z.string().max(64).regex(/^-?[0-9]+(?:\.[0-9]+)?$/);
const bounds = z.strictObject({ lower: decimal, upper: decimal });
export const candidateOrderInputSchema = z.strictObject({
  schema: z.literal("lupine.candidate_order.input.v1"),
  unit: z.literal("eV"),
  context: z.strictObject({
    source_id: id, source_sha256: hash.nullable(),
    model_id: id, model_sha256: hash.nullable(), model_kind: z.enum(["model", "reported", "synthetic"]),
    material: text, composition: text, reference_convention: text.nullable(),
    protocol: text.nullable(), fit_exposure: text.nullable(),
    candidate_set_id: id, candidate_set_sha256: hash.nullable(),
    candidate_set_scope: z.enum(["listed_only", "declared_exhaustive"]),
    comparability: z.enum(["declared", "unknown"]),
  }),
  bounds_kind: z.enum(["exact_values", "assumed_printing_bounds", "declared_deterministic_bounds"]),
  rows: z.array(z.strictObject({
    candidate_id: id, label: text, anchor: text, reference: bounds, prediction: bounds,
  })).min(2).max(32),
});
export type CandidateOrderInput = z.infer<typeof candidateOrderInputSchema>;
type Q = readonly [bigint, bigint];
type Interval = readonly [Q, Q];
export type OrderFraction = { numerator: string; denominator: string };
type Gap = { lower: OrderFraction; upper: OrderFraction };
export type Order = "left_lower" | "right_lower" | "exact_tie" | "unresolved";

function ratio(n: bigint, d: bigint): Q {
  let a = n < 0n ? -n : n; let b = d;
  while (b !== 0n) { const next = a % b; a = b; b = next; }
  return [n / a, d / a];
}
function parse(value: string): Q {
  const negative = value.startsWith("-");
  const parts = (negative ? value.slice(1) : value).split(".");
  return ratio((negative ? -1n : 1n) * BigInt(parts.join("")), 10n ** BigInt(parts[1]?.length ?? 0));
}
function sub(a: Q, b: Q): Q { return ratio(a[0] * b[1] - b[0] * a[1], a[1] * b[1]); }
function cmp(a: Q, b: Q): number { const d = a[0] * b[1] - b[0] * a[1]; return d < 0n ? -1 : d > 0n ? 1 : 0; }
function interval(b: { lower: string; upper: string }): Interval {
  const l = parse(b.lower); const u = parse(b.upper);
  if (cmp(l, u) > 0) throw new Error("Reversed interval");
  return [l, u];
}
function gap(a: Interval, b: Interval): Interval { return [sub(b[0], a[1]), sub(b[1], a[0])]; }
function fraction(q: Q): OrderFraction { return { numerator: q[0].toString(), denominator: q[1].toString() }; }
function exported(v: Interval): Gap { return { lower: fraction(v[0]), upper: fraction(v[1]) }; }
function order(v: Interval): Order {
  if (v[0][0] > 0n) return "left_lower";
  if (v[1][0] < 0n) return "right_lower";
  if (v[0][0] === 0n && v[1][0] === 0n) return "exact_tie";
  return "unresolved";
}
function minima(ids: string[], values: Interval[]) {
  const possible: string[] = []; const guaranteed: string[] = []; let unique: string | null = null;
  values.forEach((v, i) => {
    if (values.every((w, j) => i === j || cmp(v[0], w[1]) <= 0)) possible.push(ids[i]);
    if (values.every((w, j) => i === j || cmp(v[1], w[0]) <= 0)) guaranteed.push(ids[i]);
    if (values.every((w, j) => i === j || cmp(v[1], w[0]) < 0)) unique = ids[i];
  });
  return { possible, guaranteed, unique };
}

/** Exact arithmetic on declared independent closed intervals; no physical admission. */
export function assessCandidateOrder(value: unknown) {
  const input = candidateOrderInputSchema.parse(value);
  const rows = [...input.rows].sort((a, b) => a.candidate_id < b.candidate_id ? -1 : a.candidate_id > b.candidate_id ? 1 : 0);
  const ids = rows.map(r => r.candidate_id);
  if (new Set(ids).size !== ids.length) throw new Error("Duplicate candidate identity");
  const reference = rows.map(r => interval(r.reference));
  const prediction = rows.map(r => interval(r.prediction));
  if (input.bounds_kind === "exact_values" && [...reference, ...prediction].some(v => cmp(v[0], v[1]) !== 0))
    throw new Error("Exact values cannot have width");
  const reference_minima = minima(ids, reference);
  const prediction_minima = minima(ids, prediction);
  const choice_relation = reference_minima.unique !== null && prediction_minima.unique !== null
    ? reference_minima.unique === prediction_minima.unique ? "same_unique_minimum" : "different_unique_minima"
    : "not_unique_or_unresolved";
  const pairs: {
    left: string; right: string; reference_gap_ev: Gap; prediction_gap_ev: Gap; gap_error_ev: Gap;
    reference_order: Order; prediction_order: Order; agreement: string;
  }[] = [];
  for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) {
    const r = gap(reference[i], reference[j]); const p = gap(prediction[i], prediction[j]);
    const ro = order(r); const po = order(p);
    const agreement = ro === "exact_tie" && po === "exact_tie" ? "exact_tie_both"
      : ro === "unresolved" || po === "unresolved" || ro === "exact_tie" || po === "exact_tie" ? "unresolved"
        : ro === po ? "same_strict_order" : "opposite_strict_order";
    pairs.push({ left: ids[i], right: ids[j], reference_gap_ev: exported(r), prediction_gap_ev: exported(p),
      gap_error_ev: exported(gap(r, p)), reference_order: ro, prediction_order: po, agreement });
  }
  const c = input.context;
  const issues = ["source_and_physical_scope_unverified"];
  if (c.comparability === "unknown") issues.push("comparability_unknown");
  if (c.reference_convention === null || c.protocol === null) issues.push("reference_or_protocol_unknown");
  if (c.source_sha256 === null || c.model_sha256 === null || c.candidate_set_sha256 === null) issues.push("artifact_identity_unknown");
  if (c.fit_exposure === null) issues.push("fitting_exposure_unknown");
  issues.push(c.candidate_set_scope === "listed_only" ? "candidate_search_not_exhaustive" : "exhaustiveness_declared_not_verified");
  if (input.bounds_kind === "assumed_printing_bounds") issues.push("printing_bounds_are_assumptions");
  if (reference_minima.unique === null) issues.push("no_unique_reference_minimum_over_bounds");
  if (prediction_minima.unique === null) issues.push("no_unique_prediction_minimum_over_bounds");
  return {
    arithmetic: "exact_rational_closed_cartesian_bounds" as const,
    reference_minima, prediction_minima, choice_relation, pairs, issues,
    source_verification: "not_performed" as const, scientific_validation: "not_established" as const,
    global_minimum_claim: "not_established" as const, uniform_shift_changes_order: false,
  };
}
export type CandidateOrderAssessment = ReturnType<typeof assessCandidateOrder>;
const reportSchema = z.strictObject({
  schema: z.literal("lupine.candidate_order.report.v1"), input_sha256: hash,
  input: candidateOrderInputSchema, assessment: z.unknown(),
});

/** Compare only the bounded expected shape, without recursing into arbitrary extra data. */
function matches(actual: unknown, expected: unknown): boolean {
  if (Array.isArray(expected))
    return Array.isArray(actual) && actual.length === expected.length && expected.every((v, i) => matches(actual[i], v));
  if (expected !== null && typeof expected === "object") {
    if (actual === null || typeof actual !== "object" || Array.isArray(actual)) return false;
    const a = actual as Record<string, unknown>; const e = expected as Record<string, unknown>;
    return Object.keys(a).length === Object.keys(e).length && Object.entries(e).every(([k, v]) =>
      Object.prototype.hasOwnProperty.call(a, k) && matches(a[k], v));
  }
  return actual === expected;
}

/** Recomputes all bounds and choices; the producer cannot suppress limits. */
export function validateCandidateOrderReport(value: unknown) {
  const report = reportSchema.parse(value);
  const assessment = assessCandidateOrder(report.input);
  if (!matches(report.assessment, assessment)) throw new Error("Inconsistent candidate-order assessment");
  return { ...report, assessment };
}
export type CandidateOrderReport = ReturnType<typeof validateCandidateOrderReport>;
