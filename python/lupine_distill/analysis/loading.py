"""Loaders for Y-matrix sweep results and reference targets.

Runs: ``lupine.statics_run.v1`` JSON emitted to ``data/y_matrix_runs/`` by the
statics CLI; predictions are extracted into canonical property names
(``families.CANONICAL_PROPERTIES``). Targets: ``lupine.y_matrix_targets.v1``
compilations; target property names are translated through a caller-supplied
map (default :data:`families.DEFAULT_TARGET_PROPERTY_MAP`), and unmapped
names are recorded rather than guessed. No paths are hardcoded here — every
loader takes the directory or payload from the caller.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.families import DEFAULT_TARGET_PROPERTY_MAP

RUN_SCHEMA_ID = "lupine.statics_run.v1"
TARGETS_SCHEMA_ID = "lupine.y_matrix_targets.v1"


@dataclass(frozen=True)
class RunRecord:
    """One sweep cell: a (material, structure, model) with its predictions."""

    material: str
    structure_type: str
    model_id: str
    predictions: Mapping[str, float]
    source_path: str

    def __post_init__(self) -> None:
        for name in ("material", "structure_type", "model_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise InputValidationError(
                    f"RunRecord.{name} must be a non-empty string, got {value!r}"
                )
        for prop, value in dict(self.predictions).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise InputValidationError(
                    f"RunRecord({self.material}/{self.model_id}) prediction "
                    f"{prop!r} is not finite: {value!r}"
                )
        object.__setattr__(
            self, "predictions", MappingProxyType(dict(self.predictions))
        )


@dataclass(frozen=True)
class ReferenceEntry:
    """One reference value from a targets compilation (one method, one cite)."""

    material: str
    structure: str
    property_name: str
    value: float
    unit: str
    method: str
    uncertainty: float | None
    citation: str
    family_label: str

    def __post_init__(self) -> None:
        for name in ("material", "structure", "property_name", "method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise InputValidationError(
                    f"ReferenceEntry.{name} must be a non-empty string, got {value!r}"
                )
        if not isinstance(self.value, (int, float)) or not math.isfinite(self.value):
            raise InputValidationError(
                f"ReferenceEntry({self.material}/{self.property_name}) value "
                f"is not finite: {self.value!r}"
            )
        if self.uncertainty is not None and (
            not isinstance(self.uncertainty, (int, float))
            or not math.isfinite(self.uncertainty)
            or self.uncertainty <= 0.0
        ):
            raise InputValidationError(
                f"ReferenceEntry({self.material}/{self.property_name}) "
                f"uncertainty must be a positive finite number or None, "
                f"got {self.uncertainty!r}"
            )


@dataclass(frozen=True)
class TargetLoadResult:
    """Parsed reference entries plus the raw property names left unmapped."""

    entries: tuple[ReferenceEntry, ...]
    unmapped_properties: tuple[str, ...] = field(default=())


def _require(payload: Mapping[str, object], key: str, source: str) -> object:
    if key not in payload:
        raise InputValidationError(f"{source}: missing required key {key!r}")
    return payload[key]


def _values_of(section: object) -> Mapping[str, object]:
    if isinstance(section, Mapping):
        values = section.get("values")
        if isinstance(values, Mapping):
            return values
    return {}


def _extract_predictions(results: Mapping[str, object]) -> dict[str, float]:
    """Map a statics_run results block to canonical property -> value."""
    preds: dict[str, float] = {}
    scalar_paths = {
        "a0": ("lattice", "a0_angstrom"),
        "b0": ("eos", "b0_gpa"),
        "b0_prime": ("eos", "b0_prime"),
        "e_vac": ("vacancy", "vacancy_formation_ev"),
        "gamma_sfe": ("sfe", "sfe_mj_per_m2"),
        "dh_f": ("formation", "formation_enthalpy_ev_per_atom"),
    }
    for canonical, (section, key) in scalar_paths.items():
        value = _values_of(results.get(section)).get(key)
        if isinstance(value, (int, float)):
            preds[canonical] = float(value)
    surfaces = results.get("surfaces")
    if isinstance(surfaces, list):
        for surface in surfaces:
            values = _values_of(surface)
            gamma = values.get("gamma_j_per_m2")
            miller = values.get("miller")
            if isinstance(gamma, (int, float)) and isinstance(miller, str):
                preds[f"gamma_{miller}"] = float(gamma)
    return preds


def parse_run_payload(
    payload: Mapping[str, object], *, source: str = "<memory>"
) -> RunRecord:
    """Parse one statics_run payload into a :class:`RunRecord` (fail fast)."""
    if not isinstance(payload, Mapping):
        raise InputValidationError(f"{source}: run payload must be a mapping")
    results = _require(payload, "results", source)
    if not isinstance(results, Mapping):
        raise InputValidationError(f"{source}: 'results' must be a mapping")
    return RunRecord(
        material=str(_require(payload, "material", source)),
        structure_type=str(_require(payload, "structure_type", source)),
        model_id=str(_require(payload, "model_id", source)),
        predictions=_extract_predictions(results),
        source_path=source,
    )


def load_run_directory(directory: Path) -> tuple[RunRecord, ...]:
    """Load every ``lupine.statics_run.v1`` file in ``directory``.

    Files with other schemas (e.g. ``lupine.mlip.calc_evidence.v1`` evidence
    companions) are skipped. Duplicate (material, structure, model) cells are
    an error: the sweep must be unambiguous before analysis.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise InputValidationError(f"run directory does not exist: {directory}")
    records: list[RunRecord] = []
    seen: dict[tuple[str, str, str], str] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"cannot read run file {path}: {exc}") from exc
        if not isinstance(payload, Mapping) or payload.get("schema") != RUN_SCHEMA_ID:
            continue
        record = parse_run_payload(payload, source=str(path))
        key = (record.material, record.structure_type, record.model_id)
        if key in seen:
            raise InputValidationError(
                f"duplicate run cell {key!r} in {path} (already in {seen[key]})"
            )
        seen[key] = str(path)
        records.append(record)
    return tuple(records)


def parse_targets_payload(
    payload: Mapping[str, object],
    *,
    source: str = "<memory>",
    property_map: Mapping[str, str] = DEFAULT_TARGET_PROPERTY_MAP,
) -> TargetLoadResult:
    """Parse one targets compilation into reference entries (fail fast)."""
    if not isinstance(payload, Mapping):
        raise InputValidationError(f"{source}: targets payload must be a mapping")
    if payload.get("schema") != TARGETS_SCHEMA_ID:
        raise InputValidationError(
            f"{source}: expected schema {TARGETS_SCHEMA_ID!r}, "
            f"got {payload.get('schema')!r}"
        )
    family_label = str(payload.get("family", ""))
    raw_entries = _require(payload, "entries", source)
    if not isinstance(raw_entries, list):
        raise InputValidationError(f"{source}: 'entries' must be a list")
    entries: list[ReferenceEntry] = []
    unmapped: list[str] = []
    for index, raw in enumerate(raw_entries):
        where = f"{source} entries[{index}]"
        if not isinstance(raw, Mapping):
            raise InputValidationError(f"{where}: entry must be a mapping")
        raw_property = str(_require(raw, "property", where))
        canonical = property_map.get(raw_property)
        if canonical is None:
            if raw_property not in unmapped:
                unmapped.append(raw_property)
            continue
        source_block = raw.get("source")
        citation = ""
        if isinstance(source_block, Mapping):
            citation = str(source_block.get("citation", ""))
        raw_uncertainty = raw.get("uncertainty")
        entries.append(
            ReferenceEntry(
                material=str(_require(raw, "material", where)),
                structure=str(_require(raw, "structure", where)),
                property_name=canonical,
                value=float(_require(raw, "value", where)),  # type: ignore[arg-type]
                unit=str(_require(raw, "unit", where)),
                method=str(_require(raw, "method", where)),
                uncertainty=(
                    float(raw_uncertainty)  # type: ignore[arg-type]
                    if raw_uncertainty is not None
                    else None
                ),
                citation=citation,
                family_label=family_label,
            )
        )
    return TargetLoadResult(entries=tuple(entries), unmapped_properties=tuple(unmapped))


def load_targets_directory(
    directory: Path,
    *,
    property_map: Mapping[str, str] = DEFAULT_TARGET_PROPERTY_MAP,
) -> TargetLoadResult:
    """Load and merge every targets compilation in ``directory``."""
    directory = Path(directory)
    if not directory.is_dir():
        raise InputValidationError(f"targets directory does not exist: {directory}")
    all_entries: list[ReferenceEntry] = []
    all_unmapped: list[str] = []
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(
                f"cannot read targets file {path}: {exc}"
            ) from exc
        result = parse_targets_payload(
            payload, source=str(path), property_map=property_map
        )
        all_entries.extend(result.entries)
        for name in result.unmapped_properties:
            if name not in all_unmapped:
                all_unmapped.append(name)
    return TargetLoadResult(
        entries=tuple(all_entries), unmapped_properties=tuple(all_unmapped)
    )


def load_run_records(paths: Iterable[Path]) -> tuple[RunRecord, ...]:
    """Load specific run files (schema-checked, duplicates rejected)."""
    records: list[RunRecord] = []
    seen: dict[tuple[str, str, str], str] = {}
    for path in paths:
        path = Path(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"cannot read run file {path}: {exc}") from exc
        if not isinstance(payload, Mapping) or payload.get("schema") != RUN_SCHEMA_ID:
            raise InputValidationError(f"{path}: not a {RUN_SCHEMA_ID} payload")
        record = parse_run_payload(payload, source=str(path))
        key = (record.material, record.structure_type, record.model_id)
        if key in seen:
            raise InputValidationError(
                f"duplicate run cell {key!r} in {path} (already in {seen[key]})"
            )
        seen[key] = str(path)
        records.append(record)
    return tuple(records)


__all__ = [
    "RUN_SCHEMA_ID",
    "TARGETS_SCHEMA_ID",
    "ReferenceEntry",
    "RunRecord",
    "TargetLoadResult",
    "load_run_directory",
    "load_run_records",
    "load_targets_directory",
    "parse_run_payload",
    "parse_targets_payload",
]
