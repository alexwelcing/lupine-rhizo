"""Tests for run_round3_analysis.py (Round-3 frozen-rule confirmatory analysis).

Pure-stdlib synthetic fixtures built against the round-1 report.json structure
(schema lupine.candidate_campaign.v1); no GPU, no MLIPs, no scipy. Binomial
expectations are hand-computed from math.comb identities.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_round3_analysis as r3  # noqa: E402

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# fixture builders (round-1 report structure)
# --------------------------------------------------------------------------

MODELS = ("m1", "m2")
NULL_REFS = {"a0": None, "b0": None, "c11": None, "c12": None, "c44": None}


def _candidate(
    group: str,
    refs: dict[str, float | None],
    preds: dict[str, dict[str, float]],
    verdict: str | None = None,
) -> dict:
    cand = {
        "group": group,
        "formula": "Xx",
        "structure_type": "perovskite",
        "references": {**NULL_REFS, **refs},
        "per_model": {
            model: {"properties": dict(props)} for model, props in preds.items()
        },
    }
    if verdict is not None:
        cand["verdict"] = verdict
    return cand


def _report(candidates: dict[str, dict], models: tuple[str, ...] = MODELS) -> dict:
    return {
        "schema": "lupine.candidate_campaign.v1",
        "models": list(models),
        "candidates": candidates,
    }


def _uniform_group(
    group: str, n: int, ref: float, pred: float, props: tuple[str, ...] = ("a0", "b0")
) -> dict[str, dict]:
    """n members, every model predicts `pred` against reference `ref`."""
    return {
        f"{group}-{i}": _candidate(
            group,
            {p: ref for p in props},
            {m: {p: pred for p in props} for m in MODELS},
        )
        for i in range(1, n + 1)
    }


def _passing_report() -> dict:
    # ratios all 1.5 -> b=1.5, s=0 -> apply; corrected exact -> all cells improve.
    return _report(_uniform_group("gp", 3, ref=100.0, pred=150.0))


def _failing_group(group: str) -> dict[str, dict]:
    # 2 members, 1 calibration member each -> insufficient -> all abstain -> FAIL.
    return {
        f"{group}-1": _candidate(
            group, {"a0": 100.0}, {m: {"a0": 100.0} for m in MODELS}
        ),
        f"{group}-2": _candidate(
            group, {"a0": 100.0}, {m: {"a0": 150.0} for m in MODELS}
        ),
    }


# --------------------------------------------------------------------------
# frozen rule: abstention and application
# --------------------------------------------------------------------------


class TestFrozenRule:
    def test_cap_abstention_when_bias_below_scatter(self):
        # b = 1.15, s = 0.20, |b-1| = 0.15 <= s -> ABSTAIN (magnitude_cap)
        out = r3.apply_frozen_rule(200.0, (1.05, 1.25))
        assert out["applied"] is False
        assert out["abstain_reason"] == "magnitude_cap"
        assert out["corrected"] == 200.0

    def test_cap_abstention_at_exact_boundary(self):
        # b = 1.5, s = 0.5, |b-1| == s (0.25-exact floats) -> not strictly > -> ABSTAIN
        out = r3.apply_frozen_rule(10.0, (1.25, 1.75))
        assert out["applied"] is False
        assert out["abstain_reason"] == "magnitude_cap"
        assert out["corrected"] == 10.0

    def test_direction_abstention_mixed_sides(self):
        out = r3.apply_frozen_rule(10.0, (0.9, 1.1))
        assert out["applied"] is False
        assert out["abstain_reason"] == "direction"
        assert out["corrected"] == 10.0

    def test_direction_abstention_ratio_exactly_one_is_not_strict(self):
        out = r3.apply_frozen_rule(10.0, (1.0, 1.2))
        assert out["applied"] is False
        assert out["abstain_reason"] == "direction"

    def test_insufficient_calibration_abstains(self):
        for ratios in ((), (1.5,)):
            out = r3.apply_frozen_rule(10.0, ratios)
            assert out["applied"] is False
            assert out["abstain_reason"] == "insufficient_calibration"
            assert out["corrected"] == 10.0

    def test_application_divides_by_median_inflation_side(self):
        # b = 1.55, s ~= 0.1, |b-1| = 0.55 > s -> apply, corrected = pred/b
        out = r3.apply_frozen_rule(155.0, (1.5, 1.6))
        assert out["applied"] is True
        assert out["abstain_reason"] is None
        assert out["corrected"] == pytest.approx(100.0)
        assert out["b"] == pytest.approx(1.55)

    def test_application_deflation_side(self):
        # all ratios < 1: b = 0.525, s = 0.05, |b-1| = 0.475 > s -> apply
        out = r3.apply_frozen_rule(52.5, (0.5, 0.55))
        assert out["applied"] is True
        assert out["corrected"] == pytest.approx(100.0)

    def test_zero_scatter_identical_ratios_applies(self):
        out = r3.apply_frozen_rule(150.0, (1.5, 1.5))
        assert out["applied"] is True
        assert out["corrected"] == pytest.approx(100.0)


# --------------------------------------------------------------------------
# exact binomial sign test (hand-computed, no scipy)
# --------------------------------------------------------------------------


class TestExactBinomialSignTest:
    @pytest.mark.parametrize(
        ("improved", "worsened", "expected"),
        [
            (5, 0, 0.0625),  # 2 * (1/32)
            (0, 5, 0.0625),  # symmetric
            (1, 5, 0.21875),  # 2 * (7/64)
            (2, 2, 1.0),  # 2 * (11/16) = 1.375 capped at 1
            (1, 0, 1.0),  # n = 1: 2 * (1/2)
            (8, 2, 0.109375),  # 2 * (56/1024)
            (9, 1, 0.021484375),  # 2 * (11/1024)
        ],
    )
    def test_hand_computed_values(self, improved, worsened, expected):
        assert r3.exact_binomial_sign_p(improved, worsened) == expected

    def test_no_effective_cells_returns_none(self):
        assert r3.exact_binomial_sign_p(0, 0) is None

    def test_negative_counts_rejected(self):
        with pytest.raises(r3.InputValidationError):
            r3.exact_binomial_sign_p(-1, 2)


# --------------------------------------------------------------------------
# summaries: improvement, worsening, tie handling
# --------------------------------------------------------------------------


def _cell(
    group: str,
    prop: str,
    candidate: str,
    raw_rel: float,
    corr_rel: float,
    applied: bool,
    reason: str | None = None,
) -> dict:
    return {
        "group": group,
        "candidate": candidate,
        "model": "m1",
        "prop": prop,
        "unit": r3.PROPERTY_UNITS[prop],
        "reference": 100.0,
        "raw": 100.0 * (1 + raw_rel),
        "corrected": 100.0 * (1 + corr_rel),
        "applied": applied,
        "abstain_reason": reason,
        "b": None,
        "s": None,
        "n_calibration": 2,
        "raw_abs_rel_err": raw_rel,
        "corrected_abs_rel_err": corr_rel,
        "raw_abs_err": 100.0 * raw_rel,
        "corrected_abs_err": 100.0 * corr_rel,
    }


class TestSummaries:
    def test_ties_dropped_from_sign_test(self):
        cells = (
            _cell("g", "b0", "c1", 0.5, 0.1, True),  # improved
            _cell("g", "b0", "c2", 0.5, 0.2, True),  # improved
            _cell("g", "b0", "c3", 0.5, 0.3, True),  # improved
            _cell("g", "b0", "c4", 0.1, 0.5, True),  # worsened
            _cell("g", "b0", "c5", 0.2, 0.2, True),  # tie -> dropped
            _cell("g", "b0", "c6", 0.3, 0.3, True),  # tie -> dropped
        )
        entry = r3.summarize_group_property(cells, "g", "b0")
        st = entry["sign_test"]
        assert st["n_improved"] == 3
        assert st["n_worsened"] == 1
        assert st["n_ties_dropped"] == 2
        assert st["n_effective"] == 4
        # n=4, k=3: 2 * min(15/16, 5/16) = 10/16
        assert st["p_two_sided"] == 0.625

    def test_abstained_cells_count_in_medians_not_sign_test(self):
        cells = (
            _cell("g", "a0", "c1", 0.5, 0.1, True),
            _cell("g", "a0", "c2", 0.5, 0.5, False, "direction"),
            _cell("g", "a0", "c3", 0.5, 0.5, False, "magnitude_cap"),
        )
        entry = r3.summarize_group_property(cells, "g", "a0")
        assert entry["n_cells"] == 3
        assert entry["n_applied"] == 1
        assert entry["n_abstained"] == 2
        assert entry["abstain_reasons"] == {
            "insufficient_calibration": 0,
            "direction": 1,
            "magnitude_cap": 1,
        }
        assert entry["sign_test"]["n_effective"] == 1
        assert entry["median_abs_rel_err_raw"] == 0.5
        assert entry["median_abs_rel_err_corrected"] == 0.5

    def test_absolute_deltas_emitted_alongside_relative(self):
        cells = (_cell("g", "c11", "c1", 0.5, 0.1, True),)
        entry = r3.summarize_group_property(cells, "g", "c11")
        assert entry["unit"] == "GPa"
        assert entry["median_abs_err_raw"] == pytest.approx(50.0)
        assert entry["median_abs_err_corrected"] == pytest.approx(10.0)

    def test_per_material_n_counts_candidates_not_cells(self):
        cells = tuple(
            {**_cell("g", "a0", cand, 0.5, 0.1, True), "model": model}
            for cand in ("c1", "c2")
            for model in ("m1", "m2", "m3")
        )
        entry = r3.summarize_group_property(cells, "g", "a0")
        assert entry["n_cells"] == 6
        assert entry["n_materials"] == 2

    def test_no_cells_returns_none(self):
        assert r3.summarize_group_property((), "g", "a0") is None


# --------------------------------------------------------------------------
# end-to-end application through the report structure
# --------------------------------------------------------------------------


class TestEvaluateCells:
    def test_application_improving_and_worsening(self):
        # A is exact (ratio 1.0), B and C inflated (1.5, 1.6).
        # Held-out A: ratios (1.5, 1.6) -> applied, corrected worsens.
        # Held-out B/C: a ratio of exactly 1.0 -> direction abstention.
        cands = {
            "A": _candidate("g", {"b0": 100.0}, {m: {"b0": 100.0} for m in MODELS}),
            "B": _candidate("g", {"b0": 100.0}, {m: {"b0": 150.0} for m in MODELS}),
            "C": _candidate("g", {"b0": 100.0}, {m: {"b0": 160.0} for m in MODELS}),
        }
        cells = r3.evaluate_cells(_report(cands), ())
        by_cand = {}
        for c in cells:
            by_cand.setdefault(c["candidate"], []).append(c)
        for c in by_cand["A"]:
            assert c["applied"] is True
            assert c["corrected"] == pytest.approx(100.0 / 1.55)
            assert c["corrected_abs_rel_err"] > c["raw_abs_rel_err"]  # worsened
        for cid in ("B", "C"):
            for c in by_cand[cid]:
                assert c["applied"] is False
                assert c["abstain_reason"] == "direction"

        # Improving case: uniform inflation, held-out corrected to exact.
        cells2 = r3.evaluate_cells(_passing_report(), ())
        assert all(c["applied"] for c in cells2)
        assert all(
            c["corrected_abs_rel_err"] < c["raw_abs_rel_err"] for c in cells2
        )

    def test_calibration_never_includes_held_out_candidate(self):
        # Held-out member predicts 0.5x; others 1.5x. If X leaked into its own
        # calibration the direction gate would abstain; it must not.
        cands = _uniform_group("g", 3, ref=100.0, pred=150.0, props=("a0",))
        cands["g-1"]["per_model"] = {m: {"properties": {"a0": 50.0}} for m in MODELS}
        cells = r3.evaluate_cells(_report(cands), ())
        held_out = [c for c in cells if c["candidate"] == "g-1"]
        assert held_out and all(c["applied"] for c in held_out)
        assert all(c["b"] == pytest.approx(1.5) for c in held_out)

    def test_null_reference_and_model_error_cells_skipped(self):
        cands = _uniform_group("g", 3, ref=100.0, pred=150.0, props=("a0",))
        cands["g-1"]["references"]["a0"] = None
        cands["g-2"]["per_model"]["m1"] = {"error": "relaxation diverged"}
        cells = r3.evaluate_cells(_report(cands), ())
        keys = {(c["candidate"], c["model"]) for c in cells}
        assert ("g-1", "m1") not in keys and ("g-1", "m2") not in keys
        assert ("g-2", "m1") not in keys
        assert ("g-2", "m2") in keys and ("g-3", "m1") in keys
        # g-3/m1 calibration lost g-1 (null ref) AND g-2 (m1 errored) -> 0 -> abstain;
        # g-3/m2 still has g-2 only (1 member) -> abstain as well.
        g3_m1 = next(c for c in cells if (c["candidate"], c["model"]) == ("g-3", "m1"))
        assert g3_m1["n_calibration"] == 0
        assert g3_m1["abstain_reason"] == "insufficient_calibration"
        g3_m2 = next(c for c in cells if (c["candidate"], c["model"]) == ("g-3", "m2"))
        assert g3_m2["n_calibration"] == 1
        assert g3_m2["abstain_reason"] == "insufficient_calibration"

    def test_registered_exclusion_removes_cell_but_not_calibration(self):
        cands = _uniform_group("g", 3, ref=100.0, pred=150.0)
        exclusions = ({"candidate": "g-1", "property": "a0"},)
        cells = r3.evaluate_cells(_report(cands), exclusions)
        a0 = [c for c in cells if c["prop"] == "a0"]
        assert {c["candidate"] for c in a0} == {"g-2", "g-3"}
        # frozen rule: exclusion does NOT alter the calibration set
        assert all(c["n_calibration"] == 2 for c in a0)
        # other property untouched
        assert {c["candidate"] for c in cells if c["prop"] == "b0"} == {
            "g-1",
            "g-2",
            "g-3",
        }

    def test_group_level_exclusion_removes_whole_property(self):
        cands = _uniform_group("g", 3, ref=100.0, pred=150.0)
        cells = r3.evaluate_cells(_report(cands), ({"group": "g", "property": "b0"},))
        assert not [c for c in cells if c["prop"] == "b0"]


# --------------------------------------------------------------------------
# registered criteria: PASS / FAIL / KILL
# --------------------------------------------------------------------------


class TestCriteria:
    def test_group_pass_requires_two_thirds_wins(self):
        win = {"win": True}
        loss = {"win": False}
        assert r3.group_success({"a0": win, "b0": win, "c11": loss})["verdict"] == "PASS"
        assert r3.group_success({"a0": win, "b0": loss, "c11": loss})["verdict"] == "FAIL"
        assert r3.group_success({"a0": win, "b0": win})["verdict"] == "PASS"
        assert r3.group_success({"a0": win, "b0": loss})["verdict"] == "FAIL"
        assert r3.group_success({})["verdict"] == "FAIL"

    def test_passing_group_end_to_end(self):
        analysis = r3.build_analysis(_passing_report(), (), "synthetic", None)
        g = analysis["groups"]["gp"]
        assert g["verdict"] == "PASS"
        assert g["n_evaluable_properties"] == 2 and g["n_wins"] == 2
        for prop in ("a0", "b0"):
            e = g["properties"][prop]
            assert e["n_materials"] == 3
            assert e["n_cells"] == 6 and e["n_applied"] == 6
            assert e["median_abs_rel_err_raw"] == 0.5
            assert e["median_abs_rel_err_corrected"] == 0.0
            # n=6, k=6: 2 * (1/64) = 0.03125
            assert e["sign_test"]["p_two_sided"] == 0.03125
            assert e["verdict"] == "WIN"
        assert analysis["kill_condition"]["triggered"] is False

    def test_kill_triggered_when_both_groups_fail(self):
        report = _report({**_failing_group("gf1"), **_failing_group("gf2")})
        analysis = r3.build_analysis(report, (), "synthetic", None)
        verdicts = {g: d["verdict"] for g, d in analysis["groups"].items()}
        assert verdicts == {"gf1": "FAIL", "gf2": "FAIL"}
        kill = analysis["kill_condition"]
        assert kill["triggered"] is True
        assert "same-class lattice constants only" in kill["registered_text"]

    def test_kill_not_triggered_when_one_group_passes(self):
        report = _report({**_passing_report()["candidates"], **_failing_group("gf")})
        analysis = r3.build_analysis(report, (), "synthetic", None)
        assert analysis["groups"]["gp"]["verdict"] == "PASS"
        assert analysis["groups"]["gf"]["verdict"] == "FAIL"
        assert analysis["kill_condition"]["triggered"] is False

    def test_risk_coverage_from_gate_verdicts(self):
        cands = _uniform_group("g", 3, ref=100.0, pred=150.0)
        for cid, verdict in zip(sorted(cands), ("CERTIFIED", "FLAGGED", "REFUSED")):
            cands[cid]["verdict"] = verdict
        analysis = r3.build_analysis(_report(cands), (), "synthetic", None)
        rc = analysis["groups"]["g"]["risk_coverage"]
        assert rc == {
            "n_candidates": 3,
            "n_certified": 1,
            "n_flagged": 1,
            "n_refused": 1,
            "n_issued": 2,
            "coverage_issued_fraction": pytest.approx(2 / 3),
        }

    def test_risk_coverage_none_without_verdicts(self):
        analysis = r3.build_analysis(_passing_report(), (), "synthetic", None)
        assert analysis["groups"]["gp"]["risk_coverage"] is None


# --------------------------------------------------------------------------
# input validation and CLI
# --------------------------------------------------------------------------


class TestInputsAndCli:
    def test_load_report_rejects_malformed(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"models": ["m1"]}), encoding="utf-8")
        with pytest.raises(r3.InputValidationError):
            r3.load_report(bad)
        with pytest.raises(r3.InputValidationError):
            r3.load_report(tmp_path / "missing.json")

    def test_load_exclusions_validation(self, tmp_path: Path):
        path = tmp_path / "excl.json"
        path.write_text(
            json.dumps({"exclusions": [{"candidate": "x", "property": "nope"}]}),
            encoding="utf-8",
        )
        with pytest.raises(r3.InputValidationError):
            r3.load_exclusions(path)
        path.write_text(
            json.dumps(
                {"exclusions": [{"candidate": "x", "group": "g", "property": "a0"}]}
            ),
            encoding="utf-8",
        )
        with pytest.raises(r3.InputValidationError):
            r3.load_exclusions(path)
        assert r3.load_exclusions(None) == ()

    def test_main_writes_json_and_markdown(self, tmp_path: Path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(_passing_report()), encoding="utf-8")
        out_dir = tmp_path / "out"
        rc = r3.main(["--report", str(report_path), "--out-dir", str(out_dir)])
        assert rc == 0
        analysis = json.loads(
            (out_dir / "round3_analysis.json").read_text(encoding="utf-8")
        )
        assert analysis["schema"] == "lupine.round3_analysis.v1"
        assert analysis["groups"]["gp"]["verdict"] == "PASS"
        md = (out_dir / "ROUND3_REPORT.md").read_text(encoding="utf-8")
        assert "Per-material n" in md
        assert "| gp | a0 | 3 | 6 | 6 | 0 |" in md
        assert "gp: PASS" in md
        assert "NOT TRIGGERED" in md

    def test_main_kill_report_text(self, tmp_path: Path):
        report_path = tmp_path / "report.json"
        report_path.write_text(
            json.dumps(_report({**_failing_group("gf1"), **_failing_group("gf2")})),
            encoding="utf-8",
        )
        out_dir = tmp_path / "out"
        assert r3.main(["--report", str(report_path), "--out-dir", str(out_dir)]) == 0
        md = (out_dir / "ROUND3_REPORT.md").read_text(encoding="utf-8")
        assert "**TRIGGERED**" in md
        assert "same-class lattice constants only" in md

    def test_main_missing_report_returns_error_code(self, tmp_path: Path):
        rc = r3.main(
            [
                "--report",
                str(tmp_path / "nope.json"),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        assert rc == 2

    def test_docstring_quotes_frozen_rule_verbatim(self):
        doc = r3.__doc__
        assert "Calibration set = other class-C members with a non-null reference" in doc
        assert "ABSTAIN unless |b - 1| > s" in doc
        assert "corrected = pred / b; else corrected = pred (abstention, risk-free)" in doc
