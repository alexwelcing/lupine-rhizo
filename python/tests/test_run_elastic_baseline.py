"""Tests for run_elastic_baseline.py threshold derivation (rederive-only path).

CPU-only synthetic evidence in tmp dirs; no calculator ever loads. Covers the
Round-3 registered instrument fix 1: floored-v1 dispersion metric, the
--rederive-only mode (thresholds from already-measured evidence, no GPU), and
the V/Cr calibration-cell audit block.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_elastic_baseline as reb  # noqa: E402

pytestmark = pytest.mark.unit

MODELS = ("model-a", "model-b", "model-c", "model-d")

#: Synthetic bcc-like baseline; V's C44 straddles zero (the registered
#: sign-crossing pathology), everything else is healthy.
_C44_BY_MATERIAL = {
    "W": (120.0, 150.0, 140.0, 130.0),
    "Mo": (90.0, 110.0, 100.0, 105.0),
    "Cr": (40.0, 90.0, 60.0, 70.0),
    "Nb": (20.0, 45.0, 30.0, 35.0),
    "Ta": (60.0, 75.0, 70.0, 65.0),
    "V": (-20.0, 30.0, 5.0, -5.0),
}


def _write_evidence(directory: Path, material: str, model: str, c44: float, bump: float) -> None:
    payload = {
        "schema": "lupine.mlip.calc_evidence.v1",
        "material": material,
        "source": {"model_id": model, "backend": "ase", "device": "cpu"},
        "properties": [
            {"name": "a0", "value": 3.2 + bump * 0.01, "unit": "Angstrom"},
            {"name": "B0", "value": 180.0 + bump, "unit": "GPa"},
            {"name": "C11", "value": 300.0 + bump * 5.0, "unit": "GPa"},
            {"name": "C12", "value": 120.0 + bump * 2.0, "unit": "GPa"},
            {"name": "C44", "value": c44, "unit": "GPa"},
        ],
    }
    path = directory / f"{material}_bcc_{model}.evidence.json"
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture()
def evidence_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "elastic_baseline"
    directory.mkdir()
    for material, c44_values in _C44_BY_MATERIAL.items():
        for bump, (model, c44) in enumerate(zip(MODELS, c44_values)):
            _write_evidence(directory, material, model, c44, float(bump))
    summary = {
        "schema": "lupine.elastic_baseline_summary.v1",
        "generated_at": "2026-07-13T13:08:11+00:00",
        "device": "cuda",
        "models": list(MODELS),
        "calculator_versions": {m: f"{m} 1.0" for m in MODELS},
        "materials": [f"{m}_bcc" for m in _C44_BY_MATERIAL],
        "parameters": {"elastic_delta": 0.005, "elastic_relax_internal": True},
    }
    (directory / "baseline_summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    return directory


class TestAuditCalibrationCells:
    def test_v_c44_flagged_as_sign_crossing(self, evidence_dir: Path) -> None:
        audit = reb.audit_calibration_cells(evidence_dir)
        cell = audit["cells"]["V.c44"]
        assert cell["sign_crossing_predictions"] is True
        # Median of (-20, -5, 5, 30) is exactly 0 -> unfloored undefined.
        assert cell["dispersion_unfloored"] is None
        assert math.isfinite(cell["dispersion_floored_v1"])
        assert cell["floor_engaged"] is True
        assert "sign-crossing" in audit["note"]

    def test_cr_c44_healthy_and_unchanged(self, evidence_dir: Path) -> None:
        audit = reb.audit_calibration_cells(evidence_dir)
        cell = audit["cells"]["Cr.c44"]
        assert cell["sign_crossing_predictions"] is False
        assert cell["floor_engaged"] is False
        assert cell["dispersion_floored_v1"] == pytest.approx(
            cell["dispersion_unfloored"]
        )


class TestRederiveOnly:
    def test_rederives_thresholds_without_calculators(
        self, evidence_dir: Path, tmp_path: Path
    ) -> None:
        thresholds_out = tmp_path / "thresholds.v2.json"
        rc = reb.main(
            [
                "--rederive-only",
                "--out-dir", str(evidence_dir),
                "--thresholds-out", str(thresholds_out),
            ]
        )
        assert rc == 0
        artifact = json.loads(thresholds_out.read_text(encoding="utf-8"))
        assert artifact["schema"] == "lupine.discovery_gates.thresholds.v2"
        assert artifact["rederived_from_existing_evidence"] is True
        assert artifact["dispersion_metric"]["version"] == "floored-v1"
        assert artifact["dispersion_metric"]["floor_fraction"] == pytest.approx(0.1)
        # Provenance carried over from the measurement run's summary.
        assert artifact["device"] == "cuda"
        assert artifact["models"] == list(MODELS)
        assert set(artifact["per_property"]) == {"a0", "b0", "c11", "c12", "c44"}
        for entry in artifact["per_property"].values():
            assert "floored-v1" in entry["source"]
            assert math.isfinite(entry["flag"]) and math.isfinite(entry["refuse"])
        # The sign-crossing V cell is finite and audited.
        c44_dispersions = dict(
            (label, value)
            for label, value in artifact["per_property"]["c44"]["sample_dispersions"]
        )
        assert math.isfinite(c44_dispersions["V"])
        assert artifact["calibration_cell_audit"]["cells"]["V.c44"][
            "sign_crossing_predictions"
        ] is True
        assert any("floored-v1" in note for note in artifact["notes"])

    def test_missing_summary_fails_cleanly(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        rc = reb.main(
            [
                "--rederive-only",
                "--out-dir", str(empty),
                "--thresholds-out", str(tmp_path / "t.json"),
            ]
        )
        assert rc == 1
        assert not (tmp_path / "t.json").exists()
