"""Coupling-aware permutation nulls (prereg section "Nulls" — mandatory).

Naive permutation nulls lie when properties are internally coupled. The
registered null keeps within-family structure and destroys cross-family
alignment: for each property family independently, the material labels of
that family's error sub-vectors are permuted (one shared permutation for all
columns of a family, drawn independently per family). 1,000 draws by
default; every draw comes from a caller-supplied seeded
``numpy.random.Generator`` — global random state is never read.

Interpretation of the H1 band: the prereg kill condition is "PR within or
above the null band", so H1 passes only when the observed PR falls *below*
the null distribution's lower tail (5th percentile at the registered 95%
level). Both p05 and p95 are reported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.dimensionality import (
    leading_mode,
    pairwise_cosine,
    participation_ratio,
)
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_FAMILY_MAP,
    require_properties_in_family_map,
)

DEFAULT_N_DRAWS = 1000


@dataclass(frozen=True)
class NullDistribution:
    """An empirical null distribution with its registered percentiles."""

    statistic: str
    n_draws: int
    values: tuple[float, ...]
    p05: float
    p50: float
    p95: float

    @classmethod
    def from_values(cls, statistic: str, values: Sequence[float]) -> "NullDistribution":
        if not values:
            raise InputValidationError("null distribution needs >= 1 draw")
        array = np.asarray(values, dtype=float)
        return cls(
            statistic=statistic,
            n_draws=len(values),
            values=tuple(float(v) for v in values),
            p05=float(np.percentile(array, 5.0)),
            p50=float(np.percentile(array, 50.0)),
            p95=float(np.percentile(array, 95.0)),
        )


def _validate_rng(rng: object) -> np.random.Generator:
    if not isinstance(rng, np.random.Generator):
        raise InputValidationError(
            "rng must be a seeded numpy.random.Generator (e.g. "
            "np.random.default_rng(seed)); global random state is never read"
        )
    return rng


def _validate_draws(n_draws: int) -> None:
    if not isinstance(n_draws, int) or n_draws < 1:
        raise InputValidationError(f"n_draws must be a positive int, got {n_draws!r}")


def _family_columns(
    properties: Sequence[str], family_map: Mapping[str, Sequence[str]]
) -> dict[str, list[int]]:
    require_properties_in_family_map(properties, family_map)
    columns: dict[str, list[int]] = {}
    for index, prop in enumerate(properties):
        for family, members in family_map.items():
            if prop in members:
                columns.setdefault(family, []).append(index)
                break
    return columns


def permute_within_families(
    values: np.ndarray,
    properties: Sequence[str],
    *,
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    rng: np.random.Generator,
) -> np.ndarray:
    """One registered null draw: per-family material-label permutation."""
    generator = _validate_rng(rng)
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[1] != len(properties):
        raise InputValidationError(
            f"values shape {array.shape} does not match {len(properties)} properties"
        )
    permuted = np.array(array, copy=True)
    for columns in _family_columns(properties, family_map).values():
        row_order = generator.permutation(array.shape[0])
        permuted[:, columns] = array[np.ix_(row_order, columns)]
    return permuted


def pr_null_distribution(
    values: np.ndarray,
    properties: Sequence[str],
    *,
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    n_draws: int = DEFAULT_N_DRAWS,
    rng: np.random.Generator,
) -> NullDistribution:
    """Null distribution of the participation ratio (H1)."""
    _validate_rng(rng)
    _validate_draws(n_draws)
    draws = [
        participation_ratio(
            permute_within_families(
                values, properties, family_map=family_map, rng=rng
            )
        )
        for _ in range(n_draws)
    ]
    return NullDistribution.from_values("participation_ratio", draws)


def leading_mode_cosine_null(
    values_by_model: Mapping[str, np.ndarray],
    properties: Sequence[str],
    *,
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    n_draws: int = DEFAULT_N_DRAWS,
    rng: np.random.Generator,
) -> dict[tuple[str, str], NullDistribution]:
    """Null distribution of pairwise leading-mode |cosine| (H2), per pair.

    Each draw permutes every model's matrix independently (fresh per-family
    permutations), recomputes leading modes, and records all pairwise
    absolute cosines.
    """
    _validate_rng(rng)
    _validate_draws(n_draws)
    models = list(values_by_model)
    if len(models) < 2:
        raise InputValidationError(
            f"cosine null needs >= 2 models, got {len(models)}"
        )
    shapes = {values_by_model[m].shape for m in models}
    if len(shapes) != 1:
        raise InputValidationError(
            f"model matrices must share a shape, got {sorted(shapes)!r}"
        )
    pairs = [
        (models[i], models[j])
        for i in range(len(models))
        for j in range(i + 1, len(models))
    ]
    draws: dict[tuple[str, str], list[float]] = {pair: [] for pair in pairs}
    for _ in range(n_draws):
        modes = {
            model: leading_mode(
                permute_within_families(
                    values_by_model[model], properties, family_map=family_map, rng=rng
                )
            )
            for model in models
        }
        for pair in pairs:
            draws[pair].append(pairwise_cosine(modes[pair[0]], modes[pair[1]]))
    return {
        pair: NullDistribution.from_values("leading_mode_abs_cosine", values)
        for pair, values in draws.items()
    }


__all__ = [
    "DEFAULT_N_DRAWS",
    "NullDistribution",
    "leading_mode_cosine_null",
    "permute_within_families",
    "pr_null_distribution",
]
