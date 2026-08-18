#!/usr/bin/env python3
"""Independent mechanical checks for the A6-DECIDE analysis artifact."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import analyze_a6_decide as a6

ROOT = Path(__file__).resolve().parent


def main() -> int:
    analysis = json.loads((ROOT / "a6_decide_analysis.json").read_text())
    assert analysis["seeds"] == [42, 1729, 20260803]
    assert analysis["decision"]["all_integrity_and_information_gates_pass"] is False
    assert analysis["decision"]["all_source_classifications_stable_across_seeds"] is False
    assert analysis["decision"]["verdict"] == "INCONCLUSIVE"
    assert analysis["decision"]["failed_source_gates"] == {
        "mptrj": (
            "MPtrj test has 0 trajectory blocks with >= 8 eligible configurations; "
            "frozen minimum is 30 independently bootstrappable blocks with >= 8 "
            "configurations per retained block and >= 240 total configurations; "
            "deterministic sampling target is 50 blocks"
        )
    }
    mptrj = analysis["sources"]["mptrj"]
    assert mptrj["integrity"]["source_identity"]["frozen_source_identity"] == "MPtrj test"
    assert mptrj["integrity"]["source_identity"]["resolved_split"] == "test"
    assert mptrj["integrity"]["eligible_blocks"] == 0
    assert mptrj["integrity"]["maximum_valid_configurations_per_block"] == 4
    assert mptrj["source_passes"] is None
    assert mptrj["seed_analyses"] == []
    for name, source in analysis["sources"].items():
        if name == "mptrj":
            continue
        assert source["integrity"]["blocks"] >= 30
        assert source["integrity"]["configurations"] >= 240
        assert min(source["integrity"]["configs_per_block"]) >= 8
        assert len(source["seed_analyses"]) == 3
        for seed_run in source["seed_analyses"]:
            assert seed_run["n_geometry_null"] == 5000
            assert seed_run["n_blocked_bootstrap"] == 2000
            assert len(seed_run["pairs"]) == 3

    # Check that the vectorized sufficient-statistic implementation exactly
    # matches direct rotation/concatenation for independently sampled rotations.
    lock = json.loads((ROOT / "manifests" / "input-lock.json").read_text())
    data, _ = a6.load_source(ROOT, "matpes-pbe-2025.2", lock)
    pair = "chgnet|mace-mp-small"
    suff = a6.pair_sufficient(data, *pair.split("|"))
    rng = np.random.default_rng(123)
    rotations = a6.haar_so3(rng, (7, len(a6.MODELS), 400))
    ia = a6.MODELS.index("chgnet")
    ib = a6.MODELS.index("mace-mp-small")
    ra = rotations[:, ia]
    rb = rotations[:, ib]
    raw = np.einsum("rcki,cij,rckj->r", ra, suff["cross"], rb, optimize=True)
    sum_a = np.einsum("rcki,ci->r", ra, suff["axis_sum_a"], optimize=True)
    sum_b = np.einsum("rcki,ci->r", rb, suff["axis_sum_b"], optimize=True)
    vectorized = a6.centered_cos(
        raw, sum_a, sum_b, suff["sq_a"].sum(), suff["sq_b"].sum(), suff["dimensions"].sum()
    )
    direct = []
    for replicate in range(7):
        left = np.concatenate([
            values @ ra[replicate, config].T
            for config, values in enumerate(data["residuals"]["chgnet"])
        ]).ravel()
        right = np.concatenate([
            values @ rb[replicate, config].T
            for config, values in enumerate(data["residuals"]["mace-mp-small"])
        ]).ravel()
        left -= left.mean()
        right -= right.mean()
        direct.append(float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right))))
    assert np.allclose(vectorized, np.asarray(direct), atol=2e-15, rtol=0)
    assert np.allclose(
        rotations @ np.swapaxes(rotations, -1, -2), np.eye(3), atol=2e-15, rtol=0
    )
    assert np.allclose(np.linalg.det(rotations), 1.0, atol=2e-15, rtol=0)
    print("PASS: fail-closed MPtrj test gate, retained-source artifact gates, replicate counts, Haar SO(3), and vectorized-vs-direct field_cos")
    print(f"max_abs_vectorization_error={np.max(np.abs(vectorized - np.asarray(direct))):.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
