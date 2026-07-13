"""Discovery-gates demo runner: reference-free gates on a real Li-S case.

Two subjects: (A) Li2S antifluorite — known-good (cubic, mp-1153-like,
a0 ~ 5.7 A) — and (B) rocksalt LiS — a speculative, unproven 1:1
composition. For each subject x model the script relaxes the lattice,
measures B0 (BM3 EOS) and the cubic elastic constants C11/C12/C44
(stress-strain, relaxed-ion), then applies the reference-free gates:

* per-model Born mechanical stability (exact physics),
* cross-model concordance on a0/B0/C11/C12/C44 with flag/refuse thresholds
  derived from OUR measured Y-matrix cross-model B0 dispersion baseline
  (p75/p95 of data/y_matrix_runs/bound — data-derived, provenance-noted),
* dynamic-return (rattle + FIRE, basin-return proxy; documented limits)
  with one designated model on a 2x2x2 supercell.

Thermodynamic (hull-level) gates are OUT OF SCOPE here and the report says
so: rocksalt LiS may well be mechanically stable — its instability is
expected to be thermodynamic, which needs the formation-energy lane.

Outputs: data/discovery_gates/report.json + REPORT.md (verdict tables,
per-gate wall times, threshold provenance).

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_discovery_gates.py \
        --device cuda
"""

from __future__ import annotations

# Dynamo OFF before any torch import: inductor needs Triton (absent on
# Windows) and eager is fine for the small statics cells. CLI only, never in
# library code (same pattern as run_y_matrix_statics.py).
import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parents[1]), str(_HERE.parents[2])):  # python/ ; repo root
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from lupine_distill.statics import (  # noqa: E402
    ConcordanceThresholds,
    StaticsError,
    born_stability_cubic,
    build_structure,
    compute_cubic_elastic_constants,
    compute_eos,
    compute_lattice,
    concordance,
    derive_concordance_thresholds,
    dispersions_by_material,
    dynamic_return,
    load_property_by_material,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("discovery_gates")

REPORT_SCHEMA = "lupine.discovery_gates.v1"
CONCORDANCE_PROPERTIES = ("a0", "b0", "c11", "c12", "c44")


@dataclass(frozen=True)
class Subject:
    label: str
    formula: str
    structure_type: str
    role: str


SUBJECTS: tuple[Subject, ...] = (
    Subject(
        label="Li2S_antifluorite",
        formula="Li2S",
        structure_type="antifluorite",
        role="known-good reference subject (cubic antifluorite, mp-1153-like)",
    ),
    Subject(
        label="LiS_rocksalt",
        formula="LiS",
        structure_type="rocksalt",
        role="speculative subject: unproven 1:1 Li-S composition",
    ),
)

DEFAULT_MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")
DEFAULT_DYNAMIC_MODEL = "mace-mp-medium"


# --------------------------------------------------------------------------
# model registry (mirrors run_y_matrix_statics.py; unknown ids fail fast)
# --------------------------------------------------------------------------


def _disable_dynamo() -> None:
    import torch._dynamo

    torch._dynamo.config.suppress_errors = True
    torch._dynamo.config.disable = True


def _make_mace(size: str) -> Callable[[str], tuple[object, str]]:
    def factory(device: str) -> tuple[object, str]:
        _disable_dynamo()
        import mace
        from mace.calculators import mace_mp

        calculator = mace_mp(model=size, device=device, default_dtype="float64")
        return calculator, f"mace-torch {getattr(mace, '__version__', '?')}"

    return factory


def _make_chgnet(device: str) -> tuple[object, str]:
    _disable_dynamo()
    import chgnet
    from chgnet.model.dynamics import CHGNetCalculator

    calculator = CHGNetCalculator(use_device=device)
    return calculator, f"chgnet {getattr(chgnet, '__version__', '?')}"


MODEL_REGISTRY: dict[str, Callable[[str], tuple[object, str]]] = {
    "mace-mp-small": _make_mace("small"),
    "mace-mp-medium": _make_mace("medium"),
    "mace-mpa-0-medium": _make_mace("medium-mpa-0"),
    "chgnet": _make_chgnet,
}


def build_calculator(model_id: str, device: str) -> tuple[object, str]:
    if model_id not in MODEL_REGISTRY:
        raise SystemExit(
            f"unknown model id {model_id!r}; known: {', '.join(sorted(MODEL_REGISTRY))}"
        )
    if device == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise SystemExit("--device cuda requested but CUDA is not available")
    return MODEL_REGISTRY[model_id](device)


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
        "--dynamic-model",
        default=DEFAULT_DYNAMIC_MODEL,
        help="Model used for the dynamic-return gate (must be in --models)",
    )
    parser.add_argument(
        "--bound-dir",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "bound"),
        help="Calc-evidence directory for the B0 dispersion baseline",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "discovery_gates"),
        help="Output directory for report.json / REPORT.md",
    )
    parser.add_argument("--delta", type=float, default=0.5e-2, help="Elastic FD strain")
    parser.add_argument("--rattle", type=float, default=0.05, help="Rattle stdev (A)")
    parser.add_argument("--seed", type=int, default=42, help="Rattle seed")
    parser.add_argument(
        "--dynamic-supercell", type=int, default=2, help="Supercell repeat for rattle"
    )
    return parser.parse_args(argv)


# --------------------------------------------------------------------------
# measurement per (subject, model)
# --------------------------------------------------------------------------


def measure_subject(
    calculator: object, subject: Subject, delta: float
) -> dict[str, object]:
    """Lattice + EOS(B0) + cubic elastic constants for one subject/model."""
    lattice = compute_lattice(calculator, subject.formula, subject.structure_type)
    log.info(
        "  a0 = %.4f A (%.1fs)", lattice.a0_angstrom, lattice.wall_time_seconds
    )
    eos = compute_eos(
        calculator, subject.formula, subject.structure_type, lattice.a0_angstrom
    )
    log.info("  B0 = %.1f GPa (%.1fs)", eos.b0_gpa, eos.wall_time_seconds)
    elastic = compute_cubic_elastic_constants(
        calculator,
        subject.formula,
        subject.structure_type,
        lattice.a0_angstrom,
        delta=delta,
        relax_internal=True,
    )
    log.info(
        "  C11 = %.1f, C12 = %.1f, C44 = %.1f GPa (%.1fs)",
        elastic.c11_gpa,
        elastic.c12_gpa,
        elastic.c44_gpa,
        elastic.wall_time_seconds,
    )
    born = born_stability_cubic(elastic.c11_gpa, elastic.c12_gpa, elastic.c44_gpa)
    log.info("  Born: %s", "PASS" if born.passed else f"FAIL ({born.detail})")
    b0_cross_check = abs(
        elastic.bulk_modulus_from_cij_gpa - eos.b0_gpa
    ) / abs(eos.b0_gpa)
    return {
        "properties": {
            "a0": lattice.a0_angstrom,
            "b0": eos.b0_gpa,
            "c11": elastic.c11_gpa,
            "c12": elastic.c12_gpa,
            "c44": elastic.c44_gpa,
        },
        "b0_from_cij_gpa": elastic.bulk_modulus_from_cij_gpa,
        "b0_elastic_vs_eos_rel_diff": b0_cross_check,
        "blocks": {
            "lattice": lattice.to_dict(),
            "eos": eos.to_dict(),
            "elastic": elastic.to_dict(),
        },
        "gates": {"born": born.to_dict()},
        "born_passed": born.passed,
        "wall_time_seconds": {
            "lattice": lattice.wall_time_seconds,
            "eos": eos.wall_time_seconds,
            "elastic_plus_born": elastic.wall_time_seconds + born.wall_time_seconds,
        },
    }


def overall_verdict(subject_report: dict[str, object]) -> str:
    """REFUSED / FLAGGED / CERTIFIED from the recorded gate outcomes.

    REFUSED: any measurement failure, any per-model Born failure, any
    concordance refusal, or a failed dynamic return. FLAGGED: no refusal but
    at least one concordance flag. CERTIFIED otherwise.
    """
    per_model = subject_report["per_model"]
    failures = [m for m, r in per_model.items() if "error" in r]
    born_fails = [
        m for m, r in per_model.items() if "error" not in r and not r["born_passed"]
    ]
    concordance_levels = {
        prop: gate["values"]["level"]
        for prop, gate in subject_report["gates"]["concordance"].items()
    }
    refusals = [p for p, level in concordance_levels.items() if level == "refuse"]
    flags = [p for p, level in concordance_levels.items() if level == "flag"]
    dynamic = subject_report["gates"].get("dynamic_return")
    dynamic_failed = dynamic is not None and not dynamic["passed"]
    if failures or born_fails or refusals or dynamic_failed:
        return "REFUSED"
    if flags:
        return "FLAGGED"
    return "CERTIFIED"


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------


def _verdict_word(gate: dict[str, object]) -> str:
    if gate["gate"] == "concordance":
        return str(gate["values"]["level"]).upper()
    return "PASS" if gate["passed"] else "FAIL"


def render_markdown(report: dict[str, object]) -> str:
    thresholds = report["concordance_thresholds"]
    lines: list[str] = [
        "# Discovery gates - reference-free verdicts on a real Li-S case",
        "",
        f"Generated: {report['generated_at']} | device: {report['device']} | "
        f"models: {', '.join(report['models'])}",
        "",
        "Two subjects: **Li2S antifluorite** (known-good) and **LiS rocksalt** "
        "(speculative 1:1 composition). All gates are reference-free: no "
        "experimental or DFT value for either subject is consulted.",
        "",
        "## Concordance thresholds (data-derived, not invented)",
        "",
        f"- metric: `(max - min) / |median|` across models, per property",
        f"- flag at >= **{thresholds['flag']:.4f}** "
        f"(p{thresholds['flag_percentile']:g}), refuse at >= "
        f"**{thresholds['refuse']:.4f}** (p{thresholds['refuse_percentile']:g})",
        f"- derivation: {thresholds['source']}",
        f"- baseline samples: {thresholds['n_samples']} materials; "
        "per-material dispersions recorded in report.json",
        "",
        report["threshold_transfer_note"],
        "",
    ]
    for subject_label, sub in report["subjects"].items():
        lines += [
            f"## {subject_label} - **{sub['overall_verdict']}**",
            "",
            f"{sub['role']}",
            "",
            "| model | a0 (A) | B0 EOS (GPa) | C11 | C12 | C44 (GPa) | "
            "B0 Cij vs EOS | Born | wall (s) |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for model, r in sub["per_model"].items():
            if "error" in r:
                lines.append(f"| {model} | - | - | - | - | - | - | ERROR | - |")
                continue
            p = r["properties"]
            walls = r["wall_time_seconds"]
            total = sum(walls.values())
            lines.append(
                f"| {model} | {p['a0']:.4f} | {p['b0']:.1f} | {p['c11']:.1f} | "
                f"{p['c12']:.1f} | {p['c44']:.1f} | "
                f"{r['b0_elastic_vs_eos_rel_diff'] * 100:.1f}% | "
                f"{'PASS' if r['born_passed'] else 'FAIL'} | {total:.1f} |"
            )
        lines += ["", "| gate | verdict | key numbers | wall (s) |", "|---|---|---|---|"]
        for model, r in sub["per_model"].items():
            if "error" in r:
                lines.append(
                    f"| born ({model}) | ERROR | measurement failed: "
                    f"{r['error'][:120]} | - |"
                )
                continue
            born = r["gates"]["born"]
            v = born["values"]
            lines.append(
                f"| born ({model}) | {_verdict_word(born)} | "
                f"C11-C12={v['c11_minus_c12_gpa']:.1f}, "
                f"C11+2C12={v['c11_plus_2c12_gpa']:.1f}, C44={v['c44_gpa']:.1f} GPa "
                f"| {r['wall_time_seconds']['elastic_plus_born']:.1f} |"
            )
        for prop, gate in sub["gates"]["concordance"].items():
            lines.append(
                f"| concordance ({prop}) | {_verdict_word(gate)} | "
                f"dispersion={gate['values']['dispersion']:.3f} | "
                f"{gate['wall_time_seconds']:.3f} |"
            )
        dynamic = sub["gates"].get("dynamic_return")
        if dynamic is not None:
            dv = dynamic["values"]
            key = (
                f"dE={dv.get('energy_delta_ev_per_atom', float('nan')):.2e} eV/atom, "
                f"max disp={dv.get('max_displacement_a', float('nan')):.3f} A, "
                f"{dv.get('n_relax_steps', '?')} steps, {dv['n_atoms']} atoms "
                f"({report['dynamic_model']})"
            )
            lines.append(
                f"| dynamic_return | {_verdict_word(dynamic)} | {key} | "
                f"{dynamic['wall_time_seconds']:.1f} |"
            )
        lines += ["", f"Subject wall time: **{sub['wall_time_seconds']:.1f} s**", ""]
    lines += [
        "## Scope and honesty notes",
        "",
    ] + [f"- {note}" for note in report["notes"]] + [""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must name at least one model")
    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model id(s): {unknown}")
    if args.dynamic_model not in models:
        raise SystemExit(
            f"--dynamic-model {args.dynamic_model!r} must be one of --models {models}"
        )
    if args.dynamic_supercell < 1:
        raise SystemExit("--dynamic-supercell must be >= 1")

    # 1. Data-derived concordance thresholds from the bound Y-matrix baseline.
    bound_dir = Path(args.bound_dir)
    b0_by_material = load_property_by_material(bound_dir, property_name="B0")
    baseline_dispersions = dispersions_by_material(b0_by_material)
    thresholds: ConcordanceThresholds = derive_concordance_thresholds(
        baseline_dispersions,
        source=(
            f"p75/p95 of the per-material cross-model relative dispersion "
            f"(max-min)/|median| of B0 over {len(b0_by_material)} Y-matrix "
            f"materials x {len(models)} models in {bound_dir.as_posix()} "
            f"(schema lupine.mlip.calc_evidence.v1)"
        ),
    )
    log.info(
        "concordance thresholds from %d baseline materials: flag >= %.4f (p75), "
        "refuse >= %.4f (p95)",
        thresholds.n_samples,
        thresholds.flag,
        thresholds.refuse,
    )

    # 2. Measurements, model-outer so each calculator loads exactly once.
    per_subject: dict[str, dict[str, object]] = {
        s.label: {
            "role": s.role,
            "formula": s.formula,
            "structure_type": s.structure_type,
            "per_model": {},
            "gates": {},
        }
        for s in SUBJECTS
    }
    calculator_versions: dict[str, str] = {}
    dynamic_gates: dict[str, dict[str, object]] = {}
    t_run0 = time.perf_counter()
    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for subject in SUBJECTS:
            log.info("%s x %s", subject.label, model_id)
            try:
                record = measure_subject(calculator, subject, args.delta)
            except StaticsError as exc:
                log.info("  MEASUREMENT FAILED: %s", exc)
                record = {"error": f"{type(exc).__name__}: {exc}"}
            per_subject[subject.label]["per_model"][model_id] = record
            if model_id == args.dynamic_model and "error" not in record:
                a0 = record["properties"]["a0"]
                n = args.dynamic_supercell
                supercell = build_structure(
                    subject.formula, subject.structure_type, a0
                ).repeat((n, n, n))
                log.info(
                    "  dynamic_return: rattle %.3f A, seed %d, %d atoms ...",
                    args.rattle,
                    args.seed,
                    len(supercell),
                )
                verdict = dynamic_return(
                    calculator,
                    supercell,
                    rattle_amplitude=args.rattle,
                    seed=args.seed,
                )
                log.info(
                    "  dynamic_return: %s (%.1fs)",
                    "PASS" if verdict.passed else "FAIL",
                    verdict.wall_time_seconds,
                )
                dynamic_gates[subject.label] = verdict.to_dict()
        del calculator  # release GPU memory before the next model loads

    # 3. Cross-model concordance per subject.
    for subject in SUBJECTS:
        sub = per_subject[subject.label]
        ok_models = {
            m: r for m, r in sub["per_model"].items() if "error" not in r
        }
        concordance_gates: dict[str, dict[str, object]] = {}
        if len(ok_models) >= 2:
            for prop in CONCORDANCE_PROPERTIES:
                values_by_model = {
                    m: r["properties"][prop] for m, r in ok_models.items()
                }
                concordance_gates[prop] = concordance(
                    prop, values_by_model, thresholds
                ).to_dict()
        sub["gates"]["concordance"] = concordance_gates
        if subject.label in dynamic_gates:
            sub["gates"]["dynamic_return"] = dynamic_gates[subject.label]
        sub["wall_time_seconds"] = sum(
            sum(r["wall_time_seconds"].values())
            for r in ok_models.values()
        ) + sub["gates"].get("dynamic_return", {}).get("wall_time_seconds", 0.0)
        sub["overall_verdict"] = overall_verdict(sub)
        log.info("%s -> %s", subject.label, sub["overall_verdict"])

    notes = [
        "Born stability is exact physics (necessary conditions only); "
        "concordance thresholds are percentiles of our own measured baseline; "
        "no threshold in this report was invented.",
        "Threshold transfer: the p75/p95 baseline is measured on B0 "
        "dispersions and applied to a0/B0/C11/C12/C44 alike. a0 disperses "
        "less than B0 (lenient there); shear constants typically disperse "
        "more (strict there). This is a documented proxy, not a per-property "
        "calibration.",
        "The dynamic-return gate is a finite-rattle basin-return probe, NOT "
        "a phonon calculation; instabilities incommensurate with the "
        f"{args.dynamic_supercell}x{args.dynamic_supercell}x"
        f"{args.dynamic_supercell} supercell are invisible to it.",
        "Thermodynamic (hull-level) gates are OUT OF SCOPE in this run: "
        "rocksalt LiS may be mechanically stable while remaining "
        "thermodynamically unstable against decomposition (e.g. to Li2S + S); "
        "deciding that requires the formation-energy lane.",
        "Cubic symmetry of each relaxed subject is assumed by construction "
        "(both prototypes are cubic); the elastic probe measures the cubic "
        "C11/C12/C44 only.",
    ]

    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": args.device,
        "models": models,
        "dynamic_model": args.dynamic_model,
        "calculator_versions": calculator_versions,
        "parameters": {
            "elastic_delta": args.delta,
            "elastic_relax_internal": True,
            "rattle_amplitude_a": args.rattle,
            "rattle_seed": args.seed,
            "dynamic_supercell": args.dynamic_supercell,
        },
        "concordance_thresholds": thresholds.to_dict(),
        "threshold_transfer_note": notes[1],
        "subjects": per_subject,
        "notes": notes,
        "total_wall_time_seconds": time.perf_counter() - t_run0,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "report.json"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md = out_dir / "REPORT.md"
    report_md.write_text(render_markdown(report), encoding="utf-8")
    log.info("report -> %s ; %s", report_json, report_md)
    log.info("total wall time: %.1f s", report["total_wall_time_seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
