from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import rfc8785

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "tools" / "build_z3_measurement_rows.py"
INGESTER = ROOT / "tools" / "ingest_campaign_results.py"
EXPECTED_MODELS = [
    "chgnet",
    "mace-mp-medium",
    "mace-mp-small",
    "mace-mpa-0-medium",
]


def content_hash(document: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(document)).hexdigest()


def test_builder_emits_four_content_addressed_aggregate_fail_rows(tmp_path: Path) -> None:
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
    assert len(rows) == 4
    assert [row["model_id"] for row in rows] == EXPECTED_MODELS
    assert rows_path.read_bytes() == b"".join(rfc8785.dumps(row) + b"\n" for row in rows)

    previous_hash = None
    for row in rows:
        assert row["campaign_manifest"] == "campaigns/v1/z3.campaign-manifest.v1.json"
        assert row["campaign_manifest_hash"] == (
            "sha256:49f5f20e41450697b63b9ff079fe25b5490ba684956c5d68bb37a5d2cd02c494"
        )
        assert row["previous_row_hash"] == previous_hash
        assert row["row_hash"] == content_hash(
            {key: value for key, value in row.items() if key != "row_hash"}
        )
        assert row["epistemic_status"] == "negative"
        assert row["claim_predicate"] == "adsorption_energy_mae<=0.1"
        aggregate = row["aggregate_result"]
        assert aggregate["metric"] == "adsorption_energy_mae"
        assert aggregate["unit"] == "eV"
        assert aggregate["sample_count"] == 20
        assert aggregate["baseline_holdout_mae_ev"] > 0
        assert aggregate["corrected_holdout_mae_ev"] > 0.1
        assert aggregate["selected_correction_form"] in {
            "A_global_constant",
            "B_family_constant",
            "C_family_linear",
        }
        assert aggregate["acceptance_test"] == {
            "comparator": "less_than_or_equal",
            "outcome": "fail",
            "threshold": 0.1,
            "unit": "eV",
        }
        artifact_path = ROOT / row["artifact"]
        assert artifact_path.name == "delta-correction-report.json"
        assert row["artifact_hash"] == "sha256:" + hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        candidate_refs = row["candidate_artifacts"]
        assert len(candidate_refs) == 32
        for candidate_ref in candidate_refs:
            candidate_path = ROOT / candidate_ref["path"]
            assert candidate_ref["sha256"] == (
                "sha256:" + hashlib.sha256(candidate_path.read_bytes()).hexdigest()
            )
        previous_hash = row["row_hash"]

    artifact_manifest = json.loads((tmp_path / "artifact-manifest.json").read_text())
    assert artifact_manifest["row_count"] == 4
    assert artifact_manifest["artifact_count"] == 32
    assert artifact_manifest["row_chain_head"] == rows[0]["row_hash"]
    assert artifact_manifest["row_chain_tail"] == rows[-1]["row_hash"]
    assert artifact_manifest["content_hash"] == content_hash(
        {key: value for key, value in artifact_manifest.items() if key != "content_hash"}
    )

    corrected_candidates = 0
    for artifact_path in sorted((tmp_path / "artifacts").glob("*.json")):
        artifact = json.loads(artifact_path.read_text())
        candidate = artifact["candidate"]
        assert candidate["candidate_id"] == artifact_path.stem
        assert artifact["campaign_manifest"]["content_hash"] == rows[0]["campaign_manifest_hash"]
        if candidate["split"] == "confirmatory_test":
            corrected_candidates += 1
            for measurement in candidate["model_measurements"]:
                assert measurement["delta_status"] == "corrected_confirmatory_test"
                assert isinstance(measurement["delta_correction_ev"], float)
                assert isinstance(measurement["corrected_signed_error_ev"], float)
                assert isinstance(measurement["corrected_absolute_error_ev"], float)
                assert isinstance(measurement["delta_hybrid_corrected_adsorption_energy_ev"], float)
        else:
            assert all(
                measurement["delta_status"] == "not_scored_fit_or_selection_split"
                for measurement in candidate["model_measurements"]
            )
    assert corrected_candidates == 20


def test_generated_rows_pass_ingester_in_temporary_validation_root(tmp_path: Path) -> None:
    generated = tmp_path / "generated"
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--root",
            str(ROOT),
            "--output-dir",
            str(generated),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    validation_root = tmp_path / "validation-root"
    for directory in ("campaigns", "evidence", "registry"):
        shutil.copytree(ROOT / directory, validation_root / directory)
    shutil.copytree(generated / "artifacts", validation_root / "data/candidates/z3/artifacts")
    measurements_path = validation_root / "data/candidates/z3/measurements.jsonl"
    measurements_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(generated / "measurements.jsonl", measurements_path)
    shutil.copyfile(
        ROOT / "data/candidates/z3/delta-correction-report.json",
        validation_root / "data/candidates/z3/delta-correction-report.json",
    )

    manifest_path = validation_root / "campaigns/v1/z3.campaign-manifest.v1.json"

    ingestion = subprocess.run(
        [
            sys.executable,
            str(INGESTER),
            "--root",
            str(validation_root),
            "--manifest",
            str(manifest_path),
            "--measurements",
            str(measurements_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert ingestion.returncode == 0, ingestion.stderr
    payload = json.loads(ingestion.stdout)
    assert len(payload["ingested_bundle_ids"]) == 4


def test_builder_rejects_internally_inconsistent_correction_report(tmp_path: Path) -> None:
    for relative_path in (
        "campaigns/v1/z3.campaign-manifest.v1.json",
        "data/candidates/z3/source/z3-candidate-measurements.json",
        "data/candidates/z3/delta-correction-report.json",
    ):
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative_path, destination)

    report_path = tmp_path / "data/candidates/z3/delta-correction-report.json"
    report = json.loads(report_path.read_text())
    report["models"]["chgnet"]["test_rows"][0]["corrected_signed_error_ev"] += 1.0
    report_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    report_path.with_suffix(".json.sha256").write_text(
        f"{digest}  delta-correction-report.json\n"
    )

    result = subprocess.run(
        [sys.executable, str(BUILDER), "--root", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "corrected signed error is inconsistent" in result.stderr