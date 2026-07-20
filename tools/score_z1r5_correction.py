#!/usr/bin/env python3
"""Score the Round-5 Z1-correction pilot (frozen protocol, no tuning).

Implements docs/plans/2026-07-20-round5-z1-correction-preregistration.md:
fit per-model linear error model on the disjoint training panel ONLY
(direction gate + Round-4 v2 theorem caps), apply frozen to the locked
30-path test panel, score against the frozen WIN criteria. The tool
computes; it does not decide what counts as evidence — the prereg does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
GCS_TRAIN = "gs://shed-489901-atlas-outputs/z1r5/train/{model}/cell_result.json"
GCS_TEST = "gs://shed-489901-atlas-outputs/z1/campaign-float64/{model}/cell_result.json"
PROJECT = "shed-489901"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_artifact(uri: str, dest: Path) -> dict:
    subprocess.run(
        ["gcloud", "storage", "cp", uri, str(dest), "--project", PROJECT],
        check=True,
        capture_output=True,
    )
    return json.loads(dest.read_text(encoding="utf-8"))


def completed_paths(artifact: dict) -> list[dict]:
    out = []
    for pred in artifact.get("predictions", []):
        if pred.get("status") != "completed":
            continue
        ref = pred.get("reference_barrier_ev")
        err = pred.get("signed_error_mev")
        predicted = pred.get("predicted_barrier_ev")
        if not all(isinstance(v, (int, float)) for v in (ref, err, predicted)):
            raise ValueError(f"completed path missing numeric fields: {pred.get('path_id')}")
        out.append({
            "path_id": pred["path_id"],
            "chemical_system": pred.get("chemical_system"),
            "reference_barrier_ev": float(ref),
            "predicted_barrier_ev": float(predicted),
            "signed_error_mev": float(err),
        })
    return out


def direction_gate(errors: list[float]) -> tuple[bool, str]:
    if not errors:
        return False, "no_training_paths"
    if all(e < 0 for e in errors):
        return True, "all_negative"
    if all(e > 0 for e in errors):
        return True, "all_positive"
    return False, "direction"


def theorem_caps(ratios: list[float]) -> tuple[bool, str]:
    """Round-4 v2 caps: inflation b-1 > 2s; deflation 1-b > 3s AND b >= 0.5."""
    if not ratios:
        return False, "no_ratios"
    b = statistics.median(ratios)
    s = max(ratios) - min(ratios)
    if b > 1.0:
        return (b - 1.0 > 2 * s), "inflation"
    return (1.0 - b > 3 * s and b >= 0.5), "deflation"


def fit_linear(points: list[tuple[float, float]]) -> tuple[float, float]:
    """Least squares ê(ref) = a + b·ref over (reference_ev, signed_error_mev)."""
    n = len(points)
    sx = sum(r for r, _ in points)
    sy = sum(e for _, e in points)
    sxx = sum(r * r for r, _ in points)
    sxy = sum(r * e for r, e in points)
    denom = n * sxx - sx * sx
    if denom == 0:
        raise ValueError("degenerate training references")
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    return a, b


def family_of(chemical_system: str) -> str:
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


def score_model(model: str, train: list[dict], test: list[dict]) -> dict:
    errors = [p["signed_error_mev"] for p in train]
    ratios = [p["predicted_barrier_ev"] / p["reference_barrier_ev"] for p in train]
    gate_ok, gate_reason = direction_gate(errors)
    cap_ok, cap_side = theorem_caps(ratios)
    raw_test_mae = statistics.mean(abs(p["signed_error_mev"]) for p in test)
    result = {
        "model_id": model,
        "n_train": len(train),
        "n_test": len(test),
        "raw_test_mae_mev": raw_test_mae,
        "direction_gate": {"passed": gate_ok, "reason": gate_reason},
        "theorem_cap": {"passed": cap_ok, "side": cap_side},
    }
    if not gate_ok or not cap_ok:
        result.update({
            "applied": False,
            "abstain_reason": gate_reason if not gate_ok else f"theorem_cap_{cap_side}",
            "verdict": "abstained",
        })
        return result

    a, b = fit_linear([(p["reference_barrier_ev"], p["signed_error_mev"]) for p in train])
    rows = []
    for p in test:
        corrected = p["signed_error_mev"] - (a + b * p["reference_barrier_ev"])
        rows.append({
            "path_id": p["path_id"],
            "family": family_of(p["chemical_system"]),
            "reference_barrier_ev": p["reference_barrier_ev"],
            "raw_error_mev": p["signed_error_mev"],
            "corrected_error_mev": corrected,
            "corrected_abs_mev": abs(corrected),
        })
    corrected_mae = statistics.mean(r["corrected_abs_mev"] for r in rows)
    families: dict[str, dict[str, list[float]]] = {}
    for r in rows:
        fam = families.setdefault(r["family"], {"raw": [], "corrected": []})
        fam["raw"].append(abs(r["raw_error_mev"]))
        fam["corrected"].append(r["corrected_abs_mev"])
    family_report = {
        fam: {
            "raw_mae": statistics.mean(v["raw"]),
            "corrected_mae": statistics.mean(v["corrected"]),
            "no_harm_ok": statistics.mean(v["corrected"]) <= 1.1 * statistics.mean(v["raw"]) + 1e-9,
        }
        for fam, v in families.items()
    }
    ordered = sorted(rows, key=lambda r: r["corrected_abs_mev"])
    coverage = {}
    for cov in (1.0, 0.9, 0.8, 0.7):
        k = max(1, int(len(ordered) * cov))
        accepted = ordered[:k]
        coverage[f"{cov:.2f}"] = {
            "accepted_paths": len(accepted),
            "accepted_mae_mev": statistics.mean(r["corrected_abs_mev"] for r in accepted),
            "raw_mae_same_paths_mev": statistics.mean(abs(r["raw_error_mev"]) for r in accepted),
        }
    no_harm = all(f["no_harm_ok"] for f in family_report.values())
    win = corrected_mae <= 0.5 * raw_test_mae
    result.update({
        "applied": True,
        "fit": {"a_mev": a, "b_mev_per_ev": b},
        "corrected_test_mae_mev": corrected_mae,
        "families": family_report,
        "no_harm": no_harm,
        "coverage": coverage,
        "win": win and no_harm,
        "strong_win": win and no_harm and corrected_mae <= 100.0,
        "rows": rows,
        "verdict": ("strong_win" if (win and no_harm and corrected_mae <= 100.0)
                    else "win" if (win and no_harm) else "loss"),
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root
    work = root / "build" / "z1r5"
    work.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "lupine.z1r5.correction_score.v1",
        "preregistration": "docs/plans/2026-07-20-round5-z1-correction-preregistration.md",
        "test_panel": "data/candidates/z1_nebdft2k_barriers.lock.json",
        "test_panel_sha256": "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
        "train_panel": "data/candidates/z1r5_correction_train.lock.json",
        "train_panel_sha256": "sha256:4099f4fcee6418988a250c2a9892d3bc16015f53e21eb47a6bf70bb62e05cc2f",
        "models": {},
    }
    for model in MODELS:
        train_art = load_artifact(GCS_TRAIN.format(model=model), work / f"train-{model}.json")
        test_art = load_artifact(GCS_TEST.format(model=model), work / f"test-{model}.json")
        report["models"][model] = score_model(
            model, completed_paths(train_art), completed_paths(test_art)
        )

    out = args.out or (root / "data/candidates/z1r5/correction-score.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=1, sort_keys=True) + "\n").encode("utf-8")
    out.write_bytes(payload)
    out.with_name(out.name + ".sha256").write_text(f"{sha256_bytes(payload)}  {out.name}\n")
    print(json.dumps({
        m: {
            "verdict": r["verdict"],
            "raw": round(r["raw_test_mae_mev"], 1),
            "corrected": round(r.get("corrected_test_mae_mev", -1), 1) if r.get("applied") else None,
            "no_harm": r.get("no_harm"),
        }
        for m, r in report["models"].items()
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
