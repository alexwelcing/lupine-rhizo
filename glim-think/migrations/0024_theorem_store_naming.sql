-- Name Rhizo's shared proof store independently of upstream libraries.
-- Historical migrations 0010 and 0011 remain unchanged. This once-only
-- migration renames their live tables and reconciliation snapshots in place,
-- preserving row ids, self-referential supersession edges, hashes and pins.
-- atlas_revision continues to identify the external Meta ATLAS-Lean dependency.
--
-- ALTER TABLE updates foreign-key references without rebuilding any rows.
-- Snapshot trigger and index names are recreated because SQLite's table rename
-- updates their SQL bodies but retains their original object names.

DROP TRIGGER atlas_theorems_0011_snapshot_insert;
DROP TRIGGER atlas_theorems_0011_snapshot_update;
DROP TRIGGER atlas_theorems_0011_snapshot_delete;
DROP TRIGGER atlas_facet_state_0011_snapshot_insert;
DROP TRIGGER atlas_facet_state_0011_snapshot_update;
DROP TRIGGER atlas_facet_state_0011_snapshot_delete;

ALTER TABLE atlas_facet_registry RENAME TO facet_registry;
ALTER TABLE atlas_theorems RENAME TO theorems;
ALTER TABLE atlas_facet_state RENAME TO facet_state;
ALTER TABLE atlas_theorems_0011_canonical_snapshot RENAME TO theorems_0011_canonical_snapshot;
ALTER TABLE atlas_facet_state_0011_canonical_snapshot RENAME TO facet_state_0011_canonical_snapshot;
ALTER TABLE atlas_0011_reconciliation_applied RENAME TO theorems_0011_reconciliation_applied;

DROP INDEX idx_atlas_theorems_identity;
DROP INDEX idx_atlas_theorems_facet;
DROP INDEX idx_atlas_theorems_status;
DROP INDEX idx_atlas_theorems_proof_revision;

CREATE UNIQUE INDEX idx_theorems_identity
  ON theorems(facet, theorem_name, module, revision);
CREATE INDEX idx_theorems_facet
  ON theorems(facet, lifecycle_status, created_at DESC);
CREATE INDEX idx_theorems_status
  ON theorems(status, lifecycle_status);
CREATE INDEX idx_theorems_proof_revision
  ON theorems(proof_repository, proof_revision);

CREATE TRIGGER theorems_0011_snapshot_insert
AFTER INSERT ON theorems
BEGIN
  INSERT OR REPLACE INTO theorems_0011_canonical_snapshot
  VALUES (
    NEW.id, NEW.facet, NEW.theorem_name, NEW.module, NEW.revision,
    NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.statement_hash, NEW.source_hash,
    NEW.build_manifest_hash, NEW.status, NEW.lifecycle_status,
    NEW.superseded_by_id, NEW.used_in_hypotheses, NEW.created_at, NEW.updated_at
  );
END;

CREATE TRIGGER theorems_0011_snapshot_update
AFTER UPDATE ON theorems
BEGIN
  DELETE FROM theorems_0011_canonical_snapshot WHERE id = OLD.id;
  INSERT OR REPLACE INTO theorems_0011_canonical_snapshot
  VALUES (
    NEW.id, NEW.facet, NEW.theorem_name, NEW.module, NEW.revision,
    NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.statement_hash, NEW.source_hash,
    NEW.build_manifest_hash, NEW.status, NEW.lifecycle_status,
    NEW.superseded_by_id, NEW.used_in_hypotheses, NEW.created_at, NEW.updated_at
  );
END;

CREATE TRIGGER theorems_0011_snapshot_delete
AFTER DELETE ON theorems
BEGIN
  DELETE FROM theorems_0011_canonical_snapshot WHERE id = OLD.id;
END;

CREATE TRIGGER facet_state_0011_snapshot_insert
AFTER INSERT ON facet_state
BEGIN
  INSERT OR REPLACE INTO facet_state_0011_canonical_snapshot
  VALUES (
    NEW.facet, NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.theorem_inventory, NEW.build_manifest_hash,
    NEW.state_schema_version, NEW.inventory_schema_version, NEW.updated_at
  );
END;

CREATE TRIGGER facet_state_0011_snapshot_update
AFTER UPDATE ON facet_state
BEGIN
  DELETE FROM facet_state_0011_canonical_snapshot WHERE facet = OLD.facet;
  INSERT OR REPLACE INTO facet_state_0011_canonical_snapshot
  VALUES (
    NEW.facet, NEW.proof_repository, NEW.proof_revision, NEW.atlas_revision,
    NEW.mathlib_revision, NEW.theorem_inventory, NEW.build_manifest_hash,
    NEW.state_schema_version, NEW.inventory_schema_version, NEW.updated_at
  );
END;

CREATE TRIGGER facet_state_0011_snapshot_delete
AFTER DELETE ON facet_state
BEGIN
  DELETE FROM facet_state_0011_canonical_snapshot WHERE facet = OLD.facet;
END;

