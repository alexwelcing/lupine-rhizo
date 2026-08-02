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


def hypothesis(
    chain: str,
    acceptance: str,
    *,
    readiness: str = "L",
    metric: str = "barrier_mae",
    predicate: str = "barrier_mae_mev<=40",
) -> dict:
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
            "metric": metric,
            "predicate": predicate,
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
            self.assertGreater(
                len(result["sync_candidate_bundle_ids"]),
                len(result["ingested_bundle_ids"]),
            )
            self.assertTrue(
                set(result["ingested_bundle_ids"]).issubset(
                    result["sync_candidate_bundle_ids"]
                )
            )
            self.assertTrue((output / "runtime-gates.json").is_file())
            self.assertTrue((output / "ingested-bundles.json").is_file())
            self.assertTrue((output / "sync-candidates.json").is_file())
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

    def test_dated_untyped_negative_bundle_supersedes_refuted_hypothesis(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "refuted",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "negative"}
                    ],
                }
            ]
        }
        negative = bundle(
            BUNDLE_A,
            outcome="fail",
            campaign="one",
            status="negative",
        )
        del negative["measurements"]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: negative},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.untyped-negative",
                    "contract_json": hypothesis("C1", "Z1"),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(len(plan["updates"]), 1)
        self.assertEqual(plan["updates"][0]["to_status"], "superseded")
        self.assertEqual(plan["updates"][0]["evidence_bundle_id"], BUNDLE_A)

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

    def test_sign_skew_bundle_yields_typed_outcomes_without_promoting_barrier_predicate(self) -> None:
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.9545,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 400,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "less_than_or_equal",
                    "threshold": 600,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
        ]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: skew},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.sign-skew",
                    "contract_json": hypothesis("C1", "Z1"),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        # The skew receipt is dated and defined, but it must not count as a passing
        # barrier_mae_mev<=40 demonstration for the bound hypothesis.
        self.assertEqual(plan["updates"], [])

    def test_sign_skew_bundle_rejects_an_asserted_outcome_that_disagrees(self) -> None:
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.4,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            }
        ]

        with self.assertRaisesRegex(ValueError, "asserted acceptance outcome"):
            build_feedback_plan(
                atlas=atlas,
                assumptions=assumptions,
                evidence_by_id={BUNDLE_A: skew},
                hypotheses=[
                    {
                        "literature_hypothesis_id": "hyp.sign-skew-inconsistent",
                        "contract_json": hypothesis("C1", "Z1"),
                    }
                ],
                new_bundle_ids={BUNDLE_A},
                as_of="2026-08-01",
            )

    def test_negative_barrier_receipt_does_not_supersede_the_sign_skew_hypothesis(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "refuted",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "negative"}
                    ],
                }
            ]
        }
        negative = bundle(BUNDLE_A, outcome="fail", campaign="one", status="negative")
        del negative["measurements"]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: negative},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.cross-predicate-negative",
                    "contract_json": hypothesis(
                        "C1",
                        "Z1",
                        metric="signed_error_positive",
                        predicate="signed_error_positive_fraction>0.5",
                    ),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])

    def test_h_readiness_counts_distinct_dataset_fingerprints_not_campaigns(self, tmp_path=None) -> None:
        import tempfile

        import tools.nightly_ontology_feedback as feedback_module

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        artifact_root = Path(temporary.name)
        original_root = feedback_module._REPO_ROOT
        self.addCleanup(setattr, feedback_module, "_REPO_ROOT", original_root)
        feedback_module._REPO_ROOT = artifact_root
        manifest_dir = artifact_root / "campaigns" / "v1"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "staging.json").write_text(
            json.dumps(
                {
                    "available_models": [
                        {"model_id": model}
                        for model in ("chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium")
                    ]
                }
            )
        )
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

        def write_artifact(name: str, value: float) -> str:
            rows = [
                {
                    "path_index": index,
                    "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                    "model": model,
                    "status": "measured",
                    "signed_error_mev": value,
                }
                for index in range(22)
                for model in ("chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium")
            ]
            (artifact_root / name).write_text(json.dumps({"per_row": rows}))
            return feedback_module._artifact_fingerprint(artifact_root / name)

        import hashlib as _hashlib

        def write_manifest(name: str, value: float, campaign_id: str) -> tuple[str, str]:
            models = ("chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium")
            locked_source = {
                "per_path": [
                    {
                        "path_index": index,
                        "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                        "per_model": {
                            model: {"vasp_signed_error_mev": value, "complete": True}
                            for model in models
                        },
                        "models_missing": {},
                    }
                    for index in range(22)
                ]
            }
            locked_bytes = json.dumps(locked_source).encode()
            (artifact_root / f"locked-{name}").write_bytes(locked_bytes)
            panel_bytes = json.dumps(
                {"paths": [{"path_id": f"mp-{1000 + index}_0_0_0_0_0"} for index in range(22)]}
            ).encode()
            (artifact_root / f"panel-{name}").write_bytes(panel_bytes)
            document = {
                "campaign_id": campaign_id,
                "acceptance_test": {
                    "metric": "signed_error_positive",
                    "operator": "gt",
                    "threshold": 0.5,
                    "unit": "fraction",
                },
                "execution": {
                    "candidate_panel": {
                        "path": f"panel-{name}",
                        "sha256": "sha256:" + _hashlib.sha256(panel_bytes).hexdigest(),
                    }
                },
                "available_models": [
                        {
                            "model_id": model,
                            "artifact_hash": {
                                "chgnet": "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890",
                                "mace-mp-small": "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694",
                                "mace-mp-medium": "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3",
                                "mace-mpa-0-medium": "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9",
                            }[model],
                            "version": {
                                "chgnet": "chgnet 0.4.2",
                                "mace-mp-small": "mace-torch 0.3.16 / small",
                                "mace-mp-medium": "mace-torch 0.3.16 / medium",
                                "mace-mpa-0-medium": "mace-torch 0.3.16 / mpa-0 medium",
                            }[model],
                        }
                        for model in models
                    ],
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": f"locked-{name}",
                            "sha256": "sha256:" + _hashlib.sha256(locked_bytes).hexdigest(),
                        }
                    ]
                },
            }
            payload = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
            document["content_hash"] = "sha256:" + _hashlib.sha256(payload).hexdigest()
            raw = json.dumps(document).encode()
            manifest_dir = artifact_root / "campaigns" / "v1"
            manifest_dir.mkdir(parents=True, exist_ok=True)
            (manifest_dir / name).write_bytes(raw)
            registry_file = artifact_root / "registry" / "campaigns.v1.json"
            registry_file.parent.mkdir(parents=True, exist_ok=True)
            registry = (
                json.loads(registry_file.read_text())
                if registry_file.exists()
                else {"campaigns": []}
            )
            registry["campaigns"].append(
                {"campaign_id": campaign_id, "content_hash": document["content_hash"]}
            )
            registry_file.write_text(json.dumps(registry))
            return f"campaigns/v1/{name}", "sha256:" + _hashlib.sha256(raw).hexdigest()

        manifest_one, manifest_one_hash = write_manifest("staging-one.json", 500.0, "campaign-one")
        manifest_two, manifest_two_hash = write_manifest("staging-two.json", 520.0, "campaign-two")

        def skew(bundle_id: str, campaign: str, fingerprint: str, artifact_name: str, median: float, manifest: str = "", manifest_hash: str = "") -> dict:
            receipt = bundle(BUNDLE_A, outcome="pass", campaign=campaign, status="confirmatory")
            receipt["bundle_id"] = bundle_id
            receipt["claim_predicate"] = "signed_error_positive_fraction>0.5"
            receipt["evidence_refs"][0]["artifact"] = artifact_name
            receipt["evidence_refs"][0]["artifact_hash"] = (
                "sha256:" + _hashlib.sha256((artifact_root / artifact_name).read_bytes()).hexdigest()
            )
            if manifest:
                receipt["evidence_refs"][0]["campaign_manifest"] = manifest
                receipt["evidence_refs"][0]["campaign_manifest_hash"] = manifest_hash
            receipt["measurements"] = [
                {
                    "metric": "signed_error_positive",
                    "value": 1.0,
                    "unit": "fraction",
                    "acceptance_test": {"comparator": "greater_than", "threshold": 0.5, "outcome": "pass"},
                    "sample_count": 22,
                },
                {
                    "metric": "median_signed_error",
                    "value": median,
                    "unit": "meV",
                    "acceptance_test": {"comparator": "greater_than_or_equal", "threshold": 400, "outcome": "pass"},
                    "sample_count": 22,
                },
                {
                    "metric": "median_signed_error",
                    "value": median,
                    "unit": "meV",
                    "acceptance_test": {"comparator": "less_than_or_equal", "threshold": 600, "outcome": "pass"},
                    "sample_count": 22,
                },
            ]
            receipt["evidence_refs"][0]["dataset_fingerprint"] = fingerprint
            return receipt

        fingerprint_one = write_artifact("art-one.json", 500.0)
        fingerprint_two = write_artifact("art-two.json", 520.0)

        hypothesis_row = {
            "literature_hypothesis_id": "hyp.sign-skew-h-grade",
            "contract_json": hypothesis(
                "C1", "Z1", readiness="M",
                metric="signed_error_positive",
                predicate="signed_error_positive_fraction>0.5",
            ),
        }
        same_dataset = {
            BUNDLE_A: skew(BUNDLE_A, "campaign-one", fingerprint_one, "art-one.json", 500.0, manifest_one, manifest_one_hash),
            BUNDLE_B: skew(BUNDLE_B, "campaign-two", fingerprint_one, "art-one.json", 500.0, manifest_one, manifest_one_hash),
        }
        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id=same_dataset,
            hypotheses=[hypothesis_row],
            new_bundle_ids={BUNDLE_A, BUNDLE_B},
            as_of="2026-08-01",
        )
        self.assertEqual(plan["updates"], [])

        two_refs_one_bundle = skew(BUNDLE_A, "campaign-one", fingerprint_one, "art-one.json", 500.0, manifest_one, manifest_one_hash)
        two_refs_one_bundle["evidence_refs"].append(
            dict(two_refs_one_bundle["evidence_refs"][0], dataset_fingerprint=fingerprint_two)
        )
        single_bundle_assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "supported",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "confirmatory"},
                    ],
                }
            ]
        }
        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=single_bundle_assumptions,
            evidence_by_id={BUNDLE_A: two_refs_one_bundle},
            hypotheses=[hypothesis_row],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )
        self.assertEqual(plan["updates"], [])

        duplicated_artifact = artifact_root / "art-dupe.json"
        duplicated_artifact.write_text(
            json.dumps(
                {
                    "per_row": [
                        {
                            "path_index": 0,
                            "path_id": "mp-1000_0_0_0_0_0",
                            "model": "chgnet",
                            "status": "measured",
                            "signed_error_mev": 500.0,
                        }
                    ]
                    * 2
                }
            )
        )
        self.assertIsNone(feedback_module._artifact_fingerprint(duplicated_artifact))

        fabricated = skew(BUNDLE_A, "campaign-one", "sha256:" + "a" * 64, "art-one.json", 500.0, manifest_one, manifest_one_hash)
        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=single_bundle_assumptions,
            evidence_by_id={BUNDLE_A: fabricated},
            hypotheses=[hypothesis_row],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )
        self.assertEqual(plan["updates"], [])

        distinct_datasets = {
            BUNDLE_A: skew(BUNDLE_A, "campaign-one", fingerprint_one, "art-one.json", 500.0, manifest_one, manifest_one_hash),
            BUNDLE_B: skew(BUNDLE_B, "campaign-two", fingerprint_two, "art-two.json", 520.0, manifest_two, manifest_two_hash),
        }
        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id=distinct_datasets,
            hypotheses=[hypothesis_row],
            new_bundle_ids={BUNDLE_A, BUNDLE_B},
            as_of="2026-08-01",
        )
        self.assertEqual(len(plan["updates"]), 1)
        self.assertEqual(plan["updates"][0]["to_readiness"], "H")

    def test_mislabeled_negative_receipt_with_passing_suite_does_not_supersede(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "refuted",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "negative"}
                    ],
                }
            ]
        }
        mislabeled = bundle(BUNDLE_A, outcome="pass", campaign="one", status="negative")
        mislabeled["claim_predicate"] = "signed_error_positive_fraction>0.5"
        mislabeled["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.9545,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 400,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "less_than_or_equal",
                    "threshold": 600,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
        ]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: mislabeled},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.mislabeled-negative",
                    "contract_json": hypothesis(
                        "C1",
                        "Z1",
                        metric="signed_error_positive",
                        predicate="signed_error_positive_fraction>0.5",
                    ),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])

    def test_negative_sign_skew_receipt_supersedes_the_sign_skew_hypothesis(self) -> None:
        atlas = {
            "discoveryChains": [{"id": "C1", "readiness": "L"}],
            "acceptanceTests": [{"id": "Z1", "chain": "C1"}],
        }
        assumptions = {
            "assumptions": [
                {
                    "claim_id": "discovery.z1.barrier-accuracy.v1",
                    "disposition": "refuted",
                    "evidence": [
                        {"bundle_id": BUNDLE_A, "epistemic_status": "negative"}
                    ],
                }
            ]
        }
        negative = bundle(BUNDLE_A, outcome="fail", campaign="one", status="negative")
        negative["claim_predicate"] = "signed_error_positive_fraction>0.5"
        del negative["measurements"]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: negative},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.own-predicate-negative",
                    "contract_json": hypothesis(
                        "C1",
                        "Z1",
                        metric="signed_error_positive",
                        predicate="signed_error_positive_fraction>0.5",
                    ),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(len(plan["updates"]), 1)
        self.assertEqual(plan["updates"][0]["to_status"], "superseded")
        self.assertEqual(plan["updates"][0]["evidence_bundle_id"], BUNDLE_A)

    def test_permissive_auxiliary_median_thresholds_are_rejected(self) -> None:
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.9545,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 300,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
        ]

        with self.assertRaisesRegex(ValueError, "outside the frozen acceptance suite"):
            build_feedback_plan(
                atlas=atlas,
                assumptions=assumptions,
                evidence_by_id={BUNDLE_A: skew},
                hypotheses=[
                    {
                        "literature_hypothesis_id": "hyp.permissive-aux",
                        "contract_json": hypothesis(
                            "C1",
                            "Z1",
                            metric="signed_error_positive",
                            predicate="signed_error_positive_fraction>0.5",
                        ),
                    }
                ],
                new_bundle_ids={BUNDLE_A},
                as_of="2026-08-01",
            )

    def test_incomplete_acceptance_suite_is_rejected(self) -> None:
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.9545,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 720.0,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 400,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
        ]

        with self.assertRaisesRegex(ValueError, "incomplete acceptance suite"):
            build_feedback_plan(
                atlas=atlas,
                assumptions=assumptions,
                evidence_by_id={BUNDLE_A: skew},
                hypotheses=[
                    {
                        "literature_hypothesis_id": "hyp.incomplete-suite",
                        "contract_json": hypothesis(
                            "C1",
                            "Z1",
                            metric="signed_error_positive",
                            predicate="signed_error_positive_fraction>0.5",
                        ),
                    }
                ],
                new_bundle_ids={BUNDLE_A},
                as_of="2026-08-01",
            )

    def test_sign_skew_receipt_promotes_the_sign_skew_hypothesis(self) -> None:
        import tempfile

        import tools.nightly_ontology_feedback as feedback_module

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        artifact_root = Path(temporary.name)
        original_root = feedback_module._REPO_ROOT
        self.addCleanup(setattr, feedback_module, "_REPO_ROOT", original_root)
        feedback_module._REPO_ROOT = artifact_root
        models = ("chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium")
        rows = [
            {
                "path_index": index,
                "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                "model": model,
                "status": "measured",
                "signed_error_mev": 460.14,
            }
            for index in range(22)
            for model in models
        ]
        (artifact_root / "data").mkdir()
        (artifact_root / "data" / "staging.json").write_text(json.dumps({"per_row": rows}))
        locked_source = {
            "per_path": [
                {
                    "path_index": index,
                    "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                    "per_model": {
                        model: {"vasp_signed_error_mev": 460.14, "complete": True}
                        for model in models
                    },
                    "models_missing": {},
                }
                for index in range(22)
            ]
        }
        locked_bytes = json.dumps(locked_source).encode()
        (artifact_root / "locked-source.json").write_bytes(locked_bytes)
        manifest_dir = artifact_root / "campaigns" / "v1"
        manifest_dir.mkdir(parents=True)
        import hashlib as _hashlib

        panel_bytes = json.dumps(
            {"paths": [{"path_id": f"mp-{1000 + index}_0_0_0_0_0"} for index in range(22)]}
        ).encode()
        (artifact_root / "panel.json").write_bytes(panel_bytes)
        document = {
            "campaign_id": "one",
            "acceptance_test": {
                "metric": "signed_error_positive",
                "operator": "gt",
                "threshold": 0.5,
                "unit": "fraction",
            },
            "execution": {
                "candidate_panel": {
                    "path": "panel.json",
                    "sha256": "sha256:" + _hashlib.sha256(panel_bytes).hexdigest(),
                }
            },
            "available_models": [
                        {
                            "model_id": model,
                            "artifact_hash": {
                                "chgnet": "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890",
                                "mace-mp-small": "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694",
                                "mace-mp-medium": "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3",
                                "mace-mpa-0-medium": "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9",
                            }[model],
                            "version": {
                                "chgnet": "chgnet 0.4.2",
                                "mace-mp-small": "mace-torch 0.3.16 / small",
                                "mace-mp-medium": "mace-torch 0.3.16 / medium",
                                "mace-mpa-0-medium": "mace-torch 0.3.16 / mpa-0 medium",
                            }[model],
                        }
                        for model in models
                    ],
            "preregistration": {
                "recorded_inputs": [
                    {
                        "path": "locked-source.json",
                        "sha256": "sha256:" + _hashlib.sha256(locked_bytes).hexdigest(),
                    }
                ]
            },
        }
        payload = json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        document["content_hash"] = "sha256:" + _hashlib.sha256(payload).hexdigest()
        manifest_raw = json.dumps(document).encode()
        (manifest_dir / "staging.json").write_bytes(manifest_raw)
        registry_file = artifact_root / "registry" / "campaigns.v1.json"
        registry_file.parent.mkdir(parents=True, exist_ok=True)
        registry_file.write_text(
            json.dumps(
                {"campaigns": [{"campaign_id": "one", "content_hash": document["content_hash"]}]}
            )
        )
        fingerprint = feedback_module._artifact_fingerprint(artifact_root / "data" / "staging.json")
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["evidence_refs"][0]["dataset_fingerprint"] = fingerprint
        skew["evidence_refs"][0]["campaign_manifest_hash"] = (
            "sha256:" + _hashlib.sha256(manifest_raw).hexdigest()
        )
        skew["evidence_refs"][0]["artifact_hash"] = (
            "sha256:"
            + _hashlib.sha256((artifact_root / "data" / "staging.json").read_bytes()).hexdigest()
        )
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 1.0,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 400,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 460.14,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "less_than_or_equal",
                    "threshold": 600,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
        ]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: skew},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.sign-skew-promotion",
                    "contract_json": hypothesis(
                        "C1",
                        "Z1",
                        metric="signed_error_positive",
                        predicate="signed_error_positive_fraction>0.5",
                    ),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(len(plan["updates"]), 1)
        update = plan["updates"][0]
        self.assertEqual(update["hypothesis_id"], "hyp.sign-skew-promotion")
        self.assertEqual(update["to_readiness"], "M")
        self.assertEqual(update["evidence_bundle_id"], BUNDLE_A)

    def test_sign_skew_receipt_with_out_of_band_median_does_not_promote(self) -> None:
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
        skew = bundle(BUNDLE_A, outcome="pass", campaign="one", status="confirmatory")
        skew["claim_predicate"] = "signed_error_positive_fraction>0.5"
        skew["measurements"] = [
            {
                "metric": "signed_error_positive",
                "value": 0.9545,
                "unit": "fraction",
                "acceptance_test": {
                    "comparator": "greater_than",
                    "threshold": 0.5,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 720.0,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "greater_than_or_equal",
                    "threshold": 400,
                    "outcome": "pass",
                },
                "sample_count": 22,
            },
            {
                "metric": "median_signed_error",
                "value": 720.0,
                "unit": "meV",
                "acceptance_test": {
                    "comparator": "less_than_or_equal",
                    "threshold": 600,
                    "outcome": "fail",
                },
                "sample_count": 22,
            },
        ]

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: skew},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.sign-skew-band",
                    "contract_json": hypothesis(
                        "C1",
                        "Z1",
                        metric="signed_error_positive",
                        predicate="signed_error_positive_fraction>0.5",
                    ),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])

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

    def test_readiness_requires_every_acceptance_measurement_to_pass(self) -> None:
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
        partial = bundle(
            BUNDLE_A,
            outcome="pass",
            campaign="one",
            status="confirmatory",
        )
        failing_measurement = json.loads(json.dumps(partial["measurements"][0]))
        failing_measurement["value"] = 70
        failing_measurement["acceptance_test"]["outcome"] = "fail"
        partial["measurements"].append(failing_measurement)

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: partial},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.partial",
                    "contract_json": hypothesis("C1", "Z1"),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])
        self.assertEqual(plan["queue"][0]["evidence_gap"]["current_readiness"], "L")

    def test_readiness_requires_hypothesis_bound_acceptance_predicate(self) -> None:
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
        self_authorized = bundle(
            BUNDLE_A,
            outcome="pass",
            campaign="one",
            status="confirmatory",
        )
        self_authorized["claim_predicate"] = "barrier_mae_mev<=999"
        self_authorized["measurements"][0]["value"] = 70
        self_authorized["measurements"][0]["acceptance_test"]["threshold"] = 999

        plan = build_feedback_plan(
            atlas=atlas,
            assumptions=assumptions,
            evidence_by_id={BUNDLE_A: self_authorized},
            hypotheses=[
                {
                    "literature_hypothesis_id": "hyp.threshold-launder",
                    "contract_json": hypothesis("C1", "Z1"),
                }
            ],
            new_bundle_ids={BUNDLE_A},
            as_of="2026-08-01",
        )

        self.assertEqual(plan["updates"], [])
        self.assertEqual(plan["queue"][0]["evidence_gap"]["current_readiness"], "L")

    def test_supersession_edges_are_all_persisted(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        apply_migrations(connection)
        predecessor_a = bundle(BUNDLE_A, outcome="fail", campaign="one", status="negative")
        predecessor_e = bundle("sha256:" + "e" * 64, outcome="fail", campaign="zero", status="negative")
        replacement = {
            **bundle(BUNDLE_B, outcome="pass", campaign="two", status="confirmatory"),
            "supersedes": [BUNDLE_A, "sha256:" + "e" * 64],
        }
        plan = {"as_of": "2026-08-01", "updates": [], "queue": [], "evidence": [replacement, predecessor_a, predecessor_e]}
        sql = render_feedback_sql(plan)
        connection.executescript(sql)
        row = connection.execute(
            "SELECT supersedes_bundle_id, supersedes_bundle_ids_json FROM evidence_bundle WHERE bundle_id = ?",
            (BUNDLE_B,),
        ).fetchone()
        self.assertEqual(row[0], BUNDLE_A)
        self.assertEqual(json.loads(row[1]), sorted([BUNDLE_A, "sha256:" + "e" * 64]))

    def test_superseded_predecessors_insert_before_replacements(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        apply_migrations(connection)
        predecessor = bundle(BUNDLE_A, outcome="fail", campaign="one", status="negative")
        replacement = {
            **bundle(BUNDLE_B, outcome="pass", campaign="two", status="confirmatory"),
            "supersedes": [BUNDLE_A],
        }
        # Hash order would place the replacement (b…) before its predecessor (a…)?
        # No — force the trap by presenting the replacement first.
        plan = {"as_of": "2026-08-01", "updates": [], "queue": [], "evidence": [replacement, predecessor]}
        sql = render_feedback_sql(plan)
        self.assertLess(sql.index(BUNDLE_A), sql.index(BUNDLE_B))
        connection.executescript(sql)
        count = connection.execute("SELECT COUNT(*) FROM evidence_bundle").fetchone()[0]
        self.assertEqual(count, 2)

    def test_workflow_rehydrates_and_persists_the_complete_nightly_corpus(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "evidence-nightly.yml").read_text()

        restore = workflow.index("Rehydrate durable ontology corpus")
        ingest = workflow.index("Ingest rows and regenerate assumptions plus runtime gate")
        apply_feedback = workflow.index("Apply feedback to production D1")
        persist = workflow.index("Persist durable ontology corpus")
        self.assertLess(restore, ingest)
        self.assertLess(persist, apply_feedback)
        self.assertIn("--new-bundle-ids nightly-output/sync-candidates.json", workflow)
        self.assertIn("registry/claims", workflow)
        self.assertIn("evidence/v1/examples", workflow)
        self.assertIn("ontology-state/$CYCLE_DATE/corpus-", workflow)
        self.assertIn("printf '%020d' \"$GITHUB_RUN_ID\"", workflow)
        self.assertIn("tar -xzf nightly-state/corpus.tar.gz -C nightly-state/restored", workflow)
        self.assertNotIn("rm -rf registry/claims evidence/v1/examples", workflow)
        self.assertIn("rsync -a --ignore-existing nightly-state/restored/registry/claims/ registry/claims/", workflow)
        self.assertIn("rsync -a --ignore-existing nightly-state/restored/evidence/v1/examples/ evidence/v1/examples/", workflow)

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

    def test_latest_state_schema_keeps_evidence_and_status_history_immutable(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript(
            (ROOT / "glim-think" / "schema.sql").read_text(encoding="utf-8")
        )
        bundle_id = "sha256:" + "a" * 64
        connection.execute(
            """
            INSERT INTO evidence_bundle (
              bundle_id, claim_predicate, epistemic_status, scope_json, provenance_json
            ) VALUES (?, 'barrier_mae_mev<=40', 'confirmatory', '{}', '{}')
            """,
            (bundle_id,),
        )
        connection.execute(
            """
            INSERT INTO status_event (
              status_event_id, entity_type, entity_id, from_status, to_status,
              evidence_bundle_id, occurred_at
            ) VALUES ('event.latest-state', 'literature_hypothesis', 'hyp.one',
                      'proposed', 'accepted', ?, '2026-08-01T08:00:00Z')
            """,
            (bundle_id,),
        )

        with self.assertRaisesRegex(sqlite3.IntegrityError, "evidence_bundle is immutable"):
            connection.execute(
                "UPDATE evidence_bundle SET epistemic_status = 'negative' WHERE bundle_id = ?",
                (bundle_id,),
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "evidence_bundle is immutable"):
            connection.execute("DELETE FROM evidence_bundle WHERE bundle_id = ?", (bundle_id,))
        with self.assertRaisesRegex(sqlite3.IntegrityError, "status_event is append-only"):
            connection.execute(
                "UPDATE status_event SET to_status = 'rejected' WHERE status_event_id = 'event.latest-state'"
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "status_event is append-only"):
            connection.execute(
                "DELETE FROM status_event WHERE status_event_id = 'event.latest-state'"
            )


if __name__ == "__main__":
    unittest.main()
