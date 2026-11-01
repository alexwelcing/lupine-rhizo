/** Coding execution is attached to the canonical durable agenda, not a second scheduler.
 * A task has one lifetime attempt. Unknown execution never expires into eligibility.
 * The runner DO must persist its dispatch intent before admission and may start only
 * for admission='created'. A replay is metadata reconciliation, never permission to run.
 */
export interface CodingAdmission {
  taskId: string;
  attemptId: string;
  ownerId: string;
  inputSha256: string;
  manifestJson: string;
}

export interface CodingEvidenceReference {
  artifactKey: string;
  sha256: string;
  bytes: number;
}

export interface CodingTerminal extends Omit<CodingAdmission, "manifestJson"> {
  outcome: "succeeded" | "failed" | "unknown";
  receiptJson: string;
  receiptSha256: string;
  executionExitCode: number | null;
  evidence: CodingEvidenceReference | null;
  evidenceVerified: boolean;
  cleanupConfirmed: boolean;
}

export interface CodingAcceptance extends Omit<CodingAdmission, "manifestJson"> {
  terminalReceiptSha256: string;
  decision: "accepted" | "rejected";
  reviewerId: string;
  reason: string;
}

export interface CodingAttemptRecord {
  attemptId: string;
  taskId: string;
  ownerId: string;
  inputSha256: string;
  manifestJson: string;
  admittedAt: string;
  terminal: CodingTerminal | null;
  acceptance: CodingAcceptance | null;
}

export class CodingLedgerError extends Error {
  constructor(public readonly code: "invalid-input" | "conflict" | "unavailable", message: string) {
    super(message);
    this.name = "CodingLedgerError";
  }
}

// Keep migration 0026_coding_attempt_ledger.sql byte-equivalent after trimming.
// The existing intelligence_tasks table is a prerequisite; this does not create
// detached tasks or silently seed a new research agenda.
export const CODING_LEDGER_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS coding_attempts (
    attempt_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE REFERENCES intelligence_tasks(task_id),
    owner_id TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    admitted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  )`,
  `CREATE TABLE IF NOT EXISTS coding_terminal_receipts (
    attempt_id TEXT PRIMARY KEY REFERENCES coding_attempts(attempt_id),
    receipt_sha256 TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('succeeded','failed','unknown')),
    record_json TEXT NOT NULL,
    agenda_result_json TEXT NOT NULL,
    artifact_key TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  )`,
  `CREATE TABLE IF NOT EXISTS coding_acceptance_receipts (
    attempt_id TEXT PRIMARY KEY REFERENCES coding_terminal_receipts(attempt_id),
    decision TEXT NOT NULL CHECK (decision IN ('accepted','rejected')),
    record_json TEXT NOT NULL,
    agenda_result_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  )`,
  ...["coding_attempts", "coding_terminal_receipts", "coding_acceptance_receipts"].flatMap(table => [
    `CREATE TRIGGER IF NOT EXISTS ${table}_immutable_update BEFORE UPDATE ON ${table}
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END`,
    `CREATE TRIGGER IF NOT EXISTS ${table}_immutable_delete BEFORE DELETE ON ${table}
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END`,
  ]),
  `CREATE TRIGGER IF NOT EXISTS coding_agenda_owner_guard BEFORE UPDATE OF claimed_by, status ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts c WHERE c.task_id = OLD.task_id)
    AND (NEW.claimed_by IS NOT (SELECT owner_id FROM coding_attempts WHERE task_id = OLD.task_id)
      OR NEW.status NOT IN ('running','blocked','done')
      OR (NEW.status = 'running' AND EXISTS (SELECT 1 FROM coding_terminal_receipts r
        JOIN coding_attempts c ON c.attempt_id = r.attempt_id WHERE c.task_id = OLD.task_id))
      OR (NEW.status = 'done' AND NOT EXISTS (SELECT 1 FROM coding_acceptance_receipts a
        JOIN coding_attempts c ON c.attempt_id = a.attempt_id
        WHERE c.task_id = OLD.task_id AND a.decision = 'accepted')))
    BEGIN SELECT RAISE(ABORT, 'coding agenda ownership or completion is fenced'); END`,
  `CREATE TRIGGER IF NOT EXISTS coding_agenda_delete_guard BEFORE DELETE ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts WHERE task_id = OLD.task_id)
    BEGIN SELECT RAISE(ABORT, 'coding task history is immutable'); END`,
  `CREATE TRIGGER IF NOT EXISTS coding_agenda_input_guard BEFORE UPDATE OF task_id, domain, payload ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts WHERE task_id = OLD.task_id)
      AND (NEW.task_id IS NOT OLD.task_id OR NEW.domain IS NOT OLD.domain OR NEW.payload IS NOT OLD.payload)
    BEGIN SELECT RAISE(ABORT, 'coding task input is immutable'); END`,
  `CREATE TRIGGER IF NOT EXISTS coding_agenda_evidence_guard BEFORE UPDATE OF status, result, artifact_key, completed_at ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
      WHERE c.task_id = OLD.task_id)
    AND EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
      LEFT JOIN coding_acceptance_receipts a ON a.attempt_id = c.attempt_id WHERE c.task_id = OLD.task_id
      AND (NEW.status IS NOT CASE WHEN a.decision = 'accepted' THEN 'done' ELSE 'blocked' END
        OR NEW.result IS NOT COALESCE(a.agenda_result_json, r.agenda_result_json)
        OR NEW.artifact_key IS NOT r.artifact_key
        OR NEW.completed_at IS NOT CASE WHEN a.decision = 'accepted' THEN a.recorded_at ELSE NULL END))
    BEGIN SELECT RAISE(ABORT, 'coding agenda projection must match immutable evidence'); END`,
] as const;

export async function ensureCodingLedgerSchema(db: D1Database): Promise<void> {
  const results = await db.batch(CODING_LEDGER_SCHEMA.map(sql => db.prepare(sql)));
  if (results.some(result => !result.success)) throw unavailable();
}

function invalid(message: string): never { throw new CodingLedgerError("invalid-input", message); }
function conflict(message: string): never { throw new CodingLedgerError("conflict", message); }
function unavailable(): CodingLedgerError { return new CodingLedgerError("unavailable", "Coding ledger outcome is unavailable; execution must not be replayed"); }
function id(value: unknown, name: string): asserts value is string {
  if (typeof value !== "string" || !/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) invalid(`Invalid ${name}`);
}
function digest(value: unknown, name: string): asserts value is string {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/.test(value)) invalid(`Invalid ${name}`);
}
function identity(input: Omit<CodingAdmission, "manifestJson">): void {
  id(input.taskId, "taskId"); id(input.attemptId, "attemptId"); id(input.ownerId, "ownerId");
  digest(input.inputSha256, "inputSha256");
}
async function checkedJson(text: string, expected: string): Promise<Record<string, unknown>> {
  if (typeof text !== "string" || new TextEncoder().encode(text).length > 65536) invalid("JSON record exceeds 64 KiB");
  let value: unknown;
  try { value = JSON.parse(text); } catch { invalid("Invalid JSON record"); }
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid("JSON record must be an object");
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  const actual = [...new Uint8Array(hash)].map(byte => byte.toString(16).padStart(2, "0")).join("");
  if (actual !== expected) invalid("JSON digest mismatch");
  return value as Record<string, unknown>;
}
function sameIdentity(record: CodingAttemptRecord, input: Omit<CodingAdmission, "manifestJson">): boolean {
  return record.taskId === input.taskId && record.attemptId === input.attemptId
    && record.ownerId === input.ownerId && record.inputSha256 === input.inputSha256;
}

interface StoredAttempt {
  attempt_id: string; task_id: string; owner_id: string; input_sha256: string;
  manifest_json: string; admitted_at: string; terminal_json: string | null; acceptance_json: string | null;
}
export async function getCodingAttempt(db: D1Database, attemptId: string): Promise<CodingAttemptRecord | null> {
  id(attemptId, "attemptId");
  const row = await db.prepare(`SELECT c.*, r.record_json AS terminal_json, a.record_json AS acceptance_json
    FROM coding_attempts c LEFT JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
    LEFT JOIN coding_acceptance_receipts a ON a.attempt_id = c.attempt_id
    WHERE c.attempt_id = ?1`).bind(attemptId).first<StoredAttempt>();
  return row ? {
    attemptId: row.attempt_id, taskId: row.task_id, ownerId: row.owner_id,
    inputSha256: row.input_sha256, manifestJson: row.manifest_json, admittedAt: row.admitted_at,
    terminal: row.terminal_json ? JSON.parse(row.terminal_json) as CodingTerminal : null,
    acceptance: row.acceptance_json ? JSON.parse(row.acceptance_json) as CodingAcceptance : null,
  } : null;
}

export async function admitCodingAttempt(db: D1Database, supplied: CodingAdmission) {
  // Snapshot primitives before the first await. Caller mutation cannot change identity.
  const input: CodingAdmission = { taskId: supplied.taskId, attemptId: supplied.attemptId,
    ownerId: supplied.ownerId, inputSha256: supplied.inputSha256, manifestJson: supplied.manifestJson };
  identity(input);
  const manifest = await checkedJson(input.manifestJson, input.inputSha256);
  if (manifest.taskId !== input.taskId || manifest.attemptId !== input.attemptId
    || manifest.schema !== "lupine.coding-task.v1") invalid("Manifest identity mismatch");
  const results = await db.batch([
    db.prepare(`INSERT OR IGNORE INTO coding_attempts (attempt_id, task_id, owner_id, input_sha256, manifest_json)
      SELECT ?1, task_id, ?3, ?4, ?5 FROM intelligence_tasks
      WHERE task_id = ?2 AND domain = 'coding' AND json_extract(payload, '$.codingInputSha256') = ?4
        AND ((status = 'queued' AND claimed_by IS NULL) OR (status = 'claimed' AND claimed_by = ?3))`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256, input.manifestJson),
    db.prepare(`UPDATE intelligence_tasks SET status = 'running', claimed_by = ?3,
        claimed_at = COALESCE(claimed_at, datetime('now')), updated_at = datetime('now')
      WHERE task_id = ?2 AND status IN ('queued','claimed')
        AND EXISTS (SELECT 1 FROM coding_attempts WHERE attempt_id = ?1 AND task_id = ?2
          AND owner_id = ?3 AND input_sha256 = ?4 AND manifest_json = ?5)`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256, input.manifestJson),
  ]);
  if (results.some(result => !result.success)) throw unavailable();
  const attempt = await getCodingAttempt(db, input.attemptId);
  if (!attempt || !sameIdentity(attempt, input) || attempt.manifestJson !== input.manifestJson)
    conflict("Task is unavailable or attempt identity conflicts");
  return { admission: results[0].meta.changes === 1 ? "created" as const : "replay" as const, attempt };
}

export async function recordCodingTerminal(db: D1Database, supplied: CodingTerminal) {
  const input: CodingTerminal = {
    taskId: supplied.taskId, attemptId: supplied.attemptId, ownerId: supplied.ownerId,
    inputSha256: supplied.inputSha256, outcome: supplied.outcome,
    receiptJson: supplied.receiptJson, receiptSha256: supplied.receiptSha256,
    executionExitCode: supplied.executionExitCode,
    evidence: supplied.evidence ? { artifactKey: supplied.evidence.artifactKey,
      sha256: supplied.evidence.sha256, bytes: supplied.evidence.bytes } : null,
    evidenceVerified: supplied.evidenceVerified, cleanupConfirmed: supplied.cleanupConfirmed,
  };
  identity(input); digest(input.receiptSha256, "receiptSha256");
  if (!["succeeded", "failed", "unknown"].includes(input.outcome)) invalid("Invalid terminal outcome");
  if (input.executionExitCode !== null && (!Number.isSafeInteger(input.executionExitCode)
    || input.executionExitCode < 0 || input.executionExitCode > 255)) invalid("Invalid process exit code");
  if (typeof input.cleanupConfirmed !== "boolean" || typeof input.evidenceVerified !== "boolean") invalid("Invalid terminal gates");
  if (input.evidence) {
    digest(input.evidence.sha256, "evidence.sha256");
    if (typeof input.evidence.artifactKey !== "string" || input.evidence.artifactKey.length > 1024
      || !input.evidence.artifactKey || !Number.isSafeInteger(input.evidence.bytes)
      || input.evidence.bytes < 0) invalid("Invalid evidence reference");
  }
  if (input.evidenceVerified && !input.evidence) invalid("Verified evidence requires an archive reference");
  if (input.outcome === "succeeded" && (input.executionExitCode !== 0 || !input.evidenceVerified
    || !input.evidence || !input.cleanupConfirmed)) invalid("Raw success requires exit zero, verified archive and confirmed cleanup");
  const receipt = await checkedJson(input.receiptJson, input.receiptSha256);
  if (receipt.taskId !== input.taskId || receipt.attemptId !== input.attemptId
    || receipt.inputSha256 !== input.inputSha256) invalid("Receipt identity mismatch");
  const recordJson = JSON.stringify(input);
  const agendaResult = JSON.stringify({ kind: "coding-execution", attemptId: input.attemptId, outcome: input.outcome,
    accepted: false, reason: input.outcome === "unknown" ? "execution-unknown-no-replay" : "awaiting-coding-review" });
  const results = await db.batch([
    db.prepare(`INSERT OR IGNORE INTO coding_terminal_receipts
      (attempt_id, receipt_sha256, outcome, record_json, agenda_result_json, artifact_key)
      SELECT c.attempt_id, ?5, ?6, ?7, ?8, ?9 FROM coding_attempts c
      JOIN intelligence_tasks t ON t.task_id = c.task_id
      WHERE c.attempt_id = ?1 AND c.task_id = ?2 AND c.owner_id = ?3 AND c.input_sha256 = ?4
        AND t.claimed_by = ?3 AND t.status IN ('running','blocked')`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256, input.receiptSha256, input.outcome,
        recordJson, agendaResult, input.evidence?.artifactKey ?? null),
    db.prepare(`UPDATE intelligence_tasks SET status = 'blocked', result = ?6,
        artifact_key = ?7, completed_at = NULL, updated_at = datetime('now')
      WHERE task_id = ?2 AND claimed_by = ?3 AND status IN ('running','blocked')
        AND (status != 'blocked' OR result IS NOT ?6)
        AND NOT EXISTS (SELECT 1 FROM coding_acceptance_receipts WHERE attempt_id = ?1)
        AND EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
          WHERE c.attempt_id = ?1 AND c.task_id = ?2 AND c.owner_id = ?3
            AND c.input_sha256 = ?4 AND r.record_json = ?5)`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256, recordJson, agendaResult,
        input.evidence?.artifactKey ?? null),
  ]);
  if (results.some(result => !result.success)) throw unavailable();
  const attempt = await getCodingAttempt(db, input.attemptId);
  if (!attempt || !sameIdentity(attempt, input) || JSON.stringify(attempt.terminal) !== recordJson)
    conflict("Terminal identity conflicts or attempt does not own the task");
  return { recording: results[0].meta.changes === 1 ? "created" as const : "replay" as const, attempt };
}

export async function recordCodingAcceptance(db: D1Database, supplied: CodingAcceptance) {
  const input: CodingAcceptance = { taskId: supplied.taskId, attemptId: supplied.attemptId,
    ownerId: supplied.ownerId, inputSha256: supplied.inputSha256,
    terminalReceiptSha256: supplied.terminalReceiptSha256, decision: supplied.decision,
    reviewerId: supplied.reviewerId, reason: supplied.reason };
  identity(input); id(input.reviewerId, "reviewerId"); digest(input.terminalReceiptSha256, "terminalReceiptSha256");
  if (!["accepted", "rejected"].includes(input.decision) || typeof input.reason !== "string"
    || !input.reason.trim() || input.reason.length > 4096) invalid("Invalid coding review");
  const recordJson = JSON.stringify(input);
  const agendaResult = JSON.stringify({ kind: "coding-execution-review", attemptId: input.attemptId,
    decision: input.decision, reviewerId: input.reviewerId, scientificAcceptance: false, publication: false });
  const results = await db.batch([
    db.prepare(`INSERT OR IGNORE INTO coding_acceptance_receipts (attempt_id, decision, record_json, agenda_result_json)
      SELECT c.attempt_id, ?6, ?7, ?8 FROM coding_attempts c
      JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
      JOIN intelligence_tasks t ON t.task_id = c.task_id
      WHERE c.attempt_id = ?1 AND c.task_id = ?2 AND c.owner_id = ?3 AND c.input_sha256 = ?4
        AND r.receipt_sha256 = ?5 AND t.claimed_by = ?3 AND t.status = 'blocked'
        AND (?6 = 'rejected' OR r.outcome = 'succeeded')`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256,
        input.terminalReceiptSha256, input.decision, recordJson, agendaResult),
    db.prepare(`UPDATE intelligence_tasks SET status = ?6, result = ?7,
        completed_at = CASE WHEN ?6 = 'done' THEN
          (SELECT recorded_at FROM coding_acceptance_receipts WHERE attempt_id = ?1) ELSE NULL END,
        updated_at = datetime('now')
      WHERE task_id = ?2 AND claimed_by = ?3 AND status = 'blocked'
        AND (status != ?6 OR result IS NOT ?7)
        AND EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_acceptance_receipts a ON a.attempt_id = c.attempt_id
          WHERE c.attempt_id = ?1 AND c.task_id = ?2 AND c.owner_id = ?3 AND c.input_sha256 = ?4
            AND a.record_json = ?5)`)
      .bind(input.attemptId, input.taskId, input.ownerId, input.inputSha256, recordJson,
        input.decision === "accepted" ? "done" : "blocked",
        agendaResult),
  ]);
  if (results.some(result => !result.success)) throw unavailable();
  const attempt = await getCodingAttempt(db, input.attemptId);
  if (!attempt || !sameIdentity(attempt, input) || JSON.stringify(attempt.acceptance) !== recordJson)
    conflict("Review identity conflicts or raw evidence is not eligible");
  return { recording: results[0].meta.changes === 1 ? "created" as const : "replay" as const, attempt };
}
