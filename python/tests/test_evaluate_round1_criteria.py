"""Tests for evaluate_round1_criteria.py (prereg S4 criteria, registered fix 3).

Synthetic Round-1/Round-2 reports in tmp dirs; no calculator, no GPU.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import evaluate_round1_criteria as erc  # noqa: E402

from lupine_distill.statics import InputValidationError  # noqa: E402

pytestmark = pytest.mark.unit

MODELS = ("m1", "m2", "m3", "m4")


# --------------------------------------------------------------------------
# exact binomial sign test
# --------------------------------------------------------------------------


class TestExactBinomialTwoSided:
    def test_unanimous_improvement(self) -> None:
        # P(X >= 8 | n=8, p=.5) = 1/256; two-sided = 2/256.
        assert erc.exact_binomial_two_sided_p(8, 8) == pytest.approx(2.0 / 256.0)

    def test_even_split_is_one(self) -> None:
        assert erc.exact_binomial_two_sided_p(5, 10) == pytest.approx(1.0)

    def test_symmetric(self) -> None:
        assert erc.exact_binomial_two_sided_p(2, 10) == pytest.approx(
            erc.exact_binomial_two_sided_p(8, 10)
        )

    def test_known_value_9_of_10(self) -> None:
        # 2 * (C(10,9) + C(10,10)) / 1024 = 2 * 11/1024.
        assert erc.exact_binomial_two_sided_p(9, 10) == pytest.approx(22.0 / 1024.0)

    def test_capped_at_one(self) -> None:
        assert erc.exact_binomial_two_sided_p(3, 6) <= 1.0

    def test_invalid_inputs_rejected(self) -> None:
        for k, n in ((1, 0), (-1, 4), (5, 4)):
            with pytest.raises(InputValidationError):
                erc.exact_binomial_two_sided_p(k, n)


# --------------------------------------------------------------------------
# synthetic reports
# --------------------------------------------------------------------------


def _candidate(
    cid: str,
    group: str,
    references: dict[str, float | None],
    raw: dict[str, float],
    bias: dict[str, float],
) -> dict:
    """One candidate whose 4 models share raw values shifted per model."""
    per_model = {}
    corrected_arm = {}
    for i, model in enumerate(MODELS):
        shift = 1.0 + 0.001 * i
        properties = {p: v * shift for p, v in raw.items()}
        per_model[model] = {"properties": properties, "born_passed": True}
        values = {}
        for prop, value in properties.items():
            b = bias.get(prop)
            values[prop] = {
                "value": value / b if b else value,
                "corrected": bool(b),
            }
        corrected_arm[model] = {"bias_class": "test", "values": values}
    return {
        "group": group,
        "formula": cid,
        "structure_type": "perovskite",
        "composition": {},
        "references": references,
        "per_model": per_model,
        "corrected_arm": corrected_arm,
        "gates": {},
        "verdict": "CERTIFIED",
    }


@pytest.fixture()
def reports(tmp_path: Path) -> tuple[Path, Path]:
    """Group 'good': a0+b0 biases genuinely help -> PASS. Group 'bad': the
    a0 bias hurts, b0/cij uncorrected -> FAIL. Cij never corrected anywhere
    (the silent Round-1 degradation). One excluded candidate id exercises the
    prereg exclusion list."""
    refs_all = {"a0": 5.0, "b0": 20.0, "c11": 50.0, "c12": 10.0, "c44": 5.0}
    candidates = {
        # raw 10% high on a0/b0; bias 1.1 -> corrected lands ~exactly on ref
        "good-1": _candidate(
            "good-1", "good", dict(refs_all),
            {"a0": 5.5, "b0": 22.0, "c11": 55.0, "c12": 11.0, "c44": 5.5},
            {"a0": 1.1, "b0": 1.1},
        ),
        "good-2": _candidate(
            "good-2", "good", dict(refs_all),
            {"a0": 5.6, "b0": 22.2, "c11": 56.0, "c12": 11.2, "c44": 5.6},
            {"a0": 1.1, "b0": 1.1},
        ),
        # raw already ~on ref; deflating by 1.1 pushes it away -> worsens
        "bad-1": _candidate(
            "bad-1", "bad", dict(refs_all),
            {"a0": 5.0, "b0": 20.0, "c11": 50.0, "c12": 10.0, "c44": 5.0},
            {"a0": 1.1},
        ),
        # prereg-excluded Cij cells: candidate id on the exclusion list
        "hp-cssni3": _candidate(
            "hp-cssni3", "good", dict(refs_all),
            {"a0": 5.5, "b0": 22.0, "c11": 55.0, "c12": 11.0, "c44": 5.5},
            {"a0": 1.1, "b0": 1.1},
        ),
    }
    round1 = {
        "schema": "lupine.candidate_campaign.v1",
        "generated_at": "2026-07-13T14:14:06+00:00",
        "parameters": {"device": "cpu"},
        "candidates": candidates,
    }
    rows = []
    for cid, sub in candidates.items():
        for model in MODELS:
            for prop, ref in sub["references"].items():
                if ref is None:
                    continue
                rows.append(
                    {
                        "group": sub["group"],
                        "candidate": cid,
                        "model": model,
                        "prop": prop,
                        "reference": ref,
                        "raw": sub["per_model"][model]["properties"][prop],
                        "cross_class": sub["corrected_arm"][model]["values"][prop][
                            "value"
                        ],
                    }
                )
    round2 = {
        "schema": "lupine.campaign_round2.v1",
        "generated_at": "2026-07-13T14:19:29+00:00",
        "rows": rows,
    }
    r1 = tmp_path / "round1_report.json"
    r2 = tmp_path / "round2_report.json"
    r1.write_text(json.dumps(round1), encoding="utf-8")
    r2.write_text(json.dumps(round2), encoding="utf-8")
    return r1, r2


# --------------------------------------------------------------------------
# cell collection + exclusions
# --------------------------------------------------------------------------


class TestCollectCells:
    def test_exclusions_never_pooled(self, reports: tuple[Path, Path]) -> None:
        round1 = json.loads(reports[0].read_text(encoding="utf-8"))
        cells, excluded = erc.collect_cells(round1)
        assert all(
            (c.candidate, c.prop) not in erc.PREREG_EXCLUSIONS for c in cells
        )
        # hp-cssni3 c11/c12/c44 x 4 models = 12 excluded cells.
        assert len(excluded) == 12
        assert {e["candidate"] for e in excluded} == {"hp-cssni3"}

    def test_null_references_skipped(self, reports: tuple[Path, Path]) -> None:
        round1 = json.loads(reports[0].read_text(encoding="utf-8"))
        round1["candidates"]["good-1"]["references"]["c44"] = None
        cells, _ = erc.collect_cells(round1)
        assert not any(c.candidate == "good-1" and c.prop == "c44" for c in cells)


# --------------------------------------------------------------------------
# group evaluation (S4 exactly)
# --------------------------------------------------------------------------


class TestEvaluateGroup:
    def _cells(self, reports: tuple[Path, Path]) -> list:
        round1 = json.loads(reports[0].read_text(encoding="utf-8"))
        return erc.collect_cells(round1)[0]

    def test_good_group_passes_two_of_three(self, reports: tuple[Path, Path]) -> None:
        result = erc.evaluate_group("good", self._cells(reports))
        assert result["legs"]["a0"]["criterion_met"] is True
        assert result["legs"]["b0"]["criterion_met"] is True
        assert result["legs"]["cij"]["criterion_met"] is False
        assert result["n_legs_met"] == 2
        assert result["verdict"] == "PASS"

    def test_cij_all_ties_carries_degradation_note(
        self, reports: tuple[Path, Path]
    ) -> None:
        result = erc.evaluate_group("good", self._cells(reports))
        cij = result["legs"]["cij"]
        assert cij["n_corrected_cells"] == 0
        assert cij["sign_test"]["n_ties_dropped"] == cij["n_cells"]
        assert cij["sign_test"]["p_two_sided_exact"] is None
        assert "2-of-2" in cij["note"]

    def test_bad_group_fails(self, reports: tuple[Path, Path]) -> None:
        result = erc.evaluate_group("bad", self._cells(reports))
        assert result["legs"]["a0"]["criterion_met"] is False
        assert result["legs"]["a0"]["reduces_median"] is False
        assert result["verdict"] == "FAIL"

    def test_ties_are_dropped_from_sign_test(self, reports: tuple[Path, Path]) -> None:
        result = erc.evaluate_group("bad", self._cells(reports))
        b0 = result["legs"]["b0"]  # uncorrected everywhere -> all ties
        assert b0["sign_test"]["n_ties_dropped"] == b0["n_cells"]
        assert b0["sign_test"]["p_two_sided_exact"] is None


# --------------------------------------------------------------------------
# round-2 cross-check + end-to-end
# --------------------------------------------------------------------------


class TestEndToEnd:
    def test_writes_artifact_with_verdicts(
        self, reports: tuple[Path, Path], tmp_path: Path
    ) -> None:
        out = tmp_path / "criteria_evaluation.json"
        rc = erc.main(
            [
                "--round1-report", str(reports[0]),
                "--round2-report", str(reports[1]),
                "--out", str(out),
            ]
        )
        assert rc == 0
        artifact = json.loads(out.read_text(encoding="utf-8"))
        assert artifact["schema"] == "lupine.round1_criteria_evaluation.v1"
        assert artifact["groups"]["good"]["verdict"] == "PASS"
        assert artifact["groups"]["bad"]["verdict"] == "FAIL"
        assert artifact["round2_cross_check"]["consistent"] is True
        assert artifact["round2_cross_check"]["n_mismatches"] == 0
        assert len(artifact["excluded_cells"]) == 12
        assert any("errata finding 8" in note for note in artifact["notes"])
        assert "good" in artifact["gates_descriptive"]

    def test_round2_mismatch_refuses_to_evaluate(
        self, reports: tuple[Path, Path], tmp_path: Path
    ) -> None:
        round2 = json.loads(reports[1].read_text(encoding="utf-8"))
        round2["rows"][0]["cross_class"] += 0.5  # corrupt one cell
        bad_r2 = tmp_path / "bad_round2.json"
        bad_r2.write_text(json.dumps(round2), encoding="utf-8")
        out = tmp_path / "out.json"
        rc = erc.main(
            [
                "--round1-report", str(reports[0]),
                "--round2-report", str(bad_r2),
                "--out", str(out),
            ]
        )
        assert rc == 1
        assert not out.exists()

    def test_wrong_schema_fails(self, reports: tuple[Path, Path], tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"schema": "other.v1"}), encoding="utf-8")
        rc = erc.main(
            [
                "--round1-report", str(bad),
                "--round2-report", str(reports[1]),
                "--out", str(tmp_path / "o.json"),
            ]
        )
        assert rc == 1
