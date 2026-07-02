"""Birch-Murnaghan (3rd order) equation-of-state fitting.

A BM3 energy is *exactly* a cubic polynomial in ``x = V**(-2/3)``, so the fit
is a linear least-squares problem in numpy -- no scipy dependency. The fit is
performed in a centred/scaled coordinate for numerical conditioning and the
physical parameters (V0, B0, B0') are recovered analytically via the chain
rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final, Sequence

import numpy as np
from ase import Atoms
from ase.calculators.calculator import Calculator

from lupine_distill.statics.errors import (
    CalculationError,
    ConvergenceError,
    InputValidationError,
)
from lupine_distill.statics.units import EV_PER_A3_TO_GPA

_MIN_POINTS: Final[int] = 5
_MAX_VOLUME_SPAN: Final[float] = 0.30


@dataclass(frozen=True)
class BirchMurnaghanFit:
    """Result of a 3rd-order Birch-Murnaghan fit (per simulation cell)."""

    e0_ev: float
    v0_a3: float
    b0_gpa: float
    b0_prime: float
    rms_residual_ev: float


def _validate_curve(volumes: Sequence[float], energies: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    v = np.asarray(volumes, dtype=float)
    e = np.asarray(energies, dtype=float)
    if v.ndim != 1 or e.ndim != 1 or v.shape != e.shape:
        raise InputValidationError(
            f"volumes and energies must be equal-length 1-D sequences, "
            f"got shapes {v.shape} and {e.shape}"
        )
    if v.size < _MIN_POINTS:
        raise InputValidationError(
            f"need at least {_MIN_POINTS} (volume, energy) points for a BM3 fit, got {v.size}"
        )
    if not np.all(np.isfinite(v)) or not np.all(np.isfinite(e)):
        raise InputValidationError("volumes and energies must all be finite")
    if np.any(v <= 0.0):
        raise InputValidationError("all volumes must be positive")
    if np.unique(v).size != v.size:
        raise InputValidationError("volumes must be distinct")
    return v, e


def fit_birch_murnaghan(
    volumes_a3: Sequence[float], energies_ev: Sequence[float]
) -> BirchMurnaghanFit:
    """Fit E(V) to 3rd-order Birch-Murnaghan; volumes in A^3, energies in eV.

    Raises :class:`ConvergenceError` if the sampled curve has no interior
    minimum with positive curvature (i.e. the scan does not bracket V0).
    """
    v, e = _validate_curve(volumes_a3, energies_ev)
    x = v ** (-2.0 / 3.0)
    # Centre/scale for conditioning: fit p(t) with x = x_mean + x_scale * t.
    x_mean = float(np.mean(x))
    x_scale = float(np.std(x))
    if x_scale <= 0.0 or not math.isfinite(x_scale):
        raise InputValidationError("volumes span is degenerate; cannot fit")
    t = (x - x_mean) / x_scale
    coeffs = np.polynomial.polynomial.polyfit(t, e, deg=3)
    p = np.polynomial.Polynomial(coeffs)
    dp, d2p, d3p = p.deriv(1), p.deriv(2), p.deriv(3)

    roots = dp.roots()
    candidates: list[tuple[float, float]] = []  # (x0, curvature d2E/dV2)
    for root in roots:
        if abs(root.imag) > 1e-9:
            continue
        t0 = float(root.real)
        x0 = x_mean + x_scale * t0
        if x0 <= 0.0:
            continue
        v0 = x0 ** (-1.5)
        # Chain rule with x(V) = V^(-2/3); at a stationary point dE/dx = 0.
        dxdv = -2.0 / 3.0 * v0 ** (-5.0 / 3.0)
        d2e_dv2 = (d2p(t0) / x_scale**2) * dxdv**2
        if d2e_dv2 > 0.0:
            candidates.append((x0, d2e_dv2))
    if not candidates:
        raise ConvergenceError(
            "BM3 fit found no minimum with positive curvature in the scanned "
            "volume range; the scan does not bracket the equilibrium volume"
        )
    # Prefer a minimum inside the scanned window; otherwise nearest to it.
    x_lo, x_hi = float(np.min(x)), float(np.max(x))
    inside = [c for c in candidates if x_lo <= c[0] <= x_hi]
    pool = inside if inside else candidates
    x0, _ = min(pool, key=lambda c: abs(c[0] - x_mean))

    t0 = (x0 - x_mean) / x_scale
    v0 = x0 ** (-1.5)
    e0 = float(p(t0))
    dxdv = -2.0 / 3.0 * v0 ** (-5.0 / 3.0)
    d2xdv2 = 10.0 / 9.0 * v0 ** (-8.0 / 3.0)
    d3xdv3 = -80.0 / 27.0 * v0 ** (-11.0 / 3.0)
    # dE/dx and its derivatives in the original x coordinate.
    de_dx2 = float(d2p(t0)) / x_scale**2
    de_dx3 = float(d3p(t0)) / x_scale**3
    d2e_dv2 = de_dx2 * dxdv**2  # dE/dx = 0 at the minimum
    d3e_dv3 = de_dx3 * dxdv**3 + 3.0 * de_dx2 * dxdv * d2xdv2
    b0_ev_a3 = v0 * d2e_dv2
    b0_prime = -1.0 - v0 * d3e_dv3 / d2e_dv2
    rms = float(np.sqrt(np.mean((p(t) - e) ** 2)))
    return BirchMurnaghanFit(
        e0_ev=e0,
        v0_a3=float(v0),
        b0_gpa=float(b0_ev_a3 * EV_PER_A3_TO_GPA),
        b0_prime=float(b0_prime),
        rms_residual_ev=rms,
    )


def validate_scan_parameters(volume_span: float, n_points: int) -> tuple[float, int]:
    """Validate the E-V scan window and sampling density."""
    try:
        span = float(volume_span)
        n = int(n_points)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"volume_span/n_points must be numeric, got {volume_span!r}, {n_points!r}"
        ) from exc
    if not math.isfinite(span) or span <= 0.0 or span > _MAX_VOLUME_SPAN:
        raise InputValidationError(
            f"volume_span must be in (0, {_MAX_VOLUME_SPAN}], got {span}"
        )
    if n < _MIN_POINTS:
        raise InputValidationError(f"n_points must be >= {_MIN_POINTS}, got {n}")
    return span, n


def scan_energy_volume(
    atoms: Atoms,
    calculator: Calculator,
    volume_span: float,
    n_points: int,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Isotropically strain ``atoms`` over ``1 +/- volume_span`` in volume.

    Works on copies; neither ``atoms`` nor the calculator's own state is
    mutated by this function. Returns per-cell (volumes A^3, energies eV).
    """
    span, n = validate_scan_parameters(volume_span, n_points)
    cell0 = atoms.get_cell().array.copy()
    volumes: list[float] = []
    energies: list[float] = []
    for factor in np.linspace(1.0 - span, 1.0 + span, n):
        image = atoms.copy()
        image.set_cell(cell0 * factor ** (1.0 / 3.0), scale_atoms=True)
        image.calc = calculator
        try:
            energy = float(image.get_potential_energy())
        except Exception as exc:
            raise CalculationError(
                f"calculator failed on {image.get_chemical_formula()} at "
                f"volume factor {factor:.4f}: {exc}"
            ) from exc
        if not math.isfinite(energy):
            raise CalculationError(
                f"calculator returned non-finite energy at volume factor {factor:.4f}"
            )
        volumes.append(float(image.get_volume()))
        energies.append(energy)
    return tuple(volumes), tuple(energies)


__all__ = [
    "BirchMurnaghanFit",
    "fit_birch_murnaghan",
    "scan_energy_volume",
    "validate_scan_parameters",
]
