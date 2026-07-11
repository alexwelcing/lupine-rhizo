"""Regression test for the env-field binder.

The binder (``python/scripts/bind_env_field_instances.py``) is the only code
path that turns Y-matrix statics runs into the Lean module and JSON report
consumed by the certificate gate and promotion scripts. This test regenerates
the artifacts into a temporary directory and checks that the output is
structurally consistent with the committed report — so refactors of the binder
break CI instead of silently changing the formal corpus.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lupine_distill.odf.field_certificates import (
    ANCHOR_COORDINATIONS,
    certificates_from_binding_report,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BINDER = _REPO_ROOT / "python" / "scripts" / "bind_env_field_instances.py"
_COMMITTED_REPORT = (
    _REPO_ROOT / "data" / "y_matrix_runs" / "env_field_binding_report.json"
)


def _run_binder(tmp_path: Path) -> tuple[Path, Path]:
    lean_out = tmp_path / "EnvFieldInstances.lean"
    report_out = tmp_path / "env_field_binding_report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(_BINDER),
            "--lean-out",
            str(lean_out),
            "--report-out",
            str(report_out),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"binder exited {result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return lean_out, report_out


def test_binder_report_schema_and_counts(tmp_path: Path):
    _, report_out = _run_binder(tmp_path)
    report = json.loads(report_out.read_text(encoding="utf-8"))

    assert report.get("schema") == "lupine.env_field_binding_report.v2"
    assert report.get("corpus_sha256_12")
    assert report.get("generator") == "python/scripts/bind_env_field_instances.py"

    committed = json.loads(_COMMITTED_REPORT.read_text(encoding="utf-8"))
    # Structural counts must match the committed report for the same input
    # corpus. If the statics/targets change, this assertion is the canary that
    # forces an intentional update of the committed artifacts.
    assert report["n_cells"] == committed["n_cells"]
    assert report["n_instances"] == committed["n_instances"]
    assert report["n_refusals"] == committed["n_refusals"]
    for structure in report["structures"]:
        committed_struct = committed["structures"][structure]
        assert report["structures"][structure]["n_cells"] == committed_struct["n_cells"]
        assert (
            report["structures"][structure]["n_instances"]
            == committed_struct["n_instances"]
        )
        assert (
            report["structures"][structure]["n_refusals"]
            == committed_struct["n_refusals"]
        )


def test_binder_cells_carry_required_fields(tmp_path: Path):
    _, report_out = _run_binder(tmp_path)
    report = json.loads(report_out.read_text(encoding="utf-8"))

    assert len(report["cells"]) == report["n_cells"]
    for cell in report["cells"]:
        assert isinstance(cell["material"], str)
        assert isinstance(cell["model_id"], str)
        assert cell["structure"] in ANCHOR_COORDINATIONS
        assert cell["lean_name"]
        assert isinstance(cell["valid"], bool)
        assert len(cell["anchors"]) == len(ANCHOR_COORDINATIONS[cell["structure"]])
        for anchor in cell["anchors"]:
            assert isinstance(anchor["coordination"], int)
            assert isinstance(anchor["p_scaled"], int)


def test_binder_certificates_match_report(tmp_path: Path):
    """The same report must yield the same certificate entries the gate uses."""
    _, report_out = _run_binder(tmp_path)
    report = json.loads(report_out.read_text(encoding="utf-8"))
    entries = certificates_from_binding_report(report)
    assert len(entries) == report["n_cells"]
    assert all(
        entry["certificate"].structure == entry["structure"]
        for entry in entries
    )


def test_binder_lean_module_is_generated(tmp_path: Path):
    lean_out, _ = _run_binder(tmp_path)
    lean_text = lean_out.read_text(encoding="utf-8")
    assert "namespace OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances" in lean_text
    assert "cells_accounted" in lean_text
    assert "0 sorry" in lean_text
