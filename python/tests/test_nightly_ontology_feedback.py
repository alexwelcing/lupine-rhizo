"""Staging-cycle tests for nightly evidence-to-ontology feedback."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools.nightly_ontology_feedback import build_feedback_plan, render_feedback_sql
from tools.run_nightly_cycle import run_cycle

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "glim-think" / "migrations"
BUNDLE_A = "sha256:" + "a" * 64
BUNDLE_B = "sha256:" + "b" * 64


def apply_migrations(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    for path in sorted(MIGRATIONS.glob("*.sql")):
        connection.executescript(path.read_text(encoding="utf-8"))


def hypothesis(chain: str, acceptance: str, *, readiness: str = "L") -> dict:
    return {
        "source": {
            "arxiv_id": "2601.00001",
            "openalex_id": None,
            "ss_id": None,
            "doi": None,
            "url": "https://arxiv.org/abs/2601.00001",
            "asOf": "2026-08-01",
        },
        "claim_text": f"Test {chain} with dated, defined evidence.",
        "bindings": {
            "errorTypes": ["T2"],
            "materialClasses": ["MC4"],
            "chains": [chain],
            "acceptanceTests": [acceptance],
        },
        "epistemicMarker": "PRP",
        "readiness": readiness,
        "confidence": "Medium",
        "proposedExperiment": {
            "metric": "barrier_mae",
            "predicate": "barrier_mae_mev<=40",
            "estimated_cells": 4,
            "estimated_gpu_hours": 1,
        },
        "status": "proposed",
    }


def bundle(bundle_id: str, *, outcome: str, campaign: str, status: str) -> dict:
    return {
        "bundle_id": bundle_id,
        "claim_predicate": "barrier_mae_mev<=40",
        "epistemic_status": status,
        "scope": {"structures": ["fcc"], "chemistries": ["Ni"], "properties": ["barrier"], "conditions": {}},
        "evidence_refs": [
            {
                "campaign": campaign,
                "campaign_manifest": "campaigns/v1/staging.json",
                "campaign_manifest_hash": "sha256:" + "c" * 64,
                "run_id": f"run-{campaign}",
                "artifact": "data/staging.json",
                "artifact_hash": "sha256:" + "d" * 64,
                "thresholds_version": "v1",
            }
        ],
        "provenance": {
            "agent": "staging-runner",
            "human": "preregistered-fixture",
            "timestamp": "2026-08-01T01:00:00Z",
            "preregistration_id": "prereg.staging.v1",
        },
        "measurements": [
            {
                "metric": "barrier_mae",
                "value": 30 if outcome == "pass" else 70,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "less_than_or_equal",
                    "threshold": 40,
                    "outcome": outcome,
                },
                "sample_count": 4,
            }
        ],
        "supersedes": [],
    }


class NightlyFeedbackTests(unittest.TestCase):
    def test_runner_executes_ingest_assumption_and_runtime_gate_stages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            for name in ("registry", "evidence", "campaigns", "config"):
                source = ROOT / name
                if source.is_dir():
                    import shutil

                    shutil.copytree(source, root / name)
            import shutil

            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            shutil.copytree(
                ROOT / "python" / "tests" / "fixtures" / "round4_ingest",
                fixture,
            )
            output = root / "nightly-output"

            result = run_cycle(
                root=root,
                campaigns=[
                    {
                        "manifest": fixture / "manifest.json",
                        "measurements": fixture / "measurements.jsonl",
                    }
                ],
                output_dir=output,
            )

            self.assertEqual(len(result["ingested_bundle_ids"]), 2)
            self.assertTrue((output / "runtime-gates.json").is_file())
            self.assertTrue((output / "ingested-bundles.json").is_file())
            regenerated = json.loads((root / "registry" / "assumptions.v1.json").read_text())
            self.assertGreater(len(regenerated["assumptions"]), 0)

    def test_full_staging_cycle_supersedes_refuted_hypothesis_and_prioritizes_gap(self) -> None:
        atlas = {
            "discoveryChains": [
                {"id": "C1", "readiness": "L"},
                {"id": "C2", "readiness": "L"},
            ],
            "acceptanceTests": [
                {"id": "Z1", "chain": "C1"},
                {"id": "Z2", "chain": "C2"},
            ],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "refuted",
                    "evidence": [{"bundle_id": BUNDLE_A, "epistemic_status": "negative"}],
                }
            ]
        }
        hypotheses = [
            {"literature_hypothesis_id": "hyp.refuted", "contract_json": hypothesis("C1", "Z1")},
            {"literature_hypothesis_id": "hyp.gap", "contract_json": hypothesis("C2", "Z2")},
        ]
        evidence = {BUNDLE_A: bundle(BUNDLE_A, outcome="fail", campaign="c1", status="negative")}

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id=evidence,
            hypotheses=hypotheses,
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"][0]["hypothesis_id"], "hyp.refuted")
        self.assertEqual(plan["updates"][0]["to_status"], "superseded")
        self.assertEqual(plan["updates"][0]["evidence_bundle_id"], BUNDLE_A)
        self.assertEqual([row["hypothesis_id"] for row in plan["queue"]], ["hyp.gap"])
        self.assertEqual(plan["queue"][0]["chain_priority"], 2)
        self.assertIn("hyp.refuted", plan["digest_markdown"])
        self.assertIn("hyp.gap", plan["digest_markdown"])

    def test_fresh_bundle_is_synced_to_d1_even_without_a_hypothesis_transition(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "supported",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "confirmatory"}
                    ],
                }
            ]
        }
        evidence = {
            BUNDLE_A: bundle(
                BUNDLE_A,
                outcome="pass",
                campaign="one",
                status="confirmatory",
            )
        }

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id=evidence,
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.already-ready",
                    "contract_json": hypothesis("C1", "Z1", readiness="M"),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])
        self.assertEqual(
            [row["bundle_id"] for row in plan["evidence"]],
            [BUNDLE_A],
        )

    def test_readiness_requires_dated_defined_new_evidence_and_two_independent_demonstrations_for_h(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "supported",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "confirmatory"},
                        {"bundle_id": BUNDLE_B, "epistemic_status": "confirmatory"},
                    ],
                }
            ]
        }
        evidence = {
            BUNDLE_A: bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory"),
            BUNDLE_B: bundle(BUNDLE_B, outcome="pass", campaign="two", status="confirmatory"),
        }
        hypotheses = [
            {"literature_hypothesis_id": "hyp.ready", "contract_json": hypothesis("C1", "Z1")}
        ]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id=evidence,
            hypotheses=hypotheses,
            new_bundle_ids={BUNDLE_B},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"][0]["to_readiness"], "H")
        self.assertEqual(plan["updates"][0]["evidence_bundle_id"], BUNDLE_B)
        self.assertEqual(plan["queue"], [])

    def test_readiness_rejects_an_asserted_outcome_that_disagrees_with_the_measurement(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "supported",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "confirmatory"}
                    ],
                }
            ]
        }
        inconsistent = bundle(
            BUNDLE_A,
            outcome="pass",
            campaign="one",
            status="confirmatory",
        )
        inconsistent["measurements"][0]["value"] = 70

        with self.assertRaisesRegex(ValueError, "asserted acceptance outcome"):
            build_feedback_plan(
                atlas=atlas,
                assumptions=assumptions,
                evidence_by_id={BUNDLE_A: inconsistent},
                hypotheses=[
                    {
                        "literature_hypothesis_id": "hyp.inconsistent",
                        "contract_json": hypothesis("C1", "Z1"),
                    }
                ],
                new_bundle_ids={BUNDLE_A},
                as_of="2026-08-01",
            )

    def test_readiness_rejects_a_threshold_that_disagrees_with_the_bound_predicate(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "supported",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "confirmatory"}
                    ],
                }
            ]
        }
        inconsistent = bundle(
            BUNDLE_A,
            outcome="pass",
            campaign="one",
            status="confirmatory",
        )
        inconsistent["measurements"][0]["value"] = 70
        inconsistent["measurements"][0]["acceptance_test"]["threshold"] = 80

        with self.assertRaisesRegex(ValueError, "acceptance threshold"):
            build_feedback_plan(
                atlas=atlas,
                assumptions=assumptions,
                evidence_by_id={BUNDLE_A: inconsistent},
                hypotheses=[
                    {
                        "literature_hypothesis_id": "hyp.inconsistent-threshold",
                        "contract_json": hypothesis("C1", "Z1"),
                    }
                ],
                new_bundle_ids={BUNDLE_A},
                as_of="2026-08-01",
            )

    def test_workflow_rehydrates_and_persists_the_complete_nightly_corpus(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "evidence-nightly.yml").read_text()

        restore = workflow.index("Rehydrate durable ontology corpus")
        ingest = workflow.index("Ingest rows and regenerate assumptions plus runtime gate")
        apply_feedback = workflow.index("Apply feedback to production D1")
        persist = workflow.index("Persist durable ontology corpus")
        self.assertLess(restore, ingest)
        self.assertLess(apply_feedback, persist)
        self.assertIn("registry/claims", workflow)
        self.assertIn("evidence/v1/examples", workflow)
        self.assertIn("ontology-state/$CYCLE_DATE/corpus-", workflow)
        self.assertIn("printf '%020d' \"$GITHUB_RUN_ID\"", workflow)
        self.assertIn("tar -xzf nightly-state/corpus.tar.gz -C nightly-state/restored", workflow)
        self.assertIn("rm -rf registry/claims evidence/v1/examples", workflow)

    def test_d1_status_change_fails_closed_without_fresh_bundle_event(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        apply_migrations(connection)
        original = hypothesis("C1", "Z1")
        connection.execute(
            "INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json) VALUES (?, ?)",
            ("hyp.one", json.dumps(original, separators=(",", ":"), sort_keys=True)),
        )
        changed = {**original, "status": "superseded"}

        with self.assertRaisesRegex(sqlite3.IntegrityError, "new EvidenceBundle"):
            connection.execute(
                "UPDATE literature_hypotheses SET contract_json = ? WHERE literature_hypothesis_id = ?",
                (json.dumps(changed, separators=(",", ":"), sort_keys=True), "hyp.one"),
            )

        evidence = bundle(BUNDLE_A, outcome="fail", campaign="one", status="negative")
        plan = {
            "as_of": "2026-08-01",
            "updates": [
                {
                    "hypothesis_id": "hyp.one",
                    "from_status": "proposed",
                    "to_status": "superseded",
                    "from_readiness": "L",
                    "to_readiness": "L",
                    "evidence_bundle_id": BUNDLE_A,
                    "contract_json": changed,
                }
            ],
            "queue": [],
            "evidence": [evidence],
        }
        connection.executescript(render_feedback_sql(plan))
        self.assertEqual(
            connection.execute("SELECT status FROM literature_hypotheses WHERE literature_hypothesis_id = 'hyp.one'").fetchone(),
            ("superseded",),
        )
        event = connection.execute(
            "SELECT evidence_bundle_id FROM status_event WHERE entity_type = 'literature_hypothesis'"
        ).fetchone()
        self.assertEqual(event, (BUNDLE_A,))

        changed_readiness = {**changed, "readiness": "H"}
        with self.assertRaisesRegex(sqlite3.IntegrityError, "new EvidenceBundle"):
            connection.execute(
                "UPDATE literature_hypotheses SET contract_json = ? WHERE literature_hypothesis_id = ?",
                (
                    json.dumps(changed_readiness, separators=(",", ":"), sort_keys=True),
                    "hyp.one",
                ),
            )

    def test_d1_guard_cannot_reuse_an_old_event_when_a_transition_repeats(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        apply_migrations(connection)
        proposed = hypothesis("C1", "Z1")
        accepted = {**proposed, "status": "accepted"}
        connection.execute(
            "INSERT INTO literature_hypotheses (literature_hypothesis_id, contract_json) VALUES (?, ?)",
            ("hyp.replay", json.dumps(proposed, separators=(",", ":"), sort_keys=True)),
        )

        def transition(
            *,
            from_contract: dict,
            to_contract: dict,
            evidence: dict,
            as_of: str,
        ) -> None:
            connection.executescript(
                render_feedback_sql(
                    {
                        "as_of": as_of,
                        "updates": [
                            {
                                "hypothesis_id": "hyp.replay",
                                "from_status": from_contract["status"],
                                "to_status": to_contract["status"],
                                "from_readiness": from_contract["readiness"],
                                "to_readiness": to_contract["readiness"],
                                "evidence_bundle_id": evidence["bundle_id"],
                                "contract_json": to_contract,
                            }
                        ],
                        "queue": [],
                        "evidence": [evidence],
                    }
                )
            )

        transition(
            from_contract=proposed,
            to_contract=accepted,
            evidence=bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory"),
            as_of="2026-08-01",
        )
        transition(
            from_contract=accepted,
            to_contract=proposed,
            evidence=bundle(BUNDLE_B, outcome="fail", campaign="two", status="negative"),
            as_of="2026-08-02",
        )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "new EvidenceBundle"):
            connection.execute(
                "UPDATE literature_hypotheses SET contract_json = ? WHERE literature_hypothesis_id = ?",
                (
                    json.dumps(accepted, separators=(",", ":"), sort_keys=True),
                    "hyp.replay",
                ),
            )

    def test_0014_replaces_the_trigger_on_an_already_migrated_database(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("PRAGMA foreign_keys = ON")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name >= "0014_":
                continue
            connection.executescript(path.read_text(encoding="utf-8"))
        before = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            ("literature_hypothesis_evidence_guard",),
        ).fetchone()[0]
        self.assertNotIn("max(latest.rowid)", before)

        migration = MIGRATIONS / "0014_nightly_ontology_event_freshness.sql"
        connection.executescript(migration.read_text(encoding="utf-8"))
        after = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            ("literature_hypothesis_evidence_guard",),
        ).fetchone()[0]
        self.assertIn("max(latest.rowid)", after)


if __name__ == "__main__":
    unittest.main()
