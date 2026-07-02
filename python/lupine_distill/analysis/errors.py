"""Exception hierarchy for the Y-matrix cross-property analysis package.

Mirrors ``lupine_distill.statics.errors``: everything derives from
:class:`AnalysisError` so callers can catch the whole family with one clause,
while bad caller inputs (:class:`InputValidationError`, fail fast, no compute)
stay distinguishable from mid-computation failures
(:class:`ComputationError`).
"""

from __future__ import annotations


class AnalysisError(Exception):
    """Base class for all lupine_distill.analysis errors."""


class InputValidationError(AnalysisError, ValueError):
    """A caller-supplied input failed validation (fail fast, no compute)."""


class ComputationError(AnalysisError, RuntimeError):
    """A statistic could not be computed from otherwise-valid inputs."""


__all__ = [
    "AnalysisError",
    "ComputationError",
    "InputValidationError",
]
