"""Bind compiled reference targets onto Y-matrix sweep evidence payloads.

The 2026-07-01 statics sweep wrote ``lupine.mlip.calc_evidence.v1`` payloads
with no ``reference_value`` (references were compiled separately, after the
runs). This module joins those payloads with the reference targets in
``data/y_matrix_targets/*.json`` (schema ``lupine.y_matrix_targets.v1``)
under the **registered** binding policy
(docs/plans/y-matrix-cross-property-preregistration-2026-07-01.md,
§Reference targets and binding policy):

* the confirmatory reference per property is the **DFT-PBE value when
  available, else experiment** (:data:`METHOD_PREFERENCE`);
* an unresolved reference leaves the property **unbound** — excluded from
  confirmatory analysis, still reported;
* nothing is ever silently dropped: every evidence property gets a
  :class:`PropertyBindingRecord` with an explicit status.

Binding is pure surgery on frozen pydantic models: matched properties are
rebuilt with ``model_copy(update=...)`` and the payload is rebuilt the same
way, so ``provenance`` (including ``inputs_sha256``) is carried over
**byte-identical** — the run inputs did not change, only annotations were
added. ``lupine_distill.calc_evidence.build_calc_evidence`` is deliberately
NOT used here: it recomputes the hash from a full ``inputs`` mapping that the
evidence payload does not carry (only the hash survives serialization), so it
cannot reproduce the original provenance.

Name vocabulary: the statics runner emits short names (``B0``,
``gamma_100``, ``stacking_fault_energy``) while the compiled targets use long
descriptive names (``bulk_modulus_0K_extrapolated``, ``surface_energy_100``,
``intrinsic_stacking_fault_energy``). :data:`PROPERTY_NAME_MAP` is the single
explicit bridge; unmapped evidence names fail fast in strict mode and are
recorded as ``skipped_unmapped`` otherwise.

Tolerance policy: bound properties keep ``tolerance=None`` (the Lean emitter's
default — ``tolerance_pct`` of ``|reference|`` — applies) EXCEPT near-zero
references where the percentage rule is degenerate. For evidence properties
with a configured absolute floor (:data:`TOLERANCE_FLOORS`; default: only
``stacking_fault_energy`` at 10 mJ/m^2), the explicit tolerance
``max(tolerance_pct% of |ref|, floor)`` is set whenever the floor binds
(i.e. exceeds the percentage tolerance); when the percentage dominates, the
default ``None`` is kept so behavior is unchanged.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .schemas import CalcEvidence, PropertyValue

# Versioned schema string carried by every compiled reference-target file.
Y_MATRIX_TARGETS_SCHEMA = "lupine.y_matrix_targets.v1"

# Registered method preference: DFT-PBE when available, else experiment.
# Entries with any other method never bind (recorded, not silently used).
METHOD_PREFERENCE: tuple[str, ...] = ("DFT-PBE", "experiment")

# Property names the statics runner emits (python/scripts/run_y_matrix_statics.py
# --evidence-out). Kept explicit so the mapping table below is checkable.
STATICS_EVIDENCE_PROPERTY_NAMES: tuple[str, ...] = (
    "a0",
    "cohesive_energy",
    "B0",
    "B0_prime",
    "vacancy_formation_energy",
    "gamma_100",
    "gamma_110",
    "gamma_111",
    "stacking_fault_energy",
    "formation_enthalpy",
)

# Evidence property name -> candidate target property names, in preference
# order. Order matters only WITHIN a method tier (method preference dominates):
# statics values are 0 K quantities, so e.g. an experimental 0K-extrapolated
# bulk modulus outranks the 300 K one. Names not present in any compiled
# target file (e.g. cohesive_energy, formation_enthalpy as of 2026-07-01)
# are still mapped so they resolve to a clean "unbound" rather than "unmapped"
# when their target families land.
PROPERTY_NAME_MAP: Mapping[str, tuple[str, ...]] = {
    "a0": ("lattice_constant_a",),
    "cohesive_energy": ("cohesive_energy",),
    "B0": (
        "bulk_modulus",  # DFT-PBE name in beyond_metals.json
        "bulk_modulus_0K_extrapolated",
        "bulk_modulus_300K",
        "bulk_modulus_isothermal_300K",
        "bulk_modulus_adiabatic_300K",
    ),
    "B0_prime": ("bulk_modulus_pressure_derivative",),
    "vacancy_formation_energy": ("vacancy_formation_energy",),
    "gamma_100": ("surface_energy_100",),
    "gamma_110": ("surface_energy_110",),
    "gamma_111": ("surface_energy_111",),
    "stacking_fault_energy": ("intrinsic_stacking_fault_energy",),
    "formation_enthalpy": ("formation_enthalpy",),
    # Finite-T lane (Tier 2, separate registration) — mapped ahead of time so
    # finite-T evidence binds without a code change when it lands.
    "melting_point": ("melting_point",),
    "thermal_expansion": ("linear_thermal_expansion_coefficient_300K",),
}

# Absolute tolerance floors (same unit as the evidence value), keyed by
# EVIDENCE property name. Applied only when the floor exceeds the default
# percentage tolerance — see module docstring. Default: SFE floor 10 mJ/m^2
# (5% of a ~10-170 mJ/m^2 reference is degenerate); no floor elsewhere.
TOLERANCE_FLOORS: Mapping[str, float] = {
    "stacking_fault_energy": 10.0,
}

BindingStatus = Literal[
    "bound",
    "unbound",
    "skipped_unmapped",
    "skipped_unit_mismatch",
    "skipped_ambiguous",
]


class UnmappedPropertyError(ValueError):
    """An evidence property name is absent from :data:`PROPERTY_NAME_MAP` (strict mode)."""


class TargetSource(BaseModel):
    """Citation block of one reference-target entry."""

    model_config = ConfigDict(frozen=True, extra="allow")

    citation: str = Field(..., min_length=1)
    doi_or_url: str | None = None
    notes: str | None = None


class TargetEntry(BaseModel):
    """One compiled reference value for (material, structure, property).

    ``family`` is not stored in the target files' entries; the loader stamps
    it from the enclosing file. Extra keys are tolerated (forward-compatible
    within v1) but the core fields are validated at the boundary.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    material: str = Field(..., min_length=1)
    structure: str = Field(..., min_length=1)
    property: str = Field(..., min_length=1)
    value: float
    unit: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    source: TargetSource
    family: str | None = None


class TargetFile(BaseModel):
    """A ``lupine.y_matrix_targets.v1`` file: one family of entries."""

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    schema_version: Literal["lupine.y_matrix_targets.v1"] = Field(
        default=Y_MATRIX_TARGETS_SCHEMA, alias="schema"
    )
    family: str = Field(..., min_length=1)
    entries: tuple[TargetEntry, ...] = ()


@dataclass(frozen=True)
class BindingConfig:
    """Knobs of the binder; defaults match the registered policy."""

    tolerance_pct: float = 5.0
    strict: bool = False
    property_map: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: PROPERTY_NAME_MAP)
    tolerance_floors: Mapping[str, float] = field(default_factory=lambda: TOLERANCE_FLOORS)
    method_preference: tuple[str, ...] = METHOD_PREFERENCE


DEFAULT_CONFIG = BindingConfig()


@dataclass(frozen=True)
class PropertyBindingRecord:
    """Per-property outcome: what happened and why, never silent."""

    name: str
    status: BindingStatus
    method: str | None = None
    target_property: str | None = None
    family: str | None = None
    reference_value: float | None = None
    tolerance: float | None = None
    reference_source: str | None = None
    detail: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "method": self.method,
            "target_property": self.target_property,
            "family": self.family,
            "reference_value": self.reference_value,
            "tolerance": self.tolerance,
            "reference_source": self.reference_source,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class BindingResult:
    """A newly constructed (never mutated) payload plus its full audit trail."""

    evidence: CalcEvidence
    records: tuple[PropertyBindingRecord, ...]

    @property
    def counts(self) -> dict[str, int]:
        buckets = {"bound": 0, "unbound": 0, "skipped": 0}
        for record in self.records:
            key = record.status if record.status in ("bound", "unbound") else "skipped"
            buckets[key] += 1
        return buckets


def load_targets(targets_dir: pathlib.Path | str) -> tuple[TargetEntry, ...]:
    """Load and validate every ``*.json`` target file in ``targets_dir``.

    Returns all entries merged, each stamped with its file's ``family``.
    Raises ``ValueError`` naming the offending file on invalid JSON or a
    schema violation, and when the directory has no target files at all
    (an empty reference set is a setup error, not "everything unbound").
    """

    directory = pathlib.Path(targets_dir)
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not paths:
        raise ValueError(f"no target files (*.json) found in {directory}")
    entries: list[TargetEntry] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            target_file = TargetFile.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid targets file {path.name}: {exc}") from exc
        entries.extend(
            entry.model_copy(update={"family": target_file.family})
            for entry in target_file.entries
        )
    return tuple(entries)


def compute_tolerance(
    evidence_name: str, reference_value: float, config: BindingConfig = DEFAULT_CONFIG
) -> float | None:
    """Explicit absolute tolerance for a bound property, or ``None`` for the default.

    ``None`` keeps the Lean emitter's percentage-of-reference rule. A
    configured floor is returned only when it exceeds that percentage
    tolerance (the near-zero-reference guard); otherwise the default stands.
    """

    floor = config.tolerance_floors.get(evidence_name)
    if floor is None:
        return None
    pct_tolerance = config.tolerance_pct / 100.0 * abs(reference_value)
    return floor if floor > pct_tolerance else None


def _select_target(
    prop: PropertyValue,
    candidate_names: Sequence[str],
    material: str,
    structure: str | None,
    targets: Sequence[TargetEntry],
    config: BindingConfig,
) -> tuple[TargetEntry | None, BindingStatus, str | None]:
    """Pick the reference entry for one evidence property.

    Match on material + structure + candidate property name (structure
    compared case-insensitively: statics evidence carries lowercase
    'b2'/'l12' while compiled targets spell 'B2'/'L12'), filter to
    unit-compatible entries (case-insensitive exact string), then apply the
    registered method preference; ties within a method tier resolve by
    candidate-name order, and residual ties are reported as ambiguous —
    never silently picked.
    """

    pool = [
        entry
        for entry in targets
        if entry.material == material
        and structure is not None
        and entry.structure.lower() == structure.lower()
        and entry.property in candidate_names
    ]
    if not pool:
        return None, "unbound", None

    unit_ok = [entry for entry in pool if entry.unit.lower() == prop.unit.lower()]
    if not unit_ok:
        units = sorted({entry.unit for entry in pool})
        return None, "skipped_unit_mismatch", (
            f"target unit(s) {units} do not match evidence unit '{prop.unit}'"
        )

    tier = next(
        (
            [entry for entry in unit_ok if entry.method == method]
            for method in config.method_preference
            if any(entry.method == method for entry in unit_ok)
        ),
        None,
    )
    if tier is None:
        methods = sorted({entry.method for entry in unit_ok})
        return None, "unbound", (
            f"target entries exist but none with a registered method "
            f"{list(config.method_preference)} (found {methods})"
        )

    best_rank = min(candidate_names.index(entry.property) for entry in tier)
    best = [entry for entry in tier if candidate_names.index(entry.property) == best_rank]
    if len(best) > 1:
        cites = [entry.source.citation for entry in best]
        return None, "skipped_ambiguous", (
            f"{len(best)} equally preferred '{best[0].property}' entries "
            f"({best[0].method}); refusing to pick silently: {cites}"
        )
    return best[0], "bound", None


def bind_evidence(
    evidence: CalcEvidence,
    *,
    structure: str | None,
    targets: Sequence[TargetEntry],
    config: BindingConfig = DEFAULT_CONFIG,
) -> BindingResult:
    """Bind reference targets onto one evidence payload.

    Returns a **new** payload (the input is frozen and never mutated) whose
    matched properties carry ``reference_value`` / ``reference_source`` (the
    citation string) / ``tolerance`` per the policy, plus one record per
    property. ``structure=None`` (unresolvable) binds nothing — structure-aware
    matching is mandatory. Strict mode raises :class:`UnmappedPropertyError`
    on the first evidence property name missing from the map.
    """

    new_properties: list[PropertyValue] = []
    records: list[PropertyBindingRecord] = []
    for prop in evidence.properties:
        candidate_names = config.property_map.get(prop.name)
        if candidate_names is None:
            if config.strict:
                raise UnmappedPropertyError(
                    f"evidence property '{prop.name}' ({evidence.material}) is not in "
                    f"the property-name map; add it to PROPERTY_NAME_MAP or drop --strict"
                )
            new_properties.append(prop)
            records.append(
                PropertyBindingRecord(
                    name=prop.name,
                    status="skipped_unmapped",
                    detail="evidence property name not in PROPERTY_NAME_MAP",
                )
            )
            continue

        entry, status, detail = _select_target(
            prop, candidate_names, evidence.material, structure, targets, config
        )
        if entry is None:
            new_properties.append(prop)
            records.append(PropertyBindingRecord(name=prop.name, status=status, detail=detail))
            continue

        tolerance = compute_tolerance(prop.name, entry.value, config)
        new_properties.append(
            prop.model_copy(
                update={
                    "reference_value": entry.value,
                    "reference_source": entry.source.citation,
                    "tolerance": tolerance,
                }
            )
        )
        records.append(
            PropertyBindingRecord(
                name=prop.name,
                status="bound",
                method=entry.method,
                target_property=entry.property,
                family=entry.family,
                reference_value=entry.value,
                tolerance=tolerance,
                reference_source=entry.source.citation,
            )
        )

    return BindingResult(
        evidence=evidence.model_copy(update={"properties": new_properties}),
        records=tuple(records),
    )


def resolve_structure(evidence_path: pathlib.Path | str, material: str) -> str | None:
    """Resolve the crystal structure for an evidence file (payloads do not carry it).

    Preference order:

    1. the sibling statics-run JSON (``X.evidence.json`` -> ``X.json``,
       ``structure_type`` field) — authoritative, written by the same run;
    2. the sweep filename convention ``<material>_<structure>_<model>...``,
       accepted only when the filename's material token matches ``material``.

    Returns ``None`` when neither source resolves; callers must then leave
    the payload entirely unbound (recorded, never guessed).
    """

    path = pathlib.Path(evidence_path)
    if path.name.endswith(".evidence.json"):
        sibling = path.with_name(path.name.removesuffix(".evidence.json") + ".json")
        try:
            payload = json.loads(sibling.read_text(encoding="utf-8"))
            structure = payload.get("structure_type")
            if isinstance(structure, str) and structure:
                return structure
        except (OSError, json.JSONDecodeError):
            pass

    stem = path.name.removesuffix(".evidence.json").removesuffix(".json")
    tokens = stem.split("_")
    if len(tokens) >= 3 and tokens[0] == material and tokens[1]:
        return tokens[1]
    return None


__all__ = [
    "DEFAULT_CONFIG",
    "METHOD_PREFERENCE",
    "PROPERTY_NAME_MAP",
    "STATICS_EVIDENCE_PROPERTY_NAMES",
    "TOLERANCE_FLOORS",
    "Y_MATRIX_TARGETS_SCHEMA",
    "BindingConfig",
    "BindingResult",
    "PropertyBindingRecord",
    "TargetEntry",
    "TargetFile",
    "TargetSource",
    "UnmappedPropertyError",
    "bind_evidence",
    "compute_tolerance",
    "load_targets",
    "resolve_structure",
]
