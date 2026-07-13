"""Random-solid-solution (RSS) supercell builders for multi-component alloys.

Builds a conventional cubic host lattice (fcc or bcc), repeats it, and
assigns chemical species to sites by a seeded random permutation, so the
same ``(composition, structure_type, lattice_constant, repeat, seed)`` always
yields the identical structure. Composition counts must scale to EXACT
integer site counts for the requested supercell -- anything else fails fast
with :class:`InputValidationError`.

Lattice-constant guesses use Vegard's law: the composition-weighted average
of per-element estimates (ASE reference lattice constant when the element's
ground state matches the host symmetry, covalent-radius nearest-neighbour
estimate otherwise), mirroring
:func:`lupine_distill.statics.structures.estimate_lattice_constant`.
"""

from __future__ import annotations

from typing import Final, Mapping

import numpy as np
from ase import Atoms
from ase.build import bulk
from ase.data import atomic_numbers, covalent_radii, reference_states

from lupine_distill.statics.errors import InputValidationError
from lupine_distill.statics.structures import validate_lattice_constant

RSS_STRUCTURE_TYPES: Final[tuple[str, ...]] = ("fcc", "bcc")

_SITES_PER_CONVENTIONAL_CELL: Final[Mapping[str, int]] = {"fcc": 4, "bcc": 2}

#: Nearest-neighbour distance d -> conventional lattice constant a.
_NN_TO_A: Final[Mapping[str, float]] = {
    "fcc": float(np.sqrt(2.0)),
    "bcc": 2.0 / float(np.sqrt(3.0)),
}


def _validate_rss_structure_type(structure_type: str) -> str:
    if not isinstance(structure_type, str):
        raise InputValidationError(
            f"structure_type must be a string, got {type(structure_type).__name__}"
        )
    normalized = structure_type.strip().lower()
    if normalized not in RSS_STRUCTURE_TYPES:
        raise InputValidationError(
            f"RSS structure_type must be one of {RSS_STRUCTURE_TYPES}, "
            f"got {structure_type!r}"
        )
    return normalized


def _validate_composition(composition: Mapping[str, int]) -> dict[str, int]:
    """Validate an RSS composition; returns ``{symbol: count}`` (order kept)."""
    if not isinstance(composition, Mapping) or not composition:
        raise InputValidationError(
            "composition must be a non-empty mapping of element symbol -> count"
        )
    counts: dict[str, int] = {}
    for symbol, count in composition.items():
        if not isinstance(symbol, str) or symbol not in atomic_numbers:
            raise InputValidationError(
                f"composition contains unknown element symbol {symbol!r}"
            )
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise InputValidationError(
                f"composition count for {symbol!r} must be a positive integer, "
                f"got {count!r}"
            )
        if symbol in counts:
            raise InputValidationError(f"duplicate element symbol {symbol!r}")
        counts[symbol] = count
    return counts


def _validate_repeat(repeat: int) -> int:
    if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
        raise InputValidationError(f"repeat must be an integer >= 1, got {repeat!r}")
    return repeat


def _validate_seed(seed: int) -> int:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise InputValidationError(f"seed must be a non-negative integer, got {seed!r}")
    return seed


def site_counts_for_supercell(
    composition: Mapping[str, int], structure_type: str, repeat: int
) -> dict[str, int]:
    """Exact per-element site counts for the ``repeat**3`` supercell.

    Fails fast unless every scaled count is an exact integer (i.e. the total
    number of lattice sites is divisible so the composition ratio is realized
    without rounding).
    """
    st = _validate_rss_structure_type(structure_type)
    counts = _validate_composition(composition)
    n_repeat = _validate_repeat(repeat)
    total_sites = _SITES_PER_CONVENTIONAL_CELL[st] * n_repeat**3
    total_units = sum(counts.values())
    scaled: dict[str, int] = {}
    for symbol, count in counts.items():
        exact = count * total_sites
        if exact % total_units != 0:
            raise InputValidationError(
                f"composition {dict(counts)} does not fit a {st} "
                f"{n_repeat}x{n_repeat}x{n_repeat} supercell: {total_sites} sites "
                f"cannot realize {symbol}:{count}/{total_units} exactly "
                f"({count}*{total_sites}/{total_units} is not an integer)"
            )
        scaled[symbol] = exact // total_units
    return scaled


def build_rss_supercell(
    composition: Mapping[str, int],
    structure_type: str,
    lattice_constant: float,
    repeat: int,
    seed: int,
) -> Atoms:
    """Random-solid-solution supercell on a conventional cubic host lattice.

    The conventional cubic cell (fcc: 4 sites, bcc: 2 sites) at
    ``lattice_constant`` is repeated ``(repeat, repeat, repeat)`` and species
    are assigned to sites via a ``numpy.random.default_rng(seed)`` permutation
    of the deterministic composition-ordered symbol list -- the same inputs
    always produce the identical structure.
    """
    st = _validate_rss_structure_type(structure_type)
    counts = _validate_composition(composition)
    a = validate_lattice_constant(lattice_constant)
    n_repeat = _validate_repeat(repeat)
    rng_seed = _validate_seed(seed)
    scaled_counts = site_counts_for_supercell(counts, st, n_repeat)

    # Host lattice: element choice is irrelevant (symbols are overwritten).
    template_symbol = next(iter(counts))
    host = bulk(template_symbol, st, a=a, cubic=True).repeat(
        (n_repeat, n_repeat, n_repeat)
    )
    total_sites = len(host)

    symbols: list[str] = []
    for symbol, n_sites in scaled_counts.items():
        symbols.extend([symbol] * n_sites)
    permutation = np.random.default_rng(rng_seed).permutation(total_sites)
    host.set_chemical_symbols([symbols[i] for i in permutation])
    return host


def _elemental_lattice_estimate(symbol: str, structure_type: str) -> float:
    """Per-element conventional lattice constant estimate for the host type.

    Uses the tabulated ASE reference lattice constant when the element's
    reference ground state has the host symmetry; otherwise a covalent-radius
    nearest-neighbour estimate (same fallback as
    :func:`lupine_distill.statics.structures.estimate_lattice_constant`).
    """
    ref = reference_states[atomic_numbers[symbol]]
    if ref is not None and ref.get("symmetry") == structure_type and "a" in ref:
        return float(ref["a"])
    nn_distance = 2.0 * float(covalent_radii[atomic_numbers[symbol]])
    return _NN_TO_A[structure_type] * nn_distance


def estimate_rss_lattice_constant(
    composition: Mapping[str, int], structure_type: str
) -> float:
    """Vegard's-law lattice-constant guess for an RSS composition (Angstrom).

    Composition-weighted average of the per-element estimates from
    :func:`_elemental_lattice_estimate`. This is only a starting guess for an
    E-V relaxation, exactly like the elemental estimator it mirrors.
    """
    st = _validate_rss_structure_type(structure_type)
    counts = _validate_composition(composition)
    total = sum(counts.values())
    weighted = sum(
        count * _elemental_lattice_estimate(symbol, st)
        for symbol, count in counts.items()
    )
    return validate_lattice_constant(weighted / total)


__all__ = [
    "RSS_STRUCTURE_TYPES",
    "build_rss_supercell",
    "estimate_rss_lattice_constant",
    "site_counts_for_supercell",
]
