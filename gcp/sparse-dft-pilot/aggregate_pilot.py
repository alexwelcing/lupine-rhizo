#!/usr/bin/env python3
"""Aggregate the sparse-DFT pilot fleet results into per-model verdicts + costs."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from google.cloud import storage

ROOT = "shed-489901-atlas-outputs/z1-sparse-dft"
MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
BUCKET = "shed-489901-atlas-outputs"


def list_results(model: str) -> list[dict]:
    client = storage.Client()
    prefix = f"z1-sparse-dft/{model}/path-"
    out = []
    for blob in client.bucket(BUCKET).list_blobs(prefix=prefix):
        out.append(json.loads(blob.download_as_text()))
    return out


def aggregate(model: str, results: list[dict]) -> dict:
    rows = [r for res in results for r in res.get("rows", [])]
    failures = [f for res in results for f in res.get("failures", [])]
    completed = [r for r in rows if r.get("status") == "completed"]
    mae = statistics.mean(r["absolute_error_ev"] for r in completed) if completed else None
    wall = sum(r.get("wall_seconds", 0.0) for r in completed) + sum(f.get("wall_seconds", 0.0) for f in failures)
    anchors = sum(r.get("anchor_count", 0) for r in completed)
    return {
        "mlip_id": model,
        "result_files": len(results),
        "paths_completed": len(completed),
        "paths_failed": len(failures),
        "sparse_mae_mev": (mae * 1000) if mae is not None else None,
        "win": bool(mae is not None and not failures and mae <= 0.040),
        "strong_win": bool(mae is not None and not failures and mae <= 0.015),
        "anchors_total": anchors,
        "wall_hours": round(wall / 3600, 2),
        "vcpu_hours": round(wall * 4 / 3600, 2),
        "est_cost_usd_at_0p06_per_vcpu_hr": round(wall * 4 / 3600 * 0.06, 2),
        "rows": rows,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = {"models": {}}
    for model in MODELS:
        results = list_results(model)
        report["models"][model] = aggregate(model, results)
        s = report["models"][model]
        print(f"{model:18s} files {s['result_files']:3d} | completed {s['paths_completed']:2d} | "
              f"MAE {s['sparse_mae_mev'] if s['sparse_mae_mev'] is None else round(s['sparse_mae_mev'], 1)} meV | "
              f"win {s['win']} strong {s['strong_win']} | {s['vcpu_hours']} vCPU-h ~${s['est_cost_usd_at_0p06_per_vcpu_hr']}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
