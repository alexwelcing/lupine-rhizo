"""Fig 4 — the environment error field (7 in, two panels).

(a) Delta-eps(c), the per-atom energy error at first-shell coordination c,
    measured from three anchors (gamma_100 -> c=8, gamma_111 -> c=9,
    E_vac/12 -> c=11) for CHGNet and MACE-MP small across the 9 fcc metals:
    a smooth, monotone field. Two sub-axes share the y scale.
(b) Blind gamma_110 test: error predicted by linear field continuation
    (de7 ~ 2*de8 - de9; gamma_110 error ~ (de7 + de11) * 16.0218 / A_110)
    vs the measured error, 36 (model, material) cells, Pearson r annotated.
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt

import common as C

FIELD_MODELS = ("chgnet", "mace-mp-small")
COORDS = (8, 9, 11)


def _material_colors() -> dict[str, tuple]:
    cmap = plt.get_cmap("viridis")
    n = len(C.FCC_MATERIALS)
    return {
        mat: cmap(0.03 + 0.80 * i / (n - 1))
        for i, mat in enumerate(C.FCC_MATERIALS)
    }


def _spread(targets: list[float], sep: float) -> list[float]:
    """Nudge label y-positions upward to enforce a minimum separation."""
    order = sorted(range(len(targets)), key=lambda i: targets[i])
    placed = list(targets)
    prev = None
    for i in order:
        y = placed[i] if prev is None else max(placed[i], prev + sep)
        placed[i] = y
        prev = y
    return placed


def build() -> dict:
    C.apply_style()
    dataset = C.load_dataset()
    field = C.environment_field_cells(dataset)
    by_key = {(c.model_id, c.material): c for c in field}

    fig = plt.figure(figsize=(C.DOUBLE_COL_IN, 2.9))
    gs = fig.add_gridspec(
        1, 2, width_ratios=[2.0, 1.35], wspace=0.24,
        left=0.075, right=0.985, top=0.93, bottom=0.16,
    )
    gs_a = gs[0].subgridspec(1, 2, wspace=0.1)
    ax_a1 = fig.add_subplot(gs_a[0])
    ax_a2 = fig.add_subplot(gs_a[1], sharey=ax_a1)
    ax_b = fig.add_subplot(gs[1])

    mat_colors = _material_colors()
    all_de = [
        v for c in field if c.model_id in FIELD_MODELS
        for v in (c.de8, c.de9, c.de11)
    ]
    label_sep = 0.055 * (max(all_de) - min(all_de))
    curves: dict[str, dict[str, list[float]]] = {}
    for ax, model in zip((ax_a1, ax_a2), FIELD_MODELS):
        curves[model] = {}
        for material in C.FCC_MATERIALS:
            cell = by_key[(model, material)]
            ys = [cell.de8, cell.de9, cell.de11]
            curves[model][material] = ys
            ax.plot(
                COORDS, ys, marker="o", ms=2.4, lw=0.9,
                color=mat_colors[material],
            )
        label_ys = _spread(
            [curves[model][m][0] for m in C.FCC_MATERIALS], label_sep
        )
        for material, label_y in zip(C.FCC_MATERIALS, label_ys):
            ax.annotate(
                C.material_label(material),
                xy=(COORDS[0] - 0.18, label_y), fontsize=5.5,
                color=mat_colors[material], va="center", ha="right",
            )
        ax.axhline(0.0, lw=0.5, color="0.75", zorder=0)
        ax.set_xticks(COORDS)
        ax.set_xlim(6.9, 11.5)
        ax.set_xlabel("first-shell coordination $c$")
        ax.set_title(C.MODEL_LABELS[model], fontsize=7.5, pad=3)
        ax.spines[["top", "right"]].set_visible(False)
    ax_a1.set_ylabel(r"$\Delta\varepsilon(c)$ (eV atom$^{-1}$)")
    plt.setp(ax_a2.get_yticklabels(), visible=False)

    # ---- panel b: blind gamma_110 -----------------------------------------
    predicted = np.array([c.predicted_gamma110_error for c in field])
    actual = np.array([c.actual_gamma110_error for c in field])
    r = C.pearson_r(predicted, actual)
    rho = C.spearman_rho(predicted, actual)
    residual = np.abs(actual - predicted)
    zero_residual = np.abs(actual)
    for model in C.MODELS:
        mask = np.array([c.model_id == model for c in field])
        ax_b.scatter(
            predicted[mask], actual[mask],
            s=16, marker=C.MODEL_MARKERS[model], color=C.MODEL_COLORS[model],
            linewidths=0.4, edgecolors="white", zorder=3,
            label=C.MODEL_LABELS[model],
        )
    lo = min(predicted.min(), actual.min()) - 0.1
    hi = max(predicted.max(), actual.max()) + 0.1
    ax_b.plot([lo, hi], [lo, hi], ls="--", lw=0.7, color="0.5", zorder=1)
    ax_b.set_xlim(lo, hi)
    ax_b.set_ylim(lo, hi)
    ax_b.set_xlabel(r"field-predicted $\gamma_{110}$ error (J m$^{-2}$)")
    ax_b.set_ylabel(r"measured $\gamma_{110}$ error (J m$^{-2}$)")
    ax_b.text(
        0.03, 0.97, f"$r$ = {r:.3f}\n$n$ = {predicted.size}",
        transform=ax_b.transAxes, va="top", ha="left", fontsize=7,
    )
    ax_b.legend(loc="lower right", handletextpad=0.15)
    ax_b.spines[["top", "right"]].set_visible(False)
    fig.text(0.008, 0.945, "a", fontsize=9, fontweight="bold")
    box_b = ax_b.get_position()
    fig.text(box_b.x0 - 0.075, 0.945, "b", fontsize=9, fontweight="bold")

    outputs = C.save_figure(fig, "fig4_environment_field")
    plt.close(fig)

    per_cell = [
        {
            "model": c.model_id,
            "material": c.material,
            "a0_model_angstrom": c.a0_model,
            "de8_ev": c.de8,
            "de9_ev": c.de9,
            "de11_ev": c.de11,
            "predicted_gamma110_error_j_m2": c.predicted_gamma110_error,
            "actual_gamma110_error_j_m2": c.actual_gamma110_error,
        }
        for c in field
    ]
    return {
        "figure": "fig4_environment_field",
        "outputs": outputs,
        "inputs": dict(dataset.input_hashes),
        "computation": {
            "anchors": (
                "delta_eps(c): c=8 <- gamma_100 err * (a0^2/2) / 16.0218; "
                "c=9 <- gamma_111 err * (sqrt(3)/4 a0^2) / 16.0218; "
                "c=11 <- E_vac err / 12; areas at the model's relaxed a0 "
                "(slabs were built at model a0)"
            ),
            "blind_prediction": (
                "gamma_110 err ~= (2*de8 - de9 + de11) * 16.0218 / "
                "(a0^2/sqrt(2)); compared against the measured gamma_110 "
                "error over 9 fcc metals x 4 models"
            ),
        },
        "stats": {
            "blind_gamma110_pearson_r": r,
            "blind_gamma110_spearman_rho": rho,
            "n_cells": int(predicted.size),
            "median_abs_residual_j_m2": float(np.median(residual)),
            "median_abs_error_predict_zero_j_m2": float(
                np.median(zero_residual)
            ),
            "strict_wins_vs_predict_zero_float64": int(
                np.sum(residual < zero_residual)
            ),
            "strict_wins_vs_predict_zero_int_1e4": int(
                np.sum(
                    np.round(residual * 1e4) < np.round(zero_residual * 1e4)
                )
            ),
            "strict_wins_note": (
                "the kernel-checked manuscript count uses x10^4 integer "
                "scaling; one float-precision win vanishes there "
                "(equal scaled residuals)"
            ),
            "per_cell": per_cell,
        },
    }


if __name__ == "__main__":
    import json

    result = build()
    (C.OUT_DIR / "fig4_stats.json").write_text(
        json.dumps(result["stats"], indent=1), encoding="utf-8"
    )
