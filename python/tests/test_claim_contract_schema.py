"""Acceptance tests for the research-claim-contract v1 JSON Schema."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[2]

CLAIM_PATHS = {
    "correction.same_class.a0.v1": ROOT / "registry" / "claims" / "correction.same_class.a0.v1.json",
    "correction.b0.v1": ROOT / "registry" / "claims" / "correction.b0.v1.json",
    "fcc.b0.anticorrelation.v1": ROOT / "registry" / "claims" / "fcc.b0.anticorrelation.v1.json",
}

EVIDENCE_PATHS = tuple(
    sorted((ROOT / "evidence" / "v1" / "examples").glob("*.json"))
)


def load(relative_path: str | Path) -> dict:
    if isinstance(relative_path, str):
        relative_path = ROOT / relative_path
    with relative_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def canonical_content_hash(document: dict, hash_field: str) -> str:
    payload = {key: value for key, value in document.items() if key != hash_field}
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


class ClaimContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.claim_schema = load("schemas/research-claim-contract.v1.schema.json")
        cls.evidence_schema = load("evidence/v1/schema.json")
        Draft202012Validator.check_schema(cls.claim_schema)
        Draft202012Validator.check_schema(cls.evidence_schema)
        cls.claim_validator = Draft202012Validator(cls.claim_schema)
        cls.evidence_validator = Draft202012Validator(cls.evidence_schema)

    def test_a0_same_class_contract_passes(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        self.claim_validator.validate(claim)
        self.assertEqual(
            claim["content_hash"], canonical_content_hash(claim, "content_hash")
        )

    def test_a0_claim_references_round3_evidence_bundle_by_content_address(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        evidence = load("evidence/v1/examples/round3-a0-confirmatory.json")
        self.claim_validator.validate(claim)
        self.evidence_validator.validate(evidence)
        self.assertEqual(
            claim["premises"][0]["bundle_references"],
            [{"bundle_id": evidence["bundle_id"]}],
        )

    def test_backfilled_claim_contracts_validate_and_have_canonical_hashes(self) -> None:
        for claim_id, path in CLAIM_PATHS.items():
            with self.subTest(claim_id=claim_id):
                claim = load(path)
                self.claim_validator.validate(claim)
                self.assertEqual(claim_id, claim["claim_id"])
                self.assertEqual(
                    claim["content_hash"], canonical_content_hash(claim, "content_hash")
                )

    def test_backfilled_claim_contracts_resolve_all_evidence_bundles(self) -> None:
        evidence_by_id = {}
        for path in EVIDENCE_PATHS:
            evidence = load(path)
            self.evidence_validator.validate(evidence)
            evidence_by_id[evidence["bundle_id"]] = evidence

        for claim_id, path in CLAIM_PATHS.items():
            with self.subTest(claim_id=claim_id):
                claim = load(path)
                referenced = {
                    reference["bundle_id"]
                    for premise in claim["premises"]
                    for reference in premise["bundle_references"]
                }
                self.assertTrue(referenced)
                self.assertLessEqual(referenced, evidence_by_id.keys())

    def test_backfilled_claim_statuses_match_round3_dispositions(self) -> None:
        a0 = load(CLAIM_PATHS["correction.same_class.a0.v1"])
        b0 = load(CLAIM_PATHS["correction.b0.v1"])
        fcc_b0 = load(CLAIM_PATHS["fcc.b0.anticorrelation.v1"])

        self.assertEqual(
            a0["classification"],
            {
                "intent": "confirmatory",
                "outcome": "supported",
                "assurance": "active",
                "strength": "predictive",
            },
        )
        self.assertEqual(b0["classification"]["intent"], "descriptive")
        self.assertEqual(b0["classification"]["outcome"], "withdrawn")
        self.assertEqual(b0["classification"]["assurance"], "withdrawn")
        self.assertEqual(fcc_b0["classification"]["outcome"], "contradicted")
        self.assertEqual(fcc_b0["classification"]["assurance"], "withdrawn")

    def test_backfilled_claim_bindings_are_bound_or_explicitly_unsupported(self) -> None:
        for claim_id, path in CLAIM_PATHS.items():
            with self.subTest(claim_id=claim_id):
                bindings = load(path)["bindings"]
                self.assertEqual(bindings["publication"]["status"], "bound")
                for binding in bindings.values():
                    if binding["status"] == "unsupported":
                        self.assertTrue(binding["reason"].strip())

    def test_bundle_reference_rejects_legacy_identifier_and_duplicate_hash(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        reference = claim["premises"][0]["bundle_references"][0]
        reference["bundle_id"] = "round3.a0.same_class.confirmatory.v1"
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

        reference["bundle_id"] = (
            "sha256:40855c6fd1c2eeea9310db45258fc1a08ea850c704cad224bf36b93f1867b36a"
        )
        reference["content_hash"] = reference["bundle_id"]
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

    def test_unsupported_binding_requires_reason_and_forbids_reference(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        claim["bindings"]["runtime_gate"] = {"status": "unsupported"}
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

        claim["bindings"]["runtime_gate"] = {
            "status": "unsupported",
            "reason": "No runtime gate exists for this descriptive claim.",
            "gate_id": "stale.gate",
        }
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

    def test_supported_premise_requires_evidence_bundle(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        claim["premises"][0]["bundle_references"] = []
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

    def test_unsupported_premise_and_bindings_are_explicit(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        claim["premises"][0]["support_policy"] = {"mode": "unsupported"}
        claim["premises"][0]["bundle_references"] = []
        claim["bindings"] = {
            "lean_theorem": {
                "status": "unsupported",
                "reason": "No theorem has been formalized.",
            },
            "runtime_gate": {
                "status": "unsupported",
                "reason": "No runtime gate exists.",
            },
            "publication": {
                "status": "unsupported",
                "reason": "The claim has not been published.",
            },
        }
        self.claim_validator.validate(claim)

    def test_at_least_policy_requires_minimum(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        claim["premises"][0]["support_policy"] = {"mode": "at_least"}
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)

    def test_hashes_are_sha256_content_addresses(self) -> None:
        claim = load("examples/claim-contract.a0-same-class.v1.json")
        claim["content_hash"] = "not-a-hash"
        with self.assertRaises(ValidationError):
            self.claim_validator.validate(claim)


if __name__ == "__main__":
    unittest.main()
