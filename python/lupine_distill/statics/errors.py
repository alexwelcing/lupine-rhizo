"""Exception hierarchy for the Tier-1 statics physics core.

All statics errors derive from :class:`StaticsError` so callers can catch the
whole family with one clause while still distinguishing bad inputs
(:class:`InputValidationError`) from runtime failures
(:class:`CalculationError` / :class:`ConvergenceError`).
"""

from __future__ import annotations


class StaticsError(Exception):
    """Base class for all lupine_distill.statics errors."""


class InputValidationError(StaticsError, ValueError):
    """A caller-supplied input failed validation (fail fast, no compute)."""


class CalculationError(StaticsError, RuntimeError):
    """A calculator evaluation failed mid-calculation."""


class ConvergenceError(CalculationError):
    """A fit or relaxation did not converge within its budget."""


__all__ = [
    "CalculationError",
    "ConvergenceError",
    "InputValidationError",
    "StaticsError",
]
