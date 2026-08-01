"""Acceptance tests for the campaign-manifest v1 JSON Schema."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]


def load(relative_path: str) -> dict:
    with (ROOT / relative_path).open(encoding="utf-8") as stream:
        return json.load(stream)


class CampaignManifestSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest_schema = load("schemas/campaign-manifest.v1.schema.json")
        Draft202012Validator.check_schema(cls.manifest_schema)
        cls.manifest_validator = Draft202012Validator(cls.manifest_schema)

    def test_round_4_manifest_with_uma_exclusion_passes(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        self.manifest_validator.validate(manifest)
        self.assertTrue(
            any(
                exclusion["subject"] == "UMA"
                and exclusion["disposition"] == "deprioritized"
                for exclusion in manifest["exclusions"]
            )
        )

    def test_condition_action_must_match_its_block(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        manifest["kill_conditions"][0]["action"] = "demote"
        with self.assertRaises(ValidationError):
            self.manifest_validator.validate(manifest)

    def test_manifest_requires_explicit_exclusions_block(self) -> None:
        manifest = load("examples/campaign-manifest.round-4.v1.json")
        del manifest["exclusions"]
        with self.assertRaises(ValidationError):
            self.manifest_validator.validate(manifest)

    def test_discovery_chain_manifests_are_frozen_and_content_addressed(self) -> None:
        paths = sorted((ROOT / "campaigns" / "v1").glob("*.json"))
        self.assertEqual(
            [path.stem.split(".")[0] for path in paths],
            ["correction-round4", "literature-protocol-offset-sign-skew", "z1", "z1r5", "z2", "z3"],
        )

        for path in paths:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            self.manifest_validator.validate(manifest)
            unhashed = {key: value for key, value in manifest.items() if key != "content_hash"}
            canonical = json.dumps(
                unhashed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            expected = "sha256:" + hashlib.sha256(canonical).hexdigest()
            self.assertEqual(manifest["content_hash"], expected)
            self.assertTrue(manifest["preregistration"]["frozen_before_execution"])
            self.assertTrue(all(item["frozen"] for item in manifest["frozen_hypotheses"]))
            self.assertTrue(manifest["evidence_requirements"])

    def test_discovery_chain_acceptance_tests_are_exact(self) -> None:
        manifests = {
            path.stem.split(".")[0]: json.loads(path.read_text(encoding="utf-8"))
            for path in (ROOT / "campaigns" / "v1").glob("*.json")
        }
        self.assertEqual(
            manifests["z1"]["acceptance_test"],
            {"metric": "barrier_mae", "operator": "lte", "threshold": 40, "unit": "meV"},
        )
        self.assertEqual(
            manifests["z2"]["acceptance_test"],
            {"metric": "magnetocrystalline_anisotropy_rank_correlation", "operator": "eq", "threshold": 1, "unit": "spearman_rho"},
        )
        self.assertEqual(
            manifests["z3"]["acceptance_test"],
            {"metric": "adsorption_energy_mae", "operator": "lte", "threshold": 0.1, "unit": "eV"},
        )

    def test_exclusions_do_not_block_available_models(self) -> None:
        for path in (ROOT / "campaigns" / "v1").glob("*.json"):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            available = {model["model_id"] for model in manifest["available_models"]}
            excluded = {item["subject"] for item in manifest["exclusions"]}
            self.assertTrue(available)
            self.assertTrue(available.isdisjoint(excluded))
            self.assertFalse(manifest["execution"]["excluded_models_block_execution"])


if __name__ == "__main__":
    unittest.main()
