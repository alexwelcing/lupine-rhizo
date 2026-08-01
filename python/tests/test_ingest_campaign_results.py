"""End-to-end tests for Round-4 campaign result ingestion."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INGESTER = ROOT / "tools" / "ingest_campaign_results.py"
GENERATOR = ROOT / "tools" / "generate_assumptions.py"
FIXTURE = ROOT / "python" / "tests" / "fixtures" / "round4_ingest"
CLAIM_ID = "correction.same_class.a0.v1"
PREMISE_ID = "round3_same_class_a0"


def load_ingest_module():
    spec = importlib.util.spec_from_file_location("ingest_campaign_results", INGESTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(INGESTER.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(INGESTER.parent))
    return module


class CampaignResultIngestionTests(unittest.TestCase):
    def prepare_root(self, destination: Path) -> None:
        shutil.copytree(ROOT / "registry", destination / "registry")
        shutil.copytree(ROOT / "evidence", destination / "evidence")
        shutil.copytree(ROOT / "campaigns", destination / "campaigns")
        shutil.copytree(FIXTURE, destination / "python" / "tests" / "fixtures" / "round4_ingest")

    def invoke(
        self, root: Path, measurements: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
        return subprocess.run(
            [
                sys.executable,
                str(INGESTER),
                "--root",
                str(root),
                "--manifest",
                str(fixture / "manifest.json"),
                "--measurements",
                str(measurements or fixture / "measurements.jsonl"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def content_hash(document: object) -> str:
        payload = json.dumps(
            document, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def rebind_measurements(self, path: Path, manifest_hash: str) -> None:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        previous_hash = None
        for row in rows:
            row["campaign_manifest_hash"] = manifest_hash
            row["previous_row_hash"] = previous_hash
            row["row_hash"] = self.content_hash(
                {key: value for key, value in row.items() if key != "row_hash"}
            )
            previous_hash = row["row_hash"]
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    @staticmethod
    def round4_bundles(root: Path) -> list[str]:
        """Names of every round4 bundle in the staged evidence dir.

        The repo now carries ingested Z1/Z3 campaign bundles, so fail-closed
        tests must assert "no NEW bundles" (set unchanged), not "no bundles".
        """
        return sorted(
            path.name for path in (root / "evidence" / "v1" / "examples").glob("round4-*.json")
        )

    def test_synthetic_round4_fixture_ingests_and_materializes_new_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            old_lock = json.loads(
                (root / "registry" / "snapshots" / "current.lock.json").read_text()
            )

            result = self.invoke(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            created = sorted(
                path
                for path in (root / "evidence" / "v1" / "examples").glob("round4-*.json")
                if "discovery-round-4-z1" not in path.name
                and "discovery-round-4-z3" not in path.name
            )
            self.assertEqual(len(created), 2)
            bundle_ids = {json.loads(path.read_text())["bundle_id"] for path in created}
            claim = json.loads((root / "registry" / "claims" / f"{CLAIM_ID}.json").read_text())
            premise = next(item for item in claim["premises"] if item["premise_id"] == PREMISE_ID)
            self.assertTrue(
                bundle_ids.issubset(
                    {reference["bundle_id"] for reference in premise["bundle_references"]}
                )
            )
            registry = json.loads((root / "registry" / "assumptions.v1.json").read_text())
            assumption = next(
                item for item in registry["assumptions"] if item["claim_id"] == CLAIM_ID
            )
            self.assertTrue(
                bundle_ids.issubset({item["bundle_id"] for item in assumption["evidence"]})
            )
            new_lock = json.loads(
                (root / "registry" / "snapshots" / "current.lock.json").read_text()
            )
            self.assertNotEqual(new_lock, old_lock)
            self.assertTrue(bundle_ids.issubset(set(new_lock["inputs"]["evidence_bundles"])))

            check = subprocess.run(
                [sys.executable, str(GENERATOR), "--root", str(root), "--check"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_typed_measurements_on_unsupported_predicate_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            measurements_path = fixture / "measurements.jsonl"
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            # Codex PR#41 P2: a barrier_mae measurement cannot describe this
            # row's a0 predicate; the ingester must refuse, not launder it.
            rows[0]["measurements"] = [
                {
                    "metric": "barrier_mae",
                    "value": 12.5,
                    "unit": "meV",
                    "acceptance_test": {
                        "comparator": "less_than_or_equal",
                        "threshold": 40,
                        "outcome": "pass",
                    },
                    "sample_count": 8,
                }
            ]
            measurements_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            manifest = json.loads((fixture / "manifest.json").read_text())
            self.rebind_measurements(measurements_path, manifest["content_hash"])

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("unsupported predicate", result.stderr)

    def test_typed_measurements_admit_the_sign_skew_predicate(self) -> None:
        module = load_ingest_module()
        row = {
            "row_id": "skew-1",
            "claim_predicate": "signed_error_positive_fraction>0.5",
            "measurements": [
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
            ],
        }

        admitted = module.typed_measurements(row)

        self.assertEqual(admitted, row["measurements"])

        row["claim_predicate"] = "signed_error_positive_fraction>=0.5"
        with self.assertRaisesRegex(ValueError, "unsupported predicate"):
            module.typed_measurements(row)

    def test_recorded_path_minimum_is_enforced(self) -> None:
        module = load_ingest_module()
        models = ["chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium"]

        def make_bundle(fraction: float = 1.0, median: float = 500.0, sample_count: int = 22) -> dict:
            return {
                "claim_predicate": "signed_error_positive_fraction>0.5",
                "measurements": [
                    {
                        "metric": "signed_error_positive",
                        "value": fraction,
                        "unit": "fraction",
                        "acceptance_test": {
                            "comparator": "greater_than",
                            "threshold": 0.5,
                            "outcome": "pass",
                        },
                        "sample_count": sample_count,
                    },
                    {
                        "metric": "median_signed_error",
                        "value": median,
                        "unit": "meV",
                        "acceptance_test": {
                            "comparator": "greater_than_or_equal",
                            "threshold": 400,
                            "outcome": "pass",
                        },
                        "sample_count": sample_count,
                    },
                ],
            }

        def write_artifact(path: Path, rows: list[dict], **extra: object) -> None:
            document = {"per_row": rows}
            document.update(extra)
            path.write_text(json.dumps(document))

        full_rows = [
            {
                "path_index": index,
                "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                "model": model,
                "status": "measured",
                "signed_error_mev": 500.0,
            }
            for index in range(22)
            for model in models
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            artifact = root / "artifact.json"
            locked_document = {
                "per_path": [
                    {
                        "path_index": index,
                        "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                        "per_model": {
                            model: {"vasp_signed_error_mev": 500.0, "complete": True}
                            for model in models
                        },
                        "models_missing": {},
                    }
                    for index in range(22)
                ]
            }
            locked_bytes = json.dumps(locked_document).encode()
            (root / "locked.json").write_bytes(locked_bytes)
            manifest = {
                "available_models": [{"model_id": model} for model in models],
                "acceptance_test": {
                    "metric": "signed_error_positive",
                    "operator": "gt",
                    "threshold": 0.5,
                    "unit": "fraction",
                },
                "evidence_requirements": [
                    {
                        "requirement_id": "e.z1.recorded-path-set",
                        "artifact_type": "neb-path-set",
                        "description": "recorded rows",
                        "minimum_count": 22,
                    }
                ],
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "locked.json",
                            "sha256": "sha256:" + hashlib.sha256(locked_bytes).hexdigest(),
                        }
                    ]
                },
            }

            def enforce(bundle: dict) -> None:
                module.enforce_path_minimums(root, manifest, bundle, artifact, "skew-1")

            # Aggregate-only artifacts cannot prove coverage, even with n_paths.
            write_artifact(artifact, [], n_paths=22)
            with self.assertRaisesRegex(ValueError, "no per-path rows"):
                enforce(make_bundle())

            # A self-reported aggregate must agree with the rows.
            write_artifact(artifact, full_rows, n_paths=23)
            with self.assertRaisesRegex(ValueError, "declares 23 recorded paths"):
                enforce(make_bundle())

            # Full coverage with matching statistics passes.
            write_artifact(artifact, full_rows, n_paths=22)
            enforce(make_bundle())

            # Sample counts must equal the artifact's measured-path count.
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "does not equal"):
                enforce(make_bundle(sample_count=6))

            # Paths with every model failed cannot pad the panel: only paths
            # with measurements count toward the floor. The locked source here
            # records path 0 measured and paths 1-21 all-failed.
            failed_document = {
                "per_path": [
                    {
                        "path_index": index,
                        "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                        "per_model": (
                            {
                                model: {"vasp_signed_error_mev": 500.0, "complete": True}
                                for model in models
                            }
                            if index == 0
                            else {}
                        ),
                        "models_missing": (
                            {} if index == 0 else {model: "failed" for model in models}
                        ),
                    }
                    for index in range(22)
                ]
            }
            failed_bytes = json.dumps(failed_document).encode()
            (root / "locked-failed.json").write_bytes(failed_bytes)
            failed_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "locked-failed.json",
                            "sha256": "sha256:" + hashlib.sha256(failed_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(
                artifact,
                [row for row in full_rows if row["path_index"] == 0]
                + [
                    {"path_index": index, "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                     "model": model, "status": "failed", "reason": "failed"}
                    for index in range(1, 22)
                    for model in models
                ],
            )
            with self.assertRaisesRegex(ValueError, "paths with measurements"):
                module.enforce_path_minimums(
                    root, failed_manifest, make_bundle(fraction=1.0, sample_count=1), artifact, "skew-1"
                )

            # Six paths measured by four models must not launder the minimum:
            # distinct path coverage, not raw sample_count, is the gate.
            write_artifact(
                artifact,
                [row for row in full_rows if row["path_index"] < 6],
            )
            with self.assertRaisesRegex(ValueError, "distinct paths"):
                enforce(make_bundle(sample_count=22))

            # Twenty-two paths from a single model omit declared available models.
            write_artifact(
                artifact,
                [row for row in full_rows if row["model"] == "chgnet"],
            )
            with self.assertRaisesRegex(ValueError, "omits declared available models"):
                enforce(make_bundle())

            # Every (path, model) pair needs an observation or a disclosed failure.
            write_artifact(
                artifact,
                [
                    row
                    for row in full_rows
                    if not (row["path_index"] == 13 and row["model"] == "mace-mp-small")
                ],
            )
            with self.assertRaisesRegex(ValueError, "path 13 model mace-mp-small"):
                enforce(make_bundle())

            # A disclosed failure satisfies the pair without entering statistics.
            pair_document = json.loads(locked_bytes)
            pair_document["per_path"][13]["per_model"].pop("mace-mp-small")
            pair_document["per_path"][13]["models_missing"] = {"mace-mp-small": "failed"}
            pair_bytes = json.dumps(pair_document).encode()
            (root / "locked-pair.json").write_bytes(pair_bytes)
            pair_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "locked-pair.json",
                            "sha256": "sha256:" + hashlib.sha256(pair_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(
                artifact,
                [
                    row
                    for row in full_rows
                    if not (row["path_index"] == 13 and row["model"] == "mace-mp-small")
                ]
                + [
                    {
                        "path_index": 13,
                        "path_id": "mp-1013_0_0_0_0_0",
                        "model": "mace-mp-small",
                        "status": "failed",
                        "reason": "failed",
                    }
                ],
            )
            module.enforce_path_minimums(root, pair_manifest, make_bundle(), artifact, "skew-1")

            # Submitted statistics must match the artifact's own rows.
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "recomputed value"):
                enforce(make_bundle(fraction=0.9))
            with self.assertRaisesRegex(ValueError, "recomputed value"):
                enforce(make_bundle(median=460.14))
            # The exact unrounded ratio and the declared 4-decimal rounding both pass.
            enforce(make_bundle(fraction=1.0))

            # Rows for models outside execution.model_selection are rejected.
            write_artifact(
                artifact,
                full_rows
                + [
                    {
                        "path_index": 0,
                        "path_id": "mp-1000_0_0_0_0_0",
                        "model": "uma",
                        "status": "measured",
                        "signed_error_mev": 500.0,
                    }
                ],
            )
            with self.assertRaisesRegex(ValueError, "no recorded counterpart"):
                enforce(make_bundle())

            # Placeholder rows are not terminal observations or failures.
            write_artifact(
                artifact,
                [
                    row
                    for row in full_rows
                    if not (row["path_index"] == 13 and row["model"] == "mace-mp-small")
                ]
                + [{"path_index": 13, "path_id": "mp-1013_0_0_0_0_0", "model": "mace-mp-small"}],
            )
            with self.assertRaisesRegex(ValueError, "measured or an explicit failure"):
                enforce(make_bundle())

            # Duplicate (path, model) rows would double-vote the path median.
            write_artifact(artifact, full_rows + [dict(full_rows[0])])
            with self.assertRaisesRegex(ValueError, "duplicate observation"):
                enforce(make_bundle())

            # The locked source digest is verified before any binding.
            write_artifact(artifact, full_rows)
            tampered_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [{"path": "locked.json", "sha256": "sha256:" + "0" * 64}]
                },
            }
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                module.enforce_path_minimums(root, tampered_manifest, make_bundle(), artifact, "skew-1")

            # Row identities, values, and statuses bind to the locked source.
            wrong_identity = [
                row if row["path_index"] != 3 else {**row, "path_id": "mp-999999_0_0_0_0_0"}
                for row in full_rows
            ]
            write_artifact(artifact, wrong_identity)
            with self.assertRaisesRegex(ValueError, "does not match the locked panel"):
                enforce(make_bundle())

            invented_values = [
                row if row["path_index"] != 5 else {**row, "signed_error_mev": 999.0}
                for row in full_rows
            ]
            write_artifact(artifact, invented_values)
            with self.assertRaisesRegex(ValueError, "disagrees with the locked source"):
                enforce(make_bundle())

            wrong_status = [
                {key: value for key, value in row.items() if key != "signed_error_mev"}
                if row["path_index"] == 7
                else row
                for row in full_rows
            ]
            wrong_status = [
                {**row, "status": "failed"} if row["path_index"] == 7 else row
                for row in wrong_status
            ]
            write_artifact(artifact, wrong_status)
            with self.assertRaisesRegex(ValueError, "disagrees with the locked source"):
                enforce(make_bundle())

            outside_rows = [
                {**row, "path_index": row["path_index"] + 100} for row in full_rows
            ]
            write_artifact(artifact, outside_rows)
            with self.assertRaisesRegex(ValueError, "outside the locked recorded panel"):
                enforce(make_bundle())

    def test_sign_skew_rows_require_a_locked_sign_skew_manifest(self) -> None:
        module = load_ingest_module()
        barrier_manifest = {
            "available_models": [{"model_id": "chgnet"}],
            "acceptance_test": {"metric": "barrier_mae", "operator": "lte", "threshold": 40, "unit": "meV"},
            "evidence_requirements": [
                {
                    "requirement_id": "e.z1.held-out-paths",
                    "artifact_type": "neb-path-set",
                    "description": "fresh paths",
                    "minimum_count": 30,
                }
            ],
        }
        bundle = {
            "claim_predicate": "signed_error_positive_fraction>0.5",
            "measurements": [
                {
                    "metric": "signed_error_positive",
                    "value": 1.0,
                    "unit": "fraction",
                    "acceptance_test": {"comparator": "greater_than", "threshold": 0.5, "outcome": "pass"},
                    "sample_count": 22,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "does not match the manifest's acceptance test"):
            module.enforce_predicate_manifest_alignment(barrier_manifest, bundle, "skew-1")

        aligned_manifest = {
            "acceptance_test": {"metric": "signed_error_positive", "operator": "gt", "threshold": 0.5, "unit": "fraction"},
        }
        module.enforce_predicate_manifest_alignment(aligned_manifest, bundle, "skew-1")

    def test_manifest_that_violates_round4_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            manifest_path = (
                root / "python" / "tests" / "fixtures" / "round4_ingest" / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text())
            del manifest["kill_conditions"]
            manifest["content_hash"] = self.content_hash(
                {key: value for key, value in manifest.items() if key != "content_hash"}
            )
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            self.rebind_measurements(
                manifest_path.with_name("measurements.jsonl"), manifest["content_hash"]
            )
            claim_path = root / "registry" / "claims" / f"{CLAIM_ID}.json"
            before_claim = claim_path.read_bytes()

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("campaign manifest schema validation failed", result.stderr)
            self.assertEqual(claim_path.read_bytes(), before_claim)
            self.assertEqual(self.round4_bundles(root), before_bundles)

    def test_two_targets_in_one_claim_preserve_both_contract_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            claim_path = root / "registry" / "claims" / f"{CLAIM_ID}.json"
            claim = json.loads(claim_path.read_text())
            second_premise = json.loads(json.dumps(claim["premises"][0]))
            second_premise["premise_id"] = "round4_same_class_a0_replication"
            claim["premises"].append(second_premise)
            claim["content_hash"] = self.content_hash(
                {key: value for key, value in claim.items() if key != "content_hash"}
            )
            claim_path.write_text(json.dumps(claim, indent=2) + "\n")

            manifest_path = fixture / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["target_premises"].append(
                {"claim_id": CLAIM_ID, "premise_id": second_premise["premise_id"]}
            )
            manifest["content_hash"] = self.content_hash(
                {key: value for key, value in manifest.items() if key != "content_hash"}
            )
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            measurements_path = fixture / "measurements.jsonl"
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[1]["premise_id"] = second_premise["premise_id"]
            measurements_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            self.rebind_measurements(measurements_path, manifest["content_hash"])

            result = self.invoke(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            updated_claim = json.loads(claim_path.read_text())
            reference_counts = {
                premise["premise_id"]: len(premise["bundle_references"])
                for premise in updated_claim["premises"]
            }
            self.assertEqual(reference_counts[PREMISE_ID], 2)
            self.assertEqual(reference_counts[second_premise["premise_id"]], 2)

    def test_broken_measurement_hash_chain_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            measurements_path = (
                root / "python" / "tests" / "fixtures" / "round4_ingest" / "measurements.jsonl"
            )
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[1]["previous_row_hash"] = "sha256:" + "0" * 64
            measurements_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("measurement hash chain is broken", result.stderr)
            self.assertEqual(self.round4_bundles(root), before_bundles)

    def test_scope_outside_baseline_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            measurements_path = fixture / "measurements.jsonl"
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[0]["scope"]["structures"] = ["diamond"]
            measurements_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            manifest = json.loads((fixture / "manifest.json").read_text())
            self.rebind_measurements(measurements_path, manifest["content_hash"])

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("scope mismatch", result.stderr)
            self.assertEqual(self.round4_bundles(root), before_bundles)

    def test_missing_evidence_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            measurements_path = fixture / "measurements.jsonl"
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[0]["artifact"] = "python/tests/fixtures/round4_ingest/artifacts/missing.json"
            measurements_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            manifest = json.loads((fixture / "manifest.json").read_text())
            self.rebind_measurements(measurements_path, manifest["content_hash"])

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("missing evidence artifact", result.stderr)
            self.assertEqual(self.round4_bundles(root), before_bundles)

    def test_tampered_claim_contract_fails_instead_of_laundering_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            claim_path = root / "registry" / "claims" / f"{CLAIM_ID}.json"
            claim = json.loads(claim_path.read_text())
            claim["statement"] = "Tampered without updating content_hash"
            claim_path.write_text(json.dumps(claim, indent=2) + "\n")
            before_claim = claim_path.read_bytes()

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("non-canonical ClaimContract content_hash", result.stderr)
            self.assertEqual(claim_path.read_bytes(), before_claim)
            self.assertEqual(self.round4_bundles(root), before_bundles)

    def test_claim_predicate_outside_baseline_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            before_bundles = self.round4_bundles(root)
            fixture = root / "python" / "tests" / "fixtures" / "round4_ingest"
            measurements_path = fixture / "measurements.jsonl"
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[0]["claim_predicate"] = "unrelated_claim(property=a0)"
            measurements_path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            manifest = json.loads((fixture / "manifest.json").read_text())
            self.rebind_measurements(measurements_path, manifest["content_hash"])

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("claim predicate mismatch", result.stderr)
            self.assertEqual(self.round4_bundles(root), before_bundles)


if __name__ == "__main__":
    unittest.main()
