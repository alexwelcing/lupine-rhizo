"""Surface energies and the intrinsic stacking-fault energy (Tier-1 statics).

Surface energies use relaxed slabs against the bulk energy at the same
lattice constant: ``gamma = (E_slab - N * e_bulk) / (2 A)``. The stacking
fault uses the displaced-slab method: the top half of an fcc(111) slab is
shifted by a Shockley-partial in-plane vector and only out-of-plane motion is
relaxed (``fixed_inplane``), so the fault cannot slip back. A cheap hcp-proxy
value (axial approximation, ``2 (E_hcp - E_fcc) / A_atom``) is reported as a
cross-check field only.
"""

from __future__ import annotations

import math
import time
from typing import Callable, Final, Mapping

import numpy as np
from ase import Atoms
from ase.build import bcc100, bcc110, bulk, fcc100, fcc110, fcc111
from ase.calculators.calculator import Calculator

from lupine_distill.statics.errors import InputValidationError
from lupine_distill.statics.relax import (
    relax_positions,
    single_point_energy,
    validate_relax_parameters,
)
from lupine_distill.statics.structures import (
    build_structure,
    normalize_structure_type,
    parse_formula,
    validate_lattice_constant,
)
from lupine_distill.statics.surface_results import (
    StackingFaultResult,
    SurfaceEnergyResult,
)
from lupine_distill.statics.units import EV_PER_A2_TO_J_PER_M2, J_PER_M2_TO_MJ_PER_M2

SUPPORTED_SURFACES: Final[dict[str, tuple[str, ...]]] = {
    "fcc": ("100", "110", "111"),
    "bcc": ("100", "110"),
}

_SLAB_BUILDERS: Final[Mapping[tuple[str, str], Callable[..., Atoms]]] = {
    ("fcc", "100"): fcc100,
    ("fcc", "110"): fcc110,
    ("fcc", "111"): fcc111,
    ("bcc", "100"): bcc100,
    ("bcc", "110"): bcc110,
}

DEFAULT_SURFACE_LAYERS: Final[int] = 8
DEFAULT_SFE_LAYERS: Final[int] = 12
DEFAULT_VACUUM_A: Final[float] = 12.0
DEFAULT_SURFACE_FMAX: Final[float] = 0.01
DEFAULT_SURFACE_MAX_STEPS: Final[int] = 500
DEFAULT_SFE_MAX_STEPS: Final[int] = 1000
DEFAULT_SURFACE_OPTIMIZER: Final[str] = "FIRE"

_MIN_SURFACE_LAYERS: Final[int] = 4
_MIN_SFE_LAYERS: Final[int] = 6
_MIN_VACUUM_A: Final[float] = 6.0

SFE_METHOD: Final[str] = "displaced_slab_fixed_inplane"


def _validate_element(formula: str, context: str) -> str:
    counts = parse_formula(formula)
    if len(counts) != 1 or next(iter(counts.values())) != 1:
        raise InputValidationError(
            f"{context} supports single elements only (e.g. 'Ni'), got {formula!r}"
        )
    return next(iter(counts))


def _validate_layers(layers: int, minimum: int) -> int:
    try:
        value = int(layers)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"layers must be an integer, got {layers!r}") from exc
    if value < minimum:
        raise InputValidationError(f"layers must be >= {minimum}, got {value}")
    return value


def _validate_vacuum(vacuum: float) -> float:
    try:
        value = float(vacuum)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"vacuum must be a number, got {vacuum!r}") from exc
    if not math.isfinite(value) or value < _MIN_VACUUM_A:
        raise InputValidationError(f"vacuum must be >= {_MIN_VACUUM_A} A per side, got {value}")
    return value


def _in_plane_area(atoms: Atoms) -> float:
    cell = atoms.cell.array
    return float(np.linalg.norm(np.cross(cell[0], cell[1])))


def _build_slab(
    symbol: str, structure_type: str, miller: str, a0: float, layers: int, vacuum: float
) -> Atoms:
    slab = _SLAB_BUILDERS[(structure_type, miller)](
        symbol, size=(1, 1, layers), a=a0, vacuum=vacuum
    )
    slab.pbc = (True, True, True)
    return slab


def compute_surface_energy(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    miller: str,
    a0_angstrom: float,
    *,
    layers: int = DEFAULT_SURFACE_LAYERS,
    vacuum: float = DEFAULT_VACUUM_A,
    fmax: float = DEFAULT_SURFACE_FMAX,
    optimizer: str = DEFAULT_SURFACE_OPTIMIZER,
    max_steps: int = DEFAULT_SURFACE_MAX_STEPS,
) -> SurfaceEnergyResult:
    """Relaxed surface energy ``gamma = (E_slab - N e_bulk) / (2 A)`` in J/m^2."""
    t0 = time.perf_counter()
    symbol = _validate_element(formula, "surface energy")
    st = normalize_structure_type(structure_type)
    if st not in SUPPORTED_SURFACES:
        raise InputValidationError(
            f"no supported surfaces for structure_type {st!r}; "
            f"supported: {sorted(SUPPORTED_SURFACES)}"
        )
    if not isinstance(miller, str) or miller not in SUPPORTED_SURFACES[st]:
        raise InputValidationError(
            f"unsupported miller {miller!r} for {st}; supported: {SUPPORTED_SURFACES[st]}"
        )
    a0 = validate_lattice_constant(a0_angstrom)
    n_layers = _validate_layers(layers, _MIN_SURFACE_LAYERS)
    vacuum_a = _validate_vacuum(vacuum)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    e_bulk_per_atom = _bulk_energy_per_atom(calculator, symbol, st, a0)
    slab = _build_slab(symbol, st, miller, a0, n_layers, vacuum_a)
    area = _in_plane_area(slab)
    _, e_slab, n_steps = relax_positions(
        slab, calculator, fmax=fmax_value, optimizer=optimizer_name, max_steps=steps_budget
    )
    gamma_ev_a2 = (e_slab - len(slab) * e_bulk_per_atom) / (2.0 * area)
    return SurfaceEnergyResult(
        formula=formula,
        structure_type=st,
        miller=miller,
        a0_angstrom=a0,
        layers=n_layers,
        vacuum_angstrom=vacuum_a,
        n_atoms_slab=len(slab),
        area_a2=area,
        e_slab_ev=e_slab,
        e_bulk_ev_per_atom=e_bulk_per_atom,
        gamma_j_per_m2=gamma_ev_a2 * EV_PER_A2_TO_J_PER_M2,
        n_relax_steps=n_steps,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


def compute_surface_energies(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    layers: int = DEFAULT_SURFACE_LAYERS,
    vacuum: float = DEFAULT_VACUUM_A,
    fmax: float = DEFAULT_SURFACE_FMAX,
    optimizer: str = DEFAULT_SURFACE_OPTIMIZER,
    max_steps: int = DEFAULT_SURFACE_MAX_STEPS,
) -> tuple[SurfaceEnergyResult, ...]:
    """All supported surface energies for the structure type, in canonical order."""
    st = normalize_structure_type(structure_type)
    if st not in SUPPORTED_SURFACES:
        raise InputValidationError(
            f"no supported surfaces for structure_type {st!r}; "
            f"supported: {sorted(SUPPORTED_SURFACES)}"
        )
    return tuple(
        compute_surface_energy(
            calculator,
            formula,
            st,
            miller,
            a0_angstrom,
            layers=layers,
            vacuum=vacuum,
            fmax=fmax,
            optimizer=optimizer,
            max_steps=max_steps,
        )
        for miller in SUPPORTED_SURFACES[st]
    )


def _bulk_energy_per_atom(
    calculator: Calculator, symbol: str, structure_type: str, a0: float
) -> float:
    reference = build_structure(symbol, structure_type, a0)
    return single_point_energy(reference, calculator) / len(reference)


def _hcp_proxy_mj_per_m2(
    calculator: Calculator, symbol: str, a0: float, e_fcc_per_atom: float
) -> float:
    """Axial-approximation cross-check: ``2 (E_hcp - E_fcc) / A_atom``."""
    d_nn = a0 / math.sqrt(2.0)
    hcp = bulk(symbol, "hcp", a=d_nn, c=d_nn * math.sqrt(8.0 / 3.0))
    e_hcp_per_atom = single_point_energy(hcp, calculator) / len(hcp)
    area_per_atom = math.sqrt(3.0) / 4.0 * a0 * a0
    gamma_ev_a2 = 2.0 * (e_hcp_per_atom - e_fcc_per_atom) / area_per_atom
    return gamma_ev_a2 * EV_PER_A2_TO_J_PER_M2 * J_PER_M2_TO_MJ_PER_M2


def _displaced_slab_energy(
    calculator: Calculator,
    slab: Atoms,
    sign: int,
    fmax: float,
    optimizer: str,
    max_steps: int,
) -> tuple[float, int]:
    """Energy of the slab with its top half shifted by ``sign * (a1 + a2) / 3``."""
    faulted = slab.copy()
    cell = faulted.cell.array
    shift = sign * (cell[0] + cell[1]) / 3.0
    positions = faulted.get_positions()
    z_mid = float(np.median(positions[:, 2]))
    positions[positions[:, 2] > z_mid] += shift
    faulted.set_positions(positions)
    _, energy, n_steps = relax_positions(
        faulted, calculator, fmax=fmax, optimizer=optimizer, max_steps=max_steps, z_only=True
    )
    return energy, n_steps


def compute_stacking_fault_energy(
    calculator: Calculator,
    formula: str,
    a0_angstrom: float,
    *,
    layers: int = DEFAULT_SFE_LAYERS,
    vacuum: float = DEFAULT_VACUUM_A,
    fmax: float = DEFAULT_SURFACE_FMAX,
    optimizer: str = DEFAULT_SURFACE_OPTIMIZER,
    max_steps: int = DEFAULT_SFE_MAX_STEPS,
) -> StackingFaultResult:
    """Intrinsic stacking-fault energy of an fcc element (mJ/m^2).

    Primary method: displace the top half of an fcc(111) slab by a Shockley
    partial in-plane vector and relax out-of-plane motion only. Both partial
    directions are evaluated and the lower-energy (physical intrinsic-fault)
    branch is kept — the other direction is the atop stacking. The hcp-proxy
    estimate is attached as a cross-check field only.
    """
    t0 = time.perf_counter()
    symbol = _validate_element(formula, "stacking fault energy")
    a0 = validate_lattice_constant(a0_angstrom)
    n_layers = _validate_layers(layers, _MIN_SFE_LAYERS)
    vacuum_a = _validate_vacuum(vacuum)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    slab = _build_slab(symbol, "fcc", "111", a0, n_layers, vacuum_a)
    area = _in_plane_area(slab)
    _, e_perfect, steps_perfect = relax_positions(
        slab, calculator, fmax=fmax_value, optimizer=optimizer_name,
        max_steps=steps_budget, z_only=True,
    )
    e_plus, steps_plus = _displaced_slab_energy(
        calculator, slab, +1, fmax_value, optimizer_name, steps_budget
    )
    e_minus, steps_minus = _displaced_slab_energy(
        calculator, slab, -1, fmax_value, optimizer_name, steps_budget
    )
    displacement_sign = +1 if e_plus <= e_minus else -1
    e_fault = min(e_plus, e_minus)
    sfe = (e_fault - e_perfect) / area * EV_PER_A2_TO_J_PER_M2 * J_PER_M2_TO_MJ_PER_M2
    e_fcc_per_atom = _bulk_energy_per_atom(calculator, symbol, "fcc", a0)
    return StackingFaultResult(
        formula=formula,
        a0_angstrom=a0,
        layers=n_layers,
        vacuum_angstrom=vacuum_a,
        area_a2=area,
        sfe_mj_per_m2=sfe,
        hcp_proxy_mj_per_m2=_hcp_proxy_mj_per_m2(calculator, symbol, a0, e_fcc_per_atom),
        method=SFE_METHOD,
        displacement_sign=displacement_sign,
        n_relax_steps=steps_perfect + steps_plus + steps_minus,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


__all__ = [
    "DEFAULT_SFE_LAYERS",
    "DEFAULT_SURFACE_LAYERS",
    "DEFAULT_VACUUM_A",
    "SFE_METHOD",
    "SUPPORTED_SURFACES",
    "StackingFaultResult",
    "SurfaceEnergyResult",
    "compute_stacking_fault_energy",
    "compute_surface_energies",
    "compute_surface_energy",
]
