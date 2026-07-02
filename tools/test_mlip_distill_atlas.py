"""Seed-SQL integrity tests for tools/mlip_distill_atlas.py.

The atlas_theorems seed feeds glim-think/src/atlas/theorems.ts, which projects
`status` into agents' FormalBasis. A theorem row may say 'verified' ONLY if its
generated Lean module actually compiled — anything else lets never-checked
claims enter the live system as machine-checked.

D1 schema (glim-think/migrations/0010_atlas_theorems.sql) accepts:
    status IN ('imported','verified','extended','failed')

All lean invocations are stubbed; no Lean toolchain is required.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import mlip_distill_atlas as atlas

_D1_STATUS_VOCAB = {"imported", "verified", "extended", "failed"}


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


def _make_material(root: Path, name: str, *, base_err: float = 0.010, dist_err: float = 0.005) -> str:
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
    monkeypatch.setattr(atlas, "REPORT", tmp_path / "report.md")
    return tmp_path


def _seed_lines(tmp_path: Path) -> list[str]:
    text = (tmp_path / "seed.sql").read_text(encoding="utf-8")
    return [ln for ln in text.splitlines() if ln.strip()]


@pytest.mark.unit
def test_all_modules_verified_marks_verified_and_exits_zero(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(atlas, "_verify_lean_module", lambda lean_file: True)
    args = [
        _make_material(atlas_env, "MatA"),
        _make_material(atlas_env, "MatB"),
    ]

    rc = atlas.main(args)

    assert rc == 0
    lines = _seed_lines(atlas_env)
    assert len(lines) == 2  # one theorem per material
    for ln in lines:
        assert "'verified'" in ln
        assert "'failed'" not in ln


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
    lines = _seed_lines(atlas_env)
    assert len(lines) == 2
    (mat_a_line,) = [ln for ln in lines if "Lupine.DistillAtlas.MatA" in ln]
    (mat_b_line,) = [ln for ln in lines if "Lupine.DistillAtlas.MatB" in ln]
    assert "'verified'" in mat_a_line
    assert "'failed'" in mat_b_line
    assert "'verified'" not in mat_b_line


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
    lines = _seed_lines(atlas_env)
    assert lines, "seed must still be written so the failure is inspectable"
    for ln in lines:
        assert "'verified'" not in ln
        assert "'failed'" in ln


@pytest.mark.unit
def test_seed_format_and_status_vocabulary(
    atlas_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mixed outcome: keep the upsert format identical, statuses in D1 vocab.
    monkeypatch.setattr(
        atlas, "_verify_lean_module", lambda lean_file: "MatA" in Path(lean_file).name
    )
    args = [
        _make_material(atlas_env, "MatA"),
        _make_material(atlas_env, "MatB", base_err=0.004, dist_err=0.009),  # regress
    ]

    atlas.main(args)

    for ln in _seed_lines(atlas_env):
        assert ln.startswith(
            "INSERT OR IGNORE INTO atlas_theorems "
            "(facet, theorem_name, module, revision, status, used_in_hypotheses) "
            "VALUES ('experiment', "
        )
        assert ln.endswith(", 1);")
        assert f"'{atlas.ATLAS_REV}'" in ln
        status = ln.rsplit("', '", 1)[-1].split("'", 1)[0]
        assert status in _D1_STATUS_VOCAB


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
