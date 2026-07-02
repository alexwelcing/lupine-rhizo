"""Statistical hardening for paper/environment-error-field-2026-07-02.md (SS3.3-3.4).

Referee-proofs the three headline statistics:
  1. Blind gamma_110 environment-field prediction (r = 0.906 over 36 cells)
     with material-clustered bootstrap CIs and a within-model permutation null.
  2. Family-exponent equality/separation via paired bootstrap over materials.
  3. LOO log-affine vs 8-knot isotonic (and correction-vs-raw) with paired
     per-cell differences and material-clustered bootstrap CIs.
  4. Multiple-testing inventory (Holm within claim families).

Inputs:  data/y_matrix_runs/bound/*.evidence.json  (lupine.mlip.calc_evidence.v1)
         data/y_matrix_runs/*_fcc_*.json           (lupine.statics_run.v1, a0)
Outputs: data/y_matrix_runs/analysis/statistical_hardening.json
         data/y_matrix_runs/analysis/STATS.md is written by the caller from the
         JSON (this script emits JSON only; STATS.md is authored prose).

Dependencies: stdlib + numpy only (scipy deliberately avoided; isotonic
regression is a hand-rolled pool-adjacent-violators implementation).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

EV_A2_TO_J_M2 = 16.0218  # 1 eV/Angstrom^2 = 16.0218 J/m^2
SEED = 20260702
N_BOOT = 10_000
N_PERM = 10_000

REPO = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO / "data" / "y_matrix_runs"
BOUND_DIR = RUNS_DIR / "bound"
OUT_PATH = RUNS_DIR / "analysis" / "statistical_hardening.json"

MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
FCC_MATERIALS = ("Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr")
SURFACE_PROPS = ("gamma_100", "gamma_110", "gamma_111")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One bound evidence cell: (material, structure, model) with properties."""

    material: str
    structure: str
    model: str
    props: Mapping[str, tuple[float, float | None]]  # name -> (value, ref)


def load_bound_cells(directory: Path) -> tuple[Cell, ...]:
    cells: list[Cell] = []
    for path in sorted(directory.glob("*.evidence.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "lupine.mlip.calc_evidence.v1":
            raise ValueError(f"{path}: unexpected schema {payload.get('schema')!r}")
        stem_parts = path.stem.replace(".evidence", "").split("_")
        structure = stem_parts[1]
        model = "_".join(stem_parts[2:]) or str(payload["source"]["model_id"])
        model = model.replace("_", "-") if "-" not in model else model
        source_model = str(payload["source"]["model_id"])
        if source_model != model:
            model = source_model  # trust payload over filename
        props: dict[str, tuple[float, float | None]] = {}
        for prop in payload["properties"]:
            value = prop.get("value")
            ref = prop.get("reference_value")
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{path}: non-finite value for {prop.get('name')}")
            props[str(prop["name"])] = (
                float(value),
                float(ref) if isinstance(ref, (int, float)) else None,
            )
        cells.append(
            Cell(
                material=str(payload["material"]),
                structure=structure,
                model=model,
                props=props,
            )
        )
    return tuple(cells)


def load_fcc_a0(directory: Path) -> dict[tuple[str, str], float]:
    """Model-relaxed a0 (Angstrom) from statics_run files, fcc only."""
    a0: dict[tuple[str, str], float] = {}
    for path in sorted(directory.glob("*_fcc_*.json")):
        if path.name.endswith(".evidence.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "lupine.statics_run.v1":
            continue
        value = payload["results"]["lattice"]["values"]["a0_angstrom"]
        a0[(str(payload["material"]), str(payload["model_id"]))] = float(value)
    return a0


# --------------------------------------------------------------------------
# Small statistics helpers (stdlib + numpy only)
# --------------------------------------------------------------------------


def pearson_r(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xd = x - x.mean()
    yd = y - y.mean()
    denom = math.sqrt(float(xd @ xd) * float(yd @ yd))
    if denom == 0.0:
        return float("nan")
    return float(xd @ yd) / denom


def loglog_slope(refs: np.ndarray, preds: np.ndarray) -> tuple[float, float]:
    """OLS of log(pred) on log(ref): returns (alpha, log_c)."""
    x = np.log(np.asarray(refs, dtype=float))
    y = np.log(np.asarray(preds, dtype=float))
    xd = x - x.mean()
    var = float(xd @ xd)
    if var == 0.0:
        return float("nan"), float("nan")
    alpha = float(xd @ (y - y.mean())) / var
    return alpha, float(y.mean() - alpha * x.mean())


def percentile_ci(draws: np.ndarray, lo: float = 2.5, hi: float = 97.5) -> list[float]:
    clean = draws[np.isfinite(draws)]
    return [float(np.percentile(clean, lo)), float(np.percentile(clean, hi))]


def boot_two_sided_p(draws: np.ndarray, null_value: float = 0.0) -> float:
    """Two-sided bootstrap p: 2 * min tail fraction relative to null_value."""
    clean = draws[np.isfinite(draws)]
    lo = float(np.mean(clean <= null_value))
    hi = float(np.mean(clean >= null_value))
    return min(1.0, 2.0 * min(lo, hi))


def pava_nondecreasing(y: Sequence[float], w: Sequence[float]) -> np.ndarray:
    """Weighted pool-adjacent-violators; returns non-decreasing fit to y."""
    blocks: list[list[float]] = []  # [mean, weight, count]
    for yi, wi in zip(y, w):
        blocks.append([float(yi), float(wi), 1.0])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            m2, w2, c2 = blocks.pop()
            m1, w1, c1 = blocks.pop()
            wt = w1 + w2
            blocks.append([(m1 * w1 + m2 * w2) / wt, wt, c1 + c2])
    out: list[float] = []
    for mean, _, count in blocks:
        out.extend([mean] * int(count))
    return np.array(out, dtype=float)


def isotonic_knots(
    train_p: np.ndarray, train_t: np.ndarray, n_knots: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """Quantile-binned (<=n_knots) monotone knot table mapping P -> T."""
    order = np.argsort(train_p)
    p_sorted = train_p[order]
    t_sorted = train_t[order]
    edges = np.quantile(p_sorted, np.linspace(0.0, 1.0, n_knots + 1))
    knot_x: list[float] = []
    knot_y: list[float] = []
    knot_w: list[float] = []
    for i in range(n_knots):
        lo, hi = edges[i], edges[i + 1]
        if i == n_knots - 1:
            mask = (p_sorted >= lo) & (p_sorted <= hi)
        else:
            mask = (p_sorted >= lo) & (p_sorted < hi)
        if not mask.any():
            continue
        knot_x.append(float(p_sorted[mask].mean()))
        knot_y.append(float(t_sorted[mask].mean()))
        knot_w.append(float(mask.sum()))
    y_iso = pava_nondecreasing(knot_y, knot_w)
    return np.array(knot_x, dtype=float), y_iso


# --------------------------------------------------------------------------
# Part 1 - blind gamma_110 prediction
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BlindCell:
    material: str
    model: str
    pred_err: float
    actual_err: float


def build_blind_cells(
    cells: Sequence[Cell], a0_map: Mapping[tuple[str, str], float]
) -> tuple[BlindCell, ...]:
    out: list[BlindCell] = []
    by_key = {(c.material, c.model): c for c in cells if c.structure == "fcc"}
    for model in MODELS:
        for material in FCC_MATERIALS:
            cell = by_key[(material, model)]
            a0 = a0_map[(material, model)]

            def err(prop: str, c: Cell = cell) -> float:
                value, ref = c.props[prop]
                if ref is None:
                    raise ValueError(f"{c.material}/{c.model}: no ref for {prop}")
                return value - ref

            de8 = err("gamma_100") * (a0**2 / 2.0) / EV_A2_TO_J_M2
            de9 = err("gamma_111") * (math.sqrt(3.0) / 4.0 * a0**2) / EV_A2_TO_J_M2
            de11 = err("vacancy_formation_energy") / 12.0
            pred = (2.0 * de8 - de9 + de11) / (a0**2 / math.sqrt(2.0) / EV_A2_TO_J_M2)
            out.append(
                BlindCell(
                    material=material,
                    model=model,
                    pred_err=pred,
                    actual_err=err("gamma_110"),
                )
            )
    return tuple(out)


def blind_arrays(
    blind: Sequence[BlindCell],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(pred, actual, material_index, model_index) arrays over the 36 cells."""
    pred = np.array([b.pred_err for b in blind])
    actual = np.array([b.actual_err for b in blind])
    mat_idx = np.array([FCC_MATERIALS.index(b.material) for b in blind])
    model_idx = np.array([MODELS.index(b.model) for b in blind])
    return pred, actual, mat_idx, model_idx


def cluster_bootstrap(
    stat: Callable[[np.ndarray], float],
    mat_idx: np.ndarray,
    n_materials: int,
    rng: np.random.Generator,
    n_draws: int = N_BOOT,
) -> np.ndarray:
    """Bootstrap resampling MATERIALS; stat receives selected cell indices."""
    cells_of = [np.flatnonzero(mat_idx == m) for m in range(n_materials)]
    draws = np.empty(n_draws)
    for i in range(n_draws):
        chosen = rng.integers(0, n_materials, size=n_materials)
        idx = np.concatenate([cells_of[m] for m in chosen])
        draws[i] = stat(idx)
    return draws


def part1_blind(blind: Sequence[BlindCell]) -> dict:
    pred, actual, mat_idx, model_idx = blind_arrays(blind)
    rng = np.random.default_rng(SEED)

    overall_r = pearson_r(pred, actual)
    per_model_r = {
        model: pearson_r(pred[model_idx == k], actual[model_idx == k])
        for k, model in enumerate(MODELS)
    }

    residual = np.abs(actual - pred)
    zero_resid = np.abs(actual)
    med_resid = float(np.median(residual))
    med_zero = float(np.median(zero_resid))

    # strict wins at x1e4 integer precision (mirrors the Lean integer check)
    resid_scaled = np.rint(residual * 1e4).astype(int)
    zero_scaled = np.rint(zero_resid * 1e4).astype(int)
    wins = int(np.sum(resid_scaled < zero_scaled))
    ties = int(np.sum(resid_scaled == zero_scaled))
    sign_p = min(
        1.0,
        2.0 * sum(math.comb(36, k) for k in range(wins, 37)) / 2.0**36,
    )

    r_draws = cluster_bootstrap(
        lambda idx: pearson_r(pred[idx], actual[idx]), mat_idx, len(FCC_MATERIALS), rng
    )
    med_diff_draws = cluster_bootstrap(
        lambda idx: float(np.median(residual[idx]) - np.median(zero_resid[idx])),
        mat_idx,
        len(FCC_MATERIALS),
        rng,
    )

    # permutation null: within each model, permute material labels of pred
    perm_rng = np.random.default_rng(SEED + 1)
    perm_r = np.empty(N_PERM)
    perm_r_per_model = {model: np.empty(N_PERM) for model in MODELS}
    model_cells = [np.flatnonzero(model_idx == k) for k in range(len(MODELS))]
    for i in range(N_PERM):
        pred_perm = pred.copy()
        for k, model in enumerate(MODELS):
            idx = model_cells[k]
            pred_perm[idx] = pred[idx][perm_rng.permutation(len(idx))]
            perm_r_per_model[model][i] = pearson_r(pred_perm[idx], actual[idx])
        perm_r[i] = pearson_r(pred_perm, actual)
    p_perm = float((1 + np.sum(perm_r >= overall_r)) / (N_PERM + 1))
    p_perm_per_model = {
        model: float(
            (1 + np.sum(perm_r_per_model[model] >= per_model_r[model])) / (N_PERM + 1)
        )
        for model in MODELS
    }

    return {
        "cells": [
            {
                "material": b.material,
                "model": b.model,
                "pred_gamma110_err_j_m2": b.pred_err,
                "actual_gamma110_err_j_m2": b.actual_err,
            }
            for b in blind
        ],
        "overall_r_36_cells": overall_r,
        "per_model_r_n9": per_model_r,
        "leave_one_material_out_r": {
            material: pearson_r(pred[mat_idx != m], actual[mat_idx != m])
            for m, material in enumerate(FCC_MATERIALS)
        },
        "per_model_permutation_p_one_sided": p_perm_per_model,
        "clustered_bootstrap_r": {
            "n_draws": N_BOOT,
            "seed": SEED,
            "resample_unit": "material (9 clusters of 4 cells)",
            "ci95": percentile_ci(r_draws),
            "median": float(np.median(r_draws)),
        },
        "median_residual": {
            "field_prediction_j_m2": med_resid,
            "predict_zero_j_m2": med_zero,
            "difference": med_resid - med_zero,
            "clustered_bootstrap_ci95_of_difference": percentile_ci(med_diff_draws),
            "bootstrap_two_sided_p": boot_two_sided_p(med_diff_draws),
        },
        "strict_wins_x1e4": {
            "wins": wins,
            "ties": ties,
            "losses": 36 - wins - ties,
            "naive_sign_test_two_sided_p": sign_p,
            "caveat": "sign test treats 36 cells as independent; they are not",
        },
        "permutation_null": {
            "n_perms": N_PERM,
            "seed": SEED + 1,
            "scheme": "permute material labels of predictions within each model",
            "observed_r": overall_r,
            "p_one_sided": p_perm,
            "null_mean": float(np.mean(perm_r)),
            "null_sd": float(np.std(perm_r)),
            "null_p95": float(np.percentile(perm_r, 95)),
            "null_p99": float(np.percentile(perm_r, 99)),
            "null_max": float(np.max(perm_r)),
        },
    }


# --------------------------------------------------------------------------
# Part 2 - family-exponent equality
# --------------------------------------------------------------------------


def family_points(
    cells: Sequence[Cell], model: str, family: str, include_g110: bool = True
) -> list[tuple[str, float, float]]:
    """(material, ref, pred) points for one model and property family."""
    points: list[tuple[str, float, float]] = []
    for cell in cells:
        if cell.model != model:
            continue
        if family == "surfaces":
            for prop in SURFACE_PROPS:
                if prop == "gamma_110" and not include_g110:
                    continue
                pair = cell.props.get(prop)
                if pair and pair[1] is not None:
                    points.append((cell.material, pair[1], pair[0]))
        elif family == "vacancy":
            pair = cell.props.get("vacancy_formation_energy")
            if pair and pair[1] is not None:
                points.append((cell.material, pair[1], pair[0]))
        elif family == "b0":
            pair = cell.props.get("B0")
            if pair and pair[1] is not None:
                points.append((cell.material, pair[1], pair[0]))
        else:
            raise ValueError(f"unknown family {family!r}")
    return points


def fit_alpha(points: Sequence[tuple[str, float, float]]) -> float:
    refs = np.array([p[1] for p in points])
    preds = np.array([p[2] for p in points])
    return loglog_slope(refs, preds)[0]


def paired_alpha_bootstrap(
    points_a: Sequence[tuple[str, float, float]],
    points_b: Sequence[tuple[str, float, float]],
    rng: np.random.Generator,
    n_draws: int = N_BOOT,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Resample materials; refit both slopes; return (diffs, alpha_a draws, n_skipped)."""
    materials = sorted({p[0] for p in points_a} | {p[0] for p in points_b})
    by_mat_a = {m: [p for p in points_a if p[0] == m] for m in materials}
    by_mat_b = {m: [p for p in points_b if p[0] == m] for m in materials}
    diffs = np.full(n_draws, np.nan)
    alpha_a_draws = np.full(n_draws, np.nan)
    skipped = 0
    n_mat = len(materials)
    for i in range(n_draws):
        chosen = rng.integers(0, n_mat, size=n_mat)
        sample_a = [p for j in chosen for p in by_mat_a[materials[j]]]
        sample_b = [p for j in chosen for p in by_mat_b[materials[j]]]
        if len({p[1] for p in sample_a}) < 2 or len({p[1] for p in sample_b}) < 2:
            skipped += 1
            continue
        alpha_a = fit_alpha(sample_a)
        alpha_b = fit_alpha(sample_b)
        alpha_a_draws[i] = alpha_a
        diffs[i] = alpha_a - alpha_b
    return diffs, alpha_a_draws, skipped


def part2_exponents(cells: Sequence[Cell]) -> dict:
    rng = np.random.default_rng(SEED + 2)
    result: dict = {"per_model": {}, "notes": {}}
    surface_alphas: dict[str, float] = {}
    surface_boot_var: dict[str, float] = {}

    for model in MODELS:
        surf = family_points(cells, model, "surfaces", include_g110=True)
        surf_no110 = family_points(cells, model, "surfaces", include_g110=False)
        vac = family_points(cells, model, "vacancy")
        b0 = family_points(cells, model, "b0")

        alpha_surf = fit_alpha(surf)
        alpha_surf_no110 = fit_alpha(surf_no110)
        alpha_vac = fit_alpha(vac)
        alpha_b0 = fit_alpha(b0)
        surface_alphas[model] = alpha_surf

        diff_sv, alpha_surf_draws, skip_sv = paired_alpha_bootstrap(surf, vac, rng)
        diff_sb, _, skip_sb = paired_alpha_bootstrap(surf, b0, rng)
        surface_boot_var[model] = float(np.nanvar(alpha_surf_draws, ddof=1))

        ci_sv = percentile_ci(diff_sv)
        ci_sb = percentile_ci(diff_sb)
        result["per_model"][model] = {
            "n_points": {"surfaces": len(surf), "vacancy": len(vac), "b0": len(b0)},
            "alpha": {
                "surfaces": alpha_surf,
                "surfaces_excl_gamma110": alpha_surf_no110,
                "vacancy": alpha_vac,
                "b0": alpha_b0,
            },
            "alpha_surfaces_bootstrap_ci95": percentile_ci(alpha_surf_draws),
            "surf_minus_vac": {
                "point": alpha_surf - alpha_vac,
                "ci95": ci_sv,
                "excludes_zero": bool(ci_sv[0] > 0 or ci_sv[1] < 0),
                "bootstrap_two_sided_p": boot_two_sided_p(diff_sv),
                "skipped_draws": skip_sv,
            },
            "surf_minus_b0": {
                "point": alpha_surf - alpha_b0,
                "ci95": ci_sb,
                "excludes_zero": bool(ci_sb[0] > 0 or ci_sb[1] < 0),
                "bootstrap_two_sided_p": boot_two_sided_p(diff_sb),
                "skipped_draws": skip_sb,
            },
        }

    alphas = np.array([surface_alphas[m] for m in MODELS])
    between_var = float(np.var(alphas, ddof=1))
    within_var = float(np.mean([surface_boot_var[m] for m in MODELS]))
    result["cross_model_surface_alpha"] = {
        "values": surface_alphas,
        "between_model_variance": between_var,
        "mean_within_model_bootstrap_variance": within_var,
        "ratio_between_over_within": between_var / within_var,
        "between_model_sd": math.sqrt(between_var),
        "mean_within_model_bootstrap_sd": math.sqrt(within_var),
    }
    result["notes"]["bootstrap"] = (
        f"paired bootstrap over materials, {N_BOOT} draws, seed {SEED + 2}; "
        "both family slopes refit on each draw with the same material resample"
    )
    return result


# --------------------------------------------------------------------------
# Part 3 - LOO comparisons on surfaces
# --------------------------------------------------------------------------


def loo_errors(points: Sequence[tuple[str, float, float]]) -> dict[str, np.ndarray]:
    """Per-cell LOO relative errors: raw / log-affine / 8-knot isotonic."""
    n = len(points)
    refs = np.array([p[1] for p in points])
    preds = np.array([p[2] for p in points])
    raw = np.abs(preds - refs) / refs
    logaff = np.empty(n)
    iso = np.empty(n)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        alpha, log_c = loglog_slope(refs[mask], preds[mask])
        corrected = math.exp((math.log(preds[i]) - log_c) / alpha)
        logaff[i] = abs(corrected - refs[i]) / refs[i]
        knot_x, knot_y = isotonic_knots(preds[mask], refs[mask])
        iso_corrected = float(np.interp(preds[i], knot_x, knot_y))
        iso[i] = abs(iso_corrected - refs[i]) / refs[i]
    return {"raw": raw, "log_affine": logaff, "isotonic8": iso}


def clustered_median_ci(
    values: np.ndarray,
    materials: Sequence[str],
    rng: np.random.Generator,
    n_draws: int = N_BOOT,
) -> dict:
    unique = sorted(set(materials))
    mat_arr = np.array(materials)
    cells_of = [np.flatnonzero(mat_arr == m) for m in unique]
    draws = np.empty(n_draws)
    for i in range(n_draws):
        chosen = rng.integers(0, len(unique), size=len(unique))
        idx = np.concatenate([cells_of[m] for m in chosen])
        draws[i] = float(np.median(values[idx]))
    ci = percentile_ci(draws)
    return {
        "median": float(np.median(values)),
        "ci95_clustered": ci,
        "excludes_zero": bool(ci[0] > 0 or ci[1] < 0),
        "bootstrap_two_sided_p": boot_two_sided_p(draws),
    }


def part3_loo(cells: Sequence[Cell]) -> dict:
    rng = np.random.default_rng(SEED + 3)
    out: dict = {"per_model": {}}
    for model in MODELS:
        points = family_points(cells, model, "surfaces", include_g110=True)
        materials = [p[0] for p in points]
        errs = loo_errors(points)
        iso_minus_logaff = errs["isotonic8"] - errs["log_affine"]
        raw_minus_logaff = errs["raw"] - errs["log_affine"]
        out["per_model"][model] = {
            "n_cells": len(points),
            "median_loo_relative_error": {
                "raw": float(np.median(errs["raw"])),
                "log_affine": float(np.median(errs["log_affine"])),
                "isotonic8": float(np.median(errs["isotonic8"])),
            },
            "isotonic_minus_log_affine": clustered_median_ci(
                iso_minus_logaff, materials, rng
            ),
            "raw_minus_log_affine": clustered_median_ci(
                raw_minus_logaff, materials, rng
            ),
        }
    out["notes"] = {
        "loo_unit": "one (material, facet) cell held out per fold",
        "log_affine": "fit log(pred)=log c + alpha log(ref) on train; "
        "correct held-out via (P/c)^(1/alpha)",
        "isotonic8": "8 quantile bins of train P; bin means; weighted PAVA; "
        "piecewise-linear interpolation, clamped at ends",
        "bootstrap": f"median of paired per-cell differences, materials "
        f"resampled as clusters, {N_BOOT} draws, seed {SEED + 3}",
    }
    return out


# --------------------------------------------------------------------------
# Part 4 - multiple-testing adjudication (Holm within claim families)
# --------------------------------------------------------------------------


def holm(pvalues: Mapping[str, float], alpha: float = 0.05) -> dict:
    """Holm step-down: adjusted p-values and rejection flags."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return {
        "m_tests": m,
        "alpha": alpha,
        "raw_p": dict(items),
        "holm_adjusted_p": adjusted,
        "reject_at_alpha": {k: bool(v <= alpha) for k, v in adjusted.items()},
    }


def part4_multiplicity(p1: dict, p2: dict, p3: dict) -> dict:
    family_blind = {
        "permutation_r": p1["permutation_null"]["p_one_sided"],
        "median_residual_vs_zero": p1["median_residual"]["bootstrap_two_sided_p"],
        "win_count_sign_test_naive": p1["strict_wins_x1e4"][
            "naive_sign_test_two_sided_p"
        ],
    }
    family_exponents = {}
    for model in MODELS:
        pm = p2["per_model"][model]
        family_exponents[f"{model}:surf_minus_vac"] = pm["surf_minus_vac"][
            "bootstrap_two_sided_p"
        ]
        family_exponents[f"{model}:surf_minus_b0"] = pm["surf_minus_b0"][
            "bootstrap_two_sided_p"
        ]
    family_loo = {}
    for model in ("chgnet", "mace-mp-small"):
        pm = p3["per_model"][model]
        family_loo[f"{model}:isotonic_minus_log_affine"] = pm[
            "isotonic_minus_log_affine"
        ]["bootstrap_two_sided_p"]
        family_loo[f"{model}:raw_minus_log_affine"] = pm["raw_minus_log_affine"][
            "bootstrap_two_sided_p"
        ]
    return {
        "policy": (
            "Holm step-down within each pre-specified claim family; "
            "kernel-checked point facts (orderings, strict inequalities on the "
            "measured dataset) are deterministic dataset properties and carry "
            "no sampling claim, hence no correction; sampling-based inferences "
            "are corrected within family"
        ),
        "paper_test_inventory": {
            "s3_1": {
                "participation_ratio_tests": 6,
                "leading_mode_cosine_tests": 3,
                "defect_vs_bulk_ratio_cis": 3,
            },
            "s3_2": {
                "rank_correlation_estimates": 16,
                "facet_orderings_deterministic": 22,
                "gamma111_exact_permutation_deterministic": 1,
            },
            "s3_3": {
                "loglog_fits": 12,
                "strict_exponent_inequalities_deterministic": 8,
                "prefactor_and_warp_orderings_deterministic": 2,
                "loo_comparisons": 2,
                "one_anchor_transfer": 1,
            },
            "s3_4": {"blind_r": 1, "median_residual": 1, "win_count": 1},
            "s3_6": {
                "eam_loo_degradation": 1,
                "zhou_vs_chgnet_cells_deterministic": 1,
            },
            "approx_sampling_based_inferences": 47,
            "approx_deterministic_point_facts": 34,
        },
        "family_blind_gamma110": holm(family_blind),
        "family_exponent_separation": holm(family_exponents),
        "family_loo_corrections": holm(family_loo),
        "paper_wide_bonferroni_note": (
            "headline blind-prediction permutation p survives even a paper-wide "
            "Bonferroni over ~47 sampling-based tests (threshold ~0.00106)"
        ),
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main() -> None:
    cells = load_bound_cells(BOUND_DIR)
    a0_map = load_fcc_a0(RUNS_DIR)
    blind = build_blind_cells(cells, a0_map)

    p1 = part1_blind(blind)
    p2 = part2_exponents(cells)
    p3 = part3_loo(cells)
    payload = {
        "schema": "lupine.stats_hardening.v1",
        "generated_by": "python/scripts/harden_stats.py",
        "seed": SEED,
        "n_bootstrap": N_BOOT,
        "n_permutations": N_PERM,
        "error_convention": "error = model value - reference value",
        "inputs": {
            "bound_evidence_files": len(list(BOUND_DIR.glob("*.evidence.json"))),
            "fcc_a0_cells": len(a0_map),
        },
        "part1_blind_gamma110": p1,
        "part2_family_exponents": p2,
        "part3_loo_comparisons": p3,
        "part4_multiple_testing": part4_multiplicity(p1, p2, p3),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH}")

    print(f"overall r = {p1['overall_r_36_cells']:.4f}")
    print(f"per-model r: {p1['per_model_r_n9']}")
    print(f"clustered r CI95 = {p1['clustered_bootstrap_r']['ci95']}")
    print(f"median resid {p1['median_residual']}")
    print(f"perm p = {p1['permutation_null']['p_one_sided']}")
    p4 = payload["part4_multiple_testing"]
    for fam in (
        "family_blind_gamma110",
        "family_exponent_separation",
        "family_loo_corrections",
    ):
        print(fam, p4[fam]["reject_at_alpha"])


if __name__ == "__main__":
    main()
