from __future__ import annotations

import pytest
from z2_soc_tc import derive_spin_observables, run_soc_tc_row, tc_estimates_k


class ReferenceEnergyEngine:
    def __init__(self, fail_material_id: str | None = None) -> None:
        self.fail_material_id = fail_material_id

    def evaluate_ordering(self, material: dict, ordering: str) -> dict:
        if material["material_id"] == self.fail_material_id:
            raise RuntimeError("intentional SOC failure")
        reference = material["reference"]
        spin = material["spin"]
        neighbors = material["nearest_neighbors"]
        exchange_ev = reference["exchange_mev"] / 1000.0
        delta = reference["exchange_anisotropy"]
        # Tiwari et al. use Δ = B / J for the anisotropic Heisenberg
        # Hamiltonian.  The in-plane AFM-FM split measures J; the
        # out-of-plane split measures J + B.
        j_perpendicular = exchange_ev * (1.0 + delta)
        j_parallel = exchange_ev
        fm_parallel = 0.0
        fm_perpendicular = reference["mae_xz_mev_per_cell"] / 1000.0
        if ordering == "fm":
            perpendicular = fm_perpendicular
            parallel = fm_parallel
        else:
            factor = 2.0 * neighbors * spin**2
            perpendicular = fm_perpendicular + factor * j_perpendicular
            parallel = fm_parallel + factor * j_parallel
        return {
            "ordering": ordering,
            "perpendicular_energy_ev": perpendicular,
            "parallel_energy_ev": parallel,
            "engine": "unit-reference",
        }


def panel_fixture() -> dict:
    materials = []
    for index, (exchange, delta, mae) in enumerate(
        [
            (2.0, 0.01, -0.1),
            (3.0, 0.02, -0.4),
            (4.0, 0.03, -0.9),
            (5.0, 0.04, -1.6),
            (6.0, 0.05, -2.5),
        ]
    ):
        tc = tc_estimates_k(
            exchange_mev=exchange,
            exchange_anisotropy=delta,
            spin=1.5,
            lattice="honeycomb",
        )
        materials.append(
            {
                "material_id": f"material-{index}",
                "formula": f"M{index}X3",
                "lattice": "honeycomb",
                "spin": 1.5,
                "nearest_neighbors": 3,
                "magnetic_atom_indices": [0, 1],
                "afm_signs": [1, -1],
                "structure": {
                    "symbols": ["Cr", "Cr"],
                    "positions_angstrom": [[0, 0, 0], [1, 1, 0]],
                    "cell_angstrom": [[5, 0, 0], [0, 5, 0], [0, 0, 15]],
                    "pbc": [True, True, False],
                    "initial_magmoms": [3.0, 3.0],
                },
                "reference": {
                    "exchange_mev": exchange,
                    "exchange_anisotropy": delta,
                    "mae_xz_mev_per_cell": mae,
                    "mae_yz_mev_per_cell": mae,
                    "tc_k": tc,
                    "tc_envelope_k": [min(tc.values()), max(tc.values())],
                },
            }
        )
    return {
        "schema": "lupine.z2.soc_tc_panel.v1",
        "panel_id": "unit-z2-panel",
        "measurement": {"minimum_material_count": 5},
        "execution_protocol": {
            "failure_policy": "record failure without imputation",
            "soc_method": "non-selfconsistent force theorem",
            "tc_model": "Tiwari et al. Eq. (3) nearest-neighbor analytical fit",
        },
        "provenance": {"supplement_sha256": "sha256:" + "a" * 64},
        "materials": materials,
    }


def test_tc_formula_reproduces_published_cri3_values() -> None:
    estimates = tc_estimates_k(
        exchange_mev=2.048469,
        exchange_anisotropy=0.068308,
        spin=1.5,
        lattice="honeycomb",
    )

    # Eq. (3) is a rounded two-parameter fit to the exact-method values in
    # Supplemental Table 1, not an identity.  It reproduces each within 1 K.
    assert estimates == pytest.approx(
        {"green": 41.3, "mc": 30.9, "rnsw": 21.4}, abs=1.0
    )


def test_spin_observables_recover_exchange_anisotropy_and_signed_mae() -> None:
    material = panel_fixture()["materials"][2]
    engine = ReferenceEnergyEngine()

    prediction = derive_spin_observables(
        material,
        engine.evaluate_ordering(material, "fm"),
        engine.evaluate_ordering(material, "afm"),
    )

    assert prediction["exchange_mev"] == pytest.approx(4.0)
    assert prediction["exchange_anisotropy"] == pytest.approx(0.03)
    assert prediction["mae_xz_mev_per_cell"] == pytest.approx(-0.9)
    assert prediction["easy_axis"] == "out_of_plane"
    assert prediction["tc_k"] == pytest.approx(material["reference"]["tc_k"])


def test_easy_axis_requires_z_to_be_below_both_in_plane_axes() -> None:
    material = panel_fixture()["materials"][2]
    fm = {
        "parallel_energy_ev": -0.001,
        "y_energy_ev": 0.001,
        "perpendicular_energy_ev": 0.0,
    }
    afm = {
        "parallel_energy_ev": 0.035,
        "y_energy_ev": 0.037,
        "perpendicular_energy_ev": 0.03618,
    }

    prediction = derive_spin_observables(material, fm, afm)

    assert prediction["mae_xz_mev_per_cell"] == pytest.approx(1.0)
    assert prediction["mae_yz_mev_per_cell"] == pytest.approx(-1.0)
    assert prediction["easy_axis"] == "in_plane"


def test_soc_tc_row_scores_complete_mae_ranking_and_tc_panel() -> None:
    panel = panel_fixture()
    manifest = {
        "campaign_id": "unit-z2",
        "acceptance_test": {"threshold": 1.0},
    }

    result = run_soc_tc_row(manifest, panel, ReferenceEnergyEngine(), {"release_ready": True})

    assert result["score"] == pytest.approx(1.0)
    assert result["metrics"]["measurement_complete"] is True
    assert result["metrics"]["magnetocrystalline_anisotropy_rank_correlation"] == pytest.approx(1.0)
    assert result["metrics"]["easy_axis_sign_errors"] == 0
    assert result["metrics"]["tc_rnsw_mae_k"] == pytest.approx(0.0)
    assert result["metrics"]["tc_envelope_coverage"] == pytest.approx(1.0)


def test_soc_failure_is_recorded_without_imputation() -> None:
    panel = panel_fixture()
    manifest = {
        "campaign_id": "unit-z2",
        "acceptance_test": {"threshold": 1.0},
    }

    result = run_soc_tc_row(
        manifest,
        panel,
        ReferenceEnergyEngine(fail_material_id="material-2"),
        {"release_ready": True},
    )

    assert result["score"] == 0.0
    assert result["metrics"]["measurement_complete"] is False
    assert result["metrics"]["completed_material_count"] == 4
    assert result["metrics"]["failed_material_count"] == 1
    failure = result["predictions"][2]
    assert failure["status"] == "failed"
    assert failure["error_class"] == "RuntimeError"
    assert "tc_k" not in failure


def test_soc_tc_row_reuses_completed_checkpoint_predictions() -> None:
    panel = panel_fixture()
    manifest = {"campaign_id": "unit-z2", "acceptance_test": {"threshold": 1.0}}
    reference_engine = ReferenceEnergyEngine()
    cached = [
        derive_spin_observables(
            material,
            reference_engine.evaluate_ordering(material, "fm"),
            reference_engine.evaluate_ordering(material, "afm"),
        )
        for material in panel["materials"]
    ]

    class CompleteCheckpoint:
        def __init__(self) -> None:
            self.recorded = 0

        def get_prediction(self, row_id, case_index, case):
            assert row_id == "soc_tc"
            return cached[case_index]

        def record_prediction(self, row_id, case_index, case, prediction):
            self.recorded += 1

    class MustNotRunEngine:
        def evaluate_ordering(self, material, ordering):
            raise AssertionError("completed checkpoint should bypass the SOC engine")

    checkpoint = CompleteCheckpoint()
    result = run_soc_tc_row(
        manifest,
        panel,
        MustNotRunEngine(),
        {"release_ready": True},
        checkpoint=checkpoint,
    )

    assert result["metrics"]["measurement_complete"] is True
    assert result["score"] == pytest.approx(1.0)
    assert checkpoint.recorded == 0
