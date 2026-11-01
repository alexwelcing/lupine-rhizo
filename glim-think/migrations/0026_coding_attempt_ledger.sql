-- Requires the canonical intelligence_tasks agenda table.
-- Coding admissions and evidence are immutable; no replay or automatic acceptance.
CREATE TABLE IF NOT EXISTS coding_attempts (
    attempt_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE REFERENCES intelligence_tasks(task_id),
    owner_id TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    admitted_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

CREATE TABLE IF NOT EXISTS coding_terminal_receipts (
    attempt_id TEXT PRIMARY KEY REFERENCES coding_attempts(attempt_id),
    receipt_sha256 TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('succeeded','failed','unknown')),
    record_json TEXT NOT NULL,
    agenda_result_json TEXT NOT NULL,
    artifact_key TEXT,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

CREATE TABLE IF NOT EXISTS coding_acceptance_receipts (
    attempt_id TEXT PRIMARY KEY REFERENCES coding_terminal_receipts(attempt_id),
    decision TEXT NOT NULL CHECK (decision IN ('accepted','rejected')),
    record_json TEXT NOT NULL,
    agenda_result_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  );

CREATE TRIGGER IF NOT EXISTS coding_attempts_immutable_update BEFORE UPDATE ON coding_attempts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_attempts_immutable_delete BEFORE DELETE ON coding_attempts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_terminal_receipts_immutable_update BEFORE UPDATE ON coding_terminal_receipts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_terminal_receipts_immutable_delete BEFORE DELETE ON coding_terminal_receipts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_acceptance_receipts_immutable_update BEFORE UPDATE ON coding_acceptance_receipts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_acceptance_receipts_immutable_delete BEFORE DELETE ON coding_acceptance_receipts
      BEGIN SELECT RAISE(ABORT, 'coding ledger records are immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_agenda_owner_guard BEFORE UPDATE OF claimed_by, status ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts c WHERE c.task_id = OLD.task_id)
    AND (NEW.claimed_by IS NOT (SELECT owner_id FROM coding_attempts WHERE task_id = OLD.task_id)
      OR NEW.status NOT IN ('running','blocked','done')
      OR (NEW.status = 'running' AND EXISTS (SELECT 1 FROM coding_terminal_receipts r
        JOIN coding_attempts c ON c.attempt_id = r.attempt_id WHERE c.task_id = OLD.task_id))
      OR (NEW.status = 'done' AND NOT EXISTS (SELECT 1 FROM coding_acceptance_receipts a
        JOIN coding_attempts c ON c.attempt_id = a.attempt_id
        WHERE c.task_id = OLD.task_id AND a.decision = 'accepted')))
    BEGIN SELECT RAISE(ABORT, 'coding agenda ownership or completion is fenced'); END;

CREATE TRIGGER IF NOT EXISTS coding_agenda_delete_guard BEFORE DELETE ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts WHERE task_id = OLD.task_id)
    BEGIN SELECT RAISE(ABORT, 'coding task history is immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_agenda_input_guard BEFORE UPDATE OF task_id, domain, payload ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts WHERE task_id = OLD.task_id)
      AND (NEW.task_id IS NOT OLD.task_id OR NEW.domain IS NOT OLD.domain OR NEW.payload IS NOT OLD.payload)
    BEGIN SELECT RAISE(ABORT, 'coding task input is immutable'); END;

CREATE TRIGGER IF NOT EXISTS coding_agenda_evidence_guard BEFORE UPDATE OF status, result, artifact_key, completed_at ON intelligence_tasks
    WHEN EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
      WHERE c.task_id = OLD.task_id)
    AND EXISTS (SELECT 1 FROM coding_attempts c JOIN coding_terminal_receipts r ON r.attempt_id = c.attempt_id
      LEFT JOIN coding_acceptance_receipts a ON a.attempt_id = c.attempt_id WHERE c.task_id = OLD.task_id
      AND (NEW.status IS NOT CASE WHEN a.decision = 'accepted' THEN 'done' ELSE 'blocked' END
        OR NEW.result IS NOT COALESCE(a.agenda_result_json, r.agenda_result_json)
        OR NEW.artifact_key IS NOT r.artifact_key
        OR NEW.completed_at IS NOT CASE WHEN a.decision = 'accepted' THEN a.recorded_at ELSE NULL END))
    BEGIN SELECT RAISE(ABORT, 'coding agenda projection must match immutable evidence'); END;
