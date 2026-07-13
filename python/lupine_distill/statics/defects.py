"""Charge-balanced compound defects (Tier-1 statics).

For compound crystals the elemental vacancy formula
``E_vac = E_defect - (N-1)/N * E_bulk`` is not chemically meaningful: removing
one atom changes the stoichiometry. Two observables that stay well-defined:

* **Schottky pair** (1:1 binaries — rocksalt, B2): remove one full formula
  unit (one atom of each species, maximally separated under PBC) and relax at
  fixed cell::

      E_schottky = E_defect - (N - 2)/N * E_bulk

  Stoichiometry is preserved, so no chemical potentials enter; for ionic
  crystals this is the charge-balanced (neutral) defect the environment-field
  binder needs for the rocksalt anchor layout.

* **Referenced vacancy** (any supported compound, e.g. the Sn vacancy in a
  CsSnI3 perovskite): remove one atom of a designated species and reference
  its chemical potential to the same-calculator relaxed elemental bulk::

      E_vac(X) = E_defect + mu_X - E_bulk

  ``mu_X`` uses the elemental ground state (ASE reference symmetry, or an
  explicit ``reference_structure`` override) relaxed by the same recentring
  EOS scan as :func:`lupine_distill.statics.calculations.compute_lattice`.
  This is the metal-rich-limit neutral vacancy; alignment/charging
  corrections are deliberately out of scope for Tier-1 statics.
"""

from __future__ import annotations

import time
from typing import Final

import numpy as np
from ase.calculators.calculator import Calculator

from lupine_distill.statics.calculations import (
    DEFAULT_FMAX,
    DEFAULT_MAX_STEPS,
    DEFAULT_N_POINTS,
    DEFAULT_OPTIMIZER,
    DEFAULT_SUPERCELL,
    DEFAULT_VOLUME_SPAN,
    _resolve_references,
    _validate_supercell,
)
from lupine_distill.statics.defect_results import (
    ReferencedVacancyFormationResult,
    SchottkyFormationResult,
)
from lupine_distill.statics.eos import validate_scan_parameters
from lupine_distill.statics.errors import InputValidationError
from lupine_distill.statics.ev_relax import (
    DEFAULT_MAX_RECENTER,
    relax_lattice,
    validate_max_recenter,
)
from lupine_distill.statics.relax import (
    relax_positions,
    single_point_energy,
    validate_relax_parameters,
)
from lupine_distill.statics.structures import (
    build_structure,
    estimate_lattice_constant,
    normalize_structure_type,
    parse_formula,
    validate_lattice_constant,
)

_SCHOTTKY_TYPES: Final[frozenset[str]] = frozenset({"rocksalt", "b2"})


def compute_schottky_formation(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    supercell: tuple[int, int, int] = DEFAULT_SUPERCELL,
    fmax: float = DEFAULT_FMAX,
    optimizer: str = DEFAULT_OPTIMIZER,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> SchottkyFormationResult:
    """Charge-balanced Schottky-pair formation energy for a 1:1 binary.

    Removes the first atom of the first formula species and the atom of the
    second species farthest from it (minimum-image), then relaxes positions
    at fixed cell.
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    if st not in _SCHOTTKY_TYPES:
        raise InputValidationError(
            f"schottky formation supports 1:1 binaries only "
            f"({sorted(_SCHOTTKY_TYPES)}), got structure_type {st!r}"
        )
    a0 = validate_lattice_constant(a0_angstrom)
    cell_repeat = _validate_supercell(supercell)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    perfect = build_structure(formula, st, a0).repeat(cell_repeat)
    n_atoms = len(perfect)
    symbols = perfect.get_chemical_symbols()
    species_a, species_b = list(parse_formula(formula))
    idx_a = symbols.index(species_a)
    b_indices = [i for i, s in enumerate(symbols) if s == species_b]
    b_distances = perfect.get_distances(idx_a, b_indices, mic=True)
    idx_b = b_indices[int(np.argmax(b_distances))]
    pair_separation = float(np.max(b_distances))
    e_bulk = single_point_energy(perfect, calculator)
    defect = perfect.copy()
    for idx in sorted((idx_a, idx_b), reverse=True):
        del defect[idx]
    _, e_defect, n_steps = relax_positions(
        defect, calculator, fmax=fmax_value, optimizer=optimizer_name, max_steps=steps_budget
    )
    pair_energy = e_defect - (n_atoms - 2) / n_atoms * e_bulk
    return SchottkyFormationResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=a0,
        supercell=cell_repeat,
        removed_indices=(idx_a, idx_b),
        removed_species=(species_a, species_b),
        pair_separation_angstrom=pair_separation,
        n_atoms_perfect=n_atoms,
        e_bulk_ev=e_bulk,
        e_defect_ev=e_defect,
        schottky_pair_ev=pair_energy,
        schottky_per_vacancy_ev=pair_energy / 2.0,
        n_relax_steps=n_steps,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


def compute_referenced_vacancy_formation(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    vacancy_species: str,
    supercell: tuple[int, int, int] = DEFAULT_SUPERCELL,
    reference_structure: str | None = None,
    fmax: float = DEFAULT_FMAX,
    optimizer: str = DEFAULT_OPTIMIZER,
    max_steps: int = DEFAULT_MAX_STEPS,
    volume_span: float = DEFAULT_VOLUME_SPAN,
    n_points: int = DEFAULT_N_POINTS,
    max_recenter: int = DEFAULT_MAX_RECENTER,
) -> ReferencedVacancyFormationResult:
    """Neutral single-species vacancy in a compound vs the elemental bulk.

    ``E_vac = E_defect + mu - E_bulk`` with ``mu`` the per-atom energy of the
    species' relaxed elemental ground state under the same calculator.
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    counts = parse_formula(formula)
    if len(counts) < 2:
        raise InputValidationError(
            f"referenced vacancy needs a compound (>= 2 elements), got {formula!r}; "
            f"use compute_vacancy_formation for elements"
        )
    if not isinstance(vacancy_species, str) or vacancy_species not in counts:
        raise InputValidationError(
            f"vacancy_species must be one of {sorted(counts)}, got {vacancy_species!r}"
        )
    a0 = validate_lattice_constant(a0_angstrom)
    cell_repeat = _validate_supercell(supercell)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    span, n = validate_scan_parameters(volume_span, n_points)
    recenter_budget = validate_max_recenter(max_recenter)
    override = (
        {vacancy_species: reference_structure} if reference_structure is not None else None
    )
    ((_, ref_st),) = _resolve_references({vacancy_species: 1}, override)
    elem_fit, elem_atoms, _ = relax_lattice(
        calculator,
        vacancy_species,
        ref_st,
        estimate_lattice_constant(vacancy_species, ref_st),
        span,
        n,
        recenter_budget,
    )
    mu = elem_fit.e0_ev / elem_atoms
    perfect = build_structure(formula, st, a0).repeat(cell_repeat)
    n_atoms = len(perfect)
    symbols = perfect.get_chemical_symbols()
    idx = symbols.index(vacancy_species)
    e_bulk = single_point_energy(perfect, calculator)
    defect = perfect.copy()
    del defect[idx]
    _, e_defect, n_steps = relax_positions(
        defect, calculator, fmax=fmax_value, optimizer=optimizer_name, max_steps=steps_budget
    )
    return ReferencedVacancyFormationResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=a0,
        supercell=cell_repeat,
        vacancy_index=idx,
        vacancy_species=vacancy_species,
        reference_structure=ref_st,
        mu_ev_per_atom=mu,
        n_atoms_perfect=n_atoms,
        e_bulk_ev=e_bulk,
        e_defect_ev=e_defect,
        vacancy_formation_ev=e_defect + mu - e_bulk,
        n_relax_steps=n_steps,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        volume_span=span,
        n_points=n,
        max_recenter=recenter_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


__all__ = [
    "ReferencedVacancyFormationResult",
    "SchottkyFormationResult",
    "compute_referenced_vacancy_formation",
    "compute_schottky_formation",
]
