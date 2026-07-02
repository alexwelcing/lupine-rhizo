"""Lupine Distill MLIP benchmarking pipeline.

Canonical home of the shared benchmark contract. Other tracks reference:

    from lupine_distill import BenchmarkResult, BenchmarkMetrics

Importing this package is cheap and dependency-light: it never imports torch /
torch_sim (the TorchSim backend imports that heavy dependency lazily inside its
methods), so it is safe to import in CPU-only CI.
"""

from __future__ import annotations

from .constants import (
    BASELINE_DISTILL_VERSION,
    BENCHMARK_SUITE_VERSION,
    MIN_UPLIFT_THRESHOLD,
    REGRESSION_THRESHOLD,
)
from .schemas import (
    LAMMPS_EVIDENCE_SCHEMA,
    Backend,
    BenchmarkMetrics,
    BenchmarkResult,
    LammpsEvidence,
    LammpsPropertyValue,
    LammpsProvenance,
    LammpsSource,
    LammpsTrajectorySummary,
    PromotionRecommendation,
)
from .suite import BENCHMARK_SUITE, BENCHMARK_WEIGHTS, resolve_suite
from .uplift import distill_v_uplift, recommend

__all__ = [
    "BASELINE_DISTILL_VERSION",
    "BENCHMARK_SUITE",
    "BENCHMARK_SUITE_VERSION",
    "BENCHMARK_WEIGHTS",
    "LAMMPS_EVIDENCE_SCHEMA",
    "Backend",
    "BenchmarkMetrics",
    "BenchmarkResult",
    "LammpsEvidence",
    "LammpsPropertyValue",
    "LammpsProvenance",
    "LammpsSource",
    "LammpsTrajectorySummary",
    "MIN_UPLIFT_THRESHOLD",
    "PromotionRecommendation",
    "REGRESSION_THRESHOLD",
    "distill_v_uplift",
    "recommend",
    "resolve_suite",
]
