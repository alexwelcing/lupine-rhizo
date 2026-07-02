/**
 * Property-aware physical-plausibility validation for benchmark records.
 *
 * History: the original contamination gate was written for the elastic-
 * constant corpus (C11/C12/C44, GPa) and hard-coded |predicted| > 1500,
 * predicted <= 0, reference <= 0, plus a scale-free >500% relative rule.
 * The corpus audit (Causal.runCorpusAudit) flagged exactly this defect:
 * a single absolute bound is myopic once the corpus carries multiple
 * property families — formation enthalpies are legitimately negative,
 * melting points legitimately exceed 1500 K, and zero-crossing properties
 * (stacking-fault energies, B0′ — Fe has B0′ < 0) make blanket positivity
 * and reference-relative rules delete real, informative model failures.
 *
 * This module is the single source of truth for the range gate, exported
 * both as a TS predicate (ingest door, /ingest/batch in src/server.ts)
 * and as SQL predicates (Causal.runDataPurge delete criterion, Manifold
 * defense-in-depth CLEAN filter) so the three lanes cannot drift.
 *
 * Rules:
 *  1. non-finite / NULL predicted or reference is always corrupt;
 *  2. |value| must stay under a per-unit-class physical ceiling
 *     (GPa 1500 — W C11 ≈ 520, diamond ≈ 1080; K 4000 — W melts at
 *     3695 K; unrecognized units fall back to the legacy 1500 backstop);
 *  3. positivity is required only for sign-fixed properties; sign-flexible
 *     properties (formation enthalpy ΔH_f, stacking-fault energy, B0′,
 *     binding/adsorption energies) legitimately cross zero;
 *  4. the scale-free >500% relative rule applies only to sign-fixed
 *     properties — for zero-crossing properties |reference| is not a
 *     scale, so the rule would purge genuine (large, informative) errors.
 *
 * On the legacy corpus (C11/C12/C44 in GPa) every rule reduces exactly to
 * the old predicate, so re-running the purge deletes nothing new.
 */

/** Properties whose sign convention legitimately admits values ≤ 0. */
export const NEGATIVE_ALLOWED_PROPERTIES: readonly string[] = [
  // Compound formation enthalpy — negative for every stable compound.
  "formation_enthalpy",
  "formation_enthalpy_ev_per_atom",
  "dh_f",
  // Intrinsic stacking-fault energy — models (and some hcp-adjacent
  // metals) legitimately produce negative values; a negative prediction
  // is a real failure mode worth keeping, not corruption.
  "stacking_fault_energy",
  "intrinsic_stacking_fault_energy",
  "gamma_sfe",
  // Bulk-modulus pressure derivative — Fe has B0′ < 0.
  "b0_prime",
  "bulk_modulus_pressure_derivative",
  // Generic negative-convention energies.
  "binding_energy",
  "adsorption_energy",
];

/**
 * Physical magnitude ceilings per unit class (case-insensitive match on
 * the `unit` column). Chosen ~30% above the largest physically known
 * value so unit errors (×1000 slips, non-converged sentinels) still trip.
 */
export const UNIT_CEILINGS: ReadonlyArray<readonly [string, number]> = [
  ["gpa", 1500], // elastic/EOS moduli — W C11 ≈ 520, diamond ≈ 1080
  ["k", 4000], // temperatures — W melting point 3695 K
  ["ev", 50], // defect/cohesive energies — max cohesive ≈ 8.9 eV/atom (W)
  ["ev/atom", 50],
  ["angstrom", 100], // lattice constants — large cells are O(10 Å)
  ["j/m^2", 50], // surface energies — max ≈ 4 J/m²
  ["mj/m^2", 50000], // same physical scale as J/m², milli units
  ["dimensionless", 1000], // B0′ and other ratios
];

/** Legacy backstop for unrecognized units (the corpus was GPa-only). */
export const DEFAULT_MAGNITUDE_CEILING = 1500;

/** Human-readable criterion, for purge claims / audit records. */
export const RANGE_GATE_CRITERION =
  "predicted/reference NULL or non-finite; |value| > per-unit ceiling " +
  "(GPa 1500, K 4000, eV 50, Angstrom 100, J/m^2 50, mJ/m^2 50000, " +
  "dimensionless 1000, else 1500); for sign-fixed properties only " +
  "(i.e. excluding formation enthalpy, stacking-fault energy, B0', " +
  "binding/adsorption energies): value <= 0 or " +
  "|predicted-reference| > 5*|reference| (>500% scale-free)";

/** True when `property` may legitimately be zero or negative. */
export function allowsNegative(property: string | null | undefined): boolean {
  if (!property) return false;
  return NEGATIVE_ALLOWED_PROPERTIES.includes(property.trim().toLowerCase());
}

/** Magnitude ceiling for a unit string (legacy 1500 when unrecognized). */
export function magnitudeCeiling(unit: string | null | undefined): number {
  const key = (unit ?? "").trim().toLowerCase();
  for (const [candidate, ceiling] of UNIT_CEILINGS) {
    if (candidate === key) return ceiling;
  }
  return DEFAULT_MAGNITUDE_CEILING;
}

export interface RecordRangeInput {
  property: string;
  unit?: string | null;
  predicted: number;
  reference: number;
}

/**
 * Why a record is physically implausible, or null when it passes.
 * This is the TS twin of `corruptRecordSqlPredicate()` below.
 */
export function recordContaminationReason(input: RecordRangeInput): string | null {
  const pred = Number(input.predicted);
  const ref = Number(input.reference);
  if (!Number.isFinite(pred) || !Number.isFinite(ref)) {
    return "non-finite predicted/reference";
  }
  const ceiling = magnitudeCeiling(input.unit);
  if (Math.abs(pred) > ceiling || Math.abs(ref) > ceiling) {
    return `|value| exceeds the ${ceiling} ceiling for unit '${input.unit ?? ""}'`;
  }
  if (!allowsNegative(input.property)) {
    if (pred <= 0 || ref <= 0) {
      return `non-positive value for sign-fixed property '${input.property}'`;
    }
    if (Math.abs(pred - ref) > 5 * Math.abs(ref)) {
      return `>500% relative error for sign-fixed property '${input.property}'`;
    }
  }
  return null;
}

/** Convenience boolean wrapper over `recordContaminationReason`. */
export function isContaminatedRecord(input: RecordRangeInput): boolean {
  return recordContaminationReason(input) !== null;
}

/** SQL CASE expression mapping the `unit` column to its ceiling. */
function ceilingCaseSql(): string {
  const whens = UNIT_CEILINGS.map(([unit, ceiling]) => `WHEN '${unit}' THEN ${ceiling}`).join(" ");
  return `CASE lower(COALESCE(unit, '')) ${whens} ELSE ${DEFAULT_MAGNITUDE_CEILING} END`;
}

/**
 * SQL predicate (against the `records` table) selecting corrupt rows —
 * the delete criterion for Causal.runDataPurge. Mirrors
 * `recordContaminationReason` exactly; NULLs are corrupt via the leading
 * IS NULL terms (SQLite stores NaN as NULL, so NaN is covered too).
 */
export function corruptRecordSqlPredicate(): string {
  const negList = NEGATIVE_ALLOWED_PROPERTIES.map((p) => `'${p}'`).join(", ");
  const ceiling = ceilingCaseSql();
  return (
    `predicted IS NULL OR reference IS NULL ` +
    `OR ABS(predicted) > (${ceiling}) OR ABS(reference) > (${ceiling}) ` +
    `OR (lower(COALESCE(property, '')) NOT IN (${negList}) ` +
    `AND (predicted <= 0 OR reference <= 0 ` +
    `OR ABS(predicted - reference) > 5 * ABS(reference)))`
  );
}

/**
 * SQL predicate selecting clean rows — the defense-in-depth filter for
 * Manifold record loading. Exact negation of `corruptRecordSqlPredicate`
 * with explicit NOT NULL guards so the negated NULL logic stays sound.
 */
export function cleanRecordSqlPredicate(): string {
  return `predicted IS NOT NULL AND reference IS NOT NULL AND NOT (${corruptRecordSqlPredicate()})`;
}
