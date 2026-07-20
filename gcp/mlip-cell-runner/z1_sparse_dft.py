"""MLIP-guided sparse-DFT barrier row for the locked Z1 panel.

Implements the frozen protocol of
docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md
(campaign `discovery.round-5.z1-sparse-dft.v1`):

1. The MLIP only GUIDES: single-point energies of the path's input images
   (no relaxation, no NEB) propose the min/max image indices.
2. Anchors = reference-profile positions {model-min, model-max +/- 1} + both
   endpoints. Paths with <= SHORT_PATH_IMAGE_THRESHOLD images widen the max
   window to +/- 2 (declared fallback, recorded per path, never tuned).
3. GPAW (fd/PBE, frozen parameters) evaluates each anchor image as a
   single point. Sparse barrier = max(anchor energies) - min(anchor energies),
   compared against the panel's locked reference barrier.
4. Fail-closed: any model- or GPAW-side failure on a path records that path
   as failed with the error; nothing is imputed, anchors beyond the frozen
   sets are never added.

GPAW is imported lazily inside the calculator factory so runner images
without gpaw keep every other row working; the sparse row itself fails
closed at evaluation time when gpaw is absent.
"""

from __future__ import annotations

import math
import statistics
from typing import Any, Callable

from z1_barrier import PredictionCheckpoint, atoms_from_image

SPARSE_DFT_ROW_ID = "sparse_dft_barrier"
CAMPAIGN_ID = "discovery.round-5.z1-sparse-dft.v1"
PREREGISTRATION = "docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md"

# Frozen success criteria (prereg "Success criteria" section).
WIN_THRESHOLD_MEV = 40.0
STRONG_WIN_THRESHOLD_MEV = 15.0
ANCHOR_BUDGET_PER_PATH = 7
COST_CLAIM_MEDIAN_ANCHORS = 10

# Frozen anchor rule: paths this short widen the saddle window from +/-1 to
# +/-2 because +/-1 already covers more than half the path.
SHORT_PATH_IMAGE_THRESHOLD = 6

# Frozen GPAW convention (prereg "Compute" section). Tests may monkeypatch
# this mapping to toy settings; the executed parameters are always recorded
# verbatim in row_spec, so a patched run is identifiable from its artifact.
FROZEN_GPAW_PARAMS: dict[str, Any] = {
    "mode": "fd",
    "xc": "PBE",
    "h": 0.18,
    "kpts": (2, 2, 2),
    "txt": None,
}

# Kill-condition line item: saddle-location guidance error above this rate is
# reported with the same prominence as a WIN.
SADDLE_LOCATION_ERROR_PROMINENCE_RATE = 0.15


def family_of(chemical_system: str) -> str:
    """Chemical-system family classifier.

    Mirrors tools/score_z1r5_correction.py:family_of exactly (same precedence).
    The runner image does not ship tools/, so the logic is duplicated here;
    test_z1_sparse_dft.py pins equivalence against the tools original so the
    two copies cannot drift.
    """
    parts = set(chemical_system.split("-"))
    if "F" in parts or "Cl" in parts:
        return "halide"
    if "S" in parts:
        return "sulfide"
    if "P" in parts:
        return "phosphate"
    if "B" in parts or "As" in parts:
        return "borate"
    if "N" in parts:
        return "nitride"
    return "oxide"


def default_dft_calculator_factory() -> Any:
    """Fresh GPAW calculator with the frozen convention, one per anchor image."""
    from gpaw import GPAW

    return GPAW(**FROZEN_GPAW_PARAMS)


def select_extrema(energies: list[float]) -> tuple[int, int]:
    """(min_index, max_index) with deterministic first-occurrence tie-break."""
    if not energies:
        raise ValueError("cannot select extrema of an empty energy profile")
    min_index = min(range(len(energies)), key=lambda i: (energies[i], i))
    max_index = max(range(len(energies)), key=lambda i: (energies[i], -i))
    return min_index, max_index


def build_anchor_set(
    image_count: int, model_min_index: int, model_max_index: int
) -> dict[str, Any]:
    """Frozen anchor set for a path of `image_count` images.

    Anchors = {0, image_count-1, model-min} ∪ {model-max-window .. model-max+window},
    window = 2 when image_count <= SHORT_PATH_IMAGE_THRESHOLD else 1, clamped
    to valid indices and de-duplicated. The applied window and the short-path
    fallback are recorded, per the preregistration.
    """
    if image_count < 3:
        raise ValueError(f"a path needs at least 3 images; got {image_count}")
    for label, index in (("model_min_index", model_min_index), ("model_max_index", model_max_index)):
        if not 0 <= index < image_count:
            raise ValueError(f"{label} {index} is outside the path of {image_count} images")
    short_path_fallback = image_count <= SHORT_PATH_IMAGE_THRESHOLD
    window = 2 if short_path_fallback else 1
    anchors = {0, image_count - 1, model_min_index}
    anchors.update(
        index
        for index in range(model_max_index - window, model_max_index + window + 1)
        if 0 <= index < image_count
    )
    return {
        "anchor_indices": sorted(anchors),
        "window": window,
        "short_path_fallback": short_path_fallback,
    }


def _finite_energies(atoms_list: list[Any], calc: Any, label: str) -> list[float]:
    """Single-point energies only. The model guide never relaxes anything."""
    energies: list[float] = []
    for index, atoms in enumerate(atoms_list):
        atoms.calc = calc
        energy = float(atoms.get_potential_energy())
        if not math.isfinite(energy):
            raise RuntimeError(f"{label} produced a non-finite energy on image {index}")
        energies.append(energy)
    return energies


def _reference_profile(path: dict[str, Any], image_count: int) -> list[float]:
    reference = path.get("reference")
    energies = reference.get("energies_ev") if isinstance(reference, dict) else None
    if (
        not isinstance(energies, list)
        or len(energies) != image_count
        or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in energies)
    ):
        raise RuntimeError(
            "panel path is missing a reference.energies_ev profile aligned with input_images"
        )
    return [float(v) for v in energies]


def run_sparse_dft_path(
    path: dict[str, Any],
    model_calc: Any,
    dft_calculator_factory: Callable[[], Any],
) -> dict[str, Any]:
    """Execute the frozen sparse-DFT protocol on one panel path."""
    images = [atoms_from_image(record) for record in path["input_images"]]
    image_count = len(images)

    # Step 1 (guide): model single-points over the input images.
    model_energies = _finite_energies(images, model_calc, "model calculator")
    model_min_index, model_max_index = select_extrema(model_energies)

    # Step 2 (anchors): frozen set, declared +/-2 short-path fallback.
    anchor = build_anchor_set(image_count, model_min_index, model_max_index)
    anchor_indices = anchor["anchor_indices"]

    # Reference profile: DFT argmax and per-anchor reference energies.
    reference_energies = _reference_profile(path, image_count)
    _, dft_profile_max_index = select_extrema(reference_energies)

    # Step 3 (measure): GPAW single-points at the anchor images only.
    anchor_records: list[dict[str, Any]] = []
    for index in anchor_indices:
        atoms = atoms_from_image(path["input_images"][index])
        atoms.calc = dft_calculator_factory()
        gpaw_energy = float(atoms.get_potential_energy())
        if not math.isfinite(gpaw_energy):
            raise RuntimeError(f"GPAW produced a non-finite energy on anchor image {index}")
        reference_energy = reference_energies[index]
        anchor_records.append(
            {
                "image_index": index,
                "gpaw_energy_ev": gpaw_energy,
                "reference_energy_ev": reference_energy,
                "offset_mev": (gpaw_energy - reference_energy) * 1000.0,
            }
        )

    gpaw_energies = [record["gpaw_energy_ev"] for record in anchor_records]
    sparse_barrier = max(gpaw_energies) - min(gpaw_energies)
    reference_barrier = float(path["reference_barrier_ev"])
    signed_error_mev = (sparse_barrier - reference_barrier) * 1000.0
    if not math.isfinite(signed_error_mev):
        raise RuntimeError("sparse barrier signed error is non-finite")
    saddle_index_distance = abs(model_max_index - dft_profile_max_index)
    return {
        "path_id": path["path_id"],
        "material_id": path.get("material_id"),
        "chemical_system": path.get("chemical_system"),
        "family": family_of(str(path.get("chemical_system"))),
        "status": "completed",
        "image_count": image_count,
        "anchor_indices": anchor_indices,
        "anchor_count": len(anchor_indices),
        "window": anchor["window"],
        "short_path_fallback": anchor["short_path_fallback"],
        "model_energies_ev": model_energies,
        "model_min_index": model_min_index,
        "model_max_index": model_max_index,
        "dft_profile_max_index": dft_profile_max_index,
        "saddle_index_agreement": saddle_index_distance == 0,
        "saddle_index_distance": saddle_index_distance,
        "anchors": anchor_records,
        "sparse_barrier_ev": sparse_barrier,
        "reference_barrier_ev": reference_barrier,
        "signed_error_mev": signed_error_mev,
        "absolute_error_mev": abs(signed_error_mev),
    }


def _mean_mev(values: list[float]) -> float | None:
    if not values:
        return None
    mae = float(math.fsum(values) / len(values))
    return mae if math.isfinite(mae) else None


def run_sparse_dft_row(
    manifest: dict[str, Any],
    panel: dict[str, Any],
    model_calc: Any,
    fixture_contract: dict[str, Any],
    checkpoint: PredictionCheckpoint | None = None,
    dft_calculator_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Run the sparse-DFT row over the locked panel and aggregate the verdict."""
    factory = dft_calculator_factory or default_dft_calculator_factory
    predictions: list[dict[str, Any]] = []
    for case_index, path in enumerate(panel["paths"]):
        cached = (
            checkpoint.get_prediction(SPARSE_DFT_ROW_ID, case_index, path)
            if checkpoint
            else None
        )
        if cached is not None:
            predictions.append(cached)
            continue
        try:
            prediction = run_sparse_dft_path(path, model_calc, factory)
        except Exception as exc:
            prediction = {
                "path_id": path.get("path_id"),
                "material_id": path.get("material_id"),
                "chemical_system": path.get("chemical_system"),
                "status": "failed",
                "reference_barrier_ev": path.get("reference_barrier_ev"),
                "error_class": exc.__class__.__name__,
                "error": str(exc),
            }
        else:
            if checkpoint is not None:
                checkpoint.record_prediction(
                    SPARSE_DFT_ROW_ID, case_index, path, prediction
                )
        predictions.append(prediction)

    completed = [p for p in predictions if p["status"] == "completed"]
    failed_count = len(predictions) - len(completed)
    minimum_path_count = int(panel["measurement"]["minimum_path_count"])
    measurement_complete = len(completed) >= minimum_path_count and failed_count == 0

    mae_mev = _mean_mev([p["absolute_error_mev"] for p in completed])
    anchor_counts = [p["anchor_count"] for p in completed]
    median_anchors = float(statistics.median(anchor_counts)) if anchor_counts else None
    max_anchors = max(anchor_counts) if anchor_counts else None
    anchor_budget_met = max_anchors is not None and max_anchors <= ANCHOR_BUDGET_PER_PATH
    cost_claim_met = (
        median_anchors is not None and median_anchors <= COST_CLAIM_MEDIAN_ANCHORS
    )

    # Saddle-location guidance quality (kill-condition line item).
    exact = [p for p in completed if p["saddle_index_agreement"]]
    within_1 = [p for p in completed if p["saddle_index_distance"] <= 1]
    saddle_exact_fraction = len(exact) / len(completed) if completed else None
    saddle_within_1_fraction = len(within_1) / len(completed) if completed else None
    saddle_error_rate = (
        1.0 - saddle_exact_fraction if saddle_exact_fraction is not None else None
    )

    # GPAW-vs-VASP convention offset, reported as its own line item (never
    # absorbed into the barrier comparison).
    offsets = [a["offset_mev"] for p in completed for a in p["anchors"]]
    offset_mean_mev = _mean_mev(offsets)
    offset_mae_mev = _mean_mev([abs(v) for v in offsets])

    # Per-family breakdown with the score_z1r5_correction classifier logic.
    families: dict[str, list[float]] = {}
    for prediction in completed:
        families.setdefault(prediction["family"], []).append(
            prediction["absolute_error_mev"]
        )
    family_report = {
        family: {
            "path_count": len(errors),
            "mae_mev": _mean_mev(errors),
        }
        for family, errors in sorted(families.items())
    }

    win = (
        measurement_complete
        and anchor_budget_met
        and mae_mev is not None
        and mae_mev <= WIN_THRESHOLD_MEV
    )
    strong_win = (
        measurement_complete
        and anchor_budget_met
        and mae_mev is not None
        and mae_mev <= STRONG_WIN_THRESHOLD_MEV
    )
    if not measurement_complete:
        verdict = "incomplete"
    elif strong_win:
        verdict = "strong_win"
    elif win:
        verdict = "win"
    else:
        verdict = "loss"

    threshold_mev = float(manifest["acceptance_test"]["threshold"])
    score = (
        max(0.0, min(1.0, 1.0 - mae_mev / max(threshold_mev, 1e-12)))
        if measurement_complete and mae_mev is not None
        else 0.0
    )

    metrics = {
        "primary_metric": "sparse_barrier_mae_mev",
        "sparse_barrier_mae_mev": mae_mev,
        "completed_path_count": len(completed),
        "failed_path_count": failed_count,
        "minimum_path_count": minimum_path_count,
        "measurement_complete": measurement_complete,
        "win_threshold_mev": WIN_THRESHOLD_MEV,
        "strong_win_threshold_mev": STRONG_WIN_THRESHOLD_MEV,
        "win": win,
        "strong_win": strong_win,
        "verdict": verdict,
        "anchor_budget_per_path": ANCHOR_BUDGET_PER_PATH,
        "anchor_budget_met": anchor_budget_met,
        "median_anchors_per_path": median_anchors,
        "max_anchors_per_path": max_anchors,
        "cost_claim_median_anchors_lte": COST_CLAIM_MEDIAN_ANCHORS,
        "cost_claim_met": cost_claim_met,
        "total_dft_evaluations": sum(anchor_counts),
        "saddle_location_exact_fraction": saddle_exact_fraction,
        "saddle_location_within_1_fraction": saddle_within_1_fraction,
        "saddle_location_error_rate": saddle_error_rate,
        "saddle_location_error_rate_gt_15pct": (
            saddle_error_rate is not None
            and saddle_error_rate > SADDLE_LOCATION_ERROR_PROMINENCE_RATE
        ),
        "gpaw_reference_offset_mean_mev": offset_mean_mev,
        "gpaw_reference_offset_mae_mev": offset_mae_mev,
        "families": family_report,
        "acceptance_threshold_mev": threshold_mev,
    }
    gpaw_params = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in FROZEN_GPAW_PARAMS.items()
    }
    return {
        "predictions": predictions,
        "score": score,
        "score_unit": "row_native_physical_score",
        "metrics": metrics,
        "row_spec": {
            "row_id": SPARSE_DFT_ROW_ID,
            "campaign_id": CAMPAIGN_ID,
            "preregistration": PREREGISTRATION,
            "anchor_protocol": {
                "anchors": "{model-min, model-max +/- window} + both endpoints",
                "window": 1,
                "short_path_fallback": {
                    "image_count_lte": SHORT_PATH_IMAGE_THRESHOLD,
                    "window": 2,
                    "declared": True,
                },
                "clamped_to_path": True,
            },
            "guide": {
                "model_role": "single-point energies over input images; no relaxation, no NEB",
            },
            "dft": {
                "engine": "gpaw",
                "parameters": gpaw_params,
                "evaluation": "single-point energies at anchor images only",
            },
            "measurement": {
                "sparse_barrier_definition": "max(anchor_energy_ev) - min(anchor_energy_ev)",
                "reference": "locked panel reference_barrier_ev and reference.energies_ev",
                "failure_policy": "record failure without imputation",
            },
        },
        "fixture_contract": fixture_contract,
        "n_structures": len(panel["paths"]),
    }
