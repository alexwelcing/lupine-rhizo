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
    PROPERTY_EVIDENCE_NAMES,
    ConcordanceThresholds,
    GateVerdict,
    InputValidationError,
    born_stability_cubic,
    build_structure,
    compute_lattice,
    concordance,
    derive_concordance_thresholds,
    derive_per_property_thresholds,
    dispersions_by_material,
    dispersions_by_material_floored,
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
# Floored dispersion metric (Round-3 registered fix 1, metric floored-v1)
# --------------------------------------------------------------------------


class TestDispersionsByMaterialFloored:
    #: Synthetic bcc-C44-like class: three healthy cells plus a V-like
    #: sign-crossing cell whose four models straddle zero (median exactly 0,
    #: the case where (max-min)/|median| is undefined/explosive).
    _CLASS = {
        "W": {"m1": 120.0, "m2": 150.0, "m3": 140.0, "m4": 130.0},
        "Mo": {"m1": 90.0, "m2": 110.0, "m3": 100.0, "m4": 105.0},
        "Cr": {"m1": 40.0, "m2": 90.0, "m3": 60.0, "m4": 70.0},
        "V": {"m1": -20.0, "m2": 30.0, "m3": 5.0, "m4": -5.0},
    }

    def test_v_c44_sign_crossing_is_finite_and_sane(self) -> None:
        # V median = median(-20, -5, 5, 30) = 0 -> unfloored metric undefined.
        with pytest.raises(InputValidationError):
            relative_dispersion(list(self._CLASS["V"].values()))
        dispersions = dispersions_by_material_floored(self._CLASS)
        # class-median |median| = median(135, 102.5, 65, 0) = 83.75; floor 8.375.
        floor = 0.1 * float(np.median([135.0, 102.5, 65.0, 0.0]))
        expected_v = (30.0 - (-20.0)) / floor
        assert dispersions["V"] == pytest.approx(expected_v)
        assert math.isfinite(dispersions["V"])
        # Sane: large (worst in class) but nowhere near the unfloored 237.7-like
        # explosion a near-zero median produces.
        assert dispersions["V"] < 10.0
        assert dispersions["V"] == max(dispersions.values())

    def test_healthy_cells_match_unfloored_metric(self) -> None:
        dispersions = dispersions_by_material_floored(self._CLASS)
        for material in ("W", "Mo", "Cr"):
            unfloored = relative_dispersion(list(self._CLASS[material].values()))
            assert dispersions[material] == pytest.approx(unfloored)

    def test_floor_engages_only_below_fraction_of_class_median(self) -> None:
        values = {
            "A": {"m1": 99.0, "m2": 101.0},
            "B": {"m1": 100.0, "m2": 102.0},
            "C": {"m1": 1.0, "m2": 3.0},  # |median| = 2 < 0.1 * 100
        }
        dispersions = dispersions_by_material_floored(values)
        assert dispersions["A"] == pytest.approx(2.0 / 100.0)
        # C floored: denominator max(2, 0.1 * median(100, 101, 2)) = 10.
        assert dispersions["C"] == pytest.approx(2.0 / 10.0)

    def test_all_sign_crossing_medians_rejected(self) -> None:
        with pytest.raises(InputValidationError, match="class-median"):
            dispersions_by_material_floored(
                {"A": {"m1": -1.0, "m2": 1.0}, "B": {"m1": -2.0, "m2": 2.0}}
            )

    def test_requires_two_models(self) -> None:
        with pytest.raises(InputValidationError):
            dispersions_by_material_floored({"Cu": {"m1": 150.0}})

    def test_bad_floor_fraction_rejected(self) -> None:
        for bad in (0.0, -0.1, math.nan):
            with pytest.raises(InputValidationError):
                dispersions_by_material_floored(
                    {"Cu": {"m1": 90.0, "m2": 110.0}}, floor_fraction=bad
                )

    def test_empty_mapping_rejected(self) -> None:
        with pytest.raises(InputValidationError):
            dispersions_by_material_floored({})


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


# --------------------------------------------------------------------------
# Per-property thresholds (thresholds.v2: no more B0-proxy transfer)
# --------------------------------------------------------------------------


def _write_full_evidence(
    directory: Path, material: str, model: str, values: dict[str, float]
) -> None:
    """Evidence file carrying any subset of the five gate properties."""
    units = {"a0": "Angstrom", "B0": "GPa", "C11": "GPa", "C12": "GPa", "C44": "GPa"}
    payload = {
        "schema": "lupine.mlip.calc_evidence.v1",
        "material": material,
        "source": {"model_id": model, "backend": "ase", "device": "cpu"},
        "properties": [
            {"name": name, "value": value, "unit": units[name]}
            for name, value in values.items()
        ],
    }
    path = directory / f"{material}_{model}.evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


class TestDerivePerPropertyThresholds:
    @staticmethod
    def _populate(directory: Path, n_materials: int = 6) -> dict[str, list[float]]:
        """Two models whose disagreement grows with the property index, so
        each property gets a distinct dispersion distribution."""
        expected: dict[str, list[float]] = {p: [] for p in PROPERTY_EVIDENCE_NAMES}
        for i in range(n_materials):
            material = f"M{i}"
            base = {"a0": 4.0 + i, "B0": 100.0 + i, "C11": 200.0, "C12": 90.0, "C44": 50.0}
            spread = 0.01 * (1 + i)
            m1 = {k: v * (1 - spread * factor) for factor, (k, v) in enumerate(base.items(), start=1)}
            m2 = {k: v * (1 + spread * factor) for factor, (k, v) in enumerate(base.items(), start=1)}
            _write_full_evidence(directory, material, "m1", m1)
            _write_full_evidence(directory, material, "m2", m2)
            for factor, (prop, evidence_name) in enumerate(
                PROPERTY_EVIDENCE_NAMES.items(), start=1
            ):
                lo = m1[evidence_name]
                hi = m2[evidence_name]
                median = float(np.median([lo, hi]))
                expected[prop].append((hi - lo) / abs(median))
        return expected

    def test_each_property_gets_its_own_percentiles(self, tmp_path: Path) -> None:
        expected = self._populate(tmp_path)
        thresholds = derive_per_property_thresholds(tmp_path)
        assert set(thresholds) == set(PROPERTY_EVIDENCE_NAMES)
        for prop, per_material in expected.items():
            t = thresholds[prop]
            assert t.n_samples == len(per_material)
            assert t.flag == pytest.approx(np.percentile(per_material, 75.0))
            assert t.refuse == pytest.approx(np.percentile(per_material, 95.0))
            assert PROPERTY_EVIDENCE_NAMES[prop] in t.source
        # Distinct dispersion distributions -> distinct thresholds.
        refuses = {prop: t.refuse for prop, t in thresholds.items()}
        assert len(set(refuses.values())) == len(refuses)
        # The construction disperses later properties more: c44 > b0 > a0.
        assert refuses["c44"] > refuses["b0"] > refuses["a0"]

    def test_missing_property_is_an_error_not_silence(self, tmp_path: Path) -> None:
        # Baseline carries only a0/B0 (like data/y_matrix_runs/bound today).
        for i in range(6):
            _write_full_evidence(tmp_path, f"M{i}", "m1", {"a0": 4.0, "B0": 100.0})
            _write_full_evidence(tmp_path, f"M{i}", "m2", {"a0": 4.1, "B0": 110.0})
        with pytest.raises(InputValidationError, match="C11"):
            derive_per_property_thresholds(tmp_path)

    def test_unknown_property_rejected(self, tmp_path: Path) -> None:
        self._populate(tmp_path)
        with pytest.raises(InputValidationError, match="unknown concordance property"):
            derive_per_property_thresholds(tmp_path, properties=("a0", "gamma_100"))

    def test_subset_of_properties(self, tmp_path: Path) -> None:
        self._populate(tmp_path)
        thresholds = derive_per_property_thresholds(tmp_path, properties=("b0",))
        assert set(thresholds) == {"b0"}

    def test_floor_fraction_selects_floored_metric(self, tmp_path: Path) -> None:
        """A sign-crossing C44 cell is finite under floored-v1 and the metric
        version is recorded in the threshold source."""
        healthy_c44 = [50.0, 60.0, 45.0, 55.0, 52.0]
        for i, c44 in enumerate(healthy_c44):
            _write_full_evidence(
                tmp_path, f"M{i}", "m1",
                {"a0": 4.0, "B0": 100.0, "C11": 200.0, "C12": 90.0, "C44": c44},
            )
            _write_full_evidence(
                tmp_path, f"M{i}", "m2",
                {"a0": 4.02, "B0": 105.0, "C11": 210.0, "C12": 95.0,
                 "C44": c44 + 10.0},
            )
        # V-like sign-crossing cell: models straddle zero on C44.
        _write_full_evidence(
            tmp_path, "V", "m1",
            {"a0": 3.0, "B0": 150.0, "C11": 250.0, "C12": 120.0, "C44": -20.0},
        )
        _write_full_evidence(
            tmp_path, "V", "m2",
            {"a0": 3.02, "B0": 155.0, "C11": 260.0, "C12": 125.0, "C44": 20.0},
        )
        # Unfloored metric cannot even be computed (median exactly 0).
        with pytest.raises(InputValidationError):
            derive_per_property_thresholds(tmp_path, properties=("c44",))
        thresholds = derive_per_property_thresholds(
            tmp_path, properties=("c44",), floor_fraction=0.1
        )
        t = thresholds["c44"]
        assert math.isfinite(t.refuse)
        assert "floored-v1" in t.source
        dispersions = dict(t.sample_dispersions)
        # V's dispersion = 40 / (0.1 * class-median |median C44|), finite.
        assert math.isfinite(dispersions["V"])
        assert dispersions["V"] == max(dispersions.values())
