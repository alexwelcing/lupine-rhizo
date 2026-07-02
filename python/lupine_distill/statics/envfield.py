"""Environment-error-field correction: an ASE calculator with analytic forces.

Implements the run-time inverse of the measured coordination error field
(paper: environment-error-field-2026-07-02, Eq. 1): an additive correction

    E_corr = - sum_i P(c_i)

where ``c_i`` is a smooth-cutoff coordination and ``P`` is the cubic through
the measured knots ``{(8, de8), (9, de9), (11, de11), (12, 0)}`` — exactly
determined (four coefficients, four points), so ``P`` and ``P'`` are analytic.
Forces follow by the chain rule and are accumulated pairwise; the calculator
is meant to be summed with a base MLIP calculator (``ase SumCalculator``).

Conventions (documented, part of the claim): coordination uses a cosine
switching function — 1 for r <= r_on, 0 for r >= r_off,
0.5*(1 + cos(pi*(r - r_on)/(r_off - r_on))) between — with defaults placed
between the model-relaxed first- and second-neighbor shells of the fcc
lattice the knots were measured on. In perfect fcc bulk at that lattice
constant, c_i = 12 and the correction vanishes identically (P(12) = 0).
"""

from __future__ import annotations

import numpy as np
from ase.calculators.calculator import Calculator, all_changes
from ase.neighborlist import neighbor_list

from .errors import InputValidationError

__all__ = ["FieldCorrectionCalculator", "cubic_through_knots", "fcc_cutoffs"]


def fcc_cutoffs(a0_angstrom: float) -> tuple[float, float]:
    """Default smooth-cutoff radii for an fcc lattice constant.

    First shell sits at a0/sqrt(2), second at a0. The switch turns on 10%
    beyond the first shell and is fully off 5% inside the second, so bulk
    coordination counts exactly the 12 first neighbors.
    """
    if a0_angstrom <= 0:
        raise InputValidationError(f"a0 must be positive, got {a0_angstrom}")
    d1 = a0_angstrom / np.sqrt(2.0)
    return 1.10 * d1, 0.95 * a0_angstrom


def cubic_through_knots(knots: dict[float, float]) -> np.ndarray:
    """Coefficients (c0..c3) of the cubic through exactly four (c, value) knots.

    The field convention fixes P(12) = 0; callers include that knot
    explicitly so the constraint is visible in the data.
    """
    if len(knots) != 4:
        raise InputValidationError(
            f"exactly four knots required for the determined cubic, got {len(knots)}"
        )
    cs = np.array(sorted(knots), dtype=float)
    vs = np.array([knots[c] for c in sorted(knots)], dtype=float)
    vander = np.vander(cs, 4, increasing=True)  # [1, c, c^2, c^3]
    return np.linalg.solve(vander, vs)


class FieldCorrectionCalculator(Calculator):
    """ASE calculator for ``E_corr = -sum_i P(c_i)`` with analytic forces."""

    implemented_properties = ["energy", "forces"]

    def __init__(
        self,
        knots: dict[float, float],
        *,
        r_on: float,
        r_off: float,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        if not (0.0 < r_on < r_off):
            raise InputValidationError(f"need 0 < r_on < r_off, got {r_on}, {r_off}")
        self._coeffs = cubic_through_knots(knots)
        self._r_on = float(r_on)
        self._r_off = float(r_off)

    # -- the cubic and its derivative -------------------------------------
    def _p(self, c: np.ndarray) -> np.ndarray:
        c0, c1, c2, c3 = self._coeffs
        return c0 + c1 * c + c2 * c * c + c3 * c * c * c

    def _dp(self, c: np.ndarray) -> np.ndarray:
        _, c1, c2, c3 = self._coeffs
        return c1 + 2.0 * c2 * c + 3.0 * c3 * c * c

    # -- smooth cutoff and its derivative ----------------------------------
    def _fc(self, r: np.ndarray) -> np.ndarray:
        x = (r - self._r_on) / (self._r_off - self._r_on)
        out = 0.5 * (1.0 + np.cos(np.pi * np.clip(x, 0.0, 1.0)))
        out[r <= self._r_on] = 1.0
        out[r >= self._r_off] = 0.0
        return out

    def _dfc(self, r: np.ndarray) -> np.ndarray:
        span = self._r_off - self._r_on
        x = (r - self._r_on) / span
        inside = (r > self._r_on) & (r < self._r_off)
        out = np.zeros_like(r)
        out[inside] = -0.5 * np.pi / span * np.sin(np.pi * x[inside])
        return out

    # -- ASE interface ------------------------------------------------------
    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        i_idx, j_idx, dists, vecs = neighbor_list(
            "ijdD", self.atoms, self._r_off, self_interaction=False
        )
        n = len(self.atoms)
        fc = self._fc(dists)
        coord = np.zeros(n)
        np.add.at(coord, i_idx, fc)

        self.results["energy"] = float(-np.sum(self._p(coord)))

        # dE/dr_pair for pair (i, j): -(P'(c_i)) * fc'(r_ij); the (j, i) pair
        # appears separately in the full neighbor list, contributing P'(c_j).
        dp_i = self._dp(coord)[i_idx]
        dfc = self._dfc(dists)
        de_dr = -dp_i * dfc                      # scalar per listed pair
        with np.errstate(invalid="ignore", divide="ignore"):
            unit = vecs / dists[:, None]         # r_j - r_i direction
        pair_force = de_dr[:, None] * unit       # force on atom i is +dE/dr * unit
        forces = np.zeros((n, 3))
        np.add.at(forces, i_idx, pair_force)
        np.add.at(forces, j_idx, -pair_force)
        self.results["forces"] = forces
