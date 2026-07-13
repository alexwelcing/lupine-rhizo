"""Schottky-pair formation panel over the halide rocksalt set (GPU lane).

For each rocksalt 1:1 binary in the halide panel (LiF/LiCl/LiBr/LiI/NaCl/MgO)
x each MODEL_REGISTRY model, computes the charge-balanced Schottky-pair
formation energy (``statics.compute_schottky_formation``: remove one full
formula unit, maximally separated under PBC, relax positions at fixed cell)
on a 2x2x2 supercell. The bulk lattice constant is NOT re-relaxed here: each
(compound, model) cell reuses THAT model's relaxed a0 from the halide-panel
discovery-gates report, and the report path + generated_at travel in the
evidence provenance.

Outputs (--out-dir, default data/defects/schottky_panel/):
* one ``lupine.mlip.calc_evidence.v1`` JSON per (compound, model) cell,
* ``panel_summary.json`` with per-compound cross-model dispersion of the
  Schottky pair energy (relative (max-min)/|median| plus absolute max-min eV)
  and wall times.

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_schottky_panel.py \
        --device cuda
Smoke (one compound, all models):
    ... run_schottky_panel.py --device cuda --compounds LiF
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
from typing import Final, Mapping

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

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import PropertyValue  # noqa: E402
from lupine_distill.statics import (  # noqa: E402
    InputValidationError,
    SchottkyFormationResult,
    StaticsError,
    compute_schottky_formation,
    relative_dispersion,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("schottky_panel")

SUMMARY_SCHEMA: Final[str] = "lupine.schottky_panel_summary.v1"
GATES_REPORT_SCHEMA: Final[str] = "lupine.discovery_gates.v1"

#: The halide-panel rocksalt 1:1 binaries (labels match the report subjects).
PANEL_COMPOUNDS: Final[tuple[tuple[str, str], ...]] = (
    ("LiF", "rocksalt"),
    ("LiCl", "rocksalt"),
    ("LiBr", "rocksalt"),
    ("LiI", "rocksalt"),
    ("NaCl", "rocksalt"),
    ("MgO", "rocksalt"),
)

#: Honesty notes carried verbatim into panel_summary.json.
PANEL_NOTES: Final[tuple[str, ...]] = (
    "Charge-balanced (neutral) Schottky pair: one atom of each species "
    "removed, maximally separated under PBC, positions relaxed at fixed "
    "cell; E_pair = E_defect - (N-2)/N * E_bulk. No chemical potentials "
    "enter (stoichiometry preserved); alignment/charging corrections are "
    "out of Tier-1 scope.",
    "a0 reuse: each (compound, model) cell uses THAT model's relaxed a0 "
    "from the halide-panel report rather than re-relaxing, so the defect "
    "cell sits at the same lattice the concordance gates were measured at; "
    "the source report path + generated_at are recorded per cell.",
    "Finite-size: a 2x2x2 rocksalt supercell (64 atoms) leaves the vacancy "
    "pair within interaction range of its images; pair energies carry an "
    "uncorrected finite-size offset that partially cancels in cross-model "
    "comparisons at fixed cell size.",
    "Model non-independence: the MACE variants share architecture and "
    "training data; cross-model dispersion is ensemble spread, not "
    "independent-error spread.",
)


# --------------------------------------------------------------------------
# a0 reuse from the halide-panel report
# --------------------------------------------------------------------------


def load_relaxed_a0(
    report_path: Path,
) -> tuple[dict[tuple[str, str], float], dict[str, str]]:
    """Per-(formula, model) relaxed a0 from a discovery-gates report.

    Returns ``(a0 map, provenance)`` where provenance carries the report
    path (repo-relative when possible) and its ``generated_at``.
    """
    report_path = Path(report_path)
    if not report_path.is_file():
        raise InputValidationError(f"halide-panel report missing: {report_path}")
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(
            f"cannot read report {report_path}: {exc}"
        ) from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != GATES_REPORT_SCHEMA:
        raise InputValidationError(
            f"{report_path}: expected schema {GATES_REPORT_SCHEMA!r}, got "
            f"{payload.get('schema')!r}"
        )
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        raise InputValidationError(f"{report_path}: missing 'generated_at' string")
    subjects = payload.get("subjects")
    if not isinstance(subjects, Mapping) or not subjects:
        raise InputValidationError(f"{report_path}: no 'subjects' mapping")
    a0_map: dict[tuple[str, str], float] = {}
    for label, subject in subjects.items():
        if not isinstance(subject, Mapping):
            raise InputValidationError(f"{report_path}: subject {label!r} malformed")
        formula = str(subject.get("formula", ""))
        per_model = subject.get("per_model")
        if not formula or not isinstance(per_model, Mapping):
            continue
        for model_id, record in per_model.items():
            if not isinstance(record, Mapping) or "error" in record:
                continue
            properties = record.get("properties")
            if not isinstance(properties, Mapping) or "a0" not in properties:
                continue
            a0_map[(formula, str(model_id))] = float(properties["a0"])  # type: ignore[arg-type]
    if not a0_map:
        raise InputValidationError(f"{report_path}: no per-model a0 values found")
    try:
        report_rel = report_path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        report_rel = report_path.resolve().as_posix()
    return a0_map, {"report": report_rel, "generated_at": generated_at}


# --------------------------------------------------------------------------
# evidence assembly
# --------------------------------------------------------------------------


def evidence_from_result(
    *,
    result: SchottkyFormationResult,
    model_id: str,
    device: str,
    calculator_version: str,
    a0_provenance: Mapping[str, str],
    run_label: str | None,
) -> dict[str, object]:
    """calc_evidence.v1 payload for one Schottky cell (a0 provenance inline)."""
    properties = [
        PropertyValue(
            name="E_schottky_pair", value=result.schottky_pair_ev, unit="eV"
        ),
        PropertyValue(
            name="E_schottky_per_vacancy",
            value=result.schottky_per_vacancy_ev,
            unit="eV",
        ),
    ]
    inputs = {
        "model_id": model_id,
        "device": device,
        "schottky": result.canonical_inputs(),
        "a0_source": dict(a0_provenance),
    }
    evidence = build_calc_evidence(
        material=result.formula,
        model_id=model_id,
        backend="ase",
        device=device,  # type: ignore[arg-type]
        calculator_version=calculator_version,
        inputs=inputs,
        properties=properties,
        run_label=run_label,
        computed_at=datetime.now(timezone.utc),
    )
    return evidence.model_dump(mode="json", by_alias=True)


def summarize_dispersions(
    pair_energies: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, object]]:
    """Per-compound cross-model dispersion of the Schottky pair energy."""
    summary: dict[str, dict[str, object]] = {}
    for formula, by_model in sorted(pair_energies.items()):
        if len(by_model) < 2:
            summary[formula] = {
                "n_models": len(by_model),
                "note": "need >= 2 model values for a dispersion",
            }
            continue
        values = list(by_model.values())
        summary[formula] = {
            "n_models": len(by_model),
            "pair_energy_by_model_ev": dict(sorted(by_model.items())),
            "relative_dispersion": relative_dispersion(values),
            "absolute_spread_ev": max(values) - min(values),
        }
    return summary


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


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
            "Comma-separated formulas (default: all "
            f"{len(PANEL_COMPOUNDS)} halide-panel rocksalts); e.g. "
            "--compounds LiF for a smoke run"
        ),
    )
    parser.add_argument(
        "--supercell", type=int, default=2, help="Cubic supercell repeat (n,n,n)"
    )
    parser.add_argument(
        "--halide-report",
        default=str(
            _REPO_ROOT / "data" / "climate_targets" / "halide_panel" / "report.json"
        ),
        help="Discovery-gates report supplying per-model relaxed a0",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "defects" / "schottky_panel"),
        help="Calc-evidence + summary output directory",
    )
    parser.add_argument("--run-label", default=None, help="Optional evidence run label")
    return parser.parse_args(argv)


def select_compounds(csv: str) -> tuple[tuple[str, str], ...]:
    if not csv.strip():
        return PANEL_COMPOUNDS
    wanted = [c.strip() for c in csv.split(",") if c.strip()]
    by_formula = {formula: (formula, structure) for formula, structure in PANEL_COMPOUNDS}
    unknown = [c for c in wanted if c not in by_formula]
    if unknown:
        raise SystemExit(
            f"unknown compound(s) {unknown}; known: "
            f"{', '.join(f for f, _ in PANEL_COMPOUNDS)}"
        )
    return tuple(by_formula[c] for c in wanted)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must name at least one model")
    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model id(s): {unknown}")
    if args.supercell < 2:
        raise SystemExit(
            "--supercell must be >= 2 (a 1x1x1 rocksalt cell cannot separate "
            "the vacancy pair from itself)"
        )
    compounds = select_compounds(args.compounds)
    try:
        a0_map, a0_provenance = load_relaxed_a0(Path(args.halide_report))
    except InputValidationError as exc:
        raise SystemExit(f"cannot load relaxed a0 values: {exc}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repeat = (args.supercell, args.supercell, args.supercell)

    cells: dict[str, dict[str, object]] = {}
    pair_energies: dict[str, dict[str, float]] = {}
    calculator_versions: dict[str, str] = {}
    t_run0 = time.perf_counter()
    n_ok = n_failed = 0
    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for formula, structure_type in compounds:
            label = f"{formula}_{structure_type}"
            cell_key = f"{label}_{model_id}"
            a0 = a0_map.get((formula, model_id))
            if a0 is None:
                log.info("%s x %s: NO relaxed a0 in report, skipped", label, model_id)
                cells[cell_key] = {
                    "error": (
                        f"no relaxed a0 for ({formula}, {model_id}) in "
                        f"{a0_provenance['report']}"
                    )
                }
                n_failed += 1
                continue
            log.info("%s x %s (a0 = %.4f A)", label, model_id, a0)
            t_cell = time.perf_counter()
            try:
                result = compute_schottky_formation(
                    calculator,
                    formula,
                    structure_type,
                    a0,
                    supercell=repeat,
                )
            except StaticsError as exc:
                log.info("  FAILED: %s", exc)
                cells[cell_key] = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "wall_time_seconds": time.perf_counter() - t_cell,
                }
                n_failed += 1
                continue
            log.info(
                "  E_pair = %.3f eV (%.3f eV/vacancy, %d steps, %.1fs)",
                result.schottky_pair_ev,
                result.schottky_per_vacancy_ev,
                result.n_relax_steps,
                result.wall_time_seconds,
            )
            payload = evidence_from_result(
                result=result,
                model_id=model_id,
                device=args.device,
                calculator_version=version,
                a0_provenance=a0_provenance,
                run_label=args.run_label,
            )
            evidence_path = out_dir / f"{cell_key}.evidence.json"
            evidence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            cells[cell_key] = {
                "a0_angstrom": a0,
                "schottky_pair_ev": result.schottky_pair_ev,
                "schottky_per_vacancy_ev": result.schottky_per_vacancy_ev,
                "pair_separation_angstrom": result.pair_separation_angstrom,
                "n_relax_steps": result.n_relax_steps,
                "wall_time_seconds": time.perf_counter() - t_cell,
            }
            pair_energies.setdefault(formula, {})[model_id] = result.schottky_pair_ev
            n_ok += 1
        del calculator  # release GPU memory before the next model loads

    summary = {
        "schema": SUMMARY_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "models": models,
        "calculator_versions": calculator_versions,
        "compounds": [f"{f}_{s}" for f, s in compounds],
        "parameters": {"supercell": list(repeat)},
        "a0_source": dict(a0_provenance),
        "n_cells_ok": n_ok,
        "n_cells_failed": n_failed,
        "cells": cells,
        "cross_model_dispersion": summarize_dispersions(pair_energies),
        "notes": list(PANEL_NOTES),
        "total_wall_time_seconds": time.perf_counter() - t_run0,
    }
    summary_path = out_dir / "panel_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info(
        "schottky panel: %d ok / %d failed cells in %.1f s -> %s",
        n_ok,
        n_failed,
        summary["total_wall_time_seconds"],
        out_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
