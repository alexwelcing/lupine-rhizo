"""Fig 3 — the family-exponent law (3.5 in, single column, two panels).

(a) log(pred) vs log(ref) for surface energies, all facets pooled, per
    model, with fitted slopes alpha (pred ~= c * ref^alpha).
(b) alpha with bootstrap 95% CIs, grouped by property family
    (surfaces / B0 / vacancy) x model — the family clustering.
"""

from __future__ import annotations

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import ticker as mticker

import common as C

BOOTSTRAP_SEED = 20260702
N_BOOTSTRAP = 1000

FAMILY_PROPS = {
    "surfaces": ("gamma_100", "gamma_110", "gamma_111"),
    "B0": ("B0",),
    "vacancy": ("vacancy_formation_energy",),
}
FAMILY_LABELS = {
    "surfaces": "surfaces",
    "B0": r"$B_0$",
    "vacancy": r"$E_\mathrm{vac}$",
}


def _family_pairs(
    dataset: C.Dataset, model: str, family: str
) -> tuple[np.ndarray, np.ndarray]:
    preds, refs = [], []
    for cell in dataset.cells_for_model(model):
        for prop in FAMILY_PROPS[family]:
            rec = cell.prop(prop)
            if rec is None or rec.reference is None:
                continue
            if rec.predicted <= 0 or rec.reference <= 0:
                raise C.DataConsistencyError(
                    f"non-positive value in log-log family {family}: "
                    f"({cell.material}, {model}, {prop})"
                )
            preds.append(rec.predicted)
            refs.append(rec.reference)
    return np.asarray(preds), np.asarray(refs)


def build() -> dict:
    C.apply_style()
    dataset = C.load_dataset()
    rng = np.random.default_rng(BOOTSTRAP_SEED)

    fig, (ax_a, ax_b) = plt.subplots(
        2, 1, figsize=(C.SINGLE_COL_IN, 4.9),
        gridspec_kw={"left": 0.155, "right": 0.975, "top": 0.975,
                     "bottom": 0.09, "hspace": 0.42,
                     "height_ratios": [1.35, 1.0]},
    )

    # ---- panel a: pooled surfaces log-log with fits ------------------------
    stats: dict[str, dict] = {f: {} for f in FAMILY_PROPS}
    surf_vals = []
    for model in C.MODELS:
        pred, ref = _family_pairs(dataset, model, "surfaces")
        alpha, prefactor, r2 = C.loglog_fit(pred, ref)
        stats["surfaces"][model] = {
            "alpha": alpha, "prefactor": prefactor, "r2": r2,
            "n": int(pred.size),
        }
        ax_a.scatter(
            ref, pred,
            s=7, marker=C.MODEL_MARKERS[model], color=C.MODEL_COLORS[model],
            alpha=0.75, linewidths=0, zorder=3,
            label=f"{C.MODEL_LABELS[model]} ($\\alpha$={alpha:.2f})",
        )
        xs = np.linspace(np.log(ref.min()), np.log(ref.max()), 24)
        ax_a.plot(
            np.exp(xs), prefactor * np.exp(xs) ** alpha,
            color=C.MODEL_COLORS[model], lw=0.9, zorder=2,
        )
        surf_vals.extend(ref.tolist())
        surf_vals.extend(pred.tolist())
    lo, hi = 0.85 * min(surf_vals), 1.2 * max(surf_vals)
    ax_a.plot([lo, hi], [lo, hi], ls="--", lw=0.7, color="0.5", zorder=1)
    ax_a.set_xscale("log")
    ax_a.set_yscale("log")
    ax_a.set_xlim(lo, hi)
    ax_a.set_ylim(lo, hi)
    ax_a.set_xlabel(r"reference $\gamma$ (J m$^{-2}$)")
    ax_a.set_ylabel(r"predicted $\gamma$ (J m$^{-2}$)")
    for axis in (ax_a.xaxis, ax_a.yaxis):
        axis.set_major_locator(mticker.FixedLocator([0.3, 0.5, 1.0, 2.0, 4.0]))
        axis.set_major_formatter(mticker.ScalarFormatter())
        axis.set_minor_formatter(mticker.NullFormatter())
    ax_a.legend(loc="upper left", handletextpad=0.15, borderaxespad=0.2)
    ax_a.spines[["top", "right"]].set_visible(False)

    # ---- panel b: alpha +/- bootstrap CI by family x model -----------------
    families = tuple(FAMILY_PROPS)
    group_width = 0.55
    offsets = np.linspace(-group_width / 2, group_width / 2, len(C.MODELS))
    for gi, family in enumerate(families):
        for mi, model in enumerate(C.MODELS):
            pred, ref = _family_pairs(dataset, model, family)
            if family == "surfaces":
                alpha = stats["surfaces"][model]["alpha"]
            else:
                alpha, prefactor, r2 = C.loglog_fit(pred, ref)
                stats[family][model] = {
                    "alpha": alpha, "prefactor": prefactor, "r2": r2,
                    "n": int(pred.size),
                }
            ci_lo, ci_hi = C.bootstrap_alpha_ci(
                pred, ref, rng=rng, n_bootstrap=N_BOOTSTRAP
            )
            stats[family][model]["alpha_ci95"] = [ci_lo, ci_hi]
            x = gi + offsets[mi]
            ax_b.errorbar(
                x, alpha,
                yerr=[[alpha - ci_lo], [ci_hi - alpha]],
                fmt=C.MODEL_MARKERS[model], color=C.MODEL_COLORS[model],
                ms=3.5, mew=0.4, mec="white", elinewidth=0.8, capsize=1.5,
                zorder=3,
            )
    ax_b.axhline(1.0, ls=":", lw=0.7, color="0.4", zorder=1)
    for boundary in (0.5, 1.5):
        ax_b.axvline(boundary, lw=0.5, color="0.88", zorder=0)
    ax_b.set_xticks(range(len(families)))
    ax_b.set_xticklabels([FAMILY_LABELS[f] for f in families])
    ax_b.set_ylabel(r"family exponent $\alpha$ (95% CI)")
    ax_b.set_xlim(-0.55, len(families) - 0.45)
    ax_b.spines[["top", "right"]].set_visible(False)
    for ax, letter in ((ax_a, "a"), (ax_b, "b")):
        box = ax.get_position()
        fig.text(0.012, box.y1 + 0.006, letter, fontsize=9, fontweight="bold")

    outputs = C.save_figure(fig, "fig3_family_exponent")
    plt.close(fig)

    return {
        "figure": "fig3_family_exponent",
        "outputs": outputs,
        "inputs": dict(dataset.input_hashes),
        "computation": {
            "fit": (
                "OLS of log(pred) on log(ref) per (model, family): "
                "pred ~= c * ref^alpha; surfaces pool gamma_100/110/111 "
                "over all materials with bound references; CIs are seeded "
                f"percentile bootstrap over points (seed {BOOTSTRAP_SEED}, "
                f"n={N_BOOTSTRAP})"
            ),
        },
        "stats": {"family_exponents": stats},
    }


if __name__ == "__main__":
    import json

    result = build()
    (C.OUT_DIR / "fig3_stats.json").write_text(
        json.dumps(result["stats"], indent=1), encoding="utf-8"
    )
