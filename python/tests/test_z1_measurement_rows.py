from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import rfc8785

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools" / "build_z1_measurement_rows.py"
INGESTER = ROOT / "tools" / "ingest_campaign_results.py"
EXPECTED_MODELS = [
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
]
EXPECTED_AGGREGATES = {
    "chgnet": (28, 2, 242.54427074310212),
    "mace-mp-small": (26, 4, 151.99119622895716),
    "mace-mp-medium": (29, 1, 174.7392625242481),
    "mace-mpa-0-medium": (28, 2, 135.00396270645913),
}


def content_hash(document: object) -> str:
    canonical = rfc8785.dumps(document)
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def test_builder_emits_hash_chained_negative_rows_and_source_manifest(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    rows_path = tmp_path / "measurements.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    assert [row["model_id"] for row in rows] == EXPECTED_MODELS
    assert rows_path.read_bytes() == b"".join(rfc8785.dumps(row) + b"\n" for row in rows)

    previous_hash = None
    for row in rows:
        model_id = row["model_id"]
        completed, failed, mae = EXPECTED_AGGREGATES[model_id]
        assert row["campaign_manifest_hash"] == (
            "sha256:0a85044ca84d10e021a0a282987976a3a9e79a611a618470e1638e9105171e40"
        )
        assert row["previous_row_hash"] == previous_hash
        assert row["row_hash"] == content_hash(
            {key: value for key, value in row.items() if key != "row_hash"}
        )
        assert row["claim_predicate"] == "barrier_mae_mev<=40"
        assert row["epistemic_status"] == "negative"
        assert row["metric"] == "barrier_mae"
        assert row["value"] == mae
        assert row["unit"] == "meV"
        assert row["sample_count"] == completed
        assert row["acceptance_test"] == {
            "comparator": "less_than_or_equal",
            "outcome": "fail",
            "threshold": 40.0,
        }
        conditions = row["scope"]["conditions"]
        assert conditions["path_count"] == 30
        assert conditions["completed_path_count"] == completed
        assert conditions["failed_path_count"] == failed
        assert len(conditions["failed_path_ids"]) == failed
        assert conditions["failure_policy"] == "record failure without imputation"
        assert conditions["outcome"] == "fail"
        previous_hash = row["row_hash"]

    artifact_manifest = json.loads((tmp_path / "artifact-manifest.json").read_text())
    assert artifact_manifest["row_count"] == 4
    assert artifact_manifest["row_chain_head"] == rows[0]["row_hash"]
    assert artifact_manifest["row_chain_tail"] == rows[-1]["row_hash"]
    assert artifact_manifest["measurements_sha256"] == (
        "sha256:" + hashlib.sha256(rows_path.read_bytes()).hexdigest()
    )
    assert artifact_manifest["files"] == [
        {
            "bytes": rows_path.stat().st_size,
            "path": "data/candidates/z1/measurements.jsonl",
            "sha256": artifact_manifest["measurements_sha256"],
        }
    ]
    assert len(artifact_manifest["source_artifacts"]) == 9
    assert artifact_manifest["content_hash"] == content_hash(
        {
            key: value
            for key, value in artifact_manifest.items()
            if key != "content_hash"
        }
    )


def test_builder_check_detects_tampered_generated_rows(tmp_path: Path) -> None:
    generate = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert generate.returncode == 0, generate.stderr
    (tmp_path / "measurements.jsonl").write_text("{}\n", encoding="utf-8")

    check = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path),
            "--check",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 1
    assert "measurements.jsonl is stale" in check.stderr


def test_builder_rejects_non_finite_values() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_z1_measurement_rows", BUILDER)
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    with pytest.raises(ValueError):
        builder.canonical_bytes({"value": float("nan")})


def test_ingester_accepts_rfc8785_row_hashes_before_contract_validation() -> None:
    assert rfc8785.__file__ is not None
    result = subprocess.run(
        [
            sys.executable,
            str(INGESTER),
            "--root",
            str(ROOT),
            "--manifest",
            "campaigns/v1/z1.campaign-manifest.v1.json",
            "--measurements",
            "data/candidates/z1/measurements.jsonl",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "row_hash mismatch" not in result.stderr
    # The seeded baseline EvidenceBundle (evidence/v1/examples/
    # z1-nebdft2k-panel-baseline.json) lets the target premise pass the
    # baseline, predicate, and scope gates; ingestion still stops at the
    # documented gap (docs/runbooks/campaign-measurement-row-schema.md): the
    # ingester does not propagate a row's measurements member, and the
    # barrier_mae_mev<=40 predicate requires typed bundle measurements.
    assert "has no baseline evidence" not in result.stderr
    assert "'measurements' is a required property" in result.stderr
