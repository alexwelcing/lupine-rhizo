-- Scientific handoffs remain disabled until configured. This protocol upgrade
-- intentionally rejects unfenced results from older bridge daemons: stop them
-- before applying. A lost claim is uncertain and must never be replayed.
ALTER TABLE herdr_bridge_jobs ADD COLUMN claim_token TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN claim_expires_at INTEGER;
ALTER TABLE herdr_bridge_jobs ADD COLUMN scientific_role TEXT
  CHECK (scientific_role IS NULL OR scientific_role IN ('codex_mac_discovery', 'claude_aledev_critique'));
ALTER TABLE herdr_bridge_jobs ADD COLUMN agenda_task_id TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN parent_job_id TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN scientific_request_json TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN scientific_receipt_json TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN result_fingerprint TEXT;
ALTER TABLE herdr_bridge_jobs ADD COLUMN result_uncertain INTEGER NOT NULL DEFAULT 0 CHECK (result_uncertain IN (0, 1));
-- Existing claims have no provable owner under the new protocol. Preserve their
-- history while requiring operator reconciliation; do not rerun local work.
UPDATE herdr_bridge_jobs SET status = 'timeout', result_uncertain = 1,
  completed_at = unixepoch(), updated_at = unixepoch() WHERE status = 'claimed';
