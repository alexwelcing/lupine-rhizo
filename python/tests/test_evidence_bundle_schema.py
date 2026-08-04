"""Acceptance tests for the EvidenceBundle v1 JSON Schema."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "evidence" / "v1" / "schema.json"
EXAMPLES_DIR = ROOT / "evidence" / "v1" / "examples"
EXAMPLES = tuple(sorted(EXAMPLES_DIR.glob("*.json")))

REQUIRED_FIELDS = (
    "bundle_id",
    "claim_predicate",
    "epistemic_status",
    "scope",
    "evidence_refs",
    "provenance",
    "supersedes",
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_payload_hash(bundle: dict) -> str:
    payload = {key: value for key, value in bundle.items() if key != "bundle_id"}
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


class EvidenceBundleSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def test_all_round3_examples_validate_and_are_content_addressed(self) -> None:
        self.assertTrue(EXAMPLES, "no example bundles found")
        for path in EXAMPLES:
            with self.subTest(path=path.name):
                bundle = load_json(path)
                self.validator.validate(bundle)
                self.assertEqual(bundle["bundle_id"], canonical_payload_hash(bundle))

    def test_required_receipt_fields_cannot_be_removed(self) -> None:
        bundle = load_json(EXAMPLES[0])
        for field in REQUIRED_FIELDS:
            with self.subTest(field=field):
                invalid = dict(bundle)
                invalid.pop(field)
                self.assertTrue(list(self.validator.iter_errors(invalid)))

    def test_hashes_require_explicit_sha256_identifiers(self) -> None:
        bundle = load_json(EXAMPLES[0])
        bundle["evidence_refs"][0]["artifact_hash"] = "not-a-content-hash"
        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_scope_requires_every_dimension(self) -> None:
        bundle = load_json(EXAMPLES[0])
        del bundle["scope"]["conditions"]
        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_epistemic_status_is_closed_vocabulary(self) -> None:
        bundle = load_json(EXAMPLES[0])
        bundle["epistemic_status"] = "proven"
        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_barrier_mae_predicate_requires_typed_measurement(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "hard-materials-z1-barrier-accuracy.json"
        )
        del bundle["measurements"]

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_barrier_measurement_rejects_non_mev_units(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "hard-materials-z1-barrier-accuracy.json"
        )
        bundle["measurements"][0]["unit"] = "eV"

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_sign_skew_predicate_requires_typed_measurement(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        del bundle["measurements"]

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_sign_skew_measurement_rejects_wrong_unit_and_comparator(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        bundle["measurements"][0]["unit"] = "meV"

        self.assertTrue(list(self.validator.iter_errors(bundle)))

        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        bundle["measurements"][0]["acceptance_test"]["comparator"] = (
            "less_than_or_equal"
        )

        self.assertTrue(list(self.validator.iter_errors(bundle)))

        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        bundle["measurements"][0]["acceptance_test"]["threshold"] = 0.1

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_measurement_types_are_tied_to_the_claim_predicate(self) -> None:
        barrier_bundle = load_json(
            EXAMPLES_DIR / "hard-materials-z1-barrier-accuracy.json"
        )
        barrier_bundle["measurements"][0] = {
            "metric": "signed_error_positive",
            "value": 0.9,
            "unit": "fraction",
            "acceptance_test": {
                "comparator": "greater_than",
                "threshold": 0.5,
                "outcome": "pass",
            },
            "sample_count": 22,
        }

        self.assertTrue(list(self.validator.iter_errors(barrier_bundle)))

        skew_bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        skew_bundle["measurements"][0] = {
            "metric": "barrier_mae",
            "value": 30.0,
            "unit": "meV",
            "acceptance_test": {
                "comparator": "less_than_or_equal",
                "threshold": 40,
                "outcome": "pass",
            },
            "sample_count": 8,
        }

        self.assertTrue(list(self.validator.iter_errors(skew_bundle)))

    def test_sign_skew_requires_the_complete_acceptance_suite(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        fraction_only = [item for item in bundle["measurements"] if item["metric"] == "signed_error_positive"]
        bundle["measurements"] = fraction_only

        self.assertTrue(list(self.validator.iter_errors(bundle)))

        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        bundle["measurements"] = [
            item
            for item in bundle["measurements"]
            if not (
                item["metric"] == "median_signed_error"
                and item["acceptance_test"]["comparator"] == "less_than_or_equal"
            )
        ]

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_sign_skew_receipts_must_carry_the_dataset_fingerprint(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        del bundle["evidence_refs"][0]["dataset_fingerprint"]

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_sign_skew_predicate_is_the_single_frozen_const(self) -> None:
        bundle = load_json(
            EXAMPLES_DIR / "protocol-offset-sign-skew-confirmatory.json"
        )
        bundle["claim_predicate"] = "signed_error_positive_fraction>0.6"

        self.assertTrue(list(self.validator.iter_errors(bundle)))

    def test_z2_receipt_requires_all_four_typed_metrics_at_locked_cardinality(self) -> None:
        bundle = {
            "bundle_id": "sha256:" + "a" * 64,
            "claim_predicate": "magnetocrystalline_anisotropy_rank_correlation==1",
            "epistemic_status": "confirmatory",
            "scope": {
                "structures": ["material-1"],
                "chemistries": ["CrI3"],
                "properties": [
                    "magnetocrystalline_anisotropy_rank",
                    "easy_axis",
                    "curie_temperature",
                ],
                "conditions": {"locked_material_count": 7},
            },
            "evidence_refs": [{
                "campaign": "discovery.round-4.z2-magnetic-anisotropy.v1",
                "campaign_manifest": "campaigns/v1/z2.campaign-manifest.v1.json",
                "campaign_manifest_hash": "sha256:" + "b" * 64,
                "run_id": "z2-run",
                "artifact": "data/candidates/z2/result.json",
                "artifact_hash": "sha256:" + "c" * 64,
                "thresholds_version": "z2-soc-tc-v1",
            }],
            "provenance": {
                "agent": "test",
                "human": "reviewer",
                "timestamp": "2026-08-04T00:00:00Z",
                "preregistration_id": "prereg.discovery.round-4.z2.2026-07-18",
            },
            "measurements": [
                {"metric": "magnetocrystalline_anisotropy_rank_correlation", "value": 1.0, "unit": "spearman_rho", "acceptance_test": {"comparator": "equal", "threshold": 1.0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "easy_axis_sign_errors", "value": 0, "unit": "materials", "acceptance_test": {"comparator": "equal", "threshold": 0, "outcome": "pass"}, "sample_count": 7},
                {"metric": "tc_rnsw_mae_k", "value": 12.5, "unit": "K", "sample_count": 7},
                {"metric": "tc_envelope_coverage", "value": 0.5, "unit": "fraction", "sample_count": 7},
            ],
            "supersedes": [],
        }

        self.assertFalse(list(self.validator.iter_errors(bundle)))
        wrong_predicate = json.loads(json.dumps(bundle))
        wrong_predicate["claim_predicate"] = (
            "magnetocrystalline_anisotropy_rank_correlation==0.9"
        )
        self.assertTrue(list(self.validator.iter_errors(wrong_predicate)))
        bundle["measurements"][0]["sample_count"] = 6
        self.assertTrue(list(self.validator.iter_errors(bundle)))
        bundle["measurements"] = bundle["measurements"][:-1]
        self.assertTrue(list(self.validator.iter_errors(bundle)))


if __name__ == "__main__":
    unittest.main()
