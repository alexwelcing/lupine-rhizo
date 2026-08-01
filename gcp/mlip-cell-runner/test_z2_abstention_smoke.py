from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mlip_cell_runner as runner
import rfc8785

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
            "--local-jsonl",
            str(tmp_path / "beats.jsonl"),
            "--z2-rows-url",
            str(rows),
            "--z2-artifact-manifest-url",
            str(MANIFEST),
        ],
    )

    assert runner.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert failure["status"] == "failed"
    assert "frozen packaged" in failure["error"]
    failure_beat = json.loads((tmp_path / "beats.jsonl").read_text(encoding="utf-8"))
    assert failure_beat["metrics"]["status"] == "failed"
    assert failure_beat["metrics"]["scientific_executions"] == 0
    assert "frozen packaged" in failure_beat["metrics"]["error"]
    assert not (tmp_path / "artifacts").exists()


def test_z2_abstention_smoke_rejects_self_consistent_override(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    rows = [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines()]
    previous_hash = None
    for row in rows:
        row["metric"] = "tampered_metric"
        row["previous_row_hash"] = previous_hash
        row_body = {key: value for key, value in row.items() if key != "row_hash"}
        row["row_hash"] = "sha256:" + hashlib.sha256(rfc8785.dumps(row_body)).hexdigest()
        previous_hash = row["row_hash"]
    rows_bytes = b"\n".join(rfc8785.dumps(row) for row in rows) + b"\n"
    rows_path = tmp_path / "measurements.jsonl"
    rows_path.write_bytes(rows_bytes)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["sha256"] = "sha256:" + hashlib.sha256(rows_bytes).hexdigest()
    manifest["chain_head"] = rows[0]["row_hash"]
    manifest["chain_tail"] = rows[-1]["row_hash"]
    manifest_path = tmp_path / "artifact-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-z2-abstention-smoke",
            "--run-id",
            "z2-smoke-self-consistent-tamper",
            "--artifact-prefix",
            str(tmp_path / "artifacts"),
            "--local-jsonl",
            str(tmp_path / "beats.jsonl"),
            "--z2-rows-url",
            str(rows_path),
            "--z2-artifact-manifest-url",
            str(manifest_path),
        ],
    )

    assert runner.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert "frozen packaged" in failure["error"]
    assert not (tmp_path / "artifacts").exists()


def test_z2_abstention_smoke_requires_beat_sink(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-z2-abstention-smoke",
            "--run-id",
            "z2-smoke-no-beat-sink",
            "--artifact-prefix",
            str(tmp_path / "artifacts"),
        ],
    )

    assert runner.main() == 1
    failure = json.loads(capsys.readouterr().err)
    assert "beat sink" in failure["error"]
    assert not (tmp_path / "artifacts").exists()
