#!/usr/bin/env python3
"""Build deterministic, content-addressed Z3 campaign measurement rows."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import rfc8785

MANIFEST_PATH = Path("campaigns/v1/z3.campaign-manifest.v1.json")
SOURCE_ROOT = Path("data/candidates/z3")
SOURCE_PATH = SOURCE_ROOT / "source" / "z3-candidate-measurements.json"
CORRECTION_PATH = SOURCE_ROOT / "delta-correction-report.json"
MEASUREMENTS_NAME = "measurements.jsonl"
ARTIFACT_MANIFEST_NAME = "artifact-manifest.json"
ARTIFACT_DIRECTORY = "artifacts"
CLAIM_ID = "discovery.z3.adsorption-accuracy.v1"
PREMISE_ID = "hard_materials_z3_adsorption_mae"
CLAIM_PREDICATE = "adsorption_energy_mae<=0.1"
THRESHOLDS_VERSION = "hard-materials-z3.v1"
PRODUCER = "gcp/z3-campaign/run_measurement.py"
ACCOUNTABLE_HUMAN = "Alex Welcing (director)"
EXPECTED_SOURCE_SCHEMA = "lupine.z3.candidate_measurements.v1"
EXPECTED_ARTIFACT_SCHEMA = "lupine.z3.candidate_measurement_artifact.v1"
EXPECTED_MODEL_COUNT = 4
EXPECTED_CANDIDATE_COUNT = 32
EXPECTED_MEASUREMENT_COUNT = EXPECTED_MODEL_COUNT * EXPECTED_CANDIDATE_COUNT


def canonical_bytes(document: Any) -> bytes:
    """Serialize a JSON value using RFC 8785 JSON canonicalization."""
    try:
        return rfc8785.dumps(document)
    except (rfc8785.CanonicalizationError, TypeError) as error:
        raise ValueError(f"value is not RFC 8785 canonicalizable: {error}") from error


def content_hash(document: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(document)).hexdigest()


def bytes_hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def rendered(document: Any) -> bytes:
    return (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


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
    if manifest.get("campaign_id") != "discovery.round-4.z3-adsorption.v1":
        raise ValueError("unexpected governing campaign")
    acceptance = manifest.get("acceptance_test", {})
    if acceptance != {
        "metric": "adsorption_energy_mae",
        "operator": "lte",
        "threshold": 0.1,
        "unit": "eV",
    }:
        raise ValueError("governing campaign has an unexpected acceptance test")
    targets = manifest.get("target_premises")
    if targets != [{"claim_id": CLAIM_ID, "premise_id": PREMISE_ID}]:
        raise ValueError("governing campaign has an unexpected target premise")
    return manifest


def require_finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def validate_source(manifest: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    if source.get("schema") != EXPECTED_SOURCE_SCHEMA:
        raise ValueError("raw source has an unexpected schema")
    if source.get("run_id") != "z3-20260719":
        raise ValueError("raw source has an unexpected run_id")
    if source.get("candidate_count") != EXPECTED_CANDIDATE_COUNT:
        raise ValueError("raw source candidate_count is incomplete")
    if source.get("model_count") != EXPECTED_MODEL_COUNT:
        raise ValueError("raw source model_count is incomplete")
    if source.get("raw_measurement_count") != EXPECTED_MEASUREMENT_COUNT:
        raise ValueError("raw source measurement count is incomplete")
    if source.get("delta_hybrid_measurement_count") != 0:
        raise ValueError("raw source unexpectedly claims delta-hybrid measurements")
    blocker = source.get("correction_blocker", {})
    if blocker.get("code") != "Z3_DELTA_CORRECTION_MODEL_UNSPECIFIED":
        raise ValueError("raw source does not retain the frozen correction blocker")

    candidates = source.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != EXPECTED_CANDIDATE_COUNT:
        raise ValueError("raw source must contain exactly 32 candidates")
    candidate_ids = [candidate.get("candidate_id") for candidate in candidates]
    if any(not isinstance(candidate_id, str) or not candidate_id for candidate_id in candidate_ids):
        raise ValueError("raw source contains a candidate without an identity")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("raw source contains duplicate candidates")
    if candidate_ids != sorted(candidate_ids):
        raise ValueError("raw source candidates are not deterministically ordered")

    expected_models = sorted(model["model_id"] for model in manifest["available_models"])
    total_measurements = 0
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        reference = candidate.get("reference", {})
        reference_energy = require_finite(
            reference.get("adsorption_energy_ev"), f"{candidate_id} reference energy"
        )
        uncertainty = require_finite(
            reference.get("uncertainty_ev"), f"{candidate_id} reference uncertainty"
        )
        if uncertainty < 0:
            raise ValueError(f"{candidate_id} reference uncertainty must be nonnegative")
        if candidate.get("split") not in {
            "delta_train",
            "delta_validation",
            "confirmatory_test",
        }:
            raise ValueError(f"{candidate_id} has an unknown locked split")
        model_measurements = candidate.get("model_measurements")
        if not isinstance(model_measurements, list):
            raise ValueError(f"{candidate_id} has no model measurements")
        model_ids = [measurement.get("model_id") for measurement in model_measurements]
        if model_ids != expected_models:
            raise ValueError(f"{candidate_id} does not contain the complete ordered model panel")
        for measurement in model_measurements:
            model_id = measurement["model_id"]
            if measurement.get("candidate_id") != candidate_id:
                raise ValueError(f"candidate mismatch for {candidate_id}/{model_id}")
            raw_energy = require_finite(
                measurement.get("raw_adsorption_energy_ev"),
                f"{candidate_id}/{model_id} raw adsorption energy",
            )
            signed_error = require_finite(
                measurement.get("raw_signed_error_ev"),
                f"{candidate_id}/{model_id} signed error",
            )
            measured_reference = require_finite(
                measurement.get("reference_adsorption_energy_ev"),
                f"{candidate_id}/{model_id} reference energy",
            )
            measured_uncertainty = require_finite(
                measurement.get("reference_uncertainty_ev"),
                f"{candidate_id}/{model_id} reference uncertainty",
            )
            if not math.isclose(measured_reference, reference_energy, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"reference mismatch for {candidate_id}/{model_id}")
            if not math.isclose(measured_uncertainty, uncertainty, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"uncertainty mismatch for {candidate_id}/{model_id}")
            if not math.isclose(raw_energy - reference_energy, signed_error, rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"signed error mismatch for {candidate_id}/{model_id}")
            if measurement.get("delta_hybrid_corrected_adsorption_energy_ev") is not None:
                raise ValueError(f"post-hoc delta correction found for {candidate_id}/{model_id}")
            if measurement.get("delta_status") != "blocked_protocol_unspecified":
                raise ValueError(f"correction blocker missing for {candidate_id}/{model_id}")
        total_measurements += len(model_measurements)
    if total_measurements != EXPECTED_MEASUREMENT_COUNT:
        raise ValueError("raw source does not contain all 128 measurements")
    return candidates


def validate_correction_report(
    root: Path, source: dict[str, Any], candidates: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    payload = (root / CORRECTION_PATH).read_bytes()
    sidecar_path = root / Path(f"{CORRECTION_PATH}.sha256")
    sidecar = sidecar_path.read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(payload).hexdigest() != sidecar:
        raise ValueError("delta-correction report does not match its SHA-256 sidecar")
    report = load_object(root / CORRECTION_PATH)
    if report.get("schema") != "lupine.z3.delta_correction_report.v1":
        raise ValueError("delta-correction report has an unexpected schema")
    if report.get("run_id") != source["run_id"]:
        raise ValueError("delta-correction report run_id does not match the raw source")
    models = report.get("models")
    expected_models = sorted(item["model_id"] for item in candidates[0]["model_measurements"])
    if not isinstance(models, dict) or sorted(models) != expected_models:
        raise ValueError("delta-correction report does not contain the complete model panel")
    expected_test_ids = {
        candidate["candidate_id"]
        for candidate in candidates
        if candidate["split"] == "confirmatory_test"
    }
    if len(expected_test_ids) != 20:
        raise ValueError("raw source does not contain exactly 20 confirmatory-test candidates")
    for model_id, result in models.items():
        rows = result.get("test_rows")
        if not isinstance(rows, list) or {row.get("candidate_id") for row in rows} != expected_test_ids:
            raise ValueError(f"{model_id} correction report has incomplete holdout coverage")
        corrected_mae = sum(
            require_finite(row.get("corrected_absolute_error_ev"), f"{model_id} corrected error")
            for row in rows
        ) / len(rows)
        reported_mae = require_finite(result.get("corrected_test_mae"), f"{model_id} corrected MAE")
        if not math.isclose(corrected_mae, reported_mae, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"{model_id} corrected holdout MAE is inconsistent")
        if result.get("gate_outcome") != "fail":
            raise ValueError(f"{model_id} correction report does not retain the failed gate")
    return models


def enriched_candidates(
    candidates: list[dict[str, Any]], models: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    enriched = copy.deepcopy(candidates)
    corrections = {
        (model_id, row["candidate_id"]): row
        for model_id, result in models.items()
        for row in result["test_rows"]
    }
    for candidate in enriched:
        for measurement in candidate["model_measurements"]:
            model_id = measurement["model_id"]
            candidate_id = candidate["candidate_id"]
            correction = corrections.get((model_id, candidate_id))
            if correction is None:
                measurement["delta_status"] = "not_scored_fit_or_selection_split"
                continue
            baseline_error = require_finite(
                measurement["raw_signed_error_ev"], f"{model_id}/{candidate_id} baseline error"
            )
            reported_baseline = require_finite(
                correction["baseline_signed_error_ev"], f"{model_id}/{candidate_id} report baseline"
            )
            if not math.isclose(baseline_error, reported_baseline, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"delta-correction baseline mismatch for {candidate_id}/{model_id}")
            signed_error = require_finite(
                correction["corrected_signed_error_ev"], f"{model_id}/{candidate_id} corrected error"
            )
            delta_correction = require_finite(
                correction["delta_correction_ev"], f"{model_id}/{candidate_id} correction"
            )
            absolute_error = require_finite(
                correction["corrected_absolute_error_ev"],
                f"{model_id}/{candidate_id} absolute error",
            )
            if not math.isclose(
                baseline_error - delta_correction,
                signed_error,
                rel_tol=1e-12,
                abs_tol=1e-12,
            ) or not math.isclose(
                abs(signed_error), absolute_error, rel_tol=1e-12, abs_tol=1e-12
            ):
                raise ValueError(
                    f"corrected signed error is inconsistent for {candidate_id}/{model_id}"
                )
            measurement.update(
                {
                    "corrected_absolute_error_ev": absolute_error,
                    "corrected_signed_error_ev": signed_error,
                    "delta_correction_ev": delta_correction,
                    "delta_hybrid_corrected_adsorption_energy_ev": (
                        measurement["reference_adsorption_energy_ev"] + signed_error
                    ),
                    "delta_status": "corrected_confirmatory_test",
                    "selected_correction_form": models[model_id]["selected_form"],
                }
            )
    return enriched


def candidate_artifact(
    manifest: dict[str, Any],
    source_hash: str,
    correction_hash: str,
    source: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": EXPECTED_ARTIFACT_SCHEMA,
        "campaign_manifest": {
            "content_hash": manifest["content_hash"],
            "path": MANIFEST_PATH.as_posix(),
        },
        "source": {
            "path": SOURCE_PATH.as_posix(),
            "sha256": source_hash,
        },
        "delta_correction_report": {
            "path": CORRECTION_PATH.as_posix(),
            "sha256": correction_hash,
        },
        "run_id": source["run_id"],
        "unit": "eV",
        "candidate": candidate,
    }


def build_row(
    manifest: dict[str, Any],
    source: dict[str, Any],
    candidates: list[dict[str, Any]],
    model_id: str,
    model_result: dict[str, Any],
    correction_payload: bytes,
    candidate_artifacts: list[dict[str, str]],
    previous_row_hash: str | None,
) -> dict[str, Any]:
    threshold = float(manifest["acceptance_test"]["threshold"])
    holdout = [candidate for candidate in candidates if candidate["split"] == "confirmatory_test"]
    structures = [candidate["candidate_id"] for candidate in holdout]
    chemistries = sorted(
        {
            system["system_id"]
            for candidate in holdout
            for measurement in candidate["model_measurements"]
            if measurement["model_id"] == model_id
            for system in measurement["systems"]
        }
    )
    aggregate = {
        "acceptance_test": {
            "comparator": "less_than_or_equal",
            "outcome": "fail",
            "threshold": threshold,
            "unit": "eV",
        },
        "baseline_holdout_mae_ev": model_result["baseline_test_mae"],
        "corrected_holdout_mae_ev": model_result["corrected_test_mae"],
        "metric": "adsorption_energy_mae",
        "sample_count": len(model_result["test_rows"]),
        "selected_correction_form": model_result["selected_form"],
        "unit": "eV",
    }
    row = {
        "row_id": f"z3-{model_id}",
        "campaign_manifest": MANIFEST_PATH.as_posix(),
        "campaign_manifest_hash": manifest["content_hash"],
        "previous_row_hash": previous_row_hash,
        "claim_id": CLAIM_ID,
        "premise_id": PREMISE_ID,
        "claim_predicate": CLAIM_PREDICATE,
        "epistemic_status": "negative",
        "scope": {
            "structures": structures,
            "chemistries": chemistries,
            "properties": ["adsorption_energy"],
            "conditions": {
                "acceptance_comparator": "less_than_or_equal",
                "acceptance_threshold_ev": threshold,
                "baseline_holdout_mae_ev": aggregate["baseline_holdout_mae_ev"],
                "correction_status": "executed_no_holdout_leakage",
                "corrected_holdout_mae_ev": aggregate["corrected_holdout_mae_ev"],
                "fit_exclusion": "delta_train fit; delta_validation selection; confirmatory_test scoring only",
                "model_id": model_id,
                "outcome": "fail",
                "reference_kind": "published DFT electronic energy at 0 K",
                "sample_count": aggregate["sample_count"],
                "selected_correction_form": aggregate["selected_correction_form"],
                "unit": "eV",
            },
        },
        "aggregate_result": aggregate,
        "candidate_artifacts": candidate_artifacts,
        "model_id": model_id,
        "run_id": source["run_id"],
        "artifact": CORRECTION_PATH.as_posix(),
        "artifact_hash": bytes_hash(correction_payload),
        "thresholds_version": THRESHOLDS_VERSION,
        "provenance": {
            "agent": PRODUCER,
            "human": ACCOUNTABLE_HUMAN,
            "timestamp": source["created_at"],
        },
    }
    row["row_hash"] = content_hash(row)
    return row


def build_outputs(root: Path) -> dict[Path, bytes]:
    manifest = validate_manifest(root)
    source_payload = (root / SOURCE_PATH).read_bytes()
    source = load_object(root / SOURCE_PATH)
    raw_candidates = validate_source(manifest, source)
    models = validate_correction_report(root, source, raw_candidates)
    candidates = enriched_candidates(raw_candidates, models)
    source_hash = bytes_hash(source_payload)
    correction_payload = (root / CORRECTION_PATH).read_bytes()
    correction_hash = bytes_hash(correction_payload)

    outputs: dict[Path, bytes] = {}
    rows = []
    previous_row_hash = None
    artifact_entries = []
    for candidate in candidates:
        artifact = candidate_artifact(
            manifest, source_hash, correction_hash, source, candidate
        )
        artifact_payload = rendered(artifact)
        artifact_relative = Path(ARTIFACT_DIRECTORY) / f"{candidate['candidate_id']}.json"
        outputs[artifact_relative] = artifact_payload
        artifact_entries.append(
            {
                "bytes": len(artifact_payload),
                "path": (SOURCE_ROOT / artifact_relative).as_posix(),
                "sha256": bytes_hash(artifact_payload),
            }
        )
    for model_id, model_result in sorted(models.items()):
        candidate_artifact_refs = [
            {"path": entry["path"], "sha256": entry["sha256"]}
            for entry in artifact_entries
        ]
        row = build_row(
            manifest,
            source,
            candidates,
            model_id,
            model_result,
            correction_payload,
            candidate_artifact_refs,
            previous_row_hash,
        )
        rows.append(row)
        previous_row_hash = row["row_hash"]

    measurements = b"".join(canonical_bytes(row) + b"\n" for row in rows)
    outputs[Path(MEASUREMENTS_NAME)] = measurements
    artifact_manifest = {
        "schema": "lupine.z3.measurement-artifact-manifest.v1",
        "campaign_manifest_hash": manifest["content_hash"],
        "source_artifact": {
            "bytes": len(source_payload),
            "path": SOURCE_PATH.as_posix(),
            "sha256": source_hash,
        },
        "delta_correction_artifact": {
            "bytes": len(correction_payload),
            "path": CORRECTION_PATH.as_posix(),
            "sha256": correction_hash,
        },
        "measurements_path": (SOURCE_ROOT / MEASUREMENTS_NAME).as_posix(),
        "measurements_bytes": len(measurements),
        "measurements_sha256": bytes_hash(measurements),
        "row_count": len(rows),
        "artifact_count": len(artifact_entries),
        "row_chain_head": rows[0]["row_hash"],
        "row_chain_tail": rows[-1]["row_hash"],
        "files": [
            {
                "bytes": len(measurements),
                "path": (SOURCE_ROOT / MEASUREMENTS_NAME).as_posix(),
                "sha256": bytes_hash(measurements),
            },
            *artifact_entries,
        ],
    }
    artifact_manifest["content_hash"] = content_hash(artifact_manifest)
    outputs[Path(ARTIFACT_MANIFEST_NAME)] = rendered(artifact_manifest)
    return outputs


def materialize(root: Path, output_dir: Path, check: bool) -> None:
    expected = {output_dir / path: payload for path, payload in build_outputs(root).items()}
    if check:
        stale = []
        for path, payload in expected.items():
            try:
                actual = path.read_bytes()
            except OSError:
                actual = None
            if actual != payload:
                stale.append(path.relative_to(output_dir).as_posix())
        if stale:
            raise ValueError(f"{', '.join(stale)} is stale; rebuild Z3 measurement rows")
        return
    for path, payload in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output_dir = (args.output_dir or root / SOURCE_ROOT).resolve()
    try:
        materialize(root, output_dir, args.check)
    except (KeyError, OSError, TypeError, ValueError, ZeroDivisionError) as error:
        print(f"Z3 measurement row build failed: {error}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "wrote"
    print(
        f"{action} {output_dir / MEASUREMENTS_NAME}, "
        f"{output_dir / ARTIFACT_MANIFEST_NAME}, and 32 candidate artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
