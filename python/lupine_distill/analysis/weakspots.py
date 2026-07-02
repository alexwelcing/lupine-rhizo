"""H3: training-distribution failure prediction (prereg H3).

Per model: median |normalized error| over defect-family cells (E_vac,
gamma_SFE, surfaces) versus bulk-family cells (a0, B0, dH_f). Registered
thresholds: pass at ratio >= 2.0 for every model; kill when any model's
ratio < 1.5; in between is inconclusive. A seeded bootstrap (cells resampled
with replacement within each group) gives a 95% percentile CI.

Exploratory quarantine: cells observed before registration — the prereg
quarantines (Ni, mace-mp-small) — are excluded via caller-supplied
:class:`CellExclusion` records, never hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_BULK_PROPERTIES,
    DEFAULT_DEFECT_PROPERTIES,
)
from lupine_distill.analysis.vectors import ErrorCell

DEFAULT_PASS_RATIO = 2.0
DEFAULT_KILL_RATIO = 1.5
DEFAULT_N_BOOTSTRAP = 1000


@dataclass(frozen=True)
class CellExclusion:
    """A quarantined (material, model[, property]) cell for H3.

    ``property_name=None`` excludes every property of the (material, model)
    cell — the prereg's exploratory quarantine for (Ni, mace-mp-small).
    """

    material: str
    model_id: str
    property_name: str | None = None

    def matches(self, cell: ErrorCell) -> bool:
        return (
            cell.material == self.material
            and cell.model_id == self.model_id
            and (self.property_name is None or cell.property_name == self.property_name)
        )

    def as_record(self) -> tuple[str, str, str]:
        return (self.material, self.model_id, self.property_name or "*")


@dataclass(frozen=True)
class WeakSpotResult:
    """The H3 statistic for one model, self-describing for the ledger."""

    model_id: str
    defect_median_abs_error: float
    bulk_median_abs_error: float
    ratio: float
    ci_low: float
    ci_high: float
    n_defect_cells: int
    n_bulk_cells: int
    n_bootstrap: int
    excluded_cells: tuple[tuple[str, str, str], ...]
    verdict: str
    pass_ratio_threshold: float
    kill_ratio_threshold: float


def _verdict(ratio: float, pass_ratio: float, kill_ratio: float) -> str:
    if ratio >= pass_ratio:
        return "pass"
    if ratio < kill_ratio:
        return "kill"
    return "inconclusive"


def weak_spot_statistic(
    cells: Sequence[ErrorCell],
    *,
    model_id: str,
    defect_properties: Sequence[str] = DEFAULT_DEFECT_PROPERTIES,
    bulk_properties: Sequence[str] = DEFAULT_BULK_PROPERTIES,
    excluded_cells: Sequence[CellExclusion] = (),
    rng: np.random.Generator,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    pass_ratio: float = DEFAULT_PASS_RATIO,
    kill_ratio: float = DEFAULT_KILL_RATIO,
) -> WeakSpotResult:
    """Registered H3 statistic for one model with a seeded bootstrap CI."""
    if not isinstance(rng, np.random.Generator):
        raise InputValidationError(
            "rng must be a seeded numpy.random.Generator; "
            "global random state is never read"
        )
    if not isinstance(n_bootstrap, int) or n_bootstrap < 1:
        raise InputValidationError(
            f"n_bootstrap must be a positive int, got {n_bootstrap!r}"
        )
    if not (0.0 < kill_ratio <= pass_ratio):
        raise InputValidationError(
            f"need 0 < kill_ratio <= pass_ratio, got {kill_ratio}, {pass_ratio}"
        )
    overlap = set(defect_properties) & set(bulk_properties)
    if overlap:
        raise InputValidationError(
            f"properties in both defect and bulk groups: {sorted(overlap)!r}"
        )
    model_cells = [c for c in cells if c.model_id == model_id]
    if not model_cells:
        raise InputValidationError(f"no cells for model {model_id!r}")
    kept = [
        c
        for c in model_cells
        if not any(exclusion.matches(c) for exclusion in excluded_cells)
    ]
    defect = np.array(
        [abs(c.normalized_error) for c in kept if c.property_name in defect_properties],
        dtype=float,
    )
    bulk = np.array(
        [abs(c.normalized_error) for c in kept if c.property_name in bulk_properties],
        dtype=float,
    )
    if defect.size == 0 or bulk.size == 0:
        raise InputValidationError(
            f"model {model_id!r} needs cells in both groups after exclusions "
            f"(defect={defect.size}, bulk={bulk.size})"
        )
    defect_median = float(np.median(defect))
    bulk_median = float(np.median(bulk))
    if bulk_median <= 0.0:
        raise InputValidationError(
            f"bulk-family median |error| is zero for model {model_id!r}; "
            "H3 ratio undefined"
        )
    ratio = defect_median / bulk_median
    boot_ratios = np.empty(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        defect_sample = defect[rng.integers(0, defect.size, size=defect.size)]
        bulk_sample = bulk[rng.integers(0, bulk.size, size=bulk.size)]
        boot_bulk = float(np.median(bulk_sample))
        boot_ratios[i] = (
            float(np.median(defect_sample)) / boot_bulk if boot_bulk > 0.0 else np.inf
        )
    finite = boot_ratios[np.isfinite(boot_ratios)]
    if finite.size == 0:
        raise InputValidationError(
            f"bootstrap degenerate for model {model_id!r}: all resampled "
            "bulk medians were zero"
        )
    return WeakSpotResult(
        model_id=model_id,
        defect_median_abs_error=defect_median,
        bulk_median_abs_error=bulk_median,
        ratio=ratio,
        ci_low=float(np.percentile(finite, 2.5)),
        ci_high=float(np.percentile(finite, 97.5)),
        n_defect_cells=int(defect.size),
        n_bulk_cells=int(bulk.size),
        n_bootstrap=n_bootstrap,
        excluded_cells=tuple(e.as_record() for e in excluded_cells),
        verdict=_verdict(ratio, pass_ratio, kill_ratio),
        pass_ratio_threshold=pass_ratio,
        kill_ratio_threshold=kill_ratio,
    )


__all__ = [
    "CellExclusion",
    "DEFAULT_KILL_RATIO",
    "DEFAULT_N_BOOTSTRAP",
    "DEFAULT_PASS_RATIO",
    "WeakSpotResult",
    "weak_spot_statistic",
]
