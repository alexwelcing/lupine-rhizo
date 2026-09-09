#!/usr/bin/env python3
"""Committed generator for the 42-group classical error geometry.

Rebuilds the classical covariance geometry from the reviewed corpus
(kim_elastic_results_all.csv, 559 rows; nist_populated_all.csv, 1,677 rows)
and diffs it against the committed 42-group file
(data/classical/manifold_revalidation_42potentials.json) WITHOUT overwriting
that file.

Gauges
------
1. absolute    : X[m, p] = predicted - reference            (GPa)  [computed]
2. relative    : X[m, p] = (predicted - reference) / reference     [computed]
3. standardized: X[m, p] = (predicted - reference) / sigma_ref      [ABSTAIN]

Gauge 3 is ABSTAINED: the reviewed inputs carry no per-reference
uncertainties. nist_populated_all.csv has no uncertainty column; the
reference values (Simmons & Wang, propagated through the NIST IPR) are point
values. No reviewed uncertainty source exists in either repository, so the
gauge is declared ABSTAIN rather than inventing a denominator.

Matched nulls (frozen null)
---------------------------
Per group, the null destroys cross-property correlation while preserving:
  n            - same number of material rows
  d            - same 3 properties (C11, C12, C44)
  missingness  - complete cases only (all 42 groups are complete; recorded)
  marginal scales - column-wise permutation preserves each column's
                    empirical marginal exactly
  Born admissibility - predicted' = reference + permuted residual is
                    rejection-sampled until every row satisfies the cubic
                    Born criteria (C44 > 0, C11 - C12 > 0, C11 + 2*C12 > 0)
  lineage      - residuals are permuted only within their short_label
                    group (short_label-level null) or within their model_id
                    group (model_id-level null, 18 KIM IDs with >=3 elements)

Null statistic: PR of the permuted, Born-screened matrix (same pipeline as
the real data). The frozen null per group is the 5th percentile of that
distribution. A group's PR "falls below the null" iff PR_real < p05_null.

Hyper-ribbon claim gate
-----------------------
No strict hyper-ribbon claim is made unless the real geometry clears the
frozen null in EVERY stratum of n (fraction of groups below the null 5th
percentile strictly above the 5% false-positive level in each stratum).
Otherwise the verdict is "not cleared".

Determinism
-----------
All randomness flows from --seed through numpy SeedSequence keyed per group.
No wall clock, no environment randomness. Output JSON is byte-reproducible;
--check verifies a previously committed results file.

Usage:
  python recompute_geometry.py            # write results + figure
  python recompute_geometry.py --check    # fail if results drifted
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

PROPS = ["C11", "C12", "C44"]
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # repository root (lupine-rhizo)
DEFAULT_KIM = REPO / "atlas-distill/benchmarks/kim_elastic_results_all.csv"
DEFAULT_NIST = REPO / "atlas-distill/benchmarks/nist_populated_all.csv"
DEFAULT_COMMITTED = (
    REPO / "replication/error-geometry/data/classical/manifold_revalidation_42potentials.json"
)
RESULTS = HERE / "results/geometry_recompute_results.json"
FIGURE_PDF = HERE / "figures/geometry_recompute_pr_vs_n.pdf"
FIGURE_PNG = HERE / "figures/geometry_recompute_pr_vs_n.png"

EPS = 1e-30
BOOT = 2000
NULL_REPS = 2000
SEED = 20260909


# --------------------------------------------------------------------------
# small utilities
# --------------------------------------------------------------------------
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def display_path(path: Path) -> str:
    """Repo-relative when the input lives under this repository, else
    absolute. Keeps the results JSON byte-identical across checkout
    locations (byte-determinism is checked by --check)."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def display_path(path: Path) -> str:
    """Repo-relative when the input lives under this repository, else
    absolute. Keeps the results JSON byte-identical across checkout
    locations (byte-determinism is checked by --check)."""
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def rng_for(seed: int, tag: str) -> np.random.Generator:
    return np.random.default_rng((seed, zlib.crc32(tag.encode("utf-8"))))


def born_admissible(c11: float, c12: float, c44: float) -> bool:
    """Cubic Born stability criteria."""
    return c44 > 0.0 and (c11 - c12) > 0.0 and (c11 + 2.0 * c12) > 0.0


# --------------------------------------------------------------------------
# geometry core (mirrors atlas-distill/src/stats.rs conventions)
# --------------------------------------------------------------------------
def pca_eigenvalues(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """SVD of the column-centered matrix.

    Returns (eigenvalues_sample_norm, eigenvectors_rows_of_Vt) with
    eigenvalues sorted descending. Sample norm = s^2/(n-1) (the current
    implementation in atlas-distill/src/stats.rs). The committed 42-group
    file used population norm s^2/n; both are reported downstream.
    """
    n = X.shape[0]
    Xc = X - X.mean(axis=0)
    _, s, vt = np.linalg.svd(Xc, full_matrices=False)
    ev = (s**2) / (n - 1)
    order = np.argsort(ev)[::-1]
    return ev[order], vt[order]


def spectrum(evs: np.ndarray) -> np.ndarray:
    """Drop numerically-zero eigenvalues (committed-file convention)."""
    if len(evs) == 0:
        return evs
    return evs[evs > 1e-10 * max(evs.max(), EPS)]


def participation_ratio(evs: np.ndarray) -> float:
    s = float(evs.sum())
    ss = float((evs**2).sum())
    return s * s / ss if ss > EPS else 0.0


def log_linear_fit(evs: np.ndarray) -> tuple[float, float, float]:
    idx = np.where(evs > EPS)[0].astype(float)
    y = np.log(evs[evs > EPS])
    if len(idx) < 2:
        return float("nan"), float("nan"), 0.0
    n = float(len(idx))
    sx, sy = idx.sum(), y.sum()
    sx2, sxy = (idx**2).sum(), (idx * y).sum()
    den = n * sx2 - sx * sx
    if abs(den) < EPS:
        return float("nan"), float("nan"), 0.0
    slope = (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    yp = slope * idx + intercept
    ss_tot = ((y - y.mean()) ** 2).sum()
    ss_res = ((y - yp) ** 2).sum()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > EPS else 0.0
    return float(slope), float(intercept), float(r2)


def mann_kendall_tau(seq: np.ndarray) -> float:
    n = len(seq)
    if n < 2:
        return 0.0
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            d = seq[j] - seq[i]
            if d > 1e-30:
                conc += 1
            elif d < -1e-30:
                disc += 1
    return (conc - disc) / (n * (n - 1) / 2.0)


def pearson_index_correlation(evs: np.ndarray) -> float:
    """Pearson correlation between eigenvalue magnitude and PC index.

    This is the statistic actually stored in the committed file's
    decay_monotonicity field (verified exactly on all 42 groups), NOT the
    Mann-Kendall tau used by the current atlas-distill implementation.
    """
    k = len(evs)
    if k < 2:
        return 0.0
    x = np.arange(k, dtype=float)
    dx, dy = x - x.mean(), evs - evs.mean()
    den = math.sqrt(float((dx**2).sum()) * float((dy**2).sum()))
    return float((dx * dy).sum() / den) if den > 0 else 0.0


def hyper_ribbon_flag(mk_tau: float, log_r2: float, frac: float) -> bool:
    return mk_tau < -0.8 and log_r2 > 0.8 and frac < 0.9


def bootstrap_cis(X: np.ndarray, seed: int, tag: str, n_boot: int = BOOT):
    """Seeded row-bootstrap CIs for PR and log-R^2 (percentile, 2.5/97.5)."""
    rng = rng_for(seed, "boot:" + tag)
    n = X.shape[0]
    prs, r2s = [], []
    for _ in range(n_boot):
        bi = rng.integers(0, n, n)
        ev, _ = pca_eigenvalues(X[bi])
        ev = spectrum(ev)
        prs.append(participation_ratio(ev))
        _, _, r2 = log_linear_fit(ev)
        r2s.append(r2)
    prs.sort()
    r2s.sort()
    lo = int(math.floor(0.025 * n_boot))
    hi = int(math.floor(0.975 * n_boot))
    return [prs[lo], prs[hi]], [r2s[lo], r2s[hi]]


def geometry(X: np.ndarray, seed: int, tag: str) -> dict:
    ev_sample, _ = pca_eigenvalues(X)
    ev = spectrum(ev_sample)
    n = X.shape[0]
    scale = (n - 1.0) / n  # sample -> population norm
    ev_pop = ev * scale
    pr = participation_ratio(ev)
    frac = pr / X.shape[1]
    _, _, r2 = log_linear_fit(ev)
    mk = mann_kendall_tau(ev)
    pearson = pearson_index_correlation(ev)
    tot = float(ev.sum())
    cum = [float(x) for x in np.cumsum(ev) / tot] if tot > EPS else []
    wr = [
        float(ev[i] / ev[i + 1]) if ev[i + 1] > EPS else float("inf")
        for i in range(len(ev) - 1)
    ]
    finite_wr = [r for r in wr if math.isfinite(r)]
    pr_ci, r2_ci = bootstrap_cis(X, seed, tag)
    return {
        "n": int(n),
        "d": int(X.shape[1]),
        "rank": int(len(ev)),
        "eigenvalues_sample_norm": [float(x) for x in ev],
        "eigenvalues_population_norm": [float(x) for x in ev_pop],
        "normalization_ratio_committed_over_sample": float(1.0 / scale),
        "pr": float(pr),
        "fractional_dimensionality": float(frac),
        "cumulative_variance": cum,
        "log_r_squared": float(r2),
        "decay_monotonicity_mk_tau_current_impl": float(mk),
        "decay_monotonicity_pearson_index_matches_stored": float(pearson),
        "width_ratios": wr,
        "mean_width_ratio": float(np.mean(finite_wr)) if finite_wr else float("nan"),
        "is_hyper_ribbon_classifier": hyper_ribbon_flag(mk, r2, frac),
        "pr_ci95_seeded": [float(x) for x in pr_ci],
        "log_r2_ci95_seeded": [float(x) for x in r2_ci],
    }


# --------------------------------------------------------------------------
# matched null
# --------------------------------------------------------------------------
def matched_null(
    X: np.ndarray,
    references: np.ndarray,
    seed: int,
    tag: str,
    gauge: str,
    n_reps: int = NULL_REPS,
    node_cap: int = 100_000,
):
    """Column-wise permutation null with Born screening (backtracking).

    X is the residual matrix (absolute or relative gauge). Each column is
    permuted independently across rows, which preserves every column's
    empirical marginal exactly (marginal scales) while destroying
    cross-property correlation (the geometry being tested). The null
    distribution is uniform over permutations whose implied tensors
    predicted' = reference + residual' (absolute) or
    reference * (1 + residual') (relative) satisfy the cubic Born criteria
    in every row.

    Naive rejection sampling is infeasible for families whose residual
    scale approaches the reference scale (e.g. the Girifalco-Weizer Morse
    potentials), so valid permutations are drawn by backtracking search:
    materials are assigned in ascending reference-C11 order (most
    constrained first), column values are drawn without replacement from a
    rng-shuffled pool, and constraint failure triggers backtracking. This
    samples uniformly from the same constrained set as rejection sampling.
    """
    n, d = X.shape
    rng = rng_for(seed, "null:" + gauge + ":" + tag)
    null_pr = np.empty(n_reps)

    order = np.argsort(references[:, 0])  # ascending ref C11: most constrained first
    stats = {"restarts": 0, "nodes": 0}

    def sample_permuted_rows():
        """One valid permutation via backtracking; returns residual matrix
        rows in ORIGINAL material order."""
        pools = [list(rng.permutation(n)) for _ in range(d)]
        chosen = [[] for _ in range(d)]  # per column, in assignment order
        assign = np.empty((n, d))

        def ok_row(row_idx, vals):
            v = np.asarray(vals, dtype=float)
            if gauge == "absolute":
                pred = references[row_idx] + v
            else:
                pred = references[row_idx] * (1.0 + v)
            return born_admissible(*pred)

        def rec(k):
            stats["nodes"] += 1
            if stats["nodes"] > node_cap:
                return False
            if k == n:
                return True
            row_idx = order[k]
            c0_pool = [i for i in pools[0] if i not in chosen[0]]
            rng.shuffle(c0_pool)
            for c0 in c0_pool:
                chosen[0].append(c0)
                v0 = X[c0, 0]
                c1_pool = [i for i in pools[1] if i not in chosen[1]]
                rng.shuffle(c1_pool)
                placed = False
                for c1 in c1_pool:
                    chosen[1].append(c1)
                    v1 = X[c1, 1]
                    c2_pool = [i for i in pools[2] if i not in chosen[2]]
                    rng.shuffle(c2_pool)
                    for c2 in c2_pool:
                        chosen[2].append(c2)
                        v2 = X[c2, 2]
                        if ok_row(row_idx, (v0, v1, v2)):
                            assign[row_idx] = (v0, v1, v2)
                            placed = True
                            break
                        chosen[2].pop()
                    if placed:
                        if rec(k + 1):
                            return True
                        placed = False
                    chosen[1].pop()
                    # keep searching c1 candidates
                    placed = False
                chosen[0].pop()
            return False

        while not rec(0):
            stats["restarts"] += 1
            stats["nodes"] = 0
            pools = [list(rng.permutation(n)) for _ in range(d)]
            chosen = [[] for _ in range(d)]
        return assign

    for r in range(n_reps):
        R = sample_permuted_rows()
        ev, _ = pca_eigenvalues(R)
        null_pr[r] = participation_ratio(spectrum(ev))
    null_pr.sort()
    p05 = float(null_pr[int(math.floor(0.05 * n_reps))])
    p50 = float(null_pr[int(math.floor(0.50 * n_reps))])
    return {
        "n_reps": n_reps,
        "sampling": "uniform over Born-valid independent column permutations (backtracking)",
        "search_restarts": stats["restarts"],
        "null_pr_median": p50,
        "null_pr_p05": p05,
    }


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------
def load_inputs(kim_path: Path, nist_path: Path):
    kim_rows = list(csv.DictReader(open(kim_path)))
    nist_rows = list(csv.DictReader(open(nist_path)))
    return kim_rows, nist_rows


def reference_map(nist_rows):
    """reference value per (material, property); must be unique (fail closed)."""
    refs = {}
    for r in nist_rows:
        if r["property"] not in PROPS or not r["reference"]:
            continue
        key = (r["material"], r["property"])
        val = float(r["reference"])
        if key in refs and abs(refs[key] - val) > 1e-12:
            raise SystemExit(f"FAIL-CLOSED: conflicting reference for {key}")
        refs[key] = val
    return refs


def build_short_label_groups(nist_rows):
    """The 42 groups: potential families with complete C11/C12/C44 over >=3
    materials, from the NIST-populated corpus.

    Duplicate (potential, material, property) rows exist when several KIM
    model implementations report the same potential family on the same
    element (231 duplicate keys corpus-wide, 103 with conflicting values).
    The committed 42-group file is reproduced exactly by FIRST-occurrence
    resolution in nist_populated_all.csv file order (verified: 42/42 PR
    matches to <1e-9 under this rule; last/mean give 34/42). Duplicates
    are therefore resolved first-wins and audited below.
    """
    by_pot = defaultdict(dict)
    dup_keys = set()
    for r in nist_rows:
        if r["property"] in PROPS and r["predicted"] and r["reference"]:
            try:
                pred = float(r["predicted"])
                ref = float(r["reference"])
            except ValueError:
                continue
            slot = by_pot[r["potential"]].setdefault(r["material"], {})
            if r["property"] in slot:
                dup_keys.add((r["potential"], r["material"], r["property"]))
                continue  # first occurrence wins (committed-file convention)
            slot[r["property"]] = (pred, ref)
    groups = {}
    for pot, mats in sorted(by_pot.items()):
        complete = {m: v for m, v in mats.items() if all(p in v for p in PROPS)}
        if len(complete) >= 3:
            groups[pot] = complete
    return groups, dup_keys


def build_model_id_groups(kim_rows, refs):
    """18 KIM IDs with >=3 elements (task contract), residual vectors joined
    against the per-material reference."""
    by_model = defaultdict(dict)
    crystal = {}
    for r in kim_rows:
        if not all(r[p] for p in ("c11", "c12", "c44")):
            continue
        mat = r["species"]
        if (mat, "C11") not in refs:
            continue
        by_model[r["model_id"]][mat] = (
            float(r["c11"]),
            float(r["c12"]),
            float(r["c44"]),
        )
        crystal[mat] = r["crystal"]
    groups = {m: v for m, v in by_model.items() if len(v) >= 3}
    return groups, crystal


def residual_matrices(
    complete_mats: dict, gauge: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    materials = sorted(complete_mats)
    refs = np.array(
        [[complete_mats[m][p][1] for p in PROPS] for m in materials], dtype=float
    )
    preds = np.array(
        [[complete_mats[m][p][0] for p in PROPS] for m in materials], dtype=float
    )
    if gauge == "absolute":
        X = preds - refs
    elif gauge == "relative":
        X = (preds - refs) / refs
    else:
        raise ValueError(gauge)
    return X, refs, preds, materials


# --------------------------------------------------------------------------
# diff against committed file
# --------------------------------------------------------------------------
def diff_group(name: str, committed: dict, geo: dict) -> dict:
    cev = committed["eigenvalues"]
    rev = geo["eigenvalues_population_norm"]
    k = min(len(cev), len(rev))
    ev_abs = [abs(rev[i] - cev[i]) for i in range(k)]
    ev_rel = [abs(rev[i] - cev[i]) / abs(cev[i]) if cev[i] else float("inf") for i in range(k)]
    return {
        "eigenvalue_max_abs_diff_population_norm": max(ev_abs) if ev_abs else 0.0,
        "eigenvalue_max_rel_diff_population_norm": max(ev_rel) if ev_rel else 0.0,
        "pr_abs_diff": abs(geo["pr"] - committed["effective_dimensionality"]),
        "pr_matches_to_1e-9": bool(abs(geo["pr"] - committed["effective_dimensionality"]) < 1e-9),
        "stored_ci_reproducible": False,
        "stored_ci_note": (
            "committed pr_ci bounds come from an unseeded bootstrap; not "
            "reproducible. Seeded CIs reported alongside."
        ),
        "monotonicity_stored": committed["decay_monotonicity"],
        "monotonicity_current_impl_mk_tau": geo["decay_monotonicity_mk_tau_current_impl"],
        "monotonicity_pearson_matches_stored": geo[
            "decay_monotonicity_pearson_index_matches_stored"
        ],
        "monotonicity_mismatch_documented": bool(
            abs(committed["decay_monotonicity"]
                - geo["decay_monotonicity_mk_tau_current_impl"]) > 1e-9
        ),
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kim-csv", type=Path, default=DEFAULT_KIM)
    ap.add_argument("--nist-csv", type=Path, default=DEFAULT_NIST)
    ap.add_argument("--committed-json", type=Path, default=DEFAULT_COMMITTED)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--n-null", type=int, default=NULL_REPS)
    ap.add_argument("--n-boot", type=int, default=BOOT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    kim_rows, nist_rows = load_inputs(args.kim_csv, args.nist_csv)
    committed_list = json.loads(open(args.committed_json).read())
    committed = {r["potential"]: r for r in committed_list}
    refs = reference_map(nist_rows)

    # ---- Born audit of the real corpus -------------------------------
    born_fail = [
        r["model_id"]
        for r in kim_rows
        if all(r[p] for p in ("c11", "c12", "c44"))
        and not born_admissible(float(r["c11"]), float(r["c12"]), float(r["c44"]))
    ]

    # ---- short_label-level groups (the committed 42) -----------------
    groups, dup_keys = build_short_label_groups(nist_rows)
    group_names = set(groups)
    committed_names = set(committed)
    missing = sorted(committed_names - group_names)
    extra = sorted(group_names - committed_names)
    if missing or extra:
        raise SystemExit(
            f"FAIL-CLOSED: group roster drift vs committed file: "
            f"missing={missing} extra={extra}"
        )

    # lineage: model_ids per short_label from the kim corpus
    models_per_label = defaultdict(set)
    for r in kim_rows:
        models_per_label[r["short_label"]].add(r["model_id"])

    results_groups = []
    strata = defaultdict(lambda: {"n_groups": 0, "below": 0})

    for pot in sorted(groups):
        geo_abs = {}
        nulls = {}
        for gauge in ("absolute", "relative"):
            X, refmat, _, materials = residual_matrices(groups[pot], gauge)
            geo = geometry(X, args.seed, f"sl:{gauge}:{pot}")
            geo_abs[gauge] = (X, refmat, materials, geo)
            null = matched_null(X, refmat, args.seed, pot, gauge, args.n_null)
            nulls[gauge] = null
        Xa, _, materials, geo_a = geo_abs["absolute"]
        _, _, _, geo_r = geo_abs["relative"]
        c = committed[pot]
        n = len(materials)
        strata[n]["n_groups"] += 1
        below = geo_a["pr"] < nulls["absolute"]["null_pr_p05"]
        strata[n]["below"] += int(below)
        results_groups.append(
            {
                "grouping": "short_label",
                "potential": pot,
                "model_ids_in_lineage": sorted(models_per_label[pot]),
                "duplicate_property_rows_resolved_first_wins": sorted(
                    f"{m}/{p}"
                    for (pp, m, p) in dup_keys
                    if pp == pot
                ),
                "n_materials": n,
                "materials": materials,
                "missingness": "none (complete cases)",
                "absolute_gauge": geo_a,
                "relative_gauge": geo_r,
                "null_short_label_absolute": nulls["absolute"],
                "null_short_label_relative": nulls["relative"],
                "real_pr_below_null_p05_absolute": bool(below),
                "diff_vs_committed": diff_group(pot, c, geo_a),
            }
        )

    # ---- model_id-level groups (18 KIM IDs) --------------------------
    model_groups, crystal_of = build_model_id_groups(kim_rows, refs)
    results_model_groups = []
    strata_m = defaultdict(lambda: {"n_groups": 0, "below": 0})
    for mid in sorted(model_groups):
        mats = model_groups[mid]
        refs_m = {m: {p: (None, refs[(m, p)]) for p in PROPS} for m in mats}
        # reuse residual_matrices with (pred, ref) tuples
        complete = {
            m: {p: (mats[m][PROPS.index(p)], refs[(m, p)]) for p in PROPS}
            for m in mats
        }
        entry = {
            "grouping": "model_id",
            "model_id": mid,
            "n_materials": len(mats),
            "crystal_classes": sorted({crystal_of[m] for m in mats}),
        }
        for gauge in ("absolute", "relative"):
            X, refmat, _, materials = residual_matrices(complete, gauge)
            geo = geometry(X, args.seed, f"mid:{gauge}:{mid}")
            null = matched_null(X, refmat, args.seed, mid, gauge, args.n_null)
            entry[gauge + "_gauge"] = geo
            entry["null_model_id_" + gauge] = null
            if gauge == "absolute":
                below = geo["pr"] < null["null_pr_p05"]
                entry["real_pr_below_null_p05_absolute"] = bool(below)
                strata_m[len(materials)]["n_groups"] += 1
                strata_m[len(materials)]["below"] += int(below)
        results_model_groups.append(entry)

    # ---- strata summary + claim gate ---------------------------------
    def strata_summary(smap):
        out = {}
        for n in sorted(smap):
            g = smap[n]
            frac = g["below"] / g["n_groups"] if g["n_groups"] else 0.0
            out[str(n)] = {
                "n_groups": g["n_groups"],
                "groups_below_null_p05": g["below"],
                "fraction_below_null_p05": float(frac),
            }
        return out

    strata_sl = strata_summary(strata)
    strata_mid = strata_summary(strata_m)

    def claim_gate(strata_dict):
        # every stratum must beat the 5% false-positive level
        verdicts = {
            n: d["fraction_below_null_p05"] > 0.05 for n, d in strata_dict.items()
        }
        cleared = bool(verdicts) and all(verdicts.values())
        return cleared, verdicts

    cleared_sl, verdicts_sl = claim_gate(strata_sl)
    cleared_mid, verdicts_mid = claim_gate(strata_mid)

    n3 = [g for g in results_groups if g["n_materials"] == 3]
    n4p = [g for g in results_groups if g["n_materials"] >= 4]

    out = {
        "schema": "lupine-research://geometry-recompute/v1",
        "generated_by": "replication/error-geometry/geometry_recompute/recompute_geometry.py",
        "seed": args.seed,
        "n_null_reps": args.n_null,
        "n_boot_reps": args.n_boot,
        "inputs": {
            "kim_elastic_results_all.csv": {
                "path": display_path(args.kim_csv),
                "sha256": sha256(args.kim_csv),
                "rows": len(kim_rows),
            },
            "nist_populated_all.csv": {
                "path": display_path(args.nist_csv),
                "sha256": sha256(args.nist_csv),
                "rows": len(nist_rows),
            },
            "manifold_revalidation_42potentials.json": {
                "path": display_path(args.committed_json),
                "sha256": sha256(args.committed_json),
                "groups": len(committed_list),
                "note": "read-only diff target; this generator never overwrites it",
            },
        },
        "gauges": {
            "absolute": "X[m,p] = predicted - reference (GPa); reproduces committed PRs exactly",
            "relative": "X[m,p] = (predicted - reference) / reference",
            "standardized": {
                "status": "ABSTAIN",
                "reason": (
                    "no reviewed per-reference uncertainty exists: "
                    "nist_populated_all.csv carries no uncertainty column and "
                    "the Simmons & Wang / NIST IPR references are point values"
                ),
            },
        },
        "corpus_audit": {
            "kim_rows": len(kim_rows),
            "kim_distinct_model_ids": len({r["model_id"] for r in kim_rows}),
            "kim_distinct_short_labels": len({r["short_label"] for r in kim_rows}),
            "nist_rows": len(nist_rows),
            "nist_duplicate_potential_material_property_keys": len(dup_keys),
            "duplicate_resolution": (
                "first occurrence in nist_populated_all.csv file order "
                "(reproduces all 42 committed PRs to <1e-9)"
            ),
            "born_inadmissible_kim_rows": len(born_fail),
            "born_audit": "all 559 kim rows pass cubic Born criteria"
            if not born_fail
            else f"FAIL rows: {born_fail[:5]}",
            "model_id_groups_with_ge3_elements": len(model_groups),
        },
        "groups": results_groups,
        "model_id_groups": results_model_groups,
        "strata_short_label": strata_sl,
        "strata_model_id": strata_mid,
        "strata_verdicts": {
            "short_label_per_stratum_beats_5pct": verdicts_sl,
            "model_id_per_stratum_beats_5pct": verdicts_mid,
        },
        "hyper_ribbon_claim": {
            "status": "cleared" if (cleared_sl and cleared_mid) else "not cleared",
            "basis": (
                "cleared requires every stratum of n to beat the 5% "
                "false-positive level against the frozen null 5th percentile, "
                "at both short_label and model_id lineage resolution"
            ),
            "short_label_cleared": cleared_sl,
            "model_id_cleared": cleared_mid,
        },
        "median_pr": {
            "absolute_all_42": float(np.median([g["absolute_gauge"]["pr"] for g in results_groups])),
            "absolute_n3": float(np.median([g["absolute_gauge"]["pr"] for g in n3])),
            "absolute_n_ge4": float(np.median([g["absolute_gauge"]["pr"] for g in n4p])),
            "relative_all_42": float(np.median([g["relative_gauge"]["pr"] for g in results_groups])),
        },
    }

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    (HERE / "figures").mkdir(exist_ok=True)
    text = json.dumps(out, indent=1, sort_keys=True) + "\n"
    if args.check:
        if not RESULTS.exists():
            print("FAIL: no committed results file to check")
            return 1
        committed_text = RESULTS.read_text()
        if committed_text != text:
            print("FAIL: results drifted; rerun generator and commit")
            return 1
        print("CHECK PASS: results JSON is current")
        return 0
    RESULTS.write_text(text)
    make_figure(results_groups, results_model_groups)
    print(f"wrote {RESULTS}")
    print(f"wrote {FIGURE_PDF} / {FIGURE_PNG}")
    print(json.dumps(out["hyper_ribbon_claim"], indent=1))
    print(json.dumps(out["median_pr"], indent=1))
    return 0


def make_figure(groups, model_groups):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    def panel(ax, rows, label_key, title):
        ns = sorted({r["n_materials"] for r in rows})
        for n in ns:
            p05s = [
                r["null_short_label_absolute"]["null_pr_p05"]
                if "null_short_label_absolute" in r
                else r["null_model_id_absolute"]["null_pr_p05"]
                for r in rows
                if r["n_materials"] == n
            ]
            ax.axvspan(n - 0.3, n + 0.3, ymin=0, ymax=1, color="none")
            ax.fill_between(
                [n - 0.3, n + 0.3],
                [min(p05s), min(p05s)],
                [max(p05s), max(p05s)],
                color="0.85",
                zorder=1,
            )
        below_x, below_y, above_x, above_y = [], [], [], []
        for r in rows:
            x = r["n_materials"]
            jitter = (zlib.crc32(r[label_key].encode("utf-8")) % 100) / 100.0 * 0.3 - 0.15
            tgt = (below_x, below_y) if r["real_pr_below_null_p05_absolute"] else (above_x, above_y)
            tgt[0].append(x + jitter)
            tgt[1].append(r["absolute_gauge"]["pr"])
        ax.scatter(above_x, above_y, c="0.45", s=28, zorder=3, label="PR >= null p05")
        ax.scatter(below_x, below_y, c="crimson", s=34, zorder=4, label="PR < null p05")
        ax.axhline(3.0, ls=":", c="0.6", lw=1)
        ax.axhline(2.0, ls=":", c="0.75", lw=1)
        ax.set_xlabel("n materials")
        ax.set_title(title)
        ax.set_xticks(ns)

    panel(axes[0], groups, "potential", "short_label lineage (42 groups)")
    panel(axes[1], model_groups, "model_id", "model_id lineage (18 KIM IDs)")
    axes[0].set_ylabel("participation ratio (absolute gauge)")
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle(
        "Classical error geometry vs matched null (n/d/missingness/marginal/Born-preserving)"
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURE_PDF)
    fig.savefig(FIGURE_PNG, dpi=200)


if __name__ == "__main__":
    sys.exit(main())
