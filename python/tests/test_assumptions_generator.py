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

from tools.generate_assumptions import (  # noqa: E402
    content_hash,
    derive_assumption,
    load_campaign_registry,
)


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
                "barrier.accuracy.z1.v1": ("withdrawn", "refuted"),
                "correction.b0.v1": ("withdrawn", "refuted"),
                "correction.same_class.a0.v1": ("active", "supported"),
                "discovery.z1.barrier-accuracy.v1": ("withdrawn", "refuted"),
                "discovery.z2.magnetic-anisotropy.v1": ("unsupported", "unsupported"),
                "discovery.z3.adsorption-accuracy.v1": ("withdrawn", "refuted"),
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

        campaigns = json.loads(
            (ROOT / "registry" / "campaigns.v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [campaign["campaign_id"] for campaign in campaigns["campaigns"]],
            [
                "correction.round-4.available-models.v1",
                "correction.round-5.optimal-bias-grouping-heldout.v4",
                "correction.round-5.optimal-bias.v3",
                "correction.round-5.sharp-license.v1",
                "correction.round-5.sharp-license.v2",
                "discovery.round-4.z1-barriers.v1",
                "discovery.round-4.z2-magnetic-anisotropy.v1",
                "discovery.round-4.z3-adsorption.v1",
                "discovery.round-5.z1-correction-train.v1",
                "literature.protocol-offset-sign-skew.v1",
            ],
        )
        self.assertEqual(len(lock["inputs"]["campaign_manifests"]), 10)
        self.assertIn("registry/campaigns.v1.json", lock["artifacts"])

    def test_campaign_loader_rejects_a_stale_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            campaign_directory = root / "campaigns" / "v1"
            campaign_directory.mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            manifest["acceptance_test"]["threshold"] = 41
            (campaign_directory / "z1.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "non-canonical CampaignManifest"):
                load_campaign_registry(root)

    def test_campaign_loader_rejects_an_included_and_excluded_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            campaign_directory = root / "campaigns" / "v1"
            campaign_directory.mkdir(parents=True)
            manifest = json.loads(
                (ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            manifest["available_models"][0]["model_id"] = "uma-family"
            manifest["content_hash"] = content_hash(
                {key: value for key, value in manifest.items() if key != "content_hash"}
            )
            (campaign_directory / "z1.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "both includes and excludes"):
                load_campaign_registry(root)


if __name__ == "__main__":
    unittest.main()
