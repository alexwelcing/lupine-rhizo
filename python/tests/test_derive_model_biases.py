"""Tests for derive_model_biases.py (calibration biases from existing evidence).

CPU-only: everything works on synthetic JSON files in tmp_path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import derive_model_biases as dmb  # noqa: E402

from lupine_distill.statics import InputValidationError  # noqa: E402

pytestmark = pytest.mark.unit


def _write_evidence(
    directory: Path,
    material: str,
    model: str,
    properties: list[dict[str, object]],
) -> None:
    payload = {
        "schema": "lupine.mlip.calc_evidence.v1",
        "material": material,
        "source": {"model_id": model, "backend": "ase", "device": "cpu"},
        "properties": properties,
    }
    (directory / f"{material}_{model}.evidence.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _prop(name: str, value: float, reference: float | None) -> dict[str, object]:
    return {
        "name": name,
        "value": value,
        "unit": "GPa",
        "reference_value": reference,
        "reference_source": "synthetic" if reference is not None else None,
    }


@pytest.fixture()
def evidence_dir(tmp_path: Path) -> Path:
    """Two models over three materials (two fcc metals + one non-fcc).

    Ratios are chosen so medians are hand-checkable:
    m1 a0 ratios: Cu 1.10, Ni 1.20, W 1.30 -> all median 1.20, fcc 1.15
    m1 B0 ratios: Cu 0.90, Ni 0.80, W 0.70 -> all median 0.80, fcc 0.85
    m2 is unbiased everywhere (ratio 1.0).
    """
    directory = tmp_path / "bound"
    directory.mkdir()
    refs = {"Cu": (3.6, 140.0), "Ni": (3.5, 180.0), "W": (3.16, 310.0)}
    m1_ratios = {"Cu": (1.10, 0.90), "Ni": (1.20, 0.80), "W": (1.30, 0.70)}
    for material, (a_ref, b_ref) in refs.items():
        ra, rb = m1_ratios[material]
        _write_evidence(
            directory,
            material,
            "m1",
            [_prop("a0", a_ref * ra, a_ref), _prop("B0", b_ref * rb, b_ref)],
        )
        _write_evidence(
            directory,
            material,
            "m2",
            [_prop("a0", a_ref, a_ref), _prop("B0", b_ref, b_ref)],
        )
    return directory


class TestLoadPredictionRatios:
    def test_ratios_computed(self, evidence_dir: Path) -> None:
        ratios = dmb.load_prediction_ratios(evidence_dir, "a0")
        assert ratios["Cu"]["m1"] == pytest.approx(1.10)
        assert ratios["Ni"]["m1"] == pytest.approx(1.20)
        assert ratios["Cu"]["m2"] == pytest.approx(1.0)

    def test_null_reference_skipped(self, tmp_path: Path) -> None:
        directory = tmp_path / "bound"
        directory.mkdir()
        _write_evidence(directory, "Cu", "m1", [_prop("a0", 3.6, None)])
        assert dmb.load_prediction_ratios(directory, "a0") == {}

    def test_missing_directory_errors(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError, match="does not exist"):
            dmb.load_prediction_ratios(tmp_path / "nope", "a0")

    def test_non_evidence_files_ignored(self, evidence_dir: Path) -> None:
        (evidence_dir / "binding_report.json").write_text(
            json.dumps({"schema": "other"}), encoding="utf-8"
        )
        ratios = dmb.load_prediction_ratios(evidence_dir, "a0")
        assert set(ratios) == {"Cu", "Ni", "W"}


class TestDeriveScalarBiases:
    def test_medians_per_class(self, evidence_dir: Path) -> None:
        biases, counts = dmb.derive_scalar_biases(evidence_dir)
        assert biases["m1"]["a0"]["all-21"] == pytest.approx(1.20)
        assert biases["m1"]["a0"]["fcc-metals"] == pytest.approx(1.15)
        assert biases["m1"]["b0"]["all-21"] == pytest.approx(0.80)
        assert biases["m1"]["b0"]["fcc-metals"] == pytest.approx(0.85)
        assert biases["m2"]["a0"]["all-21"] == pytest.approx(1.0)
        assert counts["m1"]["a0"]["all-21"] == 3
        assert counts["m1"]["a0"]["fcc-metals"] == 2

    def test_no_references_errors(self, tmp_path: Path) -> None:
        directory = tmp_path / "bound"
        directory.mkdir()
        _write_evidence(directory, "Cu", "m1", [_prop("a0", 3.6, None)])
        with pytest.raises(InputValidationError, match="cannot calibrate"):
            dmb.derive_scalar_biases(directory)


class TestCijInspection:
    def test_missing_file(self, tmp_path: Path) -> None:
        result = dmb.inspect_cij_calibration(tmp_path / "results.json")
        assert result["available"] is False
        assert "not found" in result["reason"]

    def test_single_model_study_unavailable(self, tmp_path: Path) -> None:
        path = tmp_path / "results.json"
        path.write_text(
            json.dumps({"arms": {"raw": {"predictions": {"Cu": [200, 120, 70]}}}}),
            encoding="utf-8",
        )
        result = dmb.inspect_cij_calibration(path)
        assert result["available"] is False
        assert "single-model" in result["reason"]

    def test_local_model_data_flagged_for_extension(self, tmp_path: Path) -> None:
        path = tmp_path / "results.json"
        path.write_text(
            json.dumps({"per_model": {"chgnet": {"Cu": [200, 120, 70]}}}),
            encoding="utf-8",
        )
        result = dmb.inspect_cij_calibration(path)
        assert result["available"] is False
        assert "no validated extractor" in result["reason"]


class TestEndToEnd:
    def test_main_writes_artifact(self, evidence_dir: Path, tmp_path: Path) -> None:
        out = tmp_path / "candidates" / "model_biases.v1.json"
        rc = dmb.main(
            [
                "--evidence-dir", str(evidence_dir),
                "--elastic-results", str(tmp_path / "absent.json"),
                "--out", str(out),
            ]
        )
        assert rc == 0
        artifact = json.loads(out.read_text(encoding="utf-8"))
        assert artifact["schema"] == "lupine.model_biases.v1"
        assert artifact["biases"]["m1"]["a0"]["all-21"] == pytest.approx(1.20)
        assert artifact["cij"]["available"] is False
        prov = artifact["provenance"]
        assert "median" in prov["formula"]
        assert prov["class_definitions"]["all-21"] == ["Cu", "Ni", "W"]
        assert prov["class_definitions"]["fcc-metals"] == ["Cu", "Ni"]
