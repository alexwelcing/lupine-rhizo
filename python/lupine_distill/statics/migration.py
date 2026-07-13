"""Vacancy-hop migration barriers via CI-NEB (kinetics lane, Tier-1 statics).

Two deterministic endpoint builders plus one CI-NEB driver:

* :func:`build_cation_vacancy_hop` — rocksalt 1:1 binary: remove the FIRST
  cation by index (the first element in formula order is the cation), then
  move its nearest cation neighbour under minimum image (the <110>
  same-sublattice neighbour at ``a0/sqrt(2)``) into the vacant site.
* :func:`build_fcc_vacancy_hop` — the same machinery on an elemental fcc
  metal (nearest-neighbour <110> hop, also ``a0/sqrt(2)``); this is the
  EMT-testable path (EMT has no halides).
* :func:`compute_migration_barrier` — relax BOTH endpoints (positions only,
  fixed cell), IDPP- (fallback linear-) interpolate a band of ``n_images``
  interior images, converge a climbing-image NEB, and report forward /
  backward barriers from the relaxed endpoint energies.

ASE NEB pitfalls handled here so callers do not have to:

* One shared calculator instance (the normal MLIP situation) requires
  ``allow_shared_calculator=True`` — NEB raises otherwise.
* ``interpolate(method="idpp")`` failures fall back to a full linear
  re-interpolation (linear overwrites every interior image, so a partial
  IDPP state cannot leak through); the method actually used is recorded.
* Climbing from an unrelaxed straight-line band is unstable, so the climb
  is two-stage: converge the plain band to ``fmax * PRE_CLIMB_FMAX_FACTOR``
  first, then enable ``neb.climb`` and converge to ``fmax``. ASE optimizer
  ``run(steps=...)`` budgets are per-call (``max_steps = nsteps + steps``),
  so the second stage is given exactly the remaining budget.
* Interpolation uses ``mic=True`` AND the final endpoint is built with the
  minimum-image target position, so the band never wraps across the cell.
* ASE >= 3.29 changed the default NEB tangent method from ``aseneb`` to
  ``improvedtangent`` (with a UserWarning when unset); the method is pinned
  explicitly to :data:`NEB_METHOD` and recorded in the result provenance.
"""

from __future__ import annotations

import math
import time
from typing import Final

import numpy as np
from ase import Atoms
from ase.calculators.calculator import Calculator
from ase.geometry import find_mic
from ase.mep import NEB
from ase.optimize import BFGS, FIRE

from lupine_distill.statics.calculations import _validate_supercell
from lupine_distill.statics.errors import (
    CalculationError,
    ConvergenceError,
    InputValidationError,
)
from lupine_distill.statics.migration_results import MigrationBarrierResult
from lupine_distill.statics.relax import relax_positions, single_point_energy
from lupine_distill.statics.structures import (
    build_structure,
    normalize_structure_type,
    parse_formula,
    validate_lattice_constant,
)

DEFAULT_N_IMAGES: Final[int] = 5
DEFAULT_NEB_FMAX: Final[float] = 0.05
DEFAULT_NEB_MAX_STEPS: Final[int] = 300
DEFAULT_HOP_SUPERCELL: Final[int] = 2
SUPPORTED_NEB_OPTIMIZERS: Final[tuple[str, ...]] = ("FIRE", "BFGS")
SUPPORTED_INTERPOLATIONS: Final[tuple[str, ...]] = ("idpp", "linear")

#: Stage-1 (no climb) convergence target as a multiple of the final fmax.
PRE_CLIMB_FMAX_FACTOR: Final[float] = 3.0

#: Pinned NEB tangent method (Henkelman & Jonsson improved tangent, the
#: ASE >= 3.29 recommended default; pinning silences the transition warning
#: and keeps results stable across ASE versions).
NEB_METHOD: Final[str] = "improvedtangent"

_NEB_OPTIMIZER_CLASSES: Final[dict[str, type]] = {"FIRE": FIRE, "BFGS": BFGS}

#: Structure types with a supported cation-vacancy hop (fcc cation sublattice).
_HOP_STRUCTURE_TYPES: Final[frozenset[str]] = frozenset({"rocksalt"})

#: Relative tolerance for grouping float-equal nearest-neighbour distances.
_DISTANCE_TIE_RTOL: Final[float] = 1.0e-9

#: Relative tolerance on the a0/sqrt(2) nearest-neighbour hop invariant.
_HOP_GEOMETRY_RTOL: Final[float] = 1.0e-6

#: Endpoints closer than this (max MIC displacement, A) are "the same state".
_MIN_ENDPOINT_SEPARATION_A: Final[float] = 1.0e-6

#: The climbing image needs interior neighbours on both sides to be meaningful.
_MIN_CLIMB_IMAGES: Final[int] = 3


class _CountingNEB(NEB):
    """NEB that counts band force evaluations (for cheap n_force_calls)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.n_band_force_evaluations = 0

    def get_forces(self) -> np.ndarray:
        self.n_band_force_evaluations += 1
        return super().get_forces()


# --------------------------------------------------------------------------
# validation helpers
# --------------------------------------------------------------------------


def _normalize_hop_supercell(supercell: int | tuple[int, int, int]) -> tuple[int, int, int]:
    """Accept ``n`` or ``(nx, ny, nz)``; every repeat must be >= 2.

    With any repeat of 1 the hopping atom is a minimum-image neighbour of the
    vacancy's own periodic image and the two endpoints stop being distinct
    local minima, so a 1-repeat is rejected up front.
    """
    if isinstance(supercell, bool):
        raise InputValidationError(f"supercell must be an int or 3-tuple, got {supercell!r}")
    parts = (
        (supercell, supercell, supercell) if isinstance(supercell, int) else supercell
    )
    validated = _validate_supercell(parts)
    if min(validated) < 2:
        raise InputValidationError(
            f"vacancy-hop supercell repeats must all be >= 2 (got {validated}); "
            f"a 1-repeat puts the hopper adjacent to the vacancy's periodic image"
        )
    return validated


def _validate_n_images(n_images: int, climb: bool) -> int:
    try:
        n = int(n_images)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"n_images must be an integer, got {n_images!r}") from exc
    if isinstance(n_images, bool) or n < 1:
        raise InputValidationError(f"n_images must be an integer >= 1, got {n_images!r}")
    if climb and n < _MIN_CLIMB_IMAGES:
        raise InputValidationError(
            f"climbing-image NEB needs n_images >= {_MIN_CLIMB_IMAGES} interior "
            f"images, got {n}; use climb=False for shorter bands"
        )
    return n


def _validate_neb_parameters(
    fmax: float, optimizer: str, max_steps: int, interpolation: str
) -> tuple[float, str, int, str]:
    try:
        fmax_value = float(fmax)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"fmax must be a number, got {fmax!r}") from exc
    if not math.isfinite(fmax_value) or fmax_value <= 0.0:
        raise InputValidationError(f"fmax must be finite and > 0 eV/A, got {fmax_value}")
    if (
        not isinstance(optimizer, str)
        or optimizer.strip().upper() not in SUPPORTED_NEB_OPTIMIZERS
    ):
        raise InputValidationError(
            f"optimizer must be one of {SUPPORTED_NEB_OPTIMIZERS}, got {optimizer!r}"
        )
    try:
        steps = int(max_steps)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"max_steps must be an integer, got {max_steps!r}") from exc
    if steps < 1:
        raise InputValidationError(f"max_steps must be >= 1, got {steps}")
    if (
        not isinstance(interpolation, str)
        or interpolation.strip().lower() not in SUPPORTED_INTERPOLATIONS
    ):
        raise InputValidationError(
            f"interpolation must be one of {SUPPORTED_INTERPOLATIONS}, got {interpolation!r}"
        )
    return fmax_value, optimizer.strip().upper(), steps, interpolation.strip().lower()


def _validate_endpoints(initial: Atoms, final: Atoms) -> None:
    for name, atoms in (("initial", initial), ("final", final)):
        if not isinstance(atoms, Atoms) or len(atoms) == 0:
            raise InputValidationError(f"{name} must be a non-empty ase.Atoms object")
        if not all(atoms.get_pbc()):
            raise InputValidationError(f"{name} must be fully periodic (pbc=True)")
    if len(initial) != len(final):
        raise InputValidationError(
            f"endpoints must have the same atom count, got {len(initial)} vs {len(final)}"
        )
    if initial.get_chemical_symbols() != final.get_chemical_symbols():
        raise InputValidationError(
            "endpoints must have identical element sequences (same atoms, same order)"
        )
    if not np.allclose(initial.get_cell()[:], final.get_cell()[:], atol=1.0e-10):
        raise InputValidationError("endpoints must share the same fixed cell")
    if _max_mic_displacement(initial, final) < _MIN_ENDPOINT_SEPARATION_A:
        raise InputValidationError(
            "endpoints are the same configuration (max minimum-image displacement "
            f"< {_MIN_ENDPOINT_SEPARATION_A} A); no migration path to compute"
        )


def _max_mic_displacement(a: Atoms, b: Atoms) -> float:
    """Largest per-atom minimum-image displacement between two same-cell states."""
    delta = b.get_positions() - a.get_positions()
    _, distances = find_mic(delta, a.get_cell(), pbc=True)
    return float(np.max(distances))


# --------------------------------------------------------------------------
# endpoint builders
# --------------------------------------------------------------------------


def _vacancy_hop_from_perfect(
    perfect: Atoms, hop_species: str, a0: float
) -> tuple[Atoms, Atoms, float]:
    """(initial, final, hop_distance) from a perfect cell and hopping species.

    Deterministic site selection: the vacancy is the FIRST atom of
    ``hop_species`` by index; the hopper is its nearest same-species
    neighbour under minimum image, ties broken by lowest index. The final
    state places the hopper on the vacancy site's minimum image so the band
    interpolates along the direct hop vector, never across the cell.
    """
    symbols = perfect.get_chemical_symbols()
    vacancy_index = symbols.index(hop_species)
    neighbour_indices = [
        i for i, s in enumerate(symbols) if s == hop_species and i != vacancy_index
    ]
    if not neighbour_indices:
        raise InputValidationError(
            f"no second {hop_species!r} atom to hop into the vacancy; "
            f"cell has {symbols.count(hop_species)} {hop_species} atom(s)"
        )
    distances = perfect.get_distances(vacancy_index, neighbour_indices, mic=True)
    d_min = float(np.min(distances))
    tied = [
        idx
        for idx, d in zip(neighbour_indices, distances)
        if d <= d_min * (1.0 + _DISTANCE_TIE_RTOL)
    ]
    hop_index = min(tied)

    expected = a0 / math.sqrt(2.0)
    if abs(d_min - expected) > _HOP_GEOMETRY_RTOL * a0:
        raise InputValidationError(
            f"nearest same-sublattice neighbour at {d_min:.6f} A does not match "
            f"the fcc-sublattice <110> hop a0/sqrt(2) = {expected:.6f} A; "
            f"unexpected geometry for this builder"
        )

    vac_position = perfect.get_positions()[vacancy_index]
    hop_position = perfect.get_positions()[hop_index]
    mic_vector, mic_distance = find_mic(
        (vac_position - hop_position)[np.newaxis, :], perfect.get_cell(), pbc=True
    )
    hop_distance = float(mic_distance[0])

    initial = perfect.copy()
    del initial[vacancy_index]
    hop_in_defect = hop_index - 1 if hop_index > vacancy_index else hop_index
    final = initial.copy()
    positions = final.get_positions()
    positions[hop_in_defect] = hop_position + mic_vector[0]
    final.set_positions(positions)
    return initial, final, hop_distance


def build_cation_vacancy_hop(
    formula: str,
    structure_type: str = "rocksalt",
    *,
    lattice_constant: float,
    supercell: int | tuple[int, int, int] = DEFAULT_HOP_SUPERCELL,
) -> tuple[Atoms, Atoms, float]:
    """Endpoints of the nearest-neighbour <110> cation-vacancy hop in rocksalt.

    The cation is the FIRST element in formula order (``'LiF'`` hops Li).
    Returns ``(initial, final, hop_distance_angstrom)`` where ``initial`` has
    one cation vacancy and ``final`` is the same cell with the vacancy's
    nearest cation neighbour (minimum image, ``a0/sqrt(2)`` away) moved onto
    the vacant site. Both endpoints are UNRELAXED; relaxation belongs to
    :func:`compute_migration_barrier`.
    """
    st = normalize_structure_type(structure_type)
    if st not in _HOP_STRUCTURE_TYPES:
        raise InputValidationError(
            f"cation vacancy hop supports {sorted(_HOP_STRUCTURE_TYPES)} only, "
            f"got structure_type {st!r}"
        )
    counts = parse_formula(formula)
    if len(counts) != 2 or sorted(counts.values()) != [1, 1]:
        raise InputValidationError(
            f"cation vacancy hop needs a 1:1 rocksalt binary (e.g. 'LiF'), "
            f"got composition {dict(counts)}"
        )
    a0 = validate_lattice_constant(lattice_constant)
    repeat = _normalize_hop_supercell(supercell)
    cation = next(iter(counts))
    perfect = build_structure(formula, st, a0).repeat(repeat)
    return _vacancy_hop_from_perfect(perfect, cation, a0)


def build_fcc_vacancy_hop(
    symbol: str,
    *,
    lattice_constant: float,
    supercell: int | tuple[int, int, int] = DEFAULT_HOP_SUPERCELL,
) -> tuple[Atoms, Atoms, float]:
    """Endpoints of the nearest-neighbour vacancy hop in an elemental fcc metal.

    Same machinery and site selection as :func:`build_cation_vacancy_hop`
    (the rocksalt cation sublattice IS fcc), on an EMT-testable element.
    Returns unrelaxed ``(initial, final, hop_distance_angstrom)``.
    """
    counts = parse_formula(symbol)
    if len(counts) != 1 or next(iter(counts.values())) != 1:
        raise InputValidationError(
            f"fcc vacancy hop expects a single element symbol (e.g. 'Al'), "
            f"got composition {dict(counts)}"
        )
    a0 = validate_lattice_constant(lattice_constant)
    repeat = _normalize_hop_supercell(supercell)
    element = next(iter(counts))
    perfect = build_structure(element, "fcc", a0).repeat(repeat)
    return _vacancy_hop_from_perfect(perfect, element, a0)


# --------------------------------------------------------------------------
# CI-NEB barrier
# --------------------------------------------------------------------------


def _interpolate_band(neb: NEB, interpolation: str) -> str:
    """IDPP-interpolate the band, falling back to linear; returns the method used.

    A failed IDPP may leave interior images partially displaced, but the
    linear fallback overwrites every interior position from the endpoints,
    so the band is always in a well-defined state afterwards.
    """
    if interpolation == "idpp":
        try:
            neb.interpolate(method="idpp", mic=True)
        except Exception:  # noqa: BLE001 - any IDPP failure falls back to linear
            neb.interpolate(method="linear", mic=True)
            return "linear"
        return "idpp"
    neb.interpolate(method="linear", mic=True)
    return "linear"


def compute_migration_barrier(
    calculator: Calculator,
    initial: Atoms,
    final: Atoms,
    *,
    n_images: int = DEFAULT_N_IMAGES,
    fmax: float = DEFAULT_NEB_FMAX,
    max_steps: int = DEFAULT_NEB_MAX_STEPS,
    climb: bool = True,
    optimizer: str = "FIRE",
    interpolation: str = "idpp",
) -> MigrationBarrierResult:
    """Forward/backward migration barrier from a CI-NEB band (fixed cell).

    Both endpoints are relaxed first (positions only, FIRE, same ``fmax``),
    then ``n_images`` interior images are interpolated (IDPP with linear
    fallback) and the band is converged with a two-stage climbing-image NEB
    (plain band to ``fmax * PRE_CLIMB_FMAX_FACTOR``, then climb to ``fmax``)
    under one shared ``max_steps`` budget.

    ``forward_barrier_ev = E_saddle - E_initial_relaxed`` and
    ``backward_barrier_ev = E_saddle - E_final_relaxed``; for a symmetric
    vacancy hop the two should match and the asymmetry is recorded.
    Raises :class:`ConvergenceError` when a relaxation or NEB stage exhausts
    its budget; never mutates the caller's ``Atoms`` objects.
    """
    t0 = time.perf_counter()
    _validate_endpoints(initial, final)
    n_interior = _validate_n_images(n_images, climb)
    fmax_value, optimizer_name, steps_budget, interpolation_name = _validate_neb_parameters(
        fmax, optimizer, max_steps, interpolation
    )

    relaxed_initial, e_initial, n_steps_initial = relax_positions(
        initial, calculator, fmax=fmax_value, optimizer="FIRE", max_steps=steps_budget
    )
    relaxed_final, e_final, n_steps_final = relax_positions(
        final, calculator, fmax=fmax_value, optimizer="FIRE", max_steps=steps_budget
    )
    hop_distance = _max_mic_displacement(relaxed_initial, relaxed_final)
    if hop_distance < _MIN_ENDPOINT_SEPARATION_A:
        raise CalculationError(
            "endpoint relaxations collapsed to the same configuration; "
            "the two hop endpoints are not distinct minima for this calculator"
        )

    images = (
        [relaxed_initial]
        + [relaxed_initial.copy() for _ in range(n_interior)]
        + [relaxed_final]
    )
    for image in images[1:-1]:
        image.calc = calculator
    neb = _CountingNEB(
        images, climb=False, method=NEB_METHOD, allow_shared_calculator=True
    )
    interpolation_used = _interpolate_band(neb, interpolation_name)

    opt = _NEB_OPTIMIZER_CLASSES[optimizer_name](neb, logfile=None)
    n_pre_climb_steps = 0
    try:
        if climb:
            pre_fmax = fmax_value * PRE_CLIMB_FMAX_FACTOR
            converged_pre = opt.run(fmax=pre_fmax, steps=steps_budget)
            n_pre_climb_steps = int(opt.get_number_of_steps())
            if not converged_pre:
                raise ConvergenceError(
                    f"pre-climb NEB stage did not reach fmax={pre_fmax:.4g} eV/A "
                    f"within {steps_budget} steps"
                )
            remaining = steps_budget - n_pre_climb_steps
            if remaining < 1:
                raise ConvergenceError(
                    f"pre-climb NEB stage consumed the whole {steps_budget}-step "
                    f"budget; no steps left for the climbing stage"
                )
            neb.climb = True
            converged = opt.run(fmax=fmax_value, steps=remaining)
        else:
            converged = opt.run(fmax=fmax_value, steps=steps_budget)
    except ConvergenceError:
        raise
    except Exception as exc:
        raise CalculationError(
            f"{optimizer_name} NEB optimization failed on "
            f"{relaxed_initial.get_chemical_formula()}: {exc}"
        ) from exc
    n_neb_steps = int(opt.get_number_of_steps())
    if not converged:
        raise ConvergenceError(
            f"{'CI-' if climb else ''}NEB did not reach fmax={fmax_value} eV/A on "
            f"{relaxed_initial.get_chemical_formula()} within {steps_budget} steps"
        )

    interior_energies = [
        single_point_energy(image, calculator) for image in images[1:-1]
    ]
    band_energies = (e_initial, *interior_energies, e_final)
    if not all(math.isfinite(e) for e in band_energies):
        raise CalculationError("NEB band contains non-finite image energies")
    saddle_index = int(np.argmax(band_energies))
    e_saddle = float(band_energies[saddle_index])
    forward = e_saddle - e_initial
    backward = e_saddle - e_final

    return MigrationBarrierResult(
        formula=relaxed_initial.get_chemical_formula(),
        n_atoms=len(relaxed_initial),
        n_images=n_interior,
        climb=climb,
        neb_method=NEB_METHOD,
        interpolation_method=interpolation_used,
        optimizer=optimizer_name,
        fmax=fmax_value,
        max_steps=steps_budget,
        hop_distance_angstrom=hop_distance,
        e_initial_ev=e_initial,
        e_final_ev=e_final,
        e_saddle_ev=e_saddle,
        forward_barrier_ev=forward,
        backward_barrier_ev=backward,
        barrier_asymmetry_ev=abs(forward - backward),
        saddle_image_index=saddle_index,
        band_energies_ev=band_energies,
        n_relax_steps_initial=n_steps_initial,
        n_relax_steps_final=n_steps_final,
        n_neb_steps=n_neb_steps,
        n_pre_climb_steps=n_pre_climb_steps,
        n_force_calls=neb.n_band_force_evaluations * n_interior,
        wall_time_seconds=time.perf_counter() - t0,
    )


__all__ = [
    "DEFAULT_HOP_SUPERCELL",
    "DEFAULT_N_IMAGES",
    "DEFAULT_NEB_FMAX",
    "DEFAULT_NEB_MAX_STEPS",
    "MigrationBarrierResult",
    "NEB_METHOD",
    "PRE_CLIMB_FMAX_FACTOR",
    "SUPPORTED_INTERPOLATIONS",
    "SUPPORTED_NEB_OPTIMIZERS",
    "build_cation_vacancy_hop",
    "build_fcc_vacancy_hop",
    "compute_migration_barrier",
]
