"""B-site vacancy formation panel for the lead-free-perovskite candidates.

Article-designated failure mode for target class #5 (lupine.science,
five-materials-for-5-to-12-gtco2-year): uMLIPs underestimate Sn vacancy
formation because vacancies create under-coordinated neighbours. This runner
measures the neutral, referenced B-site vacancy formation energy
(``compute_referenced_vacancy_formation``: E_vac = E_defect + mu - E_bulk)
for the round-1 perovskite candidates across the 4 local MLIPs and reports
cross-model relative dispersion per compound, compared against the SAME
compounds' bulk a0/B0/C11 dispersions from the round-1 report (H3: defect
observables should disperse more across models than bulk observables).

No flag/refuse thresholds exist for E_vac yet — dispersions are reported
descriptively; deriving per-property vacancy thresholds is a Round-3
calibration need.

Inputs:
* relaxed a0 per (compound, model) is REUSED from
  ``data/candidates/round1/report.json`` (per_model properties a0), not
  re-relaxed, so the defect sits on each model's own relaxed lattice.

Outputs (in --out-dir):
* ``report.json``  (lupine.perovskite_vacancy_panel.v1)
* ``REPORT.md``    (human-readable tables + honesty notes)

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_perovskite_vacancy_panel.py \
        --device cuda
Smoke (one compound, one model):
    ... run_perovskite_vacancy_panel.py --device cuda \
        --compounds CsPbI3 --models chgnet
"""

from __future__ import annotations

# Dynamo OFF before any torch import (no Triton on Windows); CLI only.
import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from run_discovery_gates import (  # noqa: E402
    DEFAULT_MODELS,
    MODEL_REGISTRY,
    build_calculator,
)

from lupine_distill.statics import (  # noqa: E402
    InputValidationError,
    StaticsError,
    compute_referenced_vacancy_formation,
    relative_dispersion,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("perovskite_vacancy_panel")

REPORT_SCHEMA = "lupine.perovskite_vacancy_panel.v1"
ROUND1_REPORT = _REPO_ROOT / "data" / "candidates" / "round1" / "report.json"
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "candidates" / "perovskite_vacancy_panel"

#: One B-site vacancy in a 2x2x2 perovskite supercell (40 -> 39 atoms).
SUPERCELL: tuple[int, int, int] = (2, 2, 2)

#: If any completed (compound, model) cell exceeds this, drop the next
#: compound in DROP_ORDER from the remaining panel instead of hanging.
CELL_BUDGET_SECONDS: float = 240.0

#: Scope-reduction order under the wall-time guard.
DROP_ORDER: tuple[str, ...] = ("CsSnCl3", "CsGeI3")

#: (round1 key, formula, B-site vacancy species, reference_structure override).
#: ASE's reference state for Sn is beta-Sn (bct, white tin), which the defects
#: module does not support (fcc/bcc/diamond only) — Sn therefore gets an
#: explicit diamond override, i.e. alpha-Sn (grey tin), the correct T=0
#: elemental ground state for an athermal chemical potential anyway.
#: Ge (diamond) and Pb (fcc) resolve from ASE reference states by default.
PANEL: tuple[tuple[str, str, str, str | None], ...] = (
    ("hp-cssni3", "CsSnI3", "Sn", "diamond"),
    ("hp-cssnbr3", "CsSnBr3", "Sn", "diamond"),
    ("hp-cssncl3", "CsSnCl3", "Sn", "diamond"),
    ("hp-csgei3", "CsGeI3", "Ge", None),
    ("hp-cspbi3-control", "CsPbI3", "Pb", None),
)

#: Honesty notes carried verbatim into report.json / REPORT.md.
HONESTY_NOTES: tuple[str, ...] = (
    "Neutral vacancies only: no charged defects, no electrostatic alignment "
    "or image-charge corrections; for these halide perovskites the physical "
    "vacancy is usually charged (V_Sn'' etc.), so values are the "
    "metal-rich-limit NEUTRAL formation energy.",
    "Finite-size: single 2x2x2 (40-atom) supercell, one vacancy, "
    "fixed-cell position relaxation; no supercell-size extrapolation. "
    "Defect-defect interaction under PBC is NOT converged out.",
    "Athermal: T=0 statics, no vibrational or configurational entropy.",
    "Chemical potential is the metal-rich limit: mu(X) from the relaxed "
    "elemental bulk under the SAME calculator (alpha-Sn diamond for Sn — "
    "ASE's default beta-Sn bct reference is unsupported by the module and "
    "alpha-Sn is the T=0 ground state; diamond-Ge; fcc-Pb). Halide-rich "
    "conditions would shift all values by the compound formation energy.",
    "Cubic perovskite reference phase: a0 per (compound, model) is reused "
    "from data/candidates/round1/report.json (per_model properties a0); the "
    "room-temperature phases of several of these compounds are distorted "
    "(orthorhombic/monoclinic) — this panel probes the cubic prototype.",
    "No thresholds exist for E_vac dispersion: values are descriptive. "
    "Deriving per-property vacancy flag/refuse percentiles (as thresholds.v2 "
    "did for a0/B0/C11/C12/C44) is a Round-3 calibration need.",
    "Model non-independence: mace-mp-small and mace-mp-medium share "
    "architecture and training data; dispersion is ensemble spread, not "
    "independent-error spread.",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated model ids (default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--compounds",
        default="",
        help=(
            "Comma-separated formulas to run (default: all "
            f"{len(PANEL)}); e.g. --compounds CsPbI3 for a smoke run"
        ),
    )
    parser.add_argument(
        "--round1-report",
        default=str(ROUND1_REPORT),
        help="Round-1 candidates report supplying relaxed a0 per (compound, model)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory for report.json / REPORT.md",
    )
    parser.add_argument(
        "--cell-budget-seconds",
        type=float,
        default=CELL_BUDGET_SECONDS,
        help="Wall-time guard per (compound, model) cell before scope reduction",
    )
    return parser.parse_args(argv)


def select_panel(csv: str) -> list[tuple[str, str, str, str | None]]:
    if not csv.strip():
        return list(PANEL)
    wanted = [c.strip() for c in csv.split(",") if c.strip()]
    by_formula = {entry[1]: entry for entry in PANEL}
    unknown = [c for c in wanted if c not in by_formula]
    if unknown:
        raise SystemExit(
            f"unknown compound(s) {unknown}; known: "
            f"{', '.join(f for _, f, _, _ in PANEL)}"
        )
    return [by_formula[c] for c in wanted]


def load_round1(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"round-1 report not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def round1_a0(round1: dict[str, object], key: str, model_id: str) -> float:
    """Relaxed a0 for (compound, model) from the round-1 report."""
    try:
        candidates = round1["candidates"]
        a0 = candidates[key]["per_model"][model_id]["properties"]["a0"]
    except (KeyError, TypeError) as exc:
        raise SystemExit(
            f"round-1 report has no relaxed a0 for {key!r} x {model_id!r}: {exc}"
        ) from exc
    if not isinstance(a0, (int, float)):
        raise SystemExit(f"round-1 a0 for {key!r} x {model_id!r} is not numeric: {a0!r}")
    return float(a0)


def round1_bulk_dispersions(
    round1: dict[str, object], key: str
) -> dict[str, float | None]:
    """Bulk a0/b0/c11 cross-model dispersions from the round-1 gates block."""
    concordance = round1["candidates"][key].get("gates", {}).get("concordance", {})
    out: dict[str, float | None] = {}
    for prop in ("a0", "b0", "c11"):
        block = concordance.get(prop, {})
        value = block.get("values", {}).get("dispersion")
        out[prop] = float(value) if isinstance(value, (int, float)) else None
    return out


def summarize_compound(
    formula: str,
    vacancy_species: str,
    cells: dict[str, dict[str, object]],
    bulk_dispersions: dict[str, float | None],
) -> dict[str, object]:
    """Per-compound dispersion summary + defect-vs-bulk comparison."""
    e_vac_by_model = {
        model: cell["vacancy_formation_ev"]
        for model, cell in cells.items()
        if "vacancy_formation_ev" in cell
    }
    values = [float(v) for v in e_vac_by_model.values()]
    dispersion: float | None = None
    dispersion_error: str | None = None
    if len(values) >= 2:
        try:
            dispersion = relative_dispersion(values)
        except InputValidationError as exc:
            dispersion_error = str(exc)
    spread_ev = (max(values) - min(values)) if len(values) >= 2 else None
    ratios = {
        f"e_vac_vs_{prop}": (
            dispersion / bulk
            if dispersion is not None and bulk not in (None, 0.0)
            else None
        )
        for prop, bulk in bulk_dispersions.items()
    }
    return {
        "formula": formula,
        "vacancy_species": vacancy_species,
        "e_vac_ev_by_model": e_vac_by_model,
        "n_models": len(values),
        "e_vac_relative_dispersion": dispersion,
        "e_vac_relative_dispersion_error": dispersion_error,
        "e_vac_absolute_spread_ev": spread_ev,
        "bulk_relative_dispersions_round1": bulk_dispersions,
        "dispersion_ratios_defect_over_bulk": ratios,
    }


def render_markdown(report: dict[str, object]) -> str:
    """REPORT.md from the report payload."""
    models: list[str] = list(report["models"])
    lines: list[str] = [
        "# Perovskite B-site vacancy panel (neutral, referenced)",
        "",
        f"Generated: {report['generated_at']}  ",
        f"Schema: `{report['schema']}`  ",
        f"Device: {report['device']} | Supercell: "
        f"{'x'.join(str(n) for n in report['parameters']['supercell'])} "
        "(one B-site vacancy, fixed-cell position relaxation)  ",
        f"E_vac = E_defect + mu - E_bulk "
        f"(metal-rich-limit neutral vacancy; fmax = "
        f"{report['parameters']['fmax_ev_per_angstrom']} eV/A)",
        "",
        "Article context: target class #5 failure mode — uMLIPs are expected "
        "to misestimate Sn vacancy formation (under-coordinated neighbours), "
        "so the H3 signature is E_vac dispersing MORE across models than the "
        "same compounds' bulk properties.",
        "",
        "## E_vac (eV) per compound x model",
        "",
        "| Compound | Vacancy | " + " | ".join(models) + " | Rel. dispersion | Spread (eV) |",
        "|---|---|" + "---|" * (len(models) + 2),
    ]
    summaries: dict[str, dict[str, object]] = report["compounds"]
    for key, s in summaries.items():
        row = [s["formula"], f"V_{s['vacancy_species']}"]
        for model in models:
            v = s["e_vac_ev_by_model"].get(model)
            row.append(f"{v:.3f}" if isinstance(v, (int, float)) else "FAILED")
        d = s["e_vac_relative_dispersion"]
        row.append(f"{d:.3f}" if isinstance(d, (int, float)) else "n/a")
        sp = s["e_vac_absolute_spread_ev"]
        row.append(f"{sp:.3f}" if isinstance(sp, (int, float)) else "n/a")
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "## Defect vs bulk cross-model dispersion (bulk from round-1 report)",
        "",
        "| Compound | E_vac disp | a0 disp | b0 disp | c11 disp | "
        "E_vac/a0 | E_vac/b0 | E_vac/c11 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, s in summaries.items():
        bulk = s["bulk_relative_dispersions_round1"]
        ratios = s["dispersion_ratios_defect_over_bulk"]
        d = s["e_vac_relative_dispersion"]

        def fmt(x: object, digits: int = 3) -> str:
            return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "n/a"

        lines.append(
            "| "
            + " | ".join(
                [
                    s["formula"],
                    fmt(d),
                    fmt(bulk.get("a0"), 4),
                    fmt(bulk.get("b0")),
                    fmt(bulk.get("c11")),
                    fmt(ratios.get("e_vac_vs_a0"), 1),
                    fmt(ratios.get("e_vac_vs_b0"), 1),
                    fmt(ratios.get("e_vac_vs_c11"), 1),
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Elemental chemical potentials mu (eV/atom) per model",
        "",
        "| Species | Reference | " + " | ".join(models) + " |",
        "|---|---|" + "---|" * len(models),
    ]
    mu_table: dict[str, dict[str, object]] = report["chemical_potentials"]
    for species, entry in mu_table.items():
        row = [species, str(entry["reference_structure"])]
        for model in models:
            v = entry["mu_ev_per_atom_by_model"].get(model)
            row.append(f"{v:.4f}" if isinstance(v, (int, float)) else "n/a")
        lines.append("| " + " | ".join(row) + " |")
    lines += ["", "## Provenance", ""]
    for item in report["provenance"]:
        lines.append(f"- {item}")
    if report["scope_reductions"]:
        lines += ["", "## Scope reductions (wall-time guard)", ""]
        for item in report["scope_reductions"]:
            lines.append(f"- {item}")
    lines += ["", "## Honesty notes", ""]
    for note in report["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must name at least one model")
    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model id(s): {unknown}")
    panel = select_panel(args.compounds)
    round1_path = Path(args.round1_report)
    round1 = load_round1(round1_path)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # a0 provenance up front so a missing cell fails before GPU work.
    a0_by_cell = {
        (key, model): round1_a0(round1, key, model)
        for key, _, _, _ in panel
        for model in models
    }

    active = list(panel)
    dropped: list[str] = []
    scope_reductions: list[str] = []
    cells: dict[str, dict[str, dict[str, object]]] = {key: {} for key, _, _, _ in panel}
    calculator_versions: dict[str, str] = {}
    mu_by_species: dict[str, dict[str, object]] = {}
    t_run0 = time.perf_counter()
    n_ok = n_failed = 0

    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for key, formula, species, ref_override in list(active):
            a0 = a0_by_cell[(key, model_id)]
            log.info("%s (V_%s, a0=%.4f A) x %s", formula, species, a0, model_id)
            t_cell = time.perf_counter()
            try:
                result = compute_referenced_vacancy_formation(
                    calculator,
                    formula,
                    "perovskite",
                    a0,
                    vacancy_species=species,
                    supercell=SUPERCELL,
                    reference_structure=ref_override,
                )
            except StaticsError as exc:
                wall = time.perf_counter() - t_cell
                log.info("  MEASUREMENT FAILED after %.1f s: %s", wall, exc)
                cells[key][model_id] = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "a0_angstrom": a0,
                    "wall_time_seconds": wall,
                }
                n_failed += 1
                continue
            wall = time.perf_counter() - t_cell
            log.info(
                "  E_vac = %+.3f eV (mu=%.4f eV/atom [%s], %d relax steps, %.1f s)",
                result.vacancy_formation_ev,
                result.mu_ev_per_atom,
                result.reference_structure,
                result.n_relax_steps,
                wall,
            )
            cells[key][model_id] = {
                "vacancy_formation_ev": result.vacancy_formation_ev,
                "e_bulk_ev": result.e_bulk_ev,
                "e_defect_ev": result.e_defect_ev,
                "mu_ev_per_atom": result.mu_ev_per_atom,
                "reference_structure": result.reference_structure,
                "a0_angstrom": a0,
                "n_atoms_perfect": result.n_atoms_perfect,
                "vacancy_index": result.vacancy_index,
                "n_relax_steps": result.n_relax_steps,
                "wall_time_seconds": wall,
            }
            entry = mu_by_species.setdefault(
                species,
                {
                    "reference_structure": result.reference_structure,
                    "ase_default_overridden": ref_override is not None,
                    "mu_ev_per_atom_by_model": {},
                },
            )
            entry["mu_ev_per_atom_by_model"][model_id] = result.mu_ev_per_atom
            n_ok += 1
            if wall > args.cell_budget_seconds:
                for drop_formula in DROP_ORDER:
                    match = next(
                        (e for e in active if e[1] == drop_formula and e[1] != formula),
                        None,
                    )
                    if match is not None:
                        active.remove(match)
                        dropped.append(drop_formula)
                        msg = (
                            f"{formula} x {model_id} took {wall:.0f} s "
                            f"(> {args.cell_budget_seconds:.0f} s budget); dropped "
                            f"{drop_formula} from the remaining panel"
                        )
                        scope_reductions.append(msg)
                        log.info("  SCOPE REDUCED: %s", msg)
                        break
        del calculator  # release GPU memory before the next model loads

    compounds = {
        key: summarize_compound(
            formula,
            species,
            cells[key],
            round1_bulk_dispersions(round1, key),
        )
        for key, formula, species, _ in panel
        if cells[key]
    }
    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "models": models,
        "calculator_versions": calculator_versions,
        "parameters": {
            "structure_type": "perovskite",
            "supercell": SUPERCELL,
            "fmax_ev_per_angstrom": 0.01,
            "optimizer": "FIRE",
            "observable": "referenced_vacancy_formation (E_vac = E_defect + mu - E_bulk)",
            "cell_budget_seconds": args.cell_budget_seconds,
        },
        "provenance": [
            f"Relaxed a0 per (compound, model) reused from {round1_path.as_posix()} "
            f"(candidates[*].per_model[*].properties.a0, "
            f"generated_at {round1.get('generated_at')}); no re-relaxation.",
            "Bulk a0/b0/c11 dispersions quoted from the same round-1 report "
            "(gates.concordance blocks, thresholds.v2 baseline).",
            "Elemental references: Sn -> explicit 'diamond' override (alpha-Sn; "
            "ASE's default Sn reference state is beta-Sn bct, unsupported by "
            "compute_referenced_vacancy_formation); Ge -> ASE default 'diamond'; "
            "Pb -> ASE default 'fcc'. mu relaxed per model by the module's "
            "recentring EOS scan.",
            "Dispersion metric: (max - min) / |median| across models "
            "(lupine_distill.statics.gates.relative_dispersion).",
        ],
        "scope_reductions": scope_reductions,
        "dropped_compounds": dropped,
        "cells": cells,
        "chemical_potentials": mu_by_species,
        "compounds": compounds,
        "n_cells_ok": n_ok,
        "n_cells_failed": n_failed,
        "notes": list(HONESTY_NOTES),
        "total_wall_time_seconds": time.perf_counter() - t_run0,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "REPORT.md").write_text(render_markdown(report), encoding="utf-8")
    log.info(
        "panel: %d ok / %d failed cells in %.1f s -> %s",
        n_ok,
        n_failed,
        report["total_wall_time_seconds"],
        out_dir,
    )
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
