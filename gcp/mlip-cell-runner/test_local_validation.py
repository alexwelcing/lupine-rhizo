"""End-to-end test for the local workstation validation driver.

Runs hpc/local_validation/run_validation.py as a subprocess with the mock
backend on CPU against the small in-tree fixture: fast, offline, and no MLIP
checkpoint download. Asserts the aggregated report.json + report.md exist,
parse, and carry the headline fields the meeting handout relies on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "hpc" / "local_validation" / "run_validation.py"
MANIFEST_PATH = Path(__file__).with_name("fixtures") / "ni_fcc_eam_distill_support_v1.json"
DEFAULT_ROWS = ("energy_volume", "forces", "elastic_constants")


@pytest.mark.integration
def test_run_validation_end_to_end_mock_cpu(tmp_path: Path) -> None:
    out_dir = tmp_path / "local-validation-out"
    proc = subprocess.run(
        [
            sys.executable,
            str(DRIVER_PATH),
            "--run-id", "lv-test",
            "--mlip", "mock-mlip",
            "--device", "cpu",
            "--manifest", str(MANIFEST_PATH),
            "--out", str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr

    report_json = out_dir / "report.json"
    report_md = out_dir / "report.md"
    assert report_json.exists()
    assert report_md.exists()

    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert report["schema"] == "lupine.mlip.local_validation_report.v1"
    assert report["run_id"] == "lv-test"
    assert report["devices"] == ["cpu"]
    assert report["summary"] == {"cells_total": 3, "cells_ok": 3, "cells_failed": 0}

    cells = {cell["row_id"]: cell for cell in report["cells"]}
    assert set(cells) == set(DEFAULT_ROWS)
    for row_id, cell in cells.items():
        assert cell["ok"] is True
        assert cell["exit_code"] == 0
        assert cell["mlip_id"] == "mock-mlip"
        assert cell["device"] == "cpu"
        assert cell["wall_seconds"] > 0
        metrics = cell["metrics"]
        assert metrics["primary_metric"]
        assert isinstance(metrics["error"], float)
        assert isinstance(metrics["accuracy_score"], float)
        assert metrics["n_structures"] >= 5
        # The raw runner artifact is preserved next to the aggregate.
        artifact = json.loads(Path(cell["artifact_path"]).read_text(encoding="utf-8"))
        assert artifact["schema"] == "lupine.mlip.cell_artifact.v1"
        assert artifact["row_id"] == row_id

    # cpu-only run: no speedup rows, and the markdown says so honestly.
    assert report["speedups"] == []
    markdown = report_md.read_text(encoding="utf-8")
    assert "| energy_volume | mock-mlip | cpu |" in markdown
    assert "## Notes" in markdown
    assert "cpu_vs_gpu speedups are unavailable" in markdown
