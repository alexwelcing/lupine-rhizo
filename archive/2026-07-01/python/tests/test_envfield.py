"""Tests for the environment-error-field correction calculator.

The force check is the load-bearing test: analytic forces must match
numerical differentiation of the same energy to tight tolerance, on a
low-symmetry (rattled slab) configuration where every code path is active.
"""

import numpy as np
import pytest
from ase.build import bulk, fcc110

from lupine_distill.statics.envfield import (
    FieldCorrectionCalculator,
    cubic_through_knots,
    fcc_cutoffs,
)
from lupine_distill.statics.errors import InputValidationError

A0 = 3.52  # Ni-like
KNOTS = {8.0: -0.20, 9.0: -0.15, 11.0: -0.03, 12.0: 0.0}


def _calc() -> FieldCorrectionCalculator:
    r_on, r_off = fcc_cutoffs(A0)
    return FieldCorrectionCalculator(KNOTS, r_on=r_on, r_off=r_off)


@pytest.mark.unit
def test_cubic_passes_through_knots() -> None:
    coeffs = cubic_through_knots(KNOTS)
    for c, v in KNOTS.items():
        val = sum(coeffs[k] * c**k for k in range(4))
        assert abs(val - v) < 1e-12


@pytest.mark.unit
def test_cubic_requires_exactly_four_knots() -> None:
    with pytest.raises(InputValidationError):
        cubic_through_knots({8.0: -0.2, 12.0: 0.0})


@pytest.mark.unit
def test_bulk_fcc_correction_vanishes() -> None:
    atoms = bulk("Ni", "fcc", a=A0, cubic=True) * (3, 3, 3)
    atoms.calc = _calc()
    assert abs(atoms.get_potential_energy()) < 1e-9
    assert np.abs(atoms.get_forces()).max() < 1e-9


@pytest.mark.unit
def test_slab_correction_negative_of_field_sum() -> None:
    # 8-layer (110) slab: top/bottom layers under-coordinated -> E_corr = -sum P(c) > 0
    # for all-negative knots (P < 0 below c=12).
    slab = fcc110("Ni", size=(2, 2, 8), a=A0, vacuum=10.0)
    slab.calc = _calc()
    e = slab.get_potential_energy()
    assert e > 0.1  # under-coordination present and correction is repulsive-signed


@pytest.mark.unit
def test_analytic_forces_match_numerical() -> None:
    rng = np.random.default_rng(20260702)
    slab = fcc110("Ni", size=(2, 2, 5), a=A0, vacuum=8.0)
    slab.positions += rng.normal(0.0, 0.05, slab.positions.shape)
    calc = _calc()
    slab.calc = calc
    analytic = slab.get_forces()
    eps = 1e-6
    for atom_index in (0, len(slab) // 2, len(slab) - 1):
        for axis in range(3):
            plus = slab.copy()
            plus.positions[atom_index, axis] += eps
            plus.calc = _calc()
            minus = slab.copy()
            minus.positions[atom_index, axis] -= eps
            minus.calc = _calc()
            numerical = -(plus.get_potential_energy() - minus.get_potential_energy()) / (2 * eps)
            assert abs(analytic[atom_index, axis] - numerical) < 1e-6, (
                f"atom {atom_index} axis {axis}: {analytic[atom_index, axis]} vs {numerical}"
            )


@pytest.mark.unit
def test_determinism() -> None:
    slab = fcc110("Ni", size=(2, 2, 5), a=A0, vacuum=8.0)
    e = []
    for _ in range(2):
        s = slab.copy()
        s.calc = _calc()
        e.append((s.get_potential_energy(), s.get_forces().copy()))
    assert e[0][0] == e[1][0]
    assert np.array_equal(e[0][1], e[1][1])
