#!/usr/bin/env python3
"""Build deterministic, content-addressed Z1 campaign measurement rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import rfc8785

MANIFEST_PATH = Path("campaigns/v1/z1.campaign-manifest.v1.json")
SOURCE_ROOT = Path("data/candidates/z1")
MEASUREMENTS_NAME = "measurements.jsonl"
ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"
CLAIM_ID = "discovery.z1.barrier-accuracy.v1"
PREMISE_ID = "chemistry-held-out-neb"
CLAIM_PREDICATE = "barrier_mae_mev<=40"
THRESHOLDS_VERSION = "hard-materials-z1.v1"
PRODUCER = "gcp/mlip-cell-runner/z1_barrier.py"
ACCOUNTABLE_HUMAN = "Alex Welcing (director)"
RESULT_URI_ROOT = "gs://shed-489901-atlas-outputs/z1/campaign"


def canonical_bytes(document: Any) -> bytes:
    """Serialize a JSON value with the RFC 8785 JSON Canonicalization Scheme."""
    try:
        return rfc8785.dumps(document)
    except (rfc8785.CanonicalizationError, TypeError) as error:
        raise ValueError(f"value is not RFC 8785 canonicalizable: {error}") from error


def content_hash(document: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def bytes_hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON object {path}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError(f"expected JSON object in {path}")
    return document


def validate_manifest(root: Path) -> dict[str, Any]:
    manifest = load_object(root / MANIFEST_PATH)
    expected_hash = content_hash(
        {key: value for key, value in manifest.items() if key != "content_hash"}
    )
    if manifest.get("content_hash") != expected_hash:
        raise ValueError("governing campaign manifest has a non-canonical content_hash")

    executed_path = root / SOURCE_ROOT / "source" / "executed-campaign-manifest.json"
    executed = load_object(executed_path)
    if executed != manifest:
        raise ValueError("executed campaign manifest differs from the governing manifest")
    return manifest


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def validate_model_result(
    manifest: dict[str, Any], model: dict[str, Any], result: dict[str, Any], checkpoint: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model_id = model["model_id"]
    manifest_hash = manifest["content_hash"]
    if result.get("mlip_id") != model_id:
        raise ValueError(f"result model mismatch for {model_id}")
    if result.get("campaign_id") != manifest["campaign_id"]:
        raise ValueError(f"result campaign mismatch for {model_id}")
    if result.get("manifest_hash") != manifest_hash:
        raise ValueError(f"result manifest mismatch for {model_id}")
    if result.get("fixture_contract", {}).get("campaign_manifest_hash") != manifest_hash:
        raise ValueError(f"fixture manifest mismatch for {model_id}")
    candidate_panel = manifest["execution"]["candidate_panel"]
    fixture_contract = result["fixture_contract"]
    if fixture_contract.get("candidate_panel_sha256") != candidate_panel["sha256"]:
        raise ValueError(f"candidate panel mismatch for {model_id}")

    predictions = result.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != 30:
        raise ValueError(f"{model_id} must retain all 30 path outcomes")
    path_ids = [prediction.get("path_id") for prediction in predictions]
    if any(not isinstance(path_id, str) or not path_id for path_id in path_ids):
        raise ValueError(f"{model_id} has a path without an identity")
    if len(set(path_ids)) != len(path_ids):
        raise ValueError(f"{model_id} has duplicate path outcomes")

    completed = [prediction for prediction in predictions if prediction.get("status") == "completed"]
    failed = [prediction for prediction in predictions if prediction.get("status") == "failed"]
    if len(completed) + len(failed) != len(predictions):
        raise ValueError(f"{model_id} has an unknown path status")
    accuracy = result.get("accuracy", {})
    if accuracy.get("completed_path_count") != len(completed):
        raise ValueError(f"completed path count mismatch for {model_id}")
    if accuracy.get("failed_path_count") != len(failed):
        raise ValueError(f"failed path count mismatch for {model_id}")
    computed_mae = sum(prediction["absolute_error_mev"] for prediction in completed) / len(completed)
    if not _close(computed_mae, accuracy.get("barrier_mae_mev")):
        raise ValueError(f"barrier MAE mismatch for {model_id}")
    for prediction in completed:
        signed_error = 1000 * (
            prediction["predicted_barrier_ev"] - prediction["reference_barrier_ev"]
        )
        if not _close(signed_error, prediction["signed_error_mev"]):
            raise ValueError(f"signed error mismatch for {model_id}/{prediction['path_id']}")
        if not _close(abs(signed_error), prediction["absolute_error_mev"]):
            raise ValueError(f"absolute error mismatch for {model_id}/{prediction['path_id']}")
    for prediction in failed:
        forbidden = {"predicted_barrier_ev", "signed_error_mev", "absolute_error_mev"}
        if forbidden & prediction.keys():
            raise ValueError(f"failed path was imputed for {model_id}/{prediction['path_id']}")

    context = checkpoint.get("context", {})
    if context.get("manifest_hash") != manifest_hash or context.get("mlip_id") != model_id:
        raise ValueError(f"checkpoint identity mismatch for {model_id}")
    checkpoint_predictions = checkpoint.get("predictions")
    if not isinstance(checkpoint_predictions, dict) or len(checkpoint_predictions) != len(completed):
        raise ValueError(f"checkpoint prediction count mismatch for {model_id}")
    checkpoint_by_path = {
        item["prediction"]["path_id"]: item["prediction"]
        for item in checkpoint_predictions.values()
    }
    if checkpoint_by_path != {item["path_id"]: item for item in completed}:
        raise ValueError(f"checkpoint predictions differ from result for {model_id}")
    return completed, failed


def build_row(
    root: Path,
    manifest: dict[str, Any],
    model: dict[str, Any],
    previous_row_hash: str | None,
) -> dict[str, Any]:
    model_id = model["model_id"]
    result_path = SOURCE_ROOT / "raw" / model_id / "cell_result.json"
    checkpoint_path = SOURCE_ROOT / "raw" / model_id / "cell_checkpoint.json"
    result = load_object(root / result_path)
    checkpoint = load_object(root / checkpoint_path)
    completed, failed = validate_model_result(manifest, model, result, checkpoint)

    accuracy = result["accuracy"]
    threshold = float(manifest["acceptance_test"]["threshold"])
    mae = accuracy["barrier_mae_mev"]
    underestimate_count = sum(item["signed_error_mev"] < 0 for item in completed)
    path_ids = [item["path_id"] for item in result["predictions"]]
    chemistries = sorted({item["chemical_system"] for item in result["predictions"]})
    structures = sorted({item["material_id"] for item in result["predictions"]})
    timestamp = datetime.fromtimestamp(checkpoint["updated_at_unix"], tz=UTC).isoformat().replace(
        "+00:00", "Z"
    )
    checkpoint_hash = bytes_hash((root / checkpoint_path).read_bytes())
    row = {
        "row_id": f"z1-{model_id}",
        "campaign_manifest_hash": manifest["content_hash"],
        "previous_row_hash": previous_row_hash,
        "claim_id": CLAIM_ID,
        "premise_id": PREMISE_ID,
        "claim_predicate": CLAIM_PREDICATE,
        "epistemic_status": "negative",
        "scope": {
            "structures": structures,
            "chemistries": chemistries,
            "properties": ["migration_barrier"],
            "conditions": {
                "acceptance_threshold_mev": threshold,
                "barrier_energy_unit": "eV",
                "barrier_mae_mev": mae,
                "candidate_panel_sha256": manifest["execution"]["candidate_panel"]["sha256"],
                "completed_path_count": len(completed),
                "failed_path_count": len(failed),
                "failed_path_ids": [item["path_id"] for item in failed],
                "failure_policy": "record failure without imputation",
                "measurement_complete": accuracy["measurement_complete"],
                "model_artifact_hash": model["artifact_hash"],
                "model_id": model_id,
                "model_version": model["version"],
                "outcome": "fail",
                "path_count": len(path_ids),
                "reference_kind": "published DFT-NEB",
                "signed_error_unit": "meV",
                "signed_underestimate_count": underestimate_count,
                "signed_underestimate_fraction": underestimate_count / len(completed),
            },
        },
        "metric": "barrier_mae",
        "value": mae,
        "unit": "meV",
        "acceptance_test": {
            "comparator": "less_than_or_equal",
            "threshold": threshold,
            "outcome": "fail",
        },
        "sample_count": len(completed),
        "model_id": model_id,
        "model_version": model["version"],
        "run_id": result["run_id"],
        "artifact": result_path.as_posix(),
        "artifact_uri": f"{RESULT_URI_ROOT}/{model_id}/cell_result.json",
        "artifact_hash": bytes_hash((root / result_path).read_bytes()),
        "checkpoint_artifact": checkpoint_path.as_posix(),
        "checkpoint_artifact_hash": checkpoint_hash,
        "thresholds_version": THRESHOLDS_VERSION,
        "provenance": {
            "agent": PRODUCER,
            "human": ACCOUNTABLE_HUMAN,
            "timestamp": timestamp,
        },
    }
    row["row_hash"] = content_hash(row)
    return row


def source_artifacts(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    paths = [SOURCE_ROOT / "source" / "executed-campaign-manifest.json"]
    for model in manifest["available_models"]:
        model_id = model["model_id"]
        paths.extend(
            [
                SOURCE_ROOT / "raw" / model_id / "cell_checkpoint.json",
                SOURCE_ROOT / "raw" / model_id / "cell_result.json",
            ]
        )
    entries = []
    for path in sorted(paths):
        payload = (root / path).read_bytes()
        if path.name == "executed-campaign-manifest.json":
            source_uri = "gs://shed-489901-atlas-inputs/z1/campaigns/v1/z1.campaign-manifest.v1.json"
        else:
            model_id = path.parts[-2]
            source_uri = f"{RESULT_URI_ROOT}/{model_id}/{path.name}"
        entries.append(
            {
                "bytes": len(payload),
                "path": path.as_posix(),
                "sha256": bytes_hash(payload),
                "source_uri": source_uri,
            }
        )
    return entries


def build_outputs(root: Path) -> tuple[bytes, bytes]:
    manifest = validate_manifest(root)
    rows = []
    previous_row_hash = None
    for model in manifest["available_models"]:
        row = build_row(root, manifest, model, previous_row_hash)
        rows.append(row)
        previous_row_hash = row["row_hash"]
    measurements = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    artifact_manifest = {
        "schema": "lupine.z1.measurement-artifact-manifest.v1",
        "campaign_manifest_hash": manifest["content_hash"],
        "measurements_path": f"{SOURCE_ROOT.as_posix()}/{MEASUREMENTS_NAME}",
        "measurements_bytes": len(measurements),
        "measurements_sha256": bytes_hash(measurements),
        "files": [
            {
                "bytes": len(measurements),
                "path": f"{SOURCE_ROOT.as_posix()}/{MEASUREMENTS_NAME}",
                "sha256": bytes_hash(measurements),
            }
        ],
        "row_count": len(rows),
        "row_chain_head": rows[0]["row_hash"],
        "row_chain_tail": rows[-1]["row_hash"],
        "source_artifacts": source_artifacts(root, manifest),
    }
    artifact_manifest["content_hash"] = content_hash(artifact_manifest)
    rendered_manifest = (
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return measurements, rendered_manifest


def materialize(root: Path, output_dir: Path, check: bool) -> None:
    measurements, artifact_manifest = build_outputs(root)
    expected = {
        output_dir / MEASUREMENTS_NAME: measurements,
        output_dir / ARTIFACT_MANIFEST_NAME: artifact_manifest,
    }
    if check:
        stale = []
        for path, payload in expected.items():
            try:
                actual = path.read_bytes()
            except OSError:
                actual = None
            if actual != payload:
                stale.append(path.name)
        if stale:
            raise ValueError(f"{', '.join(stale)} is stale; rebuild Z1 measurement rows")
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, payload in expected.items():
        path.write_bytes(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--source-root",
        type=Path,
        help="input tree holding source/ and raw/ (default: data/candidates/z1)",
    )
    parser.add_argument(
        "--result-uri-root",
        help="GCS URI prefix for raw artifacts (default: the float32 campaign root)",
    )
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    global SOURCE_ROOT, RESULT_URI_ROOT
    args = parse_args()
    if args.source_root is not None and args.result_uri_root is None:
        print(
            "--source-root requires --result-uri-root: rows must reference the same "
            "artifact root the raw inputs came from (Codex PR#45 P2)",
            file=sys.stderr,
        )
        return 2
    if args.source_root is not None:
        SOURCE_ROOT = args.source_root
    if args.result_uri_root is not None:
        RESULT_URI_ROOT = args.result_uri_root
    root = args.root.resolve()
    output_dir = (args.output_dir or root / SOURCE_ROOT).resolve()
    try:
        materialize(root, output_dir, args.check)
    except (KeyError, OSError, TypeError, ValueError, ZeroDivisionError) as error:
        print(f"Z1 measurement row build failed: {error}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "wrote"
    print(f"{action} {output_dir / MEASUREMENTS_NAME} and {output_dir / ARTIFACT_MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
