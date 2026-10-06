#!/usr/bin/env python3
"""Descriptive real-force pilot: no inference, fitting, downloads or publication.

The three fixed baseline models and uniform weights are declared before loading
the data. Five previously inspected configurations are NOT a sealed test set.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import itertools
import json
import math
import os
from pathlib import Path

MODELS = ("chgnet", "mace-mp-0", "sevennet")
GEOMETRY = "gcp/mlip-cell-runner/fixtures/canonical_structures_v2_mptrj.json"
BASELINES = {model: f"docs/glim-m3-upgrade/runs/live/forces/{model}__baseline.json" for model in MODELS}
PRIOR = "data/a6_bridge/results_pilot_mptrj_v2_5000.json"


def read_input(root, relative):
    content = (root / relative).read_bytes()
    return json.loads(content), {"path": relative, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


def matrix(value, rows, label):
    if (not isinstance(value, list) or len(value) != rows
            or any(not isinstance(row, list) or len(row) != 3 for row in value)
            or any(type(x) not in (int, float) or not math.isfinite(x) for row in value for x in row)):
        raise ValueError(f"{label}: expected finite [{rows},3] array")


def validate_join(fixture, payloads):
    cases = fixture["row_fixtures"]["forces"]["structures"]
    if len(cases) != 5 or len({c["material_id"] for c in cases}) != 5:
        raise ValueError("Expected exactly the historical five-material pilot")
    ids = [c["structure_id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate fixture structure_id")
    joined = {}
    for model in MODELS:
        payload = payloads[model]
        if (payload["mlip_id"] != model or payload["variant_id"] != "baseline" or payload["row_id"] != "forces"
                or payload["fixture_contract"]["manifest_hash"] != fixture["manifest_hash"]):
            raise ValueError(f"{model}: baseline identity or manifest mismatch")
        if payload["accuracy"]["error_unit"] != "ev_per_angstrom_rmse":
            raise ValueError(f"{model}: unexpected force units")
        predictions = payload["predictions"]
        mapping = {p["structure_id"]: p for p in predictions}
        if len(mapping) != len(predictions) or set(mapping) != set(ids):
            raise ValueError(f"{model}: duplicate, missing or extra structure_id")
        joined[model] = mapping
    for case in cases:
        count = len(case["symbols"])
        if count < 2:
            raise ValueError("Pilot requires at least two atoms per configuration")
        matrix(case["positions"], count, "positions")
        matrix(case["cell"], 3, "cell")
        matrix(case["reference"]["forces_ev_per_angstrom"], count, "reference forces")
        for model, mapping in joined.items():
            pred = mapping[case["structure_id"]]
            if any(pred.get(key) != case.get(key) for key in ("material_id", "symbols", "reference")):
                raise ValueError(f"{model}: material, ordered symbols or reference mismatch")
            matrix(pred["forces_ev_per_angstrom"], count, "predicted forces")
    return cases, joined


def flat(values):
    return [x for row in values for x in row]


def dot(a, b):
    return math.fsum(x * y for x, y in zip(a, b, strict=True))


def norm(a):
    return math.sqrt(dot(a, a))


def cosine(a, b):
    denominator = norm(a) * norm(b)
    return max(-1.0, min(1.0, dot(a, b) / denominator)) if denominator else None


def totals(values):
    return [math.fsum(row[j] for row in values) for j in range(3)]


def project(values):
    mean = [x / len(values) for x in totals(values)]
    return [[row[j] - mean[j] for j in range(3)] for row in values], mean


def metrics(predicted, reference):
    count = len(reference)
    residual = [[p[j] - r[j] for j in range(3)] for p, r in zip(predicted, reference, strict=True)]
    projected, mean = project(residual)
    squared = dot(flat(residual), flat(residual))
    projected_squared = dot(flat(projected), flat(projected))
    translation_squared = count * dot(mean, mean)
    if not math.isclose(squared, projected_squared + translation_squared, rel_tol=1e-12, abs_tol=1e-14):
        raise ArithmeticError("Orthogonal force decomposition failed")
    result = {
        "cartesian_rmse_ev_per_angstrom": math.sqrt(squared / (3 * count)),
        "mean_atom_vector_error_ev_per_angstrom": math.fsum(norm(row) for row in residual) / count,
        "projected_cartesian_rmse_ev_per_angstrom": math.sqrt(projected_squared / (3 * count)),
        "squared_error_ev2_per_angstrom2": squared,
        "projected_squared_error_ev2_per_angstrom2": projected_squared,
        "translation_squared_error_ev2_per_angstrom2": translation_squared,
        "translation_error_fraction": translation_squared / squared if squared else None,
        "residual_mean_vector_ev_per_angstrom": mean,
        "predicted_net_force_norm_ev_per_angstrom": norm(totals(predicted)),
    }
    return result, residual, projected


def analyze(root):
    fixture, fixture_receipt = read_input(root, GEOMETRY)
    payloads, inputs = {}, [fixture_receipt]
    for model, relative in BASELINES.items():
        payloads[model], receipt = read_input(root, relative)
        inputs.append(receipt)
    prior, prior_receipt = read_input(root, PRIOR)
    inputs.append(prior_receipt)
    cases, joined = validate_join(fixture, payloads)
    rows = []
    residuals = {model: [] for model in MODELS}
    projections = {model: [] for model in MODELS}
    for case in cases:
        reference = case["reference"]["forces_ev_per_angstrom"]
        count = len(reference)
        geometry = {key: case[key] for key in ("cell", "positions", "pbc", "symbols")}
        row = {
            "structure_id": case["structure_id"], "material_id": case["material_id"],
            "task_id": case.get("task_id"), "ionic_step": case.get("ionic_step"), "atoms": count,
            "ordered_symbols": case["symbols"],
            "geometry_sha256": hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "reference_net_force_norm_ev_per_angstrom": norm(totals(reference)),
            "models": {}, "pairwise": {},
        }
        forces = {}
        for model in MODELS:
            forces[model] = joined[model][case["structure_id"]]["forces_ev_per_angstrom"]
            row["models"][model], residual, projected = metrics(forces[model], reference)
            residuals[model].append(flat(residual))
            projections[model].append(flat(projected))
        uniform = [[math.fsum(forces[m][i][j] for m in MODELS) / len(MODELS) for j in range(3)] for i in range(count)]
        row["models"]["uniform_ensemble"], _, _ = metrics(uniform, reference)
        for a, b in itertools.combinations(MODELS, 2):
            row["pairwise"][a + "|" + b] = {
                "raw_cosine": cosine(residuals[a][-1], residuals[b][-1]),
                "physical_translation_projected_cosine": cosine(projections[a][-1], projections[b][-1]),
            }
        rows.append(row)
    total_atoms = sum(row["atoms"] for row in rows)
    summary = {}
    for model in (*MODELS, "uniform_ensemble"):
        entries = [row["models"][model] for row in rows]
        squared = math.fsum(e["squared_error_ev2_per_angstrom2"] for e in entries)
        translation = math.fsum(e["translation_squared_error_ev2_per_angstrom2"] for e in entries)
        summary[model] = {
            "material_balanced_mean_cartesian_rmse_ev_per_angstrom": math.fsum(e["cartesian_rmse_ev_per_angstrom"] for e in entries) / len(entries),
            "material_balanced_root_mean_mse_ev_per_angstrom": math.sqrt(math.fsum(
                e["squared_error_ev2_per_angstrom2"] / (3 * row["atoms"])
                for e, row in zip(entries, rows, strict=True)) / len(entries)),
            "pooled_cartesian_rmse_ev_per_angstrom": math.sqrt(squared / (3 * total_atoms)),
            "pooled_translation_error_fraction": translation / squared if squared else None,
            "largest_material_squared_error_share": max(e["squared_error_ev2_per_angstrom2"] for e in entries) / squared if squared else None,
        }
    pairwise = {}
    for a, b in itertools.combinations(MODELS, 2):
        pair = a + "|" + b
        pooled = [[x for values in residuals[m] for x in values] for m in (a, b)]
        centered = [[x - math.fsum(values) / len(values) for x in values] for values in pooled]
        pairwise[pair] = {
            "pooled_raw_cosine": cosine(*pooled),
            "pooled_global_scalar_centered_cosine": cosine(*centered),
            "prior_a6_reported_scalar_centered_cosine": prior["force_field"]["pairs"][pair]["field_cos"]["observed"],
            "pooled_physical_translation_projected_cosine": cosine(*[[x for values in projections[m] for x in values] for m in (a, b)]),
            "material_balanced_mean_raw_cosine": math.fsum(row["pairwise"][pair]["raw_cosine"] for row in rows) / len(rows),
            "material_balanced_mean_projected_cosine": math.fsum(row["pairwise"][pair]["physical_translation_projected_cosine"] for row in rows) / len(rows),
        }
    ensemble_comparisons = {}
    for model in MODELS:
        ensemble_comparisons[model] = {
            "materials_uniform_beats_model": sum(row["models"]["uniform_ensemble"]["cartesian_rmse_ev_per_angstrom"] < row["models"][model]["cartesian_rmse_ev_per_angstrom"] for row in rows),
            "material_balanced_rmse_ratio_uniform_over_model": summary["uniform_ensemble"]["material_balanced_mean_cartesian_rmse_ev_per_angstrom"] / summary[model]["material_balanced_mean_cartesian_rmse_ev_per_angstrom"],
            "pooled_rmse_ratio_uniform_over_model": summary["uniform_ensemble"]["pooled_cartesian_rmse_ev_per_angstrom"] / summary[model]["pooled_cartesian_rmse_ev_per_angstrom"],
            "material_balanced_root_mean_mse_ratio_uniform_over_model": summary["uniform_ensemble"]["material_balanced_root_mean_mse_ev_per_angstrom"] / summary[model]["material_balanced_root_mean_mse_ev_per_angstrom"],
        }
    script = Path(__file__)
    return {
        "schema": "lupine.pi.pilot_force_descriptive.v1", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "exploratory_real_archived_data", "inference_calls": 0, "publication": "held",
        "inputs": inputs, "analysis_script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "fixture_contract_manifest_hash": fixture["manifest_hash"],
        "dataset": {"configurations": len(rows), "materials": len(rows), "atoms": total_atoms, "frames_per_material": 1},
        "definitions": {
            "force_units": "eV/angstrom", "geometry_units": "angstrom", "residual": "predicted force minus reference force",
            "rmse": "sqrt(sum over atoms/components of residual squared / (3*N))",
            "physical_projection": "Subtract each Cartesian component's mean across atoms separately in every configuration. This is a diagnostic on residuals, not a newly evaluated force field.",
            "translation_fraction": "N*||mean_atom(residual)||^2 / ||residual||^2",
            "uniform_ensemble": "Arithmetic mean of the three archived baseline forces; fixed weights1/3, no fitted or selected weights.",
            "macro": "Equal weight per material, averaging per-material Cartesian RMSE or cosine.",
            "macro_squared_loss_control": "sqrt(mean over materials of per-material MSE). Separates atom weighting from taking the square root before versus after averaging; a different risk functional from mean per-material RMSE.",
            "pooled": "All Cartesian components; larger/high-error cases can dominate. Pooled vectors are used for descriptive alignment only, not covariance fitting.",
            "prior_comparison": "A6 centers all pooled scalar components by one scalar mean. Physical conservation projection instead subtracts3component means within each configuration.",
        },
        "limitations": [
            "Five previously inspected configurations, one per material; not a sealed or newly held-out test set.",
            "No fitted covariance, uncertainty calibration, statistical significance, transfer claim or discovery of universal modes.",
            "Cross-model correlation and any averaging gain are descriptive; shared training/reference biases remain possible.",
            "Net-force projection tests only uniform translation modes; it does not eliminate all mechanical or geometric constraints.",
            "Pilot metadata retains MPtrj test provenance but not exact per-case DFT settings; model package versions do not pin weight hashes.",
            "No frame or outlier is removed; all model comparisons and all five materials are reported.",
        ],
        "model_provenance": {m: {k: payloads[m].get(k) for k in ("run_id", "manifest_hash", "versions", "execution")} for m in MODELS},
        "rows": rows, "model_summary": summary, "pairwise_summary": pairwise, "uniform_ensemble_comparisons": ensemble_comparisons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.repo)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output.resolve()), "dataset": result["dataset"],
                      "model_summary": result["model_summary"], "ensemble": result["uniform_ensemble_comparisons"]}, allow_nan=False))


if __name__ == "__main__":
    main()
