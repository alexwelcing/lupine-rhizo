"""H4: correction-transfer analysis (prereg H4, binding addendum 2026-07-02).

Operator (reimplemented to the documented v0.2 definition, adapted to the
Y-matrix): per model, a single stiffness-rescaling scalar
``s = median(B0_ref / B0_pred)`` fitted leave-one-material-out over the
registered material set — the held-out material never contributes to its own
correction. Application: ``corrected = s x prediction`` for the
energy/stiffness-like properties (:data:`CORRECTED_PROPERTIES`); a0 is
excluded (a length, not an energy scale — the softening mechanism predicts no
first-order a0 effect), and b0_prime is dimensionless and outside the
registered application list.

Metrics per (model, family): median |normalized error| before vs after
(normalization: the registered H1 rule via
:func:`lupine_distill.analysis.vectors.normalized_signed_error`, so the
near-zero-reference guard behaves identically to the confirmatory run), with
a seeded paired-bootstrap CI95 on the delta. Registered verdicts: a family
improves/degrades when |delta| exceeds the bootstrap CI95 half-width, else
unchanged; H4 pass when >= half of the non-EOS families (with cells) improve
and none degrade; H4 kill when the EOS family improves while >= half of the
non-EOS families degrade or are unchanged.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.binding import (
    family_reference_scales,
    select_references,
)
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    B0,
    DEFAULT_FAMILY_MAP,
    DEFAULT_METHOD_PREFERENCE,
    DEFAULT_TARGET_PROPERTY_MAP,
    require_properties_in_family_map,
)
from lupine_distill.analysis.loading import (
    ReferenceEntry,
    RunRecord,
    load_run_directory,
    load_targets_directory,
)
from lupine_distill.analysis.vectors import normalized_signed_error

H4_SCHEMA_ID = "lupine.y_matrix.h4_transfer_report.v1"
PREREG_DOC = "docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md"
ADDENDUM = "H4 binding addendum (2026-07-02), registered before this analysis ran"
REGISTERED_SEED = 20260702
DEFAULT_N_BOOTSTRAP = 1000
EOS_FAMILY = "eos"

# Registered application list: energy/stiffness-like properties only.
CORRECTED_PROPERTIES: tuple[str, ...] = (
    "b0",
    "e_vac",
    "gamma_100",
    "gamma_110",
    "gamma_111",
    "gamma_sfe",
    "dh_f",
)

# Target-file property map used by the confirmatory run: the registered
# default plus the compilation names for the 0 K bulk modulus and the cubic
# lattice constant (data/y_matrix_targets/eos.json, lattice_constants.json).
H4_TARGET_PROPERTY_MAP: Mapping[str, str] = MappingProxyType(
    {
        **DEFAULT_TARGET_PROPERTY_MAP,
        "bulk_modulus_0K_extrapolated": "b0",
        "lattice_constant_a": "a0",
    }
)

VERDICT_IMPROVES = "improves"
VERDICT_DEGRADES = "degrades"
VERDICT_UNCHANGED = "unchanged"
VERDICT_NO_CELLS = "no_cells"

IMPROVEMENT_CRITERION = (
    "family improves/degrades when |delta of median |rel err|| exceeds the "
    "bootstrap CI95 half-width; else unchanged"
)
PASS_CRITERION = (
    ">= half of non-EOS families (with cells) improve and none degrade"
)
KILL_CRITERION = (
    "EOS family improves and >= half of non-EOS families (with cells) "
    "degrade or are unchanged (registered expectation after H1/H2 kills)"
)


@dataclass(frozen=True)
class LooFold:
    """One leave-one-material-out fold: the held-out material's scalar."""

    material: str
    scalar: float
    n_donors: int


@dataclass(frozen=True)
class H4Cell:
    """One corrected (material, model, property) cell with both errors."""

    material: str
    model_id: str
    property_name: str
    family: str
    predicted: float
    corrected: float
    reference_value: float
    reference_method: str
    scalar: float
    abs_error_before: float
    abs_error_after: float
    guard_engaged: bool


@dataclass(frozen=True)
class FamilyTransfer:
    """Before/after transfer statistic for one (model, family)."""

    model_id: str
    family: str
    properties: tuple[str, ...]
    n_cells: int
    median_abs_error_before: float | None
    median_abs_error_after: float | None
    delta: float | None
    ci_low: float | None
    ci_high: float | None
    ci_half_width: float | None
    n_bootstrap: int
    verdict: str


@dataclass(frozen=True)
class H4ModelVerdict:
    """The registered H4 verdict for one model."""

    model_id: str
    eos_family_verdict: str
    n_non_eos_families_with_cells: int
    n_improve: int
    n_degrade: int
    n_unchanged: int
    pass_condition: bool
    kill_condition: bool
    verdict: str


def _require_finite(name: str, value: object) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InputValidationError(f"{name} must be finite, got {value!r}")
    return float(value)


def loo_stiffness_scalars(
    *, b0_ref: Mapping[str, float], b0_pred: Mapping[str, float]
) -> tuple[LooFold, ...]:
    """Registered LOO fit: s_i = median over j != i of (B0_ref_j / B0_pred_j).

    The held-out material's own B0 never contributes to its scalar.
    """
    if set(b0_ref) != set(b0_pred):
        raise InputValidationError(
            f"b0_ref and b0_pred cover different materials: "
            f"{sorted(set(b0_ref) ^ set(b0_pred))!r}"
        )
    materials = sorted(b0_ref)
    if len(materials) < 2:
        raise InputValidationError(
            f"LOO fit needs >= 2 materials, got {materials!r}"
        )
    ratios: dict[str, float] = {}
    for material in materials:
        ref = _require_finite(f"b0_ref[{material}]", b0_ref[material])
        pred = _require_finite(f"b0_pred[{material}]", b0_pred[material])
        if pred == 0.0:
            raise InputValidationError(
                f"b0_pred[{material}] is zero; B0 ratio undefined"
            )
        ratios[material] = ref / pred
    return tuple(
        LooFold(
            material=material,
            scalar=statistics.median(
                [ratios[donor] for donor in materials if donor != material]
            ),
            n_donors=len(materials) - 1,
        )
        for material in materials
    )


def family_transfer_statistic(
    before: Sequence[float],
    after: Sequence[float],
    *,
    model_id: str,
    family: str,
    properties: Sequence[str],
    rng: np.random.Generator,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
) -> FamilyTransfer:
    """Median |rel err| before vs after with a paired bootstrap CI95 on delta.

    An empty family is reported as ``no_cells`` (it consumes no rng draws)
    rather than silently omitted — the registered handling for dh_f, whose
    compounds sit outside the metal set.
    """
    if not isinstance(rng, np.random.Generator):
        raise InputValidationError(
            "rng must be a seeded numpy.random.Generator; "
            "global random state is never read"
        )
    if not isinstance(n_bootstrap, int) or n_bootstrap < 1:
        raise InputValidationError(
            f"n_bootstrap must be a positive int, got {n_bootstrap!r}"
        )
    if len(before) != len(after):
        raise InputValidationError(
            f"before/after are paired per cell; got lengths "
            f"{len(before)} != {len(after)}"
        )
    for name, values in (("before", before), ("after", after)):
        for value in values:
            if _require_finite(f"{name} error", value) < 0.0:
                raise InputValidationError(
                    f"{name} errors must be absolute (>= 0), got {value!r}"
                )
    if not before:
        return FamilyTransfer(
            model_id=model_id,
            family=family,
            properties=tuple(properties),
            n_cells=0,
            median_abs_error_before=None,
            median_abs_error_after=None,
            delta=None,
            ci_low=None,
            ci_high=None,
            ci_half_width=None,
            n_bootstrap=n_bootstrap,
            verdict=VERDICT_NO_CELLS,
        )
    before_arr = np.asarray(before, dtype=float)
    after_arr = np.asarray(after, dtype=float)
    median_before = float(np.median(before_arr))
    median_after = float(np.median(after_arr))
    delta = median_after - median_before
    boot_deltas = np.empty(n_bootstrap, dtype=float)
    n = before_arr.size
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        boot_deltas[i] = float(np.median(after_arr[idx])) - float(
            np.median(before_arr[idx])
        )
    ci_low = float(np.percentile(boot_deltas, 2.5))
    ci_high = float(np.percentile(boot_deltas, 97.5))
    half_width = (ci_high - ci_low) / 2.0
    if abs(delta) > half_width:
        verdict = VERDICT_IMPROVES if delta < 0.0 else VERDICT_DEGRADES
    else:
        verdict = VERDICT_UNCHANGED
    return FamilyTransfer(
        model_id=model_id,
        family=family,
        properties=tuple(properties),
        n_cells=int(n),
        median_abs_error_before=median_before,
        median_abs_error_after=median_after,
        delta=delta,
        ci_low=ci_low,
        ci_high=ci_high,
        ci_half_width=half_width,
        n_bootstrap=n_bootstrap,
        verdict=verdict,
    )


def h4_model_verdict(
    families: Sequence[FamilyTransfer],
    *,
    model_id: str,
    eos_family: str = EOS_FAMILY,
) -> H4ModelVerdict:
    """Registered H4 verdict logic over one model's family results."""
    eos_results = [f for f in families if f.family == eos_family]
    if len(eos_results) != 1:
        raise InputValidationError(
            f"model {model_id!r} needs exactly one {eos_family!r} family "
            f"result, got {len(eos_results)}"
        )
    eos_verdict = eos_results[0].verdict
    if eos_verdict == VERDICT_NO_CELLS:
        raise InputValidationError(
            f"model {model_id!r} has no EOS cells; H4 is not evaluable"
        )
    non_eos = [
        f
        for f in families
        if f.family != eos_family and f.verdict != VERDICT_NO_CELLS
    ]
    n = len(non_eos)
    n_improve = sum(1 for f in non_eos if f.verdict == VERDICT_IMPROVES)
    n_degrade = sum(1 for f in non_eos if f.verdict == VERDICT_DEGRADES)
    n_unchanged = sum(1 for f in non_eos if f.verdict == VERDICT_UNCHANGED)
    pass_condition = n > 0 and 2 * n_improve >= n and n_degrade == 0
    kill_condition = (
        eos_verdict == VERDICT_IMPROVES and 2 * (n_degrade + n_unchanged) >= n > 0
    )
    if pass_condition and kill_condition:
        verdict = "ambiguous"
    elif pass_condition:
        verdict = "pass"
    elif kill_condition:
        verdict = "kill"
    else:
        verdict = "inconclusive"
    return H4ModelVerdict(
        model_id=model_id,
        eos_family_verdict=eos_verdict,
        n_non_eos_families_with_cells=n,
        n_improve=n_improve,
        n_degrade=n_degrade,
        n_unchanged=n_unchanged,
        pass_condition=pass_condition,
        kill_condition=kill_condition,
        verdict=verdict,
    )


def _model_runs(
    runs: Sequence[RunRecord], model_id: str, materials: Sequence[str]
) -> dict[str, RunRecord]:
    selected: dict[str, RunRecord] = {}
    for run in runs:
        if run.model_id != model_id:
            continue
        if run.material in selected:
            raise InputValidationError(
                f"duplicate run for material {run.material!r} under model "
                f"{model_id!r} ({selected[run.material].source_path} and "
                f"{run.source_path})"
            )
        selected[run.material] = run
    missing = [m for m in materials if m not in selected]
    if missing:
        raise InputValidationError(
            f"model {model_id!r} has no runs for materials {missing!r}"
        )
    return selected


def assemble_h4_cells(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_id: str,
    materials: Sequence[str],
    corrected_properties: Sequence[str] = CORRECTED_PROPERTIES,
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
    near_zero_epsilon: float,
) -> tuple[tuple[H4Cell, ...], tuple[LooFold, ...]]:
    """Bind, fit the LOO scalars, and correct one model's cells.

    Property availability follows the data: a cell exists only where both a
    prediction and a bound reference exist. B0 is mandatory per material (it
    is the fit input) — its absence fails fast.
    """
    if not materials or len(set(materials)) != len(materials):
        raise InputValidationError(
            f"materials must be non-empty and unique, got {materials!r}"
        )
    prop_to_family = require_properties_in_family_map(
        corrected_properties, family_map
    )
    model_runs = _model_runs(runs, model_id, materials)
    bound = select_references(references, method_preference=method_preference)

    def _entry(material: str, prop: str) -> ReferenceEntry | None:
        run = model_runs[material]
        return bound.get((material, run.structure_type.lower(), prop))

    b0_ref: dict[str, float] = {}
    b0_pred: dict[str, float] = {}
    for material in materials:
        entry = _entry(material, B0)
        predicted = model_runs[material].predictions.get(B0)
        if entry is None or predicted is None:
            raise InputValidationError(
                f"material {material!r} lacks a b0 "
                f"{'reference' if entry is None else 'prediction'} under "
                f"model {model_id!r}; the LOO stiffness fit requires b0"
            )
        b0_ref[material] = entry.value
        b0_pred[material] = float(predicted)
    folds = loo_stiffness_scalars(b0_ref=b0_ref, b0_pred=b0_pred)
    scalar_by_material = {fold.material: fold.scalar for fold in folds}

    scale_inputs: dict[tuple[str, str], float] = {}
    for material in materials:
        for prop in corrected_properties:
            entry = _entry(material, prop)
            if entry is not None:
                scale_inputs[(material, prop)] = entry.value
    scales = family_reference_scales(
        scale_inputs, corrected_properties, family_map
    )

    cells: list[H4Cell] = []
    for material in materials:
        run = model_runs[material]
        scalar = scalar_by_material[material]
        for prop in corrected_properties:
            predicted = run.predictions.get(prop)
            entry = _entry(material, prop)
            if predicted is None or entry is None:
                continue
            family = prop_to_family[prop]
            common = dict(
                uncertainty=entry.uncertainty,
                family_scale=scales.get(family, 0.0),
                near_zero_epsilon=near_zero_epsilon,
            )
            before = normalized_signed_error(
                float(predicted), entry.value, **common
            )
            after = normalized_signed_error(
                scalar * float(predicted), entry.value, **common
            )
            cells.append(
                H4Cell(
                    material=material,
                    model_id=model_id,
                    property_name=prop,
                    family=family,
                    predicted=float(predicted),
                    corrected=scalar * float(predicted),
                    reference_value=entry.value,
                    reference_method=entry.method,
                    scalar=scalar,
                    abs_error_before=abs(before.value),
                    abs_error_after=abs(after.value),
                    guard_engaged=before.guard_engaged,
                )
            )
    return tuple(cells), folds


def _ordered_families(
    family_map: Mapping[str, Sequence[str]],
    corrected_properties: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    corrected = set(corrected_properties)
    return {
        family: tuple(p for p in members if p in corrected)
        for family, members in family_map.items()
        if any(p in corrected for p in members)
    }


def _family_dict(result: FamilyTransfer) -> dict[str, object]:
    return {
        "properties": list(result.properties),
        "n_cells": result.n_cells,
        "median_abs_error_before": result.median_abs_error_before,
        "median_abs_error_after": result.median_abs_error_after,
        "delta": result.delta,
        "ci95": (
            None
            if result.ci_low is None
            else [result.ci_low, result.ci_high]
        ),
        "ci_half_width": result.ci_half_width,
        "verdict": result.verdict,
    }


def build_h4_transfer_report(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_ids: Sequence[str],
    materials: Sequence[str],
    corrected_properties: Sequence[str] = CORRECTED_PROPERTIES,
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
    near_zero_epsilon: float,
    seed: int,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    deviations: Sequence[str] = (),
) -> dict[str, object]:
    """Run the registered H4 transfer analysis and return the ledger report.

    Determinism: a single ``numpy.random.default_rng(seed)`` is consumed in a
    fixed order (models in ``model_ids`` order, families in ``family_map``
    order; empty families consume no draws), so identical inputs and seed
    reproduce the report bit for bit.
    """
    if not model_ids or len(set(model_ids)) != len(model_ids):
        raise InputValidationError(
            f"model_ids must be non-empty and unique, got {model_ids!r}"
        )
    if not isinstance(seed, int):
        raise InputValidationError(f"seed must be an int, got {seed!r}")
    rng = np.random.default_rng(seed)
    families = _ordered_families(family_map, corrected_properties)

    per_model: dict[str, object] = {}
    verdict_by_model: dict[str, str] = {}
    guard_cells: list[list[str]] = []
    references_used: list[dict[str, object]] = []
    empty_families: dict[str, list[str]] = {}
    for model_index, model_id in enumerate(model_ids):
        cells, folds = assemble_h4_cells(
            runs,
            references,
            model_id=model_id,
            materials=materials,
            corrected_properties=corrected_properties,
            family_map=family_map,
            method_preference=method_preference,
            near_zero_epsilon=near_zero_epsilon,
        )
        family_results: list[FamilyTransfer] = []
        for family, props in families.items():
            family_cells = [c for c in cells if c.family == family]
            result = family_transfer_statistic(
                [c.abs_error_before for c in family_cells],
                [c.abs_error_after for c in family_cells],
                model_id=model_id,
                family=family,
                properties=props,
                rng=rng,
                n_bootstrap=n_bootstrap,
            )
            family_results.append(result)
            if result.verdict == VERDICT_NO_CELLS:
                empty_families.setdefault(family, []).append(model_id)
        verdict = h4_model_verdict(family_results, model_id=model_id)
        verdict_by_model[model_id] = verdict.verdict
        for cell in cells:
            if cell.guard_engaged:
                record = [cell.model_id, cell.material, cell.property_name]
                if record not in guard_cells:
                    guard_cells.append(record)
            if model_index == 0:
                references_used.append(
                    {
                        "material": cell.material,
                        "property": cell.property_name,
                        "value": cell.reference_value,
                        "method": cell.reference_method,
                    }
                )
        per_model[model_id] = {
            "loo_folds": [
                {
                    "material": fold.material,
                    "scalar": fold.scalar,
                    "n_donors": fold.n_donors,
                }
                for fold in folds
            ],
            "scalar_median": float(
                statistics.median([fold.scalar for fold in folds])
            ),
            "scalar_min": min(fold.scalar for fold in folds),
            "scalar_max": max(fold.scalar for fold in folds),
            "n_cells": len(cells),
            "families": {
                result.family: _family_dict(result)
                for result in family_results
            },
            "verdict": {
                "eos_family_verdict": verdict.eos_family_verdict,
                "n_non_eos_families_with_cells": (
                    verdict.n_non_eos_families_with_cells
                ),
                "n_improve": verdict.n_improve,
                "n_degrade": verdict.n_degrade,
                "n_unchanged": verdict.n_unchanged,
                "pass_condition": verdict.pass_condition,
                "kill_condition": verdict.kill_condition,
                "verdict": verdict.verdict,
            },
        }

    verdicts = list(verdict_by_model.values())
    n_pass = verdicts.count("pass")
    n_kill = verdicts.count("kill")
    overall = verdicts[0] if len(set(verdicts)) == 1 else "mixed"

    notes = [
        "a0 is excluded from correction per the addendum (a length, not an "
        "energy scale); b0_prime is dimensionless and outside the registered "
        "application list, so the eos family is evaluated on b0 cells.",
        "the addendum's per-model pass/kill criteria are aggregated as: "
        "the overall verdict is the unanimous per-model verdict, else "
        "'mixed'.",
    ]
    for family, models_empty in empty_families.items():
        props = ", ".join(families[family])
        notes.append(
            f"family {family!r} ({props}) has no cells for models "
            f"{sorted(set(models_empty))!r} in this run: its properties "
            "(e.g. dh_f, compounds-only) do not bind inside the registered "
            "material set; recorded as no_cells rather than silently omitted."
        )

    return {
        "schema": H4_SCHEMA_ID,
        "prereg": PREREG_DOC,
        "addendum": ADDENDUM,
        "hypothesis": "H4",
        "mode": "confirmatory",
        "operator": (
            "per-model LOO stiffness rescaling: s_i = median over the other "
            "materials of (B0_ref / B0_pred); corrected = s_i x prediction "
            "for the corrected properties of held-out material i"
        ),
        "seed": seed,
        "n_bootstrap": n_bootstrap,
        "near_zero_epsilon": float(near_zero_epsilon),
        "method_preference": list(method_preference),
        "models": list(model_ids),
        "materials": list(materials),
        "corrected_properties": list(corrected_properties),
        "family_map": {
            family: list(members) for family, members in family_map.items()
        },
        "evaluated_families": {
            family: list(props) for family, props in families.items()
        },
        "criteria": {
            "improvement": IMPROVEMENT_CRITERION,
            "pass": PASS_CRITERION,
            "kill": KILL_CRITERION,
            "neither": (
                "when neither registered condition fires (e.g. the EOS "
                "family itself does not improve, so the kill precondition "
                "fails) the model verdict is 'inconclusive'"
            ),
        },
        "references_used": references_used,
        "guard_engaged_cells": guard_cells,
        "per_model": per_model,
        "overall": {
            "per_model": verdict_by_model,
            "n_pass": n_pass,
            "n_kill": n_kill,
            "n_other": len(verdicts) - n_pass - n_kill,
            "verdict": overall,
        },
        "notes": notes,
        "deviations": list(deviations),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lupine_distill.analysis.operator",
        description=(
            "Registered H4 correction-transfer analysis (prereg H4, binding "
            "addendum 2026-07-02): LOO stiffness-rescaling operator applied "
            "to the Y-matrix, per-family before/after verdicts."
        ),
    )
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--targets-dir", required=True)
    parser.add_argument(
        "--confirmatory-report",
        required=True,
        help=(
            "confirmatory primary report JSON; supplies the matched material "
            "set, model grid, method preference, and near-zero epsilon"
        ),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=REGISTERED_SEED)
    parser.add_argument("--n-bootstrap", type=int, default=DEFAULT_N_BOOTSTRAP)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        confirmatory = json.loads(
            Path(args.confirmatory_report).read_text(encoding="utf-8")
        )
        for key in ("matched_materials", "models", "method_preference",
                    "near_zero_epsilon"):
            if key not in confirmatory:
                raise InputValidationError(
                    f"confirmatory report lacks required key {key!r}"
                )
        runs = load_run_directory(Path(args.runs_dir))
        targets = load_targets_directory(
            Path(args.targets_dir), property_map=H4_TARGET_PROPERTY_MAP
        )
        report = build_h4_transfer_report(
            runs,
            targets.entries,
            model_ids=tuple(confirmatory["models"]),
            materials=tuple(confirmatory["matched_materials"]),
            method_preference=tuple(confirmatory["method_preference"]),
            near_zero_epsilon=float(confirmatory["near_zero_epsilon"]),
            seed=args.seed,
            n_bootstrap=args.n_bootstrap,
        )
        report["config_source"] = str(args.confirmatory_report)
        report["unmapped_target_properties"] = list(
            targets.unmapped_properties
        )
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(report, indent=1) + "\n", encoding="utf-8"
        )
        overall = report["overall"]
        print(f"h4_transfer report written: {out_path}")
        print(f"per-model verdicts: {overall['per_model']}")
        print(f"overall: {overall['verdict']}")
        return 0
    except InputValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ADDENDUM",
    "CORRECTED_PROPERTIES",
    "DEFAULT_N_BOOTSTRAP",
    "EOS_FAMILY",
    "FamilyTransfer",
    "H4Cell",
    "H4ModelVerdict",
    "H4_SCHEMA_ID",
    "H4_TARGET_PROPERTY_MAP",
    "LooFold",
    "PREREG_DOC",
    "REGISTERED_SEED",
    "assemble_h4_cells",
    "build_h4_transfer_report",
    "family_transfer_statistic",
    "h4_model_verdict",
    "loo_stiffness_scalars",
    "main",
]
