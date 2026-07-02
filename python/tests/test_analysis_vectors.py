"""Tests for error-vector assembly (prereg H1 normalization + binding policy).

Covers: signed relative error, the near-zero-reference guard (uncertainty and
epsilon branches), DFT-PBE-else-experiment reference binding, matched-n
exclusion of incomplete materials, caller-supplied material exclusions
(Fe per the deviations log), descriptive (cross-model disagreement) mode,
and loading of real-schema run/target JSON files.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from lupine_distill.analysis.binding import select_references
from lupine_distill.analysis.descriptive import assemble_descriptive_matrices
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.loading import (
    ReferenceEntry,
    RunRecord,
    load_run_directory,
    load_targets_directory,
)
from lupine_distill.analysis.vectors import (
    assemble_error_cells,
    assemble_error_matrix,
    normalized_signed_error,
)

FCC_PROPS = (
    "a0",
    "b0",
    "b0_prime",
    "e_vac",
    "gamma_100",
    "gamma_110",
    "gamma_111",
    "gamma_sfe",
)


def _run(material: str, model: str, preds: dict, structure: str = "fcc") -> RunRecord:
    return RunRecord(
        material=material,
        structure_type=structure,
        model_id=model,
        predictions=preds,
        source_path="<synthetic>",
    )


def _ref(
    material: str,
    prop: str,
    value: float,
    method: str = "DFT-PBE",
    structure: str = "fcc",
    uncertainty: float | None = None,
) -> ReferenceEntry:
    return ReferenceEntry(
        material=material,
        structure=structure,
        property_name=prop,
        value=value,
        unit="arb",
        method=method,
        uncertainty=uncertainty,
        citation="synthetic",
        family_label="synthetic",
    )


# ---------------------------------------------------------------- normalization


def test_signed_relative_error_matches_prereg_definition():
    res = normalized_signed_error(
        2.0, 1.6, uncertainty=None, family_scale=1.0, near_zero_epsilon=1e-9
    )
    assert res.value == pytest.approx(0.25)
    assert res.guard_engaged is False


def test_signed_relative_error_keeps_sign_for_negative_reference():
    res = normalized_signed_error(
        -2.0, -1.6, uncertainty=None, family_scale=1.0, near_zero_epsilon=1e-9
    )
    assert res.value == pytest.approx(-0.25)


def test_guard_engages_when_reference_below_10x_uncertainty():
    # |ref| = 0.05 < 10 * 0.02 -> absolute error scaled by family scale.
    res = normalized_signed_error(
        0.15, 0.05, uncertainty=0.02, family_scale=2.0, near_zero_epsilon=1e-9
    )
    assert res.guard_engaged is True
    assert res.value == pytest.approx((0.15 - 0.05) / 2.0)


def test_guard_uses_epsilon_only_when_uncertainty_absent():
    # Uncertainty present and |ref| >= 10*uncertainty: no guard even with a
    # huge epsilon (the uncertainty rule takes precedence per prereg H1).
    res = normalized_signed_error(
        110.0, 100.0, uncertainty=2.0, family_scale=5.0, near_zero_epsilon=1e6
    )
    assert res.guard_engaged is False
    assert res.value == pytest.approx(0.1)


def test_guard_epsilon_branch_engages_for_near_zero_reference():
    res = normalized_signed_error(
        3.0, 0.5, uncertainty=None, family_scale=125.0, near_zero_epsilon=1.0
    )
    assert res.guard_engaged is True
    assert res.value == pytest.approx(2.5 / 125.0)


def test_normalization_rejects_bad_inputs():
    with pytest.raises(InputValidationError):
        normalized_signed_error(
            1.0, 1.0, uncertainty=None, family_scale=1.0, near_zero_epsilon=0.0
        )
    with pytest.raises(InputValidationError):
        normalized_signed_error(
            float("nan"), 1.0, uncertainty=None, family_scale=1.0, near_zero_epsilon=1e-9
        )
    with pytest.raises(InputValidationError):
        # Guard engaged but no usable family scale.
        normalized_signed_error(
            1.0, 0.0, uncertainty=None, family_scale=0.0, near_zero_epsilon=1.0
        )


# ---------------------------------------------------------------- binding policy


def test_binding_policy_prefers_dft_pbe_then_experiment():
    entries = (
        _ref("Ni", "e_vac", 1.39, method="DFT-PBE"),
        _ref("Ni", "e_vac", 1.79, method="experiment"),
        _ref("Cu", "b0", 137.0, method="experiment"),
    )
    bound = select_references(entries)
    assert bound[("Ni", "fcc", "e_vac")].value == pytest.approx(1.39)
    assert bound[("Ni", "fcc", "e_vac")].method == "DFT-PBE"
    assert bound[("Cu", "fcc", "b0")].method == "experiment"


def test_binding_policy_rejects_ambiguous_duplicates():
    entries = (
        _ref("Ni", "e_vac", 1.39, method="DFT-PBE"),
        _ref("Ni", "e_vac", 1.45, method="DFT-PBE"),
    )
    with pytest.raises(InputValidationError):
        select_references(entries)


# ---------------------------------------------------------------- assembly


def _small_world():
    refs = (
        _ref("M1", "a0", 4.0),
        _ref("M1", "b0", 100.0),
        _ref("M2", "a0", 4.1),
        _ref("M2", "b0", 110.0),
    )
    runs = (
        _run("M1", "modelA", {"a0": 4.2, "b0": 90.0}),
        _run("M2", "modelA", {"a0": 4.1, "b0": 121.0}),
    )
    return runs, refs


def test_error_matrix_values_are_signed_relative_errors():
    runs, refs = _small_world()
    matrix = assemble_error_matrix(
        runs, refs, model_id="modelA", properties=("a0", "b0"), near_zero_epsilon=1e-9
    )
    assert matrix.materials == ("M1", "M2")
    assert matrix.properties == ("a0", "b0")
    expected = np.array([[0.2 / 4.0, -10.0 / 100.0], [0.0, 11.0 / 110.0]])
    np.testing.assert_allclose(matrix.values, expected)
    assert matrix.mode == "confirmatory"
    assert not matrix.values.flags.writeable


def test_matched_n_drops_incomplete_materials_with_reasons():
    refs = (
        _ref("M1", "a0", 4.0),
        _ref("M1", "b0", 100.0),
        _ref("M2", "a0", 4.1),
        _ref("M2", "b0", 110.0),
        _ref("M3", "a0", 4.2),  # M3 has no b0 reference
    )
    runs = (
        _run("M1", "modelA", {"a0": 4.2, "b0": 90.0}),
        _run("M2", "modelA", {"a0": 4.1}),  # M2 missing b0 prediction
        _run("M3", "modelA", {"a0": 4.3, "b0": 130.0}),
    )
    matrix = assemble_error_matrix(
        runs, refs, model_id="modelA", properties=("a0", "b0"), near_zero_epsilon=1e-9
    )
    assert matrix.materials == ("M1",)
    excluded = dict(matrix.excluded_materials)
    assert "b0" in excluded["M2"]  # missing prediction
    assert "b0" in excluded["M3"]  # missing reference


def test_caller_supplied_exclusion_list_is_honored_not_hardcoded():
    runs, refs = _small_world()
    matrix = assemble_error_matrix(
        runs,
        refs,
        model_id="modelA",
        properties=("a0", "b0"),
        excluded_materials=("M2",),
        near_zero_epsilon=1e-9,
    )
    assert matrix.materials == ("M1",)
    excluded = dict(matrix.excluded_materials)
    assert "caller" in excluded["M2"].lower()


def test_assembly_fails_fast_when_no_material_survives():
    runs, refs = _small_world()
    with pytest.raises(InputValidationError):
        assemble_error_matrix(
            runs,
            refs,
            model_id="modelA",
            properties=("a0", "b0"),
            excluded_materials=("M1", "M2"),
            near_zero_epsilon=1e-9,
        )


def test_assembly_rejects_property_not_in_family_map():
    runs, refs = _small_world()
    with pytest.raises(InputValidationError):
        assemble_error_matrix(
            runs,
            refs,
            model_id="modelA",
            properties=("a0", "not_a_property"),
            near_zero_epsilon=1e-9,
        )


def test_sfe_like_near_zero_reference_engages_guard_with_family_median_scale():
    # gamma_sfe references: one near zero, the rest O(100) mJ/m^2.
    sfe_refs = {"M1": 0.5, "M2": 120.0, "M3": 130.0, "M4": 140.0, "M5": 150.0}
    refs = []
    runs = []
    for mat, sfe in sfe_refs.items():
        refs.append(_ref(mat, "a0", 4.0))
        refs.append(_ref(mat, "gamma_sfe", sfe))
        runs.append(_run(mat, "modelA", {"a0": 4.0, "gamma_sfe": sfe + 10.0}))
    cells = assemble_error_cells(
        tuple(runs),
        tuple(refs),
        model_id="modelA",
        properties=("a0", "gamma_sfe"),
        near_zero_epsilon=1.0,
    )
    by_key = {(c.material, c.property_name): c for c in cells}
    guarded = by_key[("M1", "gamma_sfe")]
    assert guarded.guard_engaged is True
    family_median = float(np.median([abs(v) for v in sfe_refs.values()]))
    assert guarded.normalized_error == pytest.approx(10.0 / family_median)
    unguarded = by_key[("M2", "gamma_sfe")]
    assert unguarded.guard_engaged is False
    assert unguarded.normalized_error == pytest.approx(10.0 / 120.0)


# ---------------------------------------------------------------- descriptive mode


def test_descriptive_mode_builds_cross_model_disagreement_vectors():
    runs = (
        _run("M1", "modelA", {"a0": 1.0, "b0": 10.0}),
        _run("M1", "modelB", {"a0": 3.0, "b0": 10.0}),
        _run("M2", "modelA", {"a0": 2.0, "b0": 20.0}),
        _run("M2", "modelB", {"a0": 2.0, "b0": 30.0}),
    )
    matrices = assemble_descriptive_matrices(
        runs,
        model_ids=("modelA", "modelB"),
        properties=("a0", "b0"),
        near_zero_epsilon=1e-9,
    )
    assert tuple(m.model_id for m in matrices) == ("modelA", "modelB")
    mat_a, mat_b = matrices
    assert mat_a.mode == "descriptive"
    assert mat_a.materials == mat_b.materials == ("M1", "M2")
    # M1 a0: mean 2.0 -> A: (1-2)/2 = -0.5, B: +0.5 (antisymmetric).
    a0_col = mat_a.properties.index("a0")
    assert mat_a.values[0, a0_col] == pytest.approx(-0.5)
    assert mat_b.values[0, a0_col] == pytest.approx(0.5)
    assert all(c.reference_method == "cross_model_mean" for c in mat_a.cells)


def test_descriptive_mode_requires_material_complete_across_all_models():
    runs = (
        _run("M1", "modelA", {"a0": 1.0}),
        _run("M1", "modelB", {"a0": 3.0}),
        _run("M2", "modelA", {"a0": 2.0}),  # M2 missing from modelB
    )
    matrices = assemble_descriptive_matrices(
        runs,
        model_ids=("modelA", "modelB"),
        properties=("a0",),
        near_zero_epsilon=1e-9,
    )
    assert matrices[0].materials == ("M1",)
    assert "M2" in dict(matrices[0].excluded_materials)


# ---------------------------------------------------------------- file loading


def _write_run_file(path, material, structure, model_id):
    payload = {
        "schema": "lupine.statics_run.v1",
        "material": material,
        "structure_type": structure,
        "model_id": model_id,
        "results": {
            "lattice": {"values": {"a0_angstrom": 3.51, "b0_gpa": 999.0}},
            "eos": {"values": {"b0_gpa": 186.6, "b0_prime": 4.61}},
            "vacancy": {"values": {"vacancy_formation_ev": 1.02}},
            "surfaces": [
                {"values": {"gamma_j_per_m2": 2.59, "miller": "100"}},
                {"values": {"gamma_j_per_m2": 2.84, "miller": "110"}},
                {"values": {"gamma_j_per_m2": 2.20, "miller": "111"}},
            ],
            "sfe": {"values": {"sfe_mj_per_m2": -7.78}},
            "formation": {"values": {"formation_enthalpy_ev_per_atom": -0.55}},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_run_directory_extracts_canonical_predictions(tmp_path):
    _write_run_file(tmp_path / "Ni_fcc_m.json", "Ni", "fcc", "modelA")
    # Evidence files carry a different schema and must be skipped.
    (tmp_path / "Ni_fcc_m.evidence.json").write_text(
        json.dumps({"schema": "lupine.mlip.calc_evidence.v1"}), encoding="utf-8"
    )
    records = load_run_directory(tmp_path)
    assert len(records) == 1
    rec = records[0]
    assert rec.material == "Ni"
    assert rec.predictions["a0"] == pytest.approx(3.51)
    assert rec.predictions["b0"] == pytest.approx(186.6)  # eos wins over lattice
    assert rec.predictions["b0_prime"] == pytest.approx(4.61)
    assert rec.predictions["e_vac"] == pytest.approx(1.02)
    assert rec.predictions["gamma_100"] == pytest.approx(2.59)
    assert rec.predictions["gamma_111"] == pytest.approx(2.20)
    assert rec.predictions["gamma_sfe"] == pytest.approx(-7.78)
    assert rec.predictions["dh_f"] == pytest.approx(-0.55)


def test_load_run_directory_rejects_duplicate_cells(tmp_path):
    _write_run_file(tmp_path / "one.json", "Ni", "fcc", "modelA")
    _write_run_file(tmp_path / "two.json", "Ni", "fcc", "modelA")
    with pytest.raises(InputValidationError):
        load_run_directory(tmp_path)


def test_load_targets_directory_maps_names_and_records_unmapped(tmp_path):
    payload = {
        "schema": "lupine.y_matrix_targets.v1",
        "family": "vacancy_formation",
        "entries": [
            {
                "material": "Ni",
                "structure": "fcc",
                "property": "vacancy_formation_energy",
                "value": 1.39,
                "unit": "eV",
                "method": "DFT-PBE",
                "source": {"citation": "Angsten 2014"},
            },
            {
                "material": "Ni",
                "structure": "fcc",
                "property": "surface_energy",  # orientation-averaged: unmapped
                "value": 2.38,
                "unit": "J/m^2",
                "method": "experiment",
                "source": {"citation": "someone"},
            },
        ],
    }
    (tmp_path / "vacancy_formation.json").write_text(json.dumps(payload), encoding="utf-8")
    result = load_targets_directory(tmp_path)
    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.property_name == "e_vac"
    assert entry.value == pytest.approx(1.39)
    assert entry.citation == "Angsten 2014"
    assert "surface_energy" in result.unmapped_properties
