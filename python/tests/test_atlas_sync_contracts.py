from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_TOOLS = _REPO / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import atlas_theorem_sync as sync  # noqa: E402
import generate_assumptions  # noqa: E402


def _copy_contract_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    assumptions_path = tmp_path / "registry" / "assumptions.v1.json"
    lock_path = tmp_path / "registry" / "snapshots" / "current.lock.json"
    claims_path = tmp_path / "registry" / "claims"
    evidence_path = tmp_path / "evidence" / "v1" / "examples"
    assumptions_path.parent.mkdir(parents=True)
    lock_path.parent.mkdir(parents=True)
    shutil.copy2(_REPO / "registry" / "assumptions.v1.json", assumptions_path)
    shutil.copy2(_REPO / "registry" / "snapshots" / "current.lock.json", lock_path)
    shutil.copytree(_REPO / "registry" / "claims", claims_path)
    shutil.copytree(_REPO / "evidence" / "v1" / "examples", evidence_path)
    return assumptions_path, lock_path, claims_path, evidence_path


def _write_content_addressed(path: Path, document: dict, field: str) -> str:
    document[field] = sync._content_hash(  # noqa: SLF001
        {key: value for key, value in document.items() if key != field}
    )
    path.write_text(json.dumps(document), encoding="utf-8")
    return document[field]


def _refresh_registry(tmp_path: Path) -> None:
    registry, lock = generate_assumptions.build_documents(tmp_path)
    (tmp_path / "registry" / "assumptions.v1.json").write_text(
        json.dumps(registry), encoding="utf-8"
    )
    (tmp_path / "registry" / "snapshots" / "current.lock.json").write_text(
        json.dumps(lock), encoding="utf-8"
    )


def _add_a0_evidence(
    tmp_path: Path, *, epistemic_status: str, condition_updates: dict | None = None
) -> str:
    source = _REPO / "evidence" / "v1" / "examples" / "round3-a0-confirmatory.json"
    bundle = json.loads(source.read_text(encoding="utf-8"))
    bundle["epistemic_status"] = epistemic_status
    bundle["claim_predicate"] += f"_{epistemic_status}_fixture"
    bundle["scope"]["conditions"].update(condition_updates or {})
    target = tmp_path / "evidence" / "v1" / "examples" / f"extra-{epistemic_status}.json"
    return _write_content_addressed(target, bundle, "bundle_id")


def _add_a0_premise_reference(
    tmp_path: Path, bundle_id: str, support_policy: dict
) -> None:
    claim_path = tmp_path / "registry" / "claims" / "correction.same_class.a0.v1.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["premises"][0]["bundle_references"].append({"bundle_id": bundle_id})
    claim["premises"][0]["support_policy"] = support_policy
    _write_content_addressed(claim_path, claim, "content_hash")
    _refresh_registry(tmp_path)
    registry = json.loads(
        (tmp_path / "registry" / "assumptions.v1.json").read_text(encoding="utf-8")
    )
    assumption = next(
        row for row in registry["assumptions"] if row["claim_id"] == claim["claim_id"]
    )
    claim["classification"]["assurance"] = assumption["status"]
    _write_content_addressed(claim_path, claim, "content_hash")
    _refresh_registry(tmp_path)


@pytest.mark.unit
def test_round3_contracts_compile_to_fail_closed_gate_manifest() -> None:
    manifest = sync.compile_gate_manifest(
        _REPO / "registry" / "assumptions.v1.json",
        _REPO / "registry" / "snapshots" / "current.lock.json",
        _REPO / "registry" / "claims",
    )

    gates = {gate["claim_contract"]["claim_id"]: gate for gate in manifest["gates"]}
    b0 = gates["correction.b0.v1"]
    a0 = gates["correction.same_class.a0.v1"]

    assert manifest["provenance"]["assumptions"] == "registry/assumptions.v1.json"
    assert manifest["provenance"]["snapshot_lock"] == "registry/snapshots/current.lock.json"
    assert b0["decision"] == "deny"
    assert b0["reason"] == "contradicting_evidence"
    assert a0["decision"] == "allow"
    assert a0["reason"] == "scope_matched_same_class_a0"
    for gate in (b0, a0):
        assert gate["claim_contract"]["content_hash"].startswith("sha256:")
        assert gate["evidence"]
        assert gate["scope"]
        assert gate["premises"]
        assert gate["theorem"]["status"] == "unsupported"


@pytest.mark.unit
def test_contract_compiler_rejects_registry_hash_mismatch(tmp_path: Path) -> None:
    lock = json.loads(
        (_REPO / "registry" / "snapshots" / "current.lock.json").read_text(
            encoding="utf-8"
        )
    )
    lock["artifacts"]["registry/assumptions.v1.json"]["content_hash"] = "sha256:" + "0" * 64
    lock_path = tmp_path / "current.lock.json"
    lock_path.write_text(json.dumps(lock), encoding="utf-8")

    with pytest.raises(sync.ManifestError, match="assumption registry content hash mismatch"):
        sync.compile_gate_manifest(
            _REPO / "registry" / "assumptions.v1.json",
            lock_path,
            _REPO / "registry" / "claims",
        )


@pytest.mark.unit
def test_contract_compiler_rejects_missing_locked_evidence(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    next(evidence.glob("*.json")).unlink()

    with pytest.raises(sync.ManifestError, match="missing locked EvidenceBundle"):
        sync.compile_gate_manifest(assumptions, lock, claims, evidence)


@pytest.mark.unit
def test_contract_compiler_rejects_evidence_content_hash_mismatch(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    evidence_file = next(evidence.glob("*.json"))
    bundle = json.loads(evidence_file.read_text(encoding="utf-8"))
    bundle["claim_predicate"] += "_tampered"
    evidence_file.write_text(json.dumps(bundle), encoding="utf-8")

    with pytest.raises(sync.ManifestError, match="EvidenceBundle content hash mismatch"):
        sync.compile_gate_manifest(assumptions, lock, claims, evidence)


@pytest.mark.unit
def test_bound_theorem_must_resolve_in_authoritative_registry(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    claim_path = claims / "correction.same_class.a0.v1.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["bindings"]["lean_theorem"] = {
        "status": "bound",
        "module": "OpenDistillationFactory.Materials.Fictional",
        "theorem": "nonexistent",
    }
    _write_content_addressed(claim_path, claim, "content_hash")
    _refresh_registry(tmp_path)

    with pytest.raises(sync.ManifestError, match="unresolved bound theorem"):
        sync.compile_gate_manifest(assumptions, lock, claims, evidence)


@pytest.mark.unit
def test_bound_theorem_requires_verified_build_evidence(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    theorem_registry_path = _REPO / "config" / "atlas_theorem_registry.v1.json"
    theorem_registry = json.loads(theorem_registry_path.read_text(encoding="utf-8"))
    theorem = theorem_registry["theorems"][0]
    claim_path = claims / "correction.same_class.a0.v1.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["bindings"]["lean_theorem"] = {
        "status": "bound",
        "module": theorem["module"],
        "theorem": theorem["theorem_name"],
    }
    _write_content_addressed(claim_path, claim, "content_hash")
    _refresh_registry(tmp_path)
    build_evidence = json.loads(
        (_REPO / "config" / "atlas_theorem_sync.bf697f0.json").read_text(encoding="utf-8")
    )
    evidence_row = next(
        row for row in build_evidence["theorems"] if row["theorem_name"] == theorem["theorem_name"]
    )
    evidence_row["status"] = "rejected"
    build_evidence_path = tmp_path / "atlas-theorem-sync.json"
    build_evidence_path.write_text(json.dumps(build_evidence), encoding="utf-8")

    with pytest.raises(sync.ManifestError, match="not active verified build evidence"):
        sync.compile_gate_manifest(
            assumptions,
            lock,
            claims,
            evidence,
            theorem_registry_path,
            build_evidence_path,
        )


@pytest.mark.unit
def test_at_least_policy_reports_insufficient_support_level(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    bundle_id = _add_a0_evidence(tmp_path, epistemic_status="descriptive")
    _add_a0_premise_reference(tmp_path, bundle_id, {"mode": "at_least", "minimum": 2})

    manifest = sync.compile_gate_manifest(assumptions, lock, claims, evidence)
    gate = next(
        row
        for row in manifest["gates"]
        if row["claim_contract"]["claim_id"] == "correction.same_class.a0.v1"
    )
    assert gate["decision"] == "deny"
    assert gate["premises"][0]["status"] == "eligible"


@pytest.mark.unit
def test_contract_compiler_rejects_incompatible_scope_conditions(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    bundle_id = _add_a0_evidence(
        tmp_path,
        epistemic_status="confirmatory",
        condition_updates={"calibration": "cross-class calibration"},
    )
    _add_a0_premise_reference(tmp_path, bundle_id, {"mode": "all"})

    with pytest.raises(sync.ManifestError, match="scope-incompatible.*conditions"):
        sync.compile_gate_manifest(assumptions, lock, claims, evidence)


@pytest.mark.unit
def test_shared_runtime_gate_has_unique_scope_key() -> None:
    manifest = sync.compile_gate_manifest()
    shared = [
        gate
        for gate in manifest["gates"]
        if gate["gate_id"] == "python.scripts.run_round3_analysis.correction_gate"
    ]

    assert len(shared) == 2
    assert len({gate["gate_key"] for gate in shared}) == 2


@pytest.mark.unit
def test_at_least_rejects_duplicate_premise_references(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    bundle_id = _add_a0_evidence(tmp_path, epistemic_status="confirmatory")
    claim_path = tmp_path / "registry" / "claims" / "correction.same_class.a0.v1.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    claim["premises"][0]["bundle_references"] = [
        {"bundle_id": bundle_id},
        {"bundle_id": bundle_id},
    ]
    claim["premises"][0]["support_policy"] = {"mode": "at_least", "minimum": 2}
    _write_content_addressed(claim_path, claim, "content_hash")
    _refresh_registry(tmp_path)

    with pytest.raises(sync.ManifestError, match="duplicates evidence"):
        sync.compile_gate_manifest(assumptions, lock, claims, evidence)


@pytest.mark.unit
def test_theorem_build_evidence_rejects_duplicate_verified_rows(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    build_evidence = json.loads(
        (_REPO / "config" / "atlas_theorem_sync.bf697f0.json").read_text(encoding="utf-8")
    )
    row = next(
        row for row in build_evidence["theorems"] if row["status"] == "verified"
    )
    build_evidence["theorems"].append(dict(row))
    build_evidence_path = tmp_path / "atlas-theorem-sync.json"
    build_evidence_path.write_text(json.dumps(build_evidence), encoding="utf-8")

    with pytest.raises(sync.ManifestError, match="duplicate verified theorem row"):
        sync.compile_gate_manifest(
            assumptions,
            lock,
            claims,
            evidence,
            _REPO / "config" / "atlas_theorem_registry.v1.json",
            build_evidence_path,
        )


@pytest.mark.unit
def test_theorem_build_evidence_rejects_invalid_statement_hash(tmp_path: Path) -> None:
    assumptions, lock, claims, evidence = _copy_contract_inputs(tmp_path)
    build_evidence = json.loads(
        (_REPO / "config" / "atlas_theorem_sync.bf697f0.json").read_text(encoding="utf-8")
    )
    row = next(
        row for row in build_evidence["theorems"] if row["status"] == "verified"
    )
    row["statement_hash"] = "not-a-hash"
    build_evidence_path = tmp_path / "atlas-theorem-sync.json"
    build_evidence_path.write_text(json.dumps(build_evidence), encoding="utf-8")

    with pytest.raises(sync.ManifestError, match="invalid statement_hash"):
        sync.compile_gate_manifest(
            assumptions,
            lock,
            claims,
            evidence,
            _REPO / "config" / "atlas_theorem_registry.v1.json",
            build_evidence_path,
        )


@pytest.mark.unit
def test_compile_gates_cli_emits_runtime_manifest(tmp_path: Path) -> None:
    output = tmp_path / "runtime-gates.json"

    assert sync.main(
        [
            "--compile-gates",
            "--assumptions",
            str(_REPO / "registry" / "assumptions.v1.json"),
            "--snapshot-lock",
            str(_REPO / "registry" / "snapshots" / "current.lock.json"),
            "--claims-dir",
            str(_REPO / "registry" / "claims"),
            "--out-gates",
            str(output),
        ]
    ) == 0

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema"] == sync.GATE_MANIFEST_SCHEMA
    assert len(manifest["gates"]) == 3
