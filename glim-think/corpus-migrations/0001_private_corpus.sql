-- Private imported research evidence. No public reader or execution authority.
-- Apply explicitly after deployment approval; migration is not run on request.
CREATE TABLE IF NOT EXISTS workspace_evidence_receipts (
  sha256 TEXT PRIMARY KEY CHECK(length(sha256)=64),
  bytes INTEGER NOT NULL CHECK(bytes BETWEEN 0 AND 26214400),
  etag TEXT NOT NULL,
  verified_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS workspace_evidence_receipts_immutable
BEFORE UPDATE ON workspace_evidence_receipts BEGIN SELECT RAISE(ABORT,'immutable evidence receipt'); END;
CREATE TRIGGER IF NOT EXISTS workspace_evidence_receipts_no_delete
BEFORE DELETE ON workspace_evidence_receipts BEGIN SELECT RAISE(ABORT,'immutable evidence receipt'); END;

CREATE TABLE IF NOT EXISTS workspace_corpus_imports (
  import_id TEXT PRIMARY KEY,
  payload_sha256 TEXT NOT NULL,
  observation_count INTEGER NOT NULL,
  qualification_count INTEGER NOT NULL,
  committed_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS workspace_corpus_imports_immutable
BEFORE UPDATE ON workspace_corpus_imports BEGIN SELECT RAISE(ABORT,'immutable corpus import'); END;
CREATE TRIGGER IF NOT EXISTS workspace_corpus_imports_no_delete
BEFORE DELETE ON workspace_corpus_imports BEGIN SELECT RAISE(ABORT,'immutable corpus import'); END;

CREATE TABLE IF NOT EXISTS workspace_corpus_observations (
  record_id TEXT NOT NULL,
  record_sha256 TEXT NOT NULL,
  projection_sha256 TEXT NOT NULL,
  evidence_sha256 TEXT NOT NULL REFERENCES workspace_evidence_receipts(sha256),
  source_id TEXT,
  study_id TEXT,
  locator TEXT NOT NULL,
  material TEXT,
  observable TEXT,
  unit TEXT,
  model_id TEXT,
  reference_kind TEXT,
  observed_at TEXT,
  reviewed_at TEXT,
  original_row_sha256 TEXT,
  missing_fields_json TEXT NOT NULL,
  record_json TEXT NOT NULL CHECK(length(CAST(record_json AS BLOB))<=65536),
  PRIMARY KEY(record_id,record_sha256)
);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_material_observable
 ON workspace_corpus_observations(material,observable,record_id,record_sha256);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_source
 ON workspace_corpus_observations(source_id,record_id,record_sha256);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_study
 ON workspace_corpus_observations(study_id,record_id,record_sha256);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_observable
 ON workspace_corpus_observations(observable,record_id,record_sha256);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_model
 ON workspace_corpus_observations(model_id,record_id,record_sha256);
CREATE TRIGGER IF NOT EXISTS workspace_corpus_observations_immutable
BEFORE UPDATE ON workspace_corpus_observations BEGIN SELECT RAISE(ABORT,'immutable corpus observation'); END;
CREATE TRIGGER IF NOT EXISTS workspace_corpus_observations_no_delete
BEFORE DELETE ON workspace_corpus_observations BEGIN SELECT RAISE(ABORT,'immutable corpus observation'); END;

CREATE TABLE IF NOT EXISTS workspace_corpus_members (
  import_id TEXT NOT NULL REFERENCES workspace_corpus_imports(import_id),
  record_id TEXT NOT NULL,
  record_sha256 TEXT NOT NULL,
  PRIMARY KEY(import_id,record_id,record_sha256),
  FOREIGN KEY(record_id,record_sha256) REFERENCES workspace_corpus_observations(record_id,record_sha256)
);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_member_record
 ON workspace_corpus_members(record_id,record_sha256,import_id);
CREATE TRIGGER IF NOT EXISTS workspace_corpus_members_immutable
BEFORE UPDATE ON workspace_corpus_members BEGIN SELECT RAISE(ABORT,'immutable corpus membership'); END;
CREATE TRIGGER IF NOT EXISTS workspace_corpus_members_no_delete
BEFORE DELETE ON workspace_corpus_members BEGIN SELECT RAISE(ABORT,'immutable corpus membership'); END;

CREATE TABLE IF NOT EXISTS workspace_corpus_qualifications (
  event_id TEXT PRIMARY KEY,
  event_sha256 TEXT NOT NULL,
  import_id TEXT NOT NULL REFERENCES workspace_corpus_imports(import_id),
  record_id TEXT NOT NULL,
  record_sha256 TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('quarantine','annotation','correction')),
  reason TEXT NOT NULL,
  original_reviewed_at TEXT,
  FOREIGN KEY(record_id,record_sha256) REFERENCES workspace_corpus_observations(record_id,record_sha256)
);
CREATE INDEX IF NOT EXISTS idx_workspace_corpus_qualification_record
 ON workspace_corpus_qualifications(record_id,record_sha256,kind);
CREATE TRIGGER IF NOT EXISTS workspace_corpus_qualifications_immutable
BEFORE UPDATE ON workspace_corpus_qualifications BEGIN SELECT RAISE(ABORT,'immutable corpus qualification'); END;
CREATE TRIGGER IF NOT EXISTS workspace_corpus_qualifications_no_delete
BEFORE DELETE ON workspace_corpus_qualifications BEGIN SELECT RAISE(ABORT,'immutable corpus qualification'); END;
