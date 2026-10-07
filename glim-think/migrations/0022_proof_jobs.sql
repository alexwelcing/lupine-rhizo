-- Private native-API proof lifecycle. Never contains local controller history.
CREATE TABLE IF NOT EXISTS proof_jobs (
  id TEXT PRIMARY KEY,
  agenda_id TEXT NOT NULL,
  request_json TEXT NOT NULL,
  request_sha256 TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('queued','submitting','processing','cancel_requested','completion_unknown','candidate_ready','failed','cancelled','expired','invalid_result')),
  batch_id TEXT,
  provider_json TEXT,
  candidate_json TEXT,
  receipt_json TEXT,
  candidate_sha256 TEXT,
  failure_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  observed_at TEXT,
  cancel_sent INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  poll_token TEXT,
  poll_until TEXT
);
-- An unknown submission keeps the agenda occupied until it is reconciled.
CREATE UNIQUE INDEX IF NOT EXISTS proof_one_active_agenda ON proof_jobs(agenda_id) WHERE active=1;
CREATE INDEX IF NOT EXISTS proof_active_poll ON proof_jobs(active,updated_at);

CREATE UNIQUE INDEX IF NOT EXISTS proof_unique_batch ON proof_jobs(batch_id) WHERE batch_id IS NOT NULL;
