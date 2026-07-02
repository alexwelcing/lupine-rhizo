"""Build every envfield paper figure + Table 1 and write figures_manifest.json.

Runs each figure builder twice and verifies the output bytes are identical
(deterministic pipeline: seeded bootstraps, Agg backend, PDF CreationDate
stripped). The manifest records, per artifact: the script, the computation,
every input file's SHA-256, every output file's SHA-256, and the computed
statistics — no number in any figure is hand-typed.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import matplotlib
import numpy
import scipy

import common as C
import fig1_error_overview
import fig2_ordinal_faithfulness
import fig3_family_exponent
import fig4_environment_field
import table1_static_results

log = logging.getLogger("envfield.figures")

BUILDERS = (
    fig1_error_overview,
    fig2_ordinal_faithfulness,
    fig3_family_exponent,
    fig4_environment_field,
    table1_static_results,
)

FIG5_SPEC = """\
# Fig 5 spec — run-time correction experiment (placeholder)

`data/y_matrix_runs/envfield_experiment/` was not present when the other
figures were built, so Fig 5 could not be generated from artifacts. When the
correction experiment lands, generate Fig 5 (7 in, two panels) from its
REPORT/JSON artifacts:

- **Panel (a): static corrections.** Grouped bars per property
  (gamma_100, gamma_110 [blind facet], gamma_111, E_vac; bulk-sanity a0/B0
  shifts as a marginal note) for the experiment's (model, material) cells
  (per the manuscript: (CHGNet, Ni) and (CHGNet, Cu)): raw prediction vs
  field-corrected prediction vs reference. Same Okabe-Ito palette as
  Figs 1–4 (`common.MODEL_COLORS`); reference as a black tick/line, raw in
  the model color at 50% alpha, corrected in the model color solid.
- **Panel (b): force errors.** Force RMSE on rattled Ni(110) slabs vs the
  stronger-model proxy reference: raw vs corrected, split into surface
  atoms / all atoms (grouped bars, log y if the spread demands it).
  Annotate MD sanity from the run artifacts (energy drift, wall-time
  overhead of the correction) as small text if present in the REPORT.

Requirements carried over from this pipeline: recompute every number from
the experiment JSONs (no hand-typed values), record input SHA-256s in
`figures_manifest.json`, vector PDF + 300 dpi PNG at 7 in width, fonts
embedded (pdf.fonttype 42), no in-figure titles, deterministic outputs
(strip PDF CreationDate; seed anything stochastic).
"""


def _build_twice(module) -> dict:
    """Build once, rebuild, and require byte-identical outputs."""
    first = module.build()
    second = module.build()
    mismatches = []
    for kind, meta in first["outputs"].items():
        if second["outputs"][kind]["sha256"] != meta["sha256"]:
            mismatches.append(meta["path"])
    if mismatches:
        raise RuntimeError(
            f"{first['figure']}: non-deterministic outputs: {mismatches}"
        )
    first["deterministic"] = True
    return first


def _fig5_entry() -> dict:
    exp_dir = C.ENVFIELD_EXPERIMENT_DIR
    if exp_dir.is_dir() and any(exp_dir.iterdir()):
        return {
            "figure": "fig5_correction",
            "status": (
                "experiment artifacts present but no builder ran; see "
                "fig5_SPEC.md and implement fig5_correction.py"
            ),
        }
    spec_path = C.OUT_DIR / "fig5_SPEC.md"
    spec_path.write_text(FIG5_SPEC, encoding="utf-8", newline="\n")
    return {
        "figure": "fig5_correction",
        "status": "placeholder spec (envfield_experiment/ absent at build)",
        "outputs": {
            "spec": {
                "path": spec_path.relative_to(C.REPO_ROOT).as_posix(),
                "sha256": C.sha256_of(spec_path),
            }
        },
    }


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    log.setLevel(logging.INFO)
    logging.getLogger("fontTools").setLevel(logging.WARNING)
    C.apply_style()
    entries = []
    all_inputs: dict[str, str] = {}
    for module in BUILDERS:
        entry = _build_twice(module)
        entry["script"] = Path(module.__file__).name
        all_inputs.update(entry.pop("inputs"))
        entries.append(entry)
        log.info("built %s (deterministic)", entry["figure"])
    entries.append(_fig5_entry())

    manifest = {
        "schema": "lupine.paper.figures_manifest.v1",
        "paper": "paper/environment-error-field-2026-07-02.md",
        "style": {
            "widths_in": {"single_column": C.SINGLE_COL_IN,
                          "double_column": C.DOUBLE_COL_IN},
            "palette": "Okabe-Ito (colorblind-safe)",
            "model_colors": dict(C.MODEL_COLORS),
            "font": "DejaVu Sans 8 pt, TrueType embedded (pdf.fonttype 42)",
            "formats": ["PDF (vector)", "PNG (300 dpi)"],
            "titles": "none in-figure; captions live in the manuscript",
        },
        "environment": {
            "python": sys.version.split()[0],
            "matplotlib": matplotlib.__version__,
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
        },
        "error_convention": "signed relative error = (pred - ref) / |ref|",
        "data_notes": [
            (
                "Fig 1b uses the registered H3 medians from analysis/"
                "r2_mpa0_confirmatory.json. Recomputing the same statistic "
                "directly from bound evidence gives identical defect "
                "medians but slightly larger bulk medians (ratios 52.2/"
                "20.1/12.4/4.2 vs 57.0/21.4/15.3/7.9): the evidence binder "
                "carries a Cr B0 reference (42 bulk cells) that the "
                "y_matrix_targets compilation excludes as too coarse "
                "(41 bulk cells), and some evidence B0 references are "
                "experimental where the registered analysis preferred "
                "DFT-PBE targets."
            ),
            (
                "Ca and Sr have predicted stacking-fault energies but no "
                "bound references (explicit compilation gaps); the SFE "
                "panels use the 7 fcc metals with references."
            ),
            (
                "V's vacancy reference is DFT-PBE (Ma & Dudarev, PRM 3, "
                "013605 (2019)); the manuscript's note about vanadium's "
                "absent vacancy energy refers to the experimental value."
            ),
            (
                "Blind-prediction strict wins: 27/36 at float64 precision, "
                "26/36 at the manuscript's kernel-checked x10^4 integer "
                "precision (one margin is exactly zero at that scaling)."
            ),
        ],
        "inputs_sha256": dict(sorted(all_inputs.items())),
        "artifacts": entries,
    }
    manifest_path = C.OUT_DIR / "figures_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=1), encoding="utf-8", newline="\n"
    )
    log.info("wrote %s", manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
