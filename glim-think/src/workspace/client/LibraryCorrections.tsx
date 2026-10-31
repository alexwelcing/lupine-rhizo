import React, { useRef, useState } from "react";
import {
  decodePublicResearchActivity, publicActivitySha256, PUBLIC_ACTIVITY_FEED_SCHEMA,
  PUBLIC_ACTIVITY_MAX_BYTES, type PublicResearchActivity,
} from "../researchActivityContracts";

const READ_LIMIT = PUBLIC_ACTIVITY_MAX_BYTES + 1024;
const enc = new TextEncoder();
export interface CorrectionPreview {
  record: PublicResearchActivity; original: PublicResearchActivity;
  body: string; sha256: string; originalSha256: string;
}

function parseCorrection(text: string): PublicResearchActivity {
  if (!text.trim() || enc.encode(text).length > PUBLIC_ACTIVITY_MAX_BYTES) throw new Error("Use one correction of 16 KiB or less.");
  const record = decodePublicResearchActivity(JSON.parse(text));
  if (!record.supersedes || !record.correctionReason || !["completed", "failed"].includes(record.state)) {
    throw new Error("Choose a reviewed clarification of a completed or failed record.");
  }
  // This form publishes an attributed activity successor, not a fabricated
  // discovery evidence sidecar under the new correction identity.
  if (record.hashes.some(hash => hash.label === "Public evidence" || hash.label === "Source availability notice")) {
    throw new Error("A clarification must label inherited evidence as original evidence.");
  }
  return record;
}

export async function readCorrectionFile(file: Pick<File, "size" | "text">): Promise<string> {
  if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > PUBLIC_ACTIVITY_MAX_BYTES) throw new Error("Choose a nonempty JSON file of 16 KiB or less.");
  const text = await file.text();
  if (enc.encode(text).length > PUBLIC_ACTIVITY_MAX_BYTES) throw new Error("Choose a JSON file of 16 KiB or less.");
  return text;
}

/** Fixed same-origin requests only. There is no token input or automatic retry. */
async function requestJson(path: string, init: RequestInit = {}): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15_000);
  try {
    const response = await fetch(path, { ...init, credentials: "same-origin", cache: "no-store", redirect: "error", signal: controller.signal });
    if (!response.ok) throw new Error(response.status === 403 ? "Operator Access is required." : "The record could not be confirmed.");
    if (Number(response.headers.get("content-length")) > READ_LIMIT || !response.body) throw new Error("Response exceeds the review limit.");
    const reader = response.body.getReader(); const chunks: Uint8Array[] = []; let size = 0;
    try {
      for (;;) {
        const { done, value } = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > READ_LIMIT) { await reader.cancel(); throw new Error("Response exceeds the review limit."); }
        chunks.push(value);
      }
    } finally { reader.releaseLock(); }
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } finally { clearTimeout(timer); }
}

async function readRecord(id: string): Promise<PublicResearchActivity> {
  const raw = await requestJson(`/research/activity/${encodeURIComponent(id)}`);
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Invalid public record.");
  const value = raw as Record<string, unknown>;
  if (Object.keys(value).sort().join() !== "items,schema,truncated" || value.schema !== PUBLIC_ACTIVITY_FEED_SCHEMA || value.truncated !== false || !Array.isArray(value.items) || value.items.length !== 1) throw new Error("Invalid public record.");
  const record = decodePublicResearchActivity(value.items[0]);
  if (record.id !== id) throw new Error("Original record identity differs.");
  return record;
}

function assertClarification(record: PublicResearchActivity, original: PublicResearchActivity) {
  if (record.supersedes !== original.id || record.id === original.id || record.activityId !== original.activityId ||
      record.evidenceKind !== original.evidenceKind || record.state !== original.state ||
      record.observedAt !== original.observedAt || record.reviewedAt <= original.reviewedAt) {
    throw new Error("The clarification must preserve the original activity, observation and terminal outcome, with a later review.");
  }
}

/** Parse locally before fetching only the exact public predecessor. */
export async function previewCorrection(text: string): Promise<CorrectionPreview> {
  const record = parseCorrection(text); const original = await readRecord(record.supersedes!);
  assertClarification(record, original);
  const body = JSON.stringify(record);
  return { record, original, body, sha256: await publicActivitySha256(body), originalSha256: await publicActivitySha256(JSON.stringify(original)) };
}

/** Acknowledgement alone is insufficient: read back both immutable records. */
export async function verifyCorrection(preview: CorrectionPreview): Promise<void> {
  const frozen = structuredClone(preview);
  const saved = await readRecord(frozen.record.id);
  if (JSON.stringify(saved) !== frozen.body) throw new Error("Published correction differs from the reviewed bytes.");
  const original = await readRecord(frozen.original.id);
  if (await publicActivitySha256(JSON.stringify(original)) !== frozen.originalSha256) throw new Error("Original record differs from the preview.");
}

export async function publishCorrection(preview: CorrectionPreview): Promise<void> {
  // Snapshot before awaiting so caller mutation cannot change published bytes
  // or the identities checked by the readback.
  const frozen = structuredClone(preview); const record = parseCorrection(frozen.body);
  assertClarification(record, frozen.original);
  if (JSON.stringify(record) !== frozen.body || JSON.stringify(record) !== JSON.stringify(frozen.record) ||
      await publicActivitySha256(frozen.body) !== frozen.sha256 ||
      await publicActivitySha256(JSON.stringify(frozen.original)) !== frozen.originalSha256) throw new Error("Preview changed. Review the correction again.");
  const ack = await requestJson("/workspace/research-activity/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: frozen.body });
  if (!ack || typeof ack !== "object" || Array.isArray(ack)) throw new Error("Publication acknowledgement differs.");
  const value = ack as Record<string, unknown>;
  if (Object.keys(value).sort().join() !== "activityId,duplicate,id,state" || value.id !== record.id || value.activityId !== record.activityId || value.state !== record.state || typeof value.duplicate !== "boolean") throw new Error("Publication acknowledgement differs.");
  await verifyCorrection(frozen);
}

export function CorrectionReview({ preview }: { preview: CorrectionPreview }) {
  const { record, original } = preview;
  return <section className="research-import-preview" aria-label="Public correction preview">
    <h2>{record.title}</h2><p>This appends a public clarification to the Library. The original record and its evidence remain available.</p>
    <dl className="correction-identities"><dt>Original record</dt><dd><a href={`/research/activity/${original.id}`} target="_blank" rel="noopener noreferrer">{original.id}</a></dd>
      <dt>New correction</dt><dd><code>{record.id}</code></dd><dt>Activity</dt><dd><code>{record.activityId}</code></dd>
      <dt>Preserved outcome</dt><dd>{record.state}</dd><dt>Observed</dt><dd><time dateTime={record.observedAt}>{record.observedAt}</time></dd>
      <dt>Reviewed</dt><dd><time dateTime={record.reviewedAt}>{record.reviewedAt}</time></dd><dt>Verification</dt><dd>{record.verification}</dd></dl>
    <h3>Review attribution and reason</h3><p>{record.correctionReason}</p>
    <div className="correction-comparison"><section><h3>Original summary</h3><p>{original.summary}</p></section><section><h3>Clarified summary</h3><p>{record.summary}</p></section></div>
    <h3>Findings</h3><ul>{record.findings.map((text, i) => <li key={i}>{text}</li>)}</ul>
    <h3>Limits of the clarification</h3><ul>{record.limitations.map((text, i) => <li key={i}>{text}</li>)}</ul>
    <h3>Next step</h3><p>{record.nextStep}</p>
    <details><summary>All proposed public fields and fingerprints</summary><p>Original record: <code>{preview.originalSha256}</code></p><p>Correction: <code>{preview.sha256}</code></p><pre>{JSON.stringify(record, null, 2)}</pre></details>
  </section>;
}

export function LibraryCorrections() {
  const [text, setText] = useState(""); const [preview, setPreview] = useState<CorrectionPreview | null>(null);
  const [submitted, setSubmitted] = useState<CorrectionPreview | null>(null); const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const revision = useRef(0); const operation = useRef(false); const fileInput = useRef<HTMLInputElement | null>(null);
  function reset(next: string) { revision.current++; setText(next); setPreview(null); setSubmitted(null); setConfirmed(false); setError(""); setNotice(""); }
  async function choose(file: File) {
    if (operation.current) return; operation.current = true;
    reset(""); const current = revision.current; setBusy(true);
    try { const value = await readCorrectionFile(file); if (current === revision.current) setText(value); }
    catch { setError("Choose one reviewed public correction JSON file of 16 KiB or less."); }
    finally { operation.current = false; setBusy(false); if (fileInput.current) fileInput.current.value = ""; }
  }
  async function inspect() {
    if (operation.current) return; operation.current = true;
    const current = ++revision.current; setBusy(true); setPreview(null); setConfirmed(false); setError(""); setNotice("");
    try { const value = await previewCorrection(text); if (current === revision.current) setPreview(value); }
    catch { setError("The correction or original record could not be validated. Check the exported correction and your connection."); }
    finally { operation.current = false; setBusy(false); }
  }
  async function publish() {
    if (!preview || !confirmed || operation.current) return; operation.current = true;
    const value = preview; setBusy(true); setError(""); setNotice(""); setSubmitted(value); setPreview(null); setConfirmed(false);
    try { await publishCorrection(value); setNotice("Published and read back the exact clarification. The original record is unchanged."); }
    catch { setError("Publication is not confirmed. Nothing is retried automatically. Check the saved record below; operator Access or a newer correction may also prevent import."); }
    finally { operation.current = false; setBusy(false); }
  }
  async function check() {
    if (!submitted || operation.current) return; operation.current = true; setBusy(true); setError(""); setNotice("");
    try { await verifyCorrection(submitted); setNotice("Published and read back the exact clarification. The original record is unchanged."); }
    catch { setError("The exact clarification and unchanged original could not be confirmed. Keep this payload and resolve access or existing history before an explicit new submission."); }
    finally { operation.current = false; setBusy(false); }
  }
  return <main className="workspace-main research-main"><header className="research-header"><div><p className="eyebrow">REVIEWED PUBLIC RECORDS</p><h1>Library corrections</h1><p>Clarify a published record while preserving its original evidence and history.</p></div></header>
    <section className="research-feed"><div className="research-import library-correction-form">
      <p>Choose a reviewed correction, compare it with its original, then explicitly publish it. Local review must be attributed in the correction reason; it does not become a hosted agent review or new experiment.</p>
      <label htmlFor="library-correction-file">Choose a correction file</label><input ref={fileInput} id="library-correction-file" className="research-file-input" type="file" accept=".json,application/json" disabled={busy} onChange={event => { const file = event.currentTarget.files?.[0]; if (file) void choose(file); }} />
      <p className="research-file-help">Up to 16 KiB. Selecting a file does not upload it. Preview reads only its existing public original.</p>
      <label htmlFor="library-correction-json">Or paste reviewed correction JSON</label><textarea id="library-correction-json" rows={6} maxLength={PUBLIC_ACTIVITY_MAX_BYTES} spellCheck={false} value={text} disabled={busy} onChange={event => reset(event.target.value)} />
      {!submitted && <div className="research-import-actions"><button disabled={busy || !text.trim()} onClick={() => void inspect()}>{busy ? "Checking…" : "Preview correction"}</button></div>}
      {preview && <><CorrectionReview preview={preview} /><label className="correction-confirm"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />I have reviewed every public field, its attribution and the preserved original.</label>
        <button disabled={busy || !confirmed} onClick={() => void publish()}>Publish clarification to Library</button></>}
      {submitted && <div className="research-import-preview"><p>Submitted identity: <code>{submitted.record.id}</code></p><button disabled={busy} onClick={() => void check()}>Check published record</button><p><a href={`https://library.lupine.science/#/activity/${submitted.record.id}`} target="_blank" rel="noopener noreferrer">Open this clarification in Library ↗</a></p></div>}
      {error && <p role="alert" className="research-import-error">{error}</p>}{notice && <p role="status">{notice}</p>}
    </div></section></main>;
}
