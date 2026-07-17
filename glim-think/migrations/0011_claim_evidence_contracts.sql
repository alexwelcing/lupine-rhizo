-- D1/SQLite schema for versioned research claims, evidence, and enforcement contracts.
-- All identifiers are stable application-assigned TEXT values; no rowid is part of a public ID.

CREATE TABLE IF NOT EXISTS campaign (
  campaign_id TEXT PRIMARY KEY,
  version INTEGER NOT NULL CHECK (version >= 1),
  preregistration_id TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE
    CHECK (length(content_hash) = 71 AND substr(content_hash, 1, 7) = 'sha256:'
      AND substr(content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
  manifest_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  activated_at TEXT
);

CREATE TABLE IF NOT EXISTS campaign_hypothesis (
  campaign_hypothesis_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
  hypothesis_id TEXT NOT NULL,
  statement TEXT NOT NULL,
  frozen INTEGER NOT NULL DEFAULT 1 CHECK (frozen = 1),
  UNIQUE (campaign_id, hypothesis_id)
);

CREATE TABLE IF NOT EXISTS measurement (
  measurement_id TEXT PRIMARY KEY,
  campaign_id TEXT REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
  run_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT,
  scope_json TEXT,
  measured_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS measurement_campaign_run_idx
  ON measurement(campaign_id, run_id);

CREATE TABLE IF NOT EXISTS calibration (
  calibration_id TEXT PRIMARY KEY,
  campaign_id TEXT REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
  method TEXT NOT NULL,
  parameters_json TEXT NOT NULL,
  source_measurement_id TEXT REFERENCES measurement(measurement_id) ON DELETE RESTRICT,
  artifact_hash TEXT UNIQUE
    CHECK (artifact_hash IS NULL OR
      (length(artifact_hash) = 71 AND substr(artifact_hash, 1, 7) = 'sha256:'
        AND substr(artifact_hash, 8) NOT GLOB '*[^0-9a-f]*')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS evidence_bundle (
  bundle_id TEXT PRIMARY KEY
    CHECK (length(bundle_id) = 71 AND substr(bundle_id, 1, 7) = 'sha256:'
      AND substr(bundle_id, 8) NOT GLOB '*[^0-9a-f]*'),
  claim_predicate TEXT NOT NULL,
  epistemic_status TEXT NOT NULL CHECK (
    epistemic_status IN ('confirmatory', 'exploratory', 'descriptive', 'negative', 'unsupported')
  ),
  scope_json TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  supersedes_bundle_id TEXT REFERENCES evidence_bundle(bundle_id) ON DELETE RESTRICT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS evidence_artifact (
  artifact_id TEXT PRIMARY KEY,
  bundle_id TEXT NOT NULL REFERENCES evidence_bundle(bundle_id) ON DELETE RESTRICT,
  campaign_id TEXT REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
  run_id TEXT NOT NULL,
  artifact_uri TEXT NOT NULL,
  artifact_hash TEXT NOT NULL
    CHECK (length(artifact_hash) = 71 AND substr(artifact_hash, 1, 7) = 'sha256:'
      AND substr(artifact_hash, 8) NOT GLOB '*[^0-9a-f]*'),
  thresholds_version TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (bundle_id, artifact_hash)
);

CREATE INDEX IF NOT EXISTS evidence_artifact_bundle_idx
  ON evidence_artifact(bundle_id);

CREATE TABLE IF NOT EXISTS claim (
  claim_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS claim_version (
  claim_version_id TEXT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES claim(claim_id) ON DELETE RESTRICT,
  version INTEGER NOT NULL CHECK (version >= 1),
  statement TEXT NOT NULL,
  intent TEXT NOT NULL CHECK (intent IN ('confirmatory', 'exploratory', 'descriptive', 'methodological')),
  outcome TEXT NOT NULL CHECK (
    outcome IN ('pending', 'supported', 'partially_supported', 'inconclusive', 'contradicted', 'withdrawn')
  ),
  assurance TEXT NOT NULL CHECK (
    assurance IN ('unsupported', 'provisional', 'eligible', 'active', 'withdrawn')
  ),
  strength TEXT NOT NULL CHECK (strength IN ('observation', 'association', 'predictive', 'causal', 'formal')),
  content_hash TEXT NOT NULL UNIQUE
    CHECK (length(content_hash) = 71 AND substr(content_hash, 1, 7) = 'sha256:'
      AND substr(content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
  supersedes_claim_version_id TEXT REFERENCES claim_version(claim_version_id) ON DELETE RESTRICT,
  excluded_scope_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  activated_at TEXT,
  UNIQUE (claim_id, version)
);

CREATE INDEX IF NOT EXISTS claim_version_claim_idx
  ON claim_version(claim_id, version);

CREATE TABLE IF NOT EXISTS premise (
  premise_id TEXT PRIMARY KEY,
  statement TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS claim_premise (
  claim_version_id TEXT NOT NULL REFERENCES claim_version(claim_version_id) ON DELETE RESTRICT,
  premise_id TEXT NOT NULL REFERENCES premise(premise_id) ON DELETE RESTRICT,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  support_mode TEXT NOT NULL CHECK (support_mode IN ('all', 'any', 'at_least', 'unsupported')),
  minimum_evidence INTEGER CHECK (
    (support_mode = 'at_least' AND minimum_evidence >= 1)
    OR (support_mode <> 'at_least' AND minimum_evidence IS NULL)
  ),
  PRIMARY KEY (claim_version_id, premise_id),
  UNIQUE (claim_version_id, ordinal)
);

CREATE TABLE IF NOT EXISTS premise_evidence (
  claim_version_id TEXT NOT NULL,
  premise_id TEXT NOT NULL,
  bundle_id TEXT NOT NULL REFERENCES evidence_bundle(bundle_id) ON DELETE RESTRICT,
  PRIMARY KEY (claim_version_id, premise_id, bundle_id),
  FOREIGN KEY (claim_version_id, premise_id)
    REFERENCES claim_premise(claim_version_id, premise_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS premise_evidence_bundle_idx
  ON premise_evidence(bundle_id);

CREATE TABLE IF NOT EXISTS theorem_binding (
  theorem_binding_id TEXT PRIMARY KEY,
  claim_version_id TEXT NOT NULL REFERENCES claim_version(claim_version_id) ON DELETE RESTRICT,
  status TEXT NOT NULL CHECK (status IN ('bound', 'unsupported')),
  module TEXT,
  theorem_name TEXT,
  reason TEXT,
  CHECK (
    (status = 'bound' AND module IS NOT NULL AND theorem_name IS NOT NULL AND reason IS NULL)
    OR (status = 'unsupported' AND module IS NULL AND theorem_name IS NULL AND reason IS NOT NULL)
  ),
  UNIQUE (claim_version_id)
);

CREATE TABLE IF NOT EXISTS runtime_gate_binding (
  runtime_gate_binding_id TEXT PRIMARY KEY,
  claim_version_id TEXT NOT NULL REFERENCES claim_version(claim_version_id) ON DELETE RESTRICT,
  status TEXT NOT NULL CHECK (status IN ('bound', 'unsupported')),
  gate_id TEXT,
  reason TEXT,
  CHECK (
    (status = 'bound' AND gate_id IS NOT NULL AND reason IS NULL)
    OR (status = 'unsupported' AND gate_id IS NULL AND reason IS NOT NULL)
  ),
  UNIQUE (claim_version_id)
);

CREATE TABLE IF NOT EXISTS publication_binding (
  publication_binding_id TEXT PRIMARY KEY,
  claim_version_id TEXT NOT NULL REFERENCES claim_version(claim_version_id) ON DELETE RESTRICT,
  status TEXT NOT NULL CHECK (status IN ('bound', 'unsupported')),
  publication_id TEXT,
  recurring_claim TEXT,
  reason TEXT,
  CHECK (
    (status = 'bound' AND publication_id IS NOT NULL AND recurring_claim IS NOT NULL AND reason IS NULL)
    OR (status = 'unsupported' AND publication_id IS NULL AND recurring_claim IS NULL AND reason IS NOT NULL)
  ),
  UNIQUE (claim_version_id),
  UNIQUE (publication_id, recurring_claim, claim_version_id)
);

CREATE INDEX IF NOT EXISTS publication_binding_recurring_claim_idx
  ON publication_binding(recurring_claim, claim_version_id);

CREATE TABLE IF NOT EXISTS status_event (
  status_event_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  from_status TEXT,
  to_status TEXT NOT NULL,
  evidence_bundle_id TEXT REFERENCES evidence_bundle(bundle_id) ON DELETE RESTRICT,
  occurred_at TEXT NOT NULL,
  actor TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS status_event_entity_idx
  ON status_event(entity_type, entity_id, occurred_at);

CREATE INDEX IF NOT EXISTS status_event_bundle_idx
  ON status_event(evidence_bundle_id);

CREATE TABLE IF NOT EXISTS registry_snapshot (
  snapshot_id TEXT PRIMARY KEY,
  content_hash TEXT NOT NULL UNIQUE
    CHECK (length(content_hash) = 71 AND substr(content_hash, 1, 7) = 'sha256:'
      AND substr(content_hash, 8) NOT GLOB '*[^0-9a-f]*'),
  registry_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Activated campaign versions may only transition from inactive to active; their frozen
-- hypotheses and manifest data cannot subsequently be changed.
CREATE TRIGGER IF NOT EXISTS campaign_activation_only
BEFORE UPDATE ON campaign
WHEN OLD.activated_at IS NULL AND NEW.activated_at IS NOT NULL AND (
  NEW.campaign_id IS NOT OLD.campaign_id OR NEW.version IS NOT OLD.version
  OR NEW.preregistration_id IS NOT OLD.preregistration_id
  OR NEW.content_hash IS NOT OLD.content_hash OR NEW.manifest_json IS NOT OLD.manifest_json
  OR NEW.created_at IS NOT OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'activation may only set activated_at');
END;

CREATE TRIGGER IF NOT EXISTS campaign_immutable_update
BEFORE UPDATE ON campaign
WHEN OLD.activated_at IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'activated campaign is immutable');
END;

CREATE TRIGGER IF NOT EXISTS campaign_immutable_delete
BEFORE DELETE ON campaign
WHEN OLD.activated_at IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'activated campaign is immutable');
END;

CREATE TRIGGER IF NOT EXISTS campaign_hypothesis_immutable_insert
BEFORE INSERT ON campaign_hypothesis
WHEN EXISTS (SELECT 1 FROM campaign WHERE campaign_id = NEW.campaign_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated campaign is immutable');
END;

CREATE TRIGGER IF NOT EXISTS campaign_hypothesis_immutable_update
BEFORE UPDATE ON campaign_hypothesis
WHEN EXISTS (SELECT 1 FROM campaign WHERE campaign_id = OLD.campaign_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM campaign WHERE campaign_id = NEW.campaign_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated campaign is immutable');
END;

CREATE TRIGGER IF NOT EXISTS campaign_hypothesis_immutable_delete
BEFORE DELETE ON campaign_hypothesis
WHEN EXISTS (SELECT 1 FROM campaign WHERE campaign_id = OLD.campaign_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated campaign is immutable');
END;

-- Activation is a single-field transition. Once active, the version and every row that
-- composes its contract are immutable.
CREATE TRIGGER IF NOT EXISTS claim_version_activation_only
BEFORE UPDATE ON claim_version
WHEN OLD.activated_at IS NULL AND NEW.activated_at IS NOT NULL AND (
  NEW.claim_version_id IS NOT OLD.claim_version_id OR NEW.claim_id IS NOT OLD.claim_id
  OR NEW.version IS NOT OLD.version OR NEW.statement IS NOT OLD.statement
  OR NEW.intent IS NOT OLD.intent OR NEW.outcome IS NOT OLD.outcome
  OR NEW.assurance IS NOT OLD.assurance OR NEW.strength IS NOT OLD.strength
  OR NEW.content_hash IS NOT OLD.content_hash
  OR NEW.supersedes_claim_version_id IS NOT OLD.supersedes_claim_version_id
  OR NEW.excluded_scope_json IS NOT OLD.excluded_scope_json OR NEW.created_at IS NOT OLD.created_at
)
BEGIN
  SELECT RAISE(ABORT, 'activation may only set activated_at');
END;

CREATE TRIGGER IF NOT EXISTS claim_version_immutable_update
BEFORE UPDATE ON claim_version
WHEN OLD.activated_at IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS claim_version_immutable_delete
BEFORE DELETE ON claim_version
WHEN OLD.activated_at IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS premise_immutable_update
BEFORE UPDATE ON premise
WHEN EXISTS (
  SELECT 1 FROM claim_premise cp JOIN claim_version cv USING (claim_version_id)
  WHERE cp.premise_id = OLD.premise_id AND cv.activated_at IS NOT NULL
)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS premise_immutable_delete
BEFORE DELETE ON premise
WHEN EXISTS (
  SELECT 1 FROM claim_premise cp JOIN claim_version cv USING (claim_version_id)
  WHERE cp.premise_id = OLD.premise_id AND cv.activated_at IS NOT NULL
)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS claim_premise_immutable_insert
BEFORE INSERT ON claim_premise
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS claim_premise_immutable_update
BEFORE UPDATE ON claim_premise
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS claim_premise_immutable_delete
BEFORE DELETE ON claim_premise
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS premise_evidence_immutable_insert
BEFORE INSERT ON premise_evidence
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS premise_evidence_immutable_update
BEFORE UPDATE ON premise_evidence
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS premise_evidence_immutable_delete
BEFORE DELETE ON premise_evidence
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS theorem_binding_immutable_insert
BEFORE INSERT ON theorem_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS theorem_binding_immutable_update
BEFORE UPDATE ON theorem_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS theorem_binding_immutable_delete
BEFORE DELETE ON theorem_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS runtime_gate_binding_immutable_insert
BEFORE INSERT ON runtime_gate_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS runtime_gate_binding_immutable_update
BEFORE UPDATE ON runtime_gate_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS runtime_gate_binding_immutable_delete
BEFORE DELETE ON runtime_gate_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS publication_binding_immutable_insert
BEFORE INSERT ON publication_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS publication_binding_immutable_update
BEFORE UPDATE ON publication_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
  OR EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = NEW.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

CREATE TRIGGER IF NOT EXISTS publication_binding_immutable_delete
BEFORE DELETE ON publication_binding
WHEN EXISTS (SELECT 1 FROM claim_version WHERE claim_version_id = OLD.claim_version_id AND activated_at IS NOT NULL)
BEGIN
  SELECT RAISE(ABORT, 'activated claim version is immutable');
END;

-- Evidence receipts and registry snapshots are content-addressed immutable records.
CREATE TRIGGER IF NOT EXISTS evidence_bundle_immutable_update
BEFORE UPDATE ON evidence_bundle
BEGIN
  SELECT RAISE(ABORT, 'evidence_bundle is immutable');
END;

CREATE TRIGGER IF NOT EXISTS evidence_bundle_immutable_delete
BEFORE DELETE ON evidence_bundle
BEGIN
  SELECT RAISE(ABORT, 'evidence_bundle is immutable');
END;

CREATE TRIGGER IF NOT EXISTS registry_snapshot_immutable_update
BEFORE UPDATE ON registry_snapshot
BEGIN
  SELECT RAISE(ABORT, 'registry_snapshot is immutable');
END;

CREATE TRIGGER IF NOT EXISTS registry_snapshot_immutable_delete
BEFORE DELETE ON registry_snapshot
BEGIN
  SELECT RAISE(ABORT, 'registry_snapshot is immutable');
END;

-- Status is history, not mutable state. Corrections are represented by a new event.
CREATE TRIGGER IF NOT EXISTS status_event_append_only_update
BEFORE UPDATE ON status_event
BEGIN
  SELECT RAISE(ABORT, 'status_event is append-only');
END;

CREATE TRIGGER IF NOT EXISTS status_event_append_only_delete
BEFORE DELETE ON status_event
BEGIN
  SELECT RAISE(ABORT, 'status_event is append-only');
END;
