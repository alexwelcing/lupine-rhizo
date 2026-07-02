"""Error-vector assembly for the Y-matrix confirmatory analysis (prereg H1).

Normalization (registered): signed relative error ``(pred - ref) / |ref|``.
Guard: when ``|ref| < 10 x`` its stated compilation uncertainty — or, when no
uncertainty is stated, ``|ref| <`` a caller-supplied epsilon — the absolute
error is scaled by the property family's median ``|ref|`` instead
(near-zero-reference degeneracy guard, e.g. SFE).

Binding policy (registered): the confirmatory target per property is the
DFT-PBE value when available, else experiment.

Matched-n (registered): materials missing any confirmatory property are
excluded from the vector analysis, never imputed. Material exclusions (e.g.
Fe per the 2026-07-01 deviations log) are caller-supplied, never hardcoded.

The reference-free descriptive mode lives in
:mod:`lupine_distill.analysis.descriptive`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.binding import (
    family_reference_scales,
    select_references,
)
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_FAMILY_MAP,
    DEFAULT_METHOD_PREFERENCE,
    require_properties_in_family_map,
)
from lupine_distill.analysis.loading import ReferenceEntry, RunRecord

CONFIRMATORY_MODE = "confirmatory"


@dataclass(frozen=True)
class NormalizedErrorValue:
    """A normalized error plus whether the near-zero-reference guard fired."""

    value: float
    guard_engaged: bool


@dataclass(frozen=True)
class ErrorCell:
    """One normalized (material, model, property) error with its provenance."""

    material: str
    model_id: str
    property_name: str
    predicted: float
    reference_value: float
    reference_method: str
    normalized_error: float
    guard_engaged: bool


@dataclass(frozen=True)
class ErrorMatrix:
    """A matched-n materials-by-properties matrix of normalized errors."""

    mode: str
    model_id: str
    materials: tuple[str, ...]
    properties: tuple[str, ...]
    values: np.ndarray
    cells: tuple[ErrorCell, ...]
    excluded_materials: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        expected = (len(self.materials), len(self.properties))
        if self.values.shape != expected:
            raise InputValidationError(
                f"ErrorMatrix values shape {self.values.shape} != {expected}"
            )
        frozen = np.array(self.values, dtype=float, copy=True)
        frozen.setflags(write=False)
        object.__setattr__(self, "values", frozen)


def _validate_epsilon(near_zero_epsilon: float) -> None:
    if (
        not isinstance(near_zero_epsilon, (int, float))
        or not math.isfinite(near_zero_epsilon)
        or near_zero_epsilon <= 0.0
    ):
        raise InputValidationError(
            f"near_zero_epsilon must be a positive finite number, "
            f"got {near_zero_epsilon!r}"
        )


def normalized_signed_error(
    predicted: float,
    reference: float,
    *,
    uncertainty: float | None,
    family_scale: float,
    near_zero_epsilon: float,
) -> NormalizedErrorValue:
    """Registered H1 normalization for one (prediction, reference) pair."""
    _validate_epsilon(near_zero_epsilon)
    for name, value in (("predicted", predicted), ("reference", reference)):
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InputValidationError(f"{name} must be finite, got {value!r}")
    if uncertainty is not None:
        guard = abs(reference) < 10.0 * uncertainty
    else:
        guard = abs(reference) < near_zero_epsilon
    if guard:
        if (
            not isinstance(family_scale, (int, float))
            or not math.isfinite(family_scale)
            or family_scale <= 0.0
        ):
            raise InputValidationError(
                f"guard engaged but family_scale is unusable: {family_scale!r}"
            )
        return NormalizedErrorValue(
            value=(predicted - reference) / family_scale, guard_engaged=True
        )
    return NormalizedErrorValue(
        value=(predicted - reference) / abs(reference), guard_engaged=False
    )


def _validate_common_args(
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]],
    near_zero_epsilon: float,
) -> None:
    if not properties:
        raise InputValidationError("properties must not be empty")
    if len(set(properties)) != len(properties):
        raise InputValidationError(f"properties contain duplicates: {properties!r}")
    require_properties_in_family_map(properties, family_map)
    _validate_epsilon(near_zero_epsilon)


def _runs_for_model(
    runs: Sequence[RunRecord], model_id: str
) -> dict[str, RunRecord]:
    if not isinstance(model_id, str) or not model_id:
        raise InputValidationError(f"model_id must be a non-empty string: {model_id!r}")
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
    return selected


def _confirmatory_cells_by_material(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_id: str,
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]],
    method_preference: Sequence[str],
    excluded_materials: Sequence[str],
    near_zero_epsilon: float,
) -> tuple[dict[str, dict[str, ErrorCell]], list[tuple[str, str]], list[str]]:
    """Bind, normalize, and diagnose; shared by cells and matrix assembly."""
    _validate_common_args(properties, family_map, near_zero_epsilon)
    prop_to_family = require_properties_in_family_map(properties, family_map)
    model_runs = _runs_for_model(runs, model_id)
    if not model_runs:
        raise InputValidationError(f"no runs found for model {model_id!r}")
    bound = select_references(references, method_preference=method_preference)
    excluded_set = set(excluded_materials)
    exclusions: list[tuple[str, str]] = []
    candidates: list[str] = []
    for material in sorted(model_runs):
        if material in excluded_set:
            exclusions.append((material, "caller-excluded"))
        else:
            candidates.append(material)
    scale_inputs: dict[tuple[str, str], float] = {}
    for material in candidates:
        run = model_runs[material]
        for prop in properties:
            entry = bound.get((material, run.structure_type.lower(), prop))
            if entry is not None:
                scale_inputs[(material, prop)] = entry.value
    scales = family_reference_scales(scale_inputs, properties, family_map)
    cells_by_material: dict[str, dict[str, ErrorCell]] = {}
    for material in candidates:
        run = model_runs[material]
        cells: dict[str, ErrorCell] = {}
        for prop in properties:
            predicted = run.predictions.get(prop)
            entry = bound.get((material, run.structure_type.lower(), prop))
            if predicted is None or entry is None:
                continue
            normalized = normalized_signed_error(
                float(predicted),
                entry.value,
                uncertainty=entry.uncertainty,
                family_scale=scales.get(prop_to_family[prop], 0.0),
                near_zero_epsilon=near_zero_epsilon,
            )
            cells[prop] = ErrorCell(
                material=material,
                model_id=model_id,
                property_name=prop,
                predicted=float(predicted),
                reference_value=entry.value,
                reference_method=entry.method,
                normalized_error=normalized.value,
                guard_engaged=normalized.guard_engaged,
            )
        cells_by_material[material] = cells
    return cells_by_material, exclusions, candidates


def assemble_error_cells(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_id: str,
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
    excluded_materials: Sequence[str] = (),
    near_zero_epsilon: float,
) -> tuple[ErrorCell, ...]:
    """All bindable (material, property) error cells — no matched-n filter.

    This is the H3 input surface: H3 compares per-group medians and does not
    require per-material completeness, unlike the H1/H2 vector analysis.
    """
    cells_by_material, _exclusions, candidates = _confirmatory_cells_by_material(
        runs,
        references,
        model_id=model_id,
        properties=properties,
        family_map=family_map,
        method_preference=method_preference,
        excluded_materials=excluded_materials,
        near_zero_epsilon=near_zero_epsilon,
    )
    return tuple(
        cells_by_material[material][prop]
        for material in candidates
        for prop in properties
        if prop in cells_by_material[material]
    )


def _build_matrix(
    *,
    mode: str,
    model_id: str,
    properties: Sequence[str],
    cells_by_material: Mapping[str, Mapping[str, ErrorCell]],
    run_props_by_material: Mapping[str, Mapping[str, float]],
    exclusions: list[tuple[str, str]],
    candidates: Sequence[str],
) -> ErrorMatrix:
    included: list[str] = []
    for material in candidates:
        cells = cells_by_material[material]
        missing = [p for p in properties if p not in cells]
        if missing:
            available = run_props_by_material[material]
            reasons = []
            for prop in missing:
                kind = "reference" if prop in available else "prediction"
                reasons.append(f"missing {kind}: {prop}")
            exclusions.append((material, "; ".join(reasons)))
        else:
            included.append(material)
    if not included:
        raise InputValidationError(
            f"matched-n left no materials for model {model_id!r}; "
            f"exclusions: {exclusions!r}"
        )
    ordered_cells = tuple(
        cells_by_material[material][prop]
        for material in included
        for prop in properties
    )
    values = np.array(
        [
            [cells_by_material[material][prop].normalized_error for prop in properties]
            for material in included
        ],
        dtype=float,
    )
    return ErrorMatrix(
        mode=mode,
        model_id=model_id,
        materials=tuple(included),
        properties=tuple(properties),
        values=values,
        cells=ordered_cells,
        excluded_materials=tuple(exclusions),
    )


def assemble_error_matrix(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_id: str,
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
    excluded_materials: Sequence[str] = (),
    include_materials: Sequence[str] | None = None,
    near_zero_epsilon: float,
) -> ErrorMatrix:
    """Matched-n confirmatory error matrix for one model (prereg H1 input)."""
    cells_by_material, exclusions, candidates = _confirmatory_cells_by_material(
        runs,
        references,
        model_id=model_id,
        properties=properties,
        family_map=family_map,
        method_preference=method_preference,
        excluded_materials=excluded_materials,
        near_zero_epsilon=near_zero_epsilon,
    )
    if include_materials is not None:
        allowed = set(include_materials)
        for material in candidates:
            if material not in allowed:
                exclusions.append((material, "outside cross-model matched set"))
        candidates = [m for m in candidates if m in allowed]
    run_props = {
        material: dict.fromkeys(run.predictions, 0.0)
        for material, run in _runs_for_model(runs, model_id).items()
    }
    return _build_matrix(
        mode=CONFIRMATORY_MODE,
        model_id=model_id,
        properties=properties,
        cells_by_material=cells_by_material,
        run_props_by_material=run_props,
        exclusions=exclusions,
        candidates=candidates,
    )


__all__ = [
    "CONFIRMATORY_MODE",
    "ErrorCell",
    "ErrorMatrix",
    "NormalizedErrorValue",
    "assemble_error_cells",
    "assemble_error_matrix",
    "normalized_signed_error",
]
