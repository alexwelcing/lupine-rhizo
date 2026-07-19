from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

MODULE_PATH = Path(__file__).with_name("run_measurement.py")
SPEC = importlib.util.spec_from_file_location("z3_run_measurement", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def campaign(tmp_path: Path) -> Path:
    path = tmp_path / "campaign.json"
    path.write_text(
        json.dumps(
            {
                "campaign_id": "discovery.round-4.z3-adsorption.v1",
                "content_hash": "sha256:campaign",
                "available_models": [
                    {
                        "model_id": "chgnet",
                        "version": "chgnet 0.4.2",
                        "artifact_hash": "sha256:model",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_dry_run_binds_job_model_and_content_addresses(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    result = runner.run(
        [
            "--model-id",
            "chgnet",
            "--fixture-url",
            "gs://inputs/z3/candidate.json",
            "--candidate-id",
            "CO-Pt111",
            "--run-id",
            "z3-smoke",
            "--campaign-manifest",
            str(campaign(tmp_path)),
            "--dry-run",
        ]
    )
    assert result == 0
    request = json.loads(capsys.readouterr().out)
    assert request["model"]["artifact_hash"] == "sha256:model"
    assert request["endpoint"]["job"] == "mlip-cell-chgnet"
    assert request["artifact_prefix"].endswith("/z3-smoke/chgnet/CO-Pt111/adsorption_energy")
    command = request["command"]
    assert "--project=shed-489901" in command
    assert "--region=us-central1" in command
    assert "--row-id,adsorption_energy" in command[-1]
    assert "--local-jsonl,/tmp/z3-measurement-beats.jsonl" in command[-1]


def test_rejects_unsafe_storage_identifier(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="candidate_id"):
        runner.run(
            [
                "--model-id",
                "chgnet",
                "--fixture-url",
                "gs://inputs/z3/candidate.json",
                "--candidate-id",
                "../escape",
                "--run-id",
                "z3",
                "--campaign-manifest",
                str(campaign(tmp_path)),
                "--dry-run",
            ]
        )


def test_collect_verifies_raw_artifact(tmp_path: Path) -> None:
    args = SimpleNamespace(
        capture_dir=tmp_path,
        candidate_id="CO-Pt111",
        model_id="chgnet",
        row_id="adsorption_energy",
    )

    def fake_run(command: list[str], check: bool) -> None:
        assert check is True
        destination = Path(command[-1])
        destination.write_text(
            json.dumps(
                {
                    "schema": "lupine.mlip.cell_artifact.v1",
                    "mlip_id": "chgnet",
                    "row_id": "adsorption_energy",
                    "predictions": [
                        {
                            "candidate_id": "CO-Pt111",
                            "status": "completed",
                            "adsorption_energy_ev": -1.2,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    with mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        captured = runner.collect_artifact(args, "gs://outputs/z3")
    assert captured == tmp_path / "CO-Pt111.chgnet.cell_result.json"


def test_collect_rejects_wrong_observable(tmp_path: Path) -> None:
    args = SimpleNamespace(
        capture_dir=tmp_path,
        candidate_id="CO-Pt111",
        model_id="chgnet",
        row_id="adsorption_energy",
    )

    def fake_run(command: list[str], check: bool) -> None:
        Path(command[-1]).write_text(
            json.dumps(
                {
                    "schema": "lupine.mlip.cell_artifact.v1",
                    "mlip_id": "chgnet",
                    "row_id": "forces",
                    "predictions": [{}],
                }
            ),
            encoding="utf-8",
        )

    with mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        with pytest.raises(ValueError, match="does not match request"):
            runner.collect_artifact(args, "gs://outputs/z3")


def test_collect_rejects_failed_adsorption_prediction(tmp_path: Path) -> None:
    args = SimpleNamespace(
        capture_dir=tmp_path,
        candidate_id="CO-Pt111",
        model_id="chgnet",
        row_id="adsorption_energy",
    )

    def fake_run(command: list[str], check: bool) -> None:
        Path(command[-1]).write_text(
            json.dumps(
                {
                    "schema": "lupine.mlip.cell_artifact.v1",
                    "mlip_id": "chgnet",
                    "row_id": "adsorption_energy",
                    "predictions": [
                        {
                            "candidate_id": "CO-Pt111",
                            "status": "failed",
                            "adsorption_energy_ev": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    with mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
        with pytest.raises(ValueError, match="not completed"):
            runner.collect_artifact(args, "gs://outputs/z3")
