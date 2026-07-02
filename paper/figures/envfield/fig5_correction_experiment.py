"""Fig 5 — run-time correction experiment, per fig5_SPEC.md.

Panel (a): static corrections for (CHGNet, Ni) and (CHGNet, Cu): raw vs
field-corrected vs reference per property (gamma_110 marked BLIND).
Panel (b): force RMSE vs the MPA-0 proxy, raw vs corrected, surface/all
atoms, with MD sanity annotated. All numbers recomputed from
data/y_matrix_runs/envfield_experiment/report.json; input hash recorded.
"""

from __future__ import annotations

import hashlib
import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

import common  # figure-pipeline shared style (palette, savefig, manifest)

HERE = pathlib.Path(__file__).resolve().parent
REPORT = HERE.parents[2] / "data" / "y_matrix_runs" / "envfield_experiment" / "report.json"


def main() -> None:
    common.apply_style()
    raw_bytes = REPORT.read_bytes()
    report = json.loads(raw_bytes)
    sha = hashlib.sha256(raw_bytes).hexdigest()

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=(7.0, 2.9), gridspec_kw={"width_ratios": [2.2, 1.0]}
    )

    # ---- panel (a): statics -------------------------------------------
    props = ["gamma_100", "gamma_110", "gamma_111", "E_vac"]
    labels = [r"$\gamma_{100}$", r"$\gamma_{110}$*", r"$\gamma_{111}$", r"$E_{\rm vac}$"]
    color = common.MODEL_COLORS["chgnet"]
    n_p = len(props)
    width = 0.35
    for m_idx, mat in enumerate(("Ni", "Cu")):
        block = report["materials"][mat]["properties"]
        xs = np.arange(n_p) + m_idx * (n_p + 0.8)
        raw = [block[p]["raw"] for p in props]
        cor = [block[p]["corrected"] for p in props]
        ref = [block[p]["reference"] for p in props]
        ax_a.bar(xs - width / 2, raw, width, color=color, alpha=0.45,
                 label="raw" if m_idx == 0 else None)
        ax_a.bar(xs + width / 2, cor, width, color=color,
                 label="corrected" if m_idx == 0 else None)
        for x, r in zip(xs, ref):
            ax_a.hlines(r, x - 0.55, x + 0.55, color="black", lw=1.2,
                        label="reference" if m_idx == 0 and x == xs[0] else None)
        ax_a.text(xs.mean(), -0.32, mat, ha="center", va="top",
                  transform=ax_a.get_xaxis_transform(), fontsize=8)
    ax_a.set_xticks(
        np.concatenate([np.arange(n_p), np.arange(n_p) + n_p + 0.8])
    )
    ax_a.set_xticklabels(labels + labels, fontsize=7)
    ax_a.set_ylabel(r"value (J/m$^2$; $E_{\rm vac}$ in eV)", fontsize=8)
    ax_a.legend(fontsize=7, frameon=False, loc="upper left")
    ax_a.text(0.99, 0.02, "* blind facet (never fitted)", ha="right",
              transform=ax_a.transAxes, fontsize=7)

    # ---- panel (b): forces + MD sanity ---------------------------------
    f = report["forces_vs_proxy"]
    groups = ["all atoms", "surface atoms"]
    raw_v = [f["rmse_all_raw"], f["rmse_surface_raw"]]
    cor_v = [f["rmse_all_corrected"], f["rmse_surface_corrected"]]
    xs = np.arange(2)
    ax_b.bar(xs - width / 2, raw_v, width, color=color, alpha=0.45, label="raw")
    ax_b.bar(xs + width / 2, cor_v, width, color=color, label="corrected")
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels(groups, fontsize=7)
    ax_b.set_ylabel(f"force RMSE vs {f['proxy']} (eV/Å)", fontsize=8)
    ax_b.set_ylim(0, max(raw_v) * 1.35)
    md = report["md"]
    ax_b.text(
        0.02, 0.98,
        f"null result (Δ<0.001)\nMD: {md['steps']} steps stable,\n+{md['overhead_pct']}% wall time",
        transform=ax_b.transAxes, fontsize=6.5, va="top",
    )

    fig.tight_layout()
    outputs = common.save_figure(fig, "fig5_correction_experiment")
    manifest_path = HERE / "figures_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["fig5_correction_experiment"] = {
        "inputs": {str(REPORT): sha},
        "outputs": outputs,
        "description": "Run-time correction: statics incl. blind facet; force null; MD sanity",
    }
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
