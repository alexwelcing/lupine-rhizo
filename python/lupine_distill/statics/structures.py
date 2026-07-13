"""Bulk crystal builders for the Tier-1 statics core.

Builds conventional (cubic) cells from ``(formula, structure_type)`` pairs and
provides deterministic initial lattice-constant guesses. All inputs are
validated up front; unknown structure types, malformed formulas, and
off-stoichiometry compositions fail fast with :class:`InputValidationError`.
"""

from __future__ import annotations

import math
from typing import Final, Mapping

import numpy as np
from ase import Atoms
from ase.build import bulk
from ase.data import atomic_numbers, covalent_radii, reference_states
from ase.formula import Formula

from lupine_distill.statics.errors import InputValidationError

SUPPORTED_STRUCTURE_TYPES: Final[tuple[str, ...]] = (
    "fcc",
    "bcc",
    "diamond",
    "rocksalt",
    "b2",
    "l12",
    "antifluorite",
    "perovskite",
)

_ELEMENTAL_TYPES: Final[frozenset[str]] = frozenset({"fcc", "bcc", "diamond"})
_BINARY_11_TYPES: Final[frozenset[str]] = frozenset({"rocksalt", "b2"})

# Largest lattice constant (A) accepted before we assume the input is garbage.
_MAX_LATTICE_CONSTANT_A: Final[float] = 50.0

# Nearest-neighbour distance d -> conventional lattice constant a, per type.
_NN_TO_A: Final[Mapping[str, float]] = {
    "fcc": math.sqrt(2.0),
    "bcc": 2.0 / math.sqrt(3.0),
    "diamond": 4.0 / math.sqrt(3.0),
    "rocksalt": 2.0,
    "b2": 2.0 / math.sqrt(3.0),
    "l12": math.sqrt(2.0),
    # Antifluorite: nearest neighbour is the cation-anion pair across a
    # tetrahedral hole, d = a*sqrt(3)/4.
    "antifluorite": 4.0 / math.sqrt(3.0),
    # Perovskite: nearest neighbour is the octahedral B-X bond, d = a/2.
    "perovskite": 2.0,
}


def normalize_structure_type(structure_type: str) -> str:
    """Validate and lowercase a structure type."""
    if not isinstance(structure_type, str):
        raise InputValidationError(
            f"structure_type must be a string, got {type(structure_type).__name__}"
        )
    normalized = structure_type.strip().lower()
    if normalized not in SUPPORTED_STRUCTURE_TYPES:
        raise InputValidationError(
            f"unknown structure_type {structure_type!r}; "
            f"supported: {', '.join(SUPPORTED_STRUCTURE_TYPES)}"
        )
    return normalized


def parse_formula(formula: str) -> dict[str, int]:
    """Parse a chemical formula into validated ``{symbol: count}`` (insertion order kept)."""
    if not isinstance(formula, str) or not formula.strip():
        raise InputValidationError("formula must be a non-empty string")
    try:
        counts = dict(Formula(formula.strip()).count())
    except Exception as exc:  # ase raises bare ValueError/KeyError on bad formulas
        raise InputValidationError(f"could not parse formula {formula!r}: {exc}") from exc
    if not counts:
        raise InputValidationError(f"formula {formula!r} contains no elements")
    unknown = [sym for sym in counts if sym not in atomic_numbers]
    if unknown:
        raise InputValidationError(
            f"formula {formula!r} contains unknown element symbol(s): {unknown}"
        )
    return counts


def validate_lattice_constant(lattice_constant: float) -> float:
    """Validate a lattice constant in Angstrom and return it as float."""
    try:
        a = float(lattice_constant)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"lattice_constant must be a number, got {lattice_constant!r}"
        ) from exc
    if not math.isfinite(a) or a <= 0.0 or a > _MAX_LATTICE_CONSTANT_A:
        raise InputValidationError(
            f"lattice_constant must be finite, > 0 and <= {_MAX_LATTICE_CONSTANT_A} A, got {a}"
        )
    return a


def _validate_composition(structure_type: str, counts: Mapping[str, int]) -> None:
    """Fail fast when the composition does not match the structure type."""
    n_elements = len(counts)
    if structure_type in _ELEMENTAL_TYPES:
        if n_elements != 1 or next(iter(counts.values())) != 1:
            raise InputValidationError(
                f"{structure_type} expects a single element symbol (e.g. 'Ni'), "
                f"got composition {dict(counts)}"
            )
        return
    if structure_type in _BINARY_11_TYPES:
        if n_elements != 2 or sorted(counts.values()) != [1, 1]:
            raise InputValidationError(
                f"{structure_type} expects a 1:1 binary formula (e.g. 'NiAl'), "
                f"got composition {dict(counts)}"
            )
        return
    if structure_type == "l12":
        if n_elements != 2 or sorted(counts.values()) != [1, 3]:
            raise InputValidationError(
                f"l12 expects an A3B formula (e.g. 'Ni3Al'), got composition {dict(counts)}"
            )
        return
    if structure_type == "antifluorite":
        if n_elements != 2 or sorted(counts.values()) != [1, 2]:
            raise InputValidationError(
                f"antifluorite expects an A2B formula (e.g. 'Li2S'), "
                f"got composition {dict(counts)}"
            )
        return
    if structure_type == "perovskite":
        if n_elements != 3 or sorted(counts.values()) != [1, 1, 3]:
            raise InputValidationError(
                f"perovskite expects an ABX3 formula (e.g. 'CsSnI3'), "
                f"got composition {dict(counts)}"
            )
        return
    raise InputValidationError(f"unhandled structure_type {structure_type!r}")  # pragma: no cover


def _build_l12(counts: Mapping[str, int], a: float) -> Atoms:
    """L1_2 (Cu3Au prototype): minority on the corner, majority on the faces."""
    majority = next(sym for sym, n in counts.items() if n == 3)
    minority = next(sym for sym, n in counts.items() if n == 1)
    scaled = [
        (0.0, 0.0, 0.0),
        (0.0, 0.5, 0.5),
        (0.5, 0.0, 0.5),
        (0.5, 0.5, 0.0),
    ]
    return Atoms(
        symbols=[minority, majority, majority, majority],
        scaled_positions=scaled,
        cell=np.eye(3) * a,
        pbc=True,
    )


def _build_antifluorite(counts: Mapping[str, int], a: float) -> Atoms:
    """Antifluorite (Li2O prototype): minority species on the fcc sublattice,
    majority species filling all eight tetrahedral holes (12-atom cell)."""
    majority = next(sym for sym, n in counts.items() if n == 2)
    minority = next(sym for sym, n in counts.items() if n == 1)
    fcc_sites = [
        (0.0, 0.0, 0.0),
        (0.0, 0.5, 0.5),
        (0.5, 0.0, 0.5),
        (0.5, 0.5, 0.0),
    ]
    tetrahedral_sites = [
        (x, y, z) for x in (0.25, 0.75) for y in (0.25, 0.75) for z in (0.25, 0.75)
    ]
    return Atoms(
        symbols=[minority] * 4 + [majority] * 8,
        scaled_positions=fcc_sites + tetrahedral_sites,
        cell=np.eye(3) * a,
        pbc=True,
    )


def _build_perovskite(counts: Mapping[str, int], a: float) -> Atoms:
    """Cubic perovskite (CaTiO3 prototype, 5-atom cell): the FIRST count-1
    element in formula order is the A site (cube corner, 12-coordinate), the
    second is the B site (body centre, octahedral); the count-3 element fills
    the face centres. Formula order is semantic: 'CsSnI3' puts Cs on A."""
    singletons = [sym for sym, n in counts.items() if n == 1]
    anion = next(sym for sym, n in counts.items() if n == 3)
    a_site, b_site = singletons[0], singletons[1]
    scaled = [
        (0.0, 0.0, 0.0),
        (0.5, 0.5, 0.5),
        (0.0, 0.5, 0.5),
        (0.5, 0.0, 0.5),
        (0.5, 0.5, 0.0),
    ]
    return Atoms(
        symbols=[a_site, b_site, anion, anion, anion],
        scaled_positions=scaled,
        cell=np.eye(3) * a,
        pbc=True,
    )


def build_structure(formula: str, structure_type: str, lattice_constant: float) -> Atoms:
    """Build the conventional cubic cell for ``(formula, structure_type)``.

    fcc/bcc/diamond use cubic conventional cells (4/2/8 atoms); rocksalt uses
    the 8-atom conventional cell; B2 (CsCl prototype) is its native 2-atom
    cubic cell; L1_2 (Cu3Au prototype) is its native 4-atom cubic cell;
    antifluorite (Li2O prototype) is its 12-atom conventional cubic cell;
    perovskite (CaTiO3 prototype) is its native 5-atom cubic cell.
    """
    st = normalize_structure_type(structure_type)
    counts = parse_formula(formula)
    a = validate_lattice_constant(lattice_constant)
    _validate_composition(st, counts)
    symbols = list(counts)
    if st in _ELEMENTAL_TYPES:
        return bulk(symbols[0], st, a=a, cubic=True)
    if st == "rocksalt":
        return bulk(f"{symbols[0]}{symbols[1]}", "rocksalt", a=a, cubic=True)
    if st == "b2":
        return bulk(f"{symbols[0]}{symbols[1]}", "cesiumchloride", a=a)
    if st == "antifluorite":
        return _build_antifluorite(counts, a)
    if st == "perovskite":
        return _build_perovskite(counts, a)
    return _build_l12(counts, a)


def _nearest_neighbour_distance(structure_type: str, counts: Mapping[str, int]) -> float:
    """Covalent-radius estimate of the nearest-neighbour distance (A)."""
    if structure_type == "perovskite":
        # The nearest neighbour is the octahedral B-X bond: second singleton
        # in formula order plus the count-3 anion.
        b_site = [sym for sym, n in counts.items() if n == 1][1]
        anion = next(sym for sym, n in counts.items() if n == 3)
        return float(
            covalent_radii[atomic_numbers[b_site]] + covalent_radii[atomic_numbers[anion]]
        )
    radii = [float(covalent_radii[atomic_numbers[sym]]) for sym in counts]
    if len(radii) == 1:
        return 2.0 * radii[0]
    # In rocksalt/B2/L1_2/antifluorite the nearest neighbour is an A-B pair.
    return radii[0] + radii[1]


def estimate_lattice_constant(formula: str, structure_type: str) -> float:
    """Deterministic initial lattice-constant guess (A) for the EOS scan.

    Elements whose ASE reference ground state matches ``structure_type`` use
    the tabulated experimental value; everything else falls back to a
    covalent-radius nearest-neighbour estimate. This is only a starting guess:
    the EOS relaxation re-centres its volume scan until the minimum is
    bracketed.
    """
    st = normalize_structure_type(structure_type)
    counts = parse_formula(formula)
    _validate_composition(st, counts)
    if st in _ELEMENTAL_TYPES:
        symbol = next(iter(counts))
        ref = reference_states[atomic_numbers[symbol]]
        if ref is not None and ref.get("symmetry") == st and "a" in ref:
            return float(ref["a"])
    return _NN_TO_A[st] * _nearest_neighbour_distance(st, counts)


__all__ = [
    "SUPPORTED_STRUCTURE_TYPES",
    "build_structure",
    "estimate_lattice_constant",
    "normalize_structure_type",
    "parse_formula",
    "validate_lattice_constant",
]
