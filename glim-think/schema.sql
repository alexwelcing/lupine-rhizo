-- Latest-state glim-think ledger schema.
-- Use this file by itself for a fresh schema-only database. Do not follow it
-- with historical migrations; `just think-d1-init` owns that separate path.

CREATE TABLE IF NOT EXISTS records (
  record_id TEXT PRIMARY KEY,
  element TEXT,
  potential_id TEXT,
  potential_label TEXT,
  pair_style TEXT,
  property TEXT,
  reference REAL,
  predicted REAL,
  unit TEXT,
  provenance TEXT,
  agent_id TEXT,
  timestamp TEXT
);

CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  agent_id TEXT,
  claim_type TEXT,
  evidence_ids TEXT,
  confidence REAL,
  status TEXT DEFAULT 'Proposed',
  timestamp TEXT,
  description TEXT,
  claim_data TEXT NOT NULL DEFAULT '{}',
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claim_type);
CREATE INDEX IF NOT EXISTS idx_claims_agent ON claims(agent_id);
CREATE INDEX IF NOT EXISTS idx_claims_created_at ON claims(created_at DESC);

-- Agent-specific state tables
CREATE TABLE IF NOT EXISTS manifold_runs (
  family TEXT,
  element TEXT,
  claim_id TEXT,
  pr REAL,
  timestamp TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (family, element)
);

CREATE TABLE IF NOT EXISTS causal_screens (
  grouping TEXT PRIMARY KEY,
  timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS theories (
  theory_id TEXT PRIMARY KEY,
  observation_claim_id TEXT,
  explanation TEXT,
  prediction TEXT,
  test_strategy TEXT,
  discriminative_property TEXT,
  timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS experiment_runs (
  run_id TEXT PRIMARY KEY,
  potential_label TEXT,
  element TEXT,
  status TEXT,
  records_count INTEGER,
  timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orchestrator_state (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pending_experiments (
  experiment_id TEXT PRIMARY KEY,
  run_id TEXT,
  element TEXT,
  potential_label TEXT,
  potential_id TEXT,
  pair_style TEXT,
  structure TEXT DEFAULT 'fcc',
  properties TEXT,
  discriminative_property TEXT,
  hypothesis_id TEXT,
  spec TEXT,
  status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT (datetime('now')),
  completed_at TEXT
);

-- Deployment observability: GitHub Actions report here
CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo TEXT NOT NULL,
  workflow TEXT NOT NULL,
  run_id TEXT NOT NULL,
  status TEXT NOT NULL,
  commit_sha TEXT,
  branch TEXT,
  service TEXT NOT NULL,
  run_url TEXT,
  started_at TEXT,
  completed_at TEXT DEFAULT (datetime('now')),
  logs TEXT
);
CREATE INDEX IF NOT EXISTS idx_deployments_service ON deployments(service);
CREATE INDEX IF NOT EXISTS idx_deployments_completed_at ON deployments(completed_at DESC);

-- Public-facing hourly progress reports for the lab broadcast.
CREATE TABLE IF NOT EXISTS lab_broadcasts (
  broadcast_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  status TEXT NOT NULL,
  cadence TEXT NOT NULL DEFAULT 'hourly',
  metrics TEXT,
  artifact_key TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lab_broadcasts_created_at ON lab_broadcasts(created_at DESC);

-- Durable research agenda tables (migrations 0001-0003).
CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('proposed','testing','confirmed','refuted')),
  confidence REAL,
  evidence_ids TEXT,
  agent_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_hypotheses_created_at ON hypotheses(created_at);

CREATE TABLE IF NOT EXISTS critiques (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  question TEXT NOT NULL,
  target_hypothesis_id TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','in_progress','completed')) DEFAULT 'pending',
  response_md TEXT,
  response_artifact_key TEXT,
  created_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_critiques_status ON critiques(status);
CREATE INDEX IF NOT EXISTS idx_critiques_source ON critiques(source);
CREATE INDEX IF NOT EXISTS idx_critiques_target ON critiques(target_hypothesis_id);

CREATE TABLE IF NOT EXISTS research_questions (
  id TEXT PRIMARY KEY,
  question TEXT NOT NULL,
  asked_by TEXT,
  status TEXT NOT NULL CHECK(status IN ('open','in_progress','answered')) DEFAULT 'open',
  answer_md TEXT,
  answer_artifact_key TEXT,
  target_hypothesis_id TEXT,
  created_at TEXT NOT NULL,
  answered_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_research_questions_status ON research_questions(status);
CREATE INDEX IF NOT EXISTS idx_research_questions_created_at ON research_questions(created_at DESC);

-- Literature and structured research findings (migrations 0005-0006).
CREATE TABLE IF NOT EXISTS literature_papers (
  doi TEXT PRIMARY KEY,
  arxiv_id TEXT,
  title TEXT,
  abstract TEXT,
  authors_json TEXT,
  year INTEGER,
  venue TEXT,
  source TEXT NOT NULL CHECK(source IN ('arxiv','semantic_scholar','openalex')),
  fetched_at TEXT NOT NULL,
  raw_artifact_key TEXT
);
CREATE INDEX IF NOT EXISTS idx_literature_papers_arxiv_id ON literature_papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_literature_papers_year ON literature_papers(year);
CREATE INDEX IF NOT EXISTS idx_literature_papers_source ON literature_papers(source);

CREATE TABLE IF NOT EXISTS research_hits (
  id TEXT PRIMARY KEY,
  hypothesis_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('missing_experiment','contradiction','reinforcement','surprise')),
  summary TEXT NOT NULL,
  proposed_action TEXT,
  source_insight_ids TEXT,
  source_claim_id TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','pursuing','resolved','dismissed')),
  dedup_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_hits_status_kind ON research_hits(status, kind);
CREATE INDEX IF NOT EXISTS idx_hits_hypothesis ON research_hits(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_hits_dedup ON research_hits(dedup_key);
CREATE INDEX IF NOT EXISTS idx_hits_created_at ON research_hits(created_at DESC);

-- Live control-plane beats (migration 0007).
CREATE TABLE IF NOT EXISTS lab_beats (
  beat_id TEXT PRIMARY KEY,
  agent TEXT NOT NULL,
  summary TEXT NOT NULL,
  metrics TEXT,
  ts INTEGER NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (unixepoch())
);
CREATE INDEX IF NOT EXISTS idx_lab_beats_ts ON lab_beats(ts DESC);

-- MLIP baseline-grid workflow state (migration 0009).
CREATE TABLE IF NOT EXISTS mlip_baseline_runs (
  run_id TEXT PRIMARY KEY,
  workflow_instance_id TEXT,
  hypothesis_id TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  profile TEXT NOT NULL,
  fixture_id TEXT NOT NULL,
  manifest_url TEXT NOT NULL,
  artifact_prefix TEXT NOT NULL,
  max_dollars_per_hour REAL NOT NULL,
  requested_max_active_gpu_cells INTEGER NOT NULL,
  max_active_gpu_cells INTEGER NOT NULL,
  max_poll_waves INTEGER NOT NULL,
  rows_json TEXT NOT NULL,
  mlips_json TEXT NOT NULL,
  cost_estimate_json TEXT NOT NULL,
  report_r2_key TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS mlip_baseline_cells (
  cell_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  mlip_id TEXT NOT NULL,
  status TEXT NOT NULL,
  target_job TEXT,
  manifest_url TEXT,
  task_name TEXT,
  operation_name TEXT,
  accuracy_score REAL,
  accuracy_unit TEXT,
  speed_score REAL,
  speed_unit TEXT,
  metrics_json TEXT,
  artifact_uri TEXT,
  trace_id TEXT,
  span_id TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  enqueued_at TEXT,
  completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mlip_baseline_cells_run_status
  ON mlip_baseline_cells(run_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_mlip_baseline_cells_grid
  ON mlip_baseline_cells(run_id, row_id, mlip_id);

-- Canonical ATLAS/Lean theorem registry (migration 0011).
CREATE TABLE IF NOT EXISTS atlas_facet_registry (
  facet TEXT COLLATE NOCASE PRIMARY KEY,
  agent_class TEXT COLLATE NOCASE NOT NULL UNIQUE,
  lifecycle_status TEXT NOT NULL DEFAULT 'active'
    CHECK(lifecycle_status IN ('active','retired')),
  schema_version INTEGER NOT NULL DEFAULT 1 CHECK(schema_version > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(facet <> '' AND facet COLLATE BINARY = lower(trim(facet)))
);
INSERT OR IGNORE INTO atlas_facet_registry (facet, agent_class) VALUES
  ('causal', 'Causal'),
  ('experiment', 'Experiment'),
  ('manifold', 'Manifold'),
  ('theorist', 'Theorist');

CREATE TABLE IF NOT EXISTS atlas_theorems (
  id INTEGER PRIMARY KEY,
  facet TEXT COLLATE NOCASE NOT NULL
    REFERENCES atlas_facet_registry(facet) ON UPDATE CASCADE ON DELETE RESTRICT,
  theorem_name TEXT NOT NULL CHECK(trim(theorem_name) <> ''),
  module TEXT NOT NULL CHECK(trim(module) <> ''),
  revision TEXT NOT NULL CHECK(trim(revision) <> ''),
  proof_repository TEXT NOT NULL DEFAULT 'legacy-unspecified'
    CHECK(trim(proof_repository) <> ''),
  proof_revision TEXT,
  atlas_revision TEXT,
  mathlib_revision TEXT,
  statement_hash TEXT,
  source_hash TEXT,
  build_manifest_hash TEXT,
  status TEXT NOT NULL DEFAULT 'imported'
    CHECK(status IN ('imported','verified','extended','failed')),
  lifecycle_status TEXT NOT NULL DEFAULT 'active'
    CHECK(lifecycle_status IN ('active','retired','superseded')),
  superseded_by_id INTEGER REFERENCES atlas_theorems(id) ON DELETE RESTRICT,
  used_in_hypotheses INTEGER NOT NULL DEFAULT 0 CHECK(used_in_hypotheses >= 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(facet <> '' AND facet COLLATE BINARY = lower(trim(facet))),
  CHECK(proof_revision IS NULL OR trim(proof_revision) <> ''),
  CHECK(atlas_revision IS NULL OR trim(atlas_revision) <> ''),
  CHECK(mathlib_revision IS NULL OR trim(mathlib_revision) <> ''),
  CHECK(statement_hash IS NULL OR (
    length(statement_hash) = 64 AND statement_hash = lower(statement_hash) AND
    statement_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(source_hash IS NULL OR (
    length(source_hash) = 64 AND source_hash = lower(source_hash) AND
    source_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(build_manifest_hash IS NULL OR (
    length(build_manifest_hash) = 64 AND build_manifest_hash = lower(build_manifest_hash) AND
    build_manifest_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(
    (lifecycle_status = 'superseded' AND superseded_by_id IS NOT NULL) OR
    (lifecycle_status IN ('active','retired') AND superseded_by_id IS NULL)
  )
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_atlas_theorems_identity
  ON atlas_theorems(facet, theorem_name, module, revision);
CREATE INDEX IF NOT EXISTS idx_atlas_theorems_facet
  ON atlas_theorems(facet, lifecycle_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_atlas_theorems_status
  ON atlas_theorems(status, lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_atlas_theorems_proof_revision
  ON atlas_theorems(proof_repository, proof_revision);

CREATE TABLE IF NOT EXISTS atlas_facet_state (
  facet TEXT COLLATE NOCASE PRIMARY KEY
    REFERENCES atlas_facet_registry(facet) ON UPDATE CASCADE ON DELETE RESTRICT,
  proof_repository TEXT,
  proof_revision TEXT,
  atlas_revision TEXT,
  mathlib_revision TEXT,
  theorem_inventory TEXT,
  build_manifest_hash TEXT,
  state_schema_version INTEGER NOT NULL DEFAULT 1 CHECK(state_schema_version > 0),
  inventory_schema_version INTEGER NOT NULL DEFAULT 1 CHECK(inventory_schema_version > 0),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(facet <> '' AND facet COLLATE BINARY = lower(trim(facet))),
  CHECK(proof_repository IS NULL OR trim(proof_repository) <> ''),
  CHECK(proof_revision IS NULL OR trim(proof_revision) <> ''),
  CHECK(atlas_revision IS NULL OR trim(atlas_revision) <> ''),
  CHECK(mathlib_revision IS NULL OR trim(mathlib_revision) <> ''),
  CHECK(theorem_inventory IS NULL OR json_valid(theorem_inventory)),
  CHECK(build_manifest_hash IS NULL OR (
    length(build_manifest_hash) = 64 AND build_manifest_hash = lower(build_manifest_hash) AND
    build_manifest_hash NOT GLOB '*[^0-9a-f]*'
  ))
);

-- Ontology-bound literature hypotheses (migration 0012).
CREATE TABLE IF NOT EXISTS literature_hypotheses (
  -- TEXT PRIMARY KEY on a rowid table does not imply NOT NULL in SQLite/D1;
  -- declare it so the stable identifier can never be NULL.
  literature_hypothesis_id TEXT PRIMARY KEY NOT NULL,
  contract_json TEXT NOT NULL
    CHECK (json_valid(contract_json) AND json_type(contract_json) = 'object'),
  source_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.source')) STORED NOT NULL
    CHECK (json_type(contract_json, '$.source') = 'object'),
  claim_text TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.claim_text')) STORED NOT NULL
    CHECK (
      json_type(contract_json, '$.claim_text') = 'text'
      AND length(trim(
        claim_text,
        char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
      )) > 0
    ),
  bindings_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.bindings')) STORED NOT NULL
    CHECK (
      json_type(contract_json, '$.bindings') = 'object'
      AND json_type(contract_json, '$.bindings.errorTypes') = 'array'
      AND json_array_length(contract_json, '$.bindings.errorTypes') > 0
      AND json_type(contract_json, '$.bindings.materialClasses') = 'array'
      AND json_array_length(contract_json, '$.bindings.materialClasses') > 0
      AND json_type(contract_json, '$.bindings.chains') = 'array'
      AND json_array_length(contract_json, '$.bindings.chains') > 0
      AND json_type(contract_json, '$.bindings.acceptanceTests') = 'array'
      AND json_array_length(contract_json, '$.bindings.acceptanceTests') > 0
    ),
  epistemic_marker TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.epistemicMarker')) STORED NOT NULL
    CHECK (epistemic_marker IN ('OBS', 'INF', 'TRN', 'PRP', 'FRC')),
  readiness TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.readiness')) STORED NOT NULL
    CHECK (
    readiness IN ('H', 'M', 'L')
    OR (
      readiness GLOB '[HML] (*)'
      AND length(readiness) > 4
      AND substr(readiness, 4, length(readiness) - 4) NOT GLOB '*[()]*'
      AND trim(
        substr(readiness, 4, length(readiness) - 4),
        char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
      ) <> ''
    )
    ),
  confidence TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.confidence')) STORED NOT NULL
    CHECK (confidence IN ('High', 'Medium')),
  proposed_experiment_json TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.proposedExperiment')) STORED NOT NULL
    CHECK (json_type(contract_json, '$.proposedExperiment') = 'object'),
  proposed_experiment_predicate TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.proposedExperiment.predicate')) STORED NOT NULL
    CHECK (proposed_experiment_predicate IN ('barrier_mae_mev<=40')),
  status TEXT GENERATED ALWAYS AS
    (json_extract(contract_json, '$.status')) STORED NOT NULL
    CHECK (status IN ('proposed', 'accepted', 'rejected', 'superseded')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- D1 cannot execute JSON Schema directly. Mirror the structural parts that are
-- not expressible as column CHECK constraints in a reusable validation view.
CREATE VIEW IF NOT EXISTS literature_hypothesis_contract_validation AS
SELECT CAST(NULL AS TEXT) AS contract_json WHERE 0;

CREATE TRIGGER IF NOT EXISTS literature_hypothesis_contract_validate
INSTEAD OF INSERT ON literature_hypothesis_contract_validation
BEGIN
  SELECT CASE WHEN
    (SELECT count(*) FROM json_each(NEW.contract_json)) <> 8
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json)
      WHERE key NOT IN (
        'source', 'claim_text', 'bindings', 'epistemicMarker', 'readiness',
        'confidence', 'proposedExperiment', 'status'
      )
    )
  THEN RAISE(ABORT, 'invalid LiteratureHypothesis top-level contract') END;

  SELECT CASE WHEN
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.source')) <> 6
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.source')
      WHERE key NOT IN ('arxiv_id', 'openalex_id', 'ss_id', 'doi', 'url', 'asOf')
    )
    OR json_type(NEW.contract_json, '$.source.arxiv_id') NOT IN ('text', 'null')
    OR json_type(NEW.contract_json, '$.source.openalex_id') NOT IN ('text', 'null')
    OR json_type(NEW.contract_json, '$.source.ss_id') NOT IN ('text', 'null')
    OR json_type(NEW.contract_json, '$.source.doi') NOT IN ('text', 'null')
    OR json_type(NEW.contract_json, '$.source.url') <> 'text'
    OR json_type(NEW.contract_json, '$.source.asOf') <> 'text'
    OR (
      json_type(NEW.contract_json, '$.source.arxiv_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.openalex_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.ss_id') = 'null'
      AND json_type(NEW.contract_json, '$.source.doi') = 'null'
    )
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.source')
      WHERE type = 'text'
        AND length(trim(
          value,
          char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
        )) = 0
    )
    OR (
      json_type(NEW.contract_json, '$.source.doi') = 'text'
      AND (
        substr(json_extract(NEW.contract_json, '$.source.doi'), 1, 3) <> '10.'
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), '/') < 8
        OR length(substr(
          json_extract(NEW.contract_json, '$.source.doi'), 4,
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') - 4
        )) NOT BETWEEN 4 AND 9
        OR substr(
          json_extract(NEW.contract_json, '$.source.doi'), 4,
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') - 4
        ) GLOB '*[^0-9]*'
        OR length(substr(
          json_extract(NEW.contract_json, '$.source.doi'),
          instr(json_extract(NEW.contract_json, '$.source.doi'), '/') + 1
        )) = 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(9)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(10)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(11)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(12)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(13)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(28)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(29)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(30)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(31)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(32)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(133)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(160)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(5760)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8192)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8193)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8194)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8195)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8196)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8197)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8198)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8199)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8200)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8201)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8202)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8232)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8233)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8239)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(8287)) > 0
        OR instr(json_extract(NEW.contract_json, '$.source.doi'), char(12288)) > 0
      )
    )
    -- The JSON Schema also constrains source.url with format "uri". D1 cannot
    -- parse URIs, so reject the malformed shapes that pass a bare prefix
    -- check: empty host, whitespace/control characters, and bracketed
    -- IP-literal hosts (out of scope for provenance links).
    OR substr(json_extract(NEW.contract_json, '$.source.url'), 1, 8) <> 'https://'
    OR length(json_extract(NEW.contract_json, '$.source.url')) = 8
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(9)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(10)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(11)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(12)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(13)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(28)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(29)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(30)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(31)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(32)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(133)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(160)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(5760)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8192)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8193)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8194)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8195)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8196)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8197)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8198)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8199)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8200)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8201)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8202)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8232)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8233)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8239)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(8287)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), char(12288)) > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), '[') > 0
    OR instr(json_extract(NEW.contract_json, '$.source.url'), ']') > 0
    OR length(json_extract(NEW.contract_json, '$.source.asOf')) <> 10
    OR json_extract(NEW.contract_json, '$.source.asOf')
      GLOB '*[^0-9-]*'
    OR substr(json_extract(NEW.contract_json, '$.source.asOf'), 5, 1) <> '-'
    OR substr(json_extract(NEW.contract_json, '$.source.asOf'), 8, 1) <> '-'
    OR CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) < 1
    OR CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 6, 2) AS INTEGER)
      NOT BETWEEN 1 AND 12
    OR CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 9, 2) AS INTEGER)
      NOT BETWEEN 1 AND 31
    OR CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 9, 2) AS INTEGER) >
      CASE CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 6, 2) AS INTEGER)
        WHEN 2 THEN 28 + CASE WHEN
          CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 400 = 0
          OR (
            CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 4 = 0
            AND CAST(substr(json_extract(NEW.contract_json, '$.source.asOf'), 1, 4) AS INTEGER) % 100 <> 0
          )
        THEN 1 ELSE 0 END
        WHEN 4 THEN 30 WHEN 6 THEN 30 WHEN 9 THEN 30 WHEN 11 THEN 30
        ELSE 31
      END
  THEN RAISE(ABORT, 'invalid LiteratureHypothesis source') END;

  SELECT CASE WHEN
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings')) <> 4
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings')
      WHERE key NOT IN ('errorTypes', 'materialClasses', 'chains', 'acceptanceTests')
    )
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.errorTypes')
      WHERE type <> 'text' OR length(value) <> 2 OR substr(value, 1, 1) <> 'T'
        OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 7
        OR value <> printf('T%d', CAST(substr(value, 2) AS INTEGER))
    )
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.materialClasses')
      WHERE type <> 'text' OR length(value) <> 3 OR substr(value, 1, 2) <> 'MC'
        OR CAST(substr(value, 3) AS INTEGER) NOT BETWEEN 1 AND 9
        OR value <> printf('MC%d', CAST(substr(value, 3) AS INTEGER))
    )
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.chains')
      WHERE type <> 'text' OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 11
        OR value <> printf('C%d', CAST(substr(value, 2) AS INTEGER))
    )
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests')
      WHERE type <> 'text' OR CAST(substr(value, 2) AS INTEGER) NOT BETWEEN 1 AND 11
        OR value <> printf('Z%d', CAST(substr(value, 2) AS INTEGER))
    )
    OR (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.errorTypes'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.errorTypes'))
    OR (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.materialClasses'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.materialClasses'))
    OR (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.chains'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.chains'))
    OR (SELECT count(*) FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests'))
      <> (SELECT count(DISTINCT value) FROM json_each(NEW.contract_json, '$.bindings.acceptanceTests'))
  THEN RAISE(ABORT, 'invalid LiteratureHypothesis bindings') END;

  SELECT CASE WHEN
    (SELECT count(*) FROM json_each(NEW.contract_json, '$.proposedExperiment')) NOT IN (4, 5)
    OR EXISTS (
      SELECT 1 FROM json_each(NEW.contract_json, '$.proposedExperiment')
      WHERE key NOT IN (
        'metric', 'predicate', 'panel_ref', 'estimated_cells', 'estimated_gpu_hours'
      )
    )
    OR json_type(NEW.contract_json, '$.proposedExperiment.metric') IS NOT 'text'
    OR json_extract(NEW.contract_json, '$.proposedExperiment.metric') <> 'barrier_mae'
    OR json_type(NEW.contract_json, '$.proposedExperiment.predicate') IS NOT 'text'
    OR json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') IS NULL
    OR (
      json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') <> 'integer'
      AND NOT (
        json_type(NEW.contract_json, '$.proposedExperiment.estimated_cells') = 'real'
        AND json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells')
          = CAST(json_extract(
            NEW.contract_json, '$.proposedExperiment.estimated_cells'
          ) AS INTEGER)
      )
    )
    OR json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells') < 1
    OR json_extract(NEW.contract_json, '$.proposedExperiment.estimated_cells')
      > 9223372036854775807
    OR json_type(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours') IS NULL
    OR json_type(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours')
      NOT IN ('integer', 'real')
    OR json_extract(NEW.contract_json, '$.proposedExperiment.estimated_gpu_hours') < 0
    OR (
      json_type(NEW.contract_json, '$.proposedExperiment.panel_ref') IS NOT NULL
      AND (
        json_type(NEW.contract_json, '$.proposedExperiment.panel_ref') <> 'text'
        OR length(trim(
          json_extract(NEW.contract_json, '$.proposedExperiment.panel_ref'),
          char(9) || char(10) || char(11) || char(12) || char(13)
        || char(28) || char(29) || char(30) || char(31) || char(32)
        || char(133) || char(160) || char(5760) || char(8192) || char(8193)
        || char(8194) || char(8195) || char(8196) || char(8197) || char(8198)
        || char(8199) || char(8200) || char(8201) || char(8202) || char(8232)
        || char(8233) || char(8239) || char(8287) || char(12288)
        )) = 0
      )
    )
  THEN RAISE(ABORT, 'invalid LiteratureHypothesis proposedExperiment') END;
END;

CREATE TRIGGER IF NOT EXISTS literature_hypotheses_contract_insert
BEFORE INSERT ON literature_hypotheses
BEGIN
  INSERT INTO literature_hypothesis_contract_validation (contract_json)
  VALUES (NEW.contract_json);
END;

CREATE TRIGGER IF NOT EXISTS literature_hypotheses_contract_update
BEFORE UPDATE OF contract_json ON literature_hypotheses
BEGIN
  INSERT INTO literature_hypothesis_contract_validation (contract_json)
  VALUES (NEW.contract_json);
END;

CREATE INDEX IF NOT EXISTS idx_literature_hypotheses_status
  ON literature_hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_literature_hypotheses_readiness
  ON literature_hypotheses(readiness);
CREATE INDEX IF NOT EXISTS idx_literature_hypotheses_predicate
  ON literature_hypotheses(proposed_experiment_predicate);
