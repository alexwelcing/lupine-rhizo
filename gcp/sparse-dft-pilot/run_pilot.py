#!/usr/bin/env python3
"""Sparse-DFT pilot driver: model guidance comes from the recorded Round-4
float64 artifacts — no model re-evaluation, no GPU needed.

Per path: read the model's predicted image energies from the R4 cell_result
artifact, select extrema, build the frozen anchor set (z1_sparse_dft),
evaluate GPAW at the anchors, and emit the per-path record + aggregate
verdicts per docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
for _candidate in (_HERE.parent, _HERE.parents[1] / "mlip-cell-runner"):
    if (_candidate / "z1_sparse_dft.py").exists():
        sys.path.insert(0, str(_candidate))
        break

from z1_sparse_dft import (  # noqa: E402
    FROZEN_GPAW_PARAMS,
    build_anchor_set,
    select_extrema,
)
from z1_barrier import atoms_from_image  # noqa: E402

GCS_PANEL = "gs://shed-489901-atlas-inputs/z1/data/candidates/z1_nebdft2k_barriers.lock.json"
GCS_RESULT = "gs://shed-489901-atlas-outputs/z1/campaign-float64/{model}/cell_result.json"
PROJECT = "shed-489901"


def gcloud_cp(uri: str, dest: Path) -> None:
    """Download a gs:// object using ADC (the job's service account)."""
    from google.cloud import storage

    bucket_name, _, blob_name = uri.removeprefix("gs://").partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"not a gs:// URI: {uri}")
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(str(dest))


def gcs_upload(local: Path, uri: str) -> None:
    from google.cloud import storage

    bucket_name, _, blob_name = uri.removeprefix("gs://").partition("/")
    if not bucket_name or not blob_name:
        raise ValueError(f"not a gs:// URI: {uri}")
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).upload_from_filename(str(local))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def guided_paths(panel: dict, artifact: dict) -> list[dict]:
    by_id = {p["path_id"]: p for p in panel["paths"]}
    out = []
    for pred in artifact.get("predictions", []):
        path = by_id.get(pred.get("path_id"))
        if path is None:
            continue
        energies = pred.get("predicted_image_energies_ev")
        if pred.get("status") == "completed" and isinstance(energies, list) and all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in energies
        ):
            out.append({"path": path, "model_energies": [float(v) for v in energies]})
    return out


def gpaw_energy(record: dict) -> float:
    from gpaw import GPAW

    atoms = atoms_from_image(record)
    atoms.calc = GPAW(**FROZEN_GPAW_PARAMS)
    energy = float(atoms.get_potential_energy())
    if not math.isfinite(energy):
        raise RuntimeError("GPAW produced a non-finite energy")
    return energy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mlip-id", required=True)
    parser.add_argument("--paths", help="0-based path indices to run, e.g. '0-29' or '3'")
    parser.add_argument("--out", required=True, help="output JSONL path (local or gs://)")
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/sparse-dft-pilot"))
    args = parser.parse_args()

    workdir = args.workdir / args.mlip_id
    workdir.mkdir(parents=True, exist_ok=True)
    gcloud_cp(GCS_PANEL, workdir / "panel.lock.json")
    gcloud_cp(GCS_RESULT.format(model=args.mlip_id), workdir / "cell_result.json")
    panel = load_json(workdir / "panel.lock.json")
    artifact = load_json(workdir / "cell_result.json")

    items = guided_paths(panel, artifact)
    if args.paths:
        if "-" in args.paths:
            lo, hi = (int(x) for x in args.paths.split("-"))
            wanted = set(range(lo, hi + 1))
        else:
            wanted = {int(x) for x in args.paths.split(",")}
        items = [item for idx, item in enumerate(items) if idx in wanted]
    if not items:
        raise SystemExit(f"no completed paths to run for {args.mlip_id}")

    rows = []
    failures = []
    for item in items:
        path = item["path"]
        images = path["input_images"]
        model_energies = item["model_energies"]
        model_min, model_max = select_extrema(model_energies)
        anchor = build_anchor_set(len(images), model_min, model_max)
        reference = path["reference"]["energies_ev"]
        started = time.time()
        try:
            anchors = []
            for index in anchor["anchor_indices"]:
                energy = gpaw_energy(images[index])
                anchors.append({
                    "index": index,
                    "gpaw_energy_ev": energy,
                    "reference_energy_ev": float(reference[index]),
                    "offset_ev": energy - float(reference[index]),
                })
            sparse = max(a["gpaw_energy_ev"] for a in anchors) - min(a["gpaw_energy_ev"] for a in anchors)
            ref_barrier = float(path["reference_barrier_ev"])
            rows.append({
                "path_id": path["path_id"],
                "chemical_system": path["chemical_system"],
                "status": "completed",
                "model_min_index": model_min,
                "model_max_index": model_max,
                "window": anchor["window"],
                "short_path_fallback": anchor["short_path_fallback"],
                "anchor_count": len(anchors),
                "anchors": anchors,
                "sparse_barrier_ev": sparse,
                "reference_barrier_ev": ref_barrier,
                "signed_error_ev": sparse - ref_barrier,
                "absolute_error_ev": abs(sparse - ref_barrier),
                "wall_seconds": round(time.time() - started, 1),
            })
        except Exception as error:  # noqa: BLE001 — failures recorded, never imputed
            failures.append({
                "path_id": path["path_id"],
                "status": "failed",
                "error_class": error.__class__.__name__,
                "error": str(error),
                "wall_seconds": round(time.time() - started, 1),
            })
            print(f"FAILED {path['path_id']}: {error}", file=sys.stderr, flush=True)

    completed = [r for r in rows if r["status"] == "completed"]
    mae = sum(r["absolute_error_ev"] for r in completed) / len(completed) if completed else None
    summary = {
        "mlip_id": args.mlip_id,
        "paths_completed": len(completed),
        "paths_failed": len(failures),
        "sparse_mae_ev": mae,
        "win": (mae is not None and not failures and mae <= 0.040),
        "strong_win": (mae is not None and not failures and mae <= 0.015),
        "median_anchor_count": sorted(r["anchor_count"] for r in completed)[len(completed) // 2] if completed else None,
        "gpaw_params": FROZEN_GPAW_PARAMS,
        "rows_sha256": None,
    }
    payload = json.dumps({"summary": summary, "rows": rows, "failures": failures},
                         indent=1, sort_keys=True) + "\n"
    summary["rows_sha256"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    payload = json.dumps({"summary": summary, "rows": rows, "failures": failures},
                         indent=1, sort_keys=True) + "\n"
    if args.out.startswith("gs://"):
        tmp = workdir / "pilot-results.json"
        tmp.write_text(payload, encoding="utf-8")
        gcs_upload(tmp, args.out)
    else:
        Path(args.out).write_text(payload, encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
