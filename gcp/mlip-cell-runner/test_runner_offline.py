"""Offline (air-gapped) execution contract for the cell runner.

These tests exercise run-cell and run-batch end-to-end with a mock calculator
backend against the in-tree release fixture: local / file:// inputs, a local
artifact directory, no --beat-emit-url, and zero network or GCP metadata
access. This is the contract the HPC lane (hpc/Apptainer.def + hpc/slurm/)
relies on.
"""

from __future__ import annotations

import json
from pathlib import Path

import mlip_cell_runner as runner
import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "canonical_structures_v2_mptrj.json"


class ConstantEnergyCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        n = len(atoms)
        self.results = {
            "energy": -1.0 * n,
            "forces": np.zeros((n, 3)),
            "stress": np.zeros(6),
        }


@pytest.fixture
def offline(monkeypatch):
    """Mock backend load and make any network attempt an immediate test failure."""

    def refuse_network(*_args, **_kwargs):
        raise AssertionError("offline run attempted a network call")

    monkeypatch.setattr(runner, "load_calculator", lambda mlip_id: ConstantEnergyCalculator())
    monkeypatch.setattr(runner.requests, "request", refuse_network)
    monkeypatch.setattr(runner.requests, "get", refuse_network)
    monkeypatch.setattr(runner.requests, "post", refuse_network)


@pytest.mark.integration
def test_run_cell_offline_with_file_url_manifest_and_no_beat_url(
    tmp_path: Path, monkeypatch, capsys, offline
) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-cell",
            "--run-id", "offline-run",
            "--cell-id", "offline-run:baseline:energy_volume:mock:s000",
            "--row-id", "energy_volume",
            "--mlip-id", "mock-mlip",
            "--manifest-url", FIXTURE_PATH.as_uri(),
            "--artifact-prefix", str(artifacts),
        ],
    )

    rc = runner.main()

    assert rc == 0
    metrics = json.loads(capsys.readouterr().out)
    assert metrics["schema"] == "lupine.mlip.cell_result.v1"
    assert metrics["status"] == "completed"
    assert metrics["n_structures"] >= 5
    artifact = json.loads((artifacts / "cell_result.json").read_text(encoding="utf-8"))
    assert artifact["schema"] == "lupine.mlip.cell_artifact.v1"
    assert artifact["manifest_url"] == FIXTURE_PATH.as_uri()
    # Default read-write checkpoint lands next to the artifact, fully local.
    checkpoint = json.loads((artifacts / "cell_checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["schema"] == "lupine.mlip.cell_checkpoint.v1"


def _write_batch_spec(tmp_path: Path, defaults_extra: dict | None = None) -> Path:
    spec_path = tmp_path / "batch.json"
    defaults = {
        "manifest_url": str(FIXTURE_PATH),
        "checkpoint_mode": "off",
    }
    defaults.update(defaults_extra or {})
    spec = {
        "schema": "lupine.mlip.batch_spec.v1",
        "batch_id": "offline-batch",
        "run_id": "offline-run",
        "campaign_id": "offline-run",
        "batch_artifact_prefix": str(tmp_path / "batch-artifacts"),
        "defaults": defaults,
        "cells": [
            {
                "cell_id": "offline-run:baseline:energy_volume:mock:s000",
                "row_id": "energy_volume",
                "mlip_id": "mock-mlip",
                "variant_id": "baseline",
                "artifact_prefix": str(tmp_path / "cells" / "energy_volume"),
            },
            {
                "cell_id": "offline-run:baseline:forces:mock:s000",
                "row_id": "forces",
                "mlip_id": "mock-mlip",
                "variant_id": "baseline",
                "artifact_prefix": str(tmp_path / "cells" / "forces"),
            },
        ],
    }
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return spec_path


@pytest.mark.integration
def test_run_batch_offline_writes_cell_results_and_local_beats(
    tmp_path: Path, monkeypatch, capsys, offline
) -> None:
    beats_path = tmp_path / "beats.jsonl"
    spec_path = _write_batch_spec(tmp_path, {"local_jsonl": str(beats_path)})
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-batch",
            "--batch-spec-url", str(spec_path),
        ],
    )

    rc = runner.main()

    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["schema"] == "lupine.mlip.batch_result.v1"
    assert summary["status"] == "completed"
    assert summary["cells_completed"] == 2
    assert summary["cells_failed"] == 0
    assert (tmp_path / "batch-artifacts" / "batch_result.json").exists()
    for row_id in ("energy_volume", "forces"):
        artifact = json.loads(
            (tmp_path / "cells" / row_id / "cell_result.json").read_text(encoding="utf-8")
        )
        assert artifact["schema"] == "lupine.mlip.cell_artifact.v1"
        assert artifact["row_id"] == row_id
    beats = [json.loads(line) for line in beats_path.read_text(encoding="utf-8").splitlines()]
    assert len(beats) == 2
    for beat in beats:
        assert beat["metrics"]["schema"] == "lupine.mlip.cell_result.v1"
        assert beat["metrics"]["status"] == "completed"


@pytest.mark.integration
def test_run_batch_offline_without_any_beat_sink_skips_beats_silently(
    tmp_path: Path, monkeypatch, capsys, offline
) -> None:
    spec_path = _write_batch_spec(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-batch",
            "--batch-spec-url", str(spec_path),
        ],
    )

    rc = runner.main()

    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "completed"
    assert summary["cells_completed"] == 2
    assert summary["failed"] == []


@pytest.mark.unit
def test_normalize_file_url_round_trips_paths(tmp_path: Path) -> None:
    plain = tmp_path / "manifest.json"
    assert runner.normalize_file_url(str(plain)) == str(plain)
    assert runner.normalize_file_url(plain.as_uri()) == str(plain)
    assert runner.normalize_file_url("gs://bucket/key") == "gs://bucket/key"
    assert runner.normalize_file_url("https://example.test/x") == "https://example.test/x"
