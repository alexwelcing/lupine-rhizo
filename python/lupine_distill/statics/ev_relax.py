"""Recentring energy-volume relaxation shared by lattice and formation runs.

The scan window recentres (up to ``max_recenter`` times) until the sampled
E-V curve brackets an interior minimum, fits Birch-Murnaghan, then refines
once with a scan centred on the fitted minimum. Deterministic throughout.
"""

from __future__ import annotations

from collections import Counter
from typing import Final

import numpy as np
from ase import Atoms
from ase.calculators.calculator import Calculator

from lupine_distill.statics.eos import (
    BirchMurnaghanFit,
    fit_birch_murnaghan,
    scan_energy_volume,
)
from lupine_distill.statics.errors import ConvergenceError, InputValidationError
from lupine_distill.statics.relax import single_point_energy
from lupine_distill.statics.structures import (
    build_structure,
    validate_lattice_constant,
)

DEFAULT_MAX_RECENTER: Final[int] = 8
_ISOLATED_ATOM_BOX_A: Final[float] = 30.0


def validate_max_recenter(max_recenter: int) -> int:
    """Validate the recentring budget for the E-V scan."""
    try:
        value = int(max_recenter)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"max_recenter must be an integer, got {max_recenter!r}"
        ) from exc
    if value < 0:
        raise InputValidationError(f"max_recenter must be >= 0, got {value}")
    return value


def scan_at(
    calculator: Calculator, formula: str, structure_type: str, a: float, span: float, n: int
) -> tuple[Atoms, tuple[float, ...], tuple[float, ...]]:
    """Build the cell at lattice constant ``a`` and scan E(V) around it."""
    atoms = build_structure(formula, structure_type, a)
    volumes, energies = scan_energy_volume(atoms, calculator, span, n)
    return atoms, volumes, energies


def _refined_fit(
    calculator: Calculator, formula: str, structure_type: str, fit: BirchMurnaghanFit,
    span: float, n: int,
) -> BirchMurnaghanFit:
    """Re-scan centred on the fitted minimum and re-fit (one deterministic pass)."""
    a_refined = fit.v0_a3 ** (1.0 / 3.0)
    _, volumes, energies = scan_at(calculator, formula, structure_type, a_refined, span, n)
    idx = int(np.argmin(energies))
    if not 0 < idx < len(energies) - 1:
        raise ConvergenceError(
            f"refinement scan for {formula} ({structure_type}) centred at the fitted "
            f"minimum a={a_refined:.4f} A does not bracket it; energy surface inconsistent"
        )
    return fit_birch_murnaghan(volumes, energies)


def relax_lattice(
    calculator: Calculator, formula: str, structure_type: str, a_start: float,
    span: float, n: int, max_recenter: int,
) -> tuple[BirchMurnaghanFit, int, dict[str, int]]:
    """EOS-relax a cubic cell; returns ``(fit, n_atoms_cell, per-cell symbol counts)``.

    Recentres the volume scan until the minimum is bracketed, fits, then
    refines once around the fitted minimum.
    """
    a = a_start
    for _ in range(max_recenter + 1):
        atoms, volumes, energies = scan_at(calculator, formula, structure_type, a, span, n)
        idx = int(np.argmin(energies))
        if 0 < idx < len(energies) - 1:
            fit = fit_birch_murnaghan(volumes, energies)
            refined = _refined_fit(calculator, formula, structure_type, fit, span, n)
            counts = dict(Counter(atoms.get_chemical_symbols()))
            return refined, len(atoms), counts
        try:
            a = validate_lattice_constant(float(volumes[idx]) ** (1.0 / 3.0))
        except InputValidationError as exc:
            raise ConvergenceError(
                f"E-V recentring for {formula} ({structure_type}) walked out of the "
                f"physical lattice-constant range: {exc}"
            ) from exc
    raise ConvergenceError(
        f"E-V scan for {formula} ({structure_type}) failed to bracket a minimum "
        f"after {max_recenter} recenterings from a={a_start:.4f} A"
    )


def isolated_atom_energy(calculator: Calculator, symbol: str) -> float:
    """Same-calculator isolated-atom energy (eV) in a large periodic box."""
    box = _ISOLATED_ATOM_BOX_A
    atom = Atoms(
        symbol,
        positions=[[box / 2.0, box / 2.0, box / 2.0]],
        cell=np.eye(3) * box,
        pbc=True,
    )
    return single_point_energy(atom, calculator)


__all__ = [
    "DEFAULT_MAX_RECENTER",
    "isolated_atom_energy",
    "relax_lattice",
    "scan_at",
    "validate_max_recenter",
]
