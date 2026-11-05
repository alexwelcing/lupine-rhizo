import { afterEach, describe, expect, it, vi } from "vitest";
import React from "react";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { formatVacancyFraction, InspectVacancyReport, readVacancyReportFile, VacancyReportView,
  vacancyDecision, VACANCY_REPORT_MAX_BYTES } from "../VacancyReport";
import { ResearchRuns } from "../ResearchRuns";
import { validateVacancyResult } from "../../vacancyEvidenceContracts";

const fixture = JSON.parse(readFileSync(new URL(
  "../../../../../distill/tests/fixtures/vacancy_uniform_bias.expected.json", import.meta.url), "utf8"));
const protocol = JSON.parse(readFileSync(new URL(
  "../../../../../distill/tests/fixtures/vacancy_calibration.protocol.json", import.meta.url), "utf8"));
const report = () => validateVacancyResult(structuredClone(fixture));
const render = (input: unknown, task?: "within_species_variation" | "formation_energy" | "vacancy_concentration") =>
  renderToStaticMarkup(React.createElement(VacancyReportView, { report: input, task }));
afterEach(() => vi.unstubAllGlobals());

describe("local vacancy report inspection", () => {
  it("renders unavailable cohort identities without manufacturing a digest", () => {
    const input = report(); input.context.reference_protocol = structuredClone(protocol);
    input.context.cohort_sha256 = null;
    input.context.reference_protocol!.reference_calibration!.cohort_sha256 = null;
    const html = render(input);
    expect(html).toContain("Parent cohort identity is unknown");
    expect(html).toContain("Reference calibration cohort identity is unknown");
    expect(html).toContain("<code>Unknown</code>");
    expect(html).toContain("reference match");
  });
  it("shows older reports as unknown and identifies singleton groups", () => {
    const html = render(report());
    expect(html).toContain("Reference protocol is unknown");
    expect(html).toContain("Species with only one supplied site: Ni");
    const input = report();
    input.context.complete_cohort = false; input.rows = 2; input.groups[0].sites = 1;
    expect(render(input, "within_species_variation")).toContain("zero centered error is uninformative");
  });
  it("renders distinct calibration and evaluation identities with declared weights", () => {
    const input = report(); input.context.reference_protocol = structuredClone(protocol);
    const html = render(input);
    for (const text of ["Calibration and evaluation cohorts", "Cr: 2, Ni: 1",
      "reference match", "prediction match", "declared shared, not independently verified",
      "2/3", "1/3", "d".repeat(64), "e".repeat(64), "f".repeat(64)])
      expect(html).toContain(text);
    expect(html).toContain("not a physical reservoir");
  });
  it("recomputes a weight mismatch despite a producer claiming no issues", () => {
    const input = report(); input.context.reference_protocol = structuredClone(protocol);
    for (const s of input.context.reference_protocol!.reference_calibration!.species)
      s.weight = { numerator: "1", denominator: "2" };
    input.issues = []; input.task_assessment = "descriptive_components_only";
    const html = render(input);
    expect(html).toContain("Reference calibration weights differ from parent composition");
    expect(html).toContain("reference mismatch");
    expect(html).toContain("prediction match");
  });

  it("opens one report locally without a provider run, network request or persistence", async () => {
    const fetcher = vi.fn(); const save = vi.fn();
    vi.stubGlobal("fetch", fetcher); vi.stubGlobal("localStorage", { setItem: save });
    const raw = JSON.stringify(fixture);
    const loaded = await readVacancyReportFile({ size: new TextEncoder().encode(raw).length, text: async () => raw });
    expect(loaded.context.prediction_id).toBe("synthetic-shift");
    expect(loaded.components.full_mse_ev2).toEqual({ numerator: "1", denominator: "100" });
    expect(fetcher).not.toHaveBeenCalled(); expect(save).not.toHaveBeenCalled();
  });
  it("rejects empty, oversized and falsely sized UTF-8 files", async () => {
    const text = vi.fn().mockResolvedValue("{}");
    for (const size of [0, -1, Number.NaN, Number.POSITIVE_INFINITY, 1.5, VACANCY_REPORT_MAX_BYTES + 1])
      await expect(readVacancyReportFile({ size, text })).rejects.toThrow();
    expect(text).not.toHaveBeenCalled();
    await expect(readVacancyReportFile({ size: 2, text: async () => "é".repeat(VACANCY_REPORT_MAX_BYTES / 2 + 1) })).rejects.toThrow("exceeds");
  });
  it("rejects malformed or inconsistent reports instead of displaying their claimed status", async () => {
    for (const raw of ["not JSON", "{}", JSON.stringify({ ...fixture, components: {
      ...fixture.components, full_mse_ev2: { numerator: "0", denominator: "1" } } })])
      await expect(readVacancyReportFile({ size: raw.length, text: async () => raw })).rejects.toThrow();
    const forged = report(); forged.scientific_validation = "validated" as never;
    expect(() => render(forged)).toThrow();
  });
  it("shows the hidden uniform bias alongside the zero centered score", () => {
    const input = report(); input.task_assessment = "descriptive_components_only";
    const html = render(input);
    for (const text of ["SYNTHETIC INPUT", "cannot support absolute formation-energy accuracy",
      "Full error", "Within-species variation", "Overall bias squared", "Species-mean imbalance",
      "Signed mean error: 0.1 eV", "0.01", "Mean squared errors (eV²)", "original input was not executed here",
      "Declared complete cohort", "Source membership has not been checked", "weighted by their site counts"])
      expect(html).toContain(text);
    expect(html).toMatch(/Within-species variation<\/th><td>0<\/td>/);
  });
  it("keeps a changed inspection task separate from the immutable report's intended use", () => {
    const input = report(); const before = JSON.stringify(input);
    const html = render(input, "within_species_variation");
    expect(html).not.toContain("This centered score cannot");
    expect(html).toContain("Intended use in the report: Absolute vacancy formation energies");
    expect(html).toContain("Inspecting for: Differences among sites of the same species");
    expect(html).toContain("Physical accuracy remains unverified");
    expect(JSON.stringify(input)).toBe(before);
  });
  it("does not turn a full score into thermodynamic or physical acceptance", () => {
    const input = report(); input.selected_score = "full"; input.selected_mse_ev2 = input.components.full_mse_ev2;
    const html = render(input, "vacancy_concentration");
    expect(html).not.toContain("This centered score cannot");
    expect(html).toContain("Concentrations also require a qualified temperature");
    expect(html).toContain("thermodynamic model");
    expect(html).toContain("Physical accuracy remains unverified");
    expect(vacancyDecision(report(), "vacancy_concentration")).toContain("cannot support a vacancy-concentration claim");
  });
  it("preserves unknown references and the full cohort when viewing a subset", () => {
    const input = report();
    input.context.complete_cohort = false; input.context.cohort_size = 4; input.context.parent_atom_count = 4;
    input.context.reference_definition = "unknown";
    const html = render(input);
    for (const text of ["Partial subset", "4 parent sites", "Unknown reference construction",
      "does not redefine chemical potentials", input.context.cohort_sha256, input.reference_rows_sha256])
      expect(html).toContain(text);
  });
  it("escapes report text and creates no links from declared identifiers", () => {
    const input = report(); input.limitations = ["<script>untrusted</script>"];
    const html = render(input);
    expect(html).toContain("&lt;script&gt;untrusted&lt;/script&gt;");
    expect(html).not.toContain("<script>"); expect(html).not.toContain("<a ");
    expect(html).toContain("not independent verification of the underlying files");
  });
  it("never displays a tiny nonzero error as zero or rounds a repeating fraction", () => {
    for (const [numerator, denominator, expected] of [
      ["1", "100", "0.01"], ["-1", "10", "-0.1"], ["0", "3", "0"], ["1", "3", "1/3"],
      ["1", "100000000000000000", "1/100000000000000000"],
      ["10000000000000000000000000000001", "1", "10000000000000000000000000000001"],
    ]) expect(formatVacancyFraction({ numerator, denominator })).toBe(expected);
  });
  it("makes the inspector available even without any saved runs", () => {
    const html = renderToStaticMarkup(React.createElement(ResearchRuns));
    expect(html).toContain("Inspect a vacancy error report");
    expect(html).toContain("single model can be inspected without a saved run");
    const inspector = renderToStaticMarkup(React.createElement(InspectVacancyReport));
    expect(inspector).toContain('type="file"');
    expect(inspector).toContain('accept=".json,application/json"');
    expect(inspector).toContain("not uploaded, saved or published");
    expect(inspector).not.toContain("<form"); expect(inspector).not.toContain("Import snapshot");
  });
});
