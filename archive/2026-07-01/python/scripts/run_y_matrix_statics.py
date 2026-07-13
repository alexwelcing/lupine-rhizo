"""Y-matrix Tier-1 statics runner: one (material, model) cell -> statics JSON.

Runs the calculator-agnostic statics core (lattice/EOS/vacancy/surfaces/SFE/
formation enthalpy) with a real MLIP calculator and writes per-property
results — value, unit, convergence parameters, wall time, and canonical
inputs — to ``--out``. Optionally emits a ``lupine.mlip.calc_evidence.v1``
payload via ``--evidence-out`` (reference values are compiled separately and
are intentionally absent here).

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_y_matrix_statics.py \
        --material Ni --structure fcc --model mace-mp-small --device cuda \
        --properties lattice,eos,vacancy --out out.json
"""

from __future__ import annotations

# Dynamo OFF before any torch import: inductor needs Triton (absent on
# Windows) and eager is fine for the small statics cells. Same pattern as
# python/scripts/run_ni_gpu_loop.py — CLI only, never in library code.
import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parents[1]), str(_HERE.parents[2])):  # python/ ; repo root
    if _p not in sys.path:
        sys.path.insert(0, _p)

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import PropertyValue  # noqa: E402
from lupine_distill.statics import (  # noqa: E402
    SUPPORTED_STRUCTURE_TYPES,
    SUPPORTED_SURFACES,
    compute_eos,
    compute_formation_enthalpy,
    compute_lattice,
    compute_stacking_fault_energy,
    compute_surface_energies,
    compute_vacancy_formation,
    parse_formula,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("y_matrix_statics")

RUN_SCHEMA = "lupine.statics_run.v1"
KNOWN_PROPERTIES = ("lattice", "eos", "vacancy", "surfaces", "sfe", "formation")
_A0_DEPENDENT = frozenset({"eos", "vacancy", "surfaces", "sfe"})


# --------------------------------------------------------------------------
# model registry — calculators are instantiated HERE and only here.
# Friendly ids map explicitly; unknown ids fail fast (never substitute).
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
    "mace-mpa-0-medium": _make_mace("medium-mpa-0"),  # OMat24-lineage; R2-H1 softening test
    "chgnet": _make_chgnet,
}


def build_calculator(model_id: str, device: str) -> tuple[object, str]:
    """Instantiate the calculator for a friendly model id; fail fast otherwise."""
    if model_id not in MODEL_REGISTRY:
        raise SystemExit(
            f"unknown model id {model_id!r}; known ids: {', '.join(sorted(MODEL_REGISTRY))}. "
            f"Refusing to substitute a different model."
        )
    if device == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise SystemExit("--device cuda requested but CUDA is not available")
    return MODEL_REGISTRY[model_id](device)


# --------------------------------------------------------------------------
# argument parsing and compatibility checks
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--material", required=True, help="Formula, e.g. Ni or NiAl")
    parser.add_argument(
        "--structure", required=True, choices=sorted(SUPPORTED_STRUCTURE_TYPES)
    )
    parser.add_argument("--model", required=True, choices=sorted(MODEL_REGISTRY))
    parser.add_argument("--device", required=True, choices=("cuda", "cpu"))
    parser.add_argument(
        "--properties",
        required=True,
        help=f"Comma-separated subset of: {','.join(KNOWN_PROPERTIES)}",
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--evidence-out",
        default=None,
        help="Optional path for a lupine.mlip.calc_evidence.v1 payload "
        "(properties are emitted WITHOUT reference values)",
    )
    parser.add_argument("--run-label", default=None, help="Optional evidence run label")
    return parser.parse_args(argv)


def validate_request(material: str, structure: str, properties: list[str]) -> None:
    """Fail fast on property/material/structure incompatibilities."""
    unknown = [p for p in properties if p not in KNOWN_PROPERTIES]
    if unknown:
        raise SystemExit(
            f"unknown properties {unknown}; known: {', '.join(KNOWN_PROPERTIES)}"
        )
    counts = parse_formula(material)
    is_element = len(counts) == 1 and next(iter(counts.values())) == 1
    if "surfaces" in properties:
        if not is_element or structure not in SUPPORTED_SURFACES:
            raise SystemExit(
                f"surfaces requires an elemental material in {sorted(SUPPORTED_SURFACES)}, "
                f"got {material!r} ({structure})"
            )
    if "sfe" in properties and (not is_element or structure != "fcc"):
        raise SystemExit(f"sfe requires an elemental fcc material, got {material!r} ({structure})")
    if "formation" in properties and is_element:
        raise SystemExit(f"formation requires a compound formula, got {material!r}")


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------


def _block(result: object, value: float, unit: str) -> dict[str, object]:
    return {"value": value, "unit": unit, **result.to_dict()}  # type: ignore[attr-defined]


def run_properties(
    calculator: object, material: str, structure: str, requested: list[str]
) -> dict[str, object]:
    """Run the requested properties in canonical order; returns result blocks.

    ``lattice`` is computed automatically (and reported) whenever a requested
    property needs the relaxed lattice constant.
    """
    results: dict[str, object] = {}
    need_lattice = "lattice" in requested or bool(_A0_DEPENDENT & set(requested))
    a0: float | None = None
    if need_lattice:
        log.info("computing lattice (%s, %s) ...", material, structure)
        lattice = compute_lattice(calculator, material, structure)
        a0 = lattice.a0_angstrom
        log.info("  a0 = %.4f A in %.1fs", a0, lattice.wall_time_seconds)
        results["lattice"] = _block(lattice, lattice.a0_angstrom, "Angstrom")
    if "eos" in requested:
        log.info("computing eos ...")
        eos = compute_eos(calculator, material, structure, a0)
        log.info("  B0 = %.1f GPa in %.1fs", eos.b0_gpa, eos.wall_time_seconds)
        results["eos"] = _block(eos, eos.b0_gpa, "GPa")
    if "vacancy" in requested:
        log.info("computing vacancy formation ...")
        vac = compute_vacancy_formation(calculator, material, structure, a0)
        log.info(
            "  E_vac = %.3f eV (%d steps) in %.1fs",
            vac.vacancy_formation_ev, vac.n_relax_steps, vac.wall_time_seconds,
        )
        results["vacancy"] = _block(vac, vac.vacancy_formation_ev, "eV")
    if "surfaces" in requested:
        log.info("computing surface energies ...")
        surfaces = compute_surface_energies(calculator, material, structure, a0)
        for s in surfaces:
            log.info("  gamma_%s = %.3f J/m^2 in %.1fs", s.miller, s.gamma_j_per_m2, s.wall_time_seconds)
        results["surfaces"] = [_block(s, s.gamma_j_per_m2, "J/m^2") for s in surfaces]
    if "sfe" in requested:
        log.info("computing stacking fault energy ...")
        sfe = compute_stacking_fault_energy(calculator, material, a0)
        log.info(
            "  SFE = %.1f mJ/m^2 (hcp proxy %.1f) in %.1fs",
            sfe.sfe_mj_per_m2, sfe.hcp_proxy_mj_per_m2, sfe.wall_time_seconds,
        )
        results["sfe"] = _block(sfe, sfe.sfe_mj_per_m2, "mJ/m^2")
    if "formation" in requested:
        log.info("computing formation enthalpy ...")
        formation = compute_formation_enthalpy(calculator, material, structure)
        log.info(
            "  dH_f = %.3f eV/atom in %.1fs",
            formation.formation_enthalpy_ev_per_atom, formation.wall_time_seconds,
        )
        results["formation"] = _block(
            formation, formation.formation_enthalpy_ev_per_atom, "eV/atom"
        )
    return results


def evidence_property_values(results: dict[str, object]) -> list[PropertyValue]:
    """Flatten result blocks into calc-evidence properties (no reference values —
    the reference compilation is a separate, in-flight lane)."""
    values: list[PropertyValue] = []
    if "lattice" in results:
        block = results["lattice"]
        values.append(PropertyValue(name="a0", value=block["value"], unit="Angstrom"))
        values.append(
            PropertyValue(
                name="cohesive_energy",
                value=block["values"]["cohesive_energy_ev_per_atom"],
                unit="eV/atom",
            )
        )
    if "eos" in results:
        block = results["eos"]
        values.append(PropertyValue(name="B0", value=block["value"], unit="GPa"))
        values.append(
            PropertyValue(
                name="B0_prime", value=block["values"]["b0_prime"], unit="dimensionless"
            )
        )
    if "vacancy" in results:
        values.append(
            PropertyValue(
                name="vacancy_formation_energy",
                value=results["vacancy"]["value"],
                unit="eV",
            )
        )
    for block in results.get("surfaces", []):
        values.append(
            PropertyValue(
                name=f"gamma_{block['values']['miller']}", value=block["value"], unit="J/m^2"
            )
        )
    if "sfe" in results:
        values.append(
            PropertyValue(
                name="stacking_fault_energy", value=results["sfe"]["value"], unit="mJ/m^2"
            )
        )
    if "formation" in results:
        values.append(
            PropertyValue(
                name="formation_enthalpy", value=results["formation"]["value"], unit="eV/atom"
            )
        )
    return values


def _canonical_run_inputs(
    material: str, structure: str, model_id: str, device: str, results: dict[str, object]
) -> dict[str, object]:
    per_property: dict[str, object] = {}
    for name, block in results.items():
        if name == "surfaces":
            for surface in block:
                miller = surface["values"]["miller"]
                per_property[f"surface_{miller}"] = surface["canonical_inputs"]
        else:
            per_property[name] = block["canonical_inputs"]
    return {
        "material": material,
        "structure_type": structure,
        "model_id": model_id,
        "device": device,
        "properties": per_property,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    requested = [p.strip() for p in args.properties.split(",") if p.strip()]
    if not requested:
        raise SystemExit("--properties must name at least one property")
    validate_request(args.material, args.structure, requested)

    log.info("loading %s on %s ...", args.model, args.device)
    calculator, calculator_version = build_calculator(args.model, args.device)
    log.info("calculator ready: %s", calculator_version)

    t0 = time.perf_counter()
    results = run_properties(calculator, args.material, args.structure, requested)
    total_wall = time.perf_counter() - t0

    payload = {
        "schema": RUN_SCHEMA,
        "material": args.material,
        "structure_type": args.structure,
        "model_id": args.model,
        "device": args.device,
        "calculator_version": calculator_version,
        "requested_properties": requested,
        "results": results,
        "total_wall_time_seconds": total_wall,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log.info("results -> %s (%.1fs total)", out_path, total_wall)

    if args.evidence_out:
        evidence = build_calc_evidence(
            material=args.material,
            model_id=args.model,
            backend="ase",
            device=args.device,
            calculator_version=calculator_version,
            inputs=_canonical_run_inputs(
                args.material, args.structure, args.model, args.device, results
            ),
            properties=evidence_property_values(results),
            run_label=args.run_label,
            computed_at=datetime.now(timezone.utc),
        )
        evidence_path = Path(args.evidence_out)
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2),
            encoding="utf-8",
        )
        log.info("evidence -> %s", evidence_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
