-- Derived review revisions for immutable observation versions.
-- Apply after 0001_private_corpus.sql in the dedicated PRIVATE_CORPUS database.
-- This is cache invalidation metadata, not a replacement for qualification events.
CREATE TABLE IF NOT EXISTS workspace_corpus_review_heads (
  record_id TEXT NOT NULL,
  record_sha256 TEXT NOT NULL,
  revision INTEGER NOT NULL CHECK(revision BETWEEN 1 AND 9007199254740991),
  PRIMARY KEY(record_id,record_sha256),
  FOREIGN KEY(record_id,record_sha256)
    REFERENCES workspace_corpus_observations(record_id,record_sha256)
);

CREATE INDEX IF NOT EXISTS idx_workspace_corpus_qualification_page
 ON workspace_corpus_qualifications(record_id,record_sha256,event_id);

-- Backfill existing immutable history. Reapplication never resets a newer head.
INSERT INTO workspace_corpus_review_heads (record_id,record_sha256,revision)
 SELECT record_id,record_sha256,COUNT(*) FROM workspace_corpus_qualifications
 GROUP BY record_id,record_sha256
 ON CONFLICT(record_id,record_sha256) DO NOTHING;

-- Runs inside the same transaction as event insertion. Exact event no-ops do
-- not fire this trigger; a rolled-back import also rolls back the head change.
CREATE TRIGGER IF NOT EXISTS workspace_corpus_review_head_advance
AFTER INSERT ON workspace_corpus_qualifications BEGIN
 INSERT INTO workspace_corpus_review_heads (record_id,record_sha256,revision)
 VALUES (NEW.record_id,NEW.record_sha256,1)
 ON CONFLICT(record_id,record_sha256)
 DO UPDATE SET revision=workspace_corpus_review_heads.revision+1;
END;
CREATE TRIGGER IF NOT EXISTS workspace_corpus_review_heads_no_delete
BEFORE DELETE ON workspace_corpus_review_heads
BEGIN SELECT RAISE(ABORT,'immutable corpus review head'); END;
