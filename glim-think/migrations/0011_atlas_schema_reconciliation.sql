-- Reconcile the permissive 0010 ATLAS tables with the durable theorem contract.
-- 0010 intentionally remains immutable: in production its tables were created
-- out of band before Wrangler recorded the migration. Its IF NOT EXISTS DDL can
-- therefore run first in both a new database and the production-shaped ledger.
--
-- Take a `wrangler d1 export` backup before applying: the preserved 0010 rows
-- are dropped at the end of this migration, so the export is the rollback copy.

-- Re-application guard. Wrangler records applied migrations in d1_migrations
-- and never runs this file twice; a *manual* re-application (d1 execute
-- --file) would otherwise rename the canonical tables away and then fail
-- partway, leaving the ledger without atlas_theorems. The marker row makes a
-- second application fail on its second statement, before anything is touched.
CREATE TABLE IF NOT EXISTS atlas_0011_reconciliation_applied (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO atlas_0011_reconciliation_applied (id) VALUES (1);

-- The 0010 indexes keep their names when their table is renamed. Remove them so
-- the canonical tables can recreate those names after the preserved-row copy.
DROP INDEX IF EXISTS idx_atlas_theorems_facet;
DROP INDEX IF EXISTS idx_atlas_theorems_status;
DROP INDEX IF EXISTS idx_atlas_theorems_identity;

ALTER TABLE atlas_theorems RENAME TO atlas_theorems_0010;
ALTER TABLE atlas_facet_state RENAME TO atlas_facet_state_0010;

-- Canonical facet names are lowercase. agent_class is the compatibility mapping
-- for the current runtime, whose getFacet() values are class-cased. The theorem
-- foreign-key columns use NOCASE so existing reads for "Experiment" continue to
-- resolve canonical "experiment" rows without duplicating facet identities.
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

-- Preserve any non-standard facet that predates the registry. It is normalized
-- once and registered under an explicit legacy mapping; new unknown facets are
-- rejected by the foreign key below.
INSERT OR IGNORE INTO atlas_facet_registry (facet, agent_class)
SELECT facet, 'Legacy:' || facet
FROM (
  SELECT CASE
           WHEN trim(facet) = '' THEN 'legacy-unknown'
           ELSE lower(trim(facet))
         END AS facet
  FROM atlas_theorems_0010
  UNION
  SELECT CASE
           WHEN trim(facet) = '' THEN 'legacy-unknown'
           ELSE lower(trim(facet))
         END AS facet
  FROM atlas_facet_state_0010
)
ORDER BY facet;

CREATE TABLE IF NOT EXISTS atlas_theorems (
  id INTEGER PRIMARY KEY,
  facet TEXT COLLATE NOCASE NOT NULL
    REFERENCES atlas_facet_registry(facet) ON UPDATE CASCADE ON DELETE RESTRICT,
  theorem_name TEXT NOT NULL CHECK(trim(theorem_name) <> ''),
  module TEXT NOT NULL CHECK(trim(module) <> ''),

  -- `revision` is retained as the write-compatible identity revision used by
  -- 0010 readers and seed scripts. New local proofs additionally identify their
  -- own repository/revision, independently of ATLAS and Mathlib dependency pins.
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
    length(statement_hash) = 64 AND
    statement_hash = lower(statement_hash) AND
    statement_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(source_hash IS NULL OR (
    length(source_hash) = 64 AND
    source_hash = lower(source_hash) AND
    source_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(build_manifest_hash IS NULL OR (
    length(build_manifest_hash) = 64 AND
    build_manifest_hash = lower(build_manifest_hash) AND
    build_manifest_hash NOT GLOB '*[^0-9a-f]*'
  )),
  CHECK(
    (lifecycle_status = 'superseded' AND superseded_by_id IS NOT NULL) OR
    (lifecycle_status IN ('active','retired') AND superseded_by_id IS NULL)
  )
);

INSERT INTO atlas_theorems (
  id,
  facet,
  theorem_name,
  module,
  revision,
  proof_repository,
  proof_revision,
  atlas_revision,
  mathlib_revision,
  statement_hash,
  source_hash,
  build_manifest_hash,
  status,
  lifecycle_status,
  superseded_by_id,
  used_in_hypotheses,
  created_at,
  updated_at
)
SELECT
  id,
  CASE WHEN trim(facet) = '' THEN 'legacy-unknown' ELSE lower(trim(facet)) END,
  theorem_name,
  module,
  revision,
  CASE
    WHEN module LIKE 'Atlas.%' OR module LIKE 'Atlas/%'
      THEN 'facebookresearch/atlas-lean'
    ELSE 'lupine-science/open-distillation-factory'
  END,
  CASE
    WHEN module LIKE 'Atlas.%' OR module LIKE 'Atlas/%' THEN revision
    ELSE NULL
  END,
  revision,
  NULL,
  NULL,
  NULL,
  NULL,
  COALESCE(status, 'imported'),
  'active',
  NULL,
  COALESCE(used_in_hypotheses, 0),
  COALESCE(created_at, CURRENT_TIMESTAMP),
  COALESCE(created_at, CURRENT_TIMESTAMP)
FROM atlas_theorems_0010;

-- Preserve the 0010 conflict target so existing INSERT OR IGNORE producers stay
-- idempotent and newer producers can use ON CONFLICT ... DO UPDATE transitions.
CREATE UNIQUE INDEX idx_atlas_theorems_identity
  ON atlas_theorems(facet, theorem_name, module, revision);
CREATE INDEX idx_atlas_theorems_facet
  ON atlas_theorems(facet, lifecycle_status, created_at DESC);
CREATE INDEX idx_atlas_theorems_status
  ON atlas_theorems(status, lifecycle_status);
CREATE INDEX idx_atlas_theorems_proof_revision
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
    length(build_manifest_hash) = 64 AND
    build_manifest_hash = lower(build_manifest_hash) AND
    build_manifest_hash NOT GLOB '*[^0-9a-f]*'
  ))
);

INSERT INTO atlas_facet_state (
  facet,
  proof_repository,
  proof_revision,
  atlas_revision,
  mathlib_revision,
  theorem_inventory,
  build_manifest_hash,
  state_schema_version,
  inventory_schema_version,
  updated_at
)
SELECT
  CASE WHEN trim(facet) = '' THEN 'legacy-unknown' ELSE lower(trim(facet)) END,
  NULL,
  NULL,
  atlas_revision,
  mathlib_revision,
  theorem_inventory,
  NULL,
  1,
  1,
  COALESCE(updated_at, CURRENT_TIMESTAMP)
FROM atlas_facet_state_0010;

DROP TABLE IF EXISTS atlas_facet_state_0010;
DROP TABLE IF EXISTS atlas_theorems_0010;
