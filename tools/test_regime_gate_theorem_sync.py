from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
import regime_gate_flywheel as flywheel

_REPO = Path(__file__).resolve().parents[1]


def _write_cell(root: Path, variant: str, error: float) -> None:
    directory = root / variant / "energy_volume" / "mace"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "cell_result.json").write_text(
        json.dumps(
            {
                "accuracy": {
                    "error": error,
                    "error_unit": "ev_per_atom_mae",
                }
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("compiled", "expected_status", "expected_rc"),
    [(True, "imported", 0), (False, "failed", 1)],
)
def test_regime_gate_uses_shared_status_and_upsert_serialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    compiled: bool,
    expected_status: str,
    expected_rc: int,
) -> None:
    cells = tmp_path / "cells"
    _write_cell(cells, "baseline", 0.01)
    _write_cell(cells, "distill_accuracy", 0.005)
    monkeypatch.setattr(flywheel, "_REPO", tmp_path)
    monkeypatch.setattr(flywheel, "LEAN_OUT", tmp_path / "lean")
    monkeypatch.setattr(flywheel, "LEAN_SPEC", tmp_path / "lean-spec")
    monkeypatch.setattr(flywheel, "REPORT", tmp_path / "report.md")
    monkeypatch.setattr(flywheel, "SEED", tmp_path / "seed.sql")
    monkeypatch.setattr(flywheel, "EXTENSION", tmp_path / "extension.json")
    monkeypatch.setattr(
        flywheel.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0 if compiled else 1,
            stdout="",
            stderr="",
        ),
    )

    rc = flywheel.main([f"MPtrj-DFT={cells}"])

    assert rc == expected_rc
    sql = (tmp_path / "seed.sql").read_text(encoding="utf-8")
    assert "INSERT OR IGNORE" not in sql
    assert "'pending'" not in sql
    assert "ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE" in sql
    db = sqlite3.connect(":memory:")
    db.executescript((_REPO / "glim-think" / "schema.sql").read_text(encoding="utf-8"))
    db.executescript(sql)
    rows = db.execute("SELECT module, status FROM atlas_theorems").fetchall()
    assert rows == [("OpenDistillationFactory.Materials.RegimeGate.Dominance", expected_status)] * 5
