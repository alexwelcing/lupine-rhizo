"""Acceptance tests for the generated assumption registry."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools" / "generate_assumptions.py"

# Tests may be invoked from the python/ directory; ensure the repo root is on
# sys.path so ``from tools.generate_assumptions import ...`` resolves.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generate_assumptions import derive_assumption


class AssumptionsGeneratorTests(unittest.TestCase):
    def test_no_bundle_is_unsupported_even_if_contract_claims_active(self) -> None:
        claim = {
            "claim_id": "example.unsupported.v1",
            "version": 1,
            "content_hash": "sha256:" + "0" * 64,
            "statement": "An unsupported test claim.",
            "classification": {"assurance": "active"},
            "premises": [
                {
                    "premise_id": "missing_evidence",
                    "support_policy": {"mode": "unsupported"},
                    "bundle_references": [],
                }
            ],
        }

        assumption = derive_assumption(claim, {})

        self.assertEqual(assumption["status"], "unsupported")
        self.assertEqual(assumption["disposition"], "unsupported")

    def test_generator_derives_active_and_withdrawn_statuses_from_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(ROOT),
                    "--output-root",
                    str(output_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry = json.loads(
                (output_root / "registry" / "assumptions.v1.json").read_text(
                    encoding="utf-8"
                )
            )

        statuses = {
            assumption["claim_id"]: (
                assumption["status"],
                assumption["disposition"],
            )
            for assumption in registry["assumptions"]
        }
        self.assertEqual(
            statuses,
            {
                "correction.b0.v1": ("withdrawn", "refuted"),
                "correction.same_class.a0.v1": ("active", "supported"),
                "fcc.b0.anticorrelation.v1": ("withdrawn", "refuted"),
            },
        )

    def test_check_detects_hand_edited_generated_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            generate = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(ROOT),
                    "--output-root",
                    str(output_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(generate.returncode, 0, generate.stderr)
            registry_path = output_root / "registry" / "assumptions.v1.json"
            registry_path.write_text("{}\n", encoding="utf-8")

            check = subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(ROOT),
                    "--output-root",
                    str(output_root),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(check.returncode, 0)
        self.assertIn("stale generated file", check.stderr)
        self.assertIn("run tools/generate_assumptions.py to refresh", check.stderr)

    def test_checked_in_outputs_round_trip_through_generator(self) -> None:
        check = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--root",
                str(ROOT),
                "--check",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 0, check.stderr)

        registry = json.loads(
            (ROOT / "registry" / "assumptions.v1.json").read_text(encoding="utf-8")
        )
        lock = json.loads(
            (ROOT / "registry" / "snapshots" / "current.lock.json").read_text(
                encoding="utf-8"
            )
        )
        canonical = json.dumps(
            registry, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        expected_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()
        self.assertEqual(
            lock["artifacts"]["registry/assumptions.v1.json"]["content_hash"],
            expected_hash,
        )


if __name__ == "__main__":
    unittest.main()
