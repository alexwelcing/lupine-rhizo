from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "build_z2_abstention_rows.py"
ROWS = ROOT / "data/candidates/z2/measurements.jsonl"
ARTIFACT_MANIFEST = ROOT / "data/candidates/z2/artifact-manifest.json"

spec = importlib.util.spec_from_file_location("build_z2_abstention_rows", TOOL)
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules.setdefault("build_z2_abstention_rows", tool)
spec.loader.exec_module(tool)


@pytest.fixture(scope="module", autouse=True)
def build_rows() -> None:
    subprocess.run([sys.executable, str(TOOL)], check=True, cwd=ROOT)


def load_rows() -> list[dict]:
    return [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_four_rows_one_per_declared_model_in_order() -> None:
    rows = load_rows()
    assert [r["model_id"] for r in rows] == [
        "chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium",
    ]


def test_every_row_abstains_unsupported_with_zero_measurements() -> None:
    for row in load_rows():
        assert row["epistemic_status"] == "unsupported"
        assert row["acceptance_test"]["outcome"] == "abstained"
        assert row["sample_count"] == 0
        assert row["value"] is None
        assert row["cloud_executions"] == 0
        assert "spin" in row["acceptance_test"]["reason"].lower()


def test_hash_chain_and_rfc8785_roundtrip() -> None:
    rows = load_rows()
    previous = None
    for row in rows:
        assert row["previous_row_hash"] == previous
        body = {k: v for k, v in row.items() if k != "row_hash"}
        assert row["row_hash"] == tool.content_hash(body)
        previous = row["row_hash"]


def test_manifest_hash_matches_locked_manifest() -> None:
    manifest = json.loads((ROOT / "campaigns/v1/z2.campaign-manifest.v1.json").read_text())
    for row in load_rows():
        assert row["campaign_manifest_hash"] == manifest["content_hash"]


def test_artifact_manifest_records_chain_and_file_hash() -> None:
    manifest = json.loads(ARTIFACT_MANIFEST.read_text())
    rows = load_rows()
    assert manifest["row_count"] == 4
    assert manifest["chain_head"] == rows[0]["row_hash"]
    assert manifest["chain_tail"] == rows[-1]["row_hash"]
    digest = "sha256:" + hashlib.sha256(ROWS.read_bytes()).hexdigest()
    assert manifest["artifacts"][0]["sha256"] == digest


def test_rebuild_is_deterministic() -> None:
    before = ROWS.read_bytes()
    subprocess.run([sys.executable, str(TOOL)], check=True, cwd=ROOT)
    assert ROWS.read_bytes() == before
