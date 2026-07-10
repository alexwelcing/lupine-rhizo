"""Bind measured environment-error-field anchors into Lean ``ErrorField`` instances.

For each fcc (material, model) cell of the Y-matrix sweep this binder:

1. reads the model-relaxed statics run (``data/y_matrix_runs/<Mat>_fcc_<model>.json``,
   schema ``lupine.statics_run.v1``): lattice constant ``a0``, per-facet surface
   energies (miller 100/111), and the vacancy formation energy;
2. binds DFT-PBE reference targets from ``data/y_matrix_targets/``
   (``surface_energies.json``, ``vacancy_formation.json``);
3. converts the signed errors into the three per-atom field anchors of the
   climate-series formalization ("A Field, Not a Neural Net"):

       P(8)  = (gamma_100^model - gamma_100^ref) * (a0^2 / 2)       [ (100) facet, eV/atom ]
       P(9)  = (gamma_111^model - gamma_111^ref) * (sqrt(3)/4 a0^2) [ (111) facet, eV/atom ]
       P(11) = (Evac^model - Evac^ref) / 12                          [ vacancy shell, eV/atom ]

   (surface-energy errors in J/m^2 are converted with 1 J/m^2 = 0.06241509074
   eV/A^2; each fcc vacancy creates 12 first-shell atoms at c = 11);
4. checks the anchored-field admissibility predicate **on the integer-scaled
   anchors** (x1e4 eV/atom, exactly the literals emitted into Lean):

       p8 <= p9 <= p11 <= 0    (monotone softening)

   and emits, per cell, either an ``ErrorField 12`` instance via
   ``Theory.AnchoredField.mkAnchoredField`` (side conditions ``by norm_num``)
   or a kernel-checked refusal certificate ``¬ scaledAnchorsValid ...``;
5. writes the Lean module to
   ``lean-spec/OpenDistillationFactory/Materials/DistillAtlas/EnvFieldInstances.lean``
   and a JSON report (schema ``lupine.env_field_binding_report.v1``) to
   ``data/y_matrix_runs/env_field_binding_report.json`` for runner telemetry
   and the promotion gate (``lupine_distill.odf.field_certificates``).

The emitted module is verified by ``lake build`` in ``lean-spec/`` (the
`#guard` locks in ``Materials/Vision.lean`` pin the valid/refused counts).

Default invocation (from the repo root):

    python python/scripts/bind_env_field_instances.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]

REPORT_SCHEMA = "lupine.env_field_binding_report.v1"
GENERATED_MODULE = (
    "lean-spec/OpenDistillationFactory/Materials/DistillAtlas/EnvFieldInstances.lean"
)

# 1 J/m^2 in eV/A^2 (CODATA e = 1.602176634e-19 C exactly; 1 J/m^2 = 1e-20 J/A^2).
EV_PER_JM2_A2 = 1e-20 / 1.602176634e-19

# Integer scale for the Lean literals: x1e4 eV/atom (0.1 meV/atom resolution).
SCALE = 10_000

FCC_MATERIALS = ("Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr")
MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")

# First-shell coordination probed by each anchor observable (fcc, bulk c=12).
ANCHOR_COORDINATION = {"gamma_100": 8, "gamma_111": 9, "vacancy": 11}
VACANCY_SHELL_ATOMS = 12  # fcc first shell


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")


@dataclass(frozen=True)
class CellAnchors:
    """One (model, material) cell's measured anchors and admissibility."""

    material: str
    model_id: str
    a0_angstrom: float
    gamma_100_model: float
    gamma_100_ref: float
    gamma_111_model: float
    gamma_111_ref: float
    evac_model: float
    evac_ref: float
    p8_ev: float
    p9_ev: float
    p11_ev: float
    p8_scaled: int
    p9_scaled: int
    p11_scaled: int
    valid: bool
    violations: tuple[str, ...]

    @property
    def lean_name(self) -> str:
        return f"{_sanitize(self.model_id)}_{_sanitize(self.material)}"


def _load_targets(targets_dir: Path) -> dict[tuple[str, str], float]:
    """Map (material, property) -> DFT-PBE reference value for fcc entries."""
    refs: dict[tuple[str, str], float] = {}
    for fname, wanted in (
        ("surface_energies.json", {"surface_energy_100", "surface_energy_111"}),
        ("vacancy_formation.json", {"vacancy_formation_energy"}),
    ):
        payload = json.loads((targets_dir / fname).read_text(encoding="utf-8"))
        for entry in payload["entries"]:
            if entry.get("structure") != "fcc":
                continue
            if entry["property"] not in wanted:
                continue
            if entry.get("method") != "DFT-PBE":
                continue
            refs[(entry["material"], entry["property"])] = float(entry["value"])
    return refs


def _facet_gamma(run: dict, miller: str) -> float:
    for surf in run["results"]["surfaces"]:
        if surf["values"]["miller"] == miller:
            return float(surf["values"]["gamma_j_per_m2"])
    raise KeyError(f"facet {miller} missing from surfaces block")


def _bind_cell(run_path: Path, refs: dict[tuple[str, str], float]) -> CellAnchors:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    material = run["material"]
    model_id = run["model_id"]
    a0 = float(run["results"]["lattice"]["values"]["a0_angstrom"])

    g100_model = _facet_gamma(run, "100")
    g111_model = _facet_gamma(run, "111")
    evac_model = float(run["results"]["vacancy"]["values"]["vacancy_formation_ev"])

    g100_ref = refs[(material, "surface_energy_100")]
    g111_ref = refs[(material, "surface_energy_111")]
    evac_ref = refs[(material, "vacancy_formation_energy")]

    area_100 = a0 * a0 / 2.0
    area_111 = math.sqrt(3.0) / 4.0 * a0 * a0

    p8 = (g100_model - g100_ref) * EV_PER_JM2_A2 * area_100
    p9 = (g111_model - g111_ref) * EV_PER_JM2_A2 * area_111
    p11 = (evac_model - evac_ref) / VACANCY_SHELL_ATOMS

    p8s, p9s, p11s = (round(v * SCALE) for v in (p8, p9, p11))

    violations: list[str] = []
    if not p8s <= p9s:
        violations.append(f"P(8) = {p8s}e-4 > P(9) = {p9s}e-4 (mono)")
    if not p9s <= p11s:
        violations.append(f"P(9) = {p9s}e-4 > P(11) = {p11s}e-4 (mono)")
    if not p11s <= 0:
        violations.append(f"P(11) = {p11s}e-4 > 0 (softening)")

    return CellAnchors(
        material=material,
        model_id=model_id,
        a0_angstrom=a0,
        gamma_100_model=g100_model,
        gamma_100_ref=g100_ref,
        gamma_111_model=g111_model,
        gamma_111_ref=g111_ref,
        evac_model=evac_model,
        evac_ref=evac_ref,
        p8_ev=p8,
        p9_ev=p9,
        p11_ev=p11,
        p8_scaled=p8s,
        p9_scaled=p9s,
        p11_scaled=p11s,
        valid=not violations,
        violations=tuple(violations),
    )


def _lean_rat(scaled: int) -> str:
    """Integer-scaled anchor as an exact Lean rational literal."""
    return f"({scaled} / {SCALE} : ℝ)" if scaled >= 0 else f"(-{-scaled} / {SCALE} : ℝ)"


def _anchor_provenance(cell: CellAnchors) -> str:
    return (
        f"P(8) = {cell.p8_scaled}e-4 from Δγ₁₀₀ = {cell.gamma_100_model:.4f} − "
        f"{cell.gamma_100_ref:.4f} J/m² on a₀²/2, "
        f"P(9) = {cell.p9_scaled}e-4 from Δγ₁₁₁ = {cell.gamma_111_model:.4f} − "
        f"{cell.gamma_111_ref:.4f} J/m² on √3a₀²/4, "
        f"P(11) = {cell.p11_scaled}e-4 from ΔE_vac = {cell.evac_model:.4f} − "
        f"{cell.evac_ref:.4f} eV over 12 shell atoms; a₀ = {cell.a0_angstrom:.4f} Å "
        f"(model-relaxed)"
    )


def _emit_measured(cell: CellAnchors) -> str:
    doc = (
        f"{cell.model_id}/{cell.material} measured field, tier 1 (eV/atom, ×1e-4 "
        f"exact): {_anchor_provenance(cell)}. Closure, bulk-invariance, "
        f"family-transfer, and ranking-recovery laws apply unconditionally. "
    )
    return (
        f"/-- {doc}-/\n"
        f"noncomputable def mfield_{cell.lean_name} : MeasuredField 12 :=\n"
        f"  mkMeasuredField {_lean_rat(cell.p8_scaled)} {_lean_rat(cell.p9_scaled)} "
        f"{_lean_rat(cell.p11_scaled)}\n"
    )


def _emit_instance(cell: CellAnchors) -> str:
    doc = (
        f"{cell.model_id}/{cell.material} anchored softening field, tier 2: "
        f"monotone softening holds on the measured anchors, so the directional "
        f"laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility "
        f"overestimation) also apply. Forgets to `mfield_{cell.lean_name}` "
        f"(`mkAnchoredField_toMeasuredField`). "
    )
    return (
        f"/-- {doc}-/\n"
        f"noncomputable def field_{cell.lean_name} : ErrorField 12 :=\n"
        f"  mkAnchoredField {_lean_rat(cell.p8_scaled)} {_lean_rat(cell.p9_scaled)} "
        f"{_lean_rat(cell.p11_scaled)}\n"
        f"    (by norm_num) (by norm_num) (by norm_num)\n"
    )


def _emit_refusal(cell: CellAnchors) -> str:
    doc = (
        f"{cell.model_id}/{cell.material} tier-2 REFUSAL: measured anchors "
        f"(P(8), P(9), P(11)) = ({cell.p8_scaled}, {cell.p9_scaled}, "
        f"{cell.p11_scaled})e-4 eV/atom violate monotone softening — "
        + "; ".join(cell.violations)
        + ". The directional softening laws do not apply to this cell (noise "
        f"floor or stiffening regime); its measured tier `mfield_{cell.lean_name}` "
        "still carries the correction and ranking laws. "
    )
    def lit(v: int) -> str:
        return f"({v})" if v < 0 else str(v)

    return (
        f"/-- {doc}-/\n"
        f"theorem field_refused_{cell.lean_name} :\n"
        f"    ¬ scaledAnchorsValid {lit(cell.p8_scaled)} {lit(cell.p9_scaled)} "
        f"{lit(cell.p11_scaled)} := by decide\n"
    )


def _emit_module(cells: list[CellAnchors], corpus_sha: str) -> str:
    valid = [c for c in cells if c.valid]
    refused = [c for c in cells if not c.valid]
    lines: list[str] = []
    lines.append(
        "/- AUTHORED by python/scripts/bind_env_field_instances.py from the\n"
        f"   Y-matrix statics corpus + DFT-PBE targets (corpus sha256 {corpus_sha}).\n"
        "   THE MEASURED FIELDS: per fcc (model, material) cell, the three anchors\n"
        "   P(8)/P(9)/P(11) (eV/atom, x1e-4 exact integers) are bound from the\n"
        "   (100)/(111) surface-energy and vacancy-formation errors on\n"
        "   model-relaxed geometry. TIER 1: every cell yields a `MeasuredField 12`\n"
        "   (closure/transfer/ranking laws, no shape assumption). TIER 2: cells\n"
        "   passing monotone softening (p8 <= p9 <= p11 <= 0, checked on the\n"
        "   emitted literals) also yield an `ErrorField 12` via `mkAnchoredField`\n"
        "   (directional barrier laws); violating cells get kernel-checked\n"
        f"   refusal certificates instead. {len(cells)} measured fields;\n"
        f"   {len(valid)} softening instances + {len(refused)} refusals =\n"
        f"   {len(cells)} cells. 0 sorry. -/\n"
    )
    lines.append("import OpenDistillationFactory.Materials.Theory.AnchoredField\n")
    lines.append(
        "namespace OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances\n"
    )
    lines.append(
        "open OpenDistillationFactory.Materials.Theory.EnvironmentField\n"
        "open OpenDistillationFactory.Materials.Theory.AnchoredField\n"
    )
    lines.append("/-! ## Tier 1: measured fields (every bound cell) -/\n")
    for cell in cells:
        lines.append(_emit_measured(cell))
    lines.append("/-! ## Tier 2: anchored softening fields (monotone-softening cells) -/\n")
    for cell in valid:
        lines.append(_emit_instance(cell))
    lines.append("/-! ## Tier-2 refusal certificates (outside the softening domain) -/\n")
    for cell in refused:
        lines.append(_emit_refusal(cell))
    lines.append(
        "/-- Every sweep cell is accounted for: instances + refusals = cells. -/\n"
        f"theorem cells_accounted : {len(valid)} + {len(refused)} = {len(cells)} := by\n"
        "  decide\n"
    )
    lines.append(
        "end OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances\n"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--runs-dir", type=Path, default=_REPO_ROOT / "data" / "y_matrix_runs"
    )
    parser.add_argument(
        "--targets-dir", type=Path, default=_REPO_ROOT / "data" / "y_matrix_targets"
    )
    parser.add_argument(
        "--lean-out", type=Path, default=_REPO_ROOT / GENERATED_MODULE
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=_REPO_ROOT / "data" / "y_matrix_runs" / "env_field_binding_report.json",
    )
    args = parser.parse_args(argv)

    refs = _load_targets(args.targets_dir)

    run_paths: list[Path] = []
    for material in FCC_MATERIALS:
        for model in MODELS:
            p = args.runs_dir / f"{material}_fcc_{model}.json"
            if not p.exists():
                print(f"WARNING: missing run {p.name}; cell skipped", file=sys.stderr)
                continue
            run_paths.append(p)

    sha = hashlib.sha256()
    for p in sorted(run_paths) + sorted(
        args.targets_dir / f for f in ("surface_energies.json", "vacancy_formation.json")
    ):
        sha.update(p.name.encode())
        sha.update(p.read_bytes())
    corpus_sha = sha.hexdigest()[:12]

    cells = sorted(
        (_bind_cell(p, refs) for p in run_paths),
        key=lambda c: (c.model_id, c.material),
    )

    module = _emit_module(cells, corpus_sha)
    args.lean_out.parent.mkdir(parents=True, exist_ok=True)
    args.lean_out.write_text(module, encoding="utf-8")

    report = {
        "schema": REPORT_SCHEMA,
        "corpus_sha256_12": corpus_sha,
        "generator": "python/scripts/bind_env_field_instances.py",
        "lean_module": str(args.lean_out.relative_to(_REPO_ROOT)),
        "scale": SCALE,
        "anchor_coordination": ANCHOR_COORDINATION,
        "cells": [asdict(c) | {"lean_name": c.lean_name} for c in cells],
        "n_cells": len(cells),
        "n_instances": sum(c.valid for c in cells),
        "n_refusals": sum(not c.valid for c in cells),
    }
    args.report_out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    print(
        f"bound {len(cells)} cells -> {report['n_instances']} instances, "
        f"{report['n_refusals']} refusals (corpus {corpus_sha})"
    )
    print(f"lean module: {args.lean_out}")
    print(f"report:      {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
