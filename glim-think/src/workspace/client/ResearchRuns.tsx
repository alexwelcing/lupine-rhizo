import React, { useEffect, useRef, useState } from "react";
import { safeEvidenceHref } from "../contracts";
import { decodeResearchRun, researchRunSchema, RESEARCH_RUN_MAX_BYTES, type ResearchRun,
  type ResearchRunStage, type ResearchRunsFeed, type ScientificPacket } from "../researchRunContracts";

const STAGES = ["discovery", "independent_critique", "pi_decision"] as const;
const TITLES = { discovery: "Literature & proposal", independent_critique: "Independent critique", pi_decision: "PI decision" };
const STATUS: Record<string, string> = { completed: "Complete", running: "In progress", stopped: "Stopped",
  not_started: "Not started", pending: "Awaiting completion", blocked: "Blocked", failed: "Failed", timeout: "Timed out",
  output_limit: "Output limit reached", interrupted: "Interrupted", invalid_result: "Result not accepted", policy_violation: "Stopped by restrictions",
  launch_unknown: "Launch unconfirmed", launch_failed: "Launch failed", transport_unknown: "Connection outcome unknown",
  status_unknown: "Status unknown", poll_timeout: "Completion not confirmed" };
const VERDICTS: Record<string, string> = { investigate: "Investigate", revise: "Revise", reject: "Reject",
  insufficient_evidence: "Insufficient evidence", advance_to_preregistration: "Prepare a preregistration" };
type Discovery = Extract<ScientificPacket, { role: "proposer" }>;
type Critique = Extract<ScientificPacket, { role: "critic" }>;
type Decision = Extract<ScientificPacket, { role: "adjudicator" }>;

function recordedDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" }).format(new Date(value));
}
function DateLabel({ value }: { value: string }) { return <time dateTime={value}>{recordedDate(value)}</time>; }

/** Refuse contradictory display data even when a server returns valid field types. */
export function decodeResearchRuns(value: unknown): ResearchRunsFeed {
  if (!value || typeof value !== "object" || !("runs" in value) || !Array.isArray(value.runs) || value.runs.length > 100
      || !("truncated" in value) || typeof value.truncated !== "boolean") throw new Error("Invalid research runs response");
  const runs = value.runs.map(raw => researchRunSchema.parse(raw));
  const ids = new Set<string>();
  for (const run of runs) {
    if (ids.has(run.id)) throw new Error("Duplicate research run");
    ids.add(run.id);
    run.stages.forEach((stage, index) => {
      if (stage.stage !== STAGES[index]) throw new Error("Research stages are out of order");
      if (stage.status === "completed") {
        if (!stage.result || stage.result.role !== stage.role || !stage.receipt || stage.receipt.status !== "completed"
            || stage.receipt.completionUnknown || !stage.receipt.modelExecutionStarted || !stage.receipt.sessionId
            || stage.receipt.jobId !== stage.jobId || !stage.receipt.resultSha256) throw new Error("Unconfirmed stage completion");
      } else if (stage.result) throw new Error("Incomplete stage contains a result");
      if (index && stage.status !== "not_started" && run.stages[index - 1].status !== "completed") throw new Error("Research stages are inconsistent");
    });
    if (run.status === "completed" && run.stages.some(stage => stage.status !== "completed")) throw new Error("Incomplete research run");
  }
  return { runs, truncated: value.truncated };
}

export async function loadResearchRuns(signal?: AbortSignal): Promise<ResearchRunsFeed> {
  const response = await fetch("/workspace/research-runs", { credentials: "same-origin", cache: "no-store", signal });
  if (!response.ok) throw new Error("Research runs unavailable");
  return decodeResearchRuns(await response.json());
}

function Experiment({ value }: { value: Discovery["proposals"][number]["cheap_discriminating_experiment"] }) {
  return <section className="research-experiment"><h4>Proposed discriminating test <span>Not started</span></h4>
    <dl><dt>Design</dt><dd>{value.design}</dd><dt>Baseline</dt><dd>{value.baseline}</dd>
      <dt>Measure</dt><dd>{value.measurement}</dd><dt>Decision rule</dt><dd>{value.decision_rule}</dd></dl>
    <p>Estimated compute: {value.estimated_compute_minutes} minutes. This is a proposal, not a recorded result.</p>
  </section>;
}

function DiscoveryResult({ packet, originalQuestion }: { packet: Discovery; originalQuestion: string }) {
  return <div className="research-packet">{packet.research_question !== originalQuestion && <div className="research-refined-question"><h4>Question after literature review</h4><p>{packet.research_question}</p></div>}
    <p className="research-synthesis">{packet.synthesis}</p>
    {packet.proposals.map(proposal => <section className="research-proposal" key={proposal.id}>
      <p className="research-label">PROPOSAL · {proposal.id}</p><h4>{proposal.hypothesis}</h4>
      <p>{proposal.mechanism}</p><p><strong>Why pursue it</strong> {proposal.priority_reason}</p>
      <div className="research-claim"><strong>What could be new · unverified</strong><p>{proposal.possible_novelty}</p></div>
      <details><summary>Closest prior work & competing explanations</summary>
        {proposal.closest_prior_art.map((prior, index) => <div className="research-prior" key={index}><p className="research-reference">Sources: {prior.source_ids.join(", ")}</p><p><strong>Overlap</strong> {prior.overlap}</p><p><strong>Possible difference</strong> {prior.difference}</p></div>)}
        <h4>Competing explanations</h4><ul>{proposal.competing_explanations.map((text, index) => <li key={index}>{text}</li>)}</ul>
      </details>
      <p className="research-falsifier"><strong>What would falsify it</strong>{proposal.falsifier}</p>
      <Experiment value={proposal.cheap_discriminating_experiment} />
    </section>)}
    <details className="research-critic-questions"><summary>Questions sent to the independent reviewer</summary><ul>{packet.independent_critique.questions_for_critic.map((text, index) => <li key={index}>{text}</li>)}</ul></details>
  </div>;
}

function CritiqueResult({ packet }: { packet: Critique }) {
  return <div className="research-packet"><p className="research-verdict">Reviewer recommendation: <strong>{VERDICTS[packet.verdict]}</strong></p>
    {packet.critiques.map(critique => <section className="research-critique" key={critique.proposal_id}>
      <h4>Review of {critique.proposal_id}</h4><p><strong>Prior work overlap</strong> {critique.prior_art_overlap}</p>
      <h4>Confounds to resolve</h4><ul>{critique.confounds.map((text, index) => <li key={index}>{text}</li>)}</ul>
      <p><strong>Does the test distinguish the explanations?</strong> {critique.discriminating_experiment_assessment}</p>
      {critique.required_changes.length > 0 && <><h4>Required changes</h4><ul>{critique.required_changes.map((text, index) => <li key={index}>{text}</li>)}</ul></>}
    </section>)}
    <p><strong>Strongest alternative</strong> {packet.strongest_alternative}</p><p><strong>Reviewer’s next step</strong> {packet.next_step}</p>
    <details><summary>Reviewer’s source checks</summary><p>The reviewer assessed the supplied evidence without browsing independently.</p>
      <ul>{packet.source_checks.map((check, index) => <li key={index}><strong>{check.source_id} · {check.status === "provided_only" ? "Supplied evidence only" : check.status === "unverified" ? "Unverified" : check.status}</strong><p>{check.reason}</p></li>)}</ul>
    </details>
  </div>;
}

function DecisionResult({ packet }: { packet: Decision }) {
  return <div className="research-packet"><div className="research-decision"><p className="research-label">PI RECOMMENDATION</p><h4>{VERDICTS[packet.recommendation]}</h4><p>{packet.reason}</p></div>
    <h4>Hypothesis after review</h4><p>{packet.revised_hypothesis}</p>
    <details open><summary>How the critique changed the decision</summary>{packet.response_to_critique.map((response, index) => <div className="research-response" key={index}>
      <p><strong>Critique</strong> {response.critique_point}</p><p><strong>Response</strong> {response.response}</p><p><strong>Change</strong> {response.change}</p>
    </div>)}</details>
    <p><strong>Boundary with prior work</strong> {packet.closest_prior_art_boundary}</p><p><strong>Competing explanation</strong> {packet.competing_explanation}</p>
    <p className="research-falsifier"><strong>What would falsify it</strong>{packet.falsifier}</p>
    <Experiment value={packet.cheap_discriminating_experiment} />
  </div>;
}

function StageReceipt({ stage }: { stage: ResearchRunStage }) {
  if (!stage.jobId) return null;
  const receipt = stage.receipt;
  return <details className="research-stage-receipt"><summary>Run receipt</summary><dl><dt>Job</dt><dd><code>{stage.jobId}</code></dd>
    <dt>Provider / device</dt><dd>{stage.provider === "codex" ? "Codex" : "Claude"} · {stage.machineId ?? "Not recorded"}</dd>
    <dt>Model</dt><dd>{receipt?.model ?? "Not reported by the provider"}</dd>
    {receipt?.startedAt && <><dt>Started</dt><dd><DateLabel value={receipt.startedAt} /></dd></>}
    {receipt?.finishedAt && <><dt>Finished</dt><dd><DateLabel value={receipt.finishedAt} /></dd></>}
    {receipt?.sessionId && <><dt>Session</dt><dd><code>{receipt.sessionId}</code></dd></>}
    {receipt?.resultSha256 && <><dt>Result fingerprint</dt><dd><code>{receipt.resultSha256}</code></dd></>}
    <dt>Automatic retry</dt><dd>Off</dd>
  </dl></details>;
}

export function ResearchRunCard({ run }: { run: ResearchRun }) {
  const discovery = run.stages[0].status === "completed" && run.stages[0].result?.role === "proposer" ? run.stages[0].result : null;
  const completed = run.stages.filter(stage => stage.status === "completed").length;
  return <article className="research-run" aria-labelledby={`research-title-${run.id}`}>
    <header><div className="research-topline"><span>RESEARCH RUN</span><span className={`research-status ${run.status}`}>{STATUS[run.status]}</span></div>
      <h2 id={`research-title-${run.id}`}>{run.question}</h2>
      <p className="research-run-meta">Started <DateLabel value={run.startedAt} /> · {completed} of 3 stages complete</p>
    </header>
    <ol className="research-stage-list" aria-label="Research stages">{run.stages.map((stage, index) => <li key={stage.stage} className={`research-stage-${stage.status}`}>
      <span className="research-stage-number" aria-hidden="true">{stage.status === "completed" ? "✓" : index + 1}</span><div><strong><a href={`#research-stage-${run.id}-${stage.stage}`}>{TITLES[stage.stage]}</a></strong><span>{STATUS[stage.status] ?? "Status unknown"}</span></div>
    </li>)}</ol>
    {run.error && <div className="research-run-error" role="status"><strong>This run stopped before completion.</strong><p>{run.error}</p></div>}
    <div className="research-stage-results">{run.stages.map(stage => <section className="research-stage-result" key={stage.stage} id={`research-stage-${run.id}-${stage.stage}`} aria-label={TITLES[stage.stage]}>
      <header><h3>{TITLES[stage.stage]}</h3><span className={`research-status ${stage.status}`}>{STATUS[stage.status] ?? "Status unknown"}</span></header>
      {stage.status === "completed" && stage.result ? <>
        {stage.result.role === "proposer" ? <DiscoveryResult packet={stage.result} originalQuestion={run.question} /> : stage.result.role === "critic" ? <CritiqueResult packet={stage.result} /> : <DecisionResult packet={stage.result} />}
      </> : <div className="research-unfinished"><p>{stage.status === "not_started" ? "This stage has not started." : stage.status === "pending" ? "No completed response has been recorded yet." : "No accepted response is available for this stage."}</p>
        {stage.receipt?.completionUnknown && <p><strong>Completion is unknown.</strong> A timeout or lost connection does not confirm a finished review.</p>}
        {stage.stage === "independent_critique" && <p>The proposal has not received a completed independent critique in this run.</p>}
        {stage.stage === "pi_decision" && <p>No final PI decision has been recorded.</p>}
      </div>}
      <StageReceipt stage={stage} />
    </section>)}</div>
    {discovery && <section className="research-sources" aria-label="Research sources"><h3>Sources considered <span>{discovery.sources.length}</span></h3>
      {discovery.sources.map(source => {
        const safe = safeEvidenceHref(source.url);
        const href = safe?.startsWith("https://") && !new URL(safe).username && !new URL(safe).password ? safe : null;
        return <article key={source.id}><p className="research-label">{source.id} · {source.year} · {source.publication_kind.replaceAll("_", " ")}</p>
          <h4>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.title} ↗</a> : source.title}</h4>
          {!href && <p className="research-reference">Provided research context · no external link</p>}
          <p><strong>Supports</strong> {source.supports}</p><p><strong>Limitations</strong> {source.limitations}</p>
        </article>;
      })}
    </section>}
    <footer className="research-run-footer"><p>Novelty remains unverified. Experiments are not started. Library publication is on hold.</p>
      <details><summary>Snapshot details</summary><p>Run <code>{run.id}</code></p><p>Captured <DateLabel value={run.capturedAt} />{run.finishedAt && <> · Finished <DateLabel value={run.finishedAt} /></>}</p></details>
    </footer>
  </article>;
}

export async function previewResearchImport(text: string): Promise<ResearchRun> {
  if (new TextEncoder().encode(text).length > RESEARCH_RUN_MAX_BYTES) throw new Error("Snapshot is too large");
  return decodeResearchRun(JSON.parse(text));
}

/** A selected file is read locally; only the explicit import action sends data. */
export async function readResearchSnapshotFile(file: Pick<File, "size" | "text">): Promise<string> {
  if (!Number.isSafeInteger(file.size) || file.size <= 0) throw new RangeError("Choose a nonempty exported JSON snapshot.");
  if (file.size > RESEARCH_RUN_MAX_BYTES) throw new RangeError("This file is too large. Choose an exported snapshot of 192 KiB or less.");
  const text = await file.text();
  if (new TextEncoder().encode(text).length > RESEARCH_RUN_MAX_BYTES) throw new RangeError("This file is too large. Choose an exported snapshot of 192 KiB or less.");
  return text;
}

export async function saveResearchImport(text: string, expected: Pick<ResearchRun, "id" | "status">): Promise<void> {
  const response = await fetch("/workspace/research-runs/import", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: text });
  if (!response.ok) throw new Error("Import failed");
  const saved: unknown = await response.json();
  if (!saved || typeof saved !== "object" || !("id" in saved) || saved.id !== expected.id
      || !("status" in saved) || saved.status !== expected.status || !("duplicate" in saved) || typeof saved.duplicate !== "boolean") throw new Error("Import acknowledgement did not match the snapshot");
}

export function ImportResearchRun({ onImported }: { onImported: () => void }) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<{ text: string; run: ResearchRun } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const revision = useRef(0);
  const fileInput = useRef<HTMLInputElement | null>(null);
  async function chooseFile(file: File) {
    const current = ++revision.current;
    setBusy(true); setError(""); setNotice(""); setPreview(null); setText("");
    try {
      const contents = await readResearchSnapshotFile(file);
      if (revision.current === current) { setText(contents); setNotice(`Loaded ${file.name} locally. Preview the snapshot before importing it.`); }
    } catch (error) {
      if (revision.current === current) setError(error instanceof RangeError ? error.message : "This file could not be read. Choose it again, or paste the exported JSON below.");
    } finally {
      if (revision.current === current) { setBusy(false); if (fileInput.current) fileInput.current.value = ""; }
    }
  }
  async function validate() {
    const current = ++revision.current;
    setBusy(true); setError(""); setNotice(""); setPreview(null);
    try { const run = await previewResearchImport(text); if (revision.current === current) setPreview({ text, run }); }
    catch { if (revision.current === current) setError("This snapshot could not be validated. Use the exported research-run JSON with its original packets and receipts."); }
    finally { if (revision.current === current) setBusy(false); }
  }
  async function save() {
    if (!preview || preview.text !== text) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await saveResearchImport(preview.text, preview.run);
      setNotice(`Saved research run ${preview.run.id}.`); setPreview(null); setText(""); onImported();
    } catch { setError("The snapshot could not be saved. Check access and the run’s existing state, then refresh before trying again."); }
    finally { setBusy(false); }
  }
  return <details className="research-import"><summary>Import a research snapshot</summary><p>Choose the exported JSON file or paste its contents below. Preview checks its receipts before you save it to this private workspace.</p>
    <label htmlFor="research-snapshot-file">Choose a snapshot file</label><input ref={fileInput} id="research-snapshot-file" className="research-file-input" type="file" accept=".json,application/json" disabled={busy}
      aria-describedby="research-file-help" onChange={event => { const file = event.currentTarget.files?.[0]; if (file) void chooseFile(file); }} />
    <p id="research-file-help" className="research-file-help">Up to 192 KiB. The file stays on this device until you select Import snapshot.</p>
    <label htmlFor="research-snapshot">Or paste exported snapshot JSON</label><textarea id="research-snapshot" value={text} disabled={busy} rows={5} spellCheck={false}
      onChange={event => { revision.current += 1; setText(event.target.value); setPreview(null); setError(""); setNotice(""); }} />
    <div className="research-import-actions"><button disabled={busy || !text.trim()} onClick={() => void validate()}>{busy && !preview ? "Checking…" : "Preview snapshot"}</button></div>
    {preview && <section className="research-import-preview" aria-label="Snapshot preview"><h3>{preview.run.question}</h3><p>Run <code>{preview.run.id}</code> · {STATUS[preview.run.status]}</p>
      <ul>{preview.run.stages.map(stage => <li key={stage.stage}>{TITLES[stage.stage]}: {STATUS[stage.status]}</li>)}</ul>
      <p>Saves recorded research only. It does not run agents, start experiments, or publish to the Library.</p><button disabled={busy} onClick={() => void save()}>{busy ? "Importing…" : "Import snapshot"}</button>
    </section>}
    {error && <p role="alert" className="research-import-error">{error}</p>}{notice && <p role="status">{notice}</p>}
  </details>;
}

export function ResearchRuns() {
  const [feed, setFeed] = useState<ResearchRunsFeed | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  async function refresh() {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setLoading(true); setError("");
    try { const result = await loadResearchRuns(controller.signal); if (!controller.signal.aborted) setFeed(result); }
    catch { if (!controller.signal.aborted) setError("Research runs could not load. Check your connection or sign in again, then refresh."); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => { void refresh(); return () => pending.current?.abort(); }, []);
  return <main className="workspace-main research-main"><header className="research-header"><div><p className="eyebrow">PRIVATE RESEARCH WORKSPACE</p><h1>Research runs</h1><p>From published work to a new question, an independent challenge, and a considered next step.</p></div>
    <button className="quiet" disabled={loading} onClick={() => void refresh()}>{loading ? "Loading…" : "Refresh runs"}</button></header>
    <div className="research-scope"><span>Saved run snapshots</span><p>Completion comes from recorded responses. Refresh reads saved work; it does not start an agent.</p></div>
    <section className="research-feed" aria-label="Saved research runs" aria-busy={loading}>
      {error && <div className="feed-error" role="alert"><h2>Research runs are unavailable.</h2><p>{error}</p>{feed && <p>The snapshots below are from the last successful load.</p>}<button disabled={loading} onClick={() => void refresh()}>Try again</button></div>}
      {loading && !feed && <div className="feed-placeholder" role="status"><h2>Loading research runs…</h2><p>Reading saved proposals, reviews, and decisions.</p></div>}
      {!loading && !error && feed?.runs.length === 0 && <div className="feed-placeholder"><h2>No saved research runs yet.</h2><p>A run appears here after its verified snapshot is imported. Existing report analyses remain in Progress.</p></div>}
      {feed?.runs.map(run => <ResearchRunCard run={run} key={run.id} />)}
      {feed?.truncated && <p className="feed-truncated">Showing the most recent saved runs.</p>}
      <ImportResearchRun onImported={() => void refresh()} />
    </section>
  </main>;
}
