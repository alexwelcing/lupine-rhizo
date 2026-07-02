"""Fixed-cell relaxation helpers shared by the Tier-1 statics calculations.

Wraps ASE's deterministic local optimizers (FIRE, LBFGS) with fail-fast
parameter validation, :class:`ConvergenceError` on budget exhaustion, and
copy-in/copy-out semantics: the caller's ``Atoms`` object is never mutated.
"""

from __future__ import annotations

import math
from typing import Final

from ase import Atoms
from ase.calculators.calculator import Calculator
from ase.constraints import FixedLine
from ase.optimize import FIRE, LBFGS

from lupine_distill.statics.errors import (
    CalculationError,
    ConvergenceError,
    InputValidationError,
)

SUPPORTED_OPTIMIZERS: Final[tuple[str, ...]] = ("FIRE", "LBFGS")
_OPTIMIZER_CLASSES: Final[dict[str, type]] = {"FIRE": FIRE, "LBFGS": LBFGS}


def validate_relax_parameters(
    fmax: float, optimizer: str, max_steps: int
) -> tuple[float, str, int]:
    """Validate relaxation controls; returns ``(fmax, OPTIMIZER, max_steps)``."""
    try:
        fmax_value = float(fmax)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"fmax must be a number, got {fmax!r}") from exc
    if not math.isfinite(fmax_value) or fmax_value <= 0.0:
        raise InputValidationError(f"fmax must be finite and > 0 eV/A, got {fmax_value}")
    if not isinstance(optimizer, str) or optimizer.strip().upper() not in SUPPORTED_OPTIMIZERS:
        raise InputValidationError(
            f"optimizer must be one of {SUPPORTED_OPTIMIZERS}, got {optimizer!r}"
        )
    try:
        steps = int(max_steps)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"max_steps must be an integer, got {max_steps!r}") from exc
    if steps < 1:
        raise InputValidationError(f"max_steps must be >= 1, got {steps}")
    return fmax_value, optimizer.strip().upper(), steps


def single_point_energy(atoms: Atoms, calculator: Calculator) -> float:
    """Potential energy of a copy of ``atoms`` (eV); never mutates the input."""
    work = atoms.copy()
    work.calc = calculator
    try:
        energy = float(work.get_potential_energy())
    except Exception as exc:
        raise CalculationError(
            f"calculator failed on {work.get_chemical_formula()}: {exc}"
        ) from exc
    if not math.isfinite(energy):
        raise CalculationError(
            f"calculator returned non-finite energy for {work.get_chemical_formula()}"
        )
    return energy


def relax_positions(
    atoms: Atoms,
    calculator: Calculator,
    *,
    fmax: float,
    optimizer: str,
    max_steps: int,
    z_only: bool = False,
) -> tuple[Atoms, float, int]:
    """Relax atomic positions at fixed cell; returns ``(relaxed, energy_ev, n_steps)``.

    ``z_only=True`` constrains every atom to move along the cell's z axis only
    (used by the displaced-slab stacking-fault method to prevent slip-back).
    Raises :class:`ConvergenceError` if ``fmax`` is not reached in ``max_steps``.
    """
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    work = atoms.copy()
    if z_only:
        work.set_constraint(
            [FixedLine(i, direction=(0.0, 0.0, 1.0)) for i in range(len(work))]
        )
    work.calc = calculator
    opt = _OPTIMIZER_CLASSES[optimizer_name](work, logfile=None)
    try:
        converged = opt.run(fmax=fmax_value, steps=steps_budget)
    except Exception as exc:
        raise CalculationError(
            f"{optimizer_name} relaxation failed on {work.get_chemical_formula()}: {exc}"
        ) from exc
    n_steps = int(opt.get_number_of_steps())
    if not converged:
        raise ConvergenceError(
            f"{optimizer_name} did not reach fmax={fmax_value} eV/A on "
            f"{work.get_chemical_formula()} within {steps_budget} steps"
        )
    energy = float(work.get_potential_energy())
    if not math.isfinite(energy):
        raise CalculationError(
            f"relaxed energy is non-finite for {work.get_chemical_formula()}"
        )
    return work, energy, n_steps


__all__ = [
    "SUPPORTED_OPTIMIZERS",
    "relax_positions",
    "single_point_energy",
    "validate_relax_parameters",
]
