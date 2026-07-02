"""Uniform serialization envelope for statics result dataclasses.

Every ``*Result.to_dict()`` in the statics core goes through
:func:`result_dict` so downstream consumers (the y-matrix CLI, evidence
assembly) see one shape: property name, values, units, canonical inputs, and
wall time. ``canonical_inputs`` never contains timing — it is the
deterministic, JSON-serializable identity of the run.
"""

from __future__ import annotations

from typing import Mapping


def result_dict(
    property_name: str,
    values: Mapping[str, object],
    units: Mapping[str, str],
    canonical_inputs: Mapping[str, object],
    wall_time_seconds: float,
) -> dict[str, object]:
    """Assemble the shared JSON-serializable result envelope."""
    return {
        "property": property_name,
        "values": dict(values),
        "units": dict(units),
        "canonical_inputs": dict(canonical_inputs),
        "wall_time_seconds": wall_time_seconds,
    }


__all__ = ["result_dict"]
