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


if __name__ == "__main__":
    unittest.main()
