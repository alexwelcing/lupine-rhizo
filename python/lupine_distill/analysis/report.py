"""Confirmatory and descriptive report assembly for the Y-matrix analysis.

``build_confirmatory_report`` runs the registered H1/H2/H3 machinery end to
end and returns one JSON-serializable dict, self-describing enough to paste
into the ledger: every exclusion (caller material list, matched-n drops, H3
quarantine cells), every n count, the reference bindings used, and the guard
engagements are recorded alongside the statistics.

``build_descriptive_report`` is the reference-free ensemble-spread analysis
(cross-model disagreement vectors); it never emits hypothesis verdicts.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.descriptive import (
    assemble_descriptive_matrices,
    stack_matrices,
)
from lupine_distill.analysis.dimensionality import (
    leading_mode,
    pairwise_cosine,
    participation_ratio,
)
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_BULK_PROPERTIES,
    DEFAULT_DEFECT_PROPERTIES,
    DEFAULT_FAMILY_MAP,
    DEFAULT_METHOD_PREFERENCE,
)
from lupine_distill.analysis.loading import ReferenceEntry, RunRecord
from lupine_distill.analysis.nulls import (
    DEFAULT_N_DRAWS,
    leading_mode_cosine_null,
    pr_null_distribution,
)
from lupine_distill.analysis.vectors import (
    ErrorMatrix,
    assemble_error_cells,
    assemble_error_matrix,
)
from lupine_distill.analysis.weakspots import (
    DEFAULT_KILL_RATIO,
    DEFAULT_N_BOOTSTRAP,
    DEFAULT_PASS_RATIO,
    CellExclusion,
    weak_spot_statistic,
)

CONFIRMATORY_SCHEMA_ID = "lupine.y_matrix.confirmatory_report.v1"
DESCRIPTIVE_SCHEMA_ID = "lupine.y_matrix.descriptive_report.v1"
PREREG_DOC = "docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md"
DEFAULT_H2_COSINE_THRESHOLD = 0.7
H1_CRITERION = (
    "pr < null_p05 (below the coupling-aware null band; prereg kill "
    "condition: PR within or above the null band)"
)


def _validate_model_ids(model_ids: Sequence[str]) -> tuple[str, ...]:
    if len(model_ids) < 2 or len(set(model_ids)) != len(model_ids):
        raise InputValidationError(
            f"need >= 2 distinct model_ids, got {model_ids!r}"
        )
    return tuple(model_ids)


def _family_map_dict(family_map: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
    return {family: list(members) for family, members in family_map.items()}


def _guard_cells(matrices: Sequence[ErrorMatrix]) -> list[list[str]]:
    seen: list[list[str]] = []
    for matrix in matrices:
        for cell in matrix.cells:
            if cell.guard_engaged:
                record = [cell.model_id, cell.material, cell.property_name]
                if record not in seen:
                    seen.append(record)
    return seen


def build_confirmatory_report(
    runs: Sequence[RunRecord],
    references: Sequence[ReferenceEntry],
    *,
    model_ids: Sequence[str],
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
    excluded_materials: Sequence[str] = (),
    h3_excluded_cells: Sequence[CellExclusion] = (),
    near_zero_epsilon: float,
    seed: int,
    n_null_draws: int = DEFAULT_N_DRAWS,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    h2_cosine_threshold: float = DEFAULT_H2_COSINE_THRESHOLD,
    h3_pass_ratio: float = DEFAULT_PASS_RATIO,
    h3_kill_ratio: float = DEFAULT_KILL_RATIO,
    defect_properties: Sequence[str] = DEFAULT_DEFECT_PROPERTIES,
    bulk_properties: Sequence[str] = DEFAULT_BULK_PROPERTIES,
) -> dict[str, object]:
    """Run the registered confirmatory analysis and return the ledger report.

    Determinism: a single ``numpy.random.default_rng(seed)`` is consumed in a
    fixed order (H1 nulls per model, H2 cosine null, H3 bootstraps per
    model), so identical inputs and seed reproduce the report bit for bit.
    """
    models = _validate_model_ids(model_ids)
    if not isinstance(seed, int):
        raise InputValidationError(f"seed must be an int, got {seed!r}")
    rng = np.random.default_rng(seed)

    def _matrix(model: str, include: Sequence[str] | None) -> ErrorMatrix:
        return assemble_error_matrix(
            runs,
            references,
            model_id=model,
            properties=properties,
            family_map=family_map,
            method_preference=method_preference,
            excluded_materials=excluded_materials,
            include_materials=include,
            near_zero_epsilon=near_zero_epsilon,
        )

    first_pass = {model: _matrix(model, None) for model in models}
    matched = sorted(
        set(first_pass[models[0]].materials).intersection(
            *[set(first_pass[m].materials) for m in models[1:]]
        )
    )
    if not matched:
        raise InputValidationError(
            "no material survives matched-n across all models; per-model "
            f"exclusions: { {m: first_pass[m].excluded_materials for m in models} !r}"
        )
    matrices = {model: _matrix(model, matched) for model in models}

    h1: dict[str, object] = {}
    for model in models:
        matrix = matrices[model]
        pr = participation_ratio(matrix.values)
        null = pr_null_distribution(
            matrix.values,
            matrix.properties,
            family_map=family_map,
            n_draws=n_null_draws,
            rng=rng,
        )
        h1[model] = {
            "pr": float(pr),
            "null_p05": null.p05,
            "null_p50": null.p50,
            "null_p95": null.p95,
            "n_null_draws": null.n_draws,
            "criterion": H1_CRITERION,
            "pass": bool(pr < null.p05),
        }

    modes = {model: leading_mode(matrices[model].values) for model in models}
    cosine_nulls = leading_mode_cosine_null(
        {model: matrices[model].values for model in models},
        properties,
        family_map=family_map,
        n_draws=n_null_draws,
        rng=rng,
    )
    pairs: dict[str, object] = {}
    pair_passes: list[bool] = []
    for (model_a, model_b), null in cosine_nulls.items():
        cosine = pairwise_cosine(modes[model_a], modes[model_b])
        passed = bool(cosine > h2_cosine_threshold and cosine > null.p95)
        pair_passes.append(passed)
        pairs[f"{model_a}|{model_b}"] = {
            "cosine": float(cosine),
            "null_p95": null.p95,
            "null_p50": null.p50,
            "pass": passed,
        }

    h3_per_model: dict[str, object] = {}
    h3_verdicts: list[str] = []
    for model in models:
        cells = assemble_error_cells(
            runs,
            references,
            model_id=model,
            properties=properties,
            family_map=family_map,
            method_preference=method_preference,
            excluded_materials=excluded_materials,
            near_zero_epsilon=near_zero_epsilon,
        )
        result = weak_spot_statistic(
            cells,
            model_id=model,
            defect_properties=defect_properties,
            bulk_properties=bulk_properties,
            excluded_cells=h3_excluded_cells,
            rng=rng,
            n_bootstrap=n_bootstrap,
            pass_ratio=h3_pass_ratio,
            kill_ratio=h3_kill_ratio,
        )
        h3_verdicts.append(result.verdict)
        h3_per_model[model] = {
            "ratio": result.ratio,
            "ci95": [result.ci_low, result.ci_high],
            "median_abs_error_defect": result.defect_median_abs_error,
            "median_abs_error_bulk": result.bulk_median_abs_error,
            "n_defect_cells": result.n_defect_cells,
            "n_bulk_cells": result.n_bulk_cells,
            "verdict": result.verdict,
        }

    reference_matrix = matrices[models[0]]
    references_used = [
        {
            "material": cell.material,
            "property": cell.property_name,
            "value": cell.reference_value,
            "method": cell.reference_method,
        }
        for cell in reference_matrix.cells
    ]

    return {
        "schema": CONFIRMATORY_SCHEMA_ID,
        "prereg": PREREG_DOC,
        "mode": "confirmatory",
        "seed": seed,
        "n_null_draws": n_null_draws,
        "n_bootstrap": n_bootstrap,
        "near_zero_epsilon": float(near_zero_epsilon),
        "method_preference": list(method_preference),
        "models": list(models),
        "properties": list(properties),
        "family_map": _family_map_dict(family_map),
        "excluded_materials": list(excluded_materials),
        "matched_materials": list(matched),
        "n_materials": len(matched),
        "n_properties": len(properties),
        "material_exclusions": {
            model: [list(pair) for pair in matrices[model].excluded_materials]
            for model in models
        },
        "references_used": references_used,
        "guard_engaged_cells": _guard_cells(list(matrices.values())),
        "h1": h1,
        "h2": {
            "threshold": float(h2_cosine_threshold),
            "pairs": pairs,
            "pass": bool(pair_passes and all(pair_passes)),
        },
        "h3": {
            "pass_ratio": float(h3_pass_ratio),
            "kill_ratio": float(h3_kill_ratio),
            "defect_properties": list(defect_properties),
            "bulk_properties": list(bulk_properties),
            "excluded_cells": [list(e.as_record()) for e in h3_excluded_cells],
            "per_model": h3_per_model,
            "pass": bool(all(v == "pass" for v in h3_verdicts)),
            "kill": bool(any(v == "kill" for v in h3_verdicts)),
        },
    }


def build_descriptive_report(
    runs: Sequence[RunRecord],
    *,
    model_ids: Sequence[str],
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]] = DEFAULT_FAMILY_MAP,
    excluded_materials: Sequence[str] = (),
    near_zero_epsilon: float,
) -> dict[str, object]:
    """Reference-free ensemble-spread report (descriptive; no verdicts)."""
    models = _validate_model_ids(model_ids)
    matrices = assemble_descriptive_matrices(
        runs,
        model_ids=models,
        properties=properties,
        family_map=family_map,
        excluded_materials=excluded_materials,
        near_zero_epsilon=near_zero_epsilon,
    )
    by_model = dict(zip(models, matrices, strict=True))
    modes = {model: leading_mode(by_model[model].values) for model in models}
    pair_cosines = {
        f"{models[i]}|{models[j]}": float(
            pairwise_cosine(modes[models[i]], modes[models[j]])
        )
        for i in range(len(models))
        for j in range(i + 1, len(models))
    }
    first = matrices[0]
    return {
        "schema": DESCRIPTIVE_SCHEMA_ID,
        "prereg": PREREG_DOC,
        "mode": "descriptive",
        "statistic": (
            "cross-model disagreement vectors (deviation from cross-model "
            "mean prediction); ensemble spread only — no reference targets "
            "consumed, no hypothesis verdicts"
        ),
        "near_zero_epsilon": float(near_zero_epsilon),
        "models": list(models),
        "properties": list(properties),
        "family_map": _family_map_dict(family_map),
        "excluded_materials": list(excluded_materials),
        "matched_materials": list(first.materials),
        "n_materials": len(first.materials),
        "n_properties": len(properties),
        "material_exclusions": [list(pair) for pair in first.excluded_materials],
        "guard_engaged_cells": _guard_cells(list(matrices)),
        "pooled_pr": float(participation_ratio(stack_matrices(matrices))),
        "per_model_pr": {
            model: float(participation_ratio(by_model[model].values))
            for model in models
        },
        "pairwise_leading_mode_cosines": pair_cosines,
    }


__all__ = [
    "CONFIRMATORY_SCHEMA_ID",
    "DEFAULT_H2_COSINE_THRESHOLD",
    "DESCRIPTIVE_SCHEMA_ID",
    "H1_CRITERION",
    "PREREG_DOC",
    "build_confirmatory_report",
    "build_descriptive_report",
]
