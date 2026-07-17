"""Acceptance tests for the campaign-manifest v1 JSON Schema."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


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


if __name__ == "__main__":
    unittest.main()
