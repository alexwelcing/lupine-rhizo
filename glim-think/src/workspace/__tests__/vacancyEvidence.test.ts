import { describe, expect, it } from "vitest";
// @ts-expect-error Test-only fixture access, excluded from Worker types.
import { readFileSync } from "node:fs";
import { assessVacancyEvidence, validateVacancyResult } from "../vacancyEvidenceContracts";

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
const models = ["synthetic-shift", "synthetic-second"];

describe("vacancy error evidence", () => {
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
