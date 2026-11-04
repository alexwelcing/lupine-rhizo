import React, { useEffect, useId, useRef, useState } from "react";
import { assessVacancyReference, validateVacancyResult, vacancyTaskSchema, type VacancyResult } from "../vacancyEvidenceContracts";

export const VACANCY_REPORT_MAX_BYTES = 512 * 1024;
type VacancyTask = VacancyResult["intended_task"];
type Fraction = VacancyResult["components"]["full_mse_ev2"];
const TASKS: Record<VacancyTask, string> = {
  within_species_variation: "Differences among sites of the same species",
  formation_energy: "Absolute vacancy formation energies",
  vacancy_concentration: "Vacancy concentrations",
};
const REFERENCES = {
  self_consistent_species_average: "Self-consistent species average",
  external_reservoir: "External reservoir",
  unknown: "Unknown reference construction",
};

/** Exact short decimals when possible; a nonzero fraction is never rounded to zero. */
export function formatVacancyFraction(value: Fraction): string {
  let n = BigInt(value.numerator); const d = BigInt(value.denominator);
  if (d <= 0n) throw new Error("Invalid denominator");
  const sign = n < 0n ? "-" : ""; if (n < 0n) n = -n;
  let scale = 1n;
  for (let places = 0; places <= 6; places++, scale *= 10n) {
    if (n * scale % d !== 0n) continue;
    const digits = (n * scale / d).toString().padStart(places + 1, "0");
    return sign + (places ? digits.slice(0, -places) + "." + digits.slice(-places) : digits);
  }
  return value.numerator + "/" + value.denominator;
}

/** File selection is local inspection only: no upload, persistence or inference. */
export async function readVacancyReportFile(file: Pick<File, "size" | "text">): Promise<VacancyResult> {
  if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > VACANCY_REPORT_MAX_BYTES)
    throw new RangeError("Choose a nonempty checker report of 512 KiB or less.");
  const text = await file.text();
  if (new TextEncoder().encode(text).length > VACANCY_REPORT_MAX_BYTES)
    throw new RangeError("The checker report exceeds 512 KiB.");
  return validateVacancyResult(JSON.parse(text));
}

export function vacancyDecision(report: VacancyResult, task: VacancyTask): string {
  vacancyTaskSchema.parse(task);
  if (report.selected_score === "within_species_centered" && task !== "within_species_variation")
    return task === "formation_energy"
      ? "This centered score cannot support absolute formation-energy accuracy."
      : "This centered score cannot support a vacancy-concentration claim.";
  return "The report describes errors in the supplied labels. Physical accuracy remains unverified.";
}

/** Shared inspector for one report; a source audit does not require a saved provider run. */
export function VacancyReportView({ report: input, task: requestedTask }: { report: unknown; task?: VacancyTask }) {
  const report = validateVacancyResult(input);
  const task = requestedTask ?? report.intended_task;
  const reference = assessVacancyReference(report);
  const c = report.components;
  const rows: [string, Fraction][] = [
    ["Full error", c.full_mse_ev2],
    ["Within-species variation", c.within_species_mse_ev2],
    ["Overall bias squared", c.overall_bias_squared_ev2],
    ["Species-mean imbalance", c.species_mean_imbalance_mse_ev2],
  ];
  return <section className="vacancy-report" aria-label="Vacancy report inspection">
    <header><p className="research-label">LOCAL REPORT · {report.context.prediction_kind.toUpperCase()} INPUT</p>
      <h3>{report.context.prediction_id}</h3></header>
    <p className="vacancy-decision"><strong>{vacancyDecision(report, task)}</strong></p>
    <p>Selected score: {report.selected_score === "full" ? "Full error" : "Within-species centered error"}.
      {" "}Intended use in the report: {TASKS[report.intended_task]}.</p>
    <p>Inspecting for: {TASKS[task]}.</p>
    <table><caption>Mean squared errors (eV²)</caption><thead><tr><th scope="col">Component</th><th scope="col">Exact value</th></tr></thead>
      <tbody>{rows.map(([label, value]) => <tr key={label}><th scope="row">{label}</th><td>{formatVacancyFraction(value)}</td></tr>)}</tbody></table>
    <p><strong>Signed mean error: {formatVacancyFraction(c.overall_mean_error_ev)} eV.</strong>
      {" "}Positive means prediction minus reference is positive on average.</p>
    <p>The full error is the sum of the three components below it. Every supplied site has equal weight; species are weighted by their site counts.</p>
    <p>{report.rows} supplied sites across {report.groups.length} species.
      {" "}{report.context.complete_cohort ? "Declared complete cohort" : "Partial subset"}:
      {" "}{report.context.cohort_size} parent sites. Source membership has not been checked.</p>
    {!report.context.complete_cohort && <p>The subset retains the original reference cohort; it does not redefine chemical potentials.</p>}
    <p>Reference: {REFERENCES[report.context.reference_definition]}.</p>
    <p>Within-species contrast dimension: {reference.withinSpeciesContrasts}.
      {reference.singletonSpecies.length > 0 && <> Species with only one supplied site: {reference.singletonSpecies.join(", ")}. Their within-species variation cannot be assessed.</>}</p>
    {reference.issues.length > 0 && <ul aria-label="Reference and sampling limits">{reference.issues.map(issue => <li key={issue}>{issue}.</li>)}</ul>}
    {reference.protocol && <p>Calibration weights against declared parent composition:
      {" "}reference {reference.referenceWeights === "not_applicable" ? "not assessed for this reference construction" : reference.referenceWeights};
      {" "}prediction {reference.predictionWeights === "not_applicable" ? "not assessed for this reference construction" : reference.predictionWeights}.
      {" "}Energy-zero alignment: {reference.protocol.energy_zero_alignment === "declared_shared" ? "declared shared, not independently verified" : "unknown"}.
      {" "}Matching weights checks the stated arithmetic condition, not a physical reservoir.</p>}
    {report.context.reference_definition === "self_consistent_species_average" &&
      (!report.reference_species_means_equal_exactly || !report.prediction_species_means_equal_exactly) &&
      <p>The printed species means are not exactly equal. Their differences remain in the reported components.</p>}
    {task === "vacancy_concentration" && <p>Concentrations also require a qualified temperature, reservoir convention and thermodynamic model; this report does not calculate them.</p>}
    <p>Arithmetic consistency of the report was checked. The original input was not executed here. Source authenticity, model applicability and physical accuracy remain unverified.</p>
    <details><summary>Species means and provenance</summary>
      <table><caption>Species means (eV)</caption><thead><tr><th scope="col">Species</th><th scope="col">Sites</th><th scope="col">Reference</th><th scope="col">Prediction</th><th scope="col">Error</th></tr></thead>
        <tbody>{report.groups.map(group => <tr key={group.species}><th scope="row">{group.species}</th><td>{group.sites}</td>
          <td>{formatVacancyFraction(group.reference_mean_ev)}</td><td>{formatVacancyFraction(group.prediction_mean_ev)}</td><td>{formatVacancyFraction(group.mean_error_ev)}</td></tr>)}</tbody></table>
      <dl><dt>Source</dt><dd>{report.context.source_id}</dd><dt>Parent</dt><dd>{report.context.parent_id}</dd>
        <dt>Source SHA-256</dt><dd><code>{report.context.source_sha256}</code></dd>
        <dt>Reference cohort SHA-256</dt><dd><code>{report.context.cohort_sha256}</code></dd>
        <dt>Reference rows SHA-256</dt><dd><code>{report.reference_rows_sha256}</code></dd>
        <dt>Declared input SHA-256</dt><dd><code>{report.input_sha256}</code></dd></dl>
      {reference.protocol && <section aria-label="Calibration provenance">
        <h4>Calibration and evaluation cohorts</h4>
        <dl><dt>Evaluation cohort SHA-256</dt><dd><code>{reference.protocol.evaluation_cohort_sha256 ?? "Unknown"}</code></dd>
          <dt>Parent composition</dt><dd>{reference.protocol.parent_species?.map(s => s.species + ": " + s.atoms).join(", ") ?? "Unknown"}</dd></dl>
        {(["reference_calibration", "prediction_calibration"] as const).map((key, index) => {
          const calibration = reference.protocol![key];
          return <div key={key}><h5>{index === 0 ? "Reference" : "Prediction"} calibration</h5>
            {calibration ? <><p>{calibration.site_count} declared calibration sites. Cohort SHA-256: <code>{calibration.cohort_sha256}</code></p>
              <table><caption>{index === 0 ? "Reference" : "Prediction"} calibration weights</caption>
                <thead><tr><th scope="col">Species</th><th scope="col">Calibration sites</th><th scope="col">Weight</th></tr></thead>
                <tbody>{calibration.species.map(s => <tr key={s.species}><th scope="row">{s.species}</th><td>{s.sites}</td><td>{formatVacancyFraction(s.weight)}</td></tr>)}</tbody>
              </table></> : <p>Unknown calibration cohort.</p>}
          </div>;
        })}
      </section>}
      <p>These identifiers are declarations in the report, not independent verification of the underlying files.</p>
      <ul>{report.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul>
    </details>
  </section>;
}

export function InspectVacancyReport() {
  const inputId = useId();
  const revision = useRef(0);
  const [report, setReport] = useState<VacancyResult | null>(null);
  const [task, setTask] = useState<VacancyTask>("formation_energy");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => () => { ++revision.current; }, []);
  async function choose(file: File) {
    const current = ++revision.current;
    setBusy(true); setReport(null); setError("");
    try {
      const next = await readVacancyReportFile(file);
      if (current === revision.current) { setReport(next); setTask(next.intended_task); }
    } catch (error) {
      if (current === revision.current) setError(error instanceof RangeError ? error.message :
        "This file is not a consistent vacancy checker report. Check its format and reported arithmetic.");
    } finally { if (current === revision.current) setBusy(false); }
  }
  return <details className="research-import vacancy-inspector"><summary>Inspect a vacancy error report</summary>
    <p>Open a report produced by the vacancy-reference checker to see which error components its score includes. A single model can be inspected without a saved run.</p>
    <label htmlFor={inputId}>Choose a checker report</label>
    <input id={inputId} className="research-file-input" type="file" accept=".json,application/json" aria-describedby={inputId + "-help"}
      onChange={event => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ""; if (file) void choose(file); }} />
    <p id={inputId + "-help"} className="research-file-help">Up to 512 KiB. The report stays in this page's memory. It is not uploaded, saved or published.</p>
    {busy && <p role="status">Reading and checking the local report…</p>}
    {(report || busy || error) && <button onClick={() => { ++revision.current; setReport(null); setBusy(false); setError(""); }}>Clear report</button>}
    {error && <p role="alert" className="research-import-error">{error}</p>}
    {report && <><label htmlFor={inputId + "-task"}>What decision are you considering?</label>
      <select id={inputId + "-task"} value={task} onChange={event => setTask(vacancyTaskSchema.parse(event.currentTarget.value))}>
        {Object.entries(TASKS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <VacancyReportView report={report} task={task} /></>}
  </details>;
}
