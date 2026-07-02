"""Fig 1 — where models fail (7 in, two panels).

(a) Signed relative error heatmaps, materials x properties, one sub-block
    per model. Diverging colorbar clipped at +/-50%; cells without a bound
    reference are gray.
(b) Defect-family vs bulk-family median |rel err| per model, log scale,
    taken from the registered confirmatory artifact
    ``analysis/r2_mpa0_confirmatory.json`` (H3, all-material cell set,
    (Ni, mace-mp-small) quarantined per the preregistration).
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import colors as mcolors

import common as C

CLIP_PCT = 50.0
BULK_COLOR = "#0072B2"  # Okabe-Ito blue
DEFECT_COLOR = "#D55E00"  # Okabe-Ito vermillion


def _error_matrix(dataset: C.Dataset, model: str) -> np.ndarray:
    grid = np.full((len(C.MATERIAL_ORDER), len(C.PROPERTY_ORDER)), np.nan)
    for i, material in enumerate(C.MATERIAL_ORDER):
        cell = dataset.cell(material, model)
        for j, prop in enumerate(C.PROPERTY_ORDER):
            rec = cell.prop(prop)
            if rec is not None and rec.rel_err is not None:
                grid[i, j] = 100.0 * rec.rel_err
    return grid


def build() -> dict:
    C.apply_style()
    dataset = C.load_dataset()
    h3_payload, h3_hash = C.load_analysis_artifact("r2_mpa0_confirmatory.json")
    h3 = h3_payload["h3"]["per_model"]

    fig = plt.figure(figsize=(C.DOUBLE_COL_IN, 5.4))
    gs = fig.add_gridspec(
        2, 1, height_ratios=[3.0, 1.15], hspace=0.34,
        left=0.085, right=0.905, top=0.955, bottom=0.075,
    )
    gs_top = gs[0].subgridspec(1, 4, wspace=0.12)

    cmap = plt.get_cmap("RdBu_r").copy()
    cmap.set_bad("#d9d9d9")
    norm = mcolors.Normalize(vmin=-CLIP_PCT, vmax=CLIP_PCT)

    grids = {}
    n_clipped = 0
    extreme = {"value_pct": 0.0}
    heat_axes = []
    for k, model in enumerate(C.MODELS):
        ax = fig.add_subplot(gs_top[0, k])
        heat_axes.append(ax)
        grid = _error_matrix(dataset, model)
        grids[model] = grid
        finite = grid[np.isfinite(grid)]
        n_clipped += int(np.sum(np.abs(finite) > CLIP_PCT))
        worst_idx = np.unravel_index(
            np.nanargmax(np.abs(grid)), grid.shape
        )
        worst = float(grid[worst_idx])
        if abs(worst) > abs(extreme["value_pct"]):
            extreme = {
                "model": model,
                "material": C.MATERIAL_ORDER[worst_idx[0]],
                "property": C.PROPERTY_ORDER[worst_idx[1]],
                "value_pct": worst,
            }
        mesh = ax.imshow(
            grid, cmap=cmap, norm=norm, aspect="auto", interpolation="nearest"
        )
        ax.set_title(C.MODEL_LABELS[model], fontsize=7.5, pad=3)
        ax.set_xticks(range(len(C.PROPERTY_ORDER)))
        ax.set_xticklabels(
            [C.PROPERTY_TEX[p] for p in C.PROPERTY_ORDER],
            rotation=90, fontsize=6.5,
        )
        ax.set_yticks(range(len(C.MATERIAL_ORDER)))
        if k == 0:
            ax.set_yticklabels(
                [C.material_label(m) for m in C.MATERIAL_ORDER], fontsize=6.0
            )
        else:
            ax.set_yticklabels([])
        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
    top_box = heat_axes[-1].get_position()
    cax = fig.add_axes([0.918, top_box.y0, 0.014, top_box.height])
    cbar = fig.colorbar(mesh, cax=cax, extend="both")
    cbar.set_label("signed relative error (%)", fontsize=7)
    cbar.set_ticks([-50, -25, 0, 25, 50])
    cbar.ax.tick_params(labelsize=6.5)
    fig.text(0.008, 0.965, "a", fontsize=9, fontweight="bold")

    # ---- panel b: defect vs bulk medians from the registered artifact ----
    ax_b = fig.add_subplot(gs[1])
    xs = np.arange(len(C.MODELS))
    width = 0.36
    stats_b = {}
    for k, model in enumerate(C.MODELS):
        entry = h3[model]
        bulk_pct = 100.0 * entry["median_abs_error_bulk"]
        defect_pct = 100.0 * entry["median_abs_error_defect"]
        ax_b.bar(
            xs[k] - width / 2, bulk_pct, width,
            color=BULK_COLOR, edgecolor="none",
            label="bulk family" if k == 0 else None,
        )
        ax_b.bar(
            xs[k] + width / 2, defect_pct, width,
            color=DEFECT_COLOR, edgecolor="none",
            label="defect family" if k == 0 else None,
        )
        ax_b.annotate(
            f"$\\times${entry['ratio']:.1f}",
            xy=(xs[k] + width / 2, defect_pct),
            xytext=(0, 2), textcoords="offset points",
            ha="center", va="bottom", fontsize=7,
        )
        stats_b[model] = {
            "median_abs_rel_err_bulk_pct": bulk_pct,
            "median_abs_rel_err_defect_pct": defect_pct,
            "ratio": entry["ratio"],
            "ratio_ci95": entry["ci95"],
            "n_bulk_cells": entry["n_bulk_cells"],
            "n_defect_cells": entry["n_defect_cells"],
        }
    ax_b.set_yscale("log")
    ax_b.set_ylim(0.1, 200.0)
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels([C.MODEL_LABELS[m] for m in C.MODELS], fontsize=7)
    ax_b.set_ylabel("median |rel. error| (%)")
    ax_b.legend(loc="upper right", ncols=2, handlelength=1.2)
    ax_b.spines[["top", "right"]].set_visible(False)
    fig.text(0.008, 0.315, "b", fontsize=9, fontweight="bold")

    outputs = C.save_figure(fig, "fig1_error_overview")
    plt.close(fig)

    inputs = dict(dataset.input_hashes)
    inputs[h3_hash[0]] = h3_hash[1]
    return {
        "figure": "fig1_error_overview",
        "outputs": outputs,
        "inputs": inputs,
        "computation": {
            "panel_a": (
                "signed relative error (pred-ref)/|ref| in % per "
                "(material, property, model) from bound evidence; color "
                f"scale clipped at +/-{CLIP_PCT:.0f}%; gray = no bound "
                "reference"
            ),
            "panel_b": (
                "median |rel err| for bulk {a0, B0} vs defect "
                "{E_vac, gamma_100, gamma_110} cells, all materials with "
                "references, (Ni, mace-mp-small) quarantined; values read "
                "from the registered artifact analysis/"
                "r2_mpa0_confirmatory.json (h3.per_model)"
            ),
        },
        "stats": {
            "panel_a_n_cells_clipped": n_clipped,
            "panel_a_most_extreme_cell": extreme,
            "panel_b_h3": stats_b,
        },
    }


if __name__ == "__main__":
    import json

    result = build()
    (C.OUT_DIR / "fig1_stats.json").write_text(
        json.dumps(result["stats"], indent=1), encoding="utf-8"
    )
