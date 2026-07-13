"""Tests for analyze_dispersion_by_class.py (class-stratified rho analysis).

Synthetic bound evidence + synthetic Round-1 report in tmp dirs; CPU only.
"""

from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import analyze_dispersion_by_class as adc  # noqa: E402
import build_class_corpus as bcc  # noqa: E402

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import PropertyValue  # noqa: E402
from lupine_distill.statics import InputValidationError  # noqa: E402

pytestmark = pytest.mark.unit

FCC_METALS = ("Ag", "Al", "Au", "Ca", "Cu")
BCC_METALS = ("Cr", "Fe", "Mo", "Nb", "Ta")


def _write_bound_evidence(
    directory: Path, material: str, model: str, *, reference: float, error: float
) -> None:
    """Evidence whose value sits ``error`` (relative) away from ``reference``.

    model 'model-lo' sits below the reference, 'model-hi' above, so both the
    dispersion and the median |relative error| grow monotonically with
    ``error`` — a perfectly rank-correlated (rho = 1) synthetic corpus.
    """
    sign = -1.0 if model == "model-lo" else 1.0
    properties = [
        PropertyValue(
            name=name,
            value=reference * (1.0 + sign * error),
            unit=unit,
            reference_value=reference,
            reference_source="synthetic",
        )
        for name, unit in (("a0", "Angstrom"), ("B0", "GPa"))
    ]
    evidence = build_calc_evidence(
        material=material,
        model_id=model,
        device="cpu",
        inputs={"material": material, "model_id": model},
        properties=properties,
        computed_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
    )
    (directory / f"{material}_{model}.evidence.json").write_text(
        json.dumps(evidence.model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )


@pytest.fixture()
def bound_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "bound"
    directory.mkdir()
    for i, material in enumerate(FCC_METALS + BCC_METALS):
        for model in ("model-lo", "model-hi"):
            _write_bound_evidence(
                directory,
                material,
                model,
                reference=4.0 + i,
                error=0.01 * (i + 1),
            )
    return directory


def _round1_report() -> dict:
    formulas = ("CsSnCl3", "CsSnBr3", "CsSnI3", "CsGeI3", "CsPbI3")
    candidates = {}
    for i, formula in enumerate(formulas):
        ref_a0 = None if formula == "CsGeI3" else 5.5 + i
        ref_b0 = 20.0 + i
        error = 0.01 * (i + 1)
        candidates[f"hp-{formula.lower()}"] = {
            "group": "halide-perovskite",
            "formula": formula,
            "structure_type": "perovskite",
            "references": {"a0": ref_a0, "b0": ref_b0},
            "per_model": {
                "model-lo": {
                    "properties": {
                        "a0": (5.5 + i) * (1.0 - error),
                        "b0": ref_b0 * (1.0 - error),
                    }
                },
                "model-hi": {
                    "properties": {
                        "a0": (5.5 + i) * (1.0 + error),
                        "b0": ref_b0 * (1.0 + error),
                    }
                },
            },
        }
    return {
        "schema": "lupine.candidate_campaign.v1",
        "generated_at": "2026-07-13T14:14:06+00:00",
        "parameters": {"device": "cpu"},
        "candidates": candidates,
    }


@pytest.fixture()
def round1_report_path(tmp_path: Path) -> Path:
    path = tmp_path / "round1.json"
    path.write_text(json.dumps(_round1_report()), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# metals stratification
# --------------------------------------------------------------------------


def test_metals_by_class_stratifies_and_correlates(bound_dir: Path) -> None:
    results = adc.metals_by_class(bound_dir)
    assert sorted(results) == [bcc.CLASS_METALS_BCC, bcc.CLASS_METALS_FCC]
    for class_name, expected in (
        (bcc.CLASS_METALS_FCC, FCC_METALS),
        (bcc.CLASS_METALS_BCC, BCC_METALS),
    ):
        for prop in ("a0", "B0"):
            entry = results[class_name][prop]
            assert entry["n_materials"] == len(expected)
            assert sorted(entry["per_material"]) == sorted(expected)
            # synthetic corpus is perfectly rank-correlated by construction
            assert entry["spearman_rho_dispersion_vs_median_rel_error"] == pytest.approx(
                1.0
            )


def test_metals_by_class_missing_dir_fails(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="missing"):
        adc.metals_by_class(tmp_path / "nope")


# --------------------------------------------------------------------------
# perovskites from the Round-1 references
# --------------------------------------------------------------------------


def test_perovskites_rho_uses_nonnull_references(round1_report_path: Path) -> None:
    results = adc.perovskites_from_report(round1_report_path)
    assert sorted(results) == ["a0", "b0"]
    assert results["b0"]["n_materials"] == 5
    assert "small_n_warning" not in results["b0"]
    # CsGeI3 has a null a0 reference -> only 4 materials, flagged as small n
    assert results["a0"]["n_materials"] == 4
    assert "CsGeI3" not in results["a0"]["per_material"]
    assert "small_n_warning" in results["a0"]
    for prop in ("a0", "b0"):
        rho = results[prop]["spearman_rho_dispersion_vs_median_rel_error"]
        assert rho == pytest.approx(1.0)


def test_perovskites_rejects_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"schema": "wrong", "generated_at": "x"}))
    with pytest.raises(InputValidationError, match="expected schema"):
        adc.perovskites_from_report(path)


# --------------------------------------------------------------------------
# artifact + table
# --------------------------------------------------------------------------


def test_main_writes_by_class_artifact(
    bound_dir: Path, round1_report_path: Path, tmp_path: Path
) -> None:
    out = tmp_path / "by_class.json"
    rc = adc.main(
        [
            "--bound-dir",
            str(bound_dir),
            "--round1-report",
            str(round1_report_path),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["schema"] == (
        "lupine.discovery_gates.dispersion_vs_error_by_class.v1"
    )
    assert sorted(artifact["by_class"]) == sorted(
        [bcc.CLASS_METALS_FCC, bcc.CLASS_METALS_BCC, bcc.CLASS_PEROVSKITES]
    )
    for entries in artifact["by_class"].values():
        for entry in entries.values():
            rho = entry["spearman_rho_dispersion_vs_median_rel_error"]
            assert rho is None or not math.isnan(rho)


def test_main_reports_failure_on_missing_inputs(tmp_path: Path) -> None:
    rc = adc.main(
        [
            "--bound-dir",
            str(tmp_path / "nope"),
            "--round1-report",
            str(tmp_path / "nope.json"),
            "--out",
            str(tmp_path / "out.json"),
        ]
    )
    assert rc == 1
    assert not (tmp_path / "out.json").exists()


def test_render_rho_table_marks_small_n(round1_report_path: Path) -> None:
    results = {bcc.CLASS_PEROVSKITES: adc.perovskites_from_report(round1_report_path)}
    table = adc.render_rho_table(results)
    lines = [line for line in table.splitlines() if "perovskites" in line]
    assert len(lines) == 2
    a0_line = next(line for line in lines if "| a0 |" in line)
    assert "(small n)" in a0_line
