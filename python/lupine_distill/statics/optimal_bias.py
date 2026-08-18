"""Round-5 fixed-point optimal-bias calibration and correction.

This module is prospective Round-5 code. Frozen Round-1 through Round-4
pipelines retain their registered median estimators and are not imported here.
Ratios use the ``U = 10000`` fixed-point convention of the machine-checked
OptimalBias and SharpCorrectionLicense developments.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from fractions import Fraction
from typing import Final

from lupine_distill.statics.errors import InputValidationError

SCALE: Final[int] = 10000
MIN_CALIBRATION: Final[int] = 4


def _validated_ratios(ratios_scaled: Sequence[int]) -> tuple[int, ...]:
    ratios = tuple(ratios_scaled)
    for index, ratio in enumerate(ratios):
        if not isinstance(ratio, int) or isinstance(ratio, bool) or ratio <= 0:
            raise InputValidationError(
                f"ratios_scaled[{index}] must be a positive fixed-point integer"
            )
    return ratios


def _half_even_median(values: Sequence[int]) -> int:
    """Integer median with the registered decimal round-half-even rule."""
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    return round(Fraction(ordered[midpoint - 1] + ordered[midpoint], 2))


def _deflation_margin(lo: int, hi: int, bias: int) -> int:
    """Numerator of the guaranteed absolute margin at ``bias``."""
    return min(lo * (SCALE - bias), 2 * SCALE * bias - hi * (SCALE + bias))


def _integer_bstar(lo: int, hi: int) -> tuple[int, dict[str, object]]:
    numerator = SCALE * (lo + hi)
    denominator = 2 * SCALE + lo - hi
    floor = numerator // denominator
    ceil = (numerator + denominator - 1) // denominator
    candidates = sorted({bias for bias in (floor, ceil) if lo <= bias <= hi})
    if not candidates:
        raise InputValidationError("deflation b* has no in-hull fixed-point candidate")

    objectives = [
        {
            "bias": candidate,
            "margin_numerator": _deflation_margin(lo, hi, candidate),
            "objective_numerator": _deflation_margin(lo, hi, candidate),
            "objective_denominator": SCALE * candidate,
        }
        for candidate in candidates
    ]

    # W(b) = Wdefl(lo, hi, b) / (U*b). Fraction compares the exact
    # cross-multiplied objective. On a tie, larger b has the larger robust safe
    # region, so it is the prospectively frozen deterministic tie-break.
    bias = max(
        candidates,
        key=lambda candidate: (
            Fraction(_deflation_margin(lo, hi, candidate), SCALE * candidate),
            candidate,
        ),
    )
    if len(objectives) == 2:
        left, right = objectives
        left_cross_product = left["objective_numerator"] * right["objective_denominator"]
        right_cross_product = right["objective_numerator"] * left["objective_denominator"]
        comparison: dict[str, object] = {
            "left_bias": left["bias"],
            "right_bias": right["bias"],
            "left_cross_product": left_cross_product,
            "right_cross_product": right_cross_product,
            "relation": (
                "greater"
                if left_cross_product > right_cross_product
                else "less"
                if left_cross_product < right_cross_product
                else "equal"
            ),
            "selected_bias": bias,
        }
    else:
        comparison = {
            "relation": "single-admissible-candidate",
            "selected_bias": bias,
        }
    return bias, {
        "numerator": numerator,
        "denominator": denominator,
        "floor": floor,
        "ceil": ceil,
        "admissible_candidates": candidates,
        "objectives": objectives,
        "comparison": comparison,
        "tie_break": "larger-bias-for-robustness",
    }


def rounding_robust_gate(*, side: str, lo: int, hi: int, bias: int) -> dict[str, object]:
    """Evaluate the THEORY-4 epsilon=1/2 rounding-robust sharp gate.

    The theorem requires ``G > 1/2 * (3U + 1/2 + b - lo)`` for inflation and
    ``G > 1/2 * (3U + 1/2 + b - hi)`` for deflation. Since ``G`` is integral,
    ``required_margin`` is the exact smallest integer satisfying that strict
    inequality; no floating-point gate arithmetic is used.
    """
    if side not in {"inflation", "deflation"}:
        raise InputValidationError(f"unknown correction side: {side!r}")
    if not (0 < lo <= hi and bias > 0):
        raise InputValidationError("lo, hi, and bias must be positive with lo <= hi")

    endpoint = lo if side == "inflation" else hi
    threshold_numerator = 2 * (3 * SCALE + bias - endpoint) + 1
    required_margin = threshold_numerator // 4 + 1
    if side == "inflation":
        sharp_margin = lo * (SCALE + bias) - 2 * SCALE * bias
        theorem_domain = SCALE < lo <= bias <= 2 * SCALE
    else:
        sharp_margin = 2 * SCALE * bias - hi * (SCALE + bias)
        theorem_domain = 0 < bias <= hi < SCALE

    sharp_passed = sharp_margin > 0
    passed = theorem_domain and sharp_margin >= required_margin
    return {
        "epsilon_scaled": "1/2",
        "sharp_margin": sharp_margin,
        "required_margin": required_margin,
        "sharp_passed": sharp_passed,
        "theorem_domain": theorem_domain,
        "passed": passed,
    }


def calibrate_optimal_bias(
    ratios_scaled: Sequence[int], *, minimum_calibration: int = MIN_CALIBRATION
) -> dict[str, object]:
    """Derive the complete prospective Round-5 calibration decision."""
    ratios = _validated_ratios(ratios_scaled)
    if minimum_calibration < 1:
        raise InputValidationError("minimum_calibration must be positive")
    if len(ratios) < minimum_calibration:
        return {
            "schema": "lupine.round5.optimal-bias-calibration.v1",
            "scale": SCALE,
            "n_calibration": len(ratios),
            "ratios_scaled": list(ratios),
            "applied": False,
            "abstain_reason": "insufficient_calibration",
        }

    lo, hi = min(ratios), max(ratios)
    median_scaled = _half_even_median(ratios)
    bstar: dict[str, object] | None = None
    if lo > SCALE:
        side = "inflation"
        estimator = "hull-minimum"
        bias = lo
    elif hi < SCALE:
        side = "deflation"
        estimator = "integer-minimax-bstar"
        bias, bstar = _integer_bstar(lo, hi)
    else:
        return {
            "schema": "lupine.round5.optimal-bias-calibration.v1",
            "scale": SCALE,
            "n_calibration": len(ratios),
            "ratios_scaled": list(ratios),
            "lo_scaled": lo,
            "hi_scaled": hi,
            "median_scaled": median_scaled,
            "applied": False,
            "abstain_reason": "direction_gate",
        }

    gate = rounding_robust_gate(side=side, lo=lo, hi=hi, bias=bias)
    result: dict[str, object] = {
        "schema": "lupine.round5.optimal-bias-calibration.v1",
        "scale": SCALE,
        "n_calibration": len(ratios),
        "ratios_scaled": list(ratios),
        "side": side,
        "lo_scaled": lo,
        "hi_scaled": hi,
        "median_scaled": median_scaled,
        "estimator": estimator,
        "bias_scaled": bias,
        "rounding_robust_gate": gate,
        "applied": bool(gate["passed"]),
        "abstain_reason": None if gate["passed"] else "rounding_robust_sharp_license",
    }
    if bstar is not None:
        result["bstar"] = bstar
    return result


def apply_optimal_bias_correction(
    prediction: float,
    ratios_scaled: Sequence[int],
    *,
    minimum_calibration: int = MIN_CALIBRATION,
) -> dict[str, object]:
    """Apply the registered bias only when calibration passes both gates."""
    if not isinstance(prediction, (int, float)) or isinstance(prediction, bool):
        raise InputValidationError("prediction must be a finite number")
    prediction = float(prediction)
    if not math.isfinite(prediction):
        raise InputValidationError("prediction must be a finite number")

    calibration = calibrate_optimal_bias(
        ratios_scaled, minimum_calibration=minimum_calibration
    )
    if not calibration["applied"]:
        return {"corrected": prediction, "applied": False, "calibration": calibration}
    bias_value = calibration.get("bias_scaled")
    if not isinstance(bias_value, int) or isinstance(bias_value, bool):
        raise InputValidationError("applied calibration is missing integer bias_scaled")
    bias = bias_value
    corrected = prediction / (bias / SCALE)
    if not math.isfinite(corrected):
        calibration = {
            **calibration,
            "applied": False,
            "abstain_reason": "non_finite_correction",
        }
        return {"corrected": prediction, "applied": False, "calibration": calibration}
    return {
        "corrected": corrected,
        "applied": True,
        "calibration": calibration,
    }
