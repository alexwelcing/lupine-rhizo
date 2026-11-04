import React, { useEffect, useId, useRef, useState } from "react";
import { validateCandidateOrderReport, type CandidateOrderReport, type OrderFraction } from "../candidateOrderContracts";
import { formatExactFraction } from "./formatExactFraction";

export const CANDIDATE_ORDER_MAX_BYTES = 512 * 1024;
export async function readCandidateOrderFile(file: Pick<File, "size" | "text">): Promise<CandidateOrderReport> {
  if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > CANDIDATE_ORDER_MAX_BYTES)
    throw new RangeError("Choose a nonempty candidate-order report of 512 KiB or less.");
  const raw = await file.text();
  if (new TextEncoder().encode(raw).length > CANDIDATE_ORDER_MAX_BYTES)
    throw new RangeError("The candidate-order report exceeds 512 KiB.");
  return validateCandidateOrderReport(JSON.parse(raw));
}

const LIMITS: Record<string, string> = {
  source_and_physical_scope_unverified: "Source authenticity and physical applicability have not been verified.",
  comparability_unknown: "Comparability of these candidates is unknown; arithmetic ordering does not resolve it.",
  reference_or_protocol_unknown: "The reference convention or evaluation protocol is unknown.",
  artifact_identity_unknown: "At least one source, model or candidate-set artifact identity is unknown.",
  fitting_exposure_unknown: "Fitting exposure is unknown.",
  candidate_search_not_exhaustive: "Only the listed candidates were compared; the search is not exhaustive.",
  exhaustiveness_declared_not_verified: "Exhaustiveness is declared by the report and has not been verified.",
  printing_bounds_are_assumptions: "Printing bounds are assumptions, not reported uncertainties or confidence intervals.",
  no_unique_reference_minimum_over_bounds: "The reference bounds do not establish one uniquely lowest candidate.",
  no_unique_prediction_minimum_over_bounds: "The prediction bounds do not establish one uniquely lowest candidate.",
};
function intervalText(g: { lower: OrderFraction; upper: OrderFraction }): string {
  const l = formatExactFraction(g.lower); const u = formatExactFraction(g.upper);
  return l === u ? l : "[" + l + ", " + u + "]";
}

export function CandidateOrderReportView({ report: supplied }: { report: unknown }) {
  const report = validateCandidateOrderReport(supplied);
  const { input, assessment: a } = report; const c = input.context;
  const labels = new Map(input.rows.map(r => [r.candidate_id, r.label]));
  const names = (ids: string[]) => ids.length ? ids.map(id => labels.get(id) + " (" + id + ")").join(", ") : "None";
  const decision = a.choice_relation === "different_unique_minima"
    ? "Reference and prediction select different candidates throughout the supplied bounds."
    : a.choice_relation === "same_unique_minimum"
      ? "Reference and prediction select the same candidate throughout the supplied bounds."
      : "The supplied bounds do not establish a unique choice for both reference and prediction.";
  return <section className="vacancy-report" aria-label="Candidate order inspection">
    <header><p className="research-label">LOCAL REPORT · {c.model_kind.toUpperCase()} INPUT</p><h3>{c.model_id}</h3></header>
    <p className="vacancy-decision"><strong>{decision}</strong></p>
    <p>{c.material}; {c.composition}. Comparing {input.rows.length} listed candidates.</p>
    <p>A global ground state is not established. A constant shift of all predicted energies cannot change their ordering.</p>
    <table><caption>Lowest energies among the listed candidates</caption>
      <thead><tr><th scope="col">Scope</th><th scope="col">Reference</th><th scope="col">Prediction</th></tr></thead>
      <tbody>
        <tr><th scope="row">Can be lowest</th><td>{names(a.reference_minima.possible)}</td><td>{names(a.prediction_minima.possible)}</td></tr>
        <tr><th scope="row">Always among the lowest</th><td>{names(a.reference_minima.guaranteed)}</td><td>{names(a.prediction_minima.guaranteed)}</td></tr>
        <tr><th scope="row">Always uniquely lowest</th><td>{names(a.reference_minima.unique ? [a.reference_minima.unique] : [])}</td>
          <td>{names(a.prediction_minima.unique ? [a.prediction_minima.unique] : [])}</td></tr>
      </tbody>
    </table>
    <p>Every combination of the supplied closed energy intervals is allowed. Touching endpoints permit a tie.
      Shared or correlated errors require a different joint constraint; these bounds do not encode it.</p>
    <ul aria-label="Candidate comparison limits">{a.issues.map(issue => <li key={issue}>{LIMITS[issue]}</li>)}</ul>
    <details open={a.pairs.length <= 16}><summary>Signed energy gaps</summary>
      <p>Each gap is right candidate minus left candidate. Positive means the left candidate is lower.
        Gap error is prediction gap minus reference gap. All values are exact eV bounds.</p>
      <table><thead><tr><th scope="col">Left</th><th scope="col">Right</th><th scope="col">Reference gap</th>
        <th scope="col">Prediction gap</th><th scope="col">Gap error</th><th scope="col">Ordering</th></tr></thead>
        <tbody>{a.pairs.map(pair => <tr key={pair.left + "/" + pair.right}>
          <th scope="row">{labels.get(pair.left)} ({pair.left})</th><td>{labels.get(pair.right)} ({pair.right})</td>
          <td>{intervalText(pair.reference_gap_ev)}</td><td>{intervalText(pair.prediction_gap_ev)}</td><td>{intervalText(pair.gap_error_ev)}</td>
          <td>{pair.agreement === "opposite_strict_order" ? "Opposite strict order" : pair.agreement === "same_strict_order"
            ? "Same strict order" : pair.agreement === "exact_tie_both" ? "Exact tie in both" : "Tie or unresolved order"}</td>
        </tr>)}</tbody>
      </table>
    </details>
    <details><summary>Source, candidate set and supplied bounds</summary>
      <dl><dt>Source</dt><dd>{c.source_id}</dd><dt>Source SHA-256</dt><dd><code>{c.source_sha256 ?? "Unknown"}</code></dd>
        <dt>Model SHA-256</dt><dd><code>{c.model_sha256 ?? "Unknown"}</code></dd><dt>Candidate set</dt><dd>{c.candidate_set_id}</dd>
        <dt>Candidate-set SHA-256</dt><dd><code>{c.candidate_set_sha256 ?? "Unknown"}</code></dd>
        <dt>Reference convention</dt><dd>{c.reference_convention ?? "Unknown"}</dd><dt>Protocol</dt><dd>{c.protocol ?? "Unknown"}</dd>
        <dt>Fitting exposure</dt><dd>{c.fit_exposure ?? "Unknown"}</dd>
        <dt>Declared original-input SHA-256</dt><dd><code>{report.input_sha256}</code></dd></dl>
      <table><caption>Supplied energy bounds (eV)</caption><thead><tr><th scope="col">Candidate</th><th scope="col">Source anchor</th>
        <th scope="col">Reference</th><th scope="col">Prediction</th></tr></thead><tbody>{input.rows.map(row =>
        <tr key={row.candidate_id}><th scope="row">{row.label} ({row.candidate_id})</th><td>{row.anchor}</td>
          <td>[{row.reference.lower}, {row.reference.upper}]</td><td>[{row.prediction.lower}, {row.prediction.upper}]</td></tr>)}</tbody></table>
    </details>
    <p>All gaps and choice sets were recomputed from the included bounds. The source files, original-input byte digest,
      model identity, search completeness and physical accuracy were not verified. This inspection does not approve a simulation.</p>
  </section>;
}

export function InspectCandidateOrderReport() {
  const id = useId(); const revision = useRef(0);
  const [report, setReport] = useState<CandidateOrderReport | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => () => { ++revision.current; }, []);
  async function choose(file: File) {
    const current = ++revision.current; setBusy(true); setReport(null); setError("");
    try {
      const next = await readCandidateOrderFile(file);
      if (current === revision.current) setReport(next);
    } catch (error) {
      if (current === revision.current) setError(error instanceof RangeError ? error.message :
        "This file is not a consistent candidate-order report. Check its format and supplied bounds.");
    } finally { if (current === revision.current) setBusy(false); }
  }
  return <details className="research-import vacancy-inspector"><summary>Inspect a candidate energy ordering</summary>
    <p>Open a candidate-order checker report to inspect energy gaps and possible ties among a fixed list of structures.
      A single model can be inspected without a saved run.</p>
    <label htmlFor={id}>Choose a candidate-order report</label>
    <input id={id} className="research-file-input" type="file" accept=".json,application/json" aria-describedby={id + "-help"}
      onChange={event => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ""; if (file) void choose(file); }} />
    <p id={id + "-help"} className="research-file-help">Up to 512 KiB. The report stays in this page's memory. It is not uploaded, saved or published.</p>
    {busy && <p role="status">Reading and checking the local report…</p>}
    {(report || busy || error) && <button onClick={() => { ++revision.current; setReport(null); setBusy(false); setError(""); }}>Clear report</button>}
    {error && <p role="alert" className="research-import-error">{error}</p>}
    {report && <CandidateOrderReportView report={report} />}
  </details>;
}
