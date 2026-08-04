"""End-to-end tests for Round-4 campaign result ingestion."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

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

    @staticmethod
    def z2_reference_prediction(material: dict[str, object]) -> dict[str, object]:
        reference = material["reference"]
        assert isinstance(reference, dict)
        expected_easy_axis = (
            "out_of_plane"
            if max(
                float(reference["mae_xz_mev_per_cell"]),
                float(reference["mae_yz_mev_per_cell"]),
            )
            < 0.0
            else "in_plane"
        )
        exchange = float(reference["exchange_mev"])
        anisotropy = float(reference["exchange_anisotropy"])
        j_parallel = exchange * (1.0 - anisotropy)
        j_perpendicular = exchange * (1.0 + anisotropy)
        spin_value = material["spin"]
        coordination_value = material["nearest_neighbors"]
        assert isinstance(spin_value, (int, float)) and not isinstance(spin_value, bool)
        assert isinstance(coordination_value, int) and not isinstance(coordination_value, bool)
        spin = float(spin_value)
        tc_k = load_ingest_module()._z2_tc_estimates(
            exchange, anisotropy, spin, str(material["lattice"])
        )
        factor = 2.0 * coordination_value * spin**2
        fm_parallel = 0.0
        fm_perpendicular = float(reference["mae_xz_mev_per_cell"]) / 1000.0
        common_ordering = {
            "scalar_total_energy_ev": 0.0,
            "scalar_band_energy_ev": 0.0,
        }
        fm_ordering = {
            **common_ordering,
            "parallel_energy_ev": fm_parallel,
            "y_energy_ev": fm_perpendicular
            - float(reference["mae_yz_mev_per_cell"]) / 1000.0,
            "perpendicular_energy_ev": fm_perpendicular,
        }
        afm_ordering = {
            **common_ordering,
            "parallel_energy_ev": fm_parallel + j_parallel * factor / 1000.0,
            "y_energy_ev": 0.0,
            "perpendicular_energy_ev": fm_perpendicular
            + j_perpendicular * factor / 1000.0,
        }
        return {
            "material_id": material["material_id"],
            "formula": material["formula"],
            "status": "completed",
            "exchange_mev": exchange,
            "j_parallel_mev": j_parallel,
            "j_perpendicular_mev": j_perpendicular,
            "anisotropic_exchange_mev": j_perpendicular - j_parallel,
            "exchange_anisotropy": anisotropy,
            "mae_xz_mev_per_cell": reference["mae_xz_mev_per_cell"],
            "mae_yz_mev_per_cell": reference["mae_yz_mev_per_cell"],
            "easy_axis": expected_easy_axis,
            "tc_k": {method: tc_k[method] for method in ("green", "mc", "rnsw")},
            "ordering_evidence": {"fm": fm_ordering, "afm": afm_ordering},
        }

    @staticmethod
    def z2_metrics(panel: dict[str, Any], predictions: list[dict[str, Any]]) -> dict[str, object]:
        materials = panel["materials"]
        assert isinstance(materials, list)
        references = {item["material_id"]: item["reference"] for item in materials}
        tc_errors = []
        covered = 0
        for prediction in predictions:
            reference = references[prediction["material_id"]]
            predicted_tc = float(prediction["tc_k"]["rnsw"])
            tc_errors.append(abs(predicted_tc - float(reference["tc_k"]["rnsw"])))
            low, high = reference["tc_envelope_k"]
            covered += int(float(low) <= predicted_tc <= float(high))
        return {
            "magnetocrystalline_anisotropy_rank_correlation": 1.0,
            "easy_axis_sign_errors": 0,
            "tc_rnsw_mae_k": statistics.fmean(tc_errors),
            "tc_envelope_coverage": covered / len(predictions),
            "completed_material_count": 7,
            "failed_material_count": 0,
            "measurement_complete": True,
        }

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

    def test_reviewed_z2_bootstrap_is_the_only_empty_baseline_path(self) -> None:
        module = load_ingest_module()
        manifest = json.loads(
            (ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json").read_text()
        )
        panel = json.loads(
            (ROOT / "data" / "candidates" / "z2_soc_tc_panel.lock.json").read_text()
        )
        premise = {
            "premise_id": "spin-orbit-resolved-held-out-ranking",
            "support_policy": {"mode": "unsupported"},
            "bundle_references": [],
        }
        row = {
            "claim_id": "discovery.z2.magnetic-anisotropy.v1",
            "premise_id": premise["premise_id"],
            "claim_predicate": "magnetocrystalline_anisotropy_rank_correlation==1",
            "epistemic_status": "confirmatory",
            "scope": {
                "structures": [item["material_id"] for item in panel["materials"]],
                "chemistries": [item["formula"] for item in panel["materials"]],
                "properties": [
                    "magnetocrystalline_anisotropy_rank",
                    "easy_axis",
                    "curie_temperature",
                ],
                "conditions": {
                    "candidate_panel_sha256": module.Z2_PANEL_SHA256,
                    "locked_material_count": 7,
                },
            },
        }

        allowed, predicates, bootstrap = module.allowed_scope(
            ROOT, premise, manifest=manifest, row=row
        )

        self.assertTrue(bootstrap)
        self.assertEqual(predicates, {row["claim_predicate"]})
        self.assertEqual(allowed["structures"], set(row["scope"]["structures"]))

        negative = dict(row)
        negative["epistemic_status"] = "negative"
        with self.assertRaisesRegex(ValueError, "must be confirmatory"):
            module.allowed_scope(ROOT, premise, manifest=manifest, row=negative)

        unreviewed = dict(manifest)
        unreviewed["campaign_id"] = "unreviewed-z2"
        with self.assertRaisesRegex(ValueError, "no baseline evidence"):
            module.allowed_scope(ROOT, premise, manifest=unreviewed, row=row)

    def test_reviewed_z2_panel_loader_refuses_tampering_on_every_ingestion(self) -> None:
        module = load_ingest_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            panel_path = root / module.Z2_PANEL_PATH
            panel_path.parent.mkdir(parents=True)
            panel_path.write_bytes((ROOT / module.Z2_PANEL_PATH).read_bytes() + b" ")

            with self.assertRaisesRegex(ValueError, "panel digest mismatch"):
                module.load_reviewed_z2_panel(root)

    def test_z2_artifact_refuses_missing_digest_and_six_of_seven(self) -> None:
        module = load_ingest_module()
        panel = json.loads(
            (ROOT / "data" / "candidates" / "z2_soc_tc_panel.lock.json").read_text()
        )
        predictions = [self.z2_reference_prediction(item) for item in panel["materials"]]
        metrics = self.z2_metrics(panel, predictions)
        artifact = {
            "run_id": "run-z2-complete",
            "campaign_id": module.Z2_CAMPAIGN_ID,
            "row_id": "soc_tc",
            "manifest_hash": module.Z2_MANIFEST_CONTENT_HASH,
            "fixture_contract": {"candidate_panel_sha256": module.Z2_PANEL_SHA256},
            "predictions": predictions,
            "execution": {
                "runner_image_digest": "sha256:" + "d" * 64,
                "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
            },
            "accuracy": metrics,
        }
        row = {
            "row_id": "soc_tc",
            "run_id": "run-z2-complete",
            "claim_predicate": module.Z2_PREDICATE,
            "provenance": {
                "runner_image_digest": "sha256:" + "d" * 64,
                "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
            },
            "measurements": [
                {"metric": "magnetocrystalline_anisotropy_rank_correlation", "value": 1.0, "unit": "spearman_rho", "acceptance_test": {"comparator": "equal", "threshold": 1.0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "easy_axis_sign_errors", "value": 0, "unit": "materials", "acceptance_test": {"comparator": "equal", "threshold": 0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "tc_rnsw_mae_k", "value": metrics["tc_rnsw_mae_k"], "unit": "K", "sample_count": 7},
                {"metric": "tc_envelope_coverage", "value": metrics["tc_envelope_coverage"], "unit": "fraction", "sample_count": 7},
            ],
        }

        module.enforce_z2_measurement(panel, artifact, row)
        artifact["run_id"] = "different-run"
        with self.assertRaisesRegex(ValueError, "run_id does not match"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["run_id"] = "run-z2-complete"
        artifact["execution"]["runner_image_digest"] = None
        with self.assertRaisesRegex(ValueError, "runner image digest"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["execution"]["runner_image_digest"] = "sha256:" + "d" * 64
        artifact["predictions"][0]["mae_xz_mev_per_cell"] = -1000.0
        with self.assertRaisesRegex(ValueError, "contradicts ordering evidence"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
        artifact["predictions"][0]["mae_yz_mev_per_cell"] = 1.0
        fm_evidence = artifact["predictions"][0]["ordering_evidence"]["fm"]
        fm_evidence["y_energy_ev"] = fm_evidence["perpendicular_energy_ev"] - 0.001
        with self.assertRaisesRegex(ValueError, "easy_axis contradicts"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
        artifact["predictions"][0]["mae_xz_mev_per_cell"] = "-1.332"
        with self.assertRaisesRegex(ValueError, "must be a JSON number"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
        del artifact["predictions"][0]["exchange_mev"]
        with self.assertRaisesRegex(ValueError, "prediction is incomplete"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
        fm_evidence = artifact["predictions"][0]["ordering_evidence"]["fm"]
        fm_evidence["perpendicular_energy_ev"] += 0.001
        with self.assertRaisesRegex(ValueError, "contradicts ordering evidence"):
            module.enforce_z2_measurement(panel, artifact, row)
        artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
        row["measurements"][0]["acceptance_test"]["outcome"] = "fail"
        with self.assertRaisesRegex(ValueError, "contradictory acceptance outcome"):
            module.enforce_z2_measurement(panel, artifact, row)
        row["measurements"][0]["acceptance_test"]["outcome"] = "pass"
        artifact["predictions"].pop()
        artifact["accuracy"]["completed_material_count"] = 6
        with self.assertRaisesRegex(ValueError, "7/7"):
            module.enforce_z2_measurement(panel, artifact, row)

    def test_reviewed_z2_first_evidence_ingests_transactionally(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            module = load_ingest_module()
            source_panel = ROOT / module.Z2_PANEL_PATH
            panel_path = root / module.Z2_PANEL_PATH
            panel_path.parent.mkdir(parents=True)
            shutil.copy2(source_panel, panel_path)
            panel = json.loads(panel_path.read_text())
            manifest_path = root / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"
            manifest = json.loads(manifest_path.read_text())
            predictions = [
                self.z2_reference_prediction(item) for item in panel["materials"]
            ]
            metrics = self.z2_metrics(panel, predictions)
            artifact = {
                "run_id": "run-z2-bootstrap",
                "campaign_id": module.Z2_CAMPAIGN_ID,
                "row_id": "soc_tc",
                "manifest_hash": module.Z2_MANIFEST_CONTENT_HASH,
                "fixture_contract": {"candidate_panel_sha256": module.Z2_PANEL_SHA256},
                "predictions": predictions,
                "execution": {
                    "runner_image_digest": "sha256:" + "d" * 64,
                    "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
                    "cloud_run_job": "mlip-cell-z2-chgnet",
                },
                "accuracy": metrics,
            }
            artifact_path = root / "data" / "candidates" / "z2" / "complete.json"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text(json.dumps(artifact))
            receipt_relative = Path("evidence/v1/build-receipts/z2-test-build.json")
            receipt_path = root / receipt_relative
            receipt_path.parent.mkdir(parents=True)
            receipt = {
                "schema": "lupine.z2.runner_build_receipt.v1",
                "campaign_id": module.Z2_CAMPAIGN_ID,
                "manifest_hash": module.Z2_MANIFEST_CONTENT_HASH,
                "candidate_panel_sha256": module.Z2_PANEL_SHA256,
                "runner_image_digest": "sha256:" + "d" * 64,
                "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
                "cloud_build_id": "test-build-id",
                "cloud_run_job": "mlip-cell-z2-chgnet",
                "reviewed_by": "test-reviewer",
                "reviewed_at": "2026-08-04T00:00:00Z",
            }
            receipt_path.write_text(json.dumps(receipt, sort_keys=True))
            execution_relative = Path(
                "evidence/v1/execution-receipts/z2-test-execution.json"
            )
            execution_path = root / execution_relative
            execution_path.parent.mkdir(parents=True)
            execution_receipt = {
                "schema": "lupine.z2.runner_execution_receipt.v1",
                "run_id": "run-z2-bootstrap",
                "campaign_id": module.Z2_CAMPAIGN_ID,
                "row_id": "soc_tc",
                "cloud_build_id": "test-build-id",
                "cloud_run_job": "mlip-cell-z2-chgnet",
                "runner_image_digest": "sha256:" + "d" * 64,
                "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
                "reviewed_by": "test-reviewer",
                "reviewed_at": "2026-08-04T00:00:00Z",
            }
            execution_path.write_text(json.dumps(execution_receipt, sort_keys=True))
            measurements = [
                {"metric": "magnetocrystalline_anisotropy_rank_correlation", "value": 1.0, "unit": "spearman_rho", "acceptance_test": {"comparator": "equal", "threshold": 1.0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "easy_axis_sign_errors", "value": 0, "unit": "materials", "acceptance_test": {"comparator": "equal", "threshold": 0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "tc_rnsw_mae_k", "value": metrics["tc_rnsw_mae_k"], "unit": "K", "sample_count": 7},
                {"metric": "tc_envelope_coverage", "value": metrics["tc_envelope_coverage"], "unit": "fraction", "sample_count": 7},
            ]
            row = {
                "row_id": "soc_tc",
                "previous_row_hash": None,
                "campaign_manifest_hash": manifest["content_hash"],
                "claim_id": module.Z2_CLAIM_ID,
                "premise_id": module.Z2_PREMISE_ID,
                "claim_predicate": module.Z2_PREDICATE,
                "epistemic_status": "confirmatory",
                "artifact": artifact_path.relative_to(root).as_posix(),
                "artifact_hash": "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                "run_id": "run-z2-bootstrap",
                "thresholds_version": "z2-soc-tc-v1",
                "scope": {
                    "structures": [item["material_id"] for item in panel["materials"]],
                    "chemistries": [item["formula"] for item in panel["materials"]],
                    "properties": sorted(module.Z2_PROPERTIES),
                    "conditions": {
                        "candidate_panel_sha256": module.Z2_PANEL_SHA256,
                        "locked_material_count": 7,
                    },
                },
                "provenance": {
                    "agent": "test-z2-runner",
                    "human": "reviewed test fixture",
                    "timestamp": "2026-08-04T00:00:00Z",
                    "runner_image_digest": "sha256:" + "d" * 64,
                    "runner_image_uri": "us-docker.pkg.dev/lupine/z2/runner@sha256:" + "d" * 64,
                    "runner_build_receipt": receipt_relative.as_posix(),
                    "runner_build_receipt_hash": "sha256:"
                    + hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                    "runner_execution_receipt": execution_relative.as_posix(),
                    "runner_execution_receipt_hash": "sha256:"
                    + hashlib.sha256(execution_path.read_bytes()).hexdigest(),
                },
                "measurements": measurements,
            }
            row["row_hash"] = "sha256:" + hashlib.sha256(
                module.rfc8785.dumps(
                    {key: value for key, value in row.items() if key != "row_hash"}
                )
            ).hexdigest()
            rows_path = root / "data" / "candidates" / "z2" / "measurements.jsonl"
            failed_prediction = artifact["predictions"][0]
            failed_prediction["mae_yz_mev_per_cell"] = 1.0
            failed_prediction["easy_axis"] = "in_plane"
            fm_evidence = failed_prediction["ordering_evidence"]["fm"]
            fm_evidence["y_energy_ev"] = fm_evidence["perpendicular_energy_ev"] - 0.001
            artifact["accuracy"]["easy_axis_sign_errors"] = 1
            artifact_path.write_text(json.dumps(artifact))
            row["artifact_hash"] = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            row["measurements"][1]["value"] = 1
            row["measurements"][1]["acceptance_test"]["outcome"] = "fail"
            row["row_hash"] = "sha256:" + hashlib.sha256(
                module.rfc8785.dumps(
                    {key: value for key, value in row.items() if key != "row_hash"}
                )
            ).hexdigest()
            rows_path.write_text(json.dumps(row) + "\n")
            failed = subprocess.run(
                [sys.executable, str(INGESTER), "--root", str(root), "--manifest", str(manifest_path), "--measurements", str(rows_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertIn("requires a passing", failed.stderr)
            unchanged_claim = json.loads(
                (root / "registry" / "claims" / f"{module.Z2_CLAIM_ID}.json").read_text()
            )
            self.assertEqual(unchanged_claim["premises"][0]["support_policy"], {"mode": "unsupported"})
            self.assertEqual(unchanged_claim["premises"][0]["bundle_references"], [])

            artifact["predictions"][0] = self.z2_reference_prediction(panel["materials"][0])
            artifact["accuracy"]["easy_axis_sign_errors"] = 0
            artifact_path.write_text(json.dumps(artifact))
            row["artifact_hash"] = "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            row["measurements"][1]["value"] = 0
            row["measurements"][1]["acceptance_test"]["outcome"] = "pass"
            row["row_hash"] = "sha256:" + hashlib.sha256(
                module.rfc8785.dumps(
                    {key: value for key, value in row.items() if key != "row_hash"}
                )
            ).hexdigest()
            rows_path.write_text(json.dumps(row) + "\n")

            result = subprocess.run(
                [sys.executable, str(INGESTER), "--root", str(root), "--manifest", str(manifest_path), "--measurements", str(rows_path)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            claim = json.loads(
                (root / "registry" / "claims" / f"{module.Z2_CLAIM_ID}.json").read_text()
            )
            premise = claim["premises"][0]
            self.assertEqual(premise["support_policy"], {"mode": "all"})
            self.assertEqual(len(premise["bundle_references"]), 1)

    def test_recorded_path_minimum_is_enforced(self) -> None:
        module = load_ingest_module()
        models = ["chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium"]

        def set_canonical(path: str, digest: str) -> None:
            module.CANONICAL_RECORDED_SOURCE = path
            module.CANONICAL_RECORDED_DIGEST = digest

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

        def registered(root: Path, doc: dict) -> dict:
            doc = dict(doc)
            payload = {key: value for key, value in doc.items() if key != "content_hash"}
            doc["content_hash"] = "sha256:" + hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
            ).hexdigest()
            registry_file = root / "registry" / "campaigns.v1.json"
            registry_file.parent.mkdir(parents=True, exist_ok=True)
            existing = (
                json.loads(registry_file.read_text())
                if registry_file.exists()
                else {"campaigns": []}
            )
            existing["campaigns"].append(
                {"campaign_id": doc.get("campaign_id"), "content_hash": doc["content_hash"]}
            )
            registry_file.write_text(json.dumps(existing))
            return doc

        full_rows = [
            {
                "path_index": index,
                "path_id": f"mp-{1000 + index}_0_0_0_0_0",
                "chemical_system": f"Chem-{index}",
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
                        "chemical_system": f"Chem-{index}",
                        "reference_barrier_ev": round(5.0 + index * 0.01, 9),
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
            set_canonical("locked.json", "sha256:" + hashlib.sha256(locked_bytes).hexdigest())
            canonical_dir = root / "data" / "candidates"
            canonical_dir.mkdir(parents=True)
            canonical_document = {
                "per_path": [
                    {
                        "path_index": index,
                        "path_id": f"mp-{7000 + index}_0_0_0_0_0",
                        "chemical_system": f"Li-{index}",
                        "reference_barrier_ev": round(9.0 + index * 0.01, 9),
                        "per_model": {
                            model: {"vasp_signed_error_mev": 999.0, "complete": True}
                            for model in models
                        },
                        "models_missing": {},
                    }
                    for index in range(22)
                ]
            }
            (canonical_dir / "z1-union-campaign.json").write_text(json.dumps(canonical_document))
            panel_bytes = json.dumps(
                {
                    "paths": [
                        {"path_id": f"mp-{1000 + index}_0_0_0_0_0", "chemical_system": f"Chem-{index}"} for index in range(24)
                    ]
                }
            ).encode()
            (root / "panel.json").write_bytes(panel_bytes)
            canonical_entries = {
                "chgnet": ("sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890", "chgnet 0.4.2"),
                "mace-mp-small": ("sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694", "mace-torch 0.3.16 / small"),
                "mace-mp-medium": ("sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3", "mace-torch 0.3.16 / medium"),
                "mace-mpa-0-medium": ("sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9", "mace-torch 0.3.16 / mpa-0 medium"),
            }
            manifest = {
                "campaign_id": "literature.protocol-offset-sign-skew.v1",
                "execution": {
                    "candidate_panel": {
                        "path": "panel.json",
                        "sha256": "sha256:" + hashlib.sha256(panel_bytes).hexdigest(),
                    }
                },
                "available_models": [
                    {
                        "model_id": model,
                        "artifact_hash": canonical_entries[model][0],
                        "version": canonical_entries[model][1],
                    }
                    for model in models
                ],
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
                module.enforce_path_minimums(root, registered(root, manifest), bundle, artifact, "skew-1")

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
                        "chemical_system": f"Chem-{index}",
                        "reference_barrier_ev": round(5.0 + index * 0.01, 9),
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
            set_canonical("locked-failed.json", "sha256:" + hashlib.sha256(failed_bytes).hexdigest())
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
                     "chemical_system": f"Chem-{index}",
                     "model": model, "status": "failed", "reason": "failed"}
                    for index in range(1, 22)
                    for model in models
                ],
            )
            with self.assertRaisesRegex(ValueError, "paths with measurements"):
                module.enforce_path_minimums(
                    root, registered(root, failed_manifest), make_bundle(fraction=1.0, sample_count=1), artifact, "skew-1"
                )
            set_canonical("locked.json", "sha256:" + hashlib.sha256(locked_bytes).hexdigest())

            # Six paths measured by four models must not launder the minimum:
            # the locked source's remaining pairs are undisclosed.
            write_artifact(
                artifact,
                [row for row in full_rows if row["path_index"] < 6],
            )
            with self.assertRaisesRegex(ValueError, "cherry-picks the locked source"):
                enforce(make_bundle(sample_count=22))

            # Twenty-two paths from a single model leave the locked source's
            # other model records undisclosed.
            write_artifact(
                artifact,
                [row for row in full_rows if row["model"] == "chgnet"],
            )
            with self.assertRaisesRegex(ValueError, "cherry-picks the locked source"):
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
            set_canonical("locked-pair.json", "sha256:" + hashlib.sha256(pair_bytes).hexdigest())
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
                        "chemical_system": "Chem-13",
                        "model": "mace-mp-small",
                        "status": "failed",
                        "reason": "failed",
                    }
                ],
            )
            module.enforce_path_minimums(root, registered(root, pair_manifest), make_bundle(), artifact, "skew-1")
            set_canonical("locked.json", "sha256:" + hashlib.sha256(locked_bytes).hexdigest())

            # Submitted statistics must match the artifact's own rows.
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "recomputed value"):
                enforce(make_bundle(fraction=0.9))
            with self.assertRaisesRegex(ValueError, "recomputed value"):
                enforce(make_bundle(median=460.14))
            # The exact unrounded ratio and the declared 4-decimal rounding both pass.
            enforce(make_bundle(fraction=1.0))

            # An asserted outcome that contradicts its own value is rejected here,
            # not left to abort the downstream nightly feedback.
            lying = make_bundle()
            lying["measurements"][0]["acceptance_test"]["outcome"] = "fail"
            with self.assertRaisesRegex(ValueError, "asserts outcome"):
                enforce(lying)

            # Rows for models outside execution.model_selection are rejected.
            write_artifact(
                artifact,
                full_rows
                + [
                    {
                        "path_index": 0,
                        "path_id": "mp-1000_0_0_0_0_0",
                        "chemical_system": "Chem-0",
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

            # Non-finite values inside the locked source are rejected too.
            nan_source = json.loads(locked_bytes)
            nan_source["per_path"][0]["per_model"]["chgnet"]["vasp_signed_error_mev"] = float("nan")
            (root / "nan-locked.json").write_text(json.dumps(nan_source))
            nan_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "nan-locked.json",
                            "sha256": "sha256:" + hashlib.sha256((root / "nan-locked.json").read_bytes()).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "non-finite"):
                module.enforce_path_minimums(root, registered(root, nan_manifest), make_bundle(), artifact, "skew-1")

            # Duplicate stable path identities cannot inflate a copied dataset.
            dupe_document = json.loads(locked_bytes)
            dupe_document["per_path"].append(
                {
                    "path_index": 99,
                    "path_id": "mp-1000_0_0_0_0_0",
                    "per_model": {},
                    "models_missing": {model: "failed" for model in models},
                }
            )
            dupe_bytes = json.dumps(dupe_document).encode()
            (root / "dupe-locked.json").write_bytes(dupe_bytes)
            dupe_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "dupe-locked.json",
                            "sha256": "sha256:" + hashlib.sha256(dupe_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "duplicate stable path identities"):
                module.enforce_path_minimums(root, registered(root, dupe_manifest), make_bundle(), artifact, "skew-1")

            # Duplicate path indices with different identities are rejected too.
            dupe_index_document = json.loads(locked_bytes)
            dupe_index_document["per_path"].append(
                {
                    "path_index": 0,
                    "path_id": "mp-5555_0_0_0_0_0",
                    "per_model": {
                        model: {"vasp_signed_error_mev": 999.0, "complete": True}
                        for model in models
                    },
                    "models_missing": {},
                }
            )
            dupe_index_bytes = json.dumps(dupe_index_document).encode()
            (root / "dupe-index-locked.json").write_bytes(dupe_index_bytes)
            dupe_index_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "dupe-index-locked.json",
                            "sha256": "sha256:" + hashlib.sha256(dupe_index_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "duplicate stable path identities"):
                module.enforce_path_minimums(root, registered(root, dupe_index_manifest), make_bundle(), artifact, "skew-1")

            # The artifact must disclose the locked source's complete pair set.
            large_document = json.loads(locked_bytes)
            for extra in (22, 23):
                large_document["per_path"].append(
                    {
                        "path_index": extra,
                        "path_id": f"mp-{1000 + extra}_0_0_0_0_0",
                        "chemical_system": f"Chem-{extra}",
                        "per_model": {
                            model: {"vasp_signed_error_mev": -900.0, "complete": True}
                            for model in models
                        },
                        "models_missing": {},
                    }
                )
            large_bytes = json.dumps(large_document).encode()
            (root / "large-locked.json").write_bytes(large_bytes)
            large_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "large-locked.json",
                            "sha256": "sha256:" + hashlib.sha256(large_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "cherry-picks the locked source"):
                module.enforce_path_minimums(root, registered(root, large_manifest), make_bundle(), artifact, "skew-1")

            # Typed receipt values must be finite numbers.
            write_artifact(artifact, full_rows)
            nan_bundle = make_bundle()
            nan_bundle["measurements"][0]["value"] = float("nan")
            with self.assertRaisesRegex(ValueError, "non-finite typed value"):
                enforce(nan_bundle)

            # Non-finite signed errors are rejected before any comparison.
            artifact.write_text(
                json.dumps({"per_row": full_rows}).replace(
                '"signed_error_mev": 500.0', '"signed_error_mev": NaN', 1
                )
            )
            with self.assertRaisesRegex(ValueError, "finite numeric"):
                enforce(make_bundle())

            # A cloned manifest under a fresh campaign_id is not replication.
            write_artifact(artifact, full_rows)
            clone_manifest = {**manifest, "campaign_id": "literature.clone.v1"}
            with self.assertRaisesRegex(ValueError, "not the canonical"):
                module.enforce_path_minimums(root, registered(root, clone_manifest), make_bundle(), artifact, "skew-1")

            # A manifest pointing at anything but the canonical source is rejected.
            write_artifact(artifact, full_rows)
            foreign_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [{"path": "other.json", "sha256": manifest["preregistration"]["recorded_inputs"][0]["sha256"]}]
                },
            }
            with self.assertRaisesRegex(ValueError, "partially matches the canonical"):
                module.enforce_path_minimums(root, registered(root, foreign_manifest), make_bundle(), artifact, "skew-1")

            # The canonical digest is verified against the actual source bytes.
            tampered_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": [{"path": "locked.json", "sha256": "sha256:" + "0" * 64}]
                },
            }
            with self.assertRaisesRegex(ValueError, "partially matches the canonical"):
                module.enforce_path_minimums(root, registered(root, tampered_manifest), make_bundle(), artifact, "skew-1")
            (root / "locked.json").write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                module.enforce_path_minimums(root, registered(root, manifest), make_bundle(), artifact, "skew-1")
            (root / "locked.json").write_bytes(locked_bytes)

            # The canonical neb-path-set requirement itself must be present.
            write_artifact(artifact, full_rows)
            bare_manifest = {**manifest, "evidence_requirements": []}
            with self.assertRaisesRegex(ValueError, "lacks the canonical neb-path-set"):
                module.enforce_path_minimums(root, registered(root, bare_manifest), make_bundle(), artifact, "skew-1")

            # Manifests with multiple recorded inputs cannot be reconciled.
            multi_manifest = {
                **manifest,
                "preregistration": {
                    "recorded_inputs": manifest["preregistration"]["recorded_inputs"] * 2
                },
            }
            with self.assertRaisesRegex(ValueError, "exactly one locked recorded input"):
                module.enforce_path_minimums(root, registered(root, multi_manifest), make_bundle(), artifact, "skew-1")

            # The path floor is pinned to the frozen panel, not the caller's manifest.
            lax_manifest = {
                **manifest,
                "evidence_requirements": [
                    {
                        "requirement_id": "e.z1.recorded-path-set",
                        "artifact_type": "neb-path-set",
                        "description": "recorded rows",
                        "minimum_count": 1,
                    }
                ],
            }
            with self.assertRaisesRegex(ValueError, "frozen sign-skew (panel|claim)"):
                module.enforce_path_minimums(root, registered(root, lax_manifest), make_bundle(), artifact, "skew-1")

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

            # Genuinely independent campaigns remain reachable with their own
            # locked dataset; an omitted lock is rejected, not trusted.
            fresh_manifest = {
                key: value for key, value in manifest.items() if key != "preregistration"
            }
            fresh_manifest["campaign_id"] = "literature.protocol-offset-sign-skew.v2"
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "omitted lock"):
                module.enforce_path_minimums(root, registered(root, fresh_manifest), make_bundle(), artifact, "skew-1")

            fresh_document = {
                "per_path": [
                    {
                        "path_index": index,
                        "path_id": f"mp-{2000 + index}_0_0_0_0_0",
                        "chemical_system": f"Fresh-{index}",
                        "reference_barrier_ev": round(7.0 + index * 0.01, 9),
                        "per_model": {
                            model: {"vasp_signed_error_mev": 500.0, "complete": True}
                            for model in models
                        },
                        "models_missing": {},
                    }
                    for index in range(22)
                ]
            }
            fresh_bytes = json.dumps(fresh_document).encode()
            (root / "fresh-locked.json").write_bytes(fresh_bytes)
            fresh_manifest["preregistration"] = {
                "recorded_inputs": [
                    {
                        "path": "fresh-locked.json",
                        "sha256": "sha256:" + hashlib.sha256(fresh_bytes).hexdigest(),
                    }
                ]
            }
            fresh_panel_bytes = json.dumps(
                {"paths": [{"path_id": f"mp-{2000 + index}_0_0_0_0_0", "chemical_system": f"Fresh-{index}"} for index in range(22)]}
            ).encode()
            (root / "fresh-panel.json").write_bytes(fresh_panel_bytes)
            fresh_manifest["execution"] = {
                "candidate_panel": {
                    "path": "fresh-panel.json",
                    "sha256": "sha256:" + hashlib.sha256(fresh_panel_bytes).hexdigest(),
                }
            }
            fresh_rows = [
                {**row, "path_id": f"mp-{2000 + row['path_index']}_0_0_0_0_0", "chemical_system": f"Fresh-{row['path_index']}"}
                for row in full_rows
            ]
            write_artifact(artifact, fresh_rows)
            module.enforce_path_minimums(root, registered(root, fresh_manifest), make_bundle(), artifact, "skew-1")

            # A second campaign over the same independent dataset is not replication.
            prior_dir = root / "evidence" / "v1" / "examples"
            prior_dir.mkdir(parents=True)
            (prior_dir / "prior.json").write_text(
                json.dumps(
                    {
                        "claim_predicate": "signed_error_positive_fraction>0.5",
                        "evidence_refs": [
                            {
                                "campaign": "literature.protocol-offset-sign-skew.v2",
                                "dataset_fingerprint": module._source_fingerprint(fresh_document),
                            }
                        ],
                    }
                )
            )
            duplicate_manifest = {**fresh_manifest, "campaign_id": "literature.dup.v3"}
            with self.assertRaisesRegex(ValueError, "not independent replication"):
                module.enforce_path_minimums(root, registered(root, duplicate_manifest), make_bundle(), artifact, "skew-1")
            # The same campaign re-ingesting its own dataset remains idempotent.
            returned = module.enforce_path_minimums(root, registered(root, fresh_manifest), make_bundle(), artifact, "skew-1")
            self.assertEqual(returned, module._source_fingerprint(fresh_document))

            # Generated bundles persist the fingerprint for later deduplication.
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({**fresh_manifest, "preregistration_id": "prereg.test.v1"}))
            row = {
                "row_id": "skew-1",
                "claim_predicate": "signed_error_positive_fraction>0.5",
                "epistemic_status": "confirmatory",
                "artifact": "artifact.json",
                "artifact_hash": "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "run_id": "run-skew-1",
                "thresholds_version": "v1",
                "scope": {
                    "structures": ["mp-2000"],
                    "chemistries": ["Li"],
                    "properties": ["migration_barrier"],
                    "conditions": {"panel": "fresh"},
                },
                "provenance": {
                    "agent": "test",
                    "human": "test",
                    "timestamp": "2026-08-01T00:00:00Z",
                },
                "measurements": make_bundle()["measurements"],
            }
            generated = module.bundle_from_row(root, manifest_path, registered(root, {**fresh_manifest, "preregistration_id": "prereg.test.v1"}), row)
            self.assertEqual(
                generated["evidence_refs"][0]["dataset_fingerprint"],
                module._source_fingerprint(fresh_document),
            )

            # A renamed clone is caught by panel reconciliation; the panel digest
            # itself is verified against the manifest pin.
            renamed_document = json.loads(locked_bytes)
            renamed_document["per_path"][0]["path_id"] = "mp-9999_0_0_0_0_0"
            renamed_bytes = json.dumps(renamed_document).encode()
            (root / "renamed.json").write_bytes(renamed_bytes)
            renamed_manifest = {
                **manifest,
                "campaign_id": "literature.renamed.v1",
                "preregistration": {
                    "recorded_inputs": [
                        {
                            "path": "renamed.json",
                            "sha256": "sha256:" + hashlib.sha256(renamed_bytes).hexdigest(),
                        }
                    ]
                },
            }
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "frozen candidate panel"):
                module.enforce_path_minimums(root, registered(root, renamed_manifest), make_bundle(), artifact, "skew-1")

            bad_panel_manifest = {
                **manifest,
                "execution": {
                    "candidate_panel": {"path": "panel.json", "sha256": "sha256:" + "2" * 64}
                },
            }
            with self.assertRaisesRegex(ValueError, "panel digest mismatch"):
                module.enforce_path_minimums(root, registered(root, bad_panel_manifest), make_bundle(), artifact, "skew-1")

            # Independent campaigns must still measure the frozen 22-path claim.
            lax_fresh = {
                **fresh_manifest,
                "evidence_requirements": [
                    {
                        "requirement_id": "e.z1.recorded-path-set",
                        "artifact_type": "neb-path-set",
                        "description": "recorded rows",
                        "minimum_count": 1,
                    }
                ],
            }
            with self.assertRaisesRegex(ValueError, "frozen sign-skew claim"):
                module.enforce_path_minimums(root, registered(root, lax_fresh), make_bundle(), artifact, "skew-1")

            # Near-clones of the canonical dataset are rejected in both directions.
            subset_document = json.loads(json.dumps(canonical_document))
            subset_document["per_path"][0]["per_model"].pop("chgnet")
            subset_bytes = json.dumps(subset_document).encode()
            (root / "subset.json").write_bytes(subset_bytes)
            canonical_panel_bytes = json.dumps(
                {"paths": [{"path_id": f"mp-{7000 + index}_0_0_0_0_0"} for index in range(23)]}
            ).encode()
            (root / "canonical-panel.json").write_bytes(canonical_panel_bytes)
            canonical_panel_lock = {
                "path": "canonical-panel.json",
                "sha256": "sha256:" + hashlib.sha256(canonical_panel_bytes).hexdigest(),
            }
            subset_manifest = {
                **fresh_manifest,
                "execution": {"candidate_panel": canonical_panel_lock},
                "preregistration": {
                    "recorded_inputs": [
                        {"path": "subset.json", "sha256": "sha256:" + hashlib.sha256(subset_bytes).hexdigest()}
                    ]
                },
            }
            write_artifact(artifact, fresh_rows)
            with self.assertRaisesRegex(ValueError, "reuses canonical path/model provenance"):
                module.enforce_path_minimums(root, registered(root, subset_manifest), make_bundle(), artifact, "skew-1")
            superset_document = json.loads(json.dumps(canonical_document))
            superset_document["per_path"].append(
                {
                    "path_index": 22,
                    "path_id": "mp-7022_0_0_0_0_0",
                    "chemical_system": "Li-22",
                    "per_model": {
                        model: {"vasp_signed_error_mev": 999.0, "complete": True}
                        for model in models
                    },
                    "models_missing": {},
                }
            )
            superset_bytes = json.dumps(superset_document).encode()
            (root / "superset.json").write_bytes(superset_bytes)
            superset_manifest = {
                **fresh_manifest,
                "execution": {"candidate_panel": canonical_panel_lock},
                "preregistration": {
                    "recorded_inputs": [
                        {"path": "superset.json", "sha256": "sha256:" + hashlib.sha256(superset_bytes).hexdigest()}
                    ]
                },
            }
            write_artifact(artifact, fresh_rows)
            with self.assertRaisesRegex(ValueError, "reuses canonical path/model provenance"):
                module.enforce_path_minimums(root, registered(root, superset_manifest), make_bundle(), artifact, "skew-1")

            # A reserialized copy of the same observations is the same dataset.
            module.CANONICAL_SOURCE_FINGERPRINT = module._source_fingerprint(locked_document)
            copy_manifest = {
                **manifest,
                "campaign_id": "literature.copy.v1",
                "preregistration": {
                    "recorded_inputs": [{"path": "copy.json", "sha256": "sha256:" + "1" * 64}]
                },
            }
            (root / "copy.json").write_text(json.dumps(locked_document, indent=2, sort_keys=True))
            copy_manifest["preregistration"]["recorded_inputs"][0]["sha256"] = (
                "sha256:" + hashlib.sha256((root / "copy.json").read_bytes()).hexdigest()
            )
            write_artifact(artifact, full_rows)
            with self.assertRaisesRegex(ValueError, "reserializes the canonical dataset"):
                module.enforce_path_minimums(root, registered(root, copy_manifest), make_bundle(), artifact, "skew-1")

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
