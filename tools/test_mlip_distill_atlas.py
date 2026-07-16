"""Theorem observation integrity tests for tools/mlip_distill_atlas.py.

The atlas_theorems seed feeds glim-think/src/atlas/theorems.ts, which projects
`status` into agents' FormalBasis. A local generated module may be recorded as
`imported`, but promotion to `verified` requires the separate immutable build
manifest consumed by tools/atlas_theorem_sync.py.

D1 schema (glim-think/migrations/0010_atlas_theorems.sql) accepts:
    status IN ('imported','verified','extended','failed')

All lean invocations are stubbed; no Lean toolchain is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import mlip_distill_atlas as atlas
import pytest

_D1_STATUS_VOCAB = {"imported", "verified", "extended", "failed"}
_REAL_REPO = Path(__file__).resolve().parents[1]


def _write_cell(root: Path, variant: str, row: str, mlip: str, error: float) -> None:
    d = root / variant / row / mlip
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "accuracy": {"error": error, "error_unit": "eV/atom", "score": 1.0},
        "speed": {"score": 10.0},
        "interventions": [],
        "refusals": [],
    }
    (d / "cell_result.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_material(
    root: Path, name: str, *, base_err: float = 0.010, dist_err: float = 0.005
) -> str:
    """One improving (baseline -> distill_accuracy) pairing => one theorem."""
    mat_root = root / name.lower()
    _write_cell(mat_root, "baseline", "energy_volume", "mace", base_err)
    _write_cell(mat_root, "distill_accuracy", "energy_volume", "mace", dist_err)
    return f"{name}={mat_root}"


@pytest.fixture()
def atlas_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every output path the script writes into tmp_path."""
    monkeypatch.setattr(atlas, "_REPO", tmp_path)
    monkeypatch.setattr(atlas, "LEAN_OUT", tmp_path / "lean_out")
    monkeypatch.setattr(atlas, "LEAN_SPEC", tmp_path / "lean_spec")
    monkeypatch.setattr(atlas, "SEED", tmp_path / "seed.sql")
    monkeypatch.setattr(atlas, "EXTENSION", tmp_path / "extension.json")
    monkeypatch.setattr(atlas, "REPORT", tmp_path / "report.md")
    return tmp_path


def _seed_rows(tmp_path: Path) -> list[dict[str, object]]:
    import sqlite3

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript((_REAL_REPO / "glim-think" / "schema.sql").read_text(encoding="utf-8"))
    db.executescript((tmp_path / "seed.sql").read_text(encoding="utf-8"))
    return [
        dict(row)
        for row in db.execute(
            "SELECT theorem_name, module, revision, proof_revision, atlas_revision, "
            "mathlib_revision, statement_hash, source_hash, build_manifest_hash, status "
            "FROM atlas_theorems ORDER BY theorem_name"
        )
    ]


@pytest.mark.unit
def test_all_modules_compile_as_imported_and_exit_zero(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atlas, "_verify_lean_module", lambda lean_file: True)
    args = [
        _make_material(atlas_env, "MatA"),
        _make_material(atlas_env, "MatB"),
    ]

    rc = atlas.main(args)

    assert rc == 0
    rows = _seed_rows(atlas_env)
    assert len(rows) == 2  # one theorem per material
    assert {row["status"] for row in rows} == {"imported"}
    assert all(row["proof_revision"] is None for row in rows)
    assert all(row["build_manifest_hash"] is None for row in rows)


@pytest.mark.unit
def test_failed_module_theorems_marked_failed_and_exit_nonzero(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # MatA compiles; MatB does not.
    monkeypatch.setattr(
        atlas, "_verify_lean_module", lambda lean_file: "MatA" in Path(lean_file).name
    )
    args = [
        _make_material(atlas_env, "MatA"),
        _make_material(atlas_env, "MatB"),
    ]

    rc = atlas.main(args)

    assert rc != 0
    rows = _seed_rows(atlas_env)
    assert len(rows) == 2
    (mat_a,) = [row for row in rows if "Lupine.DistillAtlas.MatA" in row["theorem_name"]]
    (mat_b,) = [row for row in rows if "Lupine.DistillAtlas.MatB" in row["theorem_name"]]
    assert mat_a["status"] == "imported"
    assert mat_b["status"] == "failed"


@pytest.mark.unit
def test_lean_missing_marks_nothing_verified_and_exits_nonzero(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Exercise the REAL _verify_lean_module error path: lean not on PATH.
    def raise_missing(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("lean not found")

    monkeypatch.setattr(atlas.subprocess, "run", raise_missing)
    args = [_make_material(atlas_env, "MatA")]

    rc = atlas.main(args)

    assert rc != 0
    rows = _seed_rows(atlas_env)
    assert rows, "seed must still be written so the failure is inspectable"
    assert {row["status"] for row in rows} == {"failed"}


@pytest.mark.unit
def test_seed_format_and_status_vocabulary(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mixed outcome: shared full-column upserts and statuses in D1 vocabulary.
    monkeypatch.setattr(
        atlas, "_verify_lean_module", lambda lean_file: "MatA" in Path(lean_file).name
    )
    args = [
        _make_material(atlas_env, "MatA"),
        _make_material(atlas_env, "MatB", base_err=0.004, dist_err=0.009),  # regress
    ]

    atlas.main(args)

    sql = (atlas_env / "seed.sql").read_text(encoding="utf-8")
    assert "INSERT OR IGNORE" not in sql
    assert "ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE" in sql
    assert "proof_repository, proof_revision" in sql
    assert "statement_hash, source_hash" in sql
    rows = _seed_rows(atlas_env)
    assert {row["status"] for row in rows} == {"imported", "failed"}
    assert all(row["status"] in _D1_STATUS_VOCAB for row in rows)
    assert all(row["revision"] == "uncommitted-generated-evidence" for row in rows)
    assert all(row["atlas_revision"] == atlas.ATLAS_REV for row in rows)
    assert all(row["statement_hash"] and row["source_hash"] for row in rows)


@pytest.mark.unit
def test_verify_lean_module_false_on_missing_binary(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_missing(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("lean not found")

    monkeypatch.setattr(atlas.subprocess, "run", raise_missing)
    lean_file = atlas_env / "X.lean"
    lean_file.write_text("theorem t : 1 = 1 := rfl\n", encoding="utf-8")

    assert atlas._verify_lean_module(lean_file) is False
