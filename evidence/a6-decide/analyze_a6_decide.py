#!/usr/bin/env python3
"""Preregistered A6-DECIDE trajectory analysis.

Primary endpoint: cross-model force-residual field cosine against independent
Haar SO(3) rotations per model and configuration. Uncertainty is a blocked
bootstrap over trajectory/material IDs. The frozen task rule requires 5,000
geometry-null and 2,000 bootstrap replicates at three specified seeds.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

MODELS = ("chgnet", "m3gnet", "mace-mp-small")
SEEDS = (42, 1729, 20260803)
N_NULL = 5000
N_BOOT = 2000
ALPHA = 0.05
OMAT = "omat24-validation-aimd-pbe-1000-nvt"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def haar_so3(rng: np.random.Generator, shape: tuple[int, ...]) -> np.ndarray:
    """Draw Haar-uniform proper 3D rotations using Shoemake quaternions."""
    u1 = rng.random(shape)
    u2 = rng.random(shape)
    u3 = rng.random(shape)
    x = np.sqrt(1.0 - u1) * np.sin(2.0 * np.pi * u2)
    y = np.sqrt(1.0 - u1) * np.cos(2.0 * np.pi * u2)
    z = np.sqrt(u1) * np.sin(2.0 * np.pi * u3)
    w = np.sqrt(u1) * np.cos(2.0 * np.pi * u3)
    rotations = np.empty(shape + (3, 3), dtype=np.float64)
    rotations[..., 0, 0] = 1 - 2 * (y * y + z * z)
    rotations[..., 0, 1] = 2 * (x * y - z * w)
    rotations[..., 0, 2] = 2 * (x * z + y * w)
    rotations[..., 1, 0] = 2 * (x * y + z * w)
    rotations[..., 1, 1] = 1 - 2 * (x * x + z * z)
    rotations[..., 1, 2] = 2 * (y * z - x * w)
    rotations[..., 2, 0] = 2 * (x * z - y * w)
    rotations[..., 2, 1] = 2 * (y * z + x * w)
    rotations[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return rotations


def centered_cos(raw_dot: np.ndarray, sum_a: np.ndarray, sum_b: np.ndarray,
                 sq_a: float | np.ndarray, sq_b: float | np.ndarray,
                 dimensions: float | np.ndarray) -> np.ndarray:
    covariance = raw_dot - sum_a * sum_b / dimensions
    var_a = np.maximum(np.asarray(sq_a) - sum_a * sum_a / dimensions, 0.0)
    var_b = np.maximum(np.asarray(sq_b) - sum_b * sum_b / dimensions, 0.0)
    denom = np.sqrt(var_a * var_b)
    return np.divide(covariance, denom, out=np.full_like(covariance, np.nan, dtype=float), where=denom > 0)


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values, key=lambda pair: (p_values[pair], pair))
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for rank, pair in enumerate(ordered):
        running = max(running, min(1.0, (count - rank) * p_values[pair]))
        adjusted[pair] = running
    return adjusted


def load_source(root: Path, source: str, lock: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    meta = lock["sources"][source]
    if source == "mptrj":
        expected_identity = {
            "dataset": "nimashoghi/mptrj",
            "frozen_source_identity": "MPtrj test",
            "resolved_split": "test",
            "dataset_revision": "f88fbe46e16524223210654bad9e1b05a15c2adb",
        }
        for key, expected in expected_identity.items():
            if meta.get(key) != expected:
                raise ValueError(f"{source}: frozen source identity mismatch for {key}")
    manifest_path = root / meta["manifest_path"]
    manifest_bytes_sha = sha256_file(manifest_path)
    if manifest_bytes_sha != meta["manifest_sha256"]:
        raise ValueError(f"{source}: manifest digest mismatch")
    parquet_path = root / meta["parquet_path"]
    if sha256_file(parquet_path) != meta["parquet_sha256"]:
        raise ValueError(f"{source}: parquet digest mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("manifest_hash") != meta["manifest_content_hash"]:
        raise ValueError(f"{source}: manifest content hash mismatch")
    source_provenance = manifest.get("reference_provenance", {}).get("a6_source", {})
    for key in ("dataset", "frozen_source_identity", "resolved_split", "dataset_revision"):
        if key in meta and source_provenance.get(key) != meta[key]:
            raise ValueError(f"{source}: manifest source provenance mismatch for {key}")
    cases = manifest["row_fixtures"]["forces"]["structures"]
    if len(cases) != 400:
        raise ValueError(f"{source}: expected 400 manifest cases, got {len(cases)}")
    if len({case["structure_id"] for case in cases}) != len(cases):
        raise ValueError(f"{source}: duplicate structure_id")
    if len({case["config_id"] for case in cases}) != len(cases):
        raise ValueError(f"{source}: duplicate config_id")

    payloads: dict[str, dict[str, Any]] = {}
    raw_digests: dict[str, str] = {}
    for model in MODELS:
        path = root / "results" / "raw-v1" / source / model / "cell_result.json"
        payload = json.loads(path.read_text())
        if payload.get("mlip_id") != model:
            raise ValueError(f"{source}/{model}: mlip_id mismatch")
        if payload.get("fixture_contract", {}).get("manifest_hash") != manifest["manifest_hash"]:
            raise ValueError(f"{source}/{model}: fixture manifest hash mismatch")
        predictions = payload.get("predictions")
        if not isinstance(predictions, list) or len(predictions) != len(cases):
            raise ValueError(f"{source}/{model}: prediction cardinality mismatch")
        for case, pred in zip(cases, predictions, strict=True):
            for key in ("structure_id", "material_id", "symbols", "reference"):
                if pred.get(key) != case.get(key):
                    raise ValueError(f"{source}/{model}: {key} mismatch for {case['structure_id']}")
            predicted = np.asarray(pred["forces_ev_per_angstrom"], dtype=float)
            reference = np.asarray(pred["reference"]["forces_ev_per_angstrom"], dtype=float)
            expected = (len(pred["symbols"]), 3)
            if predicted.shape != expected or reference.shape != expected:
                raise ValueError(f"{source}/{model}: force shape mismatch for {case['structure_id']}")
            if not np.isfinite(predicted).all() or not np.isfinite(reference).all():
                raise ValueError(f"{source}/{model}: nonfinite force for {case['structure_id']}")
        payloads[model] = payload
        raw_digests[model] = sha256_file(path)

    block_counts = Counter(case["material_id"] for case in cases)
    if len(block_counts) < 30 or min(block_counts.values()) < 8 or len(cases) < 240:
        raise ValueError(f"{source}: preregistered information gate failed: {dict(block_counts)}")

    residuals: dict[str, list[np.ndarray]] = {model: [] for model in MODELS}
    for model in MODELS:
        for pred in payloads[model]["predictions"]:
            residuals[model].append(
                np.asarray(pred["forces_ev_per_angstrom"], dtype=float)
                - np.asarray(pred["reference"]["forces_ev_per_angstrom"], dtype=float)
            )

    integrity = {
        "manifest_path": str(manifest_path.relative_to(root)),
        "manifest_sha256": manifest_bytes_sha,
        "manifest_content_hash": manifest["manifest_hash"],
        "parquet_path": str(parquet_path.relative_to(root)),
        "parquet_sha256": meta["parquet_sha256"],
        "source_identity": {
            key: meta[key]
            for key in ("dataset", "frozen_source_identity", "resolved_split", "dataset_revision", "url")
            if key in meta
        },
        "raw_result_sha256": raw_digests,
        "blocks": len(block_counts),
        "configurations": len(cases),
        "configs_per_block": sorted(set(block_counts.values())),
        "atoms": sum(len(case["symbols"]) for case in cases),
        "atom_count_range": [min(len(case["symbols"]) for case in cases), max(len(case["symbols"]) for case in cases)],
        "all_integrity_and_information_gates_pass": True,
    }
    data = {"cases": cases, "residuals": residuals}
    return data, integrity


def pair_sufficient(data: dict[str, Any], left: str, right: str) -> dict[str, np.ndarray]:
    configs_a = data["residuals"][left]
    configs_b = data["residuals"][right]
    cross = []
    cross_unit = []
    sum_a = []
    sum_b = []
    axis_sum_a = []
    axis_sum_b = []
    sq_a = []
    sq_b = []
    dimensions = []
    atoms = []
    for a, b in zip(configs_a, configs_b, strict=True):
        cross.append(a.T @ b)
        norms_a = np.linalg.norm(a, axis=1)
        norms_b = np.linalg.norm(b, axis=1)
        valid = (norms_a > 0) & (norms_b > 0)
        unit_a = np.divide(a, norms_a[:, None], out=np.zeros_like(a), where=norms_a[:, None] > 0)
        unit_b = np.divide(b, norms_b[:, None], out=np.zeros_like(b), where=norms_b[:, None] > 0)
        cross_unit.append(unit_a[valid].T @ unit_b[valid])
        sum_a.append(float(a.sum()))
        sum_b.append(float(b.sum()))
        axis_sum_a.append(a.sum(axis=0))
        axis_sum_b.append(b.sum(axis=0))
        sq_a.append(float(np.square(a).sum()))
        sq_b.append(float(np.square(b).sum()))
        dimensions.append(float(a.size))
        atoms.append(float(valid.sum()))
    return {
        "cross": np.stack(cross),
        "cross_unit": np.stack(cross_unit),
        "sum_a": np.asarray(sum_a),
        "sum_b": np.asarray(sum_b),
        "axis_sum_a": np.stack(axis_sum_a),
        "axis_sum_b": np.stack(axis_sum_b),
        "sq_a": np.asarray(sq_a),
        "sq_b": np.asarray(sq_b),
        "dimensions": np.asarray(dimensions),
        "atoms": np.asarray(atoms),
    }


def observed_stats(suff: dict[str, np.ndarray]) -> tuple[float, float]:
    field = centered_cos(
        np.asarray(np.trace(suff["cross"], axis1=1, axis2=2).sum()),
        np.asarray(suff["sum_a"].sum()),
        np.asarray(suff["sum_b"].sum()),
        suff["sq_a"].sum(), suff["sq_b"].sum(), suff["dimensions"].sum(),
    ).item()
    atom = float(np.trace(suff["cross_unit"], axis1=1, axis2=2).sum() / suff["atoms"].sum())
    return field, atom


def geometry_null(sufficient: dict[str, dict[str, np.ndarray]], seed: int,
                  n_replicates: int, chunk: int = 100) -> dict[str, dict[str, np.ndarray]]:
    rng = np.random.default_rng(seed)
    pairs = list(sufficient)
    n_configs = next(iter(sufficient.values()))["cross"].shape[0]
    output = {pair: {"field_cos": np.empty(n_replicates), "atom_cos": np.empty(n_replicates)} for pair in pairs}
    model_index = {model: idx for idx, model in enumerate(MODELS)}
    for start in range(0, n_replicates, chunk):
        size = min(chunk, n_replicates - start)
        rotations = haar_so3(rng, (size, len(MODELS), n_configs))
        for pair, suff in sufficient.items():
            left, right = pair.split("|")
            ra = rotations[:, model_index[left]]
            rb = rotations[:, model_index[right]]
            raw_dot = np.einsum("rcki,cij,rckj->r", ra, suff["cross"], rb, optimize=True)
            rotated_sum_a = np.einsum("rcki,ci->r", ra, suff["axis_sum_a"], optimize=True)
            rotated_sum_b = np.einsum("rcki,ci->r", rb, suff["axis_sum_b"], optimize=True)
            output[pair]["field_cos"][start:start + size] = centered_cos(
                raw_dot, rotated_sum_a, rotated_sum_b,
                suff["sq_a"].sum(), suff["sq_b"].sum(), suff["dimensions"].sum(),
            )
            atom_dot = np.einsum("rcki,cij,rckj->r", ra, suff["cross_unit"], rb, optimize=True)
            output[pair]["atom_cos"][start:start + size] = atom_dot / suff["atoms"].sum()
    return output


def blocked_bootstrap(data: dict[str, Any], sufficient: dict[str, dict[str, np.ndarray]],
                      seed: int, n_replicates: int) -> dict[str, dict[str, np.ndarray]]:
    rng = np.random.default_rng(seed)
    blocks = sorted({case["material_id"] for case in data["cases"]})
    block_index = {block: idx for idx, block in enumerate(blocks)}
    config_block = np.asarray([block_index[case["material_id"]] for case in data["cases"]])
    draws = rng.integers(0, len(blocks), size=(n_replicates, len(blocks)))
    weights = np.zeros((n_replicates, len(blocks)), dtype=float)
    rows = np.repeat(np.arange(n_replicates), len(blocks))
    np.add.at(weights, (rows, draws.ravel()), 1.0)
    config_weights = weights[:, config_block]
    output: dict[str, dict[str, np.ndarray]] = {}
    for pair, suff in sufficient.items():
        raw_dot_config = np.trace(suff["cross"], axis1=1, axis2=2)
        raw_dot = config_weights @ raw_dot_config
        sum_a = config_weights @ suff["sum_a"]
        sum_b = config_weights @ suff["sum_b"]
        sq_a = config_weights @ suff["sq_a"]
        sq_b = config_weights @ suff["sq_b"]
        dimensions = config_weights @ suff["dimensions"]
        atom_dot = config_weights @ np.trace(suff["cross_unit"], axis1=1, axis2=2)
        atoms = config_weights @ suff["atoms"]
        output[pair] = {
            "field_cos": centered_cos(raw_dot, sum_a, sum_b, sq_a, sq_b, dimensions),
            "atom_cos": np.divide(atom_dot, atoms, out=np.full_like(atom_dot, np.nan), where=atoms > 0),
        }
    return output


def finite_summary(values: np.ndarray) -> dict[str, float]:
    valid = values[np.isfinite(values)]
    if len(valid) != len(values):
        raise ValueError(f"nonfinite replicate statistic: {len(values) - len(valid)} of {len(values)}")
    return {
        "mean": float(np.mean(valid)),
        "sd": float(np.std(valid, ddof=1)),
        "q025": float(np.quantile(valid, 0.025)),
        "q500": float(np.quantile(valid, 0.5)),
        "q975": float(np.quantile(valid, 0.975)),
    }


def analyze_source(data: dict[str, Any], seed: int, n_null: int, n_boot: int) -> dict[str, Any]:
    pairs = [f"{a}|{b}" for a, b in itertools.combinations(MODELS, 2)]
    sufficient = {pair: pair_sufficient(data, *pair.split("|")) for pair in pairs}
    observed = {pair: dict(zip(("field_cos", "atom_cos"), observed_stats(sufficient[pair]), strict=True)) for pair in pairs}
    null = geometry_null(sufficient, seed, n_null)
    bootstrap = blocked_bootstrap(data, sufficient, seed, n_boot)
    raw_p = {
        pair: float((np.sum(null[pair]["field_cos"] >= observed[pair]["field_cos"]) + 1) / (n_null + 1))
        for pair in pairs
    }
    adjusted = holm_adjust(raw_p)
    pair_results: dict[str, Any] = {}
    for pair in pairs:
        pair_results[pair] = {}
        for statistic in ("field_cos", "atom_cos"):
            null_summary = finite_summary(null[pair][statistic])
            boot_summary = finite_summary(bootstrap[pair][statistic])
            p_one_sided = float((np.sum(null[pair][statistic] >= observed[pair][statistic]) + 1) / (n_null + 1))
            pair_results[pair][statistic] = {
                "observed": observed[pair][statistic],
                "null": {**null_summary, "p_one_sided": p_one_sided},
                "bootstrap": boot_summary,
            }
        primary = pair_results[pair]["field_cos"]
        primary["holm_adjusted_p"] = adjusted[pair]
        primary["passes_primary_pair_rule"] = bool(
            adjusted[pair] <= ALPHA and primary["bootstrap"]["q025"] > primary["null"]["mean"]
        )
    passing = [pair for pair in pairs if pair_results[pair]["field_cos"]["passes_primary_pair_rule"]]
    return {
        "seed": seed,
        "n_geometry_null": n_null,
        "n_blocked_bootstrap": n_boot,
        "pairs": pair_results,
        "passing_pairs": passing,
        "source_passes": len(passing) >= 2,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--null", type=int, default=N_NULL)
    parser.add_argument("--bootstrap", type=int, default=N_BOOT)
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    args = parser.parse_args()
    root = args.root.resolve()
    seeds = tuple(int(seed) for seed in args.seeds.split(","))
    lock_path = root / "manifests" / "input-lock.json"
    lock = json.loads(lock_path.read_text())
    result: dict[str, Any] = {
        "schema": "lupine.a6_decide.analysis.v1",
        "preregistered_rule": {
            "primary_endpoint": "field_cos",
            "null": "independent Haar SO(3) rotation per model x configuration",
            "familywise_alpha": ALPHA,
            "multiplicity": "Holm within each source across 3 model pairs",
            "source_pass": ">=2 pairs with Holm p<=0.05 and blocked-bootstrap q025 > geometry-null mean",
            "verdict": "SUPPORTED iff OMat24 and >=1 of MPtrj/MatPES pass; REFUTATION iff all gates pass and OMat24 fails; otherwise INCONCLUSIVE",
        },
        "input_lock_sha256": sha256_file(lock_path),
        "models": list(MODELS),
        "seeds": list(seeds),
        "sources": {},
    }
    for source in sorted(lock["sources"]):
        meta = lock["sources"][source]
        if meta.get("status") == "inconclusive":
            result["sources"][source] = {
                "integrity": {
                    "all_integrity_and_information_gates_pass": False,
                    "status": "inconclusive",
                    "failed_gate": meta["failed_gate"],
                    "parquet_path": meta["parquet_path"],
                    "parquet_sha256": meta["parquet_sha256"],
                    "source_identity": {
                        key: meta[key]
                        for key in ("dataset", "frozen_source_identity", "resolved_split", "dataset_revision", "url")
                        if key in meta
                    },
                    "eligible_blocks": meta["eligible_blocks"],
                    "valid_blocks": meta["valid_blocks"],
                    "valid_configurations": meta["valid_configurations"],
                    "maximum_valid_configurations_per_block": meta["maximum_valid_configurations_per_block"],
                },
                "seed_analyses": [],
                "classification_stable_across_seeds": None,
                "source_passes": None,
            }
            continue
        data, integrity = load_source(root, source, lock)
        analyses = []
        for seed in seeds:
            print(f"{source}: seed {seed}", flush=True)
            analyses.append(analyze_source(data, seed, args.null, args.bootstrap))
        classifications = [analysis["source_passes"] for analysis in analyses]
        stable = len(set(classifications)) == 1
        result["sources"][source] = {
            "integrity": integrity,
            "seed_analyses": analyses,
            "classification_stable_across_seeds": stable,
            "source_passes": classifications[0] if stable else None,
        }
    all_gates = all(source["integrity"]["all_integrity_and_information_gates_pass"] for source in result["sources"].values())
    all_stable = all(source["classification_stable_across_seeds"] is True for source in result["sources"].values())
    omat_pass = result["sources"][OMAT]["source_passes"]
    fit_pass = any(result["sources"][source]["source_passes"] is True for source in ("mptrj", "matpes-pbe-2025.2"))
    if not all_gates or not all_stable:
        verdict = "INCONCLUSIVE"
    elif omat_pass and fit_pass:
        verdict = "SUPPORTED beyond mechanical coupling"
    elif omat_pass is False:
        verdict = "SCOPE-TRUNCATING REFUTATION at sampled trajectory scale"
    else:
        verdict = "INCONCLUSIVE"
    result["decision"] = {
        "all_integrity_and_information_gates_pass": all_gates,
        "all_source_classifications_stable_across_seeds": all_stable,
        "failed_source_gates": {
            source: data["integrity"]["failed_gate"]
            for source, data in result["sources"].items()
            if not data["integrity"]["all_integrity_and_information_gates_pass"]
        },
        "omat24_passes": omat_pass,
        "mptrj_or_matpes_passes": fit_pass,
        "verdict": verdict,
    }
    output = args.output or root / "a6_decide_analysis.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["decision"], indent=2, sort_keys=True))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
