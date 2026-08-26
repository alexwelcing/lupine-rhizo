"""Round-5 optimal-bias correction contract tests."""

from __future__ import annotations

import pytest
from lupine_distill.statics.optimal_bias import (
    SCALE,
    apply_optimal_bias_correction,
    calibrate_optimal_bias,
    rounding_robust_gate,
)

pytestmark = pytest.mark.unit


def test_inflation_uses_hull_minimum_instead_of_median() -> None:
    calibration = calibrate_optimal_bias([10100, 10200, 10400, 10500])

    assert calibration["side"] == "inflation"
    assert calibration["estimator"] == "hull-minimum"
    assert calibration["lo_scaled"] == 10100
    assert calibration["hi_scaled"] == 10500
    assert calibration["bias_scaled"] == 10100
    assert calibration["median_scaled"] == 10300
    assert calibration["rounding_robust_gate"]["passed"] is True
    assert calibration["applied"] is True


def test_audit_median_is_exact_for_large_even_integer_input() -> None:
    calibration = calibrate_optimal_bias([10002, 10002, 2**60, 2**60 + 1])

    assert calibration["median_scaled"] == 576460752303428489
    assert calibration["rounding_robust_gate"]["passed"] is True
    assert calibration["applied"] is True


def test_deflation_uses_exact_integer_minimax_candidate() -> None:
    calibration = calibrate_optimal_bias([7000, 7600, 8400, 9000])

    assert calibration["side"] == "deflation"
    assert calibration["estimator"] == "integer-minimax-bstar"
    assert calibration["bias_scaled"] == 8889
    assert calibration["bstar"] == {
        "numerator": SCALE * (7000 + 9000),
        "denominator": 2 * SCALE + 7000 - 9000,
        "floor": 8888,
        "ceil": 8889,
        "admissible_candidates": [8888, 8889],
        "objectives": [
            {
                "bias": 8888,
                "margin_numerator": 7768000,
                "objective_numerator": 7768000,
                "objective_denominator": 88880000,
            },
            {
                "bias": 8889,
                "margin_numerator": 7777000,
                "objective_numerator": 7777000,
                "objective_denominator": 88890000,
            },
        ],
        "comparison": {
            "left_bias": 8888,
            "right_bias": 8889,
            "left_cross_product": 690497520000000,
            "right_cross_product": 691219760000000,
            "relation": "less",
            "selected_bias": 8889,
        },
        "tie_break": "larger-bias-for-robustness",
    }
    assert calibration["rounding_robust_gate"]["passed"] is True
    assert calibration["applied"] is True


def test_rounding_robust_gate_refuses_theory4_deflation_witness() -> None:
    gate = rounding_robust_gate(side="deflation", lo=3000, hi=5756, bias=4041)

    assert gate["sharp_margin"] == 4
    assert gate["sharp_passed"] is True
    assert gate["required_margin"] == 14143
    assert gate["passed"] is False


def test_rounding_robust_gate_refuses_theory4_severe_inflation_witness() -> None:
    gate = rounding_robust_gate(side="inflation", lo=10001, hi=10002, bias=10002)

    assert gate["sharp_margin"] == 2
    assert gate["sharp_passed"] is True
    assert gate["required_margin"] == 15001
    assert gate["passed"] is False


def test_near_neutral_optimal_estimator_still_fails_closed_on_rounding() -> None:
    calibration = calibrate_optimal_bias([10001, 10001, 10001, 10001])

    assert calibration["bias_scaled"] == 10001
    assert calibration["rounding_robust_gate"]["sharp_passed"] is True
    assert calibration["rounding_robust_gate"]["passed"] is False
    assert calibration["applied"] is False
    assert calibration["abstain_reason"] == "rounding_robust_sharp_license"


def test_deflation_integer_objective_tie_prefers_larger_bias() -> None:
    calibration = calibrate_optimal_bias([282, 282, 462, 462])

    assert calibration["bstar"]["admissible_candidates"] == [375, 376]
    assert calibration["bstar"]["comparison"]["relation"] == "equal"
    assert calibration["bstar"]["comparison"]["selected_bias"] == 376
    assert calibration["bias_scaled"] == 376


def test_direction_gate_abstains_on_mixed_or_neutral_hull() -> None:
    calibration = calibrate_optimal_bias([9900, 9950, 10000, 10100])

    assert calibration["applied"] is False
    assert calibration["abstain_reason"] == "direction_gate"
    assert "bias_scaled" not in calibration


def test_apply_correction_uses_registered_fixed_point_bias() -> None:
    decision = apply_optimal_bias_correction(90.0, [7000, 7600, 8400, 9000])

    assert decision["applied"] is True
    assert decision["corrected"] == pytest.approx(90.0 / 0.8889)
    assert decision["calibration"]["bias_scaled"] == 8889


def test_apply_correction_abstains_if_finite_input_would_overflow() -> None:
    prediction = 1.79e308

    decision = apply_optimal_bias_correction(prediction, [3000, 3000, 3400, 3400])

    assert decision["corrected"] == prediction
    assert decision["applied"] is False
    assert decision["calibration"]["applied"] is False
    assert decision["calibration"]["abstain_reason"] == "non_finite_correction"
