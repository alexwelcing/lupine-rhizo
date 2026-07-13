"""Unit tests for lupine_distill.statics.gates (reference-free discovery gates).

Born stability is exact physics; concordance thresholds are data-derived
(percentiles of a measured cross-model dispersion distribution, never
invented); dynamic-return is a documented basin-return proxy. All gates
return frozen, JSON-serializable verdicts.
"""

from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    ConcordanceThresholds,
    GateVerdict,
    InputValidationError,
    born_stability_cubic,
    build_structure,
    compute_lattice,
    concordance,
    derive_concordance_thresholds,
    dispersions_by_material,
    dynamic_return,
    facet_ordering,
    load_property_by_material,
    relative_dispersion,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# Born stability (exact physics: Born & Huang 1954; Mouhat & Coudert 2014)
# --------------------------------------------------------------------------


class TestBornStabilityCubic:
    def test_stable_constants_pass(self) -> None:
        verdict = born_stability_cubic(200.0, 100.0, 50.0)
        assert verdict.passed is True
        assert verdict.values["c11_minus_c12_gpa"] == pytest.approx(100.0)
        assert verdict.values["c11_plus_2c12_gpa"] == pytest.approx(400.0)
        assert verdict.values["c44_gpa"] == pytest.approx(50.0)

    def test_shear_instability_fails(self) -> None:
        # C' = (C11 - C12)/2 < 0: tetragonal shear instability.
        verdict = born_stability_cubic(100.0, 150.0, 50.0)
        assert verdict.passed is False
        assert "C11 - C12" in verdict.detail

    def test_negative_c44_fails(self) -> None:
        verdict = born_stability_cubic(200.0, 100.0, -5.0)
        assert verdict.passed is False
        assert "C44" in verdict.detail

    def test_spinodal_instability_fails(self) -> None:
        # C11 + 2*C12 < 0 with C11 - C12 > 0.
        verdict = born_stability_cubic(10.0, -20.0, 5.0)
        assert verdict.passed is False
        assert "C11 + 2*C12" in verdict.detail

    def test_nonfinite_input_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            born_stability_cubic(math.nan, 100.0, 50.0)
        with pytest.raises(InputValidationError):
            born_stability_cubic(200.0, math.inf, 50.0)

    def test_verdict_is_frozen_and_serializable(self) -> None:
        verdict = born_stability_cubic(200.0, 100.0, 50.0)
        assert isinstance(verdict, GateVerdict)
        with pytest.raises(dataclasses.FrozenInstanceError):
            verdict.passed = False  # type: ignore[misc]
        block = verdict.to_dict()
        assert block["gate"] == "born_stability_cubic"
        json.dumps(block)


# --------------------------------------------------------------------------
# Facet ordering / surface-energy positivity (optional gate)
# --------------------------------------------------------------------------


class TestFacetOrdering:
    def test_positive_gammas_pass(self) -> None:
        verdict = facet_ordering({"111": 0.8, "100": 1.0, "110": 1.1})
        assert verdict.passed is True
        assert "111" in verdict.detail  # ordering reported descriptively

    def test_negative_gamma_fails(self) -> None:
        verdict = facet_ordering({"111": -0.2, "100": 1.0})
        assert verdict.passed is False
        assert "111" in verdict.detail

    def test_empty_mapping_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            facet_ordering({})

    def test_nonfinite_gamma_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            facet_ordering({"100": math.nan})


# --------------------------------------------------------------------------
# Cross-model concordance (thresholds derived from measured dispersions)
# --------------------------------------------------------------------------


class TestRelativeDispersion:
    def test_known_value(self) -> None:
        assert relative_dispersion([90.0, 100.0, 110.0]) == pytest.approx(0.2)

    def test_two_values(self) -> None:
        assert relative_dispersion([1.0, 1.1]) == pytest.approx(0.1 / 1.05)

    def test_sign_insensitive_median(self) -> None:
        assert relative_dispersion([-110.0, -100.0, -90.0]) == pytest.approx(0.2)

    def test_single_value_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            relative_dispersion([42.0])

    def test_zero_median_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            relative_dispersion([-1.0, 0.0, 1.0])

    def test_nonfinite_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            relative_dispersion([1.0, math.nan])


class TestDeriveConcordanceThresholds:
    def test_percentiles_match_numpy(self) -> None:
        dispersions = {f"M{i}": float(i) / 100.0 for i in range(1, 22)}  # 21 samples
        thresholds = derive_concordance_thresholds(dispersions, source="unit-test")
        values = np.array(sorted(dispersions.values()))
        assert thresholds.flag == pytest.approx(float(np.percentile(values, 75.0)))
        assert thresholds.refuse == pytest.approx(float(np.percentile(values, 95.0)))
        assert thresholds.n_samples == 21
        assert thresholds.source == "unit-test"
        assert thresholds.flag < thresholds.refuse

    def test_too_few_samples_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            derive_concordance_thresholds({"A": 0.1, "B": 0.2}, source="unit-test")

    def test_disordered_percentiles_rejected(self) -> None:
        dispersions = {f"M{i}": float(i) for i in range(10)}
        with pytest.raises(InputValidationError):
            derive_concordance_thresholds(
                dispersions, flag_percentile=95.0, refuse_percentile=75.0,
                source="unit-test",
            )

    def test_thresholds_frozen(self) -> None:
        dispersions = {f"M{i}": float(i) / 10.0 for i in range(1, 9)}
        thresholds = derive_concordance_thresholds(dispersions, source="unit-test")
        assert isinstance(thresholds, ConcordanceThresholds)
        with pytest.raises(dataclasses.FrozenInstanceError):
            thresholds.flag = 0.0  # type: ignore[misc]


class TestConcordance:
    def _thresholds(self) -> ConcordanceThresholds:
        dispersions = {f"M{i}": 0.05 * i for i in range(1, 9)}  # 0.05 .. 0.40
        return derive_concordance_thresholds(dispersions, source="unit-test")

    def test_tight_agreement_passes(self) -> None:
        thresholds = self._thresholds()
        verdict = concordance("b0", {"m1": 100.0, "m2": 101.0, "m3": 99.0}, thresholds)
        assert verdict.passed is True
        assert verdict.values["level"] == "pass"
        assert verdict.values["dispersion"] == pytest.approx(0.02)

    def test_moderate_disagreement_flags_but_passes(self) -> None:
        thresholds = self._thresholds()
        # dispersion 40/120 = 0.333: >= flag (p75 = 0.3125 of the synthetic
        # set) but < refuse (p95 = 0.3825).
        verdict = concordance("b0", {"m1": 100.0, "m2": 140.0}, thresholds)
        assert verdict.values["level"] == "flag"
        assert verdict.passed is True  # flag warns; only refuse stops

    def test_gross_disagreement_refuses(self) -> None:
        thresholds = self._thresholds()
        verdict = concordance("c44", {"m1": 100.0, "m2": 160.0}, thresholds)
        assert verdict.values["level"] == "refuse"
        assert verdict.passed is False

    def test_needs_at_least_two_models(self) -> None:
        with pytest.raises(InputValidationError):
            concordance("b0", {"m1": 100.0}, self._thresholds())

    def test_criteria_carry_provenance(self) -> None:
        verdict = concordance("b0", {"m1": 100.0, "m2": 101.0}, self._thresholds())
        assert verdict.criteria["thresholds_source"] == "unit-test"
        json.dumps(verdict.to_dict())


# --------------------------------------------------------------------------
# Evidence-directory loading (baseline for threshold derivation)
# --------------------------------------------------------------------------


def _write_evidence(
    directory: Path, material: str, model: str, b0: float | None
) -> None:
    properties = []
    if b0 is not None:
        properties.append({"name": "B0", "value": b0, "unit": "GPa"})
    payload = {
        "schema": "lupine.mlip.calc_evidence.v1",
        "material": material,
        "source": {"model_id": model, "backend": "ase", "device": "cpu"},
        "properties": properties,
    }
    path = directory / f"{material}_{model}.evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestLoadPropertyByMaterial:
    def test_loads_nested_mapping(self, tmp_path: Path) -> None:
        _write_evidence(tmp_path, "Cu", "m1", 150.0)
        _write_evidence(tmp_path, "Cu", "m2", 160.0)
        _write_evidence(tmp_path, "Al", "m1", 70.0)
        _write_evidence(tmp_path, "Al", "m2", 80.0)
        values = load_property_by_material(tmp_path, property_name="B0")
        assert values == {
            "Cu": {"m1": 150.0, "m2": 160.0},
            "Al": {"m1": 70.0, "m2": 80.0},
        }

    def test_other_schemas_skipped(self, tmp_path: Path) -> None:
        _write_evidence(tmp_path, "Cu", "m1", 150.0)
        _write_evidence(tmp_path, "Cu", "m2", 160.0)
        (tmp_path / "binding_report.json").write_text(
            json.dumps({"schema": "lupine.other.v1"}), encoding="utf-8"
        )
        values = load_property_by_material(tmp_path, property_name="B0")
        assert set(values) == {"Cu"}

    def test_file_without_property_skipped(self, tmp_path: Path) -> None:
        _write_evidence(tmp_path, "Cu", "m1", 150.0)
        _write_evidence(tmp_path, "Cu", "m2", 160.0)
        _write_evidence(tmp_path, "Zr", "m1", None)
        values = load_property_by_material(tmp_path, property_name="B0")
        assert set(values) == {"Cu"}

    def test_duplicate_cell_rejected(self, tmp_path: Path) -> None:
        _write_evidence(tmp_path, "Cu", "m1", 150.0)
        duplicate = {
            "schema": "lupine.mlip.calc_evidence.v1",
            "material": "Cu",
            "source": {"model_id": "m1"},
            "properties": [{"name": "B0", "value": 155.0, "unit": "GPa"}],
        }
        (tmp_path / "dup.json").write_text(json.dumps(duplicate), encoding="utf-8")
        with pytest.raises(InputValidationError):
            load_property_by_material(tmp_path, property_name="B0")

    def test_missing_directory_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError):
            load_property_by_material(tmp_path / "nope", property_name="B0")

    def test_dispersions_require_two_models(self) -> None:
        with pytest.raises(InputValidationError):
            dispersions_by_material({"Cu": {"m1": 150.0}})

    def test_dispersions_computed(self) -> None:
        dispersions = dispersions_by_material(
            {"Cu": {"m1": 90.0, "m2": 100.0, "m3": 110.0}}
        )
        assert dispersions == {"Cu": pytest.approx(0.2)}


# --------------------------------------------------------------------------
# Dynamic return (finite-rattle basin-return proxy; NOT phonons)
# --------------------------------------------------------------------------


class TestDynamicReturn:
    @pytest.fixture(scope="class")
    def cu_supercell(self):
        lattice = compute_lattice(EMT(), "Cu", "fcc")
        return build_structure("Cu", "fcc", lattice.a0_angstrom).repeat((2, 2, 2))

    def test_stable_crystal_returns(self, cu_supercell) -> None:
        verdict = dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.05, seed=42)
        assert verdict.passed is True
        assert verdict.values["max_displacement_a"] < 0.25
        assert abs(verdict.values["energy_delta_ev_per_atom"]) < 2e-3
        assert verdict.values["seed"] == 42
        json.dumps(verdict.to_dict())

    def test_deterministic_for_fixed_seed(self, cu_supercell) -> None:
        v1 = dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.05, seed=7)
        v2 = dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.05, seed=7)
        assert v1.values["max_displacement_a"] == pytest.approx(
            v2.values["max_displacement_a"]
        )
        assert v1.passed == v2.passed

    def test_impossible_displacement_tolerance_fails(self, cu_supercell) -> None:
        verdict = dynamic_return(
            EMT(), cu_supercell, rattle_amplitude=0.05, seed=42,
            displacement_tol_a=1e-12,
        )
        assert verdict.passed is False

    def test_relaxation_budget_exhaustion_is_a_failed_verdict(
        self, cu_supercell
    ) -> None:
        verdict = dynamic_return(
            EMT(), cu_supercell, rattle_amplitude=0.05, seed=42, max_steps=1
        )
        assert verdict.passed is False
        assert "converge" in verdict.detail.lower()

    def test_detail_documents_limits(self, cu_supercell) -> None:
        verdict = dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.05, seed=42)
        assert "phonon" in verdict.detail.lower()

    def test_input_validation(self, cu_supercell) -> None:
        with pytest.raises(InputValidationError):
            dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.0, seed=42)
        with pytest.raises(InputValidationError):
            dynamic_return(EMT(), cu_supercell, rattle_amplitude=-0.1, seed=42)
        with pytest.raises(InputValidationError):
            dynamic_return(EMT(), cu_supercell, rattle_amplitude=0.05, seed=-1)
        with pytest.raises(InputValidationError):
            dynamic_return(
                EMT(), cu_supercell, rattle_amplitude=0.05, seed=42,
                energy_tol_ev_per_atom=0.0,
            )
