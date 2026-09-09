#!/usr/bin/env python3
"""Build and render the TMS 2027 proceedings canonical result bundle.

The build step is fail-closed: it reads the reviewed Lupine/Lupine-Rhizo
records, derives the claimed aggregates, and refuses to write if any frozen
manuscript value or cardinality no longer matches. Figure generation reads only
results.json, making that single object the source for manuscript and public
figures.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("SOURCE_DATE_EPOCH", "1788955200")

HERE = Path(__file__).resolve().parent
RHIZO_ROOT = HERE.parents[2]
RESULTS_PATH = HERE / "results.json"
FIGURES = (
    "denominator-provenance-funnel",
    "participation-ratio-by-group-size",
    "correction-falsification",
    "qualification-dft-reference-stack",
)
EXPECTED = {
    "queried_objects": 965,
    "retained_tensors": 559,
    "distinct_model_ids": 423,
    "analysis_groups": 42,
    "n_size_three_groups": 21,
    "raw_mae_gpa": 17.84,
    "oracle_mae_gpa": 10.36,
    "global_raw_mae_gpa": 14.55,
    "global_corrected_mae_gpa": 63.40,
    "spearman_rho": 0.26,
    "spearman_p": 0.34,
    "z1_min_mae_mev": 135.0,
    "z1_max_mae_mev": 242.5,
    "env_r": 0.906,
    "env_cells": 36,
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def source_record(repository: str, root: Path, relative: str, locator: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"required source is missing: {path}")
    return {
        "repository": repository,
        "repository_revision": git_revision(root),
        "path": relative,
        "sha256": sha256(path),
        "locator": locator,
    }


def rounded(value: float, digits: int) -> float:
    return round(float(value), digits)


def assert_equal(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{name}: expected {expected!r}, observed {actual!r}")


def build(lupine_root: Path) -> dict[str, Any]:
    classical_csv = lupine_root / "atlas-distill/benchmarks/kim_elastic_results_all.csv"
    geometry_path = (
        lupine_root
        / "replication/error-geometry/data/classical/manifold_revalidation_42potentials.json"
    )
    alignment_path = (
        lupine_root
        / "Kimi_Agent_Draft Assistance Team Selected/cross_mlip_alignment_born_filtered.json"
    )
    benchmark_path = lupine_root / "data/benchmark_layer2_3x3x3_summary.json"
    operator_path = RHIZO_ROOT / "paper/negative-results-preprint/global-operator.lock.json"
    negative_path = RHIZO_ROOT / "paper/negative-results-preprint/figure-source-data.json"
    env_path = RHIZO_ROOT / "data/y_matrix_runs/analysis/statistical_hardening.json"

    with classical_csv.open(newline="", encoding="utf-8") as handle:
        tensors = list(csv.DictReader(handle))
    geometry_raw = read_json(geometry_path)
    alignment = read_json(alignment_path)
    benchmark = read_json(benchmark_path)
    operator = read_json(operator_path)["measurement"]
    negative = read_json(negative_path)
    env = read_json(env_path)["part1_blind_gamma110"]

    distinct_ids = {row["model_id"] for row in tensors}
    sizes = Counter(int(row["n_materials"]) for row in geometry_raw)
    geometry = [
        {
            "source_row": index,
            "group": row["potential"],
            "n_materials": int(row["n_materials"]),
            "participation_ratio": float(row["effective_dimensionality"]),
            "pr_ci95": [float(row["pr_ci_lower"]), float(row["pr_ci_upper"])],
        }
        for index, row in enumerate(geometry_raw)
    ]

    raw_mae = float(benchmark["summary"]["overall_mean_mae_cij"])
    oracle_mae = 10.36  # reviewed LOO table row; distinct from in-sample JSON correction
    global_raw = rounded(operator["raw_mae_gpa"], 2)
    global_corrected = rounded(operator["corrected_mae_gpa"], 2)
    rho = rounded(alignment["spearman_rho_classical_vs_mlip"], 2)
    spearman_p = rounded(alignment["spearman_p"], 2)
    z1_rows = negative["z1"]["float64"]
    z1_min = rounded(min(row["mae_mev"] for row in z1_rows), 1)
    z1_max = rounded(max(row["mae_mev"] for row in z1_rows), 1)
    z3_rows = negative["z3"]["models"]
    z3_worse = sum(
        row["corrected_holdout_mae_ev"] > row["baseline_holdout_mae_ev"]
        for row in z3_rows
    )
    env_r = rounded(env["overall_r_36_cells"], 3)
    env_cells = len(env["cells"])

    checks = {
        "retained_tensors": len(tensors),
        "distinct_model_ids": len(distinct_ids),
        "analysis_groups": len(geometry),
        "n_size_three_groups": sizes[3],
        "raw_mae_gpa": raw_mae,
        "oracle_mae_gpa": oracle_mae,
        "global_raw_mae_gpa": global_raw,
        "global_corrected_mae_gpa": global_corrected,
        "spearman_rho": rho,
        "spearman_p": spearman_p,
        "z1_min_mae_mev": z1_min,
        "z1_max_mae_mev": z1_max,
        "env_r": env_r,
        "env_cells": env_cells,
    }
    for key, actual in checks.items():
        assert_equal(key, actual, EXPECTED[key])
    assert_equal("z3 corrections worsening holdout", z3_worse, len(z3_rows))
    assert_equal("Z3 tested models", len(z3_rows), 4)

    source_files = {
        "query_universe": source_record(
            "lupine", lupine_root, "paper/immi-paper.tex", "line 122: 965 queried"
        ),
        "classical_tensors": source_record(
            "lupine",
            lupine_root,
            "atlas-distill/benchmarks/kim_elastic_results_all.csv",
            "data rows 1-559; model_id column has 423 distinct values",
        ),
        "geometry": source_record(
            "lupine",
            lupine_root,
            "replication/error-geometry/data/classical/manifold_revalidation_42potentials.json",
            "array rows 0-41; n_materials=3 for 21 rows",
        ),
        "alignment": source_record(
            "lupine",
            lupine_root,
            "Kimi_Agent_Draft Assistance Team Selected/cross_mlip_alignment_born_filtered.json",
            "$.spearman_rho_classical_vs_mlip, $.spearman_p, $.per_element[*]",
        ),
        "benchmark_rows": source_record(
            "lupine",
            lupine_root,
            "data/benchmark_layer2_3x3x3_summary.json",
            "$.rows[0:128], $.summary.overall_mean_mae_cij",
        ),
        "oracle_loo_table": source_record(
            "lupine-rhizo",
            RHIZO_ROOT,
            "paper/lupine-layer2-3x3x3-final-paper.md",
            "lines 99-111; All models table row",
        ),
        "global_operator": source_record(
            "lupine-rhizo",
            RHIZO_ROOT,
            "paper/negative-results-preprint/global-operator.lock.json",
            "$.measurement",
        ),
        "negative_results": source_record(
            "lupine-rhizo",
            RHIZO_ROOT,
            "paper/negative-results-preprint/figure-source-data.json",
            "$.z1.float64[*], $.z3.models[*]",
        ),
        "environment_field": source_record(
            "lupine-rhizo",
            RHIZO_ROOT,
            "data/y_matrix_runs/analysis/statistical_hardening.json",
            "$.part1_blind_gamma110.cells[*], $.part1_blind_gamma110.overall_r_36_cells",
        ),
        "anchor_spec": source_record(
            "lupine",
            lupine_root,
            "replication/error-geometry/prereg_r2b_dft_anchor_spec.md",
            "lines 1-12 and 68-85: STAGED/PENDING and expected schema",
        ),
        "anchor_blocker": source_record(
            "lupine",
            lupine_root,
            "docs/science/h3_blocker.md",
            "lines 1-18: required outputs absent",
        ),
    }

    return {
        "schema": "lupine.tms2027.proceedings-results.v1",
        "status": "evidence-frozen",
        "purpose": (
            "Canonical numeric object for the TMS 2027 proceedings manuscript and public figures. "
            "Values are descriptive or negative results unless explicitly labeled otherwise."
        ),
        "source_files": source_files,
        "denominator_funnel": {
            "stages": [
                {
                    "key": "queried_objects",
                    "count": 965,
                    "unit": "KIM model objects queried",
                    "binding": "source_files.query_universe",
                },
                {
                    "key": "retained_tensors",
                    "count": len(tensors),
                    "unit": "Born-stable model-element tensors",
                    "binding": "source_files.classical_tensors:data rows",
                },
                {
                    "key": "distinct_model_ids",
                    "count": len(distinct_ids),
                    "unit": "distinct KIM model IDs in retained rows",
                    "binding": "source_files.classical_tensors:model_id distinct",
                },
                {
                    "key": "analysis_groups",
                    "count": len(geometry),
                    "unit": "multi-element groups (n >= 3)",
                    "binding": "geometry.groups[*]",
                },
            ],
            "guard": "Objects, tensors, IDs, and analysis groups are different units.",
        },
        "geometry": {
            "groups": geometry,
            "group_size_counts": {str(key): sizes[key] for key in sorted(sizes)},
            "n_size_three_groups": sizes[3],
            "finite_sample_guard": (
                "For n=3, centering three observations in three variables rank-limits covariance "
                "to at most two; low PR is descriptive, not a universal classifier."
            ),
        },
        "elastic_benchmark": {
            "n_cases": int(benchmark["n_tasks"]),
            "raw_aggregate_mae_gpa": raw_mae,
            "oracle_directional_ceiling": {
                "raw_mae_gpa": raw_mae,
                "corrected_mae_gpa": oracle_mae,
                "holdout": "one benchmark row at a time for direction fitting",
                "target_access": "held-out target supplies projection coefficient",
                "deployable": False,
                "binding": "source_files.oracle_loo_table",
            },
            "global_operator_failure": {
                "raw_mae_gpa": global_raw,
                "corrected_mae_gpa": global_corrected,
                "method": operator["bias_method"],
                "target": operator["target"],
                "n_elements": int(operator["n_elements"]),
                "deployable_test": True,
                "outcome": "worsened",
                "binding": "source_files.global_operator:$.measurement",
            },
        },
        "cross_paradigm_alignment": {
            "spearman_rho": rho,
            "p_value": spearman_p,
            "n_elements": len(alignment["per_element"]),
            "outcome": "not_detected",
            "rows": alignment["per_element"],
            "binding": "source_files.alignment",
        },
        "negative_and_conditional_results": {
            "z1": {
                "gate_mev": float(negative["z1"]["gate_mev"]),
                "mae_range_mev": [z1_min, z1_max],
                "models": z1_rows,
                "outcome": "all four models fail the gate",
                "binding": "source_files.negative_results:$.z1.float64[*]",
            },
            "z3": {
                "models": z3_rows,
                "tested": len(z3_rows),
                "holdout_worsened": z3_worse,
                "outcome": "all validation-selected corrections worsen untouched holdout MAE",
                "binding": "source_files.negative_results:$.z3.models[*]",
            },
            "environment_field": {
                "pearson_r": env_r,
                "n_cells": env_cells,
                "scope": "blind gamma_110 prediction over 9 FCC materials x 4 models",
                "outcome": "promising separate result; no generalization beyond tested scope",
                "binding": "source_files.environment_field",
            },
        },
        "qualification_stack": {
            "layers": [
                {
                    "key": "model_output",
                    "label": "Model output",
                    "status": "measured",
                    "question": "Which model object, family, observable, material and protocol?",
                },
                {
                    "key": "training_lineage",
                    "label": "Training / parent-DFT lineage",
                    "status": "qualified",
                    "question": "What fitting exposure and parent functional shape the residual?",
                },
                {
                    "key": "curated_reference",
                    "label": "Curated 0 K reference table",
                    "status": "mixed-reference",
                    "question": "Are functional, implementation and convention matched?",
                },
                {
                    "key": "all_electron_anchor",
                    "label": "Paired all-electron PBE / r2SCAN elastic anchor",
                    "status": "PENDING",
                    "question": "Can fitting error be separated from reference-standard offset?",
                },
                {
                    "key": "experiment",
                    "label": "Experiment / decision endpoint",
                    "status": "requires-condition-matching",
                    "question": "Are temperature, phase, magnetism and measurement conventions aligned?",
                },
            ],
            "guard": "The all-electron anchor has not run and must not be presented as truth obtained.",
            "bindings": ["source_files.anchor_spec", "source_files.anchor_blocker"],
        },
    }


def validate(result: dict[str, Any]) -> None:
    assert_equal("schema", result.get("schema"), "lupine.tms2027.proceedings-results.v1")
    stages = result["denominator_funnel"]["stages"]
    assert_equal("funnel counts", [row["count"] for row in stages], [965, 559, 423, 42])
    groups = result["geometry"]["groups"]
    assert_equal("geometry rows", len(groups), 42)
    assert_equal("n=3 groups", sum(row["n_materials"] == 3 for row in groups), 21)
    elastic = result["elastic_benchmark"]
    assert_equal("raw MAE", elastic["raw_aggregate_mae_gpa"], 17.84)
    assert_equal("oracle corrected MAE", elastic["oracle_directional_ceiling"]["corrected_mae_gpa"], 10.36)
    assert_equal("oracle deployability", elastic["oracle_directional_ceiling"]["deployable"], False)
    assert_equal("global failure raw", elastic["global_operator_failure"]["raw_mae_gpa"], 14.55)
    assert_equal("global failure corrected", elastic["global_operator_failure"]["corrected_mae_gpa"], 63.40)
    alignment = result["cross_paradigm_alignment"]
    assert_equal("Spearman rho", alignment["spearman_rho"], 0.26)
    assert_equal("Spearman p", alignment["p_value"], 0.34)
    negative = result["negative_and_conditional_results"]
    assert_equal("Z1 range", negative["z1"]["mae_range_mev"], [135.0, 242.5])
    assert_equal("Z3 worsening", negative["z3"]["holdout_worsened"], 4)
    assert_equal("environment-field r", negative["environment_field"]["pearson_r"], 0.906)
    assert_equal("environment-field cells", negative["environment_field"]["n_cells"], 36)
    pending = [row for row in result["qualification_stack"]["layers"] if row["status"] == "PENDING"]
    assert_equal("pending all-electron layer", [row["key"] for row in pending], ["all_electron_anchor"])
    for key, record in result["source_files"].items():
        if len(record["sha256"]) != 64:
            raise ValueError(f"source {key} has an invalid SHA-256")


def figure_metadata(title: str) -> dict[str, Any]:
    timestamp = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    return {
        "Title": title,
        "Author": "Lupine Science",
        "Creator": "paper/tms2027-proceedings/results/build_results.py",
        "CreationDate": timestamp,
        "ModDate": timestamp,
    }


def save_figure(fig: Any, stem: str, title: str) -> None:
    png = HERE / f"{stem}.png"
    pdf = HERE / f"{stem}.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", metadata={"Software": "Lupine Science"})
    fig.savefig(pdf, bbox_inches="tight", metadata=figure_metadata(title))


def render_figures(result: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
        }
    )
    blue, orange, red, green, ink, pale = (
        "#3156A3",
        "#D9892B",
        "#B5453D",
        "#2D7D62",
        "#202733",
        "#E8EDF5",
    )

    stages = result["denominator_funnel"]["stages"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    widths = [row["count"] for row in stages]
    labels = [row["unit"] for row in stages]
    y = list(reversed(range(len(stages))))
    ax.barh(y, widths, color=[blue, "#5675B8", "#7890C6", orange], height=0.66)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Count (units change at each stage)")
    ax.set_title("Denominator and provenance funnel", fontweight="bold")
    for yi, count in zip(y, widths, strict=True):
        ax.text(count + 14, yi, f"{count:,}", va="center", fontweight="bold", color=ink)
    ax.set_xlim(0, 1070)
    ax.text(
        0.99,
        -0.20,
        result["denominator_funnel"]["guard"],
        transform=ax.transAxes,
        ha="right",
        color=red,
        fontsize=8,
    )
    save_figure(fig, FIGURES[0], "TMS 2027 denominator and provenance funnel")
    plt.close(fig)

    groups = result["geometry"]["groups"]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for row in groups:
        highlight = row["n_materials"] == 3
        color = orange if highlight else blue
        ax.plot(
            [row["n_materials"], row["n_materials"]],
            row["pr_ci95"],
            color=color,
            alpha=0.18 if highlight else 0.10,
            linewidth=0.8,
        )
        ax.scatter(
            row["n_materials"],
            row["participation_ratio"],
            s=34 if highlight else 28,
            color=color,
            edgecolor="white",
            linewidth=0.4,
            alpha=0.9,
        )
    ax.axvspan(2.72, 3.28, color=orange, alpha=0.08)
    ax.axhline(3, color=ink, linestyle=":", linewidth=1, label="maximum PR = 3")
    ax.set_xlabel("Materials in classical-potential group (n)")
    ax.set_ylabel("Participation ratio (PR)")
    ax.set_ylim(0.9, 3.12)
    ax.set_xticks(sorted({row["n_materials"] for row in groups}))
    ax.set_title("Participation ratio is strongly exposed to group size", fontweight="bold")
    ax.scatter([], [], color=orange, label="21 of 42 groups have n = 3")
    ax.scatter([], [], color=blue, label="groups with n > 3")
    ax.legend(frameon=True, facecolor="white", edgecolor="none", framealpha=0.95, loc="upper right")
    fig.text(
        0.5,
        0.025,
        "At n=3, centered 3-variable covariance has rank ≤ 2; low PR is descriptive, not universal.",
        ha="center",
        fontsize=8,
        color=red,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save_figure(fig, FIGURES[1], "TMS 2027 participation ratio by group size")
    plt.close(fig)

    elastic = result["elastic_benchmark"]
    oracle = elastic["oracle_directional_ceiling"]
    global_failure = elastic["global_operator_failure"]
    fig, axes = plt.subplots(1, 2, figsize=(8.1, 4.3), constrained_layout=True, sharey=True)
    axes[0].bar([0, 1], [oracle["raw_mae_gpa"], oracle["corrected_mae_gpa"]], color=[blue, green])
    axes[0].set_xticks([0, 1], ["Raw", "Directional\nceiling"])
    axes[0].set_title("Oracle ceiling — not deployable", fontweight="bold", color=green)
    axes[0].text(
        0.5,
        0.88,
        "held-out target supplies\nthe correction coefficient",
        transform=axes[0].transAxes,
        ha="center",
        va="top",
        fontsize=8,
    )
    axes[1].bar(
        [0, 1],
        [global_failure["raw_mae_gpa"], global_failure["corrected_mae_gpa"]],
        color=[blue, red],
    )
    axes[1].set_xticks([0, 1], ["Raw", "Global\nLOO-PCA"])
    axes[1].set_title("Deployable global operator — fails", fontweight="bold", color=red)
    axes[1].text(
        0.5,
        0.88,
        "reference-free transfer test\nworsens mean error",
        transform=axes[1].transAxes,
        ha="center",
        va="top",
        fontsize=8,
    )
    axes[0].set_ylabel(r"Elastic $C_{ij}$ MAE (GPa)")
    axes[0].set_ylim(0, 72)
    for ax, values in zip(
        axes,
        ([oracle["raw_mae_gpa"], oracle["corrected_mae_gpa"]], [global_failure["raw_mae_gpa"], global_failure["corrected_mae_gpa"]]),
        strict=True,
    ):
        for index, value in enumerate(values):
            ax.text(index, value + 1.5, f"{value:.2f}", ha="center", fontweight="bold")
    z3 = result["negative_and_conditional_results"]["z3"]
    fig.suptitle(
        f"Correction falsification: oracle access and deployable performance are separate estimands\n"
        f"Independent Z3 check: untouched holdout worsened for {z3['holdout_worsened']}/{z3['tested']} selected corrections",
        fontweight="bold",
    )
    save_figure(fig, FIGURES[2], "TMS 2027 correction falsification")
    plt.close(fig)

    layers = result["qualification_stack"]["layers"]
    fig, ax = plt.subplots(figsize=(8.0, 5.4), constrained_layout=True)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.4, len(layers) + 0.55)
    ax.axis("off")
    status_colors = {
        "measured": blue,
        "qualified": "#5675B8",
        "mixed-reference": orange,
        "PENDING": red,
        "requires-condition-matching": "#6B7280",
    }
    for index, layer in enumerate(layers):
        y0 = len(layers) - index - 0.35
        color = status_colors[layer["status"]]
        box = FancyBboxPatch(
            (0.45, y0 - 0.42),
            9.1,
            0.72,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            linewidth=2.4 if layer["status"] == "PENDING" else 1.1,
            edgecolor=color,
            facecolor="#FFF1F0" if layer["status"] == "PENDING" else pale,
        )
        ax.add_patch(box)
        ax.text(0.72, y0, layer["label"], va="center", fontweight="bold", color=ink)
        ax.text(9.28, y0 + 0.12, layer["status"], va="center", ha="right", color=color, fontweight="bold")
        ax.text(9.28, y0 - 0.16, layer["question"], va="center", ha="right", color=ink, fontsize=7.2)
        if index < len(layers) - 1:
            ax.annotate("", xy=(5, y0 - 0.60), xytext=(5, y0 - 0.42), arrowprops={"arrowstyle": "-|>", "color": ink})
    ax.set_title("Qualification and DFT-reference stack", fontweight="bold", fontsize=13)
    ax.text(
        0.5,
        -0.14,
        result["qualification_stack"]["guard"],
        transform=ax.transAxes,
        ha="center",
        color=red,
        fontweight="bold",
        fontsize=8.5,
    )
    save_figure(fig, FIGURES[3], "TMS 2027 qualification and DFT reference stack")
    plt.close(fig)


def verify_outputs() -> None:
    result = read_json(RESULTS_PATH)
    validate(result)
    for stem in FIGURES:
        for suffix in (".png", ".pdf"):
            path = HERE / f"{stem}{suffix}"
            if not path.is_file() or path.stat().st_size == 0:
                raise FileNotFoundError(f"missing figure output: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "figures", "all", "verify"), nargs="?", default="all")
    parser.add_argument("--lupine-root", type=Path, default=Path("/home/alex/Dev/lupine/lupine"))
    args = parser.parse_args()

    if args.command in {"build", "all"}:
        result = build(args.lupine_root.resolve())
        validate(result)
        RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.command in {"figures", "all"}:
        result = read_json(RESULTS_PATH)
        validate(result)
        render_figures(result)
    if args.command in {"verify", "all"}:
        verify_outputs()
    print(f"PASS: {args.command}; canonical results: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
