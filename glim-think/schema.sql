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
