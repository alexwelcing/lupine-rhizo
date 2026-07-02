"""Tier-1 statics: lattice relaxation, EOS, vacancy formation, formation enthalpy.

All functions take an already-instantiated ASE calculator (EMT in tests,
MACE/CHGNet in the y-matrix CLI), validate every input up front, work on
copies of any ``Atoms`` object, and return frozen result dataclasses whose
``canonical_inputs()`` are deterministic and JSON-serializable.
"""

from __future__ import annotations

import time
from typing import Final, Mapping

import numpy as np
from ase.calculators.calculator import Calculator
from ase.data import atomic_numbers, reference_states

from lupine_distill.statics.eos import fit_birch_murnaghan, validate_scan_parameters
from lupine_distill.statics.errors import ConvergenceError, InputValidationError
from lupine_distill.statics.ev_relax import (
    DEFAULT_MAX_RECENTER,
    isolated_atom_energy,
    relax_lattice,
    scan_at,
    validate_max_recenter,
)
from lupine_distill.statics.relax import (
    relax_positions,
    single_point_energy,
    validate_relax_parameters,
)
from lupine_distill.statics.results import (
    EosResult,
    FormationEnthalpyResult,
    LatticeResult,
    VacancyFormationResult,
)
from lupine_distill.statics.structures import (
    build_structure,
    estimate_lattice_constant,
    normalize_structure_type,
    parse_formula,
    validate_lattice_constant,
)

DEFAULT_VOLUME_SPAN: Final[float] = 0.06
DEFAULT_N_POINTS: Final[int] = 11
DEFAULT_FMAX: Final[float] = 0.01
DEFAULT_MAX_STEPS: Final[int] = 500
DEFAULT_OPTIMIZER: Final[str] = "FIRE"
DEFAULT_SUPERCELL: Final[tuple[int, int, int]] = (3, 3, 3)

_ELEMENTAL_REFERENCE_TYPES: Final[frozenset[str]] = frozenset({"fcc", "bcc", "diamond"})


# --------------------------------------------------------------------------
# public calculations
# --------------------------------------------------------------------------


def compute_lattice(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    *,
    volume_span: float = DEFAULT_VOLUME_SPAN,
    n_points: int = DEFAULT_N_POINTS,
    max_recenter: int = DEFAULT_MAX_RECENTER,
    initial_a_angstrom: float | None = None,
) -> LatticeResult:
    """Relax the lattice constant via a recentring E-V scan + BM3 fit.

    Also computes the cohesive energy per atom against same-calculator
    isolated-atom energies.
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    span, n = validate_scan_parameters(volume_span, n_points)
    recenter_budget = validate_max_recenter(max_recenter)
    if initial_a_angstrom is None:
        a_start = estimate_lattice_constant(formula, st)
    else:
        a_start = validate_lattice_constant(initial_a_angstrom)
        parse_formula(formula)
    fit, n_atoms, cell_counts = relax_lattice(
        calculator, formula, st, a_start, span, n, recenter_budget
    )
    isolated = tuple(
        (symbol, isolated_atom_energy(calculator, symbol)) for symbol in sorted(cell_counts)
    )
    e_free_atoms = sum(cell_counts[symbol] * energy for symbol, energy in isolated)
    return LatticeResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=fit.v0_a3 ** (1.0 / 3.0),
        e0_ev_per_atom=fit.e0_ev / n_atoms,
        v0_a3_per_atom=fit.v0_a3 / n_atoms,
        b0_gpa=fit.b0_gpa,
        b0_prime=fit.b0_prime,
        cohesive_energy_ev_per_atom=(e_free_atoms - fit.e0_ev) / n_atoms,
        isolated_atom_energies_ev=isolated,
        n_atoms_cell=n_atoms,
        initial_a_angstrom=a_start,
        volume_span=span,
        n_points=n,
        max_recenter=recenter_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


def compute_eos(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    volume_span: float = DEFAULT_VOLUME_SPAN,
    n_points: int = DEFAULT_N_POINTS,
) -> EosResult:
    """Single E-V scan + BM3 fit at a caller-supplied lattice constant.

    Unlike :func:`compute_lattice` this never recentres: if the scan around
    ``a0_angstrom`` does not bracket the minimum, :class:`ConvergenceError`
    is raised (the caller's lattice constant is wrong).
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    span, n = validate_scan_parameters(volume_span, n_points)
    a0 = validate_lattice_constant(a0_angstrom)
    atoms, volumes, energies = scan_at(calculator, formula, st, a0, span, n)
    idx = int(np.argmin(energies))
    if not 0 < idx < len(energies) - 1:
        raise ConvergenceError(
            f"E-V scan for {formula} ({st}) at a={a0:.4f} A has its minimum on the "
            f"scan boundary; the lattice constant does not bracket the minimum"
        )
    fit = fit_birch_murnaghan(volumes, energies)
    n_atoms = len(atoms)
    return EosResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=a0,
        volume_span=span,
        n_points=n,
        n_atoms_cell=n_atoms,
        volumes_a3=volumes,
        energies_ev=energies,
        e0_ev=fit.e0_ev,
        v0_a3=fit.v0_a3,
        v0_a3_per_atom=fit.v0_a3 / n_atoms,
        b0_gpa=fit.b0_gpa,
        b0_prime=fit.b0_prime,
        rms_residual_ev=fit.rms_residual_ev,
        wall_time_seconds=time.perf_counter() - t0,
    )


def _validate_supercell(supercell: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        parts = tuple(int(x) for x in supercell)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"supercell must be three positive integers, got {supercell!r}"
        ) from exc
    if len(parts) != 3 or any(x < 1 for x in parts):
        raise InputValidationError(f"supercell must be three integers >= 1, got {supercell!r}")
    return parts  # type: ignore[return-value]


def _validate_vacancy_index(vacancy_index: int, n_atoms: int) -> int:
    try:
        idx = int(vacancy_index)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"vacancy_index must be an integer, got {vacancy_index!r}"
        ) from exc
    if not 0 <= idx < n_atoms:
        raise InputValidationError(
            f"vacancy_index must be in [0, {n_atoms}) for this supercell, got {idx}"
        )
    return idx


def compute_vacancy_formation(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    a0_angstrom: float,
    *,
    supercell: tuple[int, int, int] = DEFAULT_SUPERCELL,
    vacancy_index: int = 0,
    fmax: float = DEFAULT_FMAX,
    optimizer: str = DEFAULT_OPTIMIZER,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> VacancyFormationResult:
    """Vacancy formation energy ``E_vac = E_defect - (N-1)/N * E_bulk``.

    Builds the conventional cell at ``a0_angstrom``, repeats it into the
    supercell, removes one atom, and relaxes positions at fixed cell.
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    a0 = validate_lattice_constant(a0_angstrom)
    fmax_value, optimizer_name, steps_budget = validate_relax_parameters(
        fmax, optimizer, max_steps
    )
    cell_repeat = _validate_supercell(supercell)
    perfect = build_structure(formula, st, a0).repeat(cell_repeat)
    n_atoms = len(perfect)
    idx = _validate_vacancy_index(vacancy_index, n_atoms)
    e_bulk = single_point_energy(perfect, calculator)
    defect = perfect.copy()
    species = str(defect[idx].symbol)
    del defect[idx]
    _, e_defect, n_steps = relax_positions(
        defect, calculator, fmax=fmax_value, optimizer=optimizer_name, max_steps=steps_budget
    )
    return VacancyFormationResult(
        formula=formula,
        structure_type=st,
        a0_angstrom=a0,
        supercell=cell_repeat,
        vacancy_index=idx,
        vacancy_species=species,
        n_atoms_perfect=n_atoms,
        e_bulk_ev=e_bulk,
        e_defect_ev=e_defect,
        vacancy_formation_ev=e_defect - (n_atoms - 1) / n_atoms * e_bulk,
        n_relax_steps=n_steps,
        fmax=fmax_value,
        optimizer=optimizer_name,
        max_steps=steps_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


def _resolve_references(
    counts: Mapping[str, int], references: Mapping[str, str] | None
) -> tuple[tuple[str, str], ...]:
    """Element -> elemental reference structure, sorted by symbol.

    Defaults come from ASE's tabulated ground states where they are one of the
    supported cubic types; anything else must be supplied via ``references``.
    """
    override = dict(references) if references is not None else {}
    unknown = sorted(set(override) - set(counts))
    if unknown:
        raise InputValidationError(
            f"references contains element(s) not in the formula: {unknown}"
        )
    resolved: dict[str, str] = {}
    for symbol in counts:
        if symbol in override:
            st = normalize_structure_type(override[symbol])
        else:
            ref = reference_states[atomic_numbers[symbol]]
            st = str(ref.get("symmetry", "")) if ref is not None else ""
        if st not in _ELEMENTAL_REFERENCE_TYPES:
            raise InputValidationError(
                f"no supported elemental reference structure for {symbol!r} "
                f"(need one of {sorted(_ELEMENTAL_REFERENCE_TYPES)}); pass "
                f"references={{{symbol!r}: <structure_type>}}"
            )
        resolved[symbol] = st
    return tuple(sorted(resolved.items()))


def compute_formation_enthalpy(
    calculator: Calculator,
    formula: str,
    structure_type: str,
    *,
    references: Mapping[str, str] | None = None,
    volume_span: float = DEFAULT_VOLUME_SPAN,
    n_points: int = DEFAULT_N_POINTS,
    max_recenter: int = DEFAULT_MAX_RECENTER,
) -> FormationEnthalpyResult:
    """Formation enthalpy per atom vs relaxed elemental references.

    ``dH_f = (E_compound_cell - sum_i n_i * E_elem_i_per_atom) / N`` with the
    compound and every elemental reference relaxed by the same calculator via
    the same recentring EOS scan.
    """
    t0 = time.perf_counter()
    st = normalize_structure_type(structure_type)
    counts = parse_formula(formula)
    if len(counts) < 2:
        raise InputValidationError(
            f"formation enthalpy needs a compound (>= 2 elements), got {formula!r}"
        )
    span, n = validate_scan_parameters(volume_span, n_points)
    recenter_budget = validate_max_recenter(max_recenter)
    resolved_references = _resolve_references(counts, references)
    compound_fit, n_atoms, cell_counts = relax_lattice(
        calculator, formula, st, estimate_lattice_constant(formula, st), span, n, recenter_budget
    )
    elemental: list[tuple[str, float]] = []
    for symbol, ref_st in resolved_references:
        elem_fit, elem_atoms, _ = relax_lattice(
            calculator,
            symbol,
            ref_st,
            estimate_lattice_constant(symbol, ref_st),
            span,
            n,
            recenter_budget,
        )
        elemental.append((symbol, elem_fit.e0_ev / elem_atoms))
    elemental_energies = dict(elemental)
    e_references = sum(
        cell_counts[symbol] * elemental_energies[symbol] for symbol in cell_counts
    )
    return FormationEnthalpyResult(
        formula=formula,
        structure_type=st,
        references=resolved_references,
        elemental_energies_ev_per_atom=tuple(elemental),
        compound_a0_angstrom=compound_fit.v0_a3 ** (1.0 / 3.0),
        compound_e0_ev_per_atom=compound_fit.e0_ev / n_atoms,
        formation_enthalpy_ev_per_atom=(compound_fit.e0_ev - e_references) / n_atoms,
        n_atoms_cell=n_atoms,
        volume_span=span,
        n_points=n,
        max_recenter=recenter_budget,
        wall_time_seconds=time.perf_counter() - t0,
    )


__all__ = [
    "DEFAULT_FMAX",
    "DEFAULT_MAX_RECENTER",
    "DEFAULT_MAX_STEPS",
    "DEFAULT_N_POINTS",
    "DEFAULT_OPTIMIZER",
    "DEFAULT_SUPERCELL",
    "DEFAULT_VOLUME_SPAN",
    "EosResult",
    "FormationEnthalpyResult",
    "LatticeResult",
    "VacancyFormationResult",
    "compute_eos",
    "compute_formation_enthalpy",
    "compute_lattice",
    "compute_vacancy_formation",
]
