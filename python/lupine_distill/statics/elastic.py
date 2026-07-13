"""Cubic elastic constants from symmetric stress-strain finite differences.

C11 and C12 come from a uniaxial strain ``eps_xx = +/-delta`` (sigma_xx ->
C11, sigma_yy/sigma_zz -> C12); C44 from a tensor shear
``eps_yz = eps_zy = +/-delta``.

Conventions (each one validated in ``tests/test_statics_elastic.py`` against
a synthetic linear-elastic calculator with a known stiffness tensor, and via
the cubic identity ``B0 = (C11 + 2*C12)/3`` against the independent BM3
energy-curvature B0 on EMT Cu):

* Strain is the symmetric *tensor* strain ``eps``, applied as
  ``cell' = cell0 @ (I + eps)`` with atomic positions scaled affinely.
* ``Atoms.get_stress(voigt=True)`` returns
  ``(s_xx, s_yy, s_zz, s_yz, s_xz, s_xy)`` in eV/A^3 with ASE's sign
  convention ``sigma = (1/V) dE/deps`` (tension positive), so
  ``C11 = (s_xx(+d) - s_xx(-d)) / (2 d)``.
* Hooke's law in Voigt form uses the *engineering* shear
  ``gamma_yz = 2 eps_yz``: ``sigma_yz = C44 * gamma_yz = 2 * C44 * eps_yz``,
  hence ``C44 = (s_yz(+d) - s_yz(-d)) / (4 d)``.

``relax_internal=True`` relaxes atomic positions at the fixed strained cell
before measuring stress (relaxed-ion constants). This matters for structures
with symmetry-free internal degrees of freedom under the applied strain
(e.g. the fluorite/antifluorite C44); clamped-ion values are upper bounds
there. For high-symmetry cells (fcc/bcc/rocksalt) forces vanish by symmetry
and both paths agree.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Final

import numpy as np
from ase.calculators.calculator import Calculator

from lupine_distill.statics.errors import CalculationError, InputValidationError
from lupine_distill.statics.relax import relax_positions, validate_relax_parameters
from lupine_distill.statics.report import result_dict
from lupine_distill.statics.structures import (
    build_structure,
    normalize_structure_type,
    validate_lattice_constant,
)
from lupine_distill.statics.units import EV_PER_A3_TO_GPA

DEFAULT_STRAIN_DELTA: Final[float] = 0.5e-2
_MIN_STRAIN_DELTA: Final[float] = 1.0e-5
_MAX_STRAIN_DELTA: Final[float] = 0.05

DEFAULT_ELASTIC_FMAX: Final[float] = 0.01
DEFAULT_ELASTIC_OPTIMIZER: Final[str] = "FIRE"
DEFAULT_ELASTIC_MAX_STEPS: Final[int] = 500

VOIGT_CONVENTION: Final[str] = (
    "ase_voigt(xx,yy,zz,yz,xz,xy); tensor strain applied as "
    "cell' = cell0 @ (I + eps); sigma_yz = 2*C44*eps_yz (engineering shear)"
)


@dataclass(frozen=True)
class CubicElasticResult:
    """Cubic C11/C12/C44 from symmetric stress-strain finite differences."""

    formula: str
    structure_type: str
    a0_angstrom: float
    delta: float
    relax_internal: bool
    c11_gpa: float
    c12_gpa: float
    c44_gpa: float
    bulk_modulus_from_cij_gpa: float
    n_atoms_cell: int
    n_relax_steps_total: int
    fmax: float
    optimizer: str
    max_steps: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "cubic_elastic",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "a0_angstrom": self.a0_angstrom,
            "delta": self.delta,
            "relax_internal": self.relax_internal,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
            "voigt_convention": VOIGT_CONVENTION,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "c11_gpa": self.c11_gpa,
            "c12_gpa": self.c12_gpa,
            "c44_gpa": self.c44_gpa,
            "bulk_modulus_from_cij_gpa": self.bulk_modulus_from_cij_gpa,
            "n_atoms_cell": self.n_atoms_cell,
            "n_relax_steps_total": self.n_relax_steps_total,
        }
        units = {
            "c11_gpa": "GPa",
            "c12_gpa": "GPa",
            "c44_gpa": "GPa",
            "bulk_modulus_from_cij_gpa": "GPa",
        }
        return result_dict(
            "cubic_elastic", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


def validate_strain_delta(delta: float) -> float:
    """Validate the finite-difference strain amplitude."""
    try:
        value = float(delta)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"delta must be a number, got {delta!r}") from exc
    if not math.isfinite(value) or not _MIN_STRAIN_DELTA <= value <= _MAX_STRAIN_DELTA:
        raise InputValidationError(
            f"delta must be finite and in [{_MIN_STRAIN_DELTA}, {_MAX_STRAIN_DELTA}], "
            f"got {value}"
        )
    return value


def _strained_stress_voigt(
    calculator: Calculator,
    reference,
    eps: np.ndarray,
    *,
    relax_internal: bool,
    fmax: float,
    optimizer: str,
    max_steps: int,
) -> tuple[np.ndarray, int]:
    """Voigt stress (eV/A^3) of the strained cell; returns (stress, relax steps)."""
    work = reference.copy()
    work.set_cell(
        reference.get_cell().array @ (np.eye(3) + eps), scale_atoms=True
    )
    n_steps = 0
    if relax_internal:
        work, _, n_steps = relax_positions(
            work, calculator, fmax=fmax, optimizer=optimizer, max_steps=max_steps
        )
    else:
        work.calc = calculator
    try:
        stress = np.asarray(work.get_stress(voigt=True), dtype=float)
    except Exception as exc:
        raise CalculationError(
            f"calculator could not provide stress for "
            f"{work.get_chemical_formula()}: {exc}"
        ) from exc
    if stress.shape != (6,) or not np.all(np.isfinite(stress)):
        raise CalculationError(
            f"calculator returned malformed/non-finite stress for "
            f"{work.get_chemical_formula()}: {stress!r}"
        )
    return stress, n_steps


def compute_cubic_elastic_constants(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    delta: float = DEFAULT_STRAIN_DELTA,
    relax_internal: bool = False,
    fmax: float = DEFAULT_ELASTIC_FMAX,
    optimizer: str = DEFAULT_ELASTIC_OPTIMIZER,
    max_steps: int = DEFAULT_ELASTIC_MAX_STEPS,
) -> CubicElasticResult:
    """Cubic C11, C12, C44 by symmetric stress differences at ``a0_angstrom``.

    The reference cell should be the relaxed lattice constant (e.g. from
    :func:`lupine_distill.statics.compute_lattice`); residual reference
    stress cancels in the symmetric differences to first order. C12 is
    averaged over the two symmetry-equivalent transverse responses
    (sigma_yy and sigma_zz under eps_xx).
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    a0 = validate_lattice_constant(a0_angstrom)
    d = validate_strain_delta(delta)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    reference = build_structure(formula, st, a0)

    def stress_at(eps: np.ndarray) -> tuple[np.ndarray, int]:
        return _strained_stress_voigt(
            calculator,
            reference,
            eps,
            relax_internal=relax_internal,
            fmax=fmax_value,
            optimizer=optimizer_name,
            max_steps=steps_budget,
        )

    eps_xx = np.zeros((3, 3))
    eps_xx[0, 0] = d
    eps_yz = np.zeros((3, 3))
    eps_yz[1, 2] = eps_yz[2, 1] = d

    s_xx_plus, n1 = stress_at(eps_xx)
    s_xx_minus, n2 = stress_at(-eps_xx)
    s_yz_plus, n3 = stress_at(eps_yz)
    s_yz_minus, n4 = stress_at(-eps_yz)

    c11 = (s_xx_plus[0] - s_xx_minus[0]) / (2.0 * d) * EV_PER_A3_TO_GPA
    c12 = (
        (s_xx_plus[1] - s_xx_minus[1]) + (s_xx_plus[2] - s_xx_minus[2])
    ) / (4.0 * d) * EV_PER_A3_TO_GPA
    c44 = (s_yz_plus[3] - s_yz_minus[3]) / (4.0 * d) * EV_PER_A3_TO_GPA

    for name, value in (("C11", c11), ("C12", c12), ("C44", c44)):
        if not math.isfinite(value):
            raise CalculationError(
                f"{name} for {formula} ({st}) is non-finite: {value!r}"
            )

    return CubicElasticResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=a0,
        delta=d,
        relax_internal=relax_internal,
        c11_gpa=float(c11),
        c12_gpa=float(c12),
        c44_gpa=float(c44),
        bulk_modulus_from_cij_gpa=float((c11 + 2.0 * c12) / 3.0),
        n_atoms_cell=len(reference),
        n_relax_steps_total=n1 + n2 + n3 + n4,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


__all__ = [
    "DEFAULT_STRAIN_DELTA",
    "CubicElasticResult",
    "VOIGT_CONVENTION",
    "compute_cubic_elastic_constants",
    "validate_strain_delta",
]
