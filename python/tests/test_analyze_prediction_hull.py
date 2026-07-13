"""Tests for analyze_prediction_hull.py (exploratory hull-proxy analysis).

Pure-stdlib synthetic fixtures against the campaign report structure
(schema lupine.candidate_campaign.v1); no GPU, no MLIPs, no scipy.
Fisher expectations are hand-computed from hypergeometric identities.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import analyze_prediction_hull as aph  # noqa: E402

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# exact Fisher test
# --------------------------------------------------------------------------


class TestFisherExact:
    def test_known_value_3113(self):
        # margins 4/4, N=8, C(8,4)=70: pmf = [1,16,36,16,1]/70; observed a=3
        # two-sided = (16+16+1+1)/70 = 34/70
        assert aph.fisher_exact_two_sided(3, 1, 1, 3) == pytest.approx(34 / 70)

    def test_perfect_association_small(self):
        # [[2,0],[0,2]]: pmf over a in {0,1,2} = [1,4,1]/6 -> p = 2/6
        assert aph.fisher_exact_two_sided(2, 0, 0, 2) == pytest.approx(2 / 6)

    def test_no_association_balanced(self):
        # identical success rates in both strata -> p = 1
        assert aph.fisher_exact_two_sided(5, 5, 5, 5) == pytest.approx(1.0)

    def test_degenerate_margin_returns_one(self):
        assert aph.fisher_exact_two_sided(4, 0, 6, 0) == 1.0  # no failures
        assert aph.fisher_exact_two_sided(4, 2, 0, 0) == 1.0  # all in-hull

    def test_empty_table_returns_none(self):
        assert aph.fisher_exact_two_sided(0, 0, 0, 0) is None

    def test_negative_count_rejected(self):
        with pytest.raises(aph.InputValidationError):
            aph.fisher_exact_two_sided(-1, 0, 0, 0)


# --------------------------------------------------------------------------
# round-4 cap preview (proven theorem caps)
# --------------------------------------------------------------------------


class TestRound4CapPreview:
    def test_inflation_licensed(self):
        # Lean non-vacuity example: hull [1.05, 1.07], b = 1.06, s = 0.02:
        # b - 1 = 0.06 > 2s = 0.04 -> licensed
        out = aph.round4_cap_preview((1.05, 1.06, 1.07))
        assert out == {"side": "inflation", "licensed": True}

    def test_inflation_counterexample_delicensed(self):
        # Lean 1s-cap counterexample: hull [1.0001, 1.0003], b - 1 = 0.0002
        # fails 2s = 0.0004 (the Round-3 1s cap would have passed)
        out = aph.round4_cap_preview((1.0001, 1.0002, 1.0003))
        assert out == {"side": "inflation", "licensed": False}

    def test_deflation_licensed(self):
        # Lean non-vacuity example: hull [0.80, 0.84], b = 0.82, s = 0.04:
        # 1 - b = 0.18 > 3s = 0.12 and b >= 0.5 -> licensed
        out = aph.round4_cap_preview((0.80, 0.82, 0.84))
        assert out == {"side": "deflation", "licensed": True}

    def test_deflation_wide_hull_delicensed(self):
        # Lean asymmetry witness regime: hull [0.50, 0.74], s = 0.24:
        # 1 - b = 0.38 < 3s = 0.72 -> not licensed
        out = aph.round4_cap_preview((0.50, 0.74))
        assert out == {"side": "deflation", "licensed": False}

    def test_deflation_floor_delicensed(self):
        # tight spread but b < 0.5 violates the proven floor
        out = aph.round4_cap_preview((0.40, 0.41, 0.42))
        assert out == {"side": "deflation", "licensed": False}

    def test_mixed_side_never_licensed(self):
        out = aph.round4_cap_preview((0.9, 1.1))
        assert out == {"side": "mixed", "licensed": False}


# --------------------------------------------------------------------------
# synthetic end-to-end fixtures (campaign report structure)
# --------------------------------------------------------------------------

MODELS = ("m1", "m2", "m3")
NULL_REFS = {"a0": None, "b0": None, "c11": None, "c12": None, "c44": None}


def _candidate(group: str, ref_a0: float, preds_a0: dict[str, float]) -> dict:
    return {
        "group": group,
        "references": {**NULL_REFS, "a0": ref_a0},
        "per_model": {m: {"properties": {"a0": v}} for m, v in preds_a0.items()},
    }


def _report(candidates: dict[str, dict]) -> dict:
    return {
        "schema": "lupine.candidate_campaign.v1",
        "models": list(MODELS),
        "candidates": candidates,
    }


def _success_group_report() -> dict:
    """m1 applies everywhere and succeeds; m2/m3 abstain via the magnitude cap.

    m1 ratios (ref 100): A1 1.51, A2 1.50, A3 1.52. For each held-out cell
    b = midpoint of the other two, s small -> applied; corrected lands near
    100 -> success. m2 ratios (1.01, 1.04, 1.13) and m3 ratios
    (0.99, 0.96, 0.87) satisfy |b - 1| < s for EVERY held-out pair
    (e.g. (1.04, 1.13): b = 1.085, s = 0.09) -> magnitude_cap abstention.
    """
    return _report(
        {
            "A1": _candidate("gA", 100.0, {"m1": 151.0, "m2": 101.0, "m3": 99.0}),
            "A2": _candidate("gA", 100.0, {"m1": 150.0, "m2": 104.0, "m3": 96.0}),
            "A3": _candidate("gA", 100.0, {"m1": 152.0, "m2": 113.0, "m3": 87.0}),
        }
    )


class TestBuildCellRowsSuccessInHull:
    def _row(self, cid: str) -> dict:
        rows = aph.build_cell_rows(_success_group_report())
        by_key = {(r["candidate"], r["model"]): r for r in rows}
        # only m1 cells applied (m2/m3 abstain on the magnitude cap)
        assert set(by_key) == {("A1", "m1"), ("A2", "m1"), ("A3", "m1")}
        return by_key[(cid, "m1")]

    def test_outcome_and_correction(self):
        row = self._row("A1")
        # calibration ratios 1.50, 1.52 -> b = 1.51 -> corrected = 100.0 exact
        assert row["b"] == pytest.approx(1.51)
        assert row["corrected"] == pytest.approx(100.0)
        assert row["success"] is True and row["tie"] is False

    def test_true_ratio_and_oracle(self):
        row = self._row("A1")
        assert row["true_ratio_r"] == pytest.approx(1.51)
        assert row["calibration_ratio_hull"] == pytest.approx([1.50, 1.52])
        assert row["oracle_ratio_in_calibration_hull"] is True

    def test_cross_model_hull_membership(self):
        row = self._row("A1")
        # other models m2/m3 predict 101/99 -> hull [99, 101]
        assert row["cross_model_hull"] == pytest.approx([99.0, 101.0])
        assert row["proxy_raw_in_cross_model_hull"] is False  # 151 outside
        assert row["proxy_corrected_in_cross_model_hull"] is True  # 100 inside

    def test_round4_preview_inflation_licensed(self):
        row = self._row("A1")
        # b - 1 = 0.51 > 2s = 0.04
        assert row["round4_cap_preview"] == {
            "side": "inflation",
            "licensed": True,
        }


def _failure_cell_report() -> dict:
    """Held-out B1's true ratio sits OUTSIDE the calibration hull -> failure.

    m1 ratios: B2 150/100 = 1.50, B3 152/100 = 1.52 -> b = 1.51 for B1.
    B1: ref 150, raw 152 -> r = 1.0133 (outside [1.50, 1.52]); corrected
    152/1.51 = 100.66, error 49.3 vs raw 2.0 -> failure. B1's own ratio
    (1.0133) poisons B2/B3 calibrations (s > |b-1| -> magnitude_cap), so
    only the B1/m1 cell applies. m2/m3 use the always-abstaining ratio
    patterns; their B1 predictions 151.5/148.5 put raw 152 outside the
    cross-model hull.
    """
    return _report(
        {
            "B1": _candidate("gB", 150.0, {"m1": 152.0, "m2": 151.5, "m3": 148.5}),
            "B2": _candidate("gB", 100.0, {"m1": 150.0, "m2": 104.0, "m3": 96.0}),
            "B3": _candidate("gB", 100.0, {"m1": 152.0, "m2": 113.0, "m3": 87.0}),
        }
    )


class TestBuildCellRowsFailureOutOfHull:
    def test_only_target_cell_applies(self):
        rows = aph.build_cell_rows(_failure_cell_report())
        assert {(r["candidate"], r["model"]) for r in rows} == {("B1", "m1")}

    def test_failure_outcome_and_oracle_out_of_hull(self):
        (row,) = aph.build_cell_rows(_failure_cell_report())
        assert row["success"] is False and row["tie"] is False
        assert row["true_ratio_r"] == pytest.approx(152.0 / 150.0)
        assert row["oracle_ratio_in_calibration_hull"] is False
        assert row["proxy_raw_in_cross_model_hull"] is False


# --------------------------------------------------------------------------
# contingency assembly
# --------------------------------------------------------------------------


def _mkrow(pred: bool | None, success: bool, tie: bool = False) -> dict:
    return {"proxy_raw_in_cross_model_hull": pred, "success": success, "tie": tie}


class TestContingency:
    def test_counts_rates_and_fisher(self):
        rows = (
            [_mkrow(True, True)] * 3
            + [_mkrow(True, False)] * 1
            + [_mkrow(False, True)] * 1
            + [_mkrow(False, False)] * 3
        )
        con = aph.contingency(rows, "proxy_raw_in_cross_model_hull")
        assert con["table"] == {
            "in_hull_success": 3,
            "in_hull_failure": 1,
            "out_hull_success": 1,
            "out_hull_failure": 3,
        }
        assert con["success_rate_in_hull"] == pytest.approx(0.75)
        assert con["success_rate_out_hull"] == pytest.approx(0.25)
        assert con["fisher_p_two_sided"] == pytest.approx(34 / 70)

    def test_undefined_and_ties_excluded_but_counted(self):
        rows = [
            _mkrow(None, True),
            _mkrow(True, True, tie=True),
            _mkrow(True, True),
            _mkrow(False, False),
        ]
        con = aph.contingency(rows, "proxy_raw_in_cross_model_hull")
        assert con["n_cells"] == 2
        assert con["n_undefined_excluded"] == 1
        assert con["n_ties_excluded"] == 1

    def test_empty_stratum_rates_none(self):
        rows = [_mkrow(True, True), _mkrow(True, False)]
        con = aph.contingency(rows, "proxy_raw_in_cross_model_hull")
        assert con["success_rate_out_hull"] is None
        assert con["fisher_p_two_sided"] == 1.0  # degenerate margin


# --------------------------------------------------------------------------
# cross-model hull helper
# --------------------------------------------------------------------------


class TestCrossModelHull:
    def test_hull_excludes_own_model(self):
        report = _success_group_report()
        hull = aph.cross_model_hull(
            report["candidates"], MODELS, "A1", "m1", "a0"
        )
        assert hull == (99.0, 101.0)

    def test_insufficient_other_models_returns_none(self):
        report = _report(
            {"C1": _candidate("gC", 100.0, {"m1": 150.0, "m2": 149.0})}
        )
        assert (
            aph.cross_model_hull(report["candidates"], ("m1", "m2"), "C1", "m1", "a0")
        ) is None
