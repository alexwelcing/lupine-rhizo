from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlip_cell_runner as runner

ROOT = Path(__file__).resolve().parents[2]
ROWS = ROOT / "data" / "candidates" / "z2" / "measurements.jsonl"
MANIFEST = ROOT / "data" / "candidates" / "z2" / "artifact-manifest.json"


def test_z2_abstention_smoke_writes_four_rows_and_beat_without_model_load(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    def fail_model_load(*_args, **_kwargs):
        raise AssertionError("abstention smoke must not load a calculator")

    monkeypatch.setattr(runner, "load_calculator", fail_model_load)
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-z2-abstention-smoke",
            "--run-id",
            "z2-smoke-test",
            "--artifact-prefix",
            str(tmp_path / "artifacts"),
            "--local-jsonl",
            str(tmp_path / "beats.jsonl"),
            "--z2-rows-url",
            str(ROWS),
            "--z2-artifact-manifest-url",
            str(MANIFEST),
        ],
    )

    assert runner.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["schema"] == "lupine.z2.abstention_smoke.v1"
    assert summary["status"] == "completed"
    assert summary["row_count"] == 4
    assert summary["outcome"] == "abstained"
    assert summary["scientific_executions"] == 0
    assert summary["artifact_hash"] == "sha256:" + hashlib.sha256(ROWS.read_bytes()).hexdigest()
    assert (tmp_path / "artifacts" / "measurements.jsonl").read_bytes() == ROWS.read_bytes()
    assert (tmp_path / "artifacts" / "artifact-manifest.json").read_bytes() == MANIFEST.read_bytes()

    beat = json.loads((tmp_path / "beats.jsonl").read_text(encoding="utf-8"))
    assert beat["beat_id"] == summary["beat_id"]
    assert beat["metrics"]["artifact_hash"] == summary["artifact_hash"]
    assert beat["metrics"]["scientific_executions"] == 0


def test_z2_abstention_smoke_fails_closed_on_tampered_rows(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    rows = tmp_path / "measurements.jsonl"
    rows.write_bytes(ROWS.read_bytes() + b"\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-z2-abstention-smoke",
            "--run-id",
            "z2-smoke-tampered",
            "--artifact-prefix",
            str(tmp_path / "artifacts"),
            "--z2-rows-url",
            str(rows),
            "--z2-artifact-manifest-url",
            str(MANIFEST),
        ],
    )

    assert runner.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert failure["status"] == "failed"
    assert "hash does not match" in failure["error"]
    assert not (tmp_path / "artifacts").exists()
