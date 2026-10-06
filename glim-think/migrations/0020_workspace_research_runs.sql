-- Private projections of the local scientific PI ledger. No dispatch or replay.
CREATE TABLE IF NOT EXISTS workspace_research_runs (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  payload TEXT NOT NULL CHECK (length(CAST(payload AS BLOB)) <= 196608),
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_workspace_research_runs_started
  ON workspace_research_runs(started_at DESC, id DESC);
