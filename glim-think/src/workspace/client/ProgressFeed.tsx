import React, { useEffect, useRef, useState } from "react";
import { safeEvidenceHref } from "../contracts";
import { progressClipSchema, type ProgressClip } from "../progressContracts";

export function nextStepDiscussion(clip: ProgressClip): { title: string; prompt: string } {
  return { title: `Next: ${clip.nextStep.title}`.slice(0, 80), prompt: [
    `Let's discuss the proposed next step from this saved research briefing: ${clip.title}`,
    `Briefing summary: ${clip.summary.slice(0, 800)}`,
    `Proposed next step (not started): ${clip.nextStep.title}\nWhy: ${clip.nextStep.why.slice(0, 800)}\nSuccess criterion: ${clip.nextStep.successCriterion.slice(0, 800)}`,
    `Initial plan:\n${clip.nextStep.steps.slice(0, 5).map((item) => `- ${item.slice(0, 400)}`).join("\n")}`,
    `Current limitations:\n${clip.limitations.slice(0, 4).map((item) => `- ${item.slice(0, 400)}`).join("\n")}`,
    `Source reports:\n${clip.sources.map((source) => `- [${source.id}] ${source.title} (report dated ${source.reportDate}): ${source.url}`).join("\n")}`,
    "This is a bounded excerpt from the saved briefing; consult its receipts for full context. Help me refine the plan and identify the evidence still needed. This is analysis of existing reports; no new experiment has been run. Do not start or dispatch work.",
  ].join("\n\n") };
}

/** Date-only source reports must not shift to yesterday in a western timezone. */
export function progressDate(value: string, includeTime = false): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "Date not recorded";
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric",
    ...(dateOnly ? { timeZone: "UTC" } : includeTime ? { hour: "numeric", minute: "2-digit", timeZoneName: "short" } : {}),
  }).format(date);
}

function sourceLink(value: string): string | null {
  const safe = safeEvidenceHref(value);
  return safe?.startsWith("https://") ? safe : null;
}

function SourceReceipt({ source }: { source: ProgressClip["sources"][number] }) {
  const href = sourceLink(source.url);
  return <article className="source-receipt">
    <header><div><span className="receipt-id">{source.id}</span><h4>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.title} ↗</a> : source.title}</h4></div>
      <span>Report dated <time dateTime={source.reportDate}>{progressDate(source.reportDate)}</time></span></header>
    <blockquote>{source.excerpt}</blockquote>
    <details className="receipt-fingerprint"><summary>Content fingerprint</summary><code>{source.sha256}</code></details>
  </article>;
}

export function ProgressCard({ clip, index = 0, onDiscuss }: { clip: ProgressClip; index?: number; onDiscuss?: (clip: ProgressClip) => void }) {
  const sourceById = new Map(clip.sources.map((source) => [source.id, source]));
  const reportDates = [...new Set(clip.sources.map((source) => source.reportDate))].sort();
  const draft = clip.runs.filter((run) => run.role === "draft");
  const reviewers = clip.runs.filter((run) => run.role === "review");
  const [receiptsOpen, setReceiptsOpen] = useState(false);
  function revealSources() {
    setReceiptsOpen(true);
    requestAnimationFrame(() => document.getElementById(`receipts-${clip.id}`)?.scrollIntoView({ block: "nearest" }));
  }

  return <article className="progress-card" aria-labelledby={`clip-title-${clip.id}`}>
    <div className="clip-topline"><span className="clip-number">{String(index + 1).padStart(2, "0")}</span><span>RESEARCH BRIEFING</span><span className="clip-status">Source-checked analysis</span></div>
    <h2 id={`clip-title-${clip.id}`}>{clip.title}</h2>
    <p className="clip-summary">{clip.summary}</p>
    <div className="clip-dates">
      <span>Source reports: {reportDates.map((date, i) => <React.Fragment key={date}>{i > 0 ? " · " : ""}<time dateTime={date}>{progressDate(date)}</time></React.Fragment>)}</span>
      <span>Analysis generated: <time dateTime={clip.createdAt}>{progressDate(clip.createdAt, true)}</time></span>
    </div>
    <section className="clip-findings" aria-label="Findings from saved reports">
      <h3>What the reports show</h3>
      <ul>{clip.findings.map((finding, i) => <li key={i}><span>{finding.text}</span><span className="finding-citations">{finding.sourceIds.map((id) => {
        const source = sourceById.get(id);
        return source ? <button key={id} onClick={revealSources} title={`Show source: ${source.title}`} aria-controls={`receipts-${clip.id}`}>[{id}]</button> : <span key={id}>[{id}]</span>;
      })}</span></li>)}</ul>
    </section>
    <section className="clip-next-step" aria-label="Proposed next step">
      <div className="next-step-label"><h3>Next step</h3><span>Proposed · not started</span></div>
      <h4>{clip.nextStep.title}</h4><p>{clip.nextStep.why}</p>
      <details className="step-plan"><summary>See the plan <span>{clip.nextStep.steps.length} steps</span></summary><ol>{clip.nextStep.steps.map((step, i) => <li key={i}>{step}</li>)}</ol></details>
      <p className="success-criterion"><strong>Success looks like</strong>{clip.nextStep.successCriterion}</p>
      {onDiscuss && <div className="discuss-next-step"><button onClick={() => onDiscuss(clip)}>Discuss this next step <span aria-hidden="true">↗</span></button><span>Opens a draft. You decide when to send.</span></div>}
    </section>
    <section className="clip-limitations" aria-label="Limitations"><h3>What remains uncertain</h3><ul>{clip.limitations.map((limitation, i) => <li key={i}>{limitation}</li>)}</ul></section>
    <details className="clip-receipts" id={`receipts-${clip.id}`} open={receiptsOpen} onToggle={(event) => setReceiptsOpen(event.currentTarget.open)}>
      <summary>Source receipts <span>{clip.sources.length} reports · dates, excerpts &amp; provenance</span></summary>
      <div className="receipt-list">{clip.sources.map((source) => <SourceReceipt source={source} key={source.id} />)}</div>
      <div className="review-notes"><h4>Source review notes</h4><ul>{clip.review.notes.map((note, i) => <li key={i}>{note}</li>)}</ul></div>
      <p className="source-commit">Source revision <code>{clip.sourceCommit}</code></p>
    </details>
    <footer className="clip-attribution">
      <div><span>Draft</span><strong>{draft.map((run) => run.modelId).join(" · ") || "Not recorded"}</strong></div>
      <div><span>Review</span><strong>{reviewers.map((run) => run.modelId).join(" · ") || "Not recorded"}</strong></div>
      <details className="run-receipts"><summary>Model run receipts</summary><dl>{clip.runs.map((run, i) => <React.Fragment key={`${run.requestId}-${i}`}>
        <dt>{run.role === "draft" ? "Draft" : "Review"} · {run.modelId}</dt><dd><time dateTime={run.startedAt}>{progressDate(run.startedAt, true)}</time> · {(run.durationMs / 1000).toFixed(1)} s · {run.inputTokens.toLocaleString()} input / {run.outputTokens.toLocaleString()} output tokens<br /><span>Request </span><code>{run.requestId}</code></dd>
      </React.Fragment>)}</dl></details>
    </footer>
    <p className="clip-boundary">Analysis of existing reports; no new experiment. Private briefing · not published to the Library.</p>
  </article>;
}

type FeedState = { clips: ProgressClip[]; truncated: boolean };
export function decodeProgressFeed(value: unknown): FeedState {
  if (!value || typeof value !== "object" || !("clips" in value) || !Array.isArray(value.clips) || value.clips.length > 100 || !("truncated" in value) || typeof value.truncated !== "boolean") throw new Error("Invalid feed");
  return { clips: value.clips.map((clip) => progressClipSchema.parse(clip)), truncated: value.truncated };
}
export function ProgressFeed({ onDiscuss }: { onDiscuss: (clip: ProgressClip) => void }) {
  const [feed, setFeed] = useState<FeedState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  async function refresh() {
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    setLoading(true); setError("");
    try {
      const response = await fetch("/workspace/progress", { credentials: "same-origin", cache: "no-store", signal: controller.signal });
      if (!response.ok) throw new Error("Feed unavailable");
      const result = decodeProgressFeed(await response.json());
      if (!controller.signal.aborted) setFeed(result);
    } catch {
      if (!controller.signal.aborted) setError("Saved briefings could not load. Check your connection or sign in again, then retry.");
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => { void refresh(); return () => pending.current?.abort(); }, []);

  return <main className="workspace-main progress-main">
    <header className="progress-header"><div><p className="eyebrow">PRIVATE RESEARCH WORKSPACE</p><h1>Progress, with receipts.</h1><p>Short briefings on what the reports show, what remains uncertain, and the next useful step.</p></div>
      <button className="quiet" disabled={loading} onClick={() => void refresh()}>{loading ? "Loading…" : "Refresh briefings"}</button></header>
    <div className="progress-scope"><span className="permission-pill">Report analysis</span><p>Existing evidence, newly considered. These briefings do not represent new experiments or publish anything to the Library.</p></div>
    <section className="progress-feed" aria-label="Saved progress briefings" aria-busy={loading}>
      {error && <div className="feed-error" role="alert"><h2>Progress is temporarily unavailable.</h2><p>{error}</p>{feed && <p>The briefings below are from the last successful load.</p>}<button onClick={() => void refresh()} disabled={loading}>Try again</button></div>}
      {loading && !feed && <div className="feed-placeholder" role="status"><span className="feed-loading-mark" aria-hidden="true">✳</span><h2>Loading saved briefings…</h2><p>Gathering the analysis and its source receipts.</p></div>}
      {!loading && !error && feed?.clips.length === 0 && <div className="feed-placeholder"><span className="feed-loading-mark" aria-hidden="true">✳</span><h2>No saved briefings yet.</h2><p>A briefing will appear here when an analysis of existing reports has been saved. Refresh checks for saved work; it does not run a model or an experiment.</p></div>}
      {feed?.clips.map((clip, index) => <ProgressCard clip={clip} index={index} onDiscuss={onDiscuss} key={clip.id} />)}
      {feed?.truncated && <p className="feed-truncated" role="status">Showing the most recent saved briefings.</p>}
    </section>
  </main>;
}
