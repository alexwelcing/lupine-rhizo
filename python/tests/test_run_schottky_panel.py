"""Tests for run_schottky_panel.py (Schottky panel runner, GPU lane).

CPU-only: the a0 loader, evidence assembly, dispersion summary and the main
orchestration are exercised with a stubbed calculator factory and a stubbed
``compute_schottky_formation`` — no MLIP ever loads and no relaxation runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_schottky_panel as rsp  # noqa: E402

from lupine_distill.schemas import CalcEvidence  # noqa: E402
from lupine_distill.statics import (  # noqa: E402
    InputValidationError,
    SchottkyFormationResult,
)

pytestmark = pytest.mark.unit


def _halide_report(a0_by_cell: dict[tuple[str, str], float]) -> dict:
    subjects: dict[str, dict] = {}
    for (formula, model), a0 in a0_by_cell.items():
        subject = subjects.setdefault(
            f"{formula}_rocksalt",
            {"formula": formula, "structure_type": "rocksalt", "per_model": {}},
        )
        subject["per_model"][model] = {"properties": {"a0": a0}}
    return {
        "schema": "lupine.discovery_gates.v1",
        "generated_at": "2026-07-13T13:17:10+00:00",
        "subjects": subjects,
    }


@pytest.fixture()
def report_path(tmp_path: Path) -> Path:
    cells = {
        ("LiF", "chgnet"): 4.09,
        ("LiF", "mace-mp-small"): 4.12,
        ("NaCl", "chgnet"): 5.69,
        ("NaCl", "mace-mp-small"): 5.72,
    }
    path = tmp_path / "halide_report.json"
    path.write_text(json.dumps(_halide_report(cells)), encoding="utf-8")
    return path


def _stub_result(formula: str, a0: float, pair_ev: float) -> SchottkyFormationResult:
    return SchottkyFormationResult(
        formula=formula,
        structure_type="rocksalt",
        a0_angstrom=a0,
        supercell=(2, 2, 2),
        removed_indices=(0, 63),
        removed_species=("A", "B"),
        pair_separation_angstrom=a0 * 1.7,
        n_atoms_perfect=64,
        e_bulk_ev=-256.0,
        e_defect_ev=-256.0 * 62.0 / 64.0 + pair_ev,
        schottky_pair_ev=pair_ev,
        schottky_per_vacancy_ev=pair_ev / 2.0,
        n_relax_steps=17,
        fmax=0.01,
        optimizer="FIRE",
        max_steps=500,
        wall_time_seconds=1.0,
    )


# --------------------------------------------------------------------------
# a0 reuse
# --------------------------------------------------------------------------


def test_load_relaxed_a0_maps_cells_with_provenance(report_path: Path) -> None:
    a0_map, provenance = rsp.load_relaxed_a0(report_path)
    assert a0_map[("LiF", "chgnet")] == pytest.approx(4.09)
    assert a0_map[("NaCl", "mace-mp-small")] == pytest.approx(5.72)
    assert provenance["generated_at"] == "2026-07-13T13:17:10+00:00"
    assert provenance["report"].endswith("halide_report.json")


def test_load_relaxed_a0_skips_error_cells(tmp_path: Path) -> None:
    report = _halide_report({("LiF", "chgnet"): 4.09})
    report["subjects"]["LiF_rocksalt"]["per_model"]["broken"] = {"error": "boom"}
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    a0_map, _ = rsp.load_relaxed_a0(path)
    assert ("LiF", "broken") not in a0_map
    assert ("LiF", "chgnet") in a0_map


def test_load_relaxed_a0_rejects_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")
    with pytest.raises(InputValidationError, match="expected schema"):
        rsp.load_relaxed_a0(path)


def test_load_relaxed_a0_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="missing"):
        rsp.load_relaxed_a0(tmp_path / "nope.json")


# --------------------------------------------------------------------------
# evidence assembly + dispersion summary
# --------------------------------------------------------------------------


def test_evidence_from_result_is_schema_valid() -> None:
    result = _stub_result("LiF", 4.09, pair_ev=2.5)
    payload = rsp.evidence_from_result(
        result=result,
        model_id="chgnet",
        device="cpu",
        calculator_version="chgnet 0.4.2",
        a0_provenance={"report": "data/x/report.json", "generated_at": "t"},
        run_label="test",
    )
    evidence = CalcEvidence.model_validate(payload)
    assert evidence.material == "LiF"
    by_name = {p.name: p.value for p in evidence.properties}
    assert by_name["E_schottky_pair"] == pytest.approx(2.5)
    assert by_name["E_schottky_per_vacancy"] == pytest.approx(1.25)
    assert evidence.provenance.inputs_sha256  # canonical-inputs hash present


def test_evidence_inputs_hash_covers_a0_source() -> None:
    result = _stub_result("LiF", 4.09, pair_ev=2.5)
    kwargs = dict(
        result=result,
        model_id="chgnet",
        device="cpu",
        calculator_version="chgnet 0.4.2",
        run_label=None,
    )
    a = rsp.evidence_from_result(
        a0_provenance={"report": "r1.json", "generated_at": "t1"}, **kwargs
    )
    b = rsp.evidence_from_result(
        a0_provenance={"report": "r2.json", "generated_at": "t2"}, **kwargs
    )
    assert a["provenance"]["inputs_sha256"] != b["provenance"]["inputs_sha256"]


def test_summarize_dispersions_per_compound() -> None:
    summary = rsp.summarize_dispersions(
        {
            "LiF": {"chgnet": 2.0, "mace-mp-small": 2.5},
            "NaCl": {"chgnet": 2.2},
        }
    )
    lif = summary["LiF"]
    assert lif["n_models"] == 2
    assert lif["absolute_spread_ev"] == pytest.approx(0.5)
    assert lif["relative_dispersion"] == pytest.approx(0.5 / 2.25)
    assert summary["NaCl"]["n_models"] == 1
    assert "note" in summary["NaCl"]


# --------------------------------------------------------------------------
# CLI plumbing
# --------------------------------------------------------------------------


def test_select_compounds_default_is_full_panel() -> None:
    assert rsp.select_compounds("") == rsp.PANEL_COMPOUNDS
    assert rsp.select_compounds("LiF,MgO") == (("LiF", "rocksalt"), ("MgO", "rocksalt"))


def test_select_compounds_unknown_exits() -> None:
    with pytest.raises(SystemExit, match="unknown compound"):
        rsp.select_compounds("Kryptonite")


def test_main_rejects_supercell_below_two(report_path: Path, tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="supercell"):
        rsp.main(
            [
                "--device",
                "cpu",
                "--supercell",
                "1",
                "--halide-report",
                str(report_path),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )


def test_main_smoke_with_stubbed_compute(
    report_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full orchestration without any calculator: stubbed factory + statics."""

    monkeypatch.setattr(
        rsp, "build_calculator", lambda model_id, device: (object(), f"{model_id} stub")
    )

    def fake_compute(calculator, formula, structure_type, a0, *, supercell):
        assert structure_type == "rocksalt"
        assert supercell == (2, 2, 2)
        return _stub_result(formula, a0, pair_ev=a0 / 2.0)  # model-dependent via a0

    monkeypatch.setattr(rsp, "compute_schottky_formation", fake_compute)
    out_dir = tmp_path / "panel"
    rc = rsp.main(
        [
            "--device",
            "cpu",
            "--models",
            "chgnet,mace-mp-small",
            "--compounds",
            "LiF,NaCl",
            "--halide-report",
            str(report_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    evidence_files = sorted(p.name for p in out_dir.glob("*.evidence.json"))
    assert evidence_files == [
        "LiF_rocksalt_chgnet.evidence.json",
        "LiF_rocksalt_mace-mp-small.evidence.json",
        "NaCl_rocksalt_chgnet.evidence.json",
        "NaCl_rocksalt_mace-mp-small.evidence.json",
    ]
    for name in evidence_files:
        CalcEvidence.model_validate(json.loads((out_dir / name).read_text()))
    summary = json.loads((out_dir / "panel_summary.json").read_text(encoding="utf-8"))
    assert summary["schema"] == "lupine.schottky_panel_summary.v1"
    assert summary["n_cells_ok"] == 4
    assert summary["n_cells_failed"] == 0
    assert summary["a0_source"]["generated_at"] == "2026-07-13T13:17:10+00:00"
    dispersion = summary["cross_model_dispersion"]
    assert sorted(dispersion) == ["LiF", "NaCl"]
    # pair_ev = a0/2 so the spread mirrors the a0 spread in the report
    assert dispersion["LiF"]["absolute_spread_ev"] == pytest.approx((4.12 - 4.09) / 2)
    assert summary["notes"]


def test_main_records_missing_a0_as_failed_cell(
    report_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        rsp, "build_calculator", lambda model_id, device: (object(), "stub")
    )
    monkeypatch.setattr(
        rsp,
        "compute_schottky_formation",
        lambda calculator, formula, structure_type, a0, *, supercell: _stub_result(
            formula, a0, pair_ev=2.0
        ),
    )
    out_dir = tmp_path / "panel"
    rc = rsp.main(
        [
            "--device",
            "cpu",
            "--models",
            "chgnet",
            "--compounds",
            "LiF,MgO",  # MgO has no a0 in the synthetic report
            "--halide-report",
            str(report_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0
    summary = json.loads((out_dir / "panel_summary.json").read_text(encoding="utf-8"))
    assert summary["n_cells_ok"] == 1
    assert summary["n_cells_failed"] == 1
    assert "no relaxed a0" in summary["cells"]["MgO_rocksalt_chgnet"]["error"]
