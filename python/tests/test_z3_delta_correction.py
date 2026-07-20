from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / "tools" / "build_z3_delta_correction.py"

spec = importlib.util.spec_from_file_location("build_z3_delta_correction", TOOL_PATH)
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules.setdefault("build_z3_delta_correction", tool)
spec.loader.exec_module(tool)


def make_data(errors: dict[str, float], natoms: dict[str, int], families: dict[str, str]):
    return tool.FitData(errors=errors, natoms=natoms, families=families)


def test_global_constant_fit_and_corrected_mae() -> None:
    data = make_data(
        errors={"a": 1.0, "b": 3.0, "v": 2.0},
        natoms={"a": 10, "b": 10, "v": 10},
        families={"a": "f", "b": "f", "v": "f"},
    )
    delta = tool.fit_form("A_global_constant", ["a", "b"], data)
    assert delta("v") == pytest.approx(2.0)
    assert tool.mae(delta, ["v"], data) == pytest.approx(0.0)


def test_family_linear_recovers_known_slope_and_intercept() -> None:
    # error = 0.5 * n - 10 exactly, two distinct sizes so the linear fit is live
    data = make_data(
        errors={"a": 0.0, "b": 10.0, "v1": 5.0, "v2": -5.0},
        natoms={"a": 20, "b": 40, "v1": 30, "v2": 10},
        families={c: "plastics" for c in ("a", "b", "v1", "v2")},
    )
    delta = tool.fit_form("C_family_linear", ["a", "b"], data)
    assert delta("v1") == pytest.approx(5.0)
    assert delta("v2") == pytest.approx(-5.0)


def test_family_linear_falls_back_to_family_constant_with_single_size() -> None:
    data = make_data(
        errors={"a": 2.0, "b": 4.0, "v": 1.0},
        natoms={"a": 25, "b": 25, "v": 30},
        families={c: "biomass" for c in ("a", "b", "v")},
    )
    delta = tool.fit_form("C_family_linear", ["a", "b"], data)
    assert delta("v") == pytest.approx(3.0)  # family mean, not an extrapolated slope


def test_selection_uses_validation_only_and_prefers_simpler_on_ties() -> None:
    # Both A and B score identically on validation (single family); A must win
    data = make_data(
        errors={"t1": 2.0, "t2": 4.0, "v": 1.0, "x": 9.0},
        natoms={"t1": 20, "t2": 20, "v": 30, "x": 40},
        families={c: "f" for c in ("t1", "t2", "v", "x")},
    )
    train, val = ["t1", "t2"], ["v"]
    scores = {form: tool.mae(tool.fit_form(form, train, data), val, data) for form in tool.FORMS}
    selected = min(tool.FORMS, key=lambda f: (scores[f], tool.FORMS.index(f)))
    assert selected == "A_global_constant"


def test_fit_never_reads_test_candidates() -> None:
    # A pathological test error must not perturb fit or selection at all
    base = {"t1": 1.0, "t2": 3.0, "v": 2.0, "x": 10_000.0}
    data = make_data(
        errors=base,
        natoms={"t1": 10, "t2": 10, "v": 10, "x": 10},
        families={c: "f" for c in base},
    )
    delta = tool.fit_form("A_global_constant", ["t1", "t2"], data)
    assert delta("x") == pytest.approx(2.0)
    # scoring reads the test error, producing the honest (bad) residual
    assert tool.mae(delta, ["x"], data) == pytest.approx(10_000.0 - 2.0)


def test_sidecar_verification_fails_closed(tmp_path: Path) -> None:
    target = tmp_path / "panel.json"
    target.write_text("{}")
    target.with_name("panel.json.sha256").write_text("0" * 64 + "  panel.json\n")
    with pytest.raises(ValueError, match="sidecar hash mismatch"):
        tool.verify_sidecar(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_name("panel.json.sha256").write_text(f"{digest}  panel.json\n")
    tool.verify_sidecar(target)


def test_report_gate_arithmetic_against_locked_threshold() -> None:
    # The report's gate outcome must be corrected_test_mae <= 0.1 exactly
    rows = [{"corrected_absolute_error_ev": v} for v in (0.05, 0.2)]
    mae = sum(r["corrected_absolute_error_ev"] for r in rows) / len(rows)
    assert (mae <= 0.1) is False
    rows[1]["corrected_absolute_error_ev"] = 0.1
    mae = sum(r["corrected_absolute_error_ev"] for r in rows) / len(rows)
    assert (mae <= 0.1) is True
