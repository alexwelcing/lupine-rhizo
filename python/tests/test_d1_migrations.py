"""Contract tests for the D1 claim/evidence schema migrations."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "glim-think" / "migrations"
EXPECTED_TABLES = {
    "campaign",
    "campaign_hypothesis",
    "measurement",
    "calibration",
    "evidence_bundle",
    "evidence_artifact",
    "claim",
    "claim_version",
    "premise",
    "claim_premise",
    "premise_evidence",
    "theorem_binding",
    "runtime_gate_binding",
    "publication_binding",
    "status_event",
    "registry_snapshot",
    "literature_hypotheses",
    "literature_reprioritization_queue",
}


def apply_migrations(connection: sqlite3.Connection) -> None:
    paths = sorted(MIGRATIONS.glob("*.sql"))
    if not paths:
        raise AssertionError("no D1 migrations found")
    connection.execute("PRAGMA foreign_keys = ON")
    for path in paths:
        connection.executescript(path.read_text(encoding="utf-8"))


def seed_claim_version(connection: sqlite3.Connection, *, activated: bool = False) -> None:
    connection.execute("INSERT INTO claim (claim_id) VALUES ('claim.alpha')")
    connection.execute(
        """
        INSERT INTO claim_version (
          claim_version_id, claim_id, version, statement, intent, outcome,
          assurance, strength, content_hash, activated_at
        ) VALUES (?, 'claim.alpha', 1, 'Alpha is supported.', 'confirmatory',
                  'supported', 'active', 'predictive', ?, ?)
        """,
        (
            "claim.alpha.v1",
            "sha256:" + "a" * 64,
            "2026-07-16T00:00:00Z" if activated else None,
        ),
    )


class D1MigrationContractTests(unittest.TestCase):
    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def test_blank_database_creates_complete_schema(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertTrue(EXPECTED_TABLES <= tables)
        self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone(), (1,))

    def test_production_shaped_database_keeps_legacy_tables_and_is_idempotent(self) -> None:
        connection = self.connect()
        connection.executescript(
            """
            CREATE TABLE records (record_id TEXT PRIMARY KEY, payload TEXT);
            CREATE TABLE claims (
              claim_id TEXT PRIMARY KEY,
              agent_id TEXT,
              claim_type TEXT,
              evidence_ids TEXT,
              confidence REAL,
              status TEXT,
              timestamp TEXT,
              description TEXT
            );
            INSERT INTO records VALUES ('existing-record', '{}');
            INSERT INTO claims VALUES ('legacy-claim', NULL, NULL, NULL, NULL, 'verified', '2026-01-01T00:00:00Z', NULL);
            """
        )
        apply_migrations(connection)
        self.assertEqual(
            connection.execute("SELECT payload FROM records").fetchone(), ("{}",)
        )
        self.assertEqual(
            connection.execute("SELECT status FROM claims").fetchone(), ("verified",)
        )

    def test_atlas_reconciliation_reapplication_preserves_canonical_state(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        connection.execute(
            """
            INSERT INTO atlas_theorems (
              id, facet, theorem_name, module, revision, proof_repository,
              proof_revision, atlas_revision, mathlib_revision, statement_hash,
              source_hash, build_manifest_hash, status, lifecycle_status,
              superseded_by_id, used_in_hypotheses, created_at, updated_at
            ) VALUES (
              101, 'causal', 'replacement', 'Lupine.Causal', 'identity-r2',
              'example/proofs', 'proof-r2', 'atlas-r2', 'mathlib-r2', ?, ?, ?,
              'verified', 'active', NULL, 7,
              '2026-07-17T01:02:03Z', '2026-07-18T04:05:06Z'
            )
            """,
            ("a" * 64, "b" * 64, "c" * 64),
        )
        connection.execute(
            """
            INSERT INTO atlas_theorems (
              id, facet, theorem_name, module, revision, proof_repository,
              proof_revision, atlas_revision, mathlib_revision, statement_hash,
              source_hash, build_manifest_hash, status, lifecycle_status,
              superseded_by_id, used_in_hypotheses, created_at, updated_at
            ) VALUES (
              100, 'causal', 'original', 'Lupine.Causal', 'identity-r1',
              'example/proofs', 'proof-r1', 'atlas-r1', 'mathlib-r1', ?, ?, ?,
              'extended', 'superseded', 101, 3,
              '2026-07-16T01:02:03Z', '2026-07-18T03:04:05Z'
            )
            """,
            ("d" * 64, "e" * 64, "f" * 64),
        )
        connection.execute(
            """
            INSERT INTO atlas_facet_state (
              facet, proof_repository, proof_revision, atlas_revision,
              mathlib_revision, theorem_inventory, build_manifest_hash,
              state_schema_version, inventory_schema_version, updated_at
            ) VALUES (
              'causal', 'example/proofs', 'proof-r2', 'atlas-r2', 'mathlib-r2',
              '{"theorems":["original","replacement"]}', ?, 4, 5,
              '2026-07-18T06:07:08Z'
            )
            """,
            ("9" * 64,),
        )
        theorems_before = connection.execute(
            "SELECT * FROM atlas_theorems ORDER BY id"
        ).fetchall()
        facet_state_before = connection.execute(
            "SELECT * FROM atlas_facet_state ORDER BY facet"
        ).fetchall()

        reconciliation = MIGRATIONS / "0011_atlas_schema_reconciliation.sql"
        connection.executescript(reconciliation.read_text(encoding="utf-8"))

        self.assertEqual(
            connection.execute("SELECT * FROM atlas_theorems ORDER BY id").fetchall(),
            theorems_before,
        )
        self.assertEqual(
            connection.execute(
                "SELECT * FROM atlas_facet_state ORDER BY facet"
            ).fetchall(),
            facet_state_before,
        )
        self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_bootstrap_supports_full_contract_graph(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        connection.execute(
            "INSERT INTO campaign (campaign_id, version, preregistration_id, content_hash) "
            "VALUES ('campaign.round4', 1, 'prereg.round4', ?)",
            ("sha256:" + "b" * 64,),
        )
        connection.execute(
            "INSERT INTO campaign_hypothesis "
            "(campaign_hypothesis_id, campaign_id, hypothesis_id, statement, frozen) "
            "VALUES ('campaign.round4:h1', 'campaign.round4', 'h1', 'Frozen.', 1)"
        )
        connection.execute(
            "INSERT INTO measurement "
            "(measurement_id, campaign_id, run_id, metric, value, unit, measured_at) "
            "VALUES ('measurement.1', 'campaign.round4', 'run.1', 'mae', 0.1, 'fraction', '2026-07-16T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO calibration "
            "(calibration_id, campaign_id, method, parameters_json, source_measurement_id) "
            "VALUES ('calibration.1', 'campaign.round4', 'leave-one-out', '{}', 'measurement.1')"
        )
        connection.execute(
            "INSERT INTO evidence_bundle "
            "(bundle_id, claim_predicate, epistemic_status, scope_json, provenance_json) "
            "VALUES (?, 'alpha_supported', 'confirmatory', '{}', '{}')",
            ("sha256:" + "c" * 64,),
        )
        connection.execute(
            "INSERT INTO evidence_artifact "
            "(artifact_id, bundle_id, campaign_id, run_id, artifact_uri, artifact_hash, thresholds_version) "
            "VALUES ('artifact.1', ?, 'campaign.round4', 'run.1', 'artifacts/result.json', ?, 'v1')",
            ("sha256:" + "c" * 64, "sha256:" + "d" * 64),
        )
        seed_claim_version(connection)
        connection.execute(
            "INSERT INTO premise (premise_id, statement) VALUES ('premise.alpha', 'Evidence exists.')"
        )
        connection.execute(
            "INSERT INTO claim_premise (claim_version_id, premise_id, ordinal, support_mode) "
            "VALUES ('claim.alpha.v1', 'premise.alpha', 0, 'all')"
        )
        connection.execute(
            "INSERT INTO premise_evidence (claim_version_id, premise_id, bundle_id) "
            "VALUES ('claim.alpha.v1', 'premise.alpha', ?)",
            ("sha256:" + "c" * 64,),
        )
        connection.execute(
            "INSERT INTO theorem_binding "
            "(theorem_binding_id, claim_version_id, status, module, theorem_name) "
            "VALUES ('theorem.1', 'claim.alpha.v1', 'bound', 'Lupine.Alpha', 'alpha')"
        )
        connection.execute(
            "INSERT INTO runtime_gate_binding "
            "(runtime_gate_binding_id, claim_version_id, status, gate_id) "
            "VALUES ('gate-binding.1', 'claim.alpha.v1', 'bound', 'gate.alpha')"
        )
        connection.execute(
            "INSERT INTO publication_binding "
            "(publication_binding_id, claim_version_id, status, publication_id, recurring_claim) "
            "VALUES ('publication-binding.1', 'claim.alpha.v1', 'bound', 'paper.alpha', 'result.alpha')"
        )
        connection.execute(
            "INSERT INTO status_event "
            "(status_event_id, entity_type, entity_id, from_status, to_status, evidence_bundle_id, occurred_at) "
            "VALUES ('event.1', 'claim_version', 'claim.alpha.v1', 'eligible', 'active', ?, '2026-07-16T00:00:00Z')",
            ("sha256:" + "c" * 64,),
        )
        connection.execute(
            "INSERT INTO registry_snapshot (snapshot_id, content_hash, registry_json) VALUES ('snapshot.1', ?, '{}')",
            ("sha256:" + "e" * 64,),
        )
        connection.commit()

    def test_stable_ids_and_content_addresses_are_unique(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        connection.execute("INSERT INTO claim (claim_id) VALUES ('claim.alpha')")
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO claim (claim_id) VALUES ('claim.alpha')")
        seed_hash = "sha256:" + "a" * 64
        connection.execute(
            "INSERT INTO registry_snapshot (snapshot_id, content_hash, registry_json) VALUES ('s1', ?, '{}')",
            (seed_hash,),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO registry_snapshot (snapshot_id, content_hash, registry_json) VALUES ('s2', ?, '{}')",
                (seed_hash,),
            )

    def test_every_binding_and_recurring_claim_references_claim_version(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        invalid_rows = [
            (
                "INSERT INTO theorem_binding "
                "(theorem_binding_id, claim_version_id, status, reason) VALUES (?, ?, 'unsupported', 'none')",
                "theorem.invalid",
            ),
            (
                "INSERT INTO runtime_gate_binding "
                "(runtime_gate_binding_id, claim_version_id, status, reason) VALUES (?, ?, 'unsupported', 'none')",
                "gate.invalid",
            ),
            (
                "INSERT INTO publication_binding "
                "(publication_binding_id, claim_version_id, status, reason) VALUES (?, ?, 'unsupported', 'none')",
                "publication.invalid",
            ),
        ]
        for statement, binding_id in invalid_rows:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(statement, (binding_id, "claim.missing.v1"))
        seed_claim_version(connection)
        connection.execute(
            "INSERT INTO publication_binding "
            "(publication_binding_id, claim_version_id, status, publication_id, recurring_claim) "
            "VALUES ('publication.valid', 'claim.alpha.v1', 'bound', 'paper.alpha', 'result.alpha')"
        )
        self.assertEqual(
            connection.execute(
                "SELECT claim_version_id FROM publication_binding WHERE recurring_claim = 'result.alpha'"
            ).fetchone(),
            ("claim.alpha.v1",),
        )

    def test_activated_claim_version_and_contract_children_are_immutable(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        seed_claim_version(connection, activated=True)
        connection.execute(
            "INSERT INTO premise (premise_id, statement) VALUES ('premise.alpha', 'Evidence exists.')"
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "activated claim version is immutable"):
            connection.execute(
                "UPDATE claim_version SET statement = 'Changed.' WHERE claim_version_id = 'claim.alpha.v1'"
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "activated claim version is immutable"):
            connection.execute("DELETE FROM claim_version WHERE claim_version_id = 'claim.alpha.v1'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "activated claim version is immutable"):
            connection.execute(
                "INSERT INTO claim_premise (claim_version_id, premise_id, ordinal, support_mode) "
                "VALUES ('claim.alpha.v1', 'premise.alpha', 0, 'all')"
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "activated claim version is immutable"):
            connection.execute(
                "INSERT INTO runtime_gate_binding "
                "(runtime_gate_binding_id, claim_version_id, status, gate_id) "
                "VALUES ('gate.1', 'claim.alpha.v1', 'bound', 'gate.alpha')"
            )

    def test_activation_cannot_smuggle_a_content_change(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        seed_claim_version(connection)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "activation may only set activated_at"):
            connection.execute(
                "UPDATE claim_version SET activated_at = '2026-07-16T00:00:00Z', statement = 'Changed.' "
                "WHERE claim_version_id = 'claim.alpha.v1'"
            )
        connection.execute(
            "UPDATE claim_version SET activated_at = '2026-07-16T00:00:00Z' "
            "WHERE claim_version_id = 'claim.alpha.v1'"
        )

    def test_status_events_are_append_only(self) -> None:
        connection = self.connect()
        apply_migrations(connection)
        bundle_hash = "sha256:" + "c" * 64
        connection.execute(
            "INSERT INTO evidence_bundle "
            "(bundle_id, claim_predicate, epistemic_status, scope_json, provenance_json) "
            "VALUES (?, 'alpha_supported', 'confirmatory', '{}', '{}')",
            (bundle_hash,),
        )
        connection.execute(
            "INSERT INTO status_event "
            "(status_event_id, entity_type, entity_id, from_status, to_status, occurred_at) "
            "VALUES ('event.1', 'claim_version', 'claim.alpha.v1', NULL, 'unsupported', '2026-07-16T00:00:00Z')"
        )
        connection.execute(
            "INSERT INTO status_event "
            "(status_event_id, entity_type, entity_id, from_status, to_status, evidence_bundle_id, occurred_at) "
            "VALUES ('event.2', 'claim_version', 'claim.alpha.v1', 'unsupported', 'active', ?, '2026-07-16T00:00:01Z')",
            (bundle_hash,),
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "status_event is append-only"):
            connection.execute("UPDATE status_event SET to_status = 'active' WHERE status_event_id = 'event.1'")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "status_event is append-only"):
            connection.execute("DELETE FROM status_event WHERE status_event_id = 'event.1'")


if __name__ == "__main__":
    unittest.main()
