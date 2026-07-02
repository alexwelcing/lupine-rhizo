"""Reference binding for the Y-matrix analysis (prereg binding policy).

Registered policy: where DFT and experimental references both exist, the
confirmatory target per property is the DFT-PBE value when available, else
experiment (chosen to match the MP/MPtrj training provenance of the model
grid). The preference order is data — callers may override it — and
:data:`families.DEFAULT_METHOD_PREFERENCE` is the registered default.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import (
    DEFAULT_METHOD_PREFERENCE,
    require_properties_in_family_map,
)
from lupine_distill.analysis.loading import ReferenceEntry


def select_references(
    entries: Sequence[ReferenceEntry],
    *,
    method_preference: Sequence[str] = DEFAULT_METHOD_PREFERENCE,
) -> dict[tuple[str, str, str], ReferenceEntry]:
    """Bind one reference per (material, structure, property).

    Registered policy: first method in ``method_preference`` that has an
    entry wins (default: DFT-PBE, else experiment). Two entries with the
    same (material, structure, property, method) are ambiguous — fail fast.
    """
    if not method_preference:
        raise InputValidationError("method_preference must not be empty")
    by_method: dict[tuple[str, str, str, str], ReferenceEntry] = {}
    for entry in entries:
        key = (
            entry.material,
            entry.structure.lower(),
            entry.property_name,
            entry.method,
        )
        if key in by_method:
            raise InputValidationError(
                f"ambiguous duplicate reference for {key!r}: "
                f"{by_method[key].value} vs {entry.value}"
            )
        by_method[key] = entry
    bound: dict[tuple[str, str, str], ReferenceEntry] = {}
    for material, structure, prop, _method in by_method:
        cell = (material, structure, prop)
        if cell in bound:
            continue
        for method in method_preference:
            entry = by_method.get((material, structure, prop, method))
            if entry is not None:
                bound[cell] = entry
                break
    return bound


def family_reference_scales(
    bound_values: Mapping[tuple[str, str], float],
    properties: Sequence[str],
    family_map: Mapping[str, Sequence[str]],
) -> dict[str, float]:
    """Median ``|ref|`` per family over the bound (material, property) values.

    This is the guard denominator from prereg H1: properties whose reference
    is degenerate (near zero) use absolute error scaled by the family's
    median ``|ref|``.
    """
    prop_to_family = require_properties_in_family_map(properties, family_map)
    per_family: dict[str, list[float]] = {}
    for (_material, prop), value in bound_values.items():
        family = prop_to_family.get(prop)
        if family is not None:
            per_family.setdefault(family, []).append(abs(value))
    return {
        family: float(np.median(values)) for family, values in per_family.items()
    }


__all__ = [
    "family_reference_scales",
    "select_references",
]
