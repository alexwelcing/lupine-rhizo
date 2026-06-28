#!/usr/bin/env python3
"""Fill placeholder keys in mlip elastic benchmark preprint + funder brief from results JSON.

Usage:
    python fill_benchmark_placeholders.py \
        --results /home/alex/Dev/lupine/lupine-mlip-benchmark/results/mlip_elastic_benchmark_results.json \
        --preprint mlip-elastic-benchmark-preprint-2026-06-27.md \
        --brief mlip-elastic-benchmark-funder-brief-2026-06-27.md
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ELEMENTS = [
    "Ag", "Al", "Au", "Ca", "Cr", "Cu", "Fe", "Mo",
    "Nb", "Ni", "Pd", "Pt", "Sr", "Ta", "V", "W",
]


def load_results(path: Path) -> dict:
    return json.loads(path.read_text())


def build_replacements(results: dict) -> dict[str, str]:
    arms = results["arms"]
    ratios = results["cost_ratios"]

    def fmt_mae(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.2f}"

    def fmt_cost(value: float | None) -> str:
        if value is None:
            return "N/A"
        # Use 4 significant digits for small core-hour numbers.
        return f"{value:.4g}"

    repl = {
        # Preprint aggregate placeholders
        "PLACEHOLDER_MAE_RAW_1X1X1_GPA": fmt_mae(arms["raw-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_RAW_1X1X1": fmt_cost(arms["raw-1x1x1"]["core_hours"]),
        "PLACEHOLDER_MAE_CORRECTED_1X1X1_GPA": fmt_mae(arms["corrected-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_CORRECTED_1X1X1": fmt_cost(arms["corrected-1x1x1"]["core_hours"]),
        "PLACEHOLDER_MAE_REF_3X3X3_GPA": fmt_mae(arms["ref-3x3x3"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_REF_3X3X3": fmt_cost(arms["ref-3x3x3"]["core_hours"]),
        "PLACEHOLDER_MAE_ENSEMBLE_1X1X1_GPA": fmt_mae(arms["ensemble-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_ENSEMBLE_1X1X1": fmt_cost(arms["ensemble-1x1x1"]["core_hours"]),
        "PLACEHOLDER_COST_RATIO_CORRECTED_VS_REF": f"{ratios.get('corrected_vs_ref', 0):.1f}",
        "PLACEHOLDER_COST_RATIO_CORRECTED_VS_ENSEMBLE": f"{ratios.get('corrected_vs_ensemble', 0):.1f}",
        # Funder-brief style placeholders
        "PLACEHOLDER_MAE_RAW": fmt_mae(arms["raw-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_RAW": fmt_cost(arms["raw-1x1x1"]["core_hours"]),
        "PLACEHOLDER_MAE_CORRECTED": fmt_mae(arms["corrected-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_CORRECTED": fmt_cost(arms["corrected-1x1x1"]["core_hours"]),
        "PLACEHOLDER_MAE_REF": fmt_mae(arms["ref-3x3x3"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_REF": fmt_cost(arms["ref-3x3x3"]["core_hours"]),
        "PLACEHOLDER_MAE_ENSEMBLE": fmt_mae(arms["ensemble-1x1x1"]["mae_cij"]),
        "PLACEHOLDER_COREHOURS_ENSEMBLE": fmt_cost(arms["ensemble-1x1x1"]["core_hours"]),
        "PLACEHOLDER_COST_RATIO_REF": f"{ratios.get('corrected_vs_ref', 0):.1f}",
        "PLACEHOLDER_COST_RATIO_ENSEMBLE": f"{ratios.get('corrected_vs_ensemble', 0):.1f}",
    }

    # Accuracy ratios (B/A and B/C etc.) — guard against zero/None.
    def ratio(a: float | None, b: float | None) -> str:
        if a is None or b is None or b == 0:
            return "N/A"
        return f"{a / b:.2f}"

    repl["PLACEHOLDER_ACCURACY_RATIO_CORRECTED_VS_REF"] = ratio(
        arms["corrected-1x1x1"]["mae_cij"], arms["ref-3x3x3"]["mae_cij"]
    )
    repl["PLACEHOLDER_ACCURACY_RATIO_CORRECTED_VS_ENSEMBLE"] = ratio(
        arms["corrected-1x1x1"]["mae_cij"], arms["ensemble-1x1x1"]["mae_cij"]
    )

    # Per-element MAE placeholders.
    by_element_arm: dict[tuple[str, str], float] = {}
    for row in results.get("per_element", []):
        key = (row["element"], row["arm"])
        by_element_arm[key] = row["mae"]

    arm_label_map = {
        "RAW_1X1X1": "raw-1x1x1",
        "CORRECTED_1X1X1": "corrected-1x1x1",
        "REF_3X3X3": "ref-3x3x3",
        "ENSEMBLE_1X1X1": "ensemble-1x1x1",
    }
    for arm_label, arm_key in arm_label_map.items():
        for e in ELEMENTS:
            key = f"PLACEHOLDER_MAE_{arm_label}_{e.upper()}_GPA"
            repl[key] = fmt_mae(by_element_arm.get((e, arm_key)))

    return repl


def fill_file(path: Path, repl: dict[str, str]) -> int:
    text = path.read_text()
    original = text
    for key, value in repl.items():
        text = text.replace(key, value)
    # Warn about any remaining PLACEHOLDER_ tokens.
    remaining = set(re.findall(r"PLACEHOLDER_[A-Z_0-9]+", text))
    if remaining:
        print(f"WARNING: {path} still has {len(remaining)} unfilled placeholders: {sorted(remaining)[:5]}")
    if text != original:
        path.write_text(text)
        print(f"Updated {path}")
    else:
        print(f"No placeholders replaced in {path}")
    return len(remaining)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--preprint", default="mlip-elastic-benchmark-preprint-2026-06-27.md", type=Path)
    parser.add_argument("--brief", default="mlip-elastic-benchmark-funder-brief-2026-06-27.md", type=Path)
    args = parser.parse_args()

    results = load_results(args.results)
    repl = build_replacements(results)
    total_remaining = 0
    for path in [args.preprint, args.brief]:
        if path.exists():
            total_remaining += fill_file(path, repl)
        else:
            print(f"Skipping {path}: not found")
    return 1 if total_remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())
