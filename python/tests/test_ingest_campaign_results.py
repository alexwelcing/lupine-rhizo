"""End-to-end tests for Round-4 campaign result ingestion."""

from __future__ import annotations

import hashlib
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

    def test_synthetic_round4_fixture_ingests_and_materializes_new_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            old_lock = json.loads(
                (root / "registry" / "snapshots" / "current.lock.json").read_text()
            )

            result = self.invoke(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            created = sorted((root / "evidence" / "v1" / "examples").glob("round4-*.json"))
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

    def test_manifest_that_violates_round4_schema_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
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
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))

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
            measurements_path = (
                root / "python" / "tests" / "fixtures" / "round4_ingest" / "measurements.jsonl"
            )
            rows = [json.loads(line) for line in measurements_path.read_text().splitlines()]
            rows[1]["previous_row_hash"] = "sha256:" + "0" * 64
            measurements_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("measurement hash chain is broken", result.stderr)
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))

    def test_scope_outside_baseline_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
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
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))

    def test_missing_evidence_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
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
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))

    def test_tampered_claim_contract_fails_instead_of_laundering_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
            claim_path = root / "registry" / "claims" / f"{CLAIM_ID}.json"
            claim = json.loads(claim_path.read_text())
            claim["statement"] = "Tampered without updating content_hash"
            claim_path.write_text(json.dumps(claim, indent=2) + "\n")
            before_claim = claim_path.read_bytes()

            result = self.invoke(root)

            self.assertEqual(result.returncode, 2)
            self.assertIn("non-canonical ClaimContract content_hash", result.stderr)
            self.assertEqual(claim_path.read_bytes(), before_claim)
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))

    def test_claim_predicate_outside_baseline_contract_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            self.prepare_root(root)
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
            self.assertFalse(list((root / "evidence" / "v1" / "examples").glob("round4-*.json")))


if __name__ == "__main__":
    unittest.main()
