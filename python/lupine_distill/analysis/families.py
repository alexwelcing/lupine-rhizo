"""Property-family data for the Y-matrix analysis (prereg 2026-07-01).

Family membership is *data*, not code: every analysis function takes a
``family_map`` argument, and the constants below are only the registered
defaults from the preregistration table
(docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md,
section "Property families (Y)"). Callers may pass alternative maps, e.g.
when elastic properties join after the Family A/B discrepancy is resolved.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping, Sequence

from lupine_distill.analysis.errors import InputValidationError

# Canonical property names used across runs, targets, and analysis.
A0 = "a0"
B0 = "b0"
B0_PRIME = "b0_prime"
E_VAC = "e_vac"
GAMMA_100 = "gamma_100"
GAMMA_110 = "gamma_110"
GAMMA_111 = "gamma_111"
GAMMA_SFE = "gamma_sfe"
DH_F = "dh_f"

CANONICAL_PROPERTIES: tuple[str, ...] = (
    A0,
    B0,
    B0_PRIME,
    E_VAC,
    GAMMA_100,
    GAMMA_110,
    GAMMA_111,
    GAMMA_SFE,
    DH_F,
)

# Registered default family map (prereg "Nulls": permutation unit per family).
DEFAULT_FAMILY_MAP: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "lattice_cohesion": (A0,),
        "eos": (B0, B0_PRIME),
        "point_defect": (E_VAC,),
        "surfaces": (GAMMA_100, GAMMA_110, GAMMA_111),
        "planar_fault": (GAMMA_SFE,),
        "compound_stability": (DH_F,),
    }
)

# Registered binding policy: DFT-PBE when available, else experiment.
DEFAULT_METHOD_PREFERENCE: tuple[str, ...] = ("DFT-PBE", "experiment")

# H3 groups (prereg H3): training-underrepresented vs bulk-adjacent.
DEFAULT_DEFECT_PROPERTIES: tuple[str, ...] = (
    E_VAC,
    GAMMA_SFE,
    GAMMA_100,
    GAMMA_110,
    GAMMA_111,
)
DEFAULT_BULK_PROPERTIES: tuple[str, ...] = (A0, B0, DH_F)

# Map from target-file property names (lupine.y_matrix_targets.v1) to
# canonical names. Names absent here (e.g. the orientation-averaged
# experimental "surface_energy", or finite-T properties outside this
# registration) are skipped and reported as unmapped, never guessed.
DEFAULT_TARGET_PROPERTY_MAP: Mapping[str, str] = MappingProxyType(
    {
        "lattice_constant": A0,
        "lattice_constant_a0": A0,
        "bulk_modulus": B0,
        "bulk_modulus_300K": B0,
        "bulk_modulus_pressure_derivative": B0_PRIME,
        "vacancy_formation_energy": E_VAC,
        "surface_energy_100": GAMMA_100,
        "surface_energy_110": GAMMA_110,
        "surface_energy_111": GAMMA_111,
        "intrinsic_stacking_fault_energy": GAMMA_SFE,
        "formation_enthalpy": DH_F,
        "formation_enthalpy_ev_per_atom": DH_F,
    }
)


def property_to_family(family_map: Mapping[str, Sequence[str]]) -> dict[str, str]:
    """Invert a family map to property -> family, rejecting overlaps."""
    validate_family_map(family_map)
    inverted: dict[str, str] = {}
    for family, members in family_map.items():
        for prop in members:
            inverted[prop] = family
    return inverted


def validate_family_map(family_map: Mapping[str, Sequence[str]]) -> None:
    """Fail fast on empty, overlapping, or malformed family maps."""
    if not family_map:
        raise InputValidationError("family_map must not be empty")
    seen: set[str] = set()
    for family, members in family_map.items():
        if not isinstance(family, str) or not family:
            raise InputValidationError(f"invalid family name: {family!r}")
        if not members:
            raise InputValidationError(f"family {family!r} has no properties")
        for prop in members:
            if not isinstance(prop, str) or not prop:
                raise InputValidationError(
                    f"family {family!r} has an invalid property name: {prop!r}"
                )
            if prop in seen:
                raise InputValidationError(
                    f"property {prop!r} appears in more than one family"
                )
            seen.add(prop)


def require_properties_in_family_map(
    properties: Sequence[str], family_map: Mapping[str, Sequence[str]]
) -> dict[str, str]:
    """Return property -> family for ``properties``; fail fast on strays."""
    inverted = property_to_family(family_map)
    missing = [p for p in properties if p not in inverted]
    if missing:
        raise InputValidationError(
            f"properties not present in family_map: {missing!r} "
            f"(known: {sorted(inverted)!r})"
        )
    return {p: inverted[p] for p in properties}


__all__ = [
    "A0",
    "B0",
    "B0_PRIME",
    "CANONICAL_PROPERTIES",
    "DEFAULT_BULK_PROPERTIES",
    "DEFAULT_DEFECT_PROPERTIES",
    "DEFAULT_FAMILY_MAP",
    "DEFAULT_METHOD_PREFERENCE",
    "DEFAULT_TARGET_PROPERTY_MAP",
    "DH_F",
    "E_VAC",
    "GAMMA_100",
    "GAMMA_110",
    "GAMMA_111",
    "GAMMA_SFE",
    "property_to_family",
    "require_properties_in_family_map",
    "validate_family_map",
]
