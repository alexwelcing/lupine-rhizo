-- Migration 0017: herdr bridge jobs
-- The control plane dispatches research/coding jobs to local machines that
-- run herdr (terminal workspace multiplexer for coding agents). herdr has no
-- inbound network surface, so a per-machine bridge daemon polls
-- GET /bridge/jobs/next?machine_id=... for the oldest pending job, runs it in
-- a fresh herdr workspace, and posts the outcome to
-- POST /bridge/jobs/:id/result. Lifecycle telemetry travels separately as
-- lab_beats (source = "herdr-bridge"). See docs/herdr-bridge.md.
--
-- Apply together with the pending 0015/0016 batch.

CREATE TABLE IF NOT EXISTS herdr_bridge_jobs (
  job_id TEXT PRIMARY KEY,
  machine_id TEXT NOT NULL,
  agent_kind TEXT NOT NULL DEFAULT 'hermes',
  prompt TEXT NOT NULL,
  campaign_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'claimed', 'done', 'failed', 'blocked', 'timeout')),
  attempts INTEGER NOT NULL DEFAULT 0,
  output_excerpt TEXT,
  result_beat_id TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()),
  claimed_at INTEGER,
  completed_at INTEGER,
  updated_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_herdr_bridge_jobs_machine_status
  ON herdr_bridge_jobs(machine_id, status, created_at);
