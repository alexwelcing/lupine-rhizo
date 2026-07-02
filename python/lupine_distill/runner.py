"""Suite orchestration: drive a backend across a benchmark suite to produce a
single :class:`BenchmarkResult`.

Also hosts the backend factory used by the CLI, which prefers TorchSim and
falls back to the deterministic mock when torch_sim is unavailable so CI never
crashes on a missing GPU dependency.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Mapping
from datetime import datetime, timezone

from .backends.base import BenchmarkBackend, System
from .backends.lammps import LammpsEvidenceBackend
from .backends.mock import MockBenchmarkBackend
from .backends.torchsim import TorchSimUnavailable, try_build_torchsim_backend
from .constants import BENCHMARK_SUITE_VERSION, TORCHSIM_VERSION_UNAVAILABLE
from .schemas import Backend, BenchmarkResult
from .suite import resolve_suite

logger = logging.getLogger("lupine_distill.benchmark")

# A tiny deterministic default system so a CLI run with no input still produces
# a well-formed result. Real runs pass explicit systems.
_DEFAULT_SYSTEM: System = {"formula": "Cu", "n_atoms": 4, "pbc": True}


def run_suite(
    *,
    backend: BenchmarkBackend,
    model_id: str,
    distill_version: int,
    suite: str = "full",
    system: System | None = None,
    suite_version: str = BENCHMARK_SUITE_VERSION,
) -> BenchmarkResult:
    """Run every benchmark in ``suite`` with ``backend`` and assemble a result.

    The backend is never asked to mutate ``system``; a fresh result is built.
    A per-benchmark failure raises (fail-loud) rather than being swallowed.
    """

    target_system: System = system if system is not None else _DEFAULT_SYSTEM
    benchmark_names = resolve_suite(suite)

    metrics = {name: backend.run(target_system, name) for name in benchmark_names}

    return BenchmarkResult(
        model_id=model_id,
        distill_version=distill_version,
        backend=backend.backend_id,
        timestamp=datetime.now(timezone.utc),
        torchsim_version=backend.engine_version,
        benchmark_suite_version=suite_version,
        results=metrics,
    )


def build_backend(
    requested: Backend,
    *,
    model_id: str,
    distill_version: int = 0,
    device: str | None = None,
    allow_mock_fallback: bool = True,
    evidence_dir: pathlib.Path | str | None = None,
) -> BenchmarkBackend:
    """Construct a backend by name with graceful TorchSim->mock fallback.

    - ``"torchsim"``: try the real engine; if torch_sim is missing and
      ``allow_mock_fallback`` is set, log clearly and return a mock that reports
      under the ``torchsim`` backend id (CI degrades gracefully). If fallback is
      disabled, re-raise :class:`TorchSimUnavailable`.
    - ``"lammps"``: with ``evidence_dir`` set, score precomputed
      ``lammps_evidence.v1`` payloads via :class:`LammpsEvidenceBackend` (no
      simulation is driven). Without an evidence dir, fall back to the mock
      when permitted, else raise ``ValueError`` naming the missing input.
    - ``"ase"``: not wired in this CPU-importable module; fall back to the mock
      when permitted, else raise ``NotImplementedError``.
    """

    if requested == "torchsim":
        backend = try_build_torchsim_backend(model_id=model_id, device=device)
        if backend is not None:
            logger.info("using TorchSim backend (engine=%s)", backend.engine_version)
            return backend
        if not allow_mock_fallback:
            raise TorchSimUnavailable("torch_sim unavailable and mock fallback disabled")
        logger.warning(
            "torch_sim not installed; falling back to deterministic MockBenchmarkBackend "
            "(results are synthetic, engine=%s)",
            TORCHSIM_VERSION_UNAVAILABLE,
        )
        return MockBenchmarkBackend(model_id=model_id, distill_version=distill_version)

    if requested == "lammps":
        if evidence_dir is not None:
            backend = LammpsEvidenceBackend(evidence_dir=evidence_dir)
            logger.info("using LAMMPS file-evidence backend (engine=%s)", backend.engine_version)
            return backend
        if not allow_mock_fallback:
            raise ValueError(
                "backend 'lammps' requires evidence_dir "
                "(a directory of lammps_evidence.v1 JSON payloads)"
            )
        logger.warning(
            "backend 'lammps' given no evidence_dir; using deterministic MockBenchmarkBackend"
        )
        return MockBenchmarkBackend(model_id=model_id, distill_version=distill_version)

    if requested == "ase":
        if not allow_mock_fallback:
            raise NotImplementedError("backend 'ase' is not wired in this environment")
        logger.warning("backend 'ase' not wired here; using deterministic MockBenchmarkBackend")
        return MockBenchmarkBackend(model_id=model_id, distill_version=distill_version)

    raise ValueError(f"unsupported backend '{requested}'")


def result_to_jsonable(result: BenchmarkResult) -> Mapping[str, object]:
    """Project a result to a plain JSON-serializable mapping (mode='json')."""

    return result.model_dump(mode="json")


__all__ = ["build_backend", "result_to_jsonable", "run_suite"]
