#!/usr/bin/env python3
"""Build and verify the hash-locked data/figure bundle for the negative-results paper."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("SOURCE_DATE_EPOCH", "1785733200")  # 2026-08-03 01:00:00 UTC

PAPER_DIR = Path(__file__).resolve().parent
REPO_ROOT = PAPER_DIR.parents[1]
EXPECTED = {
    "campaigns/v1/z1.campaign-manifest.v1.json": "579d72125c53597750cc6ee9ce01e87ce1a0d3dda5e5a6fe72009abc62d943f6",
    "campaigns/v1/z3.campaign-manifest.v1.json": "2b624c9258e0d6ec0a22cb936bf5d63de592a171b0dc8aa99573f66906006f43",
    "data/candidates/z1_nebdft2k_barriers.lock.json": "192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
    "data/candidates/z1/measurements.jsonl": "09d510615138c98653ed4a621b9986b2e4d6cff097024b597309d250a26239ca",
    "data/candidates/z1/f64/measurements.jsonl": "550fc6b12c8b34837b552e5e7aa282c35b21893e58d901670c06623c48e82c55",
    "data/candidates/z3_catbench_bm_adsorption.lock.json": "b434de005e5da46e33e3275ffc8bec2d251b8a52438c1cfe7d6f4f3d8dbb41f4",
    "data/candidates/z3_catbench_bm_delta_splits.lock.json": "00f3b4c80378f271021e2f2c44b93e8b856aeb2b93980cba0490e6d08afe4dbc",
    "data/candidates/z3/delta-correction-report.json": "95c4fd245fa3e14ca80ff85fff235ce8f58f43dffce996fbf9bd3254adbf838f",
    "data/candidates/z3/source/z3-candidate-measurements.json": "d100d09defa3d7dd0395d3a28de8d80389b753646fbde743efeb115c1cf2914e",
    "paper/negative-results-preprint/global-operator.lock.json": "4450ea8ffb4cfbc075d761e7f54f06fbcff16c73d1866b0026369415d43a5e4b",
}
EXPECTED_Z3_CANDIDATES = 32


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def verify_inputs() -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in EXPECTED.items():
        path = REPO_ROOT / relative
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"digest mismatch: {relative}: expected {expected}, got {actual}")
        observed[relative] = actual
    return observed


def z1_rows(chain: str) -> list[dict[str, Any]]:
    root = REPO_ROOT / "data/candidates/z1" / chain / "raw" if chain else REPO_ROOT / "data/candidates/z1/raw"
    rows = []
    for path in sorted(root.glob("*/cell_result.json")):
        result = read_json(path)
        signed = [
            float(row["signed_error_mev"])
            for row in result["predictions"]
            if row["status"] == "completed"
        ]
        rows.append(
            {
                "model": result["mlip_id"],
                "mae_mev": float(result["accuracy"]["barrier_mae_mev"]),
                "completed_paths": len(signed),
                "failed_paths": int(result["accuracy"]["failed_path_count"]),
                "negative_signed_errors": sum(value < 0 for value in signed),
                "positive_signed_errors": sum(value > 0 for value in signed),
                "mean_signed_error_mev": sum(signed) / len(signed),
                "minimum_signed_error_mev": min(signed),
                "maximum_signed_error_mev": max(signed),
            }
        )
    return rows


def validate_z3_completion(raw: dict[str, Any], expected_models: set[str]) -> tuple[int, int]:
    if raw.get("schema") != "lupine.z3.candidate_measurements.v1":
        raise ValueError("raw Z3 registry schema is not supported")
    candidates = raw.get("candidates")
    if not isinstance(candidates, list) or raw.get("candidate_count") != EXPECTED_Z3_CANDIDATES:
        raise ValueError(f"raw Z3 registry must declare {EXPECTED_Z3_CANDIDATES} candidates")
    if len(candidates) != EXPECTED_Z3_CANDIDATES:
        raise ValueError(f"raw Z3 registry must contain {EXPECTED_Z3_CANDIDATES} candidates")
    candidate_ids = [candidate.get("candidate_id") for candidate in candidates]
    if len(set(candidate_ids)) != EXPECTED_Z3_CANDIDATES:
        raise ValueError("raw Z3 registry candidate IDs must be unique")

    completed = 0
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        measurements = candidate.get("model_measurements")
        if not isinstance(measurements, list):
            raise ValueError(f"{candidate_id} has no model measurements")
        model_ids = [measurement.get("model_id") for measurement in measurements]
        if len(model_ids) != len(expected_models) or set(model_ids) != expected_models:
            raise ValueError(f"{candidate_id} does not contain the complete model panel")
        for measurement in measurements:
            if measurement.get("candidate_id") != candidate_id:
                raise ValueError(f"candidate mismatch for {candidate_id}/{measurement.get('model_id')}")
            raw_energy = measurement.get("raw_adsorption_energy_ev")
            if not isinstance(raw_energy, (int, float)) or not math.isfinite(raw_energy):
                raise ValueError(f"non-finite raw Z3 energy for {candidate_id}/{measurement['model_id']}")
        completed += len(measurements)

    expected = EXPECTED_Z3_CANDIDATES * len(expected_models)
    if raw.get("model_count") != len(expected_models):
        raise ValueError("raw Z3 registry model_count contradicts the model panel")
    if raw.get("raw_measurement_count") != expected:
        raise ValueError("raw Z3 registry raw_measurement_count contradicts the candidate cells")
    if completed != expected:
        raise ValueError(f"raw Z3 registry contains {completed}/{expected} completed cells")
    return completed, expected


def build_source_data(input_digests: dict[str, str]) -> dict[str, Any]:
    z3 = read_json(REPO_ROOT / "data/candidates/z3/delta-correction-report.json")
    z3_raw = read_json(REPO_ROOT / "data/candidates/z3/source/z3-candidate-measurements.json")
    operator = read_json(PAPER_DIR / "global-operator.lock.json")
    expected_models = set(z3["models"])
    completed_cells, expected_cells = validate_z3_completion(z3_raw, expected_models)
    z3_rows = []
    for model, result in sorted(z3["models"].items()):
        z3_rows.append(
            {
                "model": model,
                "selected_form": result["selected_form"],
                "validation_mae_ev": result["validation_mae_after_correction"],
                "baseline_holdout_mae_ev": result["baseline_test_mae"],
                "corrected_holdout_mae_ev": result["corrected_test_mae"],
                "holdout_rows": len(result["test_rows"]),
            }
        )
    source = {
        "schema": "lupine.negative-results.figure-source.v1",
        "input_sha256": input_digests,
        "z1": {
            "gate_mev": 40.0,
            "float32": z1_rows(""),
            "float64": z1_rows("f64"),
            "claim_guard": (
                "The locked records do not support an all-26-path underprediction claim: "
                "mace-mp-small has 17 negative and 9 positive signed errors in both chains."
            ),
        },
        "z3": {
            "gate_ev": 0.1,
            "candidate_model_cells_completed": completed_cells,
            "candidate_model_cells_expected": expected_cells,
            "model_level_corrections_worse": sum(
                row["corrected_holdout_mae_ev"] > row["baseline_holdout_mae_ev"]
                for row in z3_rows
            ),
            "model_level_corrections_tested": len(z3_rows),
            "models": z3_rows,
        },
        "global_operator": operator,
    }
    return source


def plot(source: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.45), constrained_layout=True)
    blue, orange, red, ink = "#3156a3", "#df8b2f", "#b5453d", "#222222"

    z1 = source["z1"]["float64"]
    labels = [row["model"].replace("mace-", "") for row in z1]
    values = [row["mae_mev"] for row in z1]
    x = range(len(labels))
    axes[0].bar(x, values, color=blue)
    axes[0].axhline(source["z1"]["gate_mev"], color=red, linestyle="--", linewidth=1.2, label="40 meV gate")
    axes[0].set_xticks(list(x), labels, rotation=35, ha="right")
    axes[0].set_ylabel("barrier MAE (meV)")
    axes[0].set_title("a  Z1: every model fails")
    axes[0].legend(frameon=False, fontsize=8)
    for idx, row in enumerate(z1):
        axes[0].text(idx, row["mae_mev"] + 5, f"{row['negative_signed_errors']}/{row['completed_paths']} negative", ha="center", va="bottom", fontsize=6.8, rotation=90)
    axes[0].set_ylim(0, max(values) * 1.33)

    z3 = source["z3"]["models"]
    labels = [row["model"].replace("mace-", "") for row in z3]
    x = list(range(len(labels)))
    width = 0.36
    axes[1].bar([v - width / 2 for v in x], [row["baseline_holdout_mae_ev"] for row in z3], width, color=blue, label="raw")
    axes[1].bar([v + width / 2 for v in x], [row["corrected_holdout_mae_ev"] for row in z3], width, color=orange, label="selected Δ-correction")
    axes[1].axhline(source["z3"]["gate_ev"], color=red, linestyle="--", linewidth=1.2, label="0.1 eV gate")
    axes[1].set_xticks(x, labels, rotation=35, ha="right")
    axes[1].set_ylabel("holdout MAE (eV)")
    axes[1].set_title("b  Z3: correction worsens 4/4")
    axes[1].legend(frameon=False, fontsize=7)

    operator = source["global_operator"]["measurement"]
    axes[2].bar([0, 1], [operator["raw_mae_gpa"], operator["corrected_mae_gpa"]], color=[blue, orange], width=0.62)
    axes[2].set_xticks([0, 1], ["raw", "global\nLOO-PCA"])
    axes[2].set_ylabel(r"elastic $C_{ij}$ MAE (GPa)")
    axes[2].set_title("c  Global operator degrades")
    for idx, value in enumerate([operator["raw_mae_gpa"], operator["corrected_mae_gpa"]]):
        axes[2].text(idx, value + 1.2, f"{value:.2f}", ha="center", color=ink)
    axes[2].set_ylim(0, operator["corrected_mae_gpa"] * 1.15)

    figures = PAPER_DIR / "figures"
    figures.mkdir(exist_ok=True)
    metadata = {
        "Title": "Preregistered negative results in universal MLIP correction",
        "Author": "Lupine Science",
        "Creator": "paper/negative-results-preprint/build_artifacts.py",
        "CreationDate": datetime(2026, 8, 3, tzinfo=timezone.utc),
        "ModDate": datetime(2026, 8, 3, tzinfo=timezone.utc),
    }
    fig.savefig(figures / "negative-results-panels.pdf", metadata=metadata)
    fig.savefig(figures / "negative-results-panels.png", dpi=220, metadata={"Software": metadata["Creator"]})
    plt.close(fig)


def write_outputs(source: dict[str, Any]) -> None:
    source_path = PAPER_DIR / "figure-source-data.json"
    source_path.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    plot(source)
    outputs = [
        PAPER_DIR / "manuscript.tex",
        PAPER_DIR / "references.bib",
        PAPER_DIR / "README.md",
        PAPER_DIR / "build_artifacts.py",
        source_path,
        PAPER_DIR / "figures/negative-results-panels.pdf",
        PAPER_DIR / "figures/negative-results-panels.png",
        PAPER_DIR / "global-operator.lock.json",
    ]
    manifest = {
        "schema": "lupine.negative-results.generated-artifacts.v1",
        "files": [
            {"path": str(path.relative_to(PAPER_DIR)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in outputs
        ],
    }
    manifest_path = PAPER_DIR / "artifact-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (PAPER_DIR / "artifact-manifest.json.sha256").write_text(sha256(manifest_path) + "  artifact-manifest.json\n", encoding="utf-8")


def verify_claims(source: dict[str, Any], manuscript: str | None = None) -> None:
    if manuscript is None:
        manuscript = (PAPER_DIR / "manuscript.tex").read_text(encoding="utf-8")
    z3 = source["z3"]
    operator = source["global_operator"]["measurement"]
    raw_operator_mae = operator["raw_mae_gpa"]
    corrected_operator_mae = operator["corrected_mae_gpa"]
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value)
        for value in (raw_operator_mae, corrected_operator_mae)
    ) or corrected_operator_mae <= raw_operator_mae:
        raise SystemExit("global operator degradation guard changed; manuscript requires review")
    required = [
        "17/26",
        f"{z3['candidate_model_cells_completed']}/{z3['candidate_model_cells_expected']}",
        f"{z3['model_level_corrections_worse']}/{z3['model_level_corrections_tested']}",
        f"{raw_operator_mae:.2f}",
        f"{corrected_operator_mae:.2f}",
        f"from ${raw_operator_mae:.2f}$ to ${corrected_operator_mae:.2f}\\GPa$",
        "$3.4$--$6.1$",
        "not all 26",
        "95c4fd245fa3e14ca80ff85fff235ce8f58f43dffce996fbf9bd3254adbf838f",
    ]
    missing = [text for text in required if text not in manuscript]
    if missing:
        raise SystemExit(f"manuscript claim-lock tokens missing: {missing}")
    small = next(row for row in source["z1"]["float64"] if row["model"] == "mace-mp-small")
    if (small["negative_signed_errors"], small["positive_signed_errors"]) != (17, 9):
        raise SystemExit("Z1 signed-error guard changed; manuscript requires review")
    if not all(row["corrected_holdout_mae_ev"] > row["baseline_holdout_mae_ev"] for row in source["z3"]["models"]):
        raise SystemExit("Z3 model-level worsening guard changed; manuscript requires review")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify and rebuild; fail on any locked-input drift")
    args = parser.parse_args()
    digests = verify_inputs()
    source = build_source_data(digests)
    write_outputs(source)
    verify_claims(source)
    manifest_hash = sha256(PAPER_DIR / "artifact-manifest.json")
    print(f"PASS: {len(EXPECTED)} locked inputs verified; generated artifacts manifest sha256={manifest_hash}")
    if args.check:
        print("PASS: manuscript claim guards verified")


if __name__ == "__main__":
    main()
