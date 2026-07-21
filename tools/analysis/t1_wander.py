"""T1 "convention-wander" gate for the Z1 sparse-DFT pilot (theorem line 1).

Implements the T1 experiment of
`docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md` (§A1) as a reusable,
stdlib-only gate. The writeup is `docs/analysis/t1-wander-gate.md`.

Barriers are energy *differences between different structures*, so any
non-constant GPAW↔VASP (cross-engine) offset injects directly into a
cross-engine barrier comparison. Per evaluated image the offset is
`gpaw_energy_ev - reference_energy_ev`; the barrier-relevant quantity is the
offset WANDER (max − min over evaluated images), not the mean.

Measured evidence that motivated this gate:
- path-7 (mp-770939_10_1_1_0_1): wander ~139 meV, cross-engine barrier error
  118.8 meV -> FAIL vs the frozen <=40 meV verdict gate.
- smoke path (mp-760344): wander ~122 meV, cross-engine error 32.2 meV -> WIN.
Same wander magnitude, opposite verdicts: wander is necessary-but-not-
sufficient for a cross-engine failure, so T1 is a GATE with a contamination
flag, never a hard refusal.

Gate semantics: `offset_wander_mev > gate_mev` (default 40 meV, the frozen
WIN threshold) => verdict "contaminated"; otherwise "clean". With fewer than
two evaluated images the wander carries no information and the verdict is
"insufficient_data". A contaminated verdict means the path's cross-engine
(VASP-referenced) numbers measure engine-convention luck and must be labelled
"convention-contaminated"; the same-engine basis (amendment A1) is the only
trustworthy score for that path.
"""

from __future__ import annotations

import math

# Gate threshold: the frozen verdict-gate value (WIN_THRESHOLD_MEV in
# gcp/mlip-cell-runner/z1_sparse_dft.py). Kept as a local constant so this
# module stays stdlib-only and import-free of the runner.
GATE_MEV = 40.0

VERDICT_CLEAN = "clean"
VERDICT_CONTAMINATED = "contaminated"
VERDICT_INSUFFICIENT_DATA = "insufficient_data"

# Minimum image count for a wander verdict; below it the gate cannot speak.
MIN_GATE_IMAGES = 2

# Minimum image count for a Spearman monotonicity estimate; with two points
# the rank correlation is always +/-1 and carries no information.
MIN_SPEARMAN_IMAGES = 3


def offset_mev(gpaw_energy_ev: float, reference_energy_ev: float) -> float:
    """Per-image cross-engine offset in meV."""
    return (float(gpaw_energy_ev) - float(reference_energy_ev)) * 1000.0


def _average_ranks(values: list[float]) -> list[float]:
    """1-based ranks with ties sharing the average rank."""
    order = sorted(range(len(values)), key=lambda i: (values[i], i))
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(order):
        end = pos
        while end + 1 < len(order) and values[order[end + 1]] == values[order[pos]]:
            end += 1
        rank = (pos + end) / 2.0 + 1.0
        for k in range(pos, end + 1):
            ranks[order[k]] = rank
        pos = end + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation; None when either side has zero variance."""
    n = len(xs)
    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    dx = [x - mean_x for x in xs]
    dy = [y - mean_y for y in ys]
    var_x = math.fsum(d * d for d in dx)
    var_y = math.fsum(d * d for d in dy)
    if var_x == 0.0 or var_y == 0.0:
        return None
    cov = math.fsum(a * b for a, b in zip(dx, dy))
    return cov / math.sqrt(var_x * var_y)


def spearman_rho(indices: list[float], values: list[float]) -> float | None:
    """Spearman rank correlation (monotonicity) of values vs image index.

    None when there are fewer than MIN_SPEARMAN_IMAGES points or when either
    side is constant (the correlation is then undefined, not zero).
    """
    if len(indices) < MIN_SPEARMAN_IMAGES:
        return None
    return _pearson(_average_ranks(indices), _average_ranks(values))


def linear_trend(
    indices: list[float], values: list[float]
) -> tuple[float, float] | None:
    """Least-squares (intercept, slope) of values vs image index.

    None when fewer than two points or all indices coincide. Indices may be
    non-contiguous (e.g. path-7's anchor set {0, 1, 2, 4}).
    """
    n = len(indices)
    if n < 2:
        return None
    mean_x = math.fsum(indices) / n
    mean_y = math.fsum(values) / n
    var_x = math.fsum((x - mean_x) ** 2 for x in indices)
    if var_x == 0.0:
        return None
    slope = math.fsum((x - mean_x) * (y - mean_y) for x, y in zip(indices, values)) / var_x
    return mean_y - slope * mean_x, slope


def analyze_offsets(
    images: list[tuple[int, float, float]], gate_mev: float = GATE_MEV
) -> dict:
    """T1 gate report for one path's evaluated images.

    `images` is a list of (image_index, gpaw_energy_ev, reference_energy_ev)
    triples in any order; indices are the path's real image indices and may
    be non-contiguous. Returns a JSON-serializable report:

    - offset_mean_mev / offset_min_mev / offset_max_mev / offset_wander_mev
      (all None when no images)
    - driver_pair: [index of min offset, index of max offset] — the image
      pair whose offset difference IS the wander (first-occurrence tie-break,
      mirroring z1_sparse_dft.select_extrema); None with < 2 images
    - verdict: "clean" | "contaminated" | "insufficient_data"
    - trend_intercept_mev / trend_slope_mev_per_image: least-squares linear
      trend of offset vs image index (None with < 2 images)
    - per_image: offset, trend value, and drift (residual vs trend) per image
    - spearman_rho: offset-vs-index monotonicity (None when undefined)
    """
    points = sorted(
        (
            int(index),
            offset_mev(gpaw_energy_ev, reference_energy_ev),
        )
        for index, gpaw_energy_ev, reference_energy_ev in images
    )
    indices = [index for index, _ in points]
    offsets = [offset for _, offset in points]
    n = len(points)

    if n == 0:
        return {
            "gate_mev": gate_mev,
            "image_count": 0,
            "offset_mean_mev": None,
            "offset_min_mev": None,
            "offset_max_mev": None,
            "offset_wander_mev": None,
            "driver_pair": None,
            "verdict": VERDICT_INSUFFICIENT_DATA,
            "trend_intercept_mev": None,
            "trend_slope_mev_per_image": None,
            "per_image": [],
            "spearman_rho": None,
        }

    min_pos = min(range(n), key=lambda k: (offsets[k], indices[k]))
    max_pos = max(range(n), key=lambda k: (offsets[k], -indices[k]))
    wander = offsets[max_pos] - offsets[min_pos]
    trend = linear_trend([float(i) for i in indices], offsets)

    per_image = []
    for index, offset in points:
        trend_value = None
        drift = None
        if trend is not None:
            trend_value = trend[0] + trend[1] * index
            drift = offset - trend_value
        per_image.append(
            {
                "index": index,
                "offset_mev": offset,
                "trend_mev": trend_value,
                "drift_mev": drift,
            }
        )

    if n < MIN_GATE_IMAGES:
        verdict = VERDICT_INSUFFICIENT_DATA
    elif wander > gate_mev:
        verdict = VERDICT_CONTAMINATED
    else:
        verdict = VERDICT_CLEAN

    return {
        "gate_mev": gate_mev,
        "image_count": n,
        "offset_mean_mev": math.fsum(offsets) / n,
        "offset_min_mev": offsets[min_pos],
        "offset_max_mev": offsets[max_pos],
        "offset_wander_mev": wander,
        "driver_pair": [indices[min_pos], indices[max_pos]] if n >= MIN_GATE_IMAGES else None,
        "verdict": verdict,
        "trend_intercept_mev": trend[0] if trend is not None else None,
        "trend_slope_mev_per_image": trend[1] if trend is not None else None,
        "per_image": per_image,
        "spearman_rho": spearman_rho([float(i) for i in indices], offsets),
    }
