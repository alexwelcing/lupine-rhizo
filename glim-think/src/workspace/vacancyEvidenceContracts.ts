import { z } from "zod";

const id = z.string().regex(/^[A-Za-z0-9_.:-]{1,96}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const rational = z.strictObject({
  numerator: z.string().regex(/^(0|-?[1-9][0-9]{0,511})$/),
  denominator: z.string().regex(/^[1-9][0-9]{0,511}$/),
});
export const vacancyTaskSchema = z.enum(["within_species_variation", "formation_energy", "vacancy_concentration"]);

/** Descriptive checker output, never an attestation of its input sources. */
export const vacancyResultSchema = z.strictObject({
  schema: z.literal("lupine.vacancy_reference.result.v1"),
  input_sha256: hash, reference_rows_sha256: hash,
  arithmetic: z.literal("exact_rational_on_supplied_decimal_strings"),
  unit: z.literal("eV_per_vacancy"),
  context: z.strictObject({
    source_id: id, source_sha256: hash, cohort_sha256: hash, parent_id: id,
    parent_atom_count: z.number().int().min(1).max(4096),
    cohort_size: z.number().int().min(1).max(4096),
    complete_cohort: z.boolean(),
    reference_definition: z.enum(["self_consistent_species_average", "external_reservoir", "unknown"]),
    prediction_id: id, prediction_kind: z.enum(["model", "reported", "synthetic"]),
  }),
  rows: z.number().int().min(1).max(4096),
  groups: z.array(z.strictObject({
    species: id, sites: z.number().int().min(1).max(4096),
    mean_error_ev: rational, reference_mean_ev: rational, prediction_mean_ev: rational,
  })).min(1).max(128),
  components: z.strictObject({
    full_mse_ev2: rational, within_species_mse_ev2: rational,
    overall_mean_error_ev: rational, overall_bias_squared_ev2: rational,
    species_mean_imbalance_mse_ev2: rational,
  }),
  selected_score: z.enum(["full", "within_species_centered"]),
  selected_mse_ev2: rational,
  intended_task: vacancyTaskSchema,
  task_assessment: z.enum(["incompatible_score_for_task", "descriptive_components_only", "scope_unresolved"]),
  issues: z.array(z.string().min(1).max(160)).max(16),
  decomposition_identity_exact: z.literal(true),
  reference_species_means_equal_exactly: z.boolean(),
  prediction_species_means_equal_exactly: z.boolean(),
  source_verification: z.literal("not_performed"),
  scientific_validation: z.literal("not_established"),
  limitations: z.array(z.string().min(1).max(240)).min(1).max(16),
});
export type VacancyResult = z.infer<typeof vacancyResultSchema>;
export const vacancyEvidenceSchema = z.strictObject({
  schemaVersion: z.literal(1), comparisonContractSha256: hash,
  task: vacancyTaskSchema,
  results: z.array(z.strictObject({ modelId: z.string().min(1).max(2000), result: vacancyResultSchema })).min(2).max(8),
});

type Q = [bigint, bigint];
function reduced(n: bigint, d: bigint): Q {
  if (n.toString().length > 4096 || d.toString().length > 4096)
    throw new Error("Vacancy arithmetic exceeds intermediate bound");
  let a = n < 0n ? -n : n; let b = d;
  while (b !== 0n) { const next = a % b; a = b; b = next; }
  return [n / a, d / a];
}
const q = (value: { numerator: string; denominator: string }): Q =>
  reduced(BigInt(value.numerator), BigInt(value.denominator));
const add = (a: Q, b: Q): Q => reduced(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
const sub = (a: Q, b: Q): Q => reduced(a[0] * b[1] - b[0] * a[1], a[1] * b[1]);
const mul = (a: Q, b: Q): Q => reduced(a[0] * b[0], a[1] * b[1]);
const eq = (a: Q, b: Q): boolean => a[0] * b[1] === b[0] * a[1];
const zero = (): Q => [0n, 1n];
function requireIdentity(ok: boolean, message: string): void {
  if (!ok) throw new Error("Invalid vacancy evidence: " + message);
}

/** Verifies bounded declared arithmetic; it does not read or execute the input artifact. */
export function validateVacancyResult(input: unknown): VacancyResult {
  const r = vacancyResultSchema.parse(input);
  const c = r.components;
  requireIdentity(r.context.cohort_size === r.context.parent_atom_count &&
    r.rows <= r.context.cohort_size &&
    (!r.context.complete_cohort || r.rows === r.context.cohort_size), "cohort counts");
  requireIdentity(r.groups.reduce((n, g) => n + g.sites, 0) === r.rows &&
    new Set(r.groups.map(g => g.species)).size === r.groups.length, "species counts");
  for (const value of [c.full_mse_ev2, c.within_species_mse_ev2,
    c.overall_bias_squared_ev2, c.species_mean_imbalance_mse_ev2, r.selected_mse_ev2])
    requireIdentity(q(value)[0] >= 0n, "negative squared error");
  const overall = q(c.overall_mean_error_ev);
  let weightedMean = zero();
  let imbalance = zero();
  for (const g of r.groups) {
    const weight: Q = [BigInt(g.sites), BigInt(r.rows)];
    const error = q(g.mean_error_ev);
    requireIdentity(eq(error, sub(q(g.prediction_mean_ev), q(g.reference_mean_ev))), "species residual");
    weightedMean = add(weightedMean, mul(weight, error));
    const delta = sub(error, overall);
    imbalance = add(imbalance, mul(weight, mul(delta, delta)));
  }
  requireIdentity(eq(weightedMean, overall), "overall mean");
  requireIdentity(eq(imbalance, q(c.species_mean_imbalance_mse_ev2)), "species imbalance");
  requireIdentity(eq(mul(overall, overall), q(c.overall_bias_squared_ev2)), "mean bias squared");
  requireIdentity(eq(q(c.full_mse_ev2), add(add(q(c.within_species_mse_ev2),
    q(c.overall_bias_squared_ev2)), q(c.species_mean_imbalance_mse_ev2))), "decomposition");
  requireIdentity(eq(q(r.selected_mse_ev2), q(r.selected_score === "full"
    ? c.full_mse_ev2 : c.within_species_mse_ev2)), "selected score");
  requireIdentity(r.reference_species_means_equal_exactly ===
    r.groups.every(g => eq(q(g.reference_mean_ev), q(r.groups[0].reference_mean_ev))), "reference means");
  requireIdentity(r.prediction_species_means_equal_exactly ===
    r.groups.every(g => eq(q(g.prediction_mean_ev), q(r.groups[0].prediction_mean_ev))), "prediction means");
  return r;
}

export function assessVacancyEvidence(input: unknown, modelIds: string[]) {
  const evidence = vacancyEvidenceSchema.parse(input);
  requireIdentity(evidence.results.length === modelIds.length &&
    new Set(evidence.results.map(x => x.modelId)).size === modelIds.length &&
    evidence.results.every(x => modelIds.includes(x.modelId)), "model binding");
  const first = evidence.results[0].result;
  const issues: string[] = [];
  const results = evidence.results.map(item => {
    const r = validateVacancyResult(item.result);
    requireIdentity(r.intended_task === evidence.task, "task binding");
    requireIdentity(r.context.prediction_id === item.modelId, "prediction identity");
    requireIdentity(r.reference_rows_sha256 === first.reference_rows_sha256 &&
      r.context.source_id === first.context.source_id &&
      r.context.source_sha256 === first.context.source_sha256 &&
      r.context.cohort_sha256 === first.context.cohort_sha256 &&
      r.context.parent_id === first.context.parent_id &&
      r.context.reference_definition === first.context.reference_definition, "reference binding");
    if (r.selected_score === "within_species_centered" && evidence.task !== "within_species_variation")
      issues.push("Centered-only vacancy score cannot support " + evidence.task + ": " + item.modelId);
    if (r.context.reference_definition === "unknown") issues.push("Unknown vacancy reference: " + item.modelId);
    if (!r.context.complete_cohort) issues.push("Vacancy subset retains incomplete cohort: " + item.modelId);
    if (r.context.prediction_kind !== "model") issues.push("Vacancy input is " + r.context.prediction_kind + ": " + item.modelId);
    return { modelId: item.modelId, result: r };
  });
  if (evidence.task === "vacancy_concentration")
    issues.push("Vacancy concentration requires a separately qualified thermodynamic model");
  return {
    evidence, task: evidence.task, results, issues: [...new Set(issues)],
    arithmeticConsistency: "checked_on_declared_components" as const,
    inputArtifactExecution: "not_verified" as const,
    sourceVerification: "not_performed" as const,
    scientificSupport: "not_asserted" as const,
  };
}
