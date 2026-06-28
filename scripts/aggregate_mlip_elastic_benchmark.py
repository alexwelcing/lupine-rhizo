#!/usr/bin/env python3
"""Aggregate mlip elastic benchmark benchmark case JSONs into lupine.mlip_elastic_benchmark.v1 results."""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ELEMENTS = "Ag Al Au Ca Cr Cu Fe Mo Nb Ni Pd Pt Sr Ta V W".split()
MODELS = {
    "M3GNet": "M3GNet-PES-MatPES-PBE-2025.2",
    "CHGNet": "CHGNet-PES-MatPES-PBE-2025.2.10",
    "TensorNet": "TensorNet-PES-MatPES-PBE-2025.2",
}
ARM_RAW = "raw-1x1x1"
ARM_CORRECTED = "corrected-1x1x1"
ARM_REF = "ref-3x3x3"
ARM_ENSEMBLE = "ensemble-1x1x1"

ROOT = Path(__file__).resolve().parents[1]
LUPINE_ROOT = ROOT.parent / "lupine"
LUPINE_PYTHON = LUPINE_ROOT / "python"
INPUT_1X1 = LUPINE_ROOT / "data" / "mlip_elastic_benchmark_outputs_1x1x1_16elem"
INPUT_3X3_16 = LUPINE_ROOT / "data" / "layer2_outputs_3x3x3_16elem"
INPUT_3X3_CUNI = LUPINE_ROOT / "data" / "layer2_outputs_3x3x3"
TARGETS = LUPINE_ROOT / "data" / "targets_0K.json"
OUTPUT = ROOT / "data" / "mlip elastic benchmark" / "mlip_elastic_benchmark_results.json"

if str(LUPINE_PYTHON) not in sys.path:
    sys.path.insert(0, str(LUPINE_PYTHON))

from lupine.operator import correct, leave_one_out_calibration  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def git_sha(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def vec(record: dict[str, Any]) -> np.ndarray:
    return np.array([record["c11"], record["c12"], record["c44"]], dtype=float)


def target_vec(targets: dict[str, Any], element: str, field: str = "TPBE_0K") -> np.ndarray:
    return np.array(targets["elements"][element][field], dtype=float)


def mae(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(np.mean(np.abs(prediction - target)))


def loo_bias(raw_by_element: dict[str, dict[str, Any]], targets: dict[str, Any], holdout: str) -> np.ndarray:
    errors = []
    for element in ELEMENTS:
        if element == holdout:
            continue
        errors.append(vec(raw_by_element[element]) - target_vec(targets, element))
    matrix = np.asarray(errors, dtype=float)
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    if not np.isfinite(centered).all() or np.allclose(centered, 0):
        return matrix.mean(axis=0)
    _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    # First principal score vector in Cij space, with sign anchored to mean error
    # so that correction subtracts the dominant signed bias, not an arbitrary SVD sign.
    bias = vh[0] * singular_values[0]
    mean_error = matrix.mean(axis=0)
    if float(np.dot(bias, mean_error)) < 0:
        bias = -bias
    return bias


def per_element_row(
    *,
    element: str,
    arm: str,
    prediction: np.ndarray,
    target: np.ndarray,
    runtime_seconds: float,
    n_atoms: int,
    model: str | None = None,
    models: list[str] | None = None,
    supercell: int,
    bias_vector: np.ndarray | None = None,
    shift_vector: np.ndarray | None = None,
    source_files: list[str] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "element": element,
        "arm": arm,
        "c11": round(float(prediction[0]), 4),
        "c12": round(float(prediction[1]), 4),
        "c44": round(float(prediction[2]), 4),
        "mae": round(mae(prediction, target), 6),
        "runtime_seconds": round(float(runtime_seconds), 4),
        "runtime_s": round(float(runtime_seconds), 4),
        "n_atoms": int(n_atoms),
        "supercell": int(supercell),
    }
    if model is not None:
        row["model"] = model
    if models is not None:
        row["models"] = models
    if bias_vector is not None:
        row["bias_vector"] = [round(float(x), 6) for x in bias_vector]
    if shift_vector is not None:
        row["shift_vector"] = [round(float(x), 6) for x in shift_vector]
    if source_files is not None:
        row["source_files"] = source_files
    return row


def arm_summary(rows: list[dict[str, Any]], extra: dict[str, Any]) -> dict[str, Any]:
    maes = np.array([row["mae"] for row in rows], dtype=float)
    runtime_seconds = float(sum(row["runtime_seconds"] for row in rows))
    summary: dict[str, Any] = {
        "mae_cij_mean": round(float(np.mean(maes)), 6),
        "mae_cij_median": round(float(np.median(maes)), 6),
        "runtime_seconds": round(runtime_seconds, 4),
        "core_hours": round(runtime_seconds / 3600.0, 8),
        "n_cases": len(rows),
    }
    summary.update(extra)
    return summary


def build() -> dict[str, Any]:
    targets = load_json(TARGETS)

    raw: dict[str, dict[str, Any]] = {}
    models_1x1: dict[str, dict[str, dict[str, Any]]] = {element: {} for element in ELEMENTS}
    for element in ELEMENTS:
        for model in MODELS:
            path = INPUT_1X1 / f"{element}_{model}_PBE_1x1x1.json"
            if not path.exists():
                raise FileNotFoundError(path)
            record = load_json(path)
            if record.get("status") != "ok":
                raise ValueError(f"{path} status is not ok: {record.get('error')}")
            record["_source_file"] = str(path.relative_to(ROOT.parent))
            models_1x1[element][model] = record
        raw[element] = models_1x1[element]["TensorNet"]

    ref: dict[str, dict[str, Any]] = {}
    for element in ELEMENTS:
        if element in {"Cu", "Ni"}:
            path = INPUT_3X3_CUNI / f"{element}_TensorNet_PBE.json"
        else:
            path = INPUT_3X3_16 / element / f"{element}_TensorNet_PBE.json"
        if not path.exists():
            raise FileNotFoundError(path)
        record = load_json(path)
        if record.get("status") != "ok":
            raise ValueError(f"{path} status is not ok: {record.get('error')}")
        record["_source_file"] = str(path.relative_to(ROOT.parent))
        ref[element] = record

    rows_by_arm: dict[str, list[dict[str, Any]]] = {
        ARM_RAW: [],
        ARM_CORRECTED: [],
        ARM_REF: [],
        ARM_ENSEMBLE: [],
    }
    for element in ELEMENTS:
        target = target_vec(targets, element)
        raw_record = raw[element]
        raw_prediction = vec(raw_record)
        rows_by_arm[ARM_RAW].append(
            per_element_row(
                element=element,
                arm=ARM_RAW,
                prediction=raw_prediction,
                target=target,
                runtime_seconds=raw_record["runtime_seconds"],
                n_atoms=raw_record.get("n_atoms", 4 if raw_record.get("structure") == "fcc" else 2),
                model=MODELS["TensorNet"],
                supercell=1,
                source_files=[raw_record["_source_file"]],
            )
        )

        bias = loo_bias(raw, targets, element)
        shift = np.zeros(3, dtype=float)
        corrected = np.array(correct(raw_prediction, bias, shift).prediction, dtype=float)
        rows_by_arm[ARM_CORRECTED].append(
            per_element_row(
                element=element,
                arm=ARM_CORRECTED,
                prediction=corrected,
                target=target,
                runtime_seconds=raw_record["runtime_seconds"],
                n_atoms=raw_record.get("n_atoms", 4 if raw_record.get("structure") == "fcc" else 2),
                model=MODELS["TensorNet"],
                supercell=1,
                bias_vector=bias,
                shift_vector=shift,
                source_files=[raw_record["_source_file"]],
            )
        )

        ref_record = ref[element]
        rows_by_arm[ARM_REF].append(
            per_element_row(
                element=element,
                arm=ARM_REF,
                prediction=vec(ref_record),
                target=target,
                runtime_seconds=ref_record["runtime_seconds"],
                n_atoms=ref_record.get("n_atoms", 108 if ref_record.get("structure") == "fcc" else 54),
                model=MODELS["TensorNet"],
                supercell=3,
                source_files=[ref_record["_source_file"]],
            )
        )

        ensemble_records = [models_1x1[element][model] for model in MODELS]
        ensemble_prediction = np.mean([vec(record) for record in ensemble_records], axis=0)
        rows_by_arm[ARM_ENSEMBLE].append(
            per_element_row(
                element=element,
                arm=ARM_ENSEMBLE,
                prediction=ensemble_prediction,
                target=target,
                runtime_seconds=sum(record["runtime_seconds"] for record in ensemble_records),
                n_atoms=raw_record.get("n_atoms", 4 if raw_record.get("structure") == "fcc" else 2),
                models=list(MODELS.values()),
                supercell=1,
                source_files=[record["_source_file"] for record in ensemble_records],
            )
        )

    per_element = [row for arm in [ARM_RAW, ARM_CORRECTED, ARM_REF, ARM_ENSEMBLE] for row in rows_by_arm[arm]]
    arms = {
        ARM_RAW: arm_summary(
            rows_by_arm[ARM_RAW],
            {"model": MODELS["TensorNet"], "supercell": 1},
        ),
        ARM_CORRECTED: arm_summary(
            rows_by_arm[ARM_CORRECTED],
            {"model": MODELS["TensorNet"], "supercell": 1, "bias_method": "LOO-PCA", "n_folds": 16},
        ),
        ARM_REF: arm_summary(
            rows_by_arm[ARM_REF],
            {"model": MODELS["TensorNet"], "supercell": 3},
        ),
        ARM_ENSEMBLE: arm_summary(
            rows_by_arm[ARM_ENSEMBLE],
            {"n_models": 3, "models": list(MODELS.values()), "supercell": 1},
        ),
    }
    cost_ratios = {
        "corrected_vs_ref": round(arms[ARM_REF]["core_hours"] / arms[ARM_CORRECTED]["core_hours"], 6),
        "corrected_vs_ensemble": round(arms[ARM_ENSEMBLE]["core_hours"] / arms[ARM_CORRECTED]["core_hours"], 6),
        "ref_vs_raw": round(arms[ARM_REF]["core_hours"] / arms[ARM_RAW]["core_hours"], 6),
    }
    calibration_rows = [
        {
            "raw_prediction": vec(raw[element]).tolist(),
            "bias_vector": loo_bias(raw, targets, element).tolist(),
            "functional_shift": [0.0, 0.0, 0.0],
            "target": target_vec(targets, element).tolist(),
        }
        for element in ELEMENTS
    ]
    arms[ARM_CORRECTED]["conformal_radius_gpa"] = round(
        leave_one_out_calibration(calibration_rows).radius,
        6,
    )
    claims = {
        "ten_x_cost_accuracy": cost_ratios["corrected_vs_ref"] >= 10.0,
        "five_x_vs_ensemble": cost_ratios["corrected_vs_ensemble"] >= 5.0,
        "operator_beats_ensemble_mae": arms[ARM_CORRECTED]["mae_cij_mean"] < arms[ARM_ENSEMBLE]["mae_cij_mean"],
        "operator_matches_ref_mae_within_1gpa": arms[ARM_CORRECTED]["mae_cij_mean"] <= arms[ARM_REF]["mae_cij_mean"] + 1.0,
        "operator_improves_raw_mae": arms[ARM_CORRECTED]["mae_cij_mean"] < arms[ARM_RAW]["mae_cij_mean"],
    }
    max_1x1_runtime = max(row["runtime_seconds"] for row in per_element if row["supercell"] == 1)
    return {
        "schema_version": "lupine.mlip_elastic_benchmark.v1",
        "provenance": {
            "benchmark_name": "mlip elastic benchmark-2026-06-27",
            "git_sha": git_sha(ROOT),
            "lupine_git_sha": git_sha(LUPINE_ROOT),
            "matpes_release": "2025.2",
            "host": socket.gethostname(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "run_at": datetime.now(timezone.utc).isoformat(),
            "aggregation_runtime_seconds": None,
            "cache_warm": True,
            "cache_warm_max_1x1_runtime_seconds": round(float(max_1x1_runtime), 4),
            "n_cores_per_case": 1,
            "source_paths": {
                "one_by_one": str(INPUT_1X1.relative_to(ROOT.parent)),
                "three_by_three_16elem": str(INPUT_3X3_16.relative_to(ROOT.parent)),
                "three_by_three_cu_ni": str(INPUT_3X3_CUNI.relative_to(ROOT.parent)),
                "targets": str(TARGETS.relative_to(ROOT.parent)),
            },
            "generated_by": str(Path(__file__).relative_to(ROOT)),
        },
        "arms": arms,
        "cost_ratios": cost_ratios,
        "claims": claims,
        "per_element": per_element,
        "caveats": [
            "Headline target is TPBE_0K; r2SCAN targets are approximated by scalar bulk-modulus shift and reserved for sensitivity analyses.",
            "QET is a TensorNet alias in MatPES 2025.2 and is deduplicated; ensemble uses three architectures.",
            "All 1x1x1 costs are cache-warm with every per-case runtime below 60 s; cold-cache timings are excluded.",
            "Au uses PW91-GGA fallback, not a pure PBE target.",
            "LOO bias fitting is used for corrected-1x1x1; in-sample fitting is intentionally avoided.",
            "Cu/Ni 1x1x1 cases reuse prior cache-warm outputs; missing non-Cu/Ni PBE cases were completed in this run.",
            "Cr is a known outlier; arm summaries report both mean and median MAE.",
        ],
    }


def validate(result: dict[str, Any]) -> None:
    errors = []
    if result.get("schema_version") != "lupine.mlip_elastic_benchmark.v1":
        errors.append("schema_version must be lupine.mlip_elastic_benchmark.v1")
    if result["arms"][ARM_CORRECTED].get("bias_method") != "LOO-PCA":
        errors.append("corrected arm bias_method must be LOO-PCA")
    if result["arms"][ARM_ENSEMBLE].get("n_models") != 3:
        errors.append("ensemble arm n_models must be 3")
    if len(result.get("per_element", [])) != 64:
        errors.append("per_element must contain 64 rows")
    for arm in [ARM_RAW, ARM_CORRECTED, ARM_REF, ARM_ENSEMBLE]:
        n = sum(1 for row in result["per_element"] if row["arm"] == arm)
        if n != 16:
            errors.append(f"{arm} must contain 16 rows, found {n}")
    if result["cost_ratios"]["corrected_vs_ref"] < 1.0:
        errors.append("corrected_vs_ref must be >= 1.0")
    hot = [
        row for row in result["per_element"] if row["supercell"] == 1 and row["runtime_seconds"] >= 60
    ]
    if hot:
        errors.append(f"1x1x1 runtime >=60s for {[row['element'] + ':' + row['arm'] for row in hot]}")
    required = {
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
    for idx, row in enumerate(result["per_element"]):
        missing = required - row.keys()
        if missing:
            errors.append(f"per_element[{idx}] missing {sorted(missing)}")
    if errors:
        raise SystemExit("\n".join(errors))


def main() -> None:
    start = time.time()
    result = build()
    result["provenance"]["aggregation_runtime_seconds"] = round(time.time() - start, 4)
    validate(result)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {OUTPUT}")
    print(json.dumps({"arms": result["arms"], "cost_ratios": result["cost_ratios"], "claims": result["claims"]}, indent=2))


if __name__ == "__main__":
    main()
