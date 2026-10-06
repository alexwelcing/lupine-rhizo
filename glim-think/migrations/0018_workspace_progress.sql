-- Private, source-checked progress analyses. This adds no generation, execution
-- or publication trigger. Writers must validate payloads with progressClipSchema.
CREATE TABLE IF NOT EXISTS workspace_progress (
  id TEXT PRIMARY KEY NOT NULL,
  created_at TEXT NOT NULL,
  payload TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workspace_progress_created_at
  ON workspace_progress(created_at DESC, id DESC);
