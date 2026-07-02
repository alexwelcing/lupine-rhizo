"""Tier-1 statics physics core: structures, EOS, lattice, defects, surfaces.

Calculator-agnostic (any ASE calculator), deterministic, and fail-fast. Every
public compute function returns a frozen result dataclass with
``canonical_inputs()`` (deterministic, JSON-serializable run identity) and
``to_dict()`` (uniform property/values/units/canonical_inputs envelope).
"""

from __future__ import annotations

from lupine_distill.statics.calculations import (
    DEFAULT_FMAX,
    DEFAULT_MAX_RECENTER,
    DEFAULT_MAX_STEPS,
    DEFAULT_N_POINTS,
    DEFAULT_OPTIMIZER,
    DEFAULT_SUPERCELL,
    DEFAULT_VOLUME_SPAN,
    EosResult,
    FormationEnthalpyResult,
    LatticeResult,
    VacancyFormationResult,
    compute_eos,
    compute_formation_enthalpy,
    compute_lattice,
    compute_vacancy_formation,
)
from lupine_distill.statics.eos import (
    BirchMurnaghanFit,
    fit_birch_murnaghan,
    scan_energy_volume,
    validate_scan_parameters,
)
from lupine_distill.statics.errors import (
    CalculationError,
    ConvergenceError,
    InputValidationError,
    StaticsError,
)
from lupine_distill.statics.relax import (
    SUPPORTED_OPTIMIZERS,
    relax_positions,
    single_point_energy,
    validate_relax_parameters,
)
from lupine_distill.statics.structures import (
    SUPPORTED_STRUCTURE_TYPES,
    build_structure,
    estimate_lattice_constant,
    normalize_structure_type,
    parse_formula,
    validate_lattice_constant,
)
from lupine_distill.statics.surfaces import (
    SFE_METHOD,
    SUPPORTED_SURFACES,
    StackingFaultResult,
    SurfaceEnergyResult,
    compute_stacking_fault_energy,
    compute_surface_energies,
    compute_surface_energy,
)

__all__ = [
    "BirchMurnaghanFit",
    "CalculationError",
    "ConvergenceError",
    "DEFAULT_FMAX",
    "DEFAULT_MAX_RECENTER",
    "DEFAULT_MAX_STEPS",
    "DEFAULT_N_POINTS",
    "DEFAULT_OPTIMIZER",
    "DEFAULT_SUPERCELL",
    "DEFAULT_VOLUME_SPAN",
    "EosResult",
    "FormationEnthalpyResult",
    "InputValidationError",
    "LatticeResult",
    "SFE_METHOD",
    "SUPPORTED_OPTIMIZERS",
    "SUPPORTED_STRUCTURE_TYPES",
    "SUPPORTED_SURFACES",
    "StackingFaultResult",
    "StaticsError",
    "SurfaceEnergyResult",
    "VacancyFormationResult",
    "build_structure",
    "compute_eos",
    "compute_formation_enthalpy",
    "compute_lattice",
    "compute_stacking_fault_energy",
    "compute_surface_energies",
    "compute_surface_energy",
    "compute_vacancy_formation",
    "estimate_lattice_constant",
    "fit_birch_murnaghan",
    "normalize_structure_type",
    "parse_formula",
    "relax_positions",
    "scan_energy_volume",
    "single_point_energy",
    "validate_lattice_constant",
    "validate_relax_parameters",
    "validate_scan_parameters",
]
