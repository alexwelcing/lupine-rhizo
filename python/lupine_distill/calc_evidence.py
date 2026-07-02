"""ASE-calculator/GPU evidence assembly: run results -> ``calc_evidence.v1``.

The calculator lane mirrors the LAMMPS one (:mod:`lupine_distill.lammps_ingest`)
but starts from in-memory results instead of a log file: a runner computes
properties with an ASE calculator (MACE, torchsim, ...) and hands them here as
:class:`~lupine_distill.schemas.PropertyValue` instances. Provenance is the
sha256 of the *canonical JSON* of the run inputs (structure + settings), so the
same inputs always hash identically regardless of dict ordering; ``computed_at``
is recorded only when the caller supplies it (this module never reads the
clock — same discipline as ``LammpsProvenance``).

Emission to Lean reuses :func:`lupine_distill.lammps_ingest.emit_lean_module`,
which accepts ``CalcEvidence`` payloads directly.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import datetime

from .schemas import (
    Backend,
    CalcEvidence,
    CalcProvenance,
    CalcSource,
    Device,
    PropertyValue,
)


def canonical_inputs_sha256(inputs: Mapping[str, object]) -> str:
    """sha256 hex digest of the canonical JSON serialization of ``inputs``.

    Canonical means sorted keys, minimal separators, no ASCII escaping, and no
    NaN/Infinity (they are not valid JSON and would break cross-tool hashing).
    Raises ``ValueError`` naming the problem if ``inputs`` is not representable
    as canonical JSON.
    """

    try:
        canonical = json.dumps(
            dict(inputs),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"inputs are not canonical-JSON serializable (need plain JSON types, "
            f"no NaN/Infinity): {exc}"
        ) from exc
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_calc_evidence(
    *,
    material: str,
    model_id: str,
    device: Device,
    inputs: Mapping[str, object],
    properties: Iterable[PropertyValue],
    backend: Backend = "ase",
    calculator_version: str | None = None,
    run_label: str | None = None,
    computed_at: datetime | None = None,
) -> CalcEvidence:
    """Assemble a ``lupine.mlip.calc_evidence.v1`` payload.

    ``inputs`` is the caller's full run description (structure identity plus
    calculator settings); it is hashed via :func:`canonical_inputs_sha256` and
    only the hash is stored. ``properties`` are ready-made
    :class:`~lupine_distill.schemas.PropertyValue` instances — include
    ``reference_value`` (and optionally an explicit absolute ``tolerance``) on
    any property that should become a Lean theorem. ``computed_at`` is recorded
    only if given (never the clock).
    """

    return CalcEvidence(
        material=material,
        source=CalcSource(
            model_id=model_id,
            backend=backend,
            device=device,
            calculator_version=calculator_version,
        ),
        properties=list(properties),
        provenance=CalcProvenance(
            inputs_sha256=canonical_inputs_sha256(inputs),
            run_label=run_label,
            computed_at=computed_at,
        ),
    )


__all__ = [
    "build_calc_evidence",
    "canonical_inputs_sha256",
]
