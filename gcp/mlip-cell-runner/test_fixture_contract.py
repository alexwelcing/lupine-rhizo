from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from lupine_distill.fixture_contract import evaluate_row, run_row, validate_manifest


class CountingEnergyCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def __init__(self, energy: float):
        super().__init__()
        self.energy = energy
        self.calls = 0

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.calls += 1
        n = len(atoms)
        self.results = {
            "energy": self.energy * n,
            "forces": np.zeros((n, 3)),
            "stress": np.zeros(6),
        }


class SystemEnergyCalculator(Calculator):
    implemented_properties = ["energy"]

    def __init__(self, energies: dict[tuple[str, ...], float], fail_symbols: tuple[str, ...] | None = None):
        super().__init__()
        self.energies = energies
        self.fail_symbols = fail_symbols

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        symbols = tuple(atoms.get_chemical_symbols())
        if symbols == self.fail_symbols:
            raise RuntimeError("intentional system failure")
        self.results = {"energy": self.energies[symbols]}


def adsorption_manifest() -> dict:
    cell = [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 12.0]]
    return {
        "schema": "lupine.mlip.fixture_manifest.v2",
        "fixture_id": "z3-single-candidate-test",
        "manifest_hash": "sha256:test-fixture",
        "reference_provenance": {"source": "unit-test"},
        "row_specs": {
            "adsorption_energy": {
                "min_cases": 1,
                "max_cases": 1,
                "error_tolerance": 0.1,
                "error_unit": "eV",
            }
        },
        "row_fixtures": {
            "adsorption_energy": {
                "structures": [
                    {
                        "candidate_id": "CO-Pt111",
                        "structure_id": "CO-Pt111",
                        "reference": {"adsorption_energy_ev": -1.2},
                        "systems": [
                            {
                                "system_id": "adsorbate-slab",
                                "role": "adsorbate_slab",
                                "stoichiometric_coefficient": 1.0,
                                "symbols": ["Pt", "Pt", "C", "O"],
                                "positions": [[0, 0, 0], [2, 2, 0], [1, 1, 2], [1, 1, 3]],
                                "cell": cell,
                                "pbc": [True, True, False],
                            },
                            {
                                "system_id": "clean-slab",
                                "role": "clean_slab",
                                "stoichiometric_coefficient": -1.0,
                                "symbols": ["Pt", "Pt"],
                                "positions": [[0, 0, 0], [2, 2, 0]],
                                "cell": cell,
                                "pbc": [True, True, False],
                            },
                            {
                                "system_id": "CO-gas",
                                "role": "reference",
                                "stoichiometric_coefficient": -1.0,
                                "symbols": ["C", "O"],
                                "positions": [[0, 0, 0], [0, 0, 1.15]],
                                "cell": [[12, 0, 0], [0, 12, 0], [0, 0, 12]],
                                "pbc": False,
                            },
                        ],
                    }
                ]
            }
        },
    }


class MemoryCheckpoint:
    def __init__(self):
        self.predictions = {}
        self.loaded = 0
        self.written = 0

    def key(self, row_id, case_index, case):
        return (row_id, case_index, case["structure_id"])

    def get_prediction(self, row_id, case_index, case):
        prediction = self.predictions.get(self.key(row_id, case_index, case))
        if prediction is not None:
            self.loaded += 1
        return prediction

    def record_prediction(self, row_id, case_index, case, prediction):
        self.predictions[self.key(row_id, case_index, case)] = prediction
        self.written += 1


def test_validate_manifest_rejects_legacy_smoke_fixture() -> None:
    manifest = {
        "schema": "lupine.mlip.fixture_manifest.v1",
        "fixture_id": "tiny-local-smoke",
        "structures": [
            {
                "structure_id": "Al-fcc-primitive",
                "symbols": ["Al"],
                "positions": [[0.0, 0.0, 0.0]],
                "reference": {"forces": [[0.0, 0.0, 0.0]]},
            }
        ],
    }

    validation = validate_manifest(manifest)

    assert validation["release_ready"] is False
    assert any("fixture_manifest.v2" in blocker for blocker in validation["blockers"])
    assert any("nonzero reference forces" in blocker for blocker in validation["blockers"])


def test_validate_adsorption_fixture_requires_balanced_single_candidate_systems() -> None:
    manifest = adsorption_manifest()

    validation = validate_manifest(manifest)

    assert validation["row_blockers"]["adsorption_energy"] == []
    assert validation["release_ready"] is True
    unbalanced = adsorption_manifest()
    unbalanced["row_fixtures"]["adsorption_energy"]["structures"][0]["systems"][2][
        "stoichiometric_coefficient"
    ] = -0.5
    blockers = validate_manifest(unbalanced)["row_blockers"]["adsorption_energy"]
    assert any("stoichiometry is not element-balanced" in blocker for blocker in blockers)


def test_validate_adsorption_fixture_cannot_override_single_candidate_contract() -> None:
    manifest = adsorption_manifest()
    manifest["row_specs"]["adsorption_energy"]["max_cases"] = 2
    duplicate = json.loads(
        json.dumps(manifest["row_fixtures"]["adsorption_energy"]["structures"][0])
    )
    duplicate["candidate_id"] = "CO-Pt111-duplicate"
    duplicate["structure_id"] = "CO-Pt111-duplicate"
    manifest["row_fixtures"]["adsorption_energy"]["structures"].append(duplicate)

    blockers = validate_manifest(manifest)["row_blockers"]["adsorption_energy"]

    assert any("exactly one candidate" in blocker for blocker in blockers)


def test_adsorption_row_retains_raw_system_energies_and_aggregate_mae() -> None:
    calculator = SystemEnergyCalculator(
        {
            ("Pt", "Pt", "C", "O"): -20.0,
            ("Pt", "Pt"): -15.0,
            ("C", "O"): -4.0,
        }
    )

    result = run_row("adsorption_energy", adsorption_manifest(), calculator)

    prediction = result["predictions"][0]
    assert prediction["status"] == "completed"
    assert prediction["adsorption_energy_ev"] == pytest.approx(-1.0)
    assert prediction["signed_error_ev"] == pytest.approx(0.2)
    assert [system["energy_ev"] for system in prediction["systems"]] == [-20.0, -15.0, -4.0]
    assert [system["reaction_contribution_ev"] for system in prediction["systems"]] == [-20.0, 15.0, 4.0]
    assert result["metrics"]["primary_metric"] == "adsorption_energy_mae"
    assert result["metrics"]["adsorption_energy_mae"] == pytest.approx(0.2)
    assert result["metrics"]["successful_candidates"] == 1
    assert result["metrics"]["failed_candidates"] == 0


@pytest.mark.parametrize("failure_mode", ["nonfinite", "exception"])
def test_adsorption_row_preserves_system_failure_without_mae_imputation(failure_mode: str) -> None:
    energies = {
        ("Pt", "Pt", "C", "O"): -20.0,
        ("Pt", "Pt"): -15.0,
        ("C", "O"): -4.0,
    }
    fail_symbols = None
    if failure_mode == "nonfinite":
        energies[("Pt", "Pt")] = float("nan")
    else:
        fail_symbols = ("Pt", "Pt")
    calculator = SystemEnergyCalculator(energies, fail_symbols=fail_symbols)

    result = run_row("adsorption_energy", adsorption_manifest(), calculator)

    prediction = result["predictions"][0]
    assert prediction["status"] == "failed"
    assert prediction["adsorption_energy_ev"] is None
    assert prediction["signed_error_ev"] is None
    assert prediction["systems"][1]["status"] == "failed"
    assert prediction["systems"][1]["energy_ev"] is None
    assert prediction["systems"][1]["error"]
    assert result["metrics"]["adsorption_energy_mae"] is None
    assert result["metrics"]["successful_candidates"] == 0
    assert result["metrics"]["failed_candidates"] == 1


def test_adsorption_metric_rejects_overflowing_signed_error_without_warning() -> None:
    predictions = [
        {
            "candidate_id": "overflow",
            "status": "completed",
            "adsorption_energy_ev": 1e308,
            "reference": {"adsorption_energy_ev": -1e308},
        },
        {
            "candidate_id": "nominal",
            "status": "completed",
            "adsorption_energy_ev": -1.0,
            "reference": {"adsorption_energy_ev": -1.2},
        },
    ]

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _, _, metrics = evaluate_row("adsorption_energy", predictions, {"error_tolerance": 0.1})

    assert metrics["adsorption_energy_mae"] == pytest.approx(0.2)
    assert metrics["successful_candidates"] == 1
    assert metrics["failed_candidates"] == 1
    assert metrics["failed_candidate_ids"] == ["overflow"]


def test_adsorption_row_preserves_raw_energy_when_contribution_overflows() -> None:
    manifest = adsorption_manifest()
    systems = manifest["row_fixtures"]["adsorption_energy"]["structures"][0]["systems"]
    # Single-Pt clean slab with coefficient -2.0 keeps stoichiometry element-balanced.
    systems[1]["symbols"] = ["Pt"]
    systems[1]["positions"] = [[0, 0, 0]]
    systems[1]["stoichiometric_coefficient"] = -2.0
    calculator = SystemEnergyCalculator(
        {
            ("Pt", "Pt", "C", "O"): -20.0,
            ("Pt",): 1e308,
            ("C", "O"): -4.0,
        }
    )

    result = run_row("adsorption_energy", manifest, calculator)

    prediction = result["predictions"][0]
    assert prediction["status"] == "failed"
    assert prediction["adsorption_energy_ev"] is None
    clean_slab = prediction["systems"][1]
    assert clean_slab["status"] == "failed"
    # The finite raw calculator energy is preserved even though the
    # stoichiometric contribution overflowed.
    assert clean_slab["energy_ev"] == 1e308
    assert clean_slab["reaction_contribution_ev"] is None
    assert "non-finite" in clean_slab["error"]
    assert result["metrics"]["adsorption_energy_mae"] is None


def test_adsorption_failed_prediction_is_not_reused_from_checkpoint() -> None:
    energies = {
        ("Pt", "Pt", "C", "O"): -20.0,
        ("Pt", "Pt"): -15.0,
        ("C", "O"): -4.0,
    }
    failing = SystemEnergyCalculator(energies, fail_symbols=("Pt", "Pt"))
    checkpoint = MemoryCheckpoint()

    first = run_row("adsorption_energy", adsorption_manifest(), failing, checkpoint=checkpoint)

    assert first["predictions"][0]["status"] == "failed"
    assert checkpoint.written == 0  # failed predictions must not be persisted

    # A stale failed entry (written before the fix) must not be reused either:
    # the system is retried and completes with a healthy calculator.
    case = adsorption_manifest()["row_fixtures"]["adsorption_energy"]["structures"][0]
    checkpoint.record_prediction("adsorption_energy", 0, case, first["predictions"][0])
    recovered = run_row("adsorption_energy", adsorption_manifest(), SystemEnergyCalculator(energies), checkpoint=checkpoint)

    assert recovered["predictions"][0]["status"] == "completed"
    assert recovered["metrics"]["adsorption_energy_mae"] == pytest.approx(0.2)


def test_combined_support_manifest_is_row_complete() -> None:
    path = Path(__file__).with_name("fixtures") / "canonical_distill_support_mptrj_train_plus_elastic_v1.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    counts = {
        row_id: len(group.get("structures") or [])
        for row_id, group in (manifest.get("row_fixtures") or {}).items()
    }

    assert manifest["fixture_id"] == "canonical-distill-support-mptrj-train-plus-elastic-v1"
    assert counts["energy_volume"] >= 20
    assert counts["forces"] >= 20
    assert counts["stress"] >= 20
    assert counts["relaxation_stability"] >= 3
    assert counts["elastic_constants"] >= 6


def test_force_score_uses_absolute_rmse_not_relative_zero_denominator() -> None:
    predictions = [
        {
            "forces_ev_per_angstrom": [[0.11, 0.0, 0.0], [0.0, -0.09, 0.0]],
            "reference": {"forces_ev_per_angstrom": [[0.10, 0.0, 0.0], [0.0, -0.10, 0.0]]},
        }
    ]

    score, unit, metrics = evaluate_row("forces", predictions, {"error_tolerance": 0.20})

    assert unit == "row_native_physical_score"
    assert metrics["primary_metric"] == "force_rmse_ev_per_angstrom"
    assert np.isclose(metrics["error"], np.sqrt((0.01**2 + 0.01**2) / 6))
    assert score > 0.95


def test_elastic_score_fits_finite_strain_stress_response() -> None:
    reference = {
        "C11": 100.0,
        "C22": 100.0,
        "C33": 100.0,
        "C44": 40.0,
        "C55": 40.0,
        "C66": 40.0,
    }
    strains = np.eye(6) * 0.01
    c = np.diag([100.0, 100.0, 100.0, 40.0, 40.0, 40.0])
    predictions = [
        {
            "strain_voigt": strain.tolist(),
            "stress_gpa": (c @ strain).tolist(),
            "reference": {"elastic_constants_gpa": reference},
        }
        for strain in strains
    ]

    score, unit, metrics = evaluate_row("elastic_constants", predictions, {"error_tolerance": 50.0})

    assert unit == "row_native_physical_score"
    assert metrics["primary_metric"] == "elastic_cij_mae_gpa"
    assert metrics["error"] < 1e-9
    assert np.isclose(score, 1.0)


def test_elastic_score_groups_materials_against_their_own_references() -> None:
    strains = [np.zeros(6), *(np.eye(6) * 0.01)]
    materials = {
        "Al": {
            "reference": {"C11": 100.0, "C22": 100.0, "C33": 100.0},
            "matrix": np.diag([100.0, 100.0, 100.0, 40.0, 40.0, 40.0]),
        },
        "Mo": {
            "reference": {"C11": 400.0, "C22": 400.0, "C33": 400.0},
            "matrix": np.diag([400.0, 400.0, 400.0, 90.0, 90.0, 90.0]),
        },
    }
    predictions = [
        {
            "material_id": material_id,
            "strain_voigt": strain.tolist(),
            "stress_gpa": (payload["matrix"] @ strain).tolist(),
            "reference": {"elastic_constants_gpa": payload["reference"]},
        }
        for material_id, payload in materials.items()
        for strain in strains
    ]

    score, _, metrics = evaluate_row("elastic_constants", predictions, {"error_tolerance": 50.0})

    assert np.isclose(score, 1.0)
    assert metrics["error"] < 1e-9
    assert set(metrics["elastic_constants_gpa_by_material"]) == {"Al", "Mo"}
    assert metrics["elastic_errors_by_material"]["Al"] < 1e-9
    assert metrics["elastic_errors_by_material"]["Mo"] < 1e-9


def test_elastic_fit_is_intercept_aware_for_residual_stress_offsets() -> None:
    reference = {"C11": 120.0, "C22": 90.0, "C33": 80.0}
    c = np.diag([120.0, 90.0, 80.0, 35.0, 35.0, 35.0])
    residual_stress = np.asarray([2.5, -1.0, 1.2, 0.4, -0.2, 0.3])
    strains = [np.zeros(6), *(np.eye(6) * 0.01), *(-np.eye(6) * 0.01)]
    predictions = [
        {
            "material_id": "Al",
            "strain_voigt": strain.tolist(),
            "stress_gpa": (residual_stress + c @ strain).tolist(),
            "reference": {"elastic_constants_gpa": reference},
        }
        for strain in strains
    ]

    score, _, metrics = evaluate_row("elastic_constants", predictions, {"error_tolerance": 50.0})

    assert np.isclose(score, 1.0)
    assert metrics["error"] < 1e-9


def test_run_row_uses_prediction_checkpoint_for_completed_cases() -> None:
    manifest = {
        "schema": "lupine.mlip.fixture_manifest.v2",
        "fixture_id": "checkpoint-test",
        "reference_provenance": {"source": "unit-test"},
        "row_specs": {"energy_volume": {"min_cases": 1, "error_tolerance": 1.0}},
        "row_fixtures": {
            "energy_volume": {
                "structures": [
                    {
                        "structure_id": "Al-one",
                        "symbols": ["Al"],
                        "positions": [[0.0, 0.0, 0.0]],
                        "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],
                        "pbc": True,
                        "reference": {"energy_ev_per_atom": 2.0},
                    }
                ]
            }
        },
    }
    checkpoint = MemoryCheckpoint()
    first_calc = CountingEnergyCalculator(2.0)
    first = run_row("energy_volume", manifest, first_calc, checkpoint=checkpoint)

    second_calc = CountingEnergyCalculator(99.0)
    second = run_row("energy_volume", manifest, second_calc, checkpoint=checkpoint)

    assert first["score"] == second["score"] == 1.0
    assert first_calc.calls == 1
    assert second_calc.calls == 0
    assert checkpoint.written == 1
    assert checkpoint.loaded == 1
