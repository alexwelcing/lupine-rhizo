from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from z2_soc_tc import (
    CellMeasurementError,
    GPAWSpinEnergyEngine,
    load_fixture,
    run_soc_tc_rows,
    validate_fixture,
)

PROTOCOL = {
    "geometry_force_convergence_ev_per_angstrom": 0.05,
    "geometry_maximum_steps": 20,
    "geometry_method": "mlip_fire_relaxation",
    "gpaw_plane_wave_cutoff_ev": 500.0,
    "gpaw_kpoint_density_per_angstrom": 6.0,
    "gpaw_fermi_width_ev": 0.05,
    "gpaw_convergence_energy_ev": 1e-6,
    "gpaw_maximum_scf_iterations": 200,
    "minimum_local_moment_muB": 0.25,
    "minimum_moment_retention_fraction": 0.5,
    "orientation_tie_tolerance_mev": 1e-6,
    "scalar_method": "gpaw_pbe_collinear_spin_polarized",
    "soc_axes_degrees": {"x": [90.0, 0.0], "y": [90.0, 90.0], "z": [0.0, 0.0]},
    "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
    "tc_model": "tiwari_eq3_eq4_nearest_neighbor",
    "failure_policy": "fail cell without measurement-row serialization",
}


def fixture(*, tier: str = "auto", modes: list[str] | None = None) -> dict[str, Any]:
    modes = modes or ["mae_ranking", "tc_prediction"]
    materials = []
    for index in range(5):
        j_parallel = 5.0 + index
        j_perpendicular = j_parallel + 0.5
        exchange = (j_parallel + j_perpendicular) / 2.0
        delta = (j_perpendicular - j_parallel) / (2.0 * exchange)
        materials.append(
            {
                "material_id": f"material-{index}",
                "formula": f"M{index}X2",
                "lattice": "honeycomb",
                "spin": 1.0,
                "nearest_neighbors": 3,
                "magnetic_atom_indices": [0, 1],
                "afm_signs": [1, -1],
                "structure": {
                    "symbols": ["Cr", "Cr"],
                    "positions_angstrom": [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
                    "cell_angstrom": [[5.0, 0.0, 0.0], [0.0, 5.0, 0.0], [0.0, 0.0, 15.0]],
                    "pbc": [True, True, False],
                    "initial_magmoms": [2.0, 2.0],
                },
                "reference": {
                    "mae_xz_mev_per_cell": -(index + 1.0),
                    "mae_yz_mev_per_cell": -(index + 0.5),
                    "exchange_mev": exchange,
                    "exchange_anisotropy": delta,
                    "tc_k": {"green": 100.0, "mc": 90.0, "rnsw": 80.0},
                    "tc_envelope_k": [70.0, 200.0],
                },
            }
        )
    return {
        "schema": "lupine.z2.soc_tc_fixture.v1",
        "fixture_id": "synthetic-z2",
        "requested_tier": tier,
        "measurement_modes": modes,
        "materials": materials,
        "execution_protocol": dict(PROTOCOL),
        "reference_provenance": {
            "source_id": "synthetic-regression-v1",
            "source_url": "https://example.test/z2-fixture",
            "sha256": "sha256:" + "a" * 64,
        },
    }


class SyntheticEngine:
    def __init__(self, fail_material_id: str | None = None) -> None:
        self.fail_material_id = fail_material_id

    def evaluate_screen(self, material: dict[str, Any]) -> dict[str, Any]:
        if material["material_id"] == self.fail_material_id:
            raise RuntimeError("synthetic scalar failure")
        return {
            "fm_scalar_energy_ev": -10.0,
            "afm_scalar_energy_ev": -9.97,
            "minimum_final_local_moment_muB": 1.8,
            "moment_retention_fraction": 0.9,
        }

    def evaluate_ordering(self, material: dict[str, Any], ordering: str) -> dict[str, Any]:
        if material["material_id"] == self.fail_material_id:
            raise RuntimeError("synthetic SOC failure")
        index = int(material["material_id"].split("-")[-1])
        fm = {"x": 0.0, "y": -(index + 0.5) / 1000.0, "z": -(index + 1.0) / 1000.0}
        if ordering == "fm":
            energies = fm
        else:
            factor = 2.0 * material["nearest_neighbors"] * material["spin"] ** 2
            j_parallel_ev = (5.0 + index) / 1000.0
            j_perpendicular_ev = (5.5 + index) / 1000.0
            energies = {
                "x": fm["x"] + factor * j_parallel_ev,
                "y": fm["y"] + factor * j_parallel_ev,
                "z": fm["z"] + factor * j_perpendicular_ev,
            }
        return {
            "ordering": ordering,
            "scalar_total_energy_ev": 0.0,
            "scalar_band_energy_ev": 0.0,
            "soc_band_energies_ev": energies,
            "orientation_energies_ev": energies,
            "soc_method": PROTOCOL["soc_method"],
            "geometry_method": PROTOCOL["geometry_method"],
        }


def assert_no_placeholders(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert key
            assert_no_placeholders(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_placeholders(item)
    elif isinstance(value, float):
        assert math.isfinite(value)
    elif isinstance(value, str):
        assert value and value.lower() not in {"failed", "abstained", "null", "nan", "placeholder"}
    else:
        assert value is not None


def test_auto_fixture_emits_separate_complete_mae_and_tc_rows() -> None:
    source = fixture()

    rows = run_soc_tc_rows(source, SyntheticEngine())

    assert [row["row_spec"]["measurement_mode"] for row in rows] == [
        "mae_ranking",
        "tc_prediction",
    ]
    assert all(row["n_structures"] == 5 for row in rows)
    assert all(row["fixture_contract"]["release_ready"] is True for row in rows)
    mae = rows[0]
    assert mae["predictions"][0]["ranked_orientations"] == ["z", "y", "x"]
    assert mae["predictions"][0]["easy_axis"] == "z"
    assert mae["predictions"][0]["fidelity_tier_used"] == "high_soc"
    assert mae["metrics"]["magnetocrystalline_anisotropy_rank_correlation"] == 1.0
    tc = rows[1]["predictions"][0]
    assert tc["exchange_parallel_mev"] == pytest.approx(5.0)
    assert tc["exchange_perpendicular_mev"] == pytest.approx(5.5)
    assert tc["exchange_mev"] == pytest.approx(5.25)
    assert tc["exchange_anisotropy"] == pytest.approx(0.5 / 10.5)
    assert tc["fidelity_tier_used"] == "high_soc"
    assert_no_placeholders(rows)


def test_synthetic_fixture_loader_returns_validated_contract() -> None:
    source = fixture()

    loaded, contract = load_fixture(
        "memory://synthetic-z2", lambda _: json.dumps(source).encode("utf-8")
    )

    assert loaded == source
    assert contract == {
        "schema": "lupine.z2.soc_tc_fixture.v1",
        "fixture_id": "synthetic-z2",
        "material_count": 5,
        "minimum_material_count": 5,
        "release_ready": True,
        "blockers": [],
    }


def test_low_collinear_fixture_emits_only_a_complete_screening_row() -> None:
    source = fixture(tier="low_collinear", modes=["screening"])

    row = run_soc_tc_rows(source, SyntheticEngine())[0]

    assert row["row_spec"]["measurement_mode"] == "screening"
    assert row["metrics"]["promotable_fraction"] == 1.0
    assert row["predictions"][0]["fidelity_tier_used"] == "low_collinear"
    assert row["predictions"][0]["promotable_to_high_soc"] is True
    assert row["predictions"][0]["screening_reasons"] == []
    assert_no_placeholders(row)


def test_invalid_low_tier_mae_request_is_rejected_before_execution() -> None:
    source = fixture(tier="low_collinear", modes=["mae_ranking"])

    with pytest.raises(ValueError, match="low_collinear.*screening"):
        validate_fixture(source)


def test_material_failure_aborts_atomically_without_a_placeholder_row() -> None:
    source = fixture()

    with pytest.raises(CellMeasurementError, match="material-2"):
        run_soc_tc_rows(source, SyntheticEngine(fail_material_id="material-2"))


def test_orientation_ties_use_average_ranks_and_xyz_presentation_order() -> None:
    source = fixture(tier="high_soc", modes=["mae_ranking"])
    source["execution_protocol"]["orientation_tie_tolerance_mev"] = 0.6

    prediction = run_soc_tc_rows(source, SyntheticEngine())[0]["predictions"][0]

    assert prediction["ranked_orientations"] == ["z", "y", "x"]
    assert prediction["orientation_ranks"] == {"x": 3.0, "y": 1.5, "z": 1.5}


def test_gpaw_engine_exposes_collinear_screening_evidence() -> None:
    source = fixture(tier="low_collinear", modes=["screening"])
    material = source["materials"][0]
    protocol = source["execution_protocol"]

    class ImmediateOptimizer:
        def __init__(self, atoms, logfile=None):
            self.atoms = atoms

        def run(self, *, fmax: float, steps: int) -> bool:
            return True

    class ScalarCalculator:
        def __init__(self, ordering: str) -> None:
            self.ordering = ordering

        def get_magnetic_moments(self, atoms):
            return atoms.get_initial_magnetic_moments() * 0.9

    engine = GPAWSpinEnergyEngine(
        geometry_calculator=object(),
        protocol=protocol,
        scalar_calculator_factory=lambda atoms, ordering, frozen: ScalarCalculator(ordering),
        scalar_energy=lambda calc, atoms: -10.0 if calc.ordering == "fm" else -9.97,
        optimizer_factory=ImmediateOptimizer,
    )

    screen = engine.evaluate_screen(material)

    assert screen == {
        "fm_scalar_energy_ev": -10.0,
        "afm_scalar_energy_ev": -9.97,
        "minimum_final_local_moment_muB": pytest.approx(1.8),
        "moment_retention_fraction": pytest.approx(0.9),
    }


def test_z2_image_copies_strict_fixture_runner_module() -> None:
    dockerfile = Path(__file__).with_name("Dockerfile.z2").read_text(encoding="utf-8")

    assert "COPY gcp/mlip-cell-runner/z2_soc_tc_contract.py ./" in dockerfile
