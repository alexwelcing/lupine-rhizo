"""Descriptive (reference-free) mode: cross-model disagreement vectors.

When reference targets are not yet bound, the sweep can still be analyzed
descriptively: per (material, property), each model's deviation from the
cross-model mean prediction forms a disagreement vector — the ensemble-spread
analog of the confirmatory error vector, normalized by ``|mean|`` with the
same near-zero guard machinery (epsilon branch; family median ``|mean|``
scale). Matrices are labeled ``mode="descriptive"`` and must never feed the
registered H1-H3 tests.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.binding import family_reference_scales
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_FAMILY_MAP,
    require_properties_in_family_map,
)
from lupine_distill.analysis.loading import RunRecord
from lupine_distill.analysis.vectors import (
    ErrorCell,
    ErrorMatrix,
    _build_matrix,
    _runs_for_model,
    _validate_common_args,
    normalized_signed_error,
)

DESCRIPTIVE_MODE = "descriptive"
CROSS_MODEL_METHOD = "cross_model_mean"


def _matched_materials(
    per_model: Mapping[str, Mapping[str, RunRecord]],
    model_ids: Sequence[str],
    properties: Sequence[str],
    excluded_materials: Sequence[str],
) -> tuple[list[str], list[tuple[str, str]]]:
    excluded_set = set(excluded_materials)
    all_materials = sorted(set().union(*[set(r) for r in per_model.values()]))
    exclusions: list[tuple[str, str]] = []
    included: list[str] = []
    for material in all_materials:
        if material in excluded_set:
            exclusions.append((material, "caller-excluded"))
            continue
        missing_models = [m for m in model_ids if material not in per_model[m]]
        if missing_models:
            exclusions.append((material, f"missing models: {missing_models}"))
            continue
        missing_props = sorted(
            {
                prop
                for m in model_ids
                for prop in properties
                if prop not in per_model[m][material].predictions
            }
        )
        if missing_props:
            exclusions.append(
                (material, f"missing prediction(s) in >=1 model: {missing_props}")
            )
            continue
        structures = {per_model[m][material].structure_type for m in model_ids}
        if len(structures) > 1:
            raise InputValidationError(
                f"material {material!r} has inconsistent structures across "
                f"models: {sorted(structures)!r}"
            )
        included.append(material)
    if not included:
        raise InputValidationError(
            f"descriptive matched-n left no materials; exclusions: {exclusions!r}"
        )
    return included, exclusions


def assemble_descriptive_matrices(
    runs: Sequence[RunRecord],
    *,
    model_ids: Sequence[str],
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    excluded_materials: Sequence[str] = (),
    near_zero_epsilon: float,
) -> tuple[ErrorMatrix, ...]:
    """One disagreement matrix per model, on a shared matched material set."""
    _validate_common_args(properties, family_map, near_zero_epsilon)
    prop_to_family = require_properties_in_family_map(properties, family_map)
    if len(model_ids) < 2 or len(set(model_ids)) != len(model_ids):
        raise InputValidationError(
            f"descriptive mode needs >= 2 distinct model_ids, got {model_ids!r}"
        )
    per_model = {m: _runs_for_model(runs, m) for m in model_ids}
    included, exclusions = _matched_materials(
        per_model, model_ids, properties, excluded_materials
    )
    consensus = {
        (material, prop): float(
            np.mean([per_model[m][material].predictions[prop] for m in model_ids])
        )
        for material in included
        for prop in properties
    }
    scales = family_reference_scales(consensus, properties, family_map)
    matrices: list[ErrorMatrix] = []
    for model in model_ids:
        cells_by_material: dict[str, dict[str, ErrorCell]] = {}
        for material in included:
            run = per_model[model][material]
            cells: dict[str, ErrorCell] = {}
            for prop in properties:
                mean = consensus[(material, prop)]
                normalized = normalized_signed_error(
                    float(run.predictions[prop]),
                    mean,
                    uncertainty=None,
                    family_scale=scales.get(prop_to_family[prop], 0.0),
                    near_zero_epsilon=near_zero_epsilon,
                )
                cells[prop] = ErrorCell(
                    material=material,
                    model_id=model,
                    property_name=prop,
                    predicted=float(run.predictions[prop]),
                    reference_value=mean,
                    reference_method=CROSS_MODEL_METHOD,
                    normalized_error=normalized.value,
                    guard_engaged=normalized.guard_engaged,
                )
            cells_by_material[material] = cells
        matrices.append(
            _build_matrix(
                mode=DESCRIPTIVE_MODE,
                model_id=model,
                properties=properties,
                cells_by_material=cells_by_material,
                run_props_by_material={
                    m: dict(per_model[model][m].predictions) for m in included
                },
                exclusions=list(exclusions),
                candidates=included,
            )
        )
    return tuple(matrices)


def stack_matrices(matrices: Sequence[ErrorMatrix]) -> np.ndarray:
    """Row-stack matrices sharing a property axis (pooled ensemble spread)."""
    if not matrices:
        raise InputValidationError("no matrices to stack")
    properties = matrices[0].properties
    for matrix in matrices[1:]:
        if matrix.properties != properties:
            raise InputValidationError(
                f"property axes differ: {matrix.properties!r} vs {properties!r}"
            )
    stacked = np.vstack([m.values for m in matrices])
    stacked.setflags(write=False)
    return stacked


__all__ = [
    "CROSS_MODEL_METHOD",
    "DESCRIPTIVE_MODE",
    "assemble_descriptive_matrices",
    "stack_matrices",
]
