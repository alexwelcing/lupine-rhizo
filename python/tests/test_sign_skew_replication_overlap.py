from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/check_sign_skew_replication_overlap.py"
SPEC = importlib.util.spec_from_file_location("sign_skew_overlap", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def structure() -> dict:
    return {
        "symbols": ["Li"],
        "positions_angstrom": [[0, 0, 0]],
        "cell_angstrom": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        "pbc": [True, True, True],
    }


def paths(prefix: str, count: int, barrier_start: float) -> list[dict]:
    return [
        {
            "path_id": f"{prefix}-path-{index}",
            "material_id": f"{prefix}-material-{index}",
            "chemical_system": f"{prefix}-system-{index}",
            "split": "test",
            "reference_barrier_ev": barrier_start + index / 1000,
            "input_images": [structure(), structure()],
            "reference": {
                "image_count": 2,
                "saddle_image_index": 1,
                "energies_ev": [0.0, barrier_start + index / 1000],
                "endpoint_initial": structure(),
                "saddle": structure(),
                "endpoint_final": structure(),
            },
        }
        for index in range(count)
    ]


def fixture() -> tuple[dict, str, dict, dict, list[dict], dict, dict, str, dict]:
    candidate_paths = paths("replication", 30, 10.0)
    candidate = {
        "schema": MODULE.EXPECTED_PANEL_SCHEMA,
        "panel_id": MODULE.EXPECTED_PANEL_ID,
        "holdout": {
            "unit": "chemical_system",
            "source_split": "test",
            "selection_rule": MODULE.EXPECTED_SELECTION_RULE,
            "selected_chemical_systems": sorted(
                path["chemical_system"] for path in candidate_paths
            ),
        },
        "reference_provenance": dict(MODULE.EXPECTED_REFERENCE_PROVENANCE),
        "execution_protocol": {
            "failure_policy": "record failure without imputation",
            "barrier_definition": "max(image_energy_ev) - min(image_energy_ev)",
        },
        "paths": candidate_paths,
    }
    candidate_bytes = (json.dumps(candidate, sort_keys=True) + "\n").encode()
    candidate_hash = "sha256:" + hashlib.sha256(candidate_bytes).hexdigest()
    baseline_panel = {"paths": paths("baseline", 30, 1.0)}
    baseline_campaign = {"per_path": deepcopy(baseline_panel["paths"][:23])}
    source_rows = deepcopy(candidate_paths)
    input_document_hash = "sha256:" + "a" * 64
    manifest = {
        "campaign_id": MODULE.EXPECTED_CAMPAIGN_ID,
        "version": 1,
        "preregistration_id": MODULE.EXPECTED_PREREGISTRATION_ID,
        "available_models": [dict(model) for model in MODULE.CANONICAL_MODELS],
        "acceptance_test": dict(MODULE.EXPECTED_ACCEPTANCE_TEST),
        "demotion_conditions": [dict(item) for item in MODULE.EXPECTED_DEMOTIONS],
        "evidence_requirements": [
            dict(item) for item in MODULE.EXPECTED_EVIDENCE_REQUIREMENTS
        ],
        "exclusions": [],
        "execution": {
            "candidate_panel": {
                "path": MODULE.EXPECTED_PANEL_PATH,
                "sha256": candidate_hash,
            },
            "lane": "literature.protocol-offset-sign-skew.replication",
            "model_selection": "available_models",
            "excluded_models_block_execution": False,
        },
        "frozen_hypotheses": [dict(item) for item in MODULE.EXPECTED_HYPOTHESES],
        "kill_conditions": [dict(item) for item in MODULE.EXPECTED_KILL_CONDITIONS],
        "preregistration": {
            "registered_at": "2026-08-04T00:00:00Z",
            "source": "https://doi.org/10.1038/s41524-025-01571-z",
            "source_as_of": MODULE.EXPECTED_SOURCE_AS_OF,
            "frozen_before_execution": True,
            "input_document": {
                "path": MODULE.EXPECTED_INPUT_DOCUMENT_PATH,
                "sha256": input_document_hash,
            },
            "recorded_inputs": [
                {
                    "path": MODULE.EXPECTED_PANEL_PATH,
                    "sha256": candidate_hash,
                }
            ]
        },
        "target_premises": [dict(item) for item in MODULE.EXPECTED_TARGET_PREMISES],
    }
    manifest["content_hash"] = MODULE.manifest_content_hash(manifest)
    manifest_schema = json.loads(
        (ROOT / "schemas/campaign-manifest.v1.schema.json").read_text(encoding="utf-8")
    )
    registry = {"campaigns": [deepcopy(manifest)]}
    return (
        candidate,
        candidate_hash,
        baseline_panel,
        baseline_campaign,
        source_rows,
        manifest,
        manifest_schema,
        input_document_hash,
        registry,
    )


def validate(
    values: tuple[dict, str, dict, dict, list[dict], dict, dict, str, dict]
) -> list[str]:
    (
        candidate,
        candidate_hash,
        baseline_panel,
        baseline_campaign,
        source_rows,
        manifest,
        manifest_schema,
        input_document_hash,
        registry,
    ) = values
    return MODULE.validate_replication(
        candidate_panel=candidate,
        candidate_panel_hash=candidate_hash,
        baseline_panel=baseline_panel,
        baseline_campaign=baseline_campaign,
        source_rows=source_rows,
        manifest=manifest,
        manifest_schema=manifest_schema,
        input_document_hash=input_document_hash,
        registry=registry,
    )


def test_fully_disjoint_registered_replication_passes() -> None:
    assert validate(fixture()) == []


def test_registered_manifest_preserves_source_freshness_date() -> None:
    values = fixture()

    assert values[5]["preregistration"]["source_as_of"] == "2026-08-03"
    assert validate(values) == []


@pytest.mark.parametrize("field", ["path_id", "chemical_system", "reference_barrier_ev"])
def test_overlap_with_frozen_panel_refuses(field: str) -> None:
    values = fixture()
    values[0]["paths"][0][field] = values[2]["paths"][0][field]
    assert any("shared" in error or "overlap" in error for error in validate(values))


@pytest.mark.parametrize("count", [21, 22, 29, 31])
def test_panel_not_exactly_30_refuses(count: int) -> None:
    values = fixture()
    if count <= 30:
        values[0]["paths"] = values[0]["paths"][:count]
    else:
        values[0]["paths"].extend(paths("extra", count - 30, 20.0))
    assert any("need exactly 30" in error for error in validate(values))


def test_noncanonical_model_identity_refuses() -> None:
    values = fixture()
    values[5]["available_models"][0]["version"] = "changed"
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("four canonical models" in error for error in validate(values))


def test_missing_recorded_input_lock_refuses() -> None:
    values = fixture()
    values[5]["preregistration"]["recorded_inputs"] = []
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("recorded_inputs" in error for error in validate(values))


def test_unregistered_manifest_refuses() -> None:
    values = fixture()
    values[8]["campaigns"] = []
    assert any("not registered byte-for-byte" in error for error in validate(values))


def test_stale_manifest_hash_refuses() -> None:
    values = fixture()
    values[5]["campaign_id"] = "literature.protocol-offset-sign-skew.replication.changed"
    assert any("content_hash is stale" in error for error in validate(values))


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("reference_provenance", "source_revision", "wrong", "source provenance"),
        ("holdout", "source_split", "train", "official test split"),
        ("holdout", "selection_rule", "arbitrary selection", "selection rule"),
        ("execution_protocol", "failure_policy", "impute failures", "forbid imputation"),
    ],
)
def test_candidate_provenance_contract_refuses(
    section: str, field: str, value: str, message: str
) -> None:
    values = fixture()
    values[0][section][field] = value
    assert any(message in error for error in validate(values))


def test_candidate_without_executable_images_refuses() -> None:
    values = fixture()
    values[0]["paths"][0]["input_images"] = []
    assert any("executable input_images" in error for error in validate(values))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda panel: panel.update(unreviewed_field=True),
        lambda panel: panel["reference_provenance"].update(
            contradictory_source="unreviewed"
        ),
    ],
)
def test_candidate_panel_rejects_unknown_fields(mutate) -> None:
    values = fixture()
    mutate(values[0])
    assert any("candidate panel fails schema" in error for error in validate(values))


def test_periodic_input_cell_must_be_nonsingular() -> None:
    values = fixture()
    singular = [[1, 0, 0], [2, 0, 0], [0, 0, 1]]
    values[0]["paths"][0]["input_images"][0]["cell_angstrom"] = singular
    values[4][0]["input_images"][0]["cell_angstrom"] = deepcopy(singular)
    assert any("malformed input image" in error for error in validate(values))


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("symbols", ["Na"]),
        ("pbc", [True, False, True]),
        ("cell_angstrom", [[2, 0, 0], [0, 1, 0], [0, 0, 1]]),
    ],
)
def test_path_topology_and_periodicity_must_be_constant(
    field: str, replacement: list
) -> None:
    values = fixture()
    values[0]["paths"][0]["input_images"][1][field] = deepcopy(replacement)
    values[4][0]["input_images"][1][field] = deepcopy(replacement)
    assert any("atom identity/order, PBC, or cell" in error for error in validate(values))


def test_candidate_with_malformed_image_refuses() -> None:
    values = fixture()
    values[0]["paths"][0]["input_images"] = [{}]
    assert any("malformed input image" in error for error in validate(values))


def test_candidate_barrier_must_match_reference_profile() -> None:
    values = fixture()
    values[0]["paths"][0]["reference_barrier_ev"] += 1.0
    values[4][0]["reference_barrier_ev"] += 1.0
    assert any("disagrees with its energy profile" in error for error in validate(values))


def test_candidate_must_match_pinned_source_selection() -> None:
    values = fixture()
    values[0]["paths"][0]["path_id"] = "fabricated-path"
    assert any("pinned deterministic source selection" in error for error in validate(values))


def test_source_archive_drives_deterministic_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive_path = tmp_path / "nebDFT2k.zip"
    rows = ["_split,chemsys,material_id,edge_id,em_dft"]
    for index in range(31):
        rows.append(f"test,Chem-{index:02d},mat-{index:02d},edge-{index:02d},{index + 1}.0")
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("nebDFT2k_index.csv", "\n".join(rows) + "\n")
    monkeypatch.setitem(
        MODULE.EXPECTED_REFERENCE_PROVENANCE,
        "source_archive_sha256",
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        MODULE,
        "_source_path_record",
        lambda _archive, row: {
            "path_id": row["edge_id"],
            "material_id": row["material_id"],
            "chemical_system": row["chemsys"],
            "reference_barrier_ev": float(row["em_dft"]),
        },
    )

    selected = MODULE.expected_replication_rows(archive_path, {"paths": []})
    assert len(selected) == 30
    assert selected[0] == {
        "path_id": "edge-00",
        "material_id": "mat-00",
        "chemical_system": "Chem-00",
        "reference_barrier_ev": 1.0,
    }
    assert selected[-1]["path_id"] == "edge-29"


def test_candidate_sidecar_is_mandatory_and_content_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    panel = tmp_path / "panel.json"
    panel.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sidecar is missing"):
        MODULE.validate_sha256_sidecar(panel)

    digest = hashlib.sha256(panel.read_bytes()).hexdigest()
    sidecar = panel.with_suffix(".json.sha256")
    sidecar.write_text(f"{digest}  {panel.name}\n", encoding="utf-8")
    MODULE.validate_sha256_sidecar(panel)
    sidecar.write_text(f"{'0' * 64}  {panel.name}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale or malformed"):
        MODULE.validate_sha256_sidecar(panel)


def test_cli_refuses_substituted_evidence_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    arbitrary = tmp_path / "arbitrary.json"
    arbitrary.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_sign_skew_replication_overlap.py",
            "--candidate-panel",
            str(arbitrary),
            "--source-archive",
            str(arbitrary),
            "--manifest",
            str(arbitrary),
        ],
    )
    assert MODULE.main() == 2
    assert "candidate panel must be repository path" in capsys.readouterr().out


def test_cli_independently_refuses_substituted_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    arbitrary = tmp_path / "arbitrary.json"
    arbitrary.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_sign_skew_replication_overlap.py",
            "--candidate-panel",
            str(MODULE.ROOT / MODULE.EXPECTED_PANEL_PATH),
            "--source-archive",
            str(arbitrary),
            "--manifest",
            str(arbitrary),
        ],
    )
    assert MODULE.main() == 2
    assert "manifest must be repository path" in capsys.readouterr().out


def test_cli_refuses_substituted_source_archive_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    arbitrary = tmp_path / "source.zip"
    arbitrary.write_bytes(b"not the reviewed archive")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_sign_skew_replication_overlap.py",
            "--candidate-panel",
            str(MODULE.ROOT / MODULE.EXPECTED_PANEL_PATH),
            "--source-archive",
            str(arbitrary),
            "--manifest",
            str(MODULE.ROOT / MODULE.EXPECTED_MANIFEST_PATH),
        ],
    )
    assert MODULE.main() == 2
    assert "source archive must be repository path" in capsys.readouterr().out


def test_canonical_evidence_path_must_not_be_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    expected = tmp_path / MODULE.EXPECTED_PANEL_PATH
    expected.parent.mkdir(parents=True)
    target = tmp_path / "outside.json"
    target.write_text("{}\n", encoding="utf-8")
    expected.symlink_to(target)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        MODULE.require_canonical_repo_argument(
            expected, MODULE.EXPECTED_PANEL_PATH, "candidate panel"
        )
    source_archive = tmp_path / MODULE.SOURCE_ARCHIVE_PATH
    source_archive.parent.mkdir(parents=True)
    source_archive.symlink_to(target)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        MODULE.require_canonical_repo_argument(
            source_archive, MODULE.SOURCE_ARCHIVE_PATH, "source archive"
        )


def test_json_artifacts_and_sidecars_must_not_be_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    linked_json = tmp_path / "linked.json"
    linked_json.symlink_to(target)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        MODULE.load_object(linked_json)

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    real_sidecar = tmp_path / "real.sha256"
    real_sidecar.write_text(f"{digest}  {target.name}\n", encoding="utf-8")
    target.with_suffix(".json.sha256").symlink_to(real_sidecar)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        MODULE.validate_sha256_sidecar(target)


def test_input_document_must_not_be_a_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    target = tmp_path / "reviewed.md"
    target.write_text(MODULE.EXPECTED_INPUT_STATUS + "\n", encoding="utf-8")
    document = tmp_path / MODULE.EXPECTED_INPUT_DOCUMENT_PATH
    document.parent.mkdir(parents=True)
    document.symlink_to(target)
    lock = {"path": MODULE.EXPECTED_INPUT_DOCUMENT_PATH, "sha256": MODULE.sha256_lock(target)}
    with pytest.raises(ValueError, match="must not contain symlinks"):
        MODULE.locked_repo_file_hash(lock)


def test_input_document_must_be_non_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    document = tmp_path / MODULE.EXPECTED_INPUT_DOCUMENT_PATH
    document.parent.mkdir(parents=True)
    document.write_text("**Status:** draft\n", encoding="utf-8")
    lock = {
        "path": MODULE.EXPECTED_INPUT_DOCUMENT_PATH,
        "sha256": MODULE.sha256_lock(document),
    }
    with pytest.raises(ValueError, match="must declare"):
        MODULE.locked_repo_file_hash(lock)

    for contradictory_status in (
        "  **Status:** DRAFT",
        "Status: DRAFT",
        "WORK IN PROGRESS",
        "**Registration status:** NOT REGISTERED",
        "Registration Status - NOT REGISTERED",
        "WIP",
        "NOT-REGISTERED",
        "WORK-IN-PROGRESS",
        "not_registered",
        "NOT **REGISTERED**",
        "D**RAFT**",
        "W.I.P.",
        "W**I**P",
        "W-I-P",
        "W_I_P",
        "W / I / P",
        "> **Status:** REJECTED",
        "> **Status:** REVIEWED / READY TO REGISTER",
        ">> **Status:** DRAFT",
        "## Draft preregistration",
        "This document is a draft.",
    ):
        document.write_text(
            MODULE.EXPECTED_INPUT_STATUS + f"\n{contradictory_status}\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="preregistration.input_document"):
            MODULE.locked_repo_file_hash(lock)

    document.write_text(
        MODULE.EXPECTED_INPUT_STATUS + "\nThe operator may swipe through evidence.\n",
        encoding="utf-8",
    )
    assert MODULE.locked_repo_file_hash(lock) == MODULE.sha256_lock(document)


def test_manifest_schema_violation_refuses() -> None:
    values = fixture()
    del values[5]["kill_conditions"]
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("fails campaign-manifest" in error for error in validate(values))


def test_registration_timestamp_must_be_utc() -> None:
    values = fixture()
    values[5]["preregistration"]["registered_at"] = "2026-08-04T01:00:00+01:00"
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("zero UTC offset" in error for error in validate(values))


def test_input_document_digest_mismatch_refuses() -> None:
    values = fixture()
    values[5]["preregistration"]["input_document"]["sha256"] = "sha256:" + "b" * 64
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("locked reviewed source" in error for error in validate(values))


def test_input_document_path_mismatch_refuses() -> None:
    values = fixture()
    values[5]["preregistration"]["input_document"]["path"] = "README.md"
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("locked reviewed source" in error for error in validate(values))


def test_extra_contradictory_demotion_refuses() -> None:
    values = fixture()
    values[5]["demotion_conditions"].append(
        {
            "condition_id": "demote.replication.contradictory",
            "metric": "median_signed_error_mev",
            "operator": "gt",
            "threshold": 500,
            "unit": "meV",
            "action": "demote",
        }
    )
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any("H1/H2 demotion bounds" in error for error in validate(values))


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda manifest: manifest["execution"].update(lane="changed.lane"), "execution block"),
        (
            lambda manifest: manifest["exclusions"].append(
                {
                    "subject": "mace-mp-small",
                    "disposition": "excluded",
                    "rationale": "post-hoc exclusion",
                }
            ),
            "exclusions must remain exactly empty",
        ),
        (
            lambda manifest: manifest["kill_conditions"][0].update(threshold=1),
            "integrity stop condition",
        ),
        (
            lambda manifest: manifest["frozen_hypotheses"][0].update(
                statement="Changed reduction"
            ),
            "path-median hypotheses",
        ),
        (
            lambda manifest: manifest["evidence_requirements"].pop(),
            "median/no-imputation requirement",
        ),
        (
            lambda manifest: manifest["preregistration"]["recorded_inputs"].append(
                {"path": "data/extra.json", "sha256": "sha256:" + "c" * 64}
            ),
            "exact frozen registration",
        ),
        (
            lambda manifest: manifest.update(preregistration_id="prereg.unrelated.v1"),
            "preregistration_id must be",
        ),
        (
            lambda manifest: manifest.update(
                target_premises=[{"claim_id": "unrelated", "premise_id": "unrelated"}]
            ),
            "target premises",
        ),
    ],
)
def test_manifest_frozen_sections_refuse_schema_valid_mutations(
    mutate, message: str
) -> None:
    values = fixture()
    mutate(values[5])
    values[5]["content_hash"] = MODULE.manifest_content_hash(values[5])
    values[8]["campaigns"][0] = deepcopy(values[5])
    assert any(message in error for error in validate(values))


def test_registry_requires_complete_manifest_entry() -> None:
    values = fixture()
    values[8]["campaigns"][0] = {
        "campaign_id": values[5]["campaign_id"],
        "content_hash": values[5]["content_hash"],
    }
    assert any("not registered byte-for-byte" in error for error in validate(values))


def test_manifest_hash_uses_rfc8785_number_encoding() -> None:
    manifest = {"campaign_id": "test", "threshold": 0.0000001}
    assert MODULE.manifest_content_hash(manifest) == (
        "sha256:"
        + hashlib.sha256(b'{"campaign_id":"test","threshold":1e-7}').hexdigest()
    )
