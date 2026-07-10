"""Bind measured environment-error-field anchors into Lean ``ErrorField`` instances.

For each fcc, bcc, and diamond (material, model) cell of the Y-matrix sweep
this binder:

1. reads the model-relaxed statics run
   (``data/y_matrix_runs/<Mat>_<structure>_<model>.json``, schema
   ``lupine.statics_run.v1``): lattice constant ``a0``, per-facet surface
   energies, and the vacancy formation energy;
2. binds DFT-PBE reference targets from ``data/y_matrix_targets/``
   (``surface_energies.json``, ``vacancy_formation.json``);
3. converts the signed errors into the three per-atom field anchors of the
   climate-series formalization ("A Field, Not a Neural Net"):

   fcc (bulk c = 12, 12 first-shell atoms per vacancy):

       P(8)  = (gamma_100^model - gamma_100^ref) * (a0^2 / 2)       [ (100), eV/atom ]
       P(9)  = (gamma_111^model - gamma_111^ref) * (sqrt(3)/4 a0^2) [ (111), eV/atom ]
       P(11) = (Evac^model - Evac^ref) / 12                          [ vacancy shell ]

   bcc (bulk c = 8, 8 first-shell atoms per vacancy):

       P(4)  = (gamma_100^model - gamma_100^ref) * a0^2              [ (100), eV/atom ]
       P(6)  = (gamma_110^model - gamma_110^ref) * (a0^2 / sqrt(2))  [ (110), eV/atom ]
       P(7)  = (Evac^model - Evac^ref) / 8                           [ vacancy shell ]

   diamond (bulk c = 4, 4 first-shell atoms per vacancy; the statics runs
   measure only the vacancy observable, so this is a single-anchor layout):

       P(3)  = (Evac^model - Evac^ref) / 4                           [ vacancy shell ]

   The rocksalt cells (MgO, NaCl) measure no surface or vacancy observables
   at all; they are recorded as unbound structures in the report rather
   than silently skipped — binding them needs new charge-balanced slab and
   defect runs, not new code.

   (surface-energy errors in J/m^2 are converted with 1 J/m^2 = 0.06241509074
   eV/A^2; the facet areas are the area per surface atom on model-relaxed
   geometry);
4. checks the anchored-field admissibility predicate **on the integer-scaled
   anchors** (x1e4 eV/atom, exactly the literals emitted into Lean):

       p_1 <= p_2 <= ... <= p_n <= 0    (monotone softening)

   and emits, per cell, either an ``ErrorField`` instance via the layout's
   constructor (``mkAnchoredField`` / ``mkAnchoredFieldBcc`` /
   ``mkAnchoredFieldDiamond``; side conditions ``by norm_num``) or a
   kernel-checked refusal certificate on the layout's decidable predicate
   (``¬ scaledAnchorsValid ...`` etc.);
5. writes the Lean module to
   ``lean-spec/OpenDistillationFactory/Materials/DistillAtlas/EnvFieldInstances.lean``
   and a JSON report (schema ``lupine.env_field_binding_report.v2``) to
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
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]

REPORT_SCHEMA = "lupine.env_field_binding_report.v2"
GENERATED_MODULE = (
    "lean-spec/OpenDistillationFactory/Materials/DistillAtlas/EnvFieldInstances.lean"
)

# 1 J/m^2 in eV/A^2 (CODATA e = 1.602176634e-19 C exactly; 1 J/m^2 = 1e-20 J/A^2).
EV_PER_JM2_A2 = 1e-20 / 1.602176634e-19

# Integer scale for the Lean literals: x1e4 eV/atom (0.1 meV/atom resolution).
SCALE = 10_000

MODELS = ("chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium")


@dataclass(frozen=True)
class FacetSpec:
    """One surface-energy anchor of a structure's layout."""

    observable: str  # target-file property suffix, e.g. "gamma_100"
    miller: str  # miller index in the statics run's surfaces block
    coordination: int  # first-shell coordination the facet probes
    gamma_label: str  # provenance label, e.g. "γ₁₀₀"
    area_label: str  # provenance label for the per-atom facet area
    area: Callable[[float], float]  # per-surface-atom area from a0 [A^2]


@dataclass(frozen=True)
class StructureLayout:
    """The anchor layout of one crystal-structure family."""

    structure: str
    materials: tuple[str, ...]
    bulk_coordination: int
    vacancy_coordination: int
    vacancy_shell_atoms: int
    facets: tuple[FacetSpec, ...]
    measured_ctor: str  # Lean tier-1 constructor
    anchored_ctor: str  # Lean tier-2 constructor
    validity_predicate: str  # Lean decidable admissibility predicate


LAYOUTS: tuple[StructureLayout, ...] = (
    StructureLayout(
        structure="fcc",
        materials=("Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr"),
        bulk_coordination=12,
        vacancy_coordination=11,
        vacancy_shell_atoms=12,
        facets=(
            FacetSpec(
                observable="gamma_100",
                miller="100",
                coordination=8,
                gamma_label="γ₁₀₀",
                area_label="a₀²/2",
                area=lambda a0: a0 * a0 / 2.0,
            ),
            FacetSpec(
                observable="gamma_111",
                miller="111",
                coordination=9,
                gamma_label="γ₁₁₁",
                area_label="√3a₀²/4",
                area=lambda a0: math.sqrt(3.0) / 4.0 * a0 * a0,
            ),
        ),
        measured_ctor="mkMeasuredField",
        anchored_ctor="mkAnchoredField",
        validity_predicate="scaledAnchorsValid",
    ),
    StructureLayout(
        structure="bcc",
        materials=("Cr", "Fe", "Mo", "Nb", "Ta", "V", "W"),
        bulk_coordination=8,
        vacancy_coordination=7,
        vacancy_shell_atoms=8,
        facets=(
            FacetSpec(
                observable="gamma_100",
                miller="100",
                coordination=4,
                gamma_label="γ₁₀₀",
                area_label="a₀²",
                area=lambda a0: a0 * a0,
            ),
            FacetSpec(
                observable="gamma_110",
                miller="110",
                coordination=6,
                gamma_label="γ₁₁₀",
                area_label="a₀²/√2",
                area=lambda a0: a0 * a0 / math.sqrt(2.0),
            ),
        ),
        measured_ctor="mkMeasuredFieldBcc",
        anchored_ctor="mkAnchoredFieldBcc",
        validity_predicate="scaledAnchorsBccValid",
    ),
    StructureLayout(
        structure="diamond",
        materials=("Si",),
        bulk_coordination=4,
        vacancy_coordination=3,
        vacancy_shell_atoms=4,
        facets=(),
        measured_ctor="mkMeasuredFieldDiamond",
        anchored_ctor="mkAnchoredFieldDiamond",
        validity_predicate="scaledAnchorDiamondValid",
    ),
)

#: Sweep structures whose statics runs measure none of the anchor
#: observables; recorded in the report so absence is documented, not silent.
UNBOUND_STRUCTURES = {
    "rocksalt": (
        "statics runs carry only EOS + lattice results (no surface energies, "
        "no vacancy formation); the anchor layout needs new charge-balanced "
        "slab and defect runs for MgO/NaCl"
    ),
}


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")


@dataclass(frozen=True)
class Anchor:
    """One measured anchor: the observable, the coordination it probes, and
    the bound per-atom field value (exact scaled integer = Lean literal)."""

    observable: str
    coordination: int
    model_value: float  # J/m^2 for facets, eV for the vacancy
    ref_value: float
    p_ev: float
    p_scaled: int


@dataclass(frozen=True)
class CellAnchors:
    """One (model, material) cell's measured anchors and admissibility."""

    material: str
    model_id: str
    structure: str
    bulk_coordination: int
    a0_angstrom: float
    anchors: tuple[Anchor, ...]
    valid: bool
    violations: tuple[str, ...]

    @property
    def lean_name(self) -> str:
        return f"{_sanitize(self.model_id)}_{_sanitize(self.material)}"

    @property
    def scaled(self) -> tuple[int, ...]:
        return tuple(a.p_scaled for a in self.anchors)


def _load_targets(targets_dir: Path) -> dict[tuple[str, str, str], float]:
    """Map (structure, material, property) -> DFT-PBE reference value."""
    structures = {layout.structure for layout in LAYOUTS}
    refs: dict[tuple[str, str, str], float] = {}
    for fname in ("surface_energies.json", "vacancy_formation.json", "beyond_metals.json"):
        payload = json.loads((targets_dir / fname).read_text(encoding="utf-8"))
        for entry in payload["entries"]:
            if entry.get("structure") not in structures:
                continue
            if entry.get("method") != "DFT-PBE":
                continue
            key = (entry["structure"], entry["material"], entry["property"])
            refs[key] = float(entry["value"])
    return refs


def _facet_gamma(run: dict, miller: str) -> float:
    for surf in run["results"]["surfaces"]:
        if surf["values"]["miller"] == miller:
            return float(surf["values"]["gamma_j_per_m2"])
    raise KeyError(f"facet {miller} missing from surfaces block")


def _bind_cell(
    run_path: Path, layout: StructureLayout, refs: dict[tuple[str, str, str], float]
) -> CellAnchors:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    material = run["material"]
    model_id = run["model_id"]
    a0 = float(run["results"]["lattice"]["values"]["a0_angstrom"])

    anchors: list[Anchor] = []
    for facet in layout.facets:
        g_model = _facet_gamma(run, facet.miller)
        g_ref = refs[(layout.structure, material, f"surface_energy_{facet.miller}")]
        p = (g_model - g_ref) * EV_PER_JM2_A2 * facet.area(a0)
        anchors.append(
            Anchor(
                observable=facet.observable,
                coordination=facet.coordination,
                model_value=g_model,
                ref_value=g_ref,
                p_ev=p,
                p_scaled=round(p * SCALE),
            )
        )
    evac_model = float(run["results"]["vacancy"]["values"]["vacancy_formation_ev"])
    evac_ref = refs[(layout.structure, material, "vacancy_formation_energy")]
    p_vac = (evac_model - evac_ref) / layout.vacancy_shell_atoms
    anchors.append(
        Anchor(
            observable="vacancy",
            coordination=layout.vacancy_coordination,
            model_value=evac_model,
            ref_value=evac_ref,
            p_ev=p_vac,
            p_scaled=round(p_vac * SCALE),
        )
    )

    violations: list[str] = []
    for lower, upper in zip(anchors, anchors[1:]):
        if not lower.p_scaled <= upper.p_scaled:
            violations.append(
                f"P({lower.coordination}) = {lower.p_scaled}e-4 > "
                f"P({upper.coordination}) = {upper.p_scaled}e-4 (mono)"
            )
    last = anchors[-1]
    if not last.p_scaled <= 0:
        violations.append(f"P({last.coordination}) = {last.p_scaled}e-4 > 0 (softening)")

    return CellAnchors(
        material=material,
        model_id=model_id,
        structure=layout.structure,
        bulk_coordination=layout.bulk_coordination,
        a0_angstrom=a0,
        anchors=tuple(anchors),
        valid=not violations,
        violations=tuple(violations),
    )


def _lean_rat(scaled: int) -> str:
    """Integer-scaled anchor as an exact Lean rational literal."""
    return f"({scaled} / {SCALE} : ℝ)" if scaled >= 0 else f"(-{-scaled} / {SCALE} : ℝ)"


def _anchor_provenance(cell: CellAnchors, layout: StructureLayout) -> str:
    parts: list[str] = []
    for anchor, facet in zip(cell.anchors, layout.facets):
        parts.append(
            f"P({anchor.coordination}) = {anchor.p_scaled}e-4 from "
            f"Δ{facet.gamma_label} = {anchor.model_value:.4f} − "
            f"{anchor.ref_value:.4f} J/m² on {facet.area_label}"
        )
    vac = cell.anchors[-1]
    parts.append(
        f"P({vac.coordination}) = {vac.p_scaled}e-4 from "
        f"ΔE_vac = {vac.model_value:.4f} − {vac.ref_value:.4f} eV over "
        f"{layout.vacancy_shell_atoms} shell atoms"
    )
    return ", ".join(parts) + f"; a₀ = {cell.a0_angstrom:.4f} Å (model-relaxed)"


def _rat_args(cell: CellAnchors) -> str:
    return " ".join(_lean_rat(s) for s in cell.scaled)


def _emit_measured(cell: CellAnchors, layout: StructureLayout) -> str:
    doc = (
        f"{cell.model_id}/{cell.material} ({cell.structure}) measured field, "
        f"tier 1 (eV/atom, ×1e-4 exact): {_anchor_provenance(cell, layout)}. "
        f"Closure, bulk-invariance, family-transfer, and ranking-recovery laws "
        f"apply unconditionally. "
    )
    return (
        f"/-- {doc}-/\n"
        f"noncomputable def mfield_{cell.lean_name} : "
        f"MeasuredField {layout.bulk_coordination} :=\n"
        f"  {layout.measured_ctor} {_rat_args(cell)}\n"
    )


def _emit_instance(cell: CellAnchors, layout: StructureLayout) -> str:
    doc = (
        f"{cell.model_id}/{cell.material} ({cell.structure}) anchored softening "
        f"field, tier 2: monotone softening holds on the measured anchors, so "
        f"the directional laws of `Theory.BarrierArrhenius` (barrier "
        f"underestimation, mobility overestimation) also apply. Forgets to "
        f"`mfield_{cell.lean_name}` (`{layout.anchored_ctor}_toMeasuredField`). "
    )
    return (
        f"/-- {doc}-/\n"
        f"noncomputable def field_{cell.lean_name} : "
        f"ErrorField {layout.bulk_coordination} :=\n"
        f"  {layout.anchored_ctor} {_rat_args(cell)}\n"
        f"    {' '.join(['(by norm_num)'] * len(cell.anchors))}\n"
    )


def _emit_refusal(cell: CellAnchors, layout: StructureLayout) -> str:
    coords = ", ".join(f"P({a.coordination})" for a in cell.anchors)
    scaled = ", ".join(str(s) for s in cell.scaled)
    doc = (
        f"{cell.model_id}/{cell.material} ({cell.structure}) tier-2 REFUSAL: "
        f"measured anchors ({coords}) = ({scaled})e-4 eV/atom violate monotone "
        f"softening — "
        + "; ".join(cell.violations)
        + ". The directional softening laws do not apply to this cell (noise "
        f"floor or stiffening regime); its measured tier `mfield_{cell.lean_name}` "
        "still carries the correction and ranking laws. "
    )

    def lit(v: int) -> str:
        return f"({v})" if v < 0 else str(v)

    args = " ".join(lit(s) for s in cell.scaled)
    return (
        f"/-- {doc}-/\n"
        f"theorem field_refused_{cell.lean_name} :\n"
        f"    ¬ {layout.validity_predicate} {args} := by decide\n"
    )


def _emit_module(cells: list[CellAnchors], corpus_sha: str) -> str:
    by_structure = {
        layout.structure: [c for c in cells if c.structure == layout.structure]
        for layout in LAYOUTS
    }
    valid = [c for c in cells if c.valid]
    refused = [c for c in cells if not c.valid]
    per_structure_counts = "; ".join(
        f"{layout.structure}: "
        f"{sum(c.valid for c in by_structure[layout.structure])} instances + "
        f"{sum(not c.valid for c in by_structure[layout.structure])} refusals = "
        f"{len(by_structure[layout.structure])} cells"
        for layout in LAYOUTS
    )
    layout_map = {layout.structure: layout for layout in LAYOUTS}
    lines: list[str] = []
    lines.append(
        "/- AUTHORED by python/scripts/bind_env_field_instances.py from the\n"
        f"   Y-matrix statics corpus + DFT-PBE targets (corpus sha256 {corpus_sha}).\n"
        "   THE MEASURED FIELDS: per (model, material) cell, the measured anchors —\n"
        "   fcc: P(8)/P(9)/P(11) with bulk pin c = 12; bcc: P(4)/P(6)/P(7) with\n"
        "   bulk pin c = 8; diamond: P(3) with bulk pin c = 4 (eV/atom, x1e-4\n"
        "   exact integers) — are bound from the facet surface-energy and\n"
        "   vacancy-formation errors on model-relaxed geometry.\n"
        "   TIER 1: every cell yields a `MeasuredField`\n"
        "   (closure/transfer/ranking laws, no shape assumption). TIER 2: cells\n"
        "   passing monotone softening (p_lo <= p_mid <= p_hi <= 0, checked on\n"
        "   the emitted literals) also yield an `ErrorField` via\n"
        "   the layout constructor (directional barrier laws);\n"
        "   violating cells get kernel-checked refusal certificates instead.\n"
        f"   {len(cells)} measured fields; {per_structure_counts};\n"
        f"   total {len(valid)} instances + {len(refused)} refusals =\n"
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
        lines.append(_emit_measured(cell, layout_map[cell.structure]))
    lines.append(
        "/-! ## Tier 2: anchored softening fields (monotone-softening cells) -/\n"
    )
    for cell in valid:
        lines.append(_emit_instance(cell, layout_map[cell.structure]))
    lines.append(
        "/-! ## Tier-2 refusal certificates (outside the softening domain) -/\n"
    )
    for cell in refused:
        lines.append(_emit_refusal(cell, layout_map[cell.structure]))
    for layout in LAYOUTS:
        group = by_structure[layout.structure]
        n_valid = sum(c.valid for c in group)
        n_refused = sum(not c.valid for c in group)
        lines.append(
            f"/-- Every {layout.structure} sweep cell is accounted for: "
            "instances + refusals = cells. -/\n"
            f"theorem {layout.structure}_cells_accounted : "
            f"{n_valid} + {n_refused} = {len(group)} := by\n"
            "  decide\n"
        )
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

    cells: list[CellAnchors] = []
    run_paths: list[Path] = []
    for layout in LAYOUTS:
        layout_paths: list[Path] = []
        for material in layout.materials:
            for model in MODELS:
                p = args.runs_dir / f"{material}_{layout.structure}_{model}.json"
                if not p.exists():
                    print(
                        f"WARNING: missing run {p.name}; cell skipped",
                        file=sys.stderr,
                    )
                    continue
                layout_paths.append(p)
        cells.extend(
            sorted(
                (_bind_cell(p, layout, refs) for p in layout_paths),
                key=lambda c: (c.model_id, c.material),
            )
        )
        run_paths.extend(layout_paths)

    sha = hashlib.sha256()
    for p in sorted(run_paths) + sorted(
        args.targets_dir / f
        for f in ("surface_energies.json", "vacancy_formation.json", "beyond_metals.json")
    ):
        sha.update(p.name.encode())
        sha.update(p.read_bytes())
    corpus_sha = sha.hexdigest()[:12]

    module = _emit_module(cells, corpus_sha)
    args.lean_out.parent.mkdir(parents=True, exist_ok=True)
    args.lean_out.write_text(module, encoding="utf-8")

    report = {
        "schema": REPORT_SCHEMA,
        "corpus_sha256_12": corpus_sha,
        "generator": "python/scripts/bind_env_field_instances.py",
        "lean_module": str(args.lean_out.relative_to(_REPO_ROOT)),
        "scale": SCALE,
        "structures": {
            layout.structure: {
                "bulk_coordination": layout.bulk_coordination,
                "vacancy_shell_atoms": layout.vacancy_shell_atoms,
                "anchor_coordination": {
                    **{f.observable: f.coordination for f in layout.facets},
                    "vacancy": layout.vacancy_coordination,
                },
                "measured_ctor": layout.measured_ctor,
                "anchored_ctor": layout.anchored_ctor,
                "validity_predicate": layout.validity_predicate,
                "n_cells": sum(c.structure == layout.structure for c in cells),
                "n_instances": sum(
                    c.valid and c.structure == layout.structure for c in cells
                ),
                "n_refusals": sum(
                    (not c.valid) and c.structure == layout.structure for c in cells
                ),
            }
            for layout in LAYOUTS
        },
        "unbound_structures": UNBOUND_STRUCTURES,
        "cells": [asdict(c) | {"lean_name": c.lean_name} for c in cells],
        "n_cells": len(cells),
        "n_instances": sum(c.valid for c in cells),
        "n_refusals": sum(not c.valid for c in cells),
    }
    args.report_out.write_text(json.dumps(report, indent=1), encoding="utf-8")

    for layout in LAYOUTS:
        s = report["structures"][layout.structure]
        print(
            f"{layout.structure}: bound {s['n_cells']} cells -> "
            f"{s['n_instances']} instances, {s['n_refusals']} refusals"
        )
    print(
        f"total: {len(cells)} cells -> {report['n_instances']} instances, "
        f"{report['n_refusals']} refusals (corpus {corpus_sha})"
    )
    print(f"lean module: {args.lean_out}")
    print(f"report:      {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
