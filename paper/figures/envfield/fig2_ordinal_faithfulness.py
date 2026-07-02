"""Fig 2 — ordinal faithfulness and its single fracture (7 in, two panels).

(a) Predicted vs reference gamma_111 for the 9 fcc metals, all 4 models,
    log-log, Spearman rank correlations annotated per model.
(b) Predicted vs reference stacking-fault energy (7 fcc metals with bound
    references), linear axes: the MPtrj-trained models' rank collapse vs
    the OMat-lineage MACE-MPA-0.
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import ticker as mticker

import common as C


def _pairs(
    dataset: C.Dataset, model: str, prop: str, materials: tuple[str, ...]
) -> tuple[np.ndarray, np.ndarray]:
    preds, refs = [], []
    for material in materials:
        rec = dataset.cell(material, model).prop(prop)
        if rec is None or rec.reference is None:
            raise C.DataConsistencyError(
                f"({material}, {model}) missing bound {prop}"
            )
        preds.append(rec.predicted)
        refs.append(rec.reference)
    return np.asarray(preds), np.asarray(refs)


def build() -> dict:
    C.apply_style()
    dataset = C.load_dataset()

    sfe_materials = tuple(
        m
        for m in C.FCC_MATERIALS
        if dataset.cell(m, C.MODELS[0]).prop("stacking_fault_energy").reference
        is not None
    )

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(C.DOUBLE_COL_IN, 2.9),
        gridspec_kw={"left": 0.095, "right": 0.985, "top": 0.93,
                     "bottom": 0.165, "wspace": 0.3},
    )

    # ---- panel a: gamma_111, log-log --------------------------------------
    stats_a = {}
    all_vals = []
    for model in C.MODELS:
        pred, ref = _pairs(dataset, model, "gamma_111", C.FCC_MATERIALS)
        rho = C.spearman_rho(pred, ref)
        stats_a[model] = {"spearman_rho": rho, "n": int(pred.size)}
        ax_a.scatter(
            ref, pred,
            s=14, marker=C.MODEL_MARKERS[model], color=C.MODEL_COLORS[model],
            linewidths=0.4, edgecolors="white", zorder=3,
            label=f"{C.MODEL_LABELS[model]} ($\\rho$={rho:.2f})",
        )
        all_vals.extend(ref.tolist())
        all_vals.extend(pred.tolist())
    lo = 0.8 * min(all_vals)
    hi = 1.25 * max(all_vals)
    ax_a.plot([lo, hi], [lo, hi], ls="--", lw=0.7, color="0.5", zorder=1)
    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlim(lo, hi)
    ax_a.set_ylim(lo, hi)
    ax_a.set_xlabel(r"reference $\gamma_{111}$ (J m$^{-2}$)")
    ax_a.set_ylabel(r"predicted $\gamma_{111}$ (J m$^{-2}$)")
    for axis in (ax_a.xaxis, ax_a.yaxis):
        axis.set_major_locator(mticker.FixedLocator([0.2, 0.5, 1.0, 2.0]))
        axis.set_major_formatter(mticker.ScalarFormatter())
        axis.set_minor_formatter(mticker.NullFormatter())
    ax_a.legend(loc="upper left", handletextpad=0.15)
    ax_a.spines[["top", "right"]].set_visible(False)

    # ---- panel b: SFE fracture, linear ------------------------------------
    stats_b = {}
    sfe_vals = []
    for model in C.MODELS:
        pred, ref = _pairs(dataset, model, "stacking_fault_energy", sfe_materials)
        rho = C.spearman_rho(pred, ref)
        stats_b[model] = {"spearman_rho": rho, "n": int(pred.size)}
        ax_b.scatter(
            ref, pred,
            s=16, marker=C.MODEL_MARKERS[model], color=C.MODEL_COLORS[model],
            linewidths=0.4, edgecolors="white", zorder=3,
        )
        sfe_vals.extend(ref.tolist())
        sfe_vals.extend(pred.tolist())
    lo_b = min(sfe_vals) - 25.0
    hi_b = max(sfe_vals) + 25.0
    ax_b.plot([lo_b, hi_b], [lo_b, hi_b], ls="--", lw=0.7, color="0.5", zorder=1)
    ax_b.axhline(0.0, lw=0.5, color="0.75", zorder=0)
    ax_b.set_xlim(min(sfe_vals) - 15.0, max(r for r in sfe_vals) + 15.0)
    ax_b.set_ylim(lo_b, hi_b)
    ax_b.set_xlabel(r"reference $\gamma_\mathrm{SFE}$ (mJ m$^{-2}$)")
    ax_b.set_ylabel(r"predicted $\gamma_\mathrm{SFE}$ (mJ m$^{-2}$)")
    mptrj_rhos = [stats_b[m]["spearman_rho"] for m in C.MPTRJ_MODELS]
    ax_b.text(
        0.03, 0.97,
        (
            f"MPtrj models: $\\rho$ = {min(mptrj_rhos):.2f}"
            f"–{max(mptrj_rhos):.2f}\n"
            f"MPA-0: $\\rho$ = "
            f"{stats_b['mace-mpa-0-medium']['spearman_rho']:.2f}"
        ),
        transform=ax_b.transAxes, va="top", ha="left", fontsize=7,
    )
    ax_b.spines[["top", "right"]].set_visible(False)
    fig.text(0.008, 0.955, "a", fontsize=9, fontweight="bold")
    fig.text(0.517, 0.955, "b", fontsize=9, fontweight="bold")

    outputs = C.save_figure(fig, "fig2_ordinal_faithfulness")
    plt.close(fig)

    return {
        "figure": "fig2_ordinal_faithfulness",
        "outputs": outputs,
        "inputs": dict(dataset.input_hashes),
        "computation": {
            "panel_a": (
                "predicted vs reference gamma_111, 9 fcc metals x 4 models, "
                "log-log; Spearman rho per model over materials"
            ),
            "panel_b": (
                "predicted vs reference stacking-fault energy over fcc "
                f"metals with bound references {list(sfe_materials)}; "
                "linear axes (negative predictions occur); Spearman rho "
                "per model"
            ),
        },
        "stats": {
            "gamma_111_spearman": stats_a,
            "sfe_spearman": stats_b,
            "sfe_materials": list(sfe_materials),
        },
    }


if __name__ == "__main__":
    import json

    result = build()
    (C.OUT_DIR / "fig2_stats.json").write_text(
        json.dumps(result["stats"], indent=1), encoding="utf-8"
    )
