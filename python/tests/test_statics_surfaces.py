"""Unit tests for lupine_distill.statics.surfaces (surface energies + SFE) with EMT."""

from __future__ import annotations

import json
import math

import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    SUPPORTED_SURFACES,
    InputValidationError,
    compute_lattice,
    compute_stacking_fault_energy,
    compute_surface_energies,
    compute_surface_energy,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def ni_a0() -> float:
    return compute_lattice(EMT(), "Ni", "fcc").a0_angstrom


class TestSurfaceEnergies:
    def test_ni_fcc_gamma_ordering(self, ni_a0: float) -> None:
        g100 = compute_surface_energy(EMT(), "Ni", "fcc", "100", ni_a0)
        g111 = compute_surface_energy(EMT(), "Ni", "fcc", "111", ni_a0)
        assert g100.gamma_j_per_m2 > 0.0
        assert g111.gamma_j_per_m2 > 0.0
        assert g111.gamma_j_per_m2 < g100.gamma_j_per_m2  # close-packed is lowest
        assert 0.3 < g111.gamma_j_per_m2 < 3.5
        assert g100.n_atoms_slab == 8  # 8 layers x 1x1 in-plane
        assert g100.area_a2 > 0.0

    def test_compute_surface_energies_defaults(self, ni_a0: float) -> None:
        results = compute_surface_energies(EMT(), "Ni", "fcc", ni_a0)
        millers = tuple(r.miller for r in results)
        assert millers == SUPPORTED_SURFACES["fcc"] == ("100", "110", "111")
        assert all(r.gamma_j_per_m2 > 0.0 for r in results)

    def test_surface_input_validation(self, ni_a0: float) -> None:
        with pytest.raises(InputValidationError):
            compute_surface_energy(EMT(), "Ni", "fcc", "211", ni_a0)
        with pytest.raises(InputValidationError):
            compute_surface_energy(EMT(), "Ni", "bcc", "111", ni_a0)
        with pytest.raises(InputValidationError):
            compute_surface_energy(EMT(), "Ni", "fcc", "100", ni_a0, layers=2)
        with pytest.raises(InputValidationError):
            compute_surface_energy(EMT(), "Ni", "fcc", "100", ni_a0, vacuum=2.0)
        with pytest.raises(InputValidationError):
            compute_surface_energy(EMT(), "NiAl", "fcc", "100", ni_a0)

    def test_surface_canonical_inputs_deterministic(self, ni_a0: float) -> None:
        r1 = compute_surface_energy(EMT(), "Ni", "fcc", "111", ni_a0)
        r2 = compute_surface_energy(EMT(), "Ni", "fcc", "111", ni_a0)
        assert r1.canonical_inputs() == r2.canonical_inputs()
        assert r1.gamma_j_per_m2 == pytest.approx(r2.gamma_j_per_m2, abs=1e-10)
        assert "wall_time_seconds" not in r1.canonical_inputs()
        json.dumps(r1.canonical_inputs())  # must be JSON-serializable


class TestStackingFault:
    def test_ni_intrinsic_sfe_finite(self, ni_a0: float) -> None:
        result = compute_stacking_fault_energy(EMT(), "Ni", ni_a0)
        assert math.isfinite(result.sfe_mj_per_m2)
        assert abs(result.sfe_mj_per_m2) < 300.0
        # The cheap hcp proxy is a cross-check field, not the primary method.
        assert math.isfinite(result.hcp_proxy_mj_per_m2)
        assert result.sfe_mj_per_m2 == pytest.approx(result.hcp_proxy_mj_per_m2, abs=60.0)
        assert result.method == "displaced_slab_fixed_inplane"

    def test_sfe_input_validation(self, ni_a0: float) -> None:
        with pytest.raises(InputValidationError):
            compute_stacking_fault_energy(EMT(), "NiAl", ni_a0)
        with pytest.raises(InputValidationError):
            compute_stacking_fault_energy(EMT(), "Ni", ni_a0, layers=4)
        with pytest.raises(InputValidationError):
            compute_stacking_fault_energy(EMT(), "Ni", ni_a0, fmax=0.0)

    def test_sfe_canonical_inputs_deterministic(self, ni_a0: float) -> None:
        r1 = compute_stacking_fault_energy(EMT(), "Ni", ni_a0)
        r2 = compute_stacking_fault_energy(EMT(), "Ni", ni_a0)
        assert r1.canonical_inputs() == r2.canonical_inputs()
        assert r1.sfe_mj_per_m2 == pytest.approx(r2.sfe_mj_per_m2, abs=1e-8)
