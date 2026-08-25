"""Adversarial tests for the Round-5 grouping and held-out split contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/round5_grouping.py"
pytestmark = pytest.mark.unit


def load_module():
    assert MODULE_PATH.is_file(), "Round-5 grouping executable is missing"
    spec = importlib.util.spec_from_file_location("round5_grouping", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_groupings_are_order_reduction_and_boundary_stable() -> None:
    module = load_module()
    vocabulary = module.load_vocabulary()
    candidate = {
        "class": "ionics-rocksalt",
        "structure_prototype": "AB_cF8_225_a_b",
        "elemental_composition": {"Cl": 2, "Na": 2},
    }
    reordered = {
        "class": "ionics-rocksalt",
        "structure_prototype": "AB_cF8_225_a_b",
        "elemental_composition": {"Na": 1, "Cl": 1},
    }
    expected = {
        "class": "ionics-rocksalt",
        "chemistry": "Na-Cl",
        "structure_prototype": "AB_cF8_225_a_b",
        "composition_space_neighbourhood": "csn-zband10-v1:Z011-020=1",
    }
    assert module.derive_groupings(candidate, vocabulary) == expected
    assert module.derive_groupings(reordered, vocabulary) == expected

    boundary = module.derive_groupings(
        {
            "class": "ionics-rocksalt",
            "structure_prototype": "AB_cF8_225_a_b",
            "elemental_composition": {"Ne": 1, "Na": 1},
        },
        vocabulary,
    )
    assert boundary["chemistry"] == "Ne-Na"
    assert boundary["composition_space_neighbourhood"] == (
        "csn-zband10-v1:Z001-010=1,Z011-020=1"
    )


def candidate(index: int, material_class: str) -> dict:
    if material_class == "ionics-rocksalt":
        return {
            "source_structure_id": f"mp-rs-{index:03d}",
            "class": material_class,
            "structure_prototype": "AB_cF8_225_a_b",
            "elemental_composition": {"Na": 1, "Cl": 1},
        }
    return {
        "source_structure_id": f"mp-pv-{index:03d}",
        "class": material_class,
        "structure_prototype": "AB3C_cP5_221_a_c_b",
        "elemental_composition": {"Sr": 1, "Ti": 1, "O": 3},
    }


def test_split_is_class_stratified_order_invariant_and_genuinely_held_out() -> None:
    module = load_module()
    candidates = [
        *(candidate(index, "ionics-rocksalt") for index in range(63)),
        *(candidate(index, "perovskites") for index in range(62)),
    ]

    assignments = module.assign_panel_roles(candidates)
    reversed_assignments = module.assign_panel_roles(list(reversed(candidates)))
    roles = {row["source_structure_id"]: row["role"] for row in assignments}
    reversed_roles = {
        row["source_structure_id"]: row["role"] for row in reversed_assignments
    }

    assert roles == reversed_roles
    assert sum(row["role"] == "calibration" for row in assignments) == 83
    assert sum(row["role"] == "held_out_target" for row in assignments) == 42
    assert {
        (row["class_size"], row["class_calibration_count"], row["class_target_count"])
        for row in assignments
    } == {(63, 42, 21), (62, 41, 21)}

    target = next(row for row in assignments if row["role"] == "held_out_target")
    calibration_ids = module.calibration_ids_for_target(
        assignments, target["source_structure_id"], "class"
    )
    assert len(calibration_ids) in {41, 42}
    assert target["source_structure_id"] not in calibration_ids


@pytest.mark.parametrize(
    "field,value",
    [
        ("chemistry", "Na-Cl"),
        ("composition_space_neighbourhood", "csn-zband10-v1:Z011-020=1"),
    ],
)
def test_operator_supplied_derived_labels_refuse(field: str, value: str) -> None:
    module = load_module()
    supplied = candidate(0, "ionics-rocksalt")
    supplied[field] = value

    with pytest.raises(
        module.GroupingRefusalError,
        match="REFUSE_PRECOMPUTED_GROUPING_VALUE",
    ):
        module.derive_groupings(supplied)


def test_nonpositive_minimum_calibration_refuses() -> None:
    module = load_module()
    candidates = [
        *(candidate(index, "ionics-rocksalt") for index in range(6)),
        *(candidate(index, "perovskites") for index in range(6)),
    ]
    assignments = module.assign_panel_roles(candidates)
    target = next(row for row in assignments if row["role"] == "held_out_target")

    with pytest.raises(
        module.GroupingRefusalError,
        match="REFUSE_MINIMUM_CALIBRATION",
    ):
        module.calibration_ids_for_target(
            assignments,
            target["source_structure_id"],
            "class",
            minimum_calibration=0,
        )


def test_cli_emits_canonical_heldout_assignment(tmp_path: Path) -> None:
    candidates = [
        *(candidate(index, "ionics-rocksalt") for index in range(6)),
        *(candidate(index, "perovskites") for index in range(6)),
    ]
    candidate_path = tmp_path / "candidates.json"
    candidate_path.write_text(json.dumps(candidates), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(candidate_path), "--assign-heldout-roles"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == json.dumps(
        json.loads(completed.stdout),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    assert {row["role"] for row in json.loads(completed.stdout)} == {
        "calibration",
        "held_out_target",
    }


def test_cli_refuses_vocabulary_path_substitution(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(
        json.dumps(candidate(0, "ionics-rocksalt")), encoding="utf-8"
    )
    substituted_vocabulary = tmp_path / "vocabulary.json"
    substituted_vocabulary.write_bytes(
        (ROOT / "data/contracts/round5-grouping-vocabulary.v1.json").read_bytes()
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            str(candidate_path),
            "--vocabulary",
            str(substituted_vocabulary),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "REFUSE_VOCABULARY_PATH" in completed.stderr


def test_vocabulary_digest_mismatch_refuses(tmp_path: Path) -> None:
    module = load_module()
    substituted_vocabulary = tmp_path / "round5-grouping-vocabulary.v1.json"
    vocabulary = json.loads(
        (ROOT / "data/contracts/round5-grouping-vocabulary.v1.json").read_text(
            encoding="utf-8"
        )
    )
    vocabulary["class_vocabulary"]["allowed"].append("post-hoc-class")
    substituted_vocabulary.write_text(json.dumps(vocabulary), encoding="utf-8")
    setattr(module, "DEFAULT_VOCABULARY", substituted_vocabulary)

    with pytest.raises(module.GroupingRefusalError, match="REFUSE_VOCABULARY_DIGEST"):
        module.load_vocabulary(substituted_vocabulary)


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda row: row.update(elemental_composition={}), "REFUSE_EMPTY_COMPOSITION"),
        (
            lambda row: row.update(elemental_composition={"Na": True, "Cl": 1}),
            "REFUSE_NON_INTEGER_STOICHIOMETRY",
        ),
        (
            lambda row: row.update(elemental_composition={"Na": 0, "Cl": 1}),
            "REFUSE_NON_POSITIVE_STOICHIOMETRY",
        ),
        (
            lambda row: row.update(elemental_composition={"Na": 1.0, "Cl": 1}),
            "REFUSE_NON_INTEGER_STOICHIOMETRY",
        ),
        (
            lambda row: row.update(elemental_composition={"Xx": 1, "Cl": 1}),
            "REFUSE_UNKNOWN_ELEMENT",
        ),
        (
            lambda row: row.update(elemental_composition={"D": 1, "Cl": 1}),
            "REFUSE_NON_ELEMENTAL_SPECIES",
        ),
        (lambda row: row.update(class_="ignored"), None),
    ],
)
def test_adversarial_compositions_refuse(mutation, code: str | None) -> None:
    module = load_module()
    row = candidate(0, "ionics-rocksalt")
    if code is None:
        row["class"] = "Ionics-Rocksalt"
        code = "REFUSE_CLASS_VOCABULARY"
    else:
        mutation(row)
    with pytest.raises(module.GroupingRefusalError, match=code):
        module.derive_groupings(row)


def test_duplicate_source_identity_and_underoccupied_class_refuse() -> None:
    module = load_module()
    rows = [
        *(candidate(index, "ionics-rocksalt") for index in range(5)),
        *(candidate(index, "perovskites") for index in range(5)),
    ]
    duplicate = [*rows, dict(rows[0])]
    with pytest.raises(
        module.GroupingRefusalError,
        match="REFUSE_DUPLICATE_SOURCE_STRUCTURE_ID",
    ):
        module.assign_panel_roles(duplicate)

    with pytest.raises(
        module.GroupingRefusalError,
        match="REFUSE_CLASS_SPLIT_UNDEROCCUPIED",
    ):
        module.assign_panel_roles(rows[:-1])


def test_secondary_rule_with_too_few_fixed_calibrators_refuses() -> None:
    module = load_module()
    rows = [
        *(candidate(index, "ionics-rocksalt") for index in range(6)),
        *(candidate(index, "perovskites") for index in range(6)),
    ]
    assignments = module.assign_panel_roles(rows)
    target = next(row for row in assignments if row["role"] == "held_out_target")
    target["groupings"]["chemistry"] = "H-He"

    with pytest.raises(
        module.GroupingRefusalError,
        match="INSUFFICIENT_GROUP_CALIBRATION",
    ):
        module.calibration_ids_for_target(
            assignments,
            target["source_structure_id"],
            "chemistry",
        )
