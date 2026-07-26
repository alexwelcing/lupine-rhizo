from __future__ import annotations

import hashlib
import json
from pathlib import Path

import rfc8785
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CLAIM = ROOT / "registry" / "claims" / "discovery.z2.magnetic-anisotropy.v1.json"
MANIFEST = ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"


def content_hash(document: dict) -> str:
    payload = {key: value for key, value in document.items() if key != "content_hash"}
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def test_z2_claim_contract_is_pending_and_targets_measurement_premise() -> None:
    claim = json.loads(CLAIM.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas" / "research-claim-contract.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(claim)
    assert claim["claim_id"] == "discovery.z2.magnetic-anisotropy.v1"
    assert claim["classification"] == {
        "intent": "confirmatory",
        "outcome": "pending",
        "assurance": "unsupported",
        "strength": "predictive",
    }
    assert [premise["premise_id"] for premise in claim["premises"]] == [
        "spin-orbit-resolved-held-out-ranking"
    ]
    assert claim["premises"][0]["support_policy"] == {"mode": "unsupported"}
    assert claim["premises"][0]["bundle_references"] == []
    assert claim["content_hash"] == content_hash(claim)


def test_z2_manifest_is_schema_valid_hash_locked_and_includes_tc_scope() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas" / "campaign-manifest.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(manifest)
    assert manifest["content_hash"] == content_hash(manifest)
    assert "h.z2.tc-prediction" in {
        hypothesis["hypothesis_id"] for hypothesis in manifest["frozen_hypotheses"]
    }
    assert "e.z2.tc-results" in {
        requirement["requirement_id"] for requirement in manifest["evidence_requirements"]
    }
