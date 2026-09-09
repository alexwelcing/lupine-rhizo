#!/usr/bin/env python3
"""Build the canonical results object and figures for the TMS 2027 proceedings draft.

Every headline number in manuscript.tex that is *recomputable* from committed data is
derived here from the source rows and written to results.json together with the SHA-256
of each source file. Numbers that are quoted from frozen reports (not recomputed) are
listed in results.json under "quoted" with their source path so the binding is explicit.

Sources live in two repositories:
  * lupine        (read-only here)  -> $LUPINE_REPO, default ../../../lupine
  * lupine-rhizo  (this repository)

Usage (from lupine-rhizo root):
  python paper/tms2027-proceedings/build_artifacts.py            # build
  python paper/tms2027-proceedings/build_artifacts.py --check    # verify results.json is current

Fails closed: a missing source file or a headline mismatch is an error, not a warning.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RHIZO = HERE.parents[1]
LUPINE = Path(os.environ.get("LUPINE_REPO", RHIZO.parent / "lupine")).resolve()

SOURCES = {
    "kim_tensors": LUPINE / "atlas-distill/benchmarks/kim_elastic_results_all.csv",
    "nist_rows": LUPINE / "atlas-distill/benchmarks/nist_populated_all.csv",
    "geometry_42": LUPINE / "replication/error-geometry/data/classical/manifold_revalidation_42potentials.json",
    "canonical_numbers": LUPINE / "replication/error-geometry/data/classical/canonical_numbers.json",
    "immi_paper": LUPINE / "paper/immi-paper.tex",
    "round2_manuscript": LUPINE / "paper2/ProjectionLaw_Round2.md",
    "anchor_spec": LUPINE / "replication/error-geometry/prereg_r2b_dft_anchor_spec.md",
    "h3_blocker": LUPINE / "docs/science/h3_blocker.md",
    "global_operator_lock": RHIZO / "paper/negative-results-preprint/global-operator.lock.json",
    "layer2_results": RHIZO / "mlip-elastic-benchmark/layer2-3x3x3-results-2026-06-29.md",
    "layer2_operator": RHIZO / "paper/lupine-layer2-3x3x3-operator.md",
    "operator_diagnosis": RHIZO / "mlip-elastic-benchmark/operator-failure-diagnosis-2026-06-27.md",
    "y_matrix": RHIZO / "docs/plans/y-matrix-confirmatory-results-2026-07-01.md",
    "round3_report": RHIZO / "data/candidates/round3/ROUND3_REPORT.md",
    "round4_report": RHIZO / "data/candidates/round4/ROUND4_REPORT.md",
    "z1_verdict": RHIZO / "docs/analysis/z1-union-campaign-verdict.md",
    "z1_deferred": RHIZO / "data/candidates/z1-sparse-dft-deferred.json",
    "negative_results": RHIZO / "paper/negative-results-preprint/manuscript.tex",
    "env_field": RHIZO / "paper/environment-error-field-2026-07-02.md",
    "errata": RHIZO / "docs/plans/2026-07-13-errata-and-red-team-dispositions.md",
    "lean_count": RHIZO / "lean-spec/theorem-count.json",
    "sprint_contract": RHIZO / "docs/plans/2026-09-09-tms-manuscript-sprint.md",
}

# Numbers quoted verbatim from frozen reports (not recomputed here). Each entry names the
# file that carries the value so a reviewer can bind the manuscript sentence to a source.
QUOTED = {
    "kim_model_objects_queried": {"value": 965, "source": "immi_paper", "note": "retrieval universe; stated in the classical manuscript methods"},
    "mlip_tensors_total": {"value": 45, "source": "immi_paper", "note": "3 foundation models x 15 elements"},
    "mlip_born_failures": {"value": 7, "source": "immi_paper"},
    "classical_vs_mlip_spearman_rho": {"value": 0.264, "source": "immi_paper"},
    "classical_vs_mlip_spearman_p": {"value": 0.341, "source": "immi_paper"},
    "global_operator_raw_mae_gpa": {"value": 14.5466, "source": "global_operator_lock"},
    "global_operator_corrected_mae_gpa": {"value": 63.3952, "source": "global_operator_lock"},
    "global_operator_raw_ci95": {"value": [10.0843, 19.7229], "source": "global_operator_lock"},
    "global_operator_corrected_ci95": {"value": [57.0699, 69.1756], "source": "global_operator_lock"},
    "global_operator_n_elements": {"value": 16, "source": "global_operator_lock"},
    "layer2_cases": {"value": 128, "source": "layer2_results", "note": "16 metals x 4 MatPES models x 2 functionals"},
    "layer2_raw_mae_gpa": {"value": 17.84, "source": "layer2_results"},
    "layer2_raw_mae_ci95": {"value": [15.51, 20.41], "source": "layer2_results"},
    "layer2_oracle_loo_mae_gpa": {"value": 10.36, "source": "layer2_operator", "note": "oracle directional ceiling: held-out target sets the projection magnitude"},
    "layer2_oracle_loo_ci95": {"value": [8.9, 12.0], "source": "layer2_operator"},
    "layer2_r2scan_vs_pbe_gap_gpa": {"value": 5.65, "source": "layer2_results"},
    "matpes_h1_effect_size": {"value": -0.14, "source": "round2_manuscript", "note": "kill triggered"},
    "matpes_h2a_permutation_p": {"value": 0.13, "source": "round2_manuscript", "note": "kill triggered"},
    "y_matrix_h1_pass_fraction": {"value": "2/6", "source": "y_matrix"},
    "y_matrix_h2_pass_fraction": {"value": "0/3", "source": "y_matrix"},
    "y_matrix_raw_cosine_max": {"value": 0.96, "source": "y_matrix"},
    "y_matrix_null_p95_cosine": {"value": 0.98, "source": "y_matrix"},
    "y_matrix_defect_bulk_ratio_range": {"value": [15.3, 57.0], "source": "y_matrix", "note": "primary matrix, MACE-medium to CHGNet"},
    "round3_group_verdicts": {"value": "FAIL, FAIL", "source": "round3_report"},
    "round3_a0_rocksalt_rel_err": {"value": [1.60, 0.33], "source": "round3_report", "note": "median |rel err| % raw -> corrected"},
    "round3_a0_perovskite_rel_err": {"value": [1.75, 0.74], "source": "round3_report"},
    "round4_confirmatory_wins": {"value": "0/4 rocksalt, 0/1 perovskite", "source": "round4_report"},
    "z1_gate_mev": {"value": 40, "source": "negative_results"},
    "z1_mae_range_mev": {"value": [135.0, 242.5], "source": "negative_results"},
    "z1_completed_paths_range": {"value": [26, 29], "source": "negative_results"},
    "z1_negative_counts": {"value": {"CHGNet": "25/28", "MACE-MP medium": "21/29", "MACE-MP small": "17/26", "MACE-MPA-0 medium": "13/28"}, "source": "negative_results"},
    "z1_gpaw_anchors": {"value": 129, "source": "z1_verdict"},
    "z1_gpaw_active_paths": {"value": 23, "source": "z1_verdict"},
    "z1_deferred_paths": {"value": 7, "source": "z1_deferred"},
    "z3_holdout_mae_ev": {"value": [[0.69, 2.27], [2.11, 5.01], [3.24, 5.00], [4.27, 5.91]], "source": "negative_results", "note": "raw -> corrected, four model-level holdout tests"},
    "env_field_r": {"value": 0.906, "source": "env_field"},
    "env_field_cells": {"value": 36, "source": "env_field"},
    "anchor_registered_metals": {"value": 15, "source": "anchor_spec"},
    "anchor_benchmark_overlap": {"value": 14, "source": "sprint_contract", "note": "15 registered vs 16 benchmarked; Pb registered only, Ca/Sr benchmarked only"},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def derive() -> dict:
    missing = [k for k, p in SOURCES.items() if not p.exists()]
    if missing:
        sys.exit(f"missing source files (fail closed): {missing}")

    rows = list(csv.DictReader(open(SOURCES["kim_tensors"], encoding="utf-8")))
    nist = list(csv.DictReader(open(SOURCES["nist_rows"], encoding="utf-8")))
    groups = json.load(open(SOURCES["geometry_42"], encoding="utf-8"))
    canon = json.load(open(SOURCES["canonical_numbers"], encoding="utf-8"))
    lean = json.load(open(SOURCES["lean_count"], encoding="utf-8"))
    lock = json.load(open(SOURCES["global_operator_lock"], encoding="utf-8"))
    deferred = json.load(open(SOURCES["z1_deferred"], encoding="utf-8"))

    species = Counter(r["species"] for r in rows)
    crystal = Counter(r["crystal"] for r in rows)
    by_label = defaultdict(set)
    by_model_id = defaultdict(set)
    for r in rows:
        by_label[r["short_label"]].add(r["species"])
        by_model_id[r["model_id"]].add(r["species"])

    prs = [g["effective_dimensionality"] for g in groups]
    n_mat = Counter(g["n_materials"] for g in groups)

    def med(xs) -> float:
        xs = list(xs)
        if not xs:
            sys.exit("empty stratum in geometry file (fail closed)")
        return float(statistics.median(xs))

    funnel = {
        "kim_model_objects_queried": QUOTED["kim_model_objects_queried"]["value"],
        "born_stable_model_element_tensors": len(rows),
        "distinct_kim_model_ids": len({r["model_id"] for r in rows}),
        "author_year_short_labels": len(by_label),
        "elements": len(species),
        "scalar_cij_values": len(nist),
        "short_labels_with_ge3_elements": sum(len(v) >= 3 for v in by_label.values()),
        "distinct_model_ids_with_ge3_elements": sum(len(v) >= 3 for v in by_model_id.values()),
        "geometry_groups_committed": len(groups),
        "tensors_by_crystal": dict(crystal),
        "tensors_by_element": dict(sorted(species.items())),
        "cij_components_per_tensor": Counter(r["property"] for r in nist),
    }
    geometry = {
        "n_groups": len(groups),
        "n_materials_distribution": {str(k): v for k, v in sorted(n_mat.items())},
        "groups_with_n3": n_mat.get(3, 0),
        "pr_median": round(med(prs), 4),
        "pr_min": round(min(prs), 4),
        "pr_max": round(max(prs), 4),
        "pr_median_n3_groups": round(med([g["effective_dimensionality"] for g in groups if g["n_materials"] == 3]), 4),
        "pr_median_n_ge4_groups": round(med([g["effective_dimensionality"] for g in groups if g["n_materials"] >= 4]), 4),
        "groups_flagged_hyper_ribbon": sum(bool(g["is_hyper_ribbon"]) for g in groups),
        "groups_pr_ci_upper_ge2": sum(g["pr_ci_upper"] >= 2.0 for g in groups),
        "groups_pr_ci_upper_ge2p9": sum(g["pr_ci_upper"] >= 2.9 for g in groups),
        "n3_groups_with_two_eigenvalues": sum(len(g["eigenvalues"]) == 2 for g in groups if g["n_materials"] == 3),
        "canonical_numbers_file": canon,
        "per_group": [
            {
                "potential": g["potential"],
                "n_materials": g["n_materials"],
                "pr": round(g["effective_dimensionality"], 4),
                "pr_ci": [round(g["pr_ci_lower"], 4), round(g["pr_ci_upper"], 4)],
                "n_eigenvalues": len(g["eigenvalues"]),
                "cum_var_1": round(g["cumulative_variance"][0], 4),
            }
            for g in sorted(groups, key=lambda g: (g["n_materials"], g["potential"]))
        ],
    }
    lean_summary = {
        "count": lean["count"],
        "modules": lean["modules"],
        "zero_sorry": lean["zero_sorry"],
        "counted_at": lean["counted_at"],
    }
    lock_measure = lock["measurement"]
    consistency = {
        "canonical_pr_median_matches": abs(canon["pr_median"] - round(med(prs), 3)) < 1e-9,
        "canonical_n_potentials_matches": canon["n_potentials"] == len(groups),
        "lock_raw_mae_matches_quoted": abs(lock_measure["raw_mae_gpa"] - QUOTED["global_operator_raw_mae_gpa"]["value"]) < 1e-9,
        "lock_corrected_mae_matches_quoted": abs(lock_measure["corrected_mae_gpa"] - QUOTED["global_operator_corrected_mae_gpa"]["value"]) < 1e-9,
        "deferred_paths_matches_quoted": len(deferred["deferred_paths"]) == QUOTED["z1_deferred_paths"]["value"],
        "funnel_559_423_233_1677": (len(rows), funnel["distinct_kim_model_ids"], funnel["author_year_short_labels"], len(nist)) == (559, 423, 233, 1677),
    }
    if not all(consistency.values()):
        sys.exit(f"headline consistency check failed: {consistency}")

    return {
        "schema": "lupine.tms2027.proceedings.results.v1",
        "note": "Derived numbers are recomputed from committed source rows; quoted numbers are copied from frozen reports named in 'source'. Live-ledger 352-row snapshot NOT recovered as of build: its exact numbers are omitted per the sprint contract.",
        "sources": {k: {"path": str(p.relative_to(RHIZO)) if p.is_relative_to(RHIZO) else f"lupine/{p.relative_to(LUPINE)}", "sha256": sha256(p)} for k, p in SOURCES.items()},
        "derived": {"funnel": funnel, "geometry": geometry, "lean": lean_summary},
        "quoted": QUOTED,
        "consistency": consistency,
        "recovery_outputs_present": (RHIZO / "data/candidates/tms2027").exists(),
    }


def figures(res: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig_dir = HERE / "figures"
    fig_dir.mkdir(exist_ok=True)
    f = res["derived"]["funnel"]
    g = res["derived"]["geometry"]
    q = res["quoted"]

    # Fig 1: denominator funnel
    labels = ["KIM model\nobjects queried", "Born-stable\nmodel-element\ntensors", "Distinct KIM\nmodel IDs", "Author/year\nshort labels", "Multi-element\ngeometry groups\n(>=3 elements)"]
    vals = [f["kim_model_objects_queried"], f["born_stable_model_element_tensors"], f["distinct_kim_model_ids"], f["author_year_short_labels"], f["geometry_groups_committed"]]
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    bars = ax.barh(range(len(vals))[::-1], vals, color=["#9aa5b1", "#4c6a92", "#4c6a92", "#4c6a92", "#b23a48"])
    ax.set_yticks(range(len(vals))[::-1])
    ax.set_yticklabels(labels, fontsize=8)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 8, b.get_y() + b.get_height() / 2, f"{v:,}", va="center", fontsize=9)
    ax.set_xlim(0, 1100)
    ax.set_xlabel("count (unit named per row)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig1_denominator_funnel.pdf")
    plt.close(fig)

    # Fig 2: PR vs group size with bootstrap intervals
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for row in g["per_group"]:
        n = row["n_materials"]
        col = "#b23a48" if n == 3 else "#2f4b7c"
        ax.errorbar(n, row["pr"], yerr=[[row["pr"] - row["pr_ci"][0]], [row["pr_ci"][1] - row["pr"]]], fmt="o", ms=4, color=col, ecolor=col, alpha=0.55, capsize=2, lw=0.8)
    ax.axhline(2.0, ls="--", lw=0.8, color="grey")
    ax.axhline(3.0, ls=":", lw=0.8, color="grey")
    ax.text(12.3, 2.03, "PR = 2 (rank limit for n = 3 centered)", fontsize=7, color="grey", ha="right")
    ax.text(12.3, 3.03, "PR = 3 (isotropic)", fontsize=7, color="grey", ha="right")
    ax.set_xlabel("elements per group (n)")
    ax.set_ylabel("participation ratio (of 3)")
    ax.set_xticks(sorted({r["n_materials"] for r in g["per_group"]}))
    ax.set_ylim(0.8, 3.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(f"42 classical groups; red = {g['groups_with_n3']} groups with n = 3; bars = stored PR intervals", fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig2_pr_vs_group_size.pdf")
    plt.close(fig)

    # Fig 3: correction arms, kept in two separate panels (different benchmarks, targets, and estimands)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.5, 3.0))
    raw, cor = q["global_operator_raw_mae_gpa"]["value"], q["global_operator_corrected_mae_gpa"]["value"]
    rci, cci = q["global_operator_raw_ci95"]["value"], q["global_operator_corrected_ci95"]["value"]
    a1.bar([0, 1], [raw, cor], color=["#4c6a92", "#b23a48"], yerr=[[raw - rci[0], cor - cci[0]], [rci[1] - raw, cci[1] - cor]], capsize=4)
    a1.set_xticks([0, 1])
    a1.set_xticklabels(["raw", "global LOO-PCA\n(deployable form)"], fontsize=8)
    a1.set_ylabel("mean $C_{ij}$ MAE (GPa)")
    a1.set_title("(a) 16 metals, TensorNet/PBE vs $T_{\\mathrm{PBE},0K}$\nprospective operator: harm", fontsize=8)
    a1.spines[["top", "right"]].set_visible(False)
    o_raw, o_cor = q["layer2_raw_mae_gpa"]["value"], q["layer2_oracle_loo_mae_gpa"]["value"]
    orci, occi = q["layer2_raw_mae_ci95"]["value"], q["layer2_oracle_loo_ci95"]["value"]
    a2.bar([0, 1], [o_raw, o_cor], color=["#4c6a92", "#e0b252"], hatch=["", "//"], yerr=[[o_raw - orci[0], o_cor - occi[0]], [orci[1] - o_raw, occi[1] - o_cor]], capsize=4)
    a2.set_xticks([0, 1])
    a2.set_xticklabels(["raw", "LOO direction +\nheld-out magnitude\n(oracle ceiling)"], fontsize=8)
    a2.set_title("(b) 128 cases, 4 MatPES models x 2 functionals\ndirectional ceiling, NOT a prediction", fontsize=8)
    a2.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig3_correction_arms.pdf")
    plt.close(fig)


    # Fig 4: reference-tier stack with the pending anchor
    fig, ax = plt.subplots(figsize=(6.5, 2.9))
    ax.axis("off")
    tiers = [
        (0.78, "#4c6a92", "Tier 1  Prediction controls", "completed MLIP outputs (MACE, CHGNet, Orb, MatPES)  -  not truth", "solid"),
        (0.52, "#7a8fa6", "Tier 2  Reference targets", "curated 0 K table: published PBE tensors, PW91 fallback (Au), scalar-rescaled r2SCAN; experiment", "solid"),
        (0.26, "#b23a48", "Tier 3  Computed all-electron anchor", "paired PBE / r2SCAN elastic tensors under one frozen protocol  -  PREREGISTERED, NOT EXECUTED", "dashed"),
    ]
    for y, col, head, body, ls in tiers:
        ax.add_patch(Rectangle((0.02, y - 0.1), 0.96, 0.2, fill=(ls == "solid"), facecolor=col if ls == "solid" else "white", edgecolor=col, lw=1.6, ls=ls, alpha=0.9 if ls == "solid" else 1.0))
        ax.text(0.04, y + 0.035, head, fontsize=9, weight="bold", color="white" if ls == "solid" else col, va="center")
        ax.text(0.04, y - 0.045, body, fontsize=7.2, color="white" if ls == "solid" else col, va="center")
    ax.annotate("", xy=(0.5, 0.36), xytext=(0.5, 0.42), arrowprops=dict(arrowstyle="-|>", color="grey", lw=1))
    ax.annotate("", xy=(0.5, 0.62), xytext=(0.5, 0.68), arrowprops=dict(arrowstyle="-|>", color="grey", lw=1))
    ax.text(0.98, 0.05, f"registered roster {q['anchor_registered_metals']['value']} metals; benchmark 16 metals; overlap {q['anchor_benchmark_overlap']['value']}", fontsize=7, ha="right", color="#b23a48")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig4_reference_stack.pdf")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify results.json matches a fresh derivation")
    args = ap.parse_args()
    res = derive()
    out = HERE / "results.json"
    if args.check:
        if not out.exists():
            sys.exit("results.json missing")
        cur = json.load(open(out, encoding="utf-8"))
        if cur != res:
            sys.exit("results.json is stale relative to sources (fail closed)")
        print("results.json is current; consistency:", res["consistency"])
        return 0
    out.write_text(json.dumps(res, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    figures(res)
    print(json.dumps({"funnel": res["derived"]["funnel"] | {"tensors_by_element": "..."}, "geometry": {k: v for k, v in res["derived"]["geometry"].items() if k != "per_group"}, "consistency": res["consistency"]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
