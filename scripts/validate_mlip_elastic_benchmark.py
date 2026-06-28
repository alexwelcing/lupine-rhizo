#!/usr/bin/env python3
"""Validate lupine.mlip_elastic_benchmark.v1 aggregate results."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ARMS = ["raw-1x1x1", "corrected-1x1x1", "ref-3x3x3", "ensemble-1x1x1"]
REQUIRED_TOP = {"schema_version", "provenance", "arms", "cost_ratios", "per_element", "caveats"}
REQUIRED_ROW = {
    "element",
    "arm",
    "c11",
    "c12",
    "c44",
    "mae",
    "runtime_seconds",
    "runtime_s",
    "n_atoms",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_top = REQUIRED_TOP - set(data)
    if missing_top:
        errors.append(f"missing top-level fields: {sorted(missing_top)}")
    if data.get("schema_version") != "lupine.mlip_elastic_benchmark.v1":
        errors.append("schema_version must equal lupine.mlip_elastic_benchmark.v1")
    arms = data.get("arms", {})
    for arm in ARMS:
        if arm not in arms:
            errors.append(f"missing arm: {arm}")
    if arms.get("corrected-1x1x1", {}).get("bias_method") != "LOO-PCA":
        errors.append("corrected-1x1x1.bias_method must equal LOO-PCA")
    if arms.get("ensemble-1x1x1", {}).get("n_models") != 3:
        errors.append("ensemble-1x1x1.n_models must equal 3")

    rows = data.get("per_element", [])
    if len(rows) != 64:
        errors.append(f"per_element must contain exactly 64 rows, found {len(rows)}")
    for arm in ARMS:
        count = sum(1 for row in rows if row.get("arm") == arm)
        if count != 16:
            errors.append(f"{arm} must contain 16 per-element rows, found {count}")
    for idx, row in enumerate(rows):
        missing = REQUIRED_ROW - set(row)
        if missing:
            errors.append(f"per_element[{idx}] missing fields: {sorted(missing)}")
        if row.get("supercell") == 1 and row.get("runtime_seconds", 999) >= 60:
            errors.append(
                f"{row.get('element')} {row.get('arm')} has non-warm 1x1x1 runtime "
                f"{row.get('runtime_seconds')}"
            )
    if data.get("cost_ratios", {}).get("corrected_vs_ref", 0.0) < 1.0:
        errors.append("cost_ratios.corrected_vs_ref must be >= 1.0")
    if data.get("provenance", {}).get("cache_warm") is not True:
        errors.append("provenance.cache_warm must be true")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="data/mlip elastic benchmark/mlip_elastic_benchmark_results.json",
        help="Path to mlip_elastic_benchmark_results.json",
    )
    args = parser.parse_args()
    data = load(Path(args.path))
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "OK lupine.mlip_elastic_benchmark.v1: "
        f"{len(data['per_element'])} per-element rows, "
        f"corrected_vs_ref={data['cost_ratios']['corrected_vs_ref']}x, "
        f"corrected_vs_ensemble={data['cost_ratios']['corrected_vs_ensemble']}x"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
