"""Unit tests for lupine_distill.statics.eos (Birch-Murnaghan fitting).

Synthetic-data roundtrips are exact because a 3rd-order Birch-Murnaghan
energy is exactly cubic in V^(-2/3); the EMT checks assert physical sanity.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    ConvergenceError,
    InputValidationError,
    compute_eos,
    compute_lattice,
    fit_birch_murnaghan,
)
from lupine_distill.statics.units import EV_PER_A3_TO_GPA

pytestmark = pytest.mark.unit


def _bm3_energy(v: np.ndarray, e0: float, v0: float, b0_ev: float, b0p: float) -> np.ndarray:
    """Exact 3rd-order Birch-Murnaghan energy (b0 in eV/A^3)."""
    eta = (v0 / v) ** (2.0 / 3.0)
    return e0 + 9.0 * v0 * b0_ev / 16.0 * (
        (eta - 1.0) ** 3 * b0p + (eta - 1.0) ** 2 * (6.0 - 4.0 * eta)
    )


class TestBirchMurnaghanFit:
    def test_exact_roundtrip(self) -> None:
        e0, v0, b0_gpa, b0p = -5.4321, 42.0, 180.0, 4.5
        b0_ev = b0_gpa / EV_PER_A3_TO_GPA
        volumes = np.linspace(0.94, 1.06, 11) * v0
        energies = _bm3_energy(volumes, e0, v0, b0_ev, b0p)
        fit = fit_birch_murnaghan(volumes, energies)
        assert fit.v0_a3 == pytest.approx(v0, rel=1e-6)
        assert fit.e0_ev == pytest.approx(e0, rel=1e-6)
        assert fit.b0_gpa == pytest.approx(b0_gpa, rel=1e-5)
        assert fit.b0_prime == pytest.approx(b0p, rel=1e-4)
        assert fit.rms_residual_ev < 1e-8

    def test_too_few_points(self) -> None:
        with pytest.raises(InputValidationError):
            fit_birch_murnaghan([40.0, 41.0, 42.0, 43.0], [1.0, 0.5, 0.4, 0.9])

    def test_mismatched_lengths(self) -> None:
        with pytest.raises(InputValidationError):
            fit_birch_murnaghan([40.0, 41.0, 42.0, 43.0, 44.0], [1.0, 0.5, 0.4])

    def test_nonpositive_volume(self) -> None:
        with pytest.raises(InputValidationError):
            fit_birch_murnaghan([-1.0, 41.0, 42.0, 43.0, 44.0], [1, 2, 3, 4, 5])

    def test_duplicate_volumes(self) -> None:
        with pytest.raises(InputValidationError):
            fit_birch_murnaghan([42.0, 42.0, 43.0, 44.0, 45.0], [1, 2, 3, 4, 5])

    def test_nonfinite_energy(self) -> None:
        with pytest.raises(InputValidationError):
            fit_birch_murnaghan([40.0, 41.0, 42.0, 43.0, 44.0], [1.0, math.nan, 3.0, 4.0, 5.0])

    def test_monotonic_curve_has_no_minimum(self) -> None:
        volumes = np.linspace(40.0, 46.0, 11)
        energies = np.linspace(1.0, 0.0, 11)  # strictly downhill: no minimum
        with pytest.raises(ConvergenceError):
            fit_birch_murnaghan(volumes, energies)


class TestComputeEosEmt:
    def test_ni_fcc_bulk_modulus_sane(self) -> None:
        lattice = compute_lattice(EMT(), "Ni", "fcc")
        eos = compute_eos(EMT(), "Ni", "fcc", lattice.a0_angstrom)
        assert 100.0 < eos.b0_gpa < 250.0
        assert 9.0 < eos.v0_a3_per_atom < 13.0
        assert 2.0 < eos.b0_prime < 8.0
        assert eos.wall_time_seconds >= 0.0
        assert len(eos.volumes_a3) == eos.n_points == 11
        assert len(eos.energies_ev) == 11

    def test_eos_requires_bracketing_lattice_constant(self) -> None:
        # A wildly wrong lattice constant cannot bracket the minimum.
        with pytest.raises(ConvergenceError):
            compute_eos(EMT(), "Ni", "fcc", 4.6)

    def test_eos_input_validation(self) -> None:
        with pytest.raises(InputValidationError):
            compute_eos(EMT(), "Ni", "fcc", 3.5, n_points=3)
        with pytest.raises(InputValidationError):
            compute_eos(EMT(), "Ni", "fcc", 3.5, volume_span=0.0)
        with pytest.raises(InputValidationError):
            compute_eos(EMT(), "Ni", "fcc", -3.5)

    def test_canonical_inputs_deterministic(self) -> None:
        r1 = compute_eos(EMT(), "Ni", "fcc", 3.487)
        r2 = compute_eos(EMT(), "Ni", "fcc", 3.487)
        c1, c2 = r1.canonical_inputs(), r2.canonical_inputs()
        assert c1 == c2
        assert json.dumps(c1, sort_keys=True) == json.dumps(c2, sort_keys=True)
        assert "wall_time_seconds" not in c1
