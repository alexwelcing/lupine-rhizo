"""Per-property dispersion baseline: a0/B0/C11/C12/C44 over the Y-matrix set.

The 2026-07-02 discovery-gates run falsely REFUSED its known-good subject
(Li2S antifluorite) because flag/refuse thresholds measured on B0 dispersions
were transferred unchanged to C11/C44, which physically disperse more across
models. This runner measures the missing per-property baseline: for each
Y-matrix bound material x model it records relaxed a0, B0 (BM3 EOS), and the
cubic C11/C12/C44 with the SAME probe the discovery gates use
(``measure_subject`` from run_discovery_gates: elastic_delta, relaxed-ion,
Born check), then derives per-property flag/refuse percentiles and writes
``thresholds.v2.json`` with full provenance.

Outputs:
* one ``lupine.mlip.calc_evidence.v1`` JSON per (material, model) cell in
  --out-dir (readable by ``lupine_distill.statics.load_property_by_material``),
* ``baseline_summary.json`` (wall times, errors, parameters) in --out-dir,
* ``thresholds.v2.json`` (per-property thresholds + caveats) at
  --thresholds-out, when every property has enough samples.

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_elastic_baseline.py \
        --device cuda
Smoke (one material, all models):
    ... run_elastic_baseline.py --device cuda --materials Ni
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
    Subject,
    build_calculator,
    measure_subject,
)

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import PropertyValue  # noqa: E402
from lupine_distill.statics import (  # noqa: E402
    InputValidationError,
    StaticsError,
    derive_per_property_thresholds,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("elastic_baseline")

THRESHOLDS_SCHEMA = "lupine.discovery_gates.thresholds.v2"

#: The 21 Y-matrix bound materials (matches data/y_matrix_runs/bound/).
BASELINE_MATERIALS: tuple[tuple[str, str], ...] = (
    ("Ag", "fcc"),
    ("Al", "fcc"),
    ("Au", "fcc"),
    ("Ca", "fcc"),
    ("Cr", "bcc"),
    ("Cu", "fcc"),
    ("Fe", "bcc"),
    ("MgO", "rocksalt"),
    ("Mo", "bcc"),
    ("NaCl", "rocksalt"),
    ("Nb", "bcc"),
    ("Ni", "fcc"),
    ("Ni3Al", "l12"),
    ("NiAl", "b2"),
    ("Pd", "fcc"),
    ("Pt", "fcc"),
    ("Si", "diamond"),
    ("Sr", "fcc"),
    ("Ta", "bcc"),
    ("V", "bcc"),
    ("W", "bcc"),
)

#: Honesty notes carried verbatim into thresholds.v2.json.
THRESHOLD_NOTES: tuple[str, ...] = (
    "Per-property calibration: each of a0/B0/C11/C12/C44 gets flag/refuse "
    "percentiles from its OWN measured cross-model dispersion distribution, "
    "replacing the v1 B0-proxy transfer. This fixes the transfer error; it "
    "does not decouple the elastic family (Cauchy relation / stability keep "
    "C11/C12/C44 internally coupled).",
    "Order-statistic uncertainty: with n~21 materials the p95 threshold "
    "interpolates the top one-to-two order statistics and is fragile to "
    "single-material composition changes; treat refuse thresholds as "
    "descriptive calibration, not sharp decision boundaries.",
    "Class composition: the baseline is metal-dominated (9 fcc + 7 bcc "
    "metals, 1 diamond, 2 rocksalts, 2 intermetallics). Known-good ionic "
    "compounds have shown C11/C44 dispersions above metal-derived "
    "percentiles (2026-07-13 halide panel); per-class calibration is future "
    "work, and per-class behaviour should be reported alongside any verdict.",
    "Model non-independence: mace-mp-small and mace-mp-medium share "
    "architecture and training data, so the effective number of independent "
    "models is below the nominal count; dispersions are ensemble spread, "
    "not independent-error spread.",
    "Same-instrument guarantee: baseline cells are measured by "
    "run_discovery_gates.measure_subject (same lattice relax, BM3 EOS, "
    "relaxed-ion stress-strain elastic probe, same elastic_delta), so "
    "thresholds are calibrated on the identical probe that gates subjects.",
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
        "--materials",
        default="",
        help=(
            "Comma-separated formulas to run (default: all "
            f"{len(BASELINE_MATERIALS)} Y-matrix bound materials); "
            "e.g. --materials Ni for a smoke run"
        ),
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "elastic_baseline"),
        help="Calc-evidence output directory",
    )
    parser.add_argument(
        "--thresholds-out",
        default=str(_REPO_ROOT / "data" / "discovery_gates" / "thresholds.v2.json"),
        help="Per-property thresholds artifact path",
    )
    parser.add_argument("--delta", type=float, default=0.5e-2, help="Elastic FD strain")
    parser.add_argument("--run-label", default=None, help="Optional evidence run label")
    return parser.parse_args(argv)


def select_materials(csv: str) -> tuple[tuple[str, str], ...]:
    if not csv.strip():
        return BASELINE_MATERIALS
    wanted = [m.strip() for m in csv.split(",") if m.strip()]
    by_formula = {formula: (formula, structure) for formula, structure in BASELINE_MATERIALS}
    unknown = [m for m in wanted if m not in by_formula]
    if unknown:
        raise SystemExit(
            f"unknown material(s) {unknown}; known: "
            f"{', '.join(f for f, _ in BASELINE_MATERIALS)}"
        )
    return tuple(by_formula[m] for m in wanted)


def evidence_from_record(
    *,
    formula: str,
    structure_type: str,
    model_id: str,
    device: str,
    delta: float,
    calculator_version: str,
    record: dict[str, object],
    run_label: str | None,
) -> dict[str, object]:
    """calc_evidence.v1 payload from one measure_subject record."""
    props = record["properties"]
    blocks = record["blocks"]
    properties = [
        PropertyValue(name="a0", value=props["a0"], unit="Angstrom"),
        PropertyValue(name="B0", value=props["b0"], unit="GPa"),
        PropertyValue(name="C11", value=props["c11"], unit="GPa"),
        PropertyValue(name="C12", value=props["c12"], unit="GPa"),
        PropertyValue(name="C44", value=props["c44"], unit="GPa"),
        PropertyValue(
            name="B0_from_Cij", value=record["b0_from_cij_gpa"], unit="GPa"
        ),
    ]
    inputs = {
        "material": formula,
        "structure_type": structure_type,
        "model_id": model_id,
        "device": device,
        "elastic_delta": delta,
        "elastic_relax_internal": True,
        "properties": {
            name: blocks[name]["canonical_inputs"] for name in ("lattice", "eos", "elastic")
        },
    }
    evidence = build_calc_evidence(
        material=formula,
        model_id=model_id,
        backend="ase",
        device=device,
        calculator_version=calculator_version,
        inputs=inputs,
        properties=properties,
        run_label=run_label,
        computed_at=datetime.now(timezone.utc),
    )
    return evidence.model_dump(mode="json", by_alias=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must name at least one model")
    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model id(s): {unknown}")
    materials = select_materials(args.materials)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cells: dict[str, dict[str, object]] = {}
    calculator_versions: dict[str, str] = {}
    t_run0 = time.perf_counter()
    n_ok = n_failed = 0
    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for formula, structure_type in materials:
            label = f"{formula}_{structure_type}"
            log.info("%s x %s", label, model_id)
            subject = Subject(
                label=label,
                formula=formula,
                structure_type=structure_type,
                role="per-property dispersion baseline material",
            )
            t_cell = time.perf_counter()
            try:
                record = measure_subject(calculator, subject, args.delta)
            except StaticsError as exc:
                log.info("  MEASUREMENT FAILED: %s", exc)
                cells[f"{label}_{model_id}"] = {
                    "error": f"{type(exc).__name__}: {exc}",
                    "wall_time_seconds": time.perf_counter() - t_cell,
                }
                n_failed += 1
                continue
            payload = evidence_from_record(
                formula=formula,
                structure_type=structure_type,
                model_id=model_id,
                device=args.device,
                delta=args.delta,
                calculator_version=version,
                record=record,
                run_label=args.run_label,
            )
            evidence_path = out_dir / f"{label}_{model_id}.evidence.json"
            evidence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            cells[f"{label}_{model_id}"] = {
                "properties": record["properties"],
                "b0_elastic_vs_eos_rel_diff": record["b0_elastic_vs_eos_rel_diff"],
                "born_passed": record["born_passed"],
                "wall_time_seconds": time.perf_counter() - t_cell,
            }
            n_ok += 1
        del calculator  # release GPU memory before the next model loads

    summary = {
        "schema": "lupine.elastic_baseline_summary.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "models": models,
        "calculator_versions": calculator_versions,
        "materials": [f"{f}_{s}" for f, s in materials],
        "parameters": {"elastic_delta": args.delta, "elastic_relax_internal": True},
        "n_cells_ok": n_ok,
        "n_cells_failed": n_failed,
        "cells": cells,
        "total_wall_time_seconds": time.perf_counter() - t_run0,
    }
    summary_path = out_dir / "baseline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info(
        "baseline: %d ok / %d failed cells in %.1f s -> %s",
        n_ok,
        n_failed,
        summary["total_wall_time_seconds"],
        out_dir,
    )

    # Thresholds only when the panel is large enough to calibrate from.
    if len(materials) < 5:
        log.info(
            "thresholds NOT derived: %d material(s) < 5 required samples "
            "(smoke run?)",
            len(materials),
        )
        return 0
    try:
        per_property = derive_per_property_thresholds(out_dir)
    except InputValidationError as exc:
        log.info("thresholds NOT derived: %s", exc)
        return 1
    artifact = {
        "schema": THRESHOLDS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_dir": out_dir.as_posix(),
        "device": args.device,
        "models": models,
        "calculator_versions": calculator_versions,
        "materials": [f"{f}_{s}" for f, s in materials],
        "parameters": {"elastic_delta": args.delta, "elastic_relax_internal": True},
        "per_property": {prop: t.to_dict() for prop, t in per_property.items()},
        "notes": list(THRESHOLD_NOTES),
    }
    thresholds_path = Path(args.thresholds_out)
    thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    thresholds_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    for prop, t in per_property.items():
        log.info(
            "thresholds.v2 %s: flag >= %.4f (p75), refuse >= %.4f (p95), n=%d",
            prop,
            t.flag,
            t.refuse,
            t.n_samples,
        )
    log.info("thresholds -> %s", thresholds_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
