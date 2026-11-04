import { describe, expect, it } from "vitest";
// @ts-expect-error Test-only fixture access, excluded from Worker types.
import { readFileSync } from "node:fs";
import { assessVacancyEvidence, assessVacancyReference, validateVacancyResult } from "../vacancyEvidenceContracts";

const base = (import.meta as ImportMeta & { url: string }).url;
const fixture = JSON.parse(readFileSync(new URL(
  "../../../../atlas-distill/tests/fixtures/vacancy_uniform_bias.expected.json", base), "utf8"));
function evidence() {
  return {
    schemaVersion: 1, comparisonContractSha256: "c".repeat(64), task: "formation_energy",
    results: ["synthetic-shift", "synthetic-second"].map(modelId => {
      const result = structuredClone(fixture); result.context.prediction_id = modelId;
      return { modelId, result };
    }),
  };
}
const protocol = JSON.parse(readFileSync(new URL(
  "../../../../atlas-distill/tests/fixtures/vacancy_calibration.protocol.json", base), "utf8"));
function calibrated() {
  const r = structuredClone(fixture);
  r.context.reference_protocol = structuredClone(protocol);
  return r;
}
const models = ["synthetic-shift", "synthetic-second"];

describe("vacancy error evidence", () => {
  it("keeps older reports explicitly unknown and derives the contrast dimension", () => {
    const old = assessVacancyReference(fixture);
    expect(old.referenceWeights).toBe("unknown");
    expect(old.issues).toContain("Reference protocol is unknown");
    expect(old.withinSpeciesContrasts).toBe(1);
    expect(old.singletonSpecies).toEqual(["Ni"]);
    const singleton = structuredClone(fixture);
    singleton.context.complete_cohort = false; singleton.rows = 2; singleton.groups[0].sites = 1;
    const checked = assessVacancyReference(singleton);
    expect(checked.withinSpeciesContrasts).toBe(0);
    expect(checked.issues.join(" ")).toContain("zero centered error is uninformative");
  });
  it("uses the shared Rust calibration fixture and preserves separate cohort identities", () => {
    const r = calibrated();
    const checked = assessVacancyReference(r);
    expect(checked.referenceWeights).toBe("match");
    expect(checked.predictionWeights).toBe("match");
    expect(checked.issues).toEqual([]);
    expect(checked.protocol!.evaluation_cohort_sha256).not.toBe(checked.protocol!.reference_calibration!.cohort_sha256);
    for (const c of [r.context.reference_protocol.reference_calibration, r.context.reference_protocol.prediction_calibration])
      for (const s of c.species) s.weight = { numerator: "1", denominator: "2" };
    r.issues = []; r.task_assessment = "descriptive_components_only";
    const mismatch = assessVacancyReference(r);
    expect(mismatch.referenceWeights).toBe("mismatch");
    expect(mismatch.predictionWeights).toBe("mismatch");
    expect(mismatch.issues.join(" ")).toContain("elemental energy-zero convention");
    expect(validateVacancyResult(r).components).toEqual(fixture.components);
  });
  it("rejects malformed declared composition, calibration counts, weights and identities", () => {
    for (const mutate of [
      (p: any) => { p.parent_species[0].atoms = 3; },
      (p: any) => { p.parent_species[1].species = "Cr"; },
      (p: any) => { p.reference_calibration.site_count = 3; },
      (p: any) => { p.reference_calibration.species[0].species = "X"; },
      (p: any) => { p.reference_calibration.species[0].weight.numerator = "1"; },
      (p: any) => { p.reference_calibration.species[0].weight.denominator = "0"; },
      (p: any) => { p.reference_calibration.species[0].weight.numerator = "-1"; },
      (p: any) => { p.evaluation_cohort_sha256 = "unknown-hash"; },
      (p: any) => { p.reference_calibration.species[1].species = "Cr"; },
    ]) {
      const r = calibrated(); mutate(r.context.reference_protocol);
      expect(() => validateVacancyResult(r)).toThrow();
    }
  });
  it("binds reference calibration across model arms but permits separately declared prediction calibration", () => {
    const e = evidence();
    for (const item of e.results) item.result.context.reference_protocol = structuredClone(protocol);
    e.results[1].result.context.reference_protocol.prediction_calibration.cohort_sha256 = "1".repeat(64);
    expect(() => assessVacancyEvidence(e, models)).not.toThrow();
    e.results[1].result.context.reference_protocol.reference_calibration.species.reverse();
    expect(() => assessVacancyEvidence(e, models)).not.toThrow();
    e.results[1].result.context.reference_protocol.reference_calibration.cohort_sha256 = "2".repeat(64);
    expect(() => assessVacancyEvidence(e, models)).toThrow(/reference binding/);
  });
  it("preserves unknown metadata and does not apply the self-consistent weight test to an external reservoir", () => {
    const r = calibrated();
    r.context.reference_protocol.parent_species = null;
    r.context.reference_protocol.evaluation_cohort_sha256 = null;
    r.context.reference_protocol.energy_zero_alignment = "unknown";
    expect(assessVacancyReference(r).referenceWeights).toBe("unknown");
    expect(assessVacancyReference(r).issues.join(" ")).toContain("alignment is unknown");
    r.context.reference_definition = "external_reservoir";
    expect(assessVacancyReference(r).referenceWeights).toBe("not_applicable");
  });

  it("reads the same exact result fixture checked by Rust and exposes the centered blind spot", () => {
    const result = validateVacancyResult(fixture);
    expect(result.components.full_mse_ev2).toEqual({ numerator: "1", denominator: "100" });
    expect(result.selected_mse_ev2).toEqual({ numerator: "0", denominator: "1" });
    const assessment = assessVacancyEvidence(evidence(), models);
    expect(assessment.issues).toContain("Centered-only vacancy score cannot support formation_energy: synthetic-shift");
    expect(assessment.scientificSupport).toBe("not_asserted");
    expect(assessment.inputArtifactExecution).toBe("not_verified");
  });
  it("does not trust the producer's task status or an asserted source verification", () => {
    const input = evidence();
    input.results[0].result.task_assessment = "descriptive_components_only";
    expect(assessVacancyEvidence(input, models).issues.join(" ")).toContain("Centered-only");
    input.results[0].result.source_verification = "verified";
    expect(() => assessVacancyEvidence(input, models)).toThrow();
  });
  it("rejects altered arithmetic, weighting, selected score and gauge assertions", () => {
    for (const mutate of [
      (r: any) => { r.components.full_mse_ev2.numerator = "0"; },
      (r: any) => { r.components.overall_bias_squared_ev2.numerator = "0"; },
      (r: any) => { r.groups[0].sites = 1; },
      (r: any) => { r.selected_mse_ev2.numerator = "1"; },
      (r: any) => { r.reference_species_means_equal_exactly = false; },
      (r: any) => { r.groups[0].mean_error_ev.numerator = "2"; },
    ]) {
      const input = structuredClone(fixture); mutate(input);
      expect(() => validateVacancyResult(input)).toThrow();
    }
  });
  it("rejects mismatched model, reference rows, cohort, source and task", () => {
    for (const mutate of [
      (e: any) => { e.results[1].modelId = e.results[0].modelId; },
      (e: any) => { e.results[1].result.context.prediction_id = "other"; },
      (e: any) => { e.results[1].result.reference_rows_sha256 = "d".repeat(64); },
      (e: any) => { e.results[1].result.context.cohort_sha256 = "d".repeat(64); },
      (e: any) => { e.results[1].result.context.source_id = "other"; },
      (e: any) => { e.results[1].result.intended_task = "within_species_variation"; },
    ]) {
      const input = evidence(); mutate(input);
      expect(() => assessVacancyEvidence(input, models)).toThrow();
    }
  });
  it("bounds rational parsing and rejects invalid signs and zero denominators", () => {
    for (const value of [
      { numerator: "NaN", denominator: "1" },
      { numerator: "1", denominator: "0" },
      { numerator: "1".repeat(513), denominator: "1" },
      { numerator: "-1", denominator: "1" },
    ]) {
      const input = structuredClone(fixture); input.components.full_mse_ev2 = value;
      expect(() => validateVacancyResult(input)).toThrow();
    }
  });
  it("keeps a full-score and same-species task descriptive, with synthetic exposure visible", () => {
    const input = evidence(); input.task = "within_species_variation";
    for (const item of input.results) item.result.intended_task = input.task;
    const result = assessVacancyEvidence(input, models);
    expect(result.issues.join(" ")).not.toContain("Centered-only");
    expect(result.issues.join(" ")).toContain("synthetic");
    expect(result.scientificSupport).toBe("not_asserted");
  });
});
