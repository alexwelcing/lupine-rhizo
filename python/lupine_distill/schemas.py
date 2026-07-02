"""Canonical Pydantic contract for MLIP benchmark results.

This module is the single source of truth for the shared benchmark contract.
Other tracks (glim-think ingest, GCP runners, Lean spec fixtures) reference
``lupine_distill.schemas.BenchmarkResult`` / ``BenchmarkMetrics`` rather than
re-deriving the shape.

Both models are frozen (immutable): construct a new instance to "change" one.
Validation runs at construction, so untrusted JSON is validated at the boundary
via :meth:`BenchmarkResult.model_validate` / ``model_validate_json``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Backend = Literal["torchsim", "ase", "lammps"]
PromotionRecommendation = Literal["promote", "review", "reject"]

# Versioned schema string carried by every LAMMPS evidence payload.
LAMMPS_EVIDENCE_SCHEMA = "lupine.mlip.lammps_evidence.v1"


class BenchmarkMetrics(BaseModel):
    """Per-benchmark accuracy / stability / cost metrics.

    All accuracy fields are optional because a given benchmark only produces a
    subset (e.g. a static-energy benchmark has no ``energy_drift``). ``None``
    means "this benchmark does not produce this metric", not "zero".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Accuracy vs DFT reference (lower is better).
    mae_energy: float | None = Field(default=None, description="MAE energy, eV/atom")
    mae_forces: float | None = Field(default=None, description="MAE forces, eV/Ang")
    mae_stress: float | None = Field(default=None, description="MAE stress, GPa")
    rmse_energy: float | None = Field(default=None, description="RMSE energy, eV/atom")

    # Dynamics stability (lower drift is better; closer-to-target temp is better).
    energy_drift: float | None = Field(default=None, description="Energy drift, eV/atom/ps")
    temperature_stability: float | None = Field(default=None, description="Temp stability, K")

    # Provenance + cost.
    dft_reference: dict[str, float] | None = Field(
        default=None, description="DFT reference values keyed by quantity"
    )
    wall_time_seconds: float = Field(..., ge=0.0, description="Wall-clock seconds for this benchmark")
    gpu_utilization_pct: float | None = Field(
        default=None, ge=0.0, le=100.0, description="Mean GPU utilization, percent"
    )


class BenchmarkResult(BaseModel):
    """A full benchmark-suite run for one (model, distill version, backend)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str = Field(..., min_length=1)
    distill_version: int = Field(..., ge=0, description="0 == teacher baseline")
    backend: Backend
    timestamp: datetime
    torchsim_version: str = Field(..., min_length=1)
    benchmark_suite_version: str = Field(..., min_length=1)

    # Map of benchmark name -> metrics. Empty is allowed (e.g. a failed run).
    results: dict[str, BenchmarkMetrics] = Field(default_factory=dict)

    # Populated only by the uplift report; a raw single-version run leaves these None.
    overall_uplift_pct: float | None = None
    promotion_recommendation: PromotionRecommendation | None = None


class LammpsSource(BaseModel):
    """Origin of a LAMMPS evidence payload: potential + driver script identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    potential_id: str = Field(..., min_length=1, description="Potential id, e.g. 'Ni_u3.eam'")
    lammps_version: str | None = Field(
        default=None, description="LAMMPS banner line, e.g. 'LAMMPS (2 Aug 2023 - Update 3)'"
    )
    input_script: str | None = Field(
        default=None, description="Driver input script name, e.g. 'in.elastic'"
    )


class LammpsPropertyValue(BaseModel):
    """One physical property extracted from a LAMMPS log, with optional reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., min_length=1, description="Property name, e.g. 'C11'")
    value: float
    unit: str = Field(..., min_length=1, description="Unit, e.g. 'GPa', 'eV', 'Angstrom'")
    reference_value: float | None = Field(
        default=None, description="Caller-supplied reference (experiment / DFT), same unit"
    )
    reference_source: str | None = Field(
        default=None, description="Citation for the reference value"
    )


class LammpsProvenance(BaseModel):
    """Provenance of the parsed log: content hash suffices, timestamp is optional."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    log_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    log_name: str | None = Field(default=None, description="Basename of the parsed log file")
    parsed_at: datetime | None = Field(
        default=None, description="Caller-supplied parse timestamp (never read from the clock)"
    )


class LammpsTrajectorySummary(BaseModel):
    """Modest summary of one LAMMPS thermo section (not a full log parse)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    n_rows: int = Field(..., ge=1, description="Thermo rows in the section")
    first_step: int
    last_step: int
    columns: list[str] = Field(..., min_length=1)
    energy_column: str | None = Field(
        default=None, description="Column used for drift: 'PotEng' preferred, else 'TotEng'"
    )
    initial_energy: float | None = None
    final_energy: float | None = None
    energy_drift_per_step: float | None = Field(
        default=None,
        description="(final - initial) energy / step span, raw log units (no /atom or /ps "
        "normalization; thermo alone does not carry timestep or atom count)",
    )
    final_values: dict[str, float] = Field(
        default_factory=dict, description="Last-row value per column (Step excluded)"
    )


class LammpsEvidence(BaseModel):
    """A ``lupine.mlip.lammps_evidence.v1`` payload: one LAMMPS log turned into
    versioned, reference-annotated property evidence.

    Serialize with ``by_alias=True`` so the JSON carries the conventional
    ``"schema"`` key (``schema`` itself shadows a ``BaseModel`` attribute).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    schema_version: Literal["lupine.mlip.lammps_evidence.v1"] = Field(
        default=LAMMPS_EVIDENCE_SCHEMA, alias="schema"
    )
    material: str = Field(..., min_length=1, description="Element / material, e.g. 'Ni'")
    source: LammpsSource
    properties: list[LammpsPropertyValue] = Field(default_factory=list)
    trajectory: LammpsTrajectorySummary | None = None
    provenance: LammpsProvenance


__all__ = [
    "LAMMPS_EVIDENCE_SCHEMA",
    "Backend",
    "BenchmarkMetrics",
    "BenchmarkResult",
    "LammpsEvidence",
    "LammpsPropertyValue",
    "LammpsProvenance",
    "LammpsSource",
    "LammpsTrajectorySummary",
    "PromotionRecommendation",
]
