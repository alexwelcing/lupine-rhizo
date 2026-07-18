-- Reconcile the permissive 0010 ATLAS tables with the durable theorem contract.
-- 0010 intentionally remains immutable: in production its tables were created
-- out of band before Wrangler recorded the migration. Its IF NOT EXISTS DDL can
-- therefore run first in both a new database and the production-shaped ledger.
--
-- Take a `wrangler d1 export` backup before applying: the preserved 0010 rows
-- are dropped at the end of this migration, so the export is the rollback copy.

-- Manual re-application is supported as well as Wrangler's normal once-only
-- application. Canonical rows are mirrored into durable snapshots by triggers;
-- those snapshots let the legacy-shaped rebuild below restore every canonical
-- column without referring to columns that do not exist in the 0010 schema.
-- Foreign keys are disabled only for the table swap (a canonical source table
-- can contain self-referential supersession edges) and are re-enabled below.
PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS atlas_0011_reconciliation_applied (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO atlas_0011_reconciliation_applied (id) VALUES (1);

CREATE TABLE IF NOT EXISTS atlas_theorems_0011_canonical_snapshot (
  id INTEGER PRIMARY KEY,
  facet TEXT NOT NULL,
  theorem_name TEXT NOT NULL,
  module TEXT NOT NULL,
  revision TEXT NOT NULL,
  proof_repository TEXT NOT NULL,
  proof_revision TEXT,
  atlas_revision TEXT,
  mathlib_revision TEXT,
  statement_hash TEXT,
  source_hash TEXT,
  build_manifest_hash TEXT,
  status TEXT NOT NULL,
  lifecycle_status TEXT NOT NULL,
  superseded_by_id INTEGER,
  used_in_hypotheses INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS atlas_facet_state_0011_canonical_snapshot (
  facet TEXT COLLATE NOCASE PRIMARY KEY,
  proof_repository TEXT,
  proof_revision TEXT,
  atlas_revision TEXT,
  mathlib_revision TEXT,
  theorem_inventory TEXT,
  build_manifest_hash TEXT,
  state_schema_version INTEGER NOT NULL,
  inventory_schema_version INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

-- On re-application, stop mirroring before the canonical tables are renamed.
-- The snapshots now contain the exact pre-migration state.
DROP TRIGGER IF EXISTS atlas_theorems_0011_snapshot_insert;
DROP TRIGGER IF EXISTS atlas_theorems_0011_snapshot_update;
DROP TRIGGER IF EXISTS atlas_theorems_0011_snapshot_delete;
DROP TRIGGER IF EXISTS atlas_facet_state_0011_snapshot_insert;
DROP TRIGGER IF EXISTS atlas_facet_state_0011_snapshot_update;
DROP TRIGGER IF EXISTS atlas_facet_state_0011_snapshot_delete;

DROP TABLE IF EXISTS atlas_facet_state_0010;
DROP TABLE IF EXISTS atlas_theorems_0010;

-- The 0010 indexes keep their names when their table is renamed. Remove them so
-- the canonical tables can recreate those names after the preserved-row copy.
DROP INDEX IF EXISTS idx_atlas_theorems_facet;
DROP INDEX IF EXISTS idx_atlas_theorems_status;
DROP INDEX IF EXISTS idx_atlas_theorems_identity;
DROP INDEX IF EXISTS idx_atlas_theorems_proof_revision;

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

-- Empty on the first application; on later applications this restores every
-- canonical-only value, including supersession edges, after all target ids have
-- been inserted by the compatibility copy above.
INSERT INTO atlas_theorems (
  id, facet, theorem_name, module, revision, proof_repository, proof_revision,
  atlas_revision, mathlib_revision, statement_hash, source_hash,
  build_manifest_hash, status, lifecycle_status, superseded_by_id,
  used_in_hypotheses, created_at, updated_at
)
SELECT
  id, facet, theorem_name, module, revision, proof_repository, proof_revision,
  atlas_revision, mathlib_revision, statement_hash, source_hash,
  build_manifest_hash, status, lifecycle_status, superseded_by_id,
  used_in_hypotheses, created_at, updated_at
FROM atlas_theorems_0011_canonical_snapshot
WHERE true
ON CONFLICT(id) DO UPDATE SET
  facet = excluded.facet,
  theorem_name = excluded.theorem_name,
  module = excluded.module,
  revision = excluded.revision,
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  statement_hash = excluded.statement_hash,
  source_hash = excluded.source_hash,
  build_manifest_hash = excluded.build_manifest_hash,
  status = excluded.status,
  lifecycle_status = excluded.lifecycle_status,
  superseded_by_id = excluded.superseded_by_id,
  used_in_hypotheses = excluded.used_in_hypotheses,
  created_at = excluded.created_at,
  updated_at = excluded.updated_at;

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

INSERT INTO atlas_facet_state (
  facet, proof_repository, proof_revision, atlas_revision, mathlib_revision,
  theorem_inventory, build_manifest_hash, state_schema_version,
  inventory_schema_version, updated_at
)
SELECT
  facet, proof_repository, proof_revision, atlas_revision, mathlib_revision,
  theorem_inventory, build_manifest_hash, state_schema_version,
  inventory_schema_version, updated_at
FROM atlas_facet_state_0011_canonical_snapshot
WHERE true
ON CONFLICT(facet) DO UPDATE SET
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  theorem_inventory = excluded.theorem_inventory,
  build_manifest_hash = excluded.build_manifest_hash,
  state_schema_version = excluded.state_schema_version,
  inventory_schema_version = excluded.inventory_schema_version,
  updated_at = excluded.updated_at;

DROP TABLE IF EXISTS atlas_facet_state_0010;
DROP TABLE IF EXISTS atlas_theorems_0010;

-- Seed the snapshots on first application (and compact them to the exact live
-- rows on re-application), then keep them current for any subsequent writes.
DELETE FROM atlas_theorems_0011_canonical_snapshot;
INSERT INTO atlas_theorems_0011_canonical_snapshot
SELECT * FROM atlas_theorems;

DELETE FROM atlas_facet_state_0011_canonical_snapshot;
INSERT INTO atlas_facet_state_0011_canonical_snapshot
SELECT * FROM atlas_facet_state;

CREATE TRIGGER atlas_theorems_0011_snapshot_insert
AFTER INSERT ON atlas_theorems
BEGIN
  INSERT OR REPLACE INTO atlas_theorems_0011_canonical_snapshot
  VALUES (
    NEW.id, NEW.facet, NEW.theorem_name, NEW.module, NEW.revision,
    NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.statement_hash, NEW.source_hash,
    NEW.build_manifest_hash, NEW.status, NEW.lifecycle_status,
    NEW.superseded_by_id, NEW.used_in_hypotheses, NEW.created_at, NEW.updated_at
  );
END;

CREATE TRIGGER atlas_theorems_0011_snapshot_update
AFTER UPDATE ON atlas_theorems
BEGIN
  DELETE FROM atlas_theorems_0011_canonical_snapshot WHERE id = OLD.id;
  INSERT OR REPLACE INTO atlas_theorems_0011_canonical_snapshot
  VALUES (
    NEW.id, NEW.facet, NEW.theorem_name, NEW.module, NEW.revision,
    NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.statement_hash, NEW.source_hash,
    NEW.build_manifest_hash, NEW.status, NEW.lifecycle_status,
    NEW.superseded_by_id, NEW.used_in_hypotheses, NEW.created_at, NEW.updated_at
  );
END;

CREATE TRIGGER atlas_theorems_0011_snapshot_delete
AFTER DELETE ON atlas_theorems
BEGIN
  DELETE FROM atlas_theorems_0011_canonical_snapshot WHERE id = OLD.id;
END;

CREATE TRIGGER atlas_facet_state_0011_snapshot_insert
AFTER INSERT ON atlas_facet_state
BEGIN
  INSERT OR REPLACE INTO atlas_facet_state_0011_canonical_snapshot
  VALUES (
    NEW.facet, NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.theorem_inventory, NEW.build_manifest_hash,
    NEW.state_schema_version, NEW.inventory_schema_version, NEW.updated_at
  );
END;

CREATE TRIGGER atlas_facet_state_0011_snapshot_update
AFTER UPDATE ON atlas_facet_state
BEGIN
  DELETE FROM atlas_facet_state_0011_canonical_snapshot WHERE facet = OLD.facet;
  INSERT OR REPLACE INTO atlas_facet_state_0011_canonical_snapshot
  VALUES (
    NEW.facet, NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.theorem_inventory, NEW.build_manifest_hash,
    NEW.state_schema_version, NEW.inventory_schema_version, NEW.updated_at
  );
END;

CREATE TRIGGER atlas_facet_state_0011_snapshot_delete
AFTER DELETE ON atlas_facet_state
BEGIN
  DELETE FROM atlas_facet_state_0011_canonical_snapshot WHERE facet = OLD.facet;
END;

PRAGMA foreign_keys = ON;
