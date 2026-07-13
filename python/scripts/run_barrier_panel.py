"""Cation-vacancy migration-barrier panel over the halide rocksalt anchors.

Kinetics lane companion to the 2026-07-13 halide statics panel: for each of
LiF/LiCl/LiBr/LiI/NaCl (rocksalt) x local MLIP the runner builds the
nearest-neighbour <110> cation-vacancy hop
(``lupine_distill.statics.build_cation_vacancy_hop``), relaxes both
endpoints, and converges a climbing-image NEB
(``compute_migration_barrier``) to get forward/backward migration barriers.
Cross-model relative dispersion of the forward barrier is reported per
compound (``gates.relative_dispersion``, descriptive — no flag/refuse
thresholds exist for barriers yet).

Inputs:
* relaxed a0 per (compound, model) is REUSED from the halide panel report
  (``subjects[<label>].per_model[<model>].properties.a0``) when present, so
  the hop sits on each model's own relaxed lattice; a missing report or cell
  falls back to the covalent-radius estimate
  (``estimate_lattice_constant``) — the provenance is recorded per cell.
* optional references file (``--targets``): flat ``{"LiF": 0.7}`` or nested
  ``{"targets": {"LiF": {"barrier_ev": 0.7, "source": "..."}}}``; a missing
  file is tolerated (the panel runs without reference comparison).

Outputs (in --out-dir):
* ``report.json``  (lupine.kinetics_barrier_panel.v1)
* ``REPORT.md``    (human-readable tables + honesty notes)

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_barrier_panel.py \
        --device cuda
Smoke (one compound, one model):
    ... run_barrier_panel.py --device cuda --compounds LiF --models chgnet
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
from typing import Mapping

import numpy as np

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
    build_cation_vacancy_hop,
    compute_migration_barrier,
    estimate_lattice_constant,
    relative_dispersion,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("barrier_panel")

REPORT_SCHEMA = "lupine.kinetics_barrier_panel.v1"
A0_REPORT = _REPO_ROOT / "data" / "climate_targets" / "halide_panel" / "report.json"
DEFAULT_TARGETS = _REPO_ROOT / "data" / "candidates" / "kinetics_targets.json"
DEFAULT_OUT_DIR = _REPO_ROOT / "data" / "kinetics" / "barrier_panel"

DEFAULT_N_IMAGES = 5
DEFAULT_SUPERCELL = 2  # 2x2x2 rocksalt conventional = 64 atoms
DEFAULT_FMAX = 0.05
DEFAULT_MAX_STEPS = 300

#: (halide-panel subject label, formula). The label keys the a0 lookup.
PANEL: tuple[tuple[str, str], ...] = (
    ("LiF_rocksalt", "LiF"),
    ("LiCl_rocksalt", "LiCl"),
    ("LiBr_rocksalt", "LiBr"),
    ("LiI_rocksalt", "LiI"),
    ("NaCl_rocksalt", "NaCl"),
)

#: Honesty notes carried verbatim into report.json / REPORT.md.
HONESTY_NOTES: tuple[str, ...] = (
    "Neutral vacancy hop only: no charged defects, no electrostatic "
    "alignment or image-charge corrections; the physical migrating defect "
    "in these halides is usually charged (V_Li'), so values are the "
    "NEUTRAL-cell CI-NEB barrier.",
    "Finite-size: single 2x2x2 (64-atom) rocksalt supercell, one vacancy, "
    "fixed-cell CI-NEB; defect-defect and elastic image interactions under "
    "PBC are NOT converged out and no supercell extrapolation is done.",
    "Athermal: T=0 minimum-energy-path barrier; no attempt frequencies, no "
    "harmonic prefactors, no finite-temperature or quantum corrections — "
    "this is E_m, not a diffusivity.",
    "Single mechanism: only the nearest-neighbour <110> cation-vacancy hop "
    "is probed; other mechanisms (anion hops, curved <110> paths, "
    "interstitialcy) are out of scope.",
    "Symmetric hop: forward and backward barriers should coincide; the "
    "recorded asymmetry is a numerical convergence check, not physics.",
    "No thresholds exist for barrier dispersion: values are descriptive. "
    "Deriving kinetics flag/refuse percentiles is future calibration work.",
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
            f"Comma-separated formulas to run (default: all {len(PANEL)}); "
            "e.g. --compounds LiF for a smoke run"
        ),
    )
    parser.add_argument(
        "--n-images",
        type=int,
        default=DEFAULT_N_IMAGES,
        help=f"Interior NEB images (default: {DEFAULT_N_IMAGES})",
    )
    parser.add_argument(
        "--supercell",
        type=int,
        default=DEFAULT_SUPERCELL,
        help=f"Cubic supercell repeat (default: {DEFAULT_SUPERCELL} -> 64 atoms)",
    )
    parser.add_argument(
        "--fmax",
        type=float,
        default=DEFAULT_FMAX,
        help=f"Endpoint + NEB force convergence, eV/A (default: {DEFAULT_FMAX})",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        help=f"Step budget per relaxation / NEB (default: {DEFAULT_MAX_STEPS})",
    )
    parser.add_argument(
        "--a0-report",
        default=str(A0_REPORT),
        help="Halide panel report supplying relaxed a0 per (compound, model)",
    )
    parser.add_argument(
        "--targets",
        default=str(DEFAULT_TARGETS),
        help="Optional kinetics references JSON (missing file: run without refs)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Output directory for report.json / REPORT.md",
    )
    return parser.parse_args(argv)


def select_panel(csv: str) -> list[tuple[str, str]]:
    if not csv.strip():
        return list(PANEL)
    wanted = [c.strip() for c in csv.split(",") if c.strip()]
    by_formula = {formula: (label, formula) for label, formula in PANEL}
    unknown = [c for c in wanted if c not in by_formula]
    if unknown:
        raise SystemExit(
            f"unknown compound(s) {unknown}; known: {', '.join(f for _, f in PANEL)}"
        )
    return [by_formula[c] for c in wanted]


def load_a0_report(path: Path) -> dict[str, object] | None:
    """Halide panel report, or None when absent (a0 falls back to estimates)."""
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read a0 report {path}: {exc}") from exc


def resolve_a0(
    a0_report: Mapping[str, object] | None,
    label: str,
    model_id: str,
    formula: str,
) -> tuple[float, str]:
    """(a0_angstrom, provenance) for one (compound, model) cell.

    Prefers the model's own relaxed a0 from the halide panel report; falls
    back to the deterministic covalent-radius estimate when the report (or
    the specific cell) is missing.
    """
    if a0_report is not None:
        subjects = a0_report.get("subjects")
        entry = subjects.get(label, {}) if isinstance(subjects, Mapping) else {}
        per_model = entry.get("per_model", {}) if isinstance(entry, Mapping) else {}
        cell = per_model.get(model_id, {}) if isinstance(per_model, Mapping) else {}
        props = cell.get("properties", {}) if isinstance(cell, Mapping) else {}
        a0 = props.get("a0") if isinstance(props, Mapping) else None
        if isinstance(a0, (int, float)) and not isinstance(a0, bool) and a0 > 0:
            return float(a0), (
                f"halide panel report subjects[{label}].per_model[{model_id}]"
                f".properties.a0 (model-relaxed)"
            )
    return (
        estimate_lattice_constant(formula, "rocksalt"),
        "covalent-radius estimate (estimate_lattice_constant; no report a0)",
    )


def load_targets(path: Path) -> dict[str, dict[str, object]] | None:
    """Optional kinetics references; None when the file does not exist.

    Accepts a flat ``{formula: barrier_ev}`` mapping or a nested
    ``{"targets": {formula: {"barrier_ev": x, "source": "..."}}}`` payload.
    A present-but-malformed file fails fast.
    """
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read targets file {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SystemExit(f"targets file {path} must be a JSON object")
    entries = payload.get("targets", payload)
    if not isinstance(entries, Mapping):
        raise SystemExit(f"targets file {path}: 'targets' must be a JSON object")
    normalized: dict[str, dict[str, object]] = {}
    for formula, value in entries.items():
        if formula in ("schema", "generated_at", "notes"):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            normalized[str(formula)] = {"barrier_ev": float(value), "source": None}
            continue
        if isinstance(value, Mapping):
            barrier = value.get("barrier_ev")
            if isinstance(barrier, (int, float)) and not isinstance(barrier, bool):
                normalized[str(formula)] = {
                    "barrier_ev": float(barrier),
                    "source": value.get("source"),
                }
                continue
        raise SystemExit(
            f"targets file {path}: entry {formula!r} must be a number or an "
            f"object with numeric 'barrier_ev', got {value!r}"
        )
    return normalized


def summarize_compound(
    formula: str,
    cells: Mapping[str, Mapping[str, object]],
    target: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Cross-model dispersion + optional reference comparison for one compound."""
    barriers = {
        model: float(cell["forward_barrier_ev"])
        for model, cell in cells.items()
        if "forward_barrier_ev" in cell
    }
    values = list(barriers.values())
    dispersion: float | None = None
    dispersion_error: str | None = None
    if len(values) >= 2:
        try:
            dispersion = relative_dispersion(values)
        except InputValidationError as exc:
            dispersion_error = str(exc)
    spread_ev = (max(values) - min(values)) if len(values) >= 2 else None
    asymmetries = [
        float(cell["barrier_asymmetry_ev"])
        for cell in cells.values()
        if "barrier_asymmetry_ev" in cell
    ]
    comparison: dict[str, object] | None = None
    if target is not None:
        reference = float(target["barrier_ev"])
        deltas = {model: barrier - reference for model, barrier in barriers.items()}
        comparison = {
            "reference_barrier_ev": reference,
            "source": target.get("source"),
            "delta_ev_by_model": deltas,
            "median_delta_ev": (
                float(np.median(list(deltas.values()))) if deltas else None
            ),
        }
    return {
        "formula": formula,
        "forward_barrier_ev_by_model": barriers,
        "n_models": len(values),
        "barrier_relative_dispersion": dispersion,
        "barrier_relative_dispersion_error": dispersion_error,
        "barrier_absolute_spread_ev": spread_ev,
        "max_barrier_asymmetry_ev": max(asymmetries) if asymmetries else None,
        "reference_comparison": comparison,
    }


def _fmt(x: object, digits: int = 3) -> str:
    return f"{x:.{digits}f}" if isinstance(x, (int, float)) else "n/a"


def render_markdown(report: dict[str, object]) -> str:
    """REPORT.md from the report payload."""
    models: list[str] = list(report["models"])
    params = report["parameters"]
    lines: list[str] = [
        "# Halide cation-vacancy migration-barrier panel (CI-NEB)",
        "",
        f"Generated: {report['generated_at']}  ",
        f"Schema: `{report['schema']}`  ",
        f"Device: {report['device']} | Supercell: "
        f"{params['supercell']}^3 rocksalt (one cation vacancy) | "
        f"{params['n_images']} interior images, climb={params['climb']}, "
        f"{params['neb_method']} tangent, fmax = {params['fmax_ev_per_angstrom']} eV/A",
        "",
        "Barrier = E_saddle - E_endpoint(relaxed) from the climbing-image "
        "NEB band; the <110> nearest-neighbour cation hop is symmetric, so "
        "forward ~ backward and the asymmetry is a convergence check.",
        "",
        "## Forward barrier (eV) per compound x model",
        "",
        "| Compound | " + " | ".join(models) + " | Rel. dispersion | Spread (eV) | Max asym (eV) |",
        "|---|" + "---|" * (len(models) + 3),
    ]
    summaries: dict[str, dict[str, object]] = report["compounds"]
    for s in summaries.values():
        row = [str(s["formula"])]
        for model in models:
            v = s["forward_barrier_ev_by_model"].get(model)
            row.append(_fmt(v) if isinstance(v, (int, float)) else "FAILED")
        row.append(_fmt(s["barrier_relative_dispersion"]))
        row.append(_fmt(s["barrier_absolute_spread_ev"]))
        row.append(_fmt(s["max_barrier_asymmetry_ev"], 4))
        lines.append("| " + " | ".join(row) + " |")
    if any(s.get("reference_comparison") for s in summaries.values()):
        lines += [
            "",
            "## Reference comparison (model - reference, eV)",
            "",
            "| Compound | Reference (eV) | " + " | ".join(models) + " | Median delta |",
            "|---|---|" + "---|" * (len(models) + 1),
        ]
        for s in summaries.values():
            comparison = s.get("reference_comparison")
            if not comparison:
                continue
            row = [str(s["formula"]), _fmt(comparison["reference_barrier_ev"])]
            for model in models:
                row.append(_fmt(comparison["delta_ev_by_model"].get(model), 3))
            row.append(_fmt(comparison["median_delta_ev"]))
            lines.append("| " + " | ".join(row) + " |")
    else:
        lines += [
            "",
            "_No kinetics references file was found; dispersions are reported "
            "without literature comparison._",
        ]
    lines += ["", "## Provenance", ""]
    for item in report["provenance"]:
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

    a0_report_path = Path(args.a0_report)
    a0_report = load_a0_report(a0_report_path)
    if a0_report is None:
        log.info(
            "a0 report %s not found; every cell falls back to the "
            "covalent-radius lattice estimate",
            a0_report_path,
        )
    targets_path = Path(args.targets)
    targets = load_targets(targets_path)
    if targets is None:
        log.info("targets file %s not found; running without references", targets_path)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cells: dict[str, dict[str, dict[str, object]]] = {label: {} for label, _ in panel}
    calculator_versions: dict[str, str] = {}
    t_run0 = time.perf_counter()
    n_ok = n_failed = 0

    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for label, formula in panel:
            a0, a0_provenance = resolve_a0(a0_report, label, model_id, formula)
            log.info("%s (a0=%.4f A) x %s", formula, a0, model_id)
            t_cell = time.perf_counter()
            try:
                initial, final, hop_distance = build_cation_vacancy_hop(
                    formula,
                    "rocksalt",
                    lattice_constant=a0,
                    supercell=args.supercell,
                )
                result = compute_migration_barrier(
                    calculator,
                    initial,
                    final,
                    n_images=args.n_images,
                    fmax=args.fmax,
                    max_steps=args.max_steps,
                    climb=True,
                )
            except StaticsError as exc:
                wall = time.perf_counter() - t_cell
                log.info("  MEASUREMENT FAILED after %.1f s: %s", wall, exc)
                cells[label][model_id] = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "a0_angstrom": a0,
                    "a0_provenance": a0_provenance,
                    "wall_time_seconds": wall,
                }
                n_failed += 1
                continue
            wall = time.perf_counter() - t_cell
            log.info(
                "  E_m = %.3f eV fwd / %.3f eV bwd (asym %.4f, saddle img %d, "
                "%d NEB steps, %.1f s)",
                result.forward_barrier_ev,
                result.backward_barrier_ev,
                result.barrier_asymmetry_ev,
                result.saddle_image_index,
                result.n_neb_steps,
                wall,
            )
            cells[label][model_id] = {
                "forward_barrier_ev": result.forward_barrier_ev,
                "backward_barrier_ev": result.backward_barrier_ev,
                "barrier_asymmetry_ev": result.barrier_asymmetry_ev,
                "e_initial_ev": result.e_initial_ev,
                "e_final_ev": result.e_final_ev,
                "e_saddle_ev": result.e_saddle_ev,
                "saddle_image_index": result.saddle_image_index,
                "band_energies_ev": list(result.band_energies_ev),
                "hop_distance_angstrom": result.hop_distance_angstrom,
                "unrelaxed_hop_distance_angstrom": hop_distance,
                "a0_angstrom": a0,
                "a0_provenance": a0_provenance,
                "n_atoms": result.n_atoms,
                "interpolation_method": result.interpolation_method,
                "n_relax_steps_initial": result.n_relax_steps_initial,
                "n_relax_steps_final": result.n_relax_steps_final,
                "n_neb_steps": result.n_neb_steps,
                "n_pre_climb_steps": result.n_pre_climb_steps,
                "n_force_calls": result.n_force_calls,
                "wall_time_seconds": wall,
            }
            n_ok += 1
        del calculator  # release GPU memory before the next model loads

    compounds = {
        label: summarize_compound(
            formula,
            cells[label],
            targets.get(formula) if targets else None,
        )
        for label, formula in panel
        if cells[label]
    }
    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "models": models,
        "calculator_versions": calculator_versions,
        "parameters": {
            "structure_type": "rocksalt",
            "observable": "cation_vacancy_migration_barrier (CI-NEB, <110> hop)",
            "supercell": args.supercell,
            "n_images": args.n_images,
            "climb": True,
            "neb_method": "improvedtangent",
            "interpolation": "idpp (linear fallback)",
            "optimizer": "FIRE",
            "fmax_ev_per_angstrom": args.fmax,
            "max_steps": args.max_steps,
        },
        "provenance": [
            (
                f"Relaxed a0 per (compound, model) reused from "
                f"{a0_report_path.as_posix()} "
                f"(subjects[*].per_model[*].properties.a0, generated_at "
                f"{a0_report.get('generated_at')}); per-cell provenance recorded."
                if a0_report is not None
                else f"a0 report {a0_report_path.as_posix()} not found; all a0 "
                f"from the covalent-radius estimate (estimate_lattice_constant)."
            ),
            (
                f"Kinetics references loaded from {targets_path.as_posix()}."
                if targets is not None
                else f"No kinetics references file at {targets_path.as_posix()}; "
                f"panel ran without reference comparison."
            ),
            "Dispersion metric: (max - min) / |median| across models on the "
            "FORWARD barrier (lupine_distill.statics.gates.relative_dispersion).",
            "Endpoints from lupine_distill.statics.build_cation_vacancy_hop "
            "(deterministic first-cation vacancy, nearest <110> cation hopper); "
            "band from compute_migration_barrier (both endpoints relaxed, IDPP "
            "interpolation, two-stage climbing-image NEB, improved tangent).",
        ],
        "cells": cells,
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
