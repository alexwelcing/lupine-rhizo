#!/usr/bin/env python3
"""Union-anchor economics for the Z1 sparse-DFT pilot (cross-model analysis).

Recomputes, from the recorded Round-4 float64 campaign artifacts, how many DFT
evaluations the frozen sparse-anchor protocol would consume across the 30-path
locked Z1 panel when each model guides independently ("naive") versus when one
DFT evaluation per unique image index is shared across models ("union").

This is a PREDICTION-side analysis: it uses only the models' recorded energy
profiles (no DFT is run). All 30 panel paths are in scope, including the seven
large-cell paths deferred from DFT *execution*
(data/candidates/z1-sparse-dft-deferred.json).

Anchor logic is mirrored EXACTLY from the frozen implementation in
gcp/mlip-cell-runner/z1_sparse_dft.py (select_extrema / build_anchor_set),
per docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md:
  anchors = {0, n-1, model-min} ∪ {model-max-window .. model-max+window},
  window = 2 when n <= 6 else 1, clamped to [0, n) and de-duplicated.

Usage:
  # download fresh from GCS (gsutil on PATH, or google-cloud-storage installed)
  python tools/analysis/union_anchor_economics.py \
      --out data/candidates/z1-union-anchor-economics.json

  # offline: read panel.lock.json + <model>/cell_result.json from a directory
  python tools/analysis/union_anchor_economics.py --local /tmp/z1-union-anchor \
      --out data/candidates/z1-union-anchor-economics.json
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "lupine.z1.union_anchor_economics.v1"
PREREGISTRATION = "docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md"
ANCHOR_SOURCE = "gcp/mlip-cell-runner/z1_sparse_dft.py"
DEFERRED_JSON = "data/candidates/z1-sparse-dft-deferred.json"

GCS_PANEL = "gs://shed-489901-atlas-inputs/z1/data/candidates/z1_nebdft2k_barriers.lock.json"
GCS_RESULT = "gs://shed-489901-atlas-outputs/z1/campaign-float64/{model}/cell_result.json"

# Model directory names under gs://shed-489901-atlas-outputs/z1/campaign-float64/
# (verified with `gsutil ls` 2026-07-21). Fixed order doubles as the cumulative
# order for the scaling curve.
MODELS = ["chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium"]

# Frozen anchor rule constant (z1_sparse_dft.SHORT_PATH_IMAGE_THRESHOLD).
SHORT_PATH_IMAGE_THRESHOLD = 6


# --- Frozen protocol logic, mirrored from z1_sparse_dft.py -------------------
# Keep these three functions byte-equivalent in behavior to the frozen source;
# they are duplicated here so the analysis runs without the runner's deps.

def select_extrema(energies: list[float]) -> tuple[int, int]:
    """(min_index, max_index) with deterministic first-occurrence tie-break."""
    if not energies:
        raise ValueError("cannot select extrema of an empty energy profile")
    min_index = min(range(len(energies)), key=lambda i: (energies[i], i))
    max_index = max(range(len(energies)), key=lambda i: (energies[i], -i))
    return min_index, max_index


def build_anchor_set(image_count: int, model_min_index: int, model_max_index) -> dict:
    """Frozen anchor set: endpoints + model-min + (model-max ± window)."""
    if image_count < 3:
        raise ValueError(f"a path needs at least 3 images; got {image_count}")
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


def completed_profile(prediction: dict) -> list[float] | None:
    """Mirror of run_pilot.guided_paths: completed + finite energy list only."""
    energies = prediction.get("predicted_image_energies_ev")
    if prediction.get("status") != "completed":
        return None
    if not isinstance(energies, list) or not all(
        isinstance(v, (int, float)) and math.isfinite(v) for v in energies
    ):
        return None
    return [float(v) for v in energies]


# --- Input loading -------------------------------------------------------------

def download(uri: str, dest: Path) -> None:
    """Fetch a gs:// object via google-cloud-storage when importable, else gsutil."""
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        gsutil = shutil.which("gsutil")
        if gsutil is None:
            raise RuntimeError(
                "neither google-cloud-storage nor gsutil is available; "
                "use --local with pre-downloaded artifacts"
            )
        subprocess.run([gsutil, "cp", uri, str(dest)], check=True)
        return
    bucket_name, _, blob_name = uri.removeprefix("gs://").partition("/")
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(str(dest))


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs(local_dir: Path | None) -> tuple[dict, dict[str, dict], dict[str, str]]:
    """Return (panel, {model: cell_result}, {label: source sha256})."""
    if local_dir is not None:
        root = local_dir
        panel_path = root / "panel.lock.json"
        result_paths = {m: root / m / "cell_result.json" for m in MODELS}
    else:
        root = Path(tempfile.mkdtemp(prefix="z1-union-anchor-"))
        panel_path = root / "panel.lock.json"
        download(GCS_PANEL, panel_path)
        result_paths = {}
        for model in MODELS:
            dest = root / model / "cell_result.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            download(GCS_RESULT.format(model=model), dest)
            result_paths[model] = dest
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    artifacts = {
        m: json.loads(p.read_text(encoding="utf-8")) for m, p in result_paths.items()
    }
    hashes = {"panel": sha256_file(panel_path)}
    hashes.update({f"cell_result/{m}": sha256_file(p) for m, p in result_paths.items()})
    return panel, artifacts, hashes


# --- Analysis -------------------------------------------------------------------

def analyze(panel: dict, artifacts: dict[str, dict]) -> dict:
    paths = panel["paths"]
    by_id = {p["path_id"]: i for i, p in enumerate(paths)}
    panel_size = len(paths)

    # Per (model, path): frozen anchor set from the model's recorded profile.
    per_pair: dict[tuple[str, int], dict] = {}
    missing: dict[int, dict[str, dict]] = {i: {} for i in range(panel_size)}
    for model in MODELS:
        for prediction in artifacts[model].get("predictions", []):
            path_id = prediction.get("path_id")
            index = by_id.get(path_id)
            if index is None:
                continue
            profile = completed_profile(prediction)
            if profile is None:
                missing[index][model] = {
                    "status": prediction.get("status"),
                    "error_class": prediction.get("error_class"),
                    "error": prediction.get("error"),
                }
                continue
            image_count = len(paths[index]["input_images"])
            if len(profile) != image_count:
                missing[index][model] = {
                    "status": "profile_length_mismatch",
                    "error": (
                        f"predicted_image_energies_ev has {len(profile)} values "
                        f"for a path of {image_count} images"
                    ),
                }
                continue
            model_min, model_max = select_extrema(profile)
            anchor = build_anchor_set(image_count, model_min, model_max)
            per_pair[(model, index)] = {
                "model_min_index": model_min,
                "model_max_index": model_max,
                "window": anchor["window"],
                "short_path_fallback": anchor["short_path_fallback"],
                "anchor_indices": anchor["anchor_indices"],
                "anchor_count": len(anchor["anchor_indices"]),
            }

    analyzable = [i for i in range(panel_size) if any((m, i) in per_pair for m in MODELS)]
    fully_covered = [i for i in range(panel_size) if all((m, i) in per_pair for m in MODELS)]
    excluded = [i for i in range(panel_size) if i not in analyzable]

    def economics(pathset: list[int], models: list[str]) -> dict:
        naive = 0
        union = 0
        for i in pathset:
            sets = []
            for m in models:
                pair = per_pair.get((m, i))
                if pair is None:
                    continue
                naive += pair["anchor_count"]
                sets.append(set(pair["anchor_indices"]))
            if sets:
                union += len(set.union(*sets))
        saving = (1.0 - union / naive) if naive else None
        return {
            "path_count": len(pathset),
            "model_path_pairs": sum(
                1 for i in pathset for m in models if (m, i) in per_pair
            ),
            "naive_dft_evaluations": naive,
            "union_dft_evaluations": union,
            "evaluations_saved": naive - union,
            "saving_fraction": saving,
            "saving_percent": (100.0 * saving) if saving is not None else None,
            "naive_over_union_ratio": (naive / union) if union else None,
        }

    def agreements(pathset: list[int]) -> dict:
        """Cross-model extrema agreement, two conventions (see JSON notes)."""
        stats = {
            k: {"available_models": 0, "all_four_required": 0}
            for k in (
                "saddle_exact",
                "saddle_within_1",
                "both_extrema_exact",
                "both_extrema_within_1",
            )
        }
        for i in pathset:
            present = [m for m in MODELS if (m, i) in per_pair]
            maxima = [per_pair[(m, i)]["model_max_index"] for m in present]
            minima = [per_pair[(m, i)]["model_min_index"] for m in present]
            checks = {
                "saddle_exact": len(set(maxima)) == 1,
                "saddle_within_1": max(maxima) - min(maxima) <= 1,
                "both_extrema_exact": len(set(maxima)) == 1 and len(set(minima)) == 1,
                "both_extrema_within_1": (
                    max(maxima) - min(maxima) <= 1 and max(minima) - min(minima) <= 1
                ),
            }
            for name, ok in checks.items():
                if ok:
                    stats[name]["available_models"] += 1
                    if len(present) == len(MODELS):
                        stats[name]["all_four_required"] += 1
        return stats

    # Per-path records.
    per_path = []
    for i, path in enumerate(paths):
        present = [m for m in MODELS if (m, i) in per_pair]
        union_set: set[int] = set()
        for m in present:
            union_set.update(per_pair[(m, i)]["anchor_indices"])
        per_path.append({
            "path_index": i,
            "path_id": path["path_id"],
            "chemical_system": path.get("chemical_system"),
            "image_count": len(path["input_images"]),
            "models_present": present,
            "models_missing": sorted(missing[i]),
            "per_model": {
                m: per_pair[(m, i)] for m in present
            },
            "naive_anchor_count": sum(per_pair[(m, i)]["anchor_count"] for m in present),
            "union_anchor_indices": sorted(union_set),
            "union_anchor_count": len(union_set),
        })

    # Scaling curve: naive/union as models are added.
    scaling_subsets = []
    for k in (1, 2, 3, 4):
        rows = []
        for combo in itertools.combinations(MODELS, k):
            pathset = [i for i in range(panel_size) if any((m, i) in per_pair for m in combo)]
            econ = economics(pathset, list(combo))
            rows.append({"models": list(combo), **econ})
        scaling_subsets.append({
            "model_count": k,
            "subsets": rows,
            "mean_naive_dft_evaluations": sum(r["naive_dft_evaluations"] for r in rows) / len(rows),
            "mean_union_dft_evaluations": sum(r["union_dft_evaluations"] for r in rows) / len(rows),
        })
    scaling_cumulative = []
    for k in (1, 2, 3, 4):
        combo = MODELS[:k]
        pathset = [i for i in range(panel_size) if any((m, i) in per_pair for m in combo)]
        scaling_cumulative.append({"models": combo, **economics(pathset, combo)})

    return {
        "panel_size": panel_size,
        "analyzable_path_indices": analyzable,
        "fully_covered_path_indices": fully_covered,
        "excluded_paths": [
            {
                "path_index": i,
                "path_id": paths[i]["path_id"],
                "reason": "no completed model profile in any of the four artifacts",
                "per_model_failure": missing[i],
            }
            for i in excluded
        ],
        "model_path_pairs_total": len(MODELS) * panel_size,
        "model_path_pairs_present": len(per_pair),
        "missing_pairs": [
            {
                "path_index": i,
                "path_id": paths[i]["path_id"],
                "model": model,
                **info,
            }
            for i in range(panel_size)
            for model, info in sorted(missing[i].items())
        ],
        "per_path": per_path,
        "economics_analyzable_paths": economics(analyzable, MODELS),
        "economics_fully_covered_paths": economics(fully_covered, MODELS),
        "agreement_analyzable_paths": agreements(analyzable),
        "agreement_fully_covered_paths": agreements(fully_covered),
        "scaling_mean_over_subsets": scaling_subsets,
        "scaling_cumulative_fixed_order": scaling_cumulative,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local",
        type=Path,
        help="directory with panel.lock.json and <model>/cell_result.json; skips GCS download",
    )
    parser.add_argument("--out", type=Path, required=True, help="output JSON path")
    parser.add_argument(
        "--deferred",
        type=Path,
        default=Path(DEFERRED_JSON),
        help="deferred-paths record to annotate (paths stay IN the analysis)",
    )
    args = parser.parse_args()

    panel, artifacts, hashes = load_inputs(args.local)
    result = analyze(panel, artifacts)

    deferred_indices: list[int] = []
    if args.deferred.is_file():
        deferred = json.loads(args.deferred.read_text(encoding="utf-8"))
        deferred_indices = [p["index"] for p in deferred.get("deferred_paths", [])]

    output = {
        "schema": SCHEMA,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "analysis": (
            "Cross-model union-anchor economics for the Z1 sparse-DFT pilot, "
            "computed from recorded campaign artifacts only (no DFT run)."
        ),
        "preregistration": PREREGISTRATION,
        "anchor_rule": {
            "source": ANCHOR_SOURCE,
            "definition": (
                "per model per path: {0, n-1, model-min} u "
                "{model-max-window .. model-max+window}, clamped, de-duplicated; "
                f"window = 2 when image_count <= {SHORT_PATH_IMAGE_THRESHOLD} else 1"
            ),
        },
        "definitions": {
            "naive_dft_evaluations": (
                "sum over models of sum over paths of |A(m,p)| — each model pays "
                "its own sparse DFT independently"
            ),
            "union_dft_evaluations": (
                "sum over paths of |union over models A(m,p)| — one DFT evaluation "
                "per unique image index per path, shared across models"
            ),
            "agreement_conventions": {
                "available_models": "agreement among the models with a completed profile on that path",
                "all_four_required": "agreement counted only when all four models have data AND agree",
            },
        },
        "sources": {
            "panel_gs": GCS_PANEL,
            "cell_result_gs_template": GCS_RESULT,
            "models": MODELS,
            "input_sha256": hashes,
        },
        "deferred_from_dft_execution": {
            "record": DEFERRED_JSON,
            "path_indices": deferred_indices,
            "note": (
                "large-cell paths deferred from GPAW execution; they REMAIN in this "
                "cross-model prediction analysis"
            ),
        },
        **result,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(output, indent=1, sort_keys=True) + "\n"
    args.out.write_text(payload, encoding="utf-8")

    econ = result["economics_analyzable_paths"]
    print(json.dumps({
        "analyzable_paths": f"{len(result['analyzable_path_indices'])}/{result['panel_size']}",
        "excluded": [p["path_index"] for p in result["excluded_paths"]],
        "naive": econ["naive_dft_evaluations"],
        "union": econ["union_dft_evaluations"],
        "saving_percent": round(econ["saving_percent"], 1),
        "ratio": round(econ["naive_over_union_ratio"], 2),
        "agreement": result["agreement_analyzable_paths"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
