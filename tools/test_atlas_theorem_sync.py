from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

import atlas_theorem_sync as sync
import pytest


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _selection(
    name: str = "Example.Core.safe",
    *,
    facet: str = "theorist",
    module: str = "Example.Core",
    status: str = "verified",
) -> dict[str, object]:
    return {
        "facet": facet,
        "theorem_name": name,
        "module": module,
        "status": status,
        "used_in_hypotheses": 1,
    }


def _evidence(
    selections: list[dict[str, object]],
    *,
    passed: bool = True,
    proof_revision: str | None = sync.FORMAL_PROOF_REVISION,
) -> dict[str, object]:
    modules: dict[str, dict[str, object]] = {}
    for selection in selections:
        module = str(selection["module"])
        theorem_name = str(selection["theorem_name"])
        source = modules.setdefault(
            module,
            {
                "module": module,
                "source_path": module.replace(".", "/") + ".lean",
                "source_hash": _hash(module),
                "built": passed,
                "theorems": [],
            },
        )
        source["theorems"].append(
            {
                "name": theorem_name,
                "namespace": theorem_name.rsplit(".", 1)[0],
                "statement_hash": _hash(theorem_name),
            }
        )

    evidence: dict[str, object] = {
        "schema": sync.BUILD_EVIDENCE_SCHEMA,
        "schema_version": 1,
        "proof_repository": sync.PROOF_REPOSITORY,
        "proof_revision": proof_revision,
        "lean_version": sync.LEAN_VERSION,
        "mathlib_revision": sync.MATHLIB_REVISION,
        "atlas_revision": sync.ATLAS_REVISION,
        "gates": {
            "lake_build": {
                "passed": passed,
                "command": "lake build",
                "exit_code": 0 if passed else 1,
            },
            "zero_sorry": {"passed": passed, "sorry_count": 0 if passed else 1},
            "vision": {
                "passed": passed,
                "legacy_theorems": 284,
                "universal_correction_theorems": 164,
                "epistemic_gaps": 5,
            },
        },
        "modules": list(modules.values()),
    }
    evidence["manifest_hash"] = sync.canonical_manifest_hash(evidence)
    return evidence


@pytest.fixture()
def connection() -> sqlite3.Connection:
    repo = Path(__file__).resolve().parents[1]
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript((repo / "glim-think" / "schema.sql").read_text(encoding="utf-8"))
    return db


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("facet", "Experiment", "invalid facet"),
        ("facet", "unknown", "invalid facet"),
        ("status", "pending", "invalid status"),
    ],
)
def test_invalid_facet_or_status_is_rejected(field: str, value: str, message: str) -> None:
    selection = _selection()
    selection[field] = value

    with pytest.raises(sync.ManifestError, match=message):
        sync.build_sync_manifest(_evidence([selection]), [selection])


@pytest.mark.unit
@pytest.mark.parametrize("failure", ["commit", "build"])
def test_verified_output_requires_immutable_commit_and_passing_build(failure: str) -> None:
    selection = _selection()
    evidence = _evidence(
        [selection],
        passed=failure != "build",
        proof_revision=None if failure == "commit" else sync.FORMAL_PROOF_REVISION,
    )

    with pytest.raises(sync.ManifestError, match="verified output requires"):
        sync.build_sync_manifest(evidence, [selection])


@pytest.mark.unit
def test_verified_output_rejects_missing_build_gate() -> None:
    selection = _selection()
    evidence = _evidence([selection])
    del evidence["gates"]["lake_build"]
    evidence["manifest_hash"] = sync.canonical_manifest_hash(evidence)

    with pytest.raises(sync.ManifestError, match="gates.lake_build"):
        sync.build_sync_manifest(evidence, [selection])


@pytest.mark.unit
def test_namespace_and_module_mismatches_are_rejected() -> None:
    selection = _selection()
    evidence = _evidence([selection])
    wrong_module = [{**selection, "module": "Example.Other"}]

    with pytest.raises(sync.ManifestError, match="source/build inventory"):
        sync.build_sync_manifest(evidence, wrong_module)

    bad_namespace = copy.deepcopy(evidence)
    bad_namespace["modules"][0]["theorems"][0]["namespace"] = "Other.Namespace"
    bad_namespace["manifest_hash"] = sync.canonical_manifest_hash(bad_namespace)
    with pytest.raises(sync.ManifestError, match="namespace mismatch"):
        sync.build_sync_manifest(bad_namespace, [selection])


@pytest.mark.unit
def test_sql_renderer_escapes_quotes_and_executes(connection: sqlite3.Connection) -> None:
    selection = _selection(name="Example.O'Hara.safe")
    manifest = sync.build_sync_manifest(_evidence([selection]), [selection])

    sql = sync.render_sync_sql(manifest)

    assert "O''Hara" in sql
    assert "ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE" in sql
    connection.executescript(sql)
    row = connection.execute("SELECT theorem_name, status FROM atlas_theorems").fetchone()
    assert dict(row) == {"theorem_name": "Example.O'Hara.safe", "status": "verified"}


@pytest.mark.unit
def test_parameterized_sync_is_idempotent_and_updates_facet_metadata(
    connection: sqlite3.Connection,
) -> None:
    selection = _selection()
    manifest = sync.build_sync_manifest(_evidence([selection]), [selection])

    sync.synchronize_connection(connection, manifest)
    sync.synchronize_connection(connection, manifest)

    assert connection.execute("SELECT COUNT(*) FROM atlas_theorems").fetchone()[0] == 1
    state = connection.execute(
        "SELECT proof_revision, build_manifest_hash, state_schema_version, "
        "inventory_schema_version, theorem_inventory FROM atlas_facet_state "
        "WHERE facet = 'theorist'"
    ).fetchone()
    assert state["proof_revision"] == sync.FORMAL_PROOF_REVISION
    assert state["build_manifest_hash"] == manifest["build_manifest_hash"]
    assert state["state_schema_version"] == sync.STATE_SCHEMA_VERSION
    assert state["inventory_schema_version"] == sync.INVENTORY_SCHEMA_VERSION
    assert json.loads(state["theorem_inventory"])["producer"] == sync.SYNC_SCHEMA


@pytest.mark.unit
def test_failed_row_transitions_to_verified(connection: sqlite3.Connection) -> None:
    failed = _selection(status="failed")
    verified = _selection(status="verified")

    sync.synchronize_connection(
        connection,
        sync.build_sync_manifest(_evidence([failed], passed=False), [failed]),
    )
    sync.synchronize_connection(
        connection,
        sync.build_sync_manifest(_evidence([verified]), [verified]),
    )

    rows = connection.execute("SELECT status FROM atlas_theorems").fetchall()
    assert [row["status"] for row in rows] == ["verified"]


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["parameterized", "rendered-sql"])
def test_removed_shared_entry_is_retired_not_deleted(
    connection: sqlite3.Connection, mode: str
) -> None:
    retained = _selection(name="Example.Core.retained")
    removed = _selection(name="Example.Core.removed")
    first = sync.build_sync_manifest(_evidence([retained, removed]), [retained, removed])
    second = sync.build_sync_manifest(_evidence([retained]), [retained])

    if mode == "parameterized":
        sync.synchronize_connection(connection, first)
        sync.synchronize_connection(connection, second)
    else:
        connection.executescript(sync.render_sync_sql(first))
        connection.executescript(sync.render_sync_sql(second))

    rows = connection.execute(
        "SELECT theorem_name, lifecycle_status FROM atlas_theorems ORDER BY theorem_name"
    ).fetchall()
    assert [dict(row) for row in rows] == [
        {"theorem_name": "Example.Core.removed", "lifecycle_status": "retired"},
        {"theorem_name": "Example.Core.retained", "lifecycle_status": "active"},
    ]


@pytest.mark.unit
def test_default_registry_covers_required_groups_and_distill_extension() -> None:
    registry = sync.load_registry(sync.DEFAULT_REGISTRY_PATH)
    names = {entry["theorem_name"] for entry in registry["theorems"]}

    assert set(registry["managed_facets"]) == sync.FACETS
    assert any("Analysis.Causal.simpsonsDetectedEmpirical" in name for name in names)
    assert any("Analysis.Manifold.fccEamPRBounded" in name for name in names)
    assert any("parameter_bound_of_linearized_certificate" in name for name in names)
    assert any("AffineFamily.residual_difference_in_direction" in name for name in names)
    assert any(
        "ExactTubularUniversality.exact_tubular_universality_of_A0ToA5" in name for name in names
    )
    assert any("certified_order_iff_endpoint_margins_fcc" in name for name in names)
    assert any("checkRuntimeContract_admit_iff" in name for name in names)
    assert any("runtime_contract_is_fail_closed" in name for name in names)

    extension = _selection(
        name="Lupine.DistillAtlas.Ni_EAM.distill_improves_energy",
        facet="experiment",
        module="OpenDistillationFactory.Materials.DistillAtlas.Ni_EAM",
    )
    evidence = _evidence([extension])
    manifest = sync.build_sync_manifest(
        evidence,
        [],
        extensions=[extension],
        extension_policy=registry["extension_policy"],
        managed_facets=["experiment"],
    )
    assert manifest["theorems"][0]["theorem_name"] == extension["theorem_name"]


@pytest.mark.unit
def test_ad_hoc_generator_rows_never_claim_verified(tmp_path: Path) -> None:
    theorem = {
        **_selection(name="Lupine.DistillAtlas.Ni.o'hara"),
        "statement": "theorem o'hara : 1 = 1 := rfl\n",
    }
    rows = sync.build_ad_hoc_rows(
        [theorem],
        module_sources={"Example.Core": "namespace Lupine\n"},
        module_results={"Example.Core": True},
    )

    assert rows[0]["status"] == "imported"
    assert rows[0]["proof_revision"] is None
    assert rows[0]["build_manifest_hash"] is None
    sql = sync.render_ad_hoc_sql(rows)
    assert "'imported'" in sql
    assert "'verified'" not in sql
    assert "o''hara" in sql
    extension_path = tmp_path / "extension.json"
    sync.write_extension_manifest(extension_path, rows)
    extension = json.loads(extension_path.read_text(encoding="utf-8"))
    assert "status" not in extension["theorems"][0]


@pytest.mark.unit
def test_proof_revision_resolution_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    other = "b" * 40
    registry_pin = "c" * 40
    monkeypatch.delenv("ATLAS_PROOF_REVISION", raising=False)

    assert sync.resolve_proof_revision() == sync.FORMAL_PROOF_REVISION
    assert sync.resolve_proof_revision(registry_pin=registry_pin) == registry_pin
    assert sync.resolve_proof_revision(other) == other

    monkeypatch.setenv("ATLAS_PROOF_REVISION", other)
    assert sync.resolve_proof_revision() == other
    assert sync.resolve_proof_revision(registry_pin=registry_pin) == other
    assert sync.resolve_proof_revision(registry_pin) == registry_pin

    with pytest.raises(sync.ManifestError):
        sync.resolve_proof_revision("not-a-commit")
    with pytest.raises(sync.ManifestError):
        monkeypatch.setenv("ATLAS_PROOF_REVISION", "also-not-a-commit")
        sync.resolve_proof_revision()


@pytest.mark.unit
def test_registry_pin_is_authoritative_and_override_must_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATLAS_PROOF_REVISION", raising=False)
    payload = json.loads(sync.DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))
    new_pin = "d" * 40
    payload["authority"]["proof_revision"] = new_pin
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    registry = sync.load_registry(registry_path)
    assert registry["authority"]["proof_revision"] == new_pin

    with pytest.raises(sync.ManifestError, match="re-pin"):
        sync.load_registry(registry_path, expected_proof_revision=sync.FORMAL_PROOF_REVISION)

    selection = _selection()
    evidence = _evidence([selection], proof_revision=new_pin)
    manifest = sync.build_sync_manifest(evidence, [selection], expected_proof_revision=new_pin)
    assert manifest["proof_revision"] == new_pin

    with pytest.raises(sync.ManifestError, match="immutable formal commit"):
        sync.build_sync_manifest(evidence, [selection])
