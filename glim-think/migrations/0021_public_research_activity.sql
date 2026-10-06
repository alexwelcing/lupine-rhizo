-- Reviewed public records only. No INSERT ... SELECT from private research data.
CREATE TABLE IF NOT EXISTS public_research_activity (
  id TEXT PRIMARY KEY,
  activity_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  supersedes_id TEXT,
  payload_sha256 TEXT NOT NULL CHECK (length(payload_sha256) = 64),
  payload TEXT NOT NULL CHECK (json_valid(payload) AND length(CAST(payload AS BLOB)) <= 16384),
  imported_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  UNIQUE (activity_id, id),
  FOREIGN KEY (activity_id, supersedes_id) REFERENCES public_research_activity(activity_id, id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_public_activity_root
  ON public_research_activity(activity_id) WHERE supersedes_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_public_activity_successor
  ON public_research_activity(supersedes_id) WHERE supersedes_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_public_activity_observed
  ON public_research_activity(observed_at DESC, id DESC);
-- Offline reviewed imports use these same guards. No overwrite, orphan,
-- branching history, backward observation, or reopening a terminal result.
CREATE TRIGGER IF NOT EXISTS public_activity_validate_insert
  BEFORE INSERT ON public_research_activity BEGIN
    SELECT CASE WHEN EXISTS (
      SELECT 1 FROM public_research_activity WHERE id = NEW.id
      AND (payload_sha256 <> NEW.payload_sha256 OR payload <> NEW.payload)
    ) THEN RAISE(ABORT, 'Public activity ID is immutable') END;
    SELECT CASE WHEN EXISTS (
      SELECT 1 FROM public_research_activity WHERE id = NEW.id
      AND payload_sha256 = NEW.payload_sha256 AND payload = NEW.payload
    ) THEN RAISE(IGNORE) END;
    SELECT CASE WHEN
      json_extract(NEW.payload, '$.schema') IS NOT 'lupine.public_research_activity.v1'
      OR json_extract(NEW.payload, '$.id') IS NOT NEW.id
      OR json_extract(NEW.payload, '$.activityId') IS NOT NEW.activity_id
      OR json_extract(NEW.payload, '$.observedAt') IS NOT NEW.observed_at
      OR json_extract(NEW.payload, '$.reviewedAt') IS NOT NEW.reviewed_at
      OR json_extract(NEW.payload, '$.supersedes') IS NOT NEW.supersedes_id
      OR NEW.reviewed_at < NEW.observed_at
    THEN RAISE(ABORT, 'Public activity envelope mismatch') END;
    SELECT CASE WHEN NEW.supersedes_id IS NULL AND EXISTS (
      SELECT 1 FROM public_research_activity WHERE activity_id = NEW.activity_id
    ) THEN RAISE(ABORT, 'Public activity root already exists') END;
    SELECT CASE WHEN NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM public_research_activity previous
      WHERE previous.id = NEW.supersedes_id AND previous.activity_id = NEW.activity_id
      AND previous.observed_at <= NEW.observed_at AND previous.reviewed_at < NEW.reviewed_at
      AND json_extract(previous.payload, '$.evidenceKind') = json_extract(NEW.payload, '$.evidenceKind')
      AND NOT EXISTS (SELECT 1 FROM public_research_activity successor WHERE successor.supersedes_id = previous.id)
      AND (
        (json_extract(previous.payload, '$.state') IN ('completed', 'failed')
         AND json_extract(NEW.payload, '$.state') = json_extract(previous.payload, '$.state')
         AND json_type(NEW.payload, '$.correctionReason') = 'text'
         AND length(trim(json_extract(NEW.payload, '$.correctionReason'))) > 0)
        OR
        (json_extract(previous.payload, '$.state') NOT IN ('completed', 'failed')
         AND (json_extract(previous.payload, '$.state') = 'planned' OR json_extract(NEW.payload, '$.state') <> 'planned'))
      )
    ) THEN RAISE(ABORT, 'Public activity ancestry or terminal state conflicts') END;
  END;
CREATE TRIGGER IF NOT EXISTS public_activity_no_update
  BEFORE UPDATE ON public_research_activity BEGIN SELECT RAISE(ABORT, 'Public activity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS public_activity_no_delete
  BEFORE DELETE ON public_research_activity BEGIN SELECT RAISE(ABORT, 'Public activity is immutable'); END;
