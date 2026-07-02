"""LAMMPS file-evidence benchmark backend.

Unlike the TorchSim backend this does not drive a simulation: LAMMPS campaigns
run on the lab's own cluster, and what crosses the boundary is a directory of
``lupine.mlip.lammps_evidence.v1`` JSON payloads produced by
``lupine_distill.lammps_ingest``. This backend maps the property abs errors vs
their caller-supplied references into the standard :class:`BenchmarkMetrics`
shape so downstream aggregation (uplift, reports) is backend-agnostic.

CPU-importable, no heavy deps (json + pydantic only).
"""

from __future__ import annotations

import pathlib
from statistics import fmean

from ..schemas import BenchmarkMetrics, LammpsEvidence
from ..suite import BENCHMARK_WEIGHTS
from .base import BenchmarkBackend, System

# Reported when no payload carries a LAMMPS banner line.
_LAMMPS_VERSION_UNKNOWN = "lammps-log-unknown"


class LammpsEvidenceBackend(BenchmarkBackend):
    """Score precomputed LAMMPS evidence payloads against their references."""

    backend_id = "lammps"

    def __init__(self, *, evidence_dir: pathlib.Path | str) -> None:
        root = pathlib.Path(evidence_dir)
        paths = sorted(root.glob("*.json"))
        if not paths:
            raise ValueError(
                f"no lammps_evidence.v1 JSON payloads found in {root} "
                "(produce them with: python3 -m lupine_distill.lammps_ingest parse ...)"
            )
        # Validate every payload at the boundary; a malformed file fails loud here.
        self._payloads = [
            LammpsEvidence.model_validate_json(p.read_text(encoding="utf-8")) for p in paths
        ]

    @property
    def engine_version(self) -> str:
        for payload in self._payloads:
            if payload.source.lammps_version:
                return payload.source.lammps_version
        return _LAMMPS_VERSION_UNKNOWN

    def run(self, system: System, benchmark: str) -> BenchmarkMetrics:
        """Map evidence abs errors onto the metrics ``benchmark`` weights.

        ``system`` is ignored (the structures already ran on the lab cluster);
        it is never mutated. Stress-like errors come from GPa properties with
        references (elastic constants, moduli), energy-like errors from eV
        properties (cohesive energy), and drift from the trajectory summary
        (raw log units per step — thermo output alone carries no timestep or
        atom count for eV/atom/ps normalization). A benchmark whose weighted
        metrics have no matching evidence yields an empty (wall-time-only)
        metric, mirroring the TorchSim empty-system behavior.
        """

        weights = BENCHMARK_WEIGHTS.get(benchmark)
        if weights is None:
            raise ValueError(f"unknown benchmark '{benchmark}'")

        stress_errors: list[float] = []
        energy_errors: list[float] = []
        drifts: list[float] = []
        references: dict[str, float] = {}
        for payload in self._payloads:
            for prop in payload.properties:
                if prop.reference_value is None:
                    continue
                references[prop.name] = prop.reference_value
                err = abs(prop.value - prop.reference_value)
                if prop.unit == "GPa":
                    stress_errors.append(err)
                elif prop.unit == "eV":
                    energy_errors.append(err)
            trajectory = payload.trajectory
            if trajectory is not None and trajectory.energy_drift_per_step is not None:
                drifts.append(abs(trajectory.energy_drift_per_step))

        wanted = set(weights)
        kwargs: dict[str, float] = {}
        if "mae_stress" in wanted and stress_errors:
            kwargs["mae_stress"] = fmean(stress_errors)
        if "mae_energy" in wanted and energy_errors:
            kwargs["mae_energy"] = fmean(energy_errors)
        if "energy_drift" in wanted and drifts:
            kwargs["energy_drift"] = fmean(drifts)
        # Evidence was computed offline on the lab cluster; no wall time is
        # spent (or knowable) here.
        return BenchmarkMetrics(
            wall_time_seconds=0.0,
            dft_reference=references if kwargs and references else None,
            **kwargs,
        )


__all__ = ["LammpsEvidenceBackend"]
