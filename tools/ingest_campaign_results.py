#!/usr/bin/env python3
"""Ingest hash-chained campaign measurements into the empirical-formal bridge.

Measurement input is JSON Lines. Each row is content-addressed by ``row_hash``
(the canonical JSON hash with that field omitted) and links to the preceding row
through ``previous_row_hash``. The first row must use null. Rows name one target
ClaimContract premise and carry the complete EvidenceBundle scope and receipt
metadata needed to produce an immutable bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import rfc8785
from generate_assumptions import (
    build_documents,
    content_hash,
    materialize,
    rendered,
)
from jsonschema import Draft202012Validator

HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
SCOPE_DIMENSIONS = ("structures", "chemistries", "properties")
MEASUREMENT_FIELDS = ("metric", "value", "unit", "acceptance_test", "sample_count")
# The EvidenceBundle schema defines typed measurements only for the predicates
# listed here (barrierErrorMeasurement and signSkewFraction/medianSignedError
# today); attaching typed measurements to any other predicate would publish a
# bundle whose measurements cannot describe the claim (Codex PR#41 P2).
# Reject instead of laundering.
TYPED_MEASUREMENT_PREDICATES = frozenset(
    {"barrier_mae_mev<=40", "signed_error_positive_fraction>0.5"}
)
EPISTEMIC_STATUSES = {
    "confirmatory",
    "exploratory",
    "descriptive",
    "negative",
    "unsupported",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA = REPOSITORY_ROOT / "schemas" / "campaign-manifest.v1.schema.json"
CLAIM_SCHEMA = REPOSITORY_ROOT / "schemas" / "research-claim-contract.v1.schema.json"
EVIDENCE_SCHEMA = REPOSITORY_ROOT / "evidence" / "v1" / "schema.json"


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label} from {path}: {error}") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be a JSON object")
    return document


def load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError(f"cannot read measurement rows from {path}: {error}") from error
    rows = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid measurement JSON on line {line_number}: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"measurement line {line_number} must be a JSON object")
        rows.append(row)
    if not rows:
        raise ValueError("measurement input contains no evidence rows")
    return rows


def validate_schema(document: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = load_object(schema_path, f"{label} schema")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"{label} schema validation failed at {location}: {error.message}")


def bytes_hash(path: Path) -> str:
    """Hash the exact bytes of an evidence artifact."""
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ValueError(f"missing evidence artifact {path}: {error}") from error
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_content_address(document: dict[str, Any], field: str, label: str) -> None:
    expected = content_hash({key: value for key, value in document.items() if key != field})
    if document.get(field) != expected:
        raise ValueError(f"non-canonical {label} {field}")


def relative_path(path: Path, root: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"{label} must be inside repository root {root}") from error


def require_string(document: dict[str, Any], field: str, label: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} requires non-empty {field}")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    validate_schema(manifest, MANIFEST_SCHEMA, "campaign manifest")
    if manifest.get("version") != 1:
        raise ValueError("campaign manifest version must be 1")
    require_string(manifest, "campaign_id", "campaign manifest")
    require_string(manifest, "preregistration_id", "campaign manifest")
    actual_hash = content_hash(
        {key: value for key, value in manifest.items() if key != "content_hash"}
    )
    if manifest.get("content_hash") != actual_hash:
        raise ValueError("campaign manifest content_hash mismatch")
    targets = manifest.get("target_premises")
    if not isinstance(targets, list) or not targets:
        raise ValueError("campaign manifest has no target premises")


def validate_scope(scope: Any, label: str) -> dict[str, Any]:
    if not isinstance(scope, dict):
        raise ValueError(f"{label} scope must be an object")
    for dimension in SCOPE_DIMENSIONS:
        values = scope.get(dimension)
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) or not value for value in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(f"{label} scope requires unique non-empty {dimension}")
    conditions = scope.get("conditions")
    if not isinstance(conditions, dict) or not conditions:
        raise ValueError(f"{label} scope requires conditions")
    return scope


def find_claim_and_premise(
    root: Path, claim_id: str, premise_id: str
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    claim_path = root / "registry" / "claims" / f"{claim_id}.json"
    claim = load_object(claim_path, f"ClaimContract {claim_id}")
    if claim.get("claim_id") != claim_id:
        raise ValueError(f"ClaimContract path does not contain {claim_id}")
    validate_schema(claim, CLAIM_SCHEMA, f"ClaimContract {claim_id}")
    validate_content_address(claim, "content_hash", "ClaimContract")
    matches = [item for item in claim.get("premises", []) if item.get("premise_id") == premise_id]
    if len(matches) != 1:
        raise ValueError(f"missing target premise {claim_id}/{premise_id}")
    return claim_path, claim, matches[0]


def allowed_scope(root: Path, premise: dict[str, Any]) -> tuple[dict[str, set[str]], set[str]]:
    allowed = {dimension: set() for dimension in SCOPE_DIMENSIONS}
    claim_predicates: set[str] = set()
    references = premise.get("bundle_references")
    if not isinstance(references, list) or not references:
        raise ValueError(
            f"target premise {premise.get('premise_id', '<unknown>')} has no baseline evidence"
        )
    evidence_paths = root / "evidence" / "v1" / "examples"
    evidence_by_id = {
        bundle["bundle_id"]: bundle
        for path in evidence_paths.glob("*.json")
        for bundle in [load_object(path, "EvidenceBundle")]
    }
    for bundle_id, bundle in evidence_by_id.items():
        validate_schema(bundle, EVIDENCE_SCHEMA, f"EvidenceBundle {bundle_id}")
        validate_content_address(bundle, "bundle_id", "EvidenceBundle")
    for reference in references:
        bundle_id = reference.get("bundle_id")
        if bundle_id not in evidence_by_id:
            raise ValueError(f"missing baseline EvidenceBundle {bundle_id}")
        scope = validate_scope(evidence_by_id[bundle_id].get("scope"), f"bundle {bundle_id}")
        claim_predicates.add(
            require_string(evidence_by_id[bundle_id], "claim_predicate", f"bundle {bundle_id}")
        )
        for dimension in SCOPE_DIMENSIONS:
            allowed[dimension].update(scope[dimension])
    return allowed, claim_predicates


def validate_scope_compatibility(
    scope: dict[str, Any], allowed: dict[str, set[str]], claim_id: str, premise_id: str
) -> None:
    for dimension in SCOPE_DIMENSIONS:
        unexpected = set(scope[dimension]) - allowed[dimension]
        if unexpected:
            raise ValueError(
                f"scope mismatch for {claim_id}/{premise_id}: {dimension} "
                f"outside supported scope: {sorted(unexpected)}"
            )


def validate_row_chain(rows: list[dict[str, Any]], manifest_hash: str) -> None:
    previous_hash: str | None = None
    seen_ids = set()
    for index, row in enumerate(rows, 1):
        row_id = require_string(row, "row_id", f"measurement row {index}")
        if row_id in seen_ids:
            raise ValueError(f"duplicate measurement row_id {row_id}")
        seen_ids.add(row_id)
        if row.get("campaign_manifest_hash") != manifest_hash:
            raise ValueError(f"measurement {row_id} is not bound to the campaign manifest")
        if row.get("previous_row_hash") != previous_hash:
            raise ValueError(f"measurement hash chain is broken at {row_id}")
        canonical_row = rfc8785.dumps(
            {key: value for key, value in row.items() if key != "row_hash"}
        )
        actual_hash = "sha256:" + hashlib.sha256(canonical_row).hexdigest()
        if row.get("row_hash") != actual_hash:
            raise ValueError(f"measurement row_hash mismatch at {row_id}")
        previous_hash = actual_hash


def typed_measurements(row: dict[str, Any]) -> Any | None:
    """Return bundle measurements from the row's canonical or legacy form.

    Fail closed when a typed measurement cannot describe the row's claim
    predicate: the bundle schema defines typed measurements for specific
    predicates, and attaching a mismatched measurement would publish a
    schema-valid bundle whose measurements describe something else.
    """
    has_typed = "measurements" in row or any(field in row for field in MEASUREMENT_FIELDS)
    if has_typed and row.get("claim_predicate") not in TYPED_MEASUREMENT_PREDICATES:
        raise ValueError(
            f"measurement {row.get('row_id', '<unknown>')} carries typed measurements on "
            f"unsupported predicate {row.get('claim_predicate')!r}; the EvidenceBundle "
            f"schema defines typed measurements only for {sorted(TYPED_MEASUREMENT_PREDICATES)}"
        )
    if "measurements" in row:
        return row["measurements"]
    present = [field for field in MEASUREMENT_FIELDS if field in row]
    if not present:
        return None
    missing = [field for field in MEASUREMENT_FIELDS if field not in row]
    if missing:
        raise ValueError(
            f"measurement {row.get('row_id', '<unknown>')} has incomplete typed measurement; "
            f"missing {', '.join(missing)}"
        )
    return [{field: row[field] for field in MEASUREMENT_FIELDS}]


def bundle_from_row(
    root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    row: dict[str, Any],
) -> dict[str, Any]:
    row_id = row["row_id"]
    status = require_string(row, "epistemic_status", f"measurement {row_id}")
    if status not in EPISTEMIC_STATUSES:
        raise ValueError(f"measurement {row_id} has unsupported epistemic_status {status!r}")
    artifact = root / require_string(row, "artifact", f"measurement {row_id}")
    relative_artifact = relative_path(artifact, root, "evidence artifact")
    expected_artifact_hash = require_string(row, "artifact_hash", f"measurement {row_id}")
    if not HASH_PATTERN.fullmatch(expected_artifact_hash):
        raise ValueError(f"measurement {row_id} has invalid artifact_hash")
    if bytes_hash(artifact) != expected_artifact_hash:
        raise ValueError(f"evidence artifact hash mismatch for {row_id}")
    provenance = row.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"measurement {row_id} requires provenance")
    bundle = {
        "claim_predicate": require_string(row, "claim_predicate", f"measurement {row_id}"),
        "epistemic_status": status,
        "scope": validate_scope(row.get("scope"), f"measurement {row_id}"),
        "evidence_refs": [
            {
                "campaign": manifest["campaign_id"],
                "campaign_manifest": relative_path(manifest_path, root, "campaign manifest"),
                "campaign_manifest_hash": bytes_hash(manifest_path),
                "run_id": require_string(row, "run_id", f"measurement {row_id}"),
                "artifact": relative_artifact,
                "artifact_hash": expected_artifact_hash,
                "thresholds_version": require_string(
                    row, "thresholds_version", f"measurement {row_id}"
                ),
            }
        ],
        "provenance": {
            "agent": require_string(provenance, "agent", f"measurement {row_id} provenance"),
            "human": require_string(provenance, "human", f"measurement {row_id} provenance"),
            "timestamp": require_string(
                provenance, "timestamp", f"measurement {row_id} provenance"
            ),
            "preregistration_id": manifest["preregistration_id"],
        },
        "supersedes": [],
    }
    if "measurements" in row or any(field in row for field in MEASUREMENT_FIELDS):
        bundle["measurements"] = typed_measurements(row)
    enforce_path_minimums(manifest, bundle, artifact, row_id)
    bundle["bundle_id"] = content_hash(bundle)
    return bundle


def _distinct_paths(document: Any) -> int | None:
    if isinstance(document, dict):
        n_paths = document.get("n_paths")
        if isinstance(n_paths, int) and not isinstance(n_paths, bool) and n_paths >= 1:
            return n_paths
        rows = document.get("per_row")
        if isinstance(rows, list) and rows:
            indices = {
                row.get("path_index")
                for row in rows
                if isinstance(row, dict) and isinstance(row.get("path_index"), int)
            }
            if indices:
                return len(indices)
    return None


def enforce_path_minimums(
    manifest: dict[str, Any], bundle: dict[str, Any], artifact: Path, row_id: str
) -> None:
    """Fail closed when a panel-level receipt under-covers a declared path minimum.

    Panel-level predicates (the sign-skew family) define their acceptance over
    the whole recorded panel, so the cited artifact must document at least the
    manifest's neb-path-set minimum of DISTINCT paths, and every typed
    measurement must cover that many samples. Per-model barrier receipts
    instead disclose honest per-path failures, so their sample_count
    legitimately falls below the panel size and is not gated here.
    """
    predicate = bundle.get("claim_predicate")
    if not isinstance(predicate, str) or not predicate.startswith(
        "signed_error_positive_fraction"
    ):
        return
    minimums = [
        requirement["minimum_count"]
        for requirement in manifest.get("evidence_requirements", [])
        if isinstance(requirement, dict)
        and requirement.get("artifact_type") == "neb-path-set"
        and isinstance(requirement.get("minimum_count"), int)
    ]
    if not minimums:
        return
    floor = max(minimums)
    try:
        document = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"measurement {row_id} cites an artifact that cannot prove path coverage: {error}"
        ) from error
    distinct = _distinct_paths(document)
    if distinct is None or distinct < floor:
        raise ValueError(
            f"measurement {row_id} documents {distinct if distinct is not None else 'no'} "
            f"distinct paths, below the manifest's recorded-path minimum {floor}"
        )
    for measurement in bundle.get("measurements", []):
        if not isinstance(measurement, dict):
            continue
        sample_count = measurement.get("sample_count")
        if isinstance(sample_count, int) and sample_count < floor:
            raise ValueError(
                f"measurement {row_id} sample_count {sample_count} is below the "
                f"manifest's recorded-path minimum {floor}"
            )


def safe_filename(campaign_id: str, row_id: str) -> str:
    stem = re.sub(r"[^a-z0-9]+", "-", f"{campaign_id}-{row_id}".lower()).strip("-")
    return f"round4-{stem}.json"


def ingest(root: Path, manifest_path: Path, measurements_path: Path) -> list[str]:
    manifest = load_object(manifest_path, "campaign manifest")
    validate_manifest(manifest)
    rows = load_rows(measurements_path)
    validate_row_chain(rows, manifest["content_hash"])

    targets = {
        (
            require_string(target, "claim_id", "campaign target"),
            require_string(target, "premise_id", "campaign target"),
        )
        for target in manifest["target_premises"]
        if isinstance(target, dict)
    }
    if len(targets) != len(manifest["target_premises"]):
        raise ValueError("campaign manifest contains invalid or duplicate target premises")
    rows_by_target: dict[tuple[str, str], list[dict[str, Any]]] = {target: [] for target in targets}
    for row in rows:
        target = (
            require_string(row, "claim_id", "measurement"),
            require_string(row, "premise_id", "measurement"),
        )
        if target not in rows_by_target:
            raise ValueError(f"measurement targets undeclared premise {target[0]}/{target[1]}")
        rows_by_target[target].append(row)
    missing = [target for target, target_rows in rows_by_target.items() if not target_rows]
    if missing:
        claim_id, premise_id = sorted(missing)[0]
        raise ValueError(f"missing evidence for target premise {claim_id}/{premise_id}")

    claims: dict[Path, dict[str, Any]] = {}
    bundles: list[tuple[Path, dict[str, Any]]] = []
    for (claim_id, premise_id), target_rows in rows_by_target.items():
        claim_path = root / "registry" / "claims" / f"{claim_id}.json"
        if claim_path in claims:
            claim = claims[claim_path]
            matches = [
                item for item in claim.get("premises", []) if item.get("premise_id") == premise_id
            ]
            if len(matches) != 1:
                raise ValueError(f"missing target premise {claim_id}/{premise_id}")
            premise = matches[0]
        else:
            claim_path, claim, premise = find_claim_and_premise(root, claim_id, premise_id)
            claims[claim_path] = claim
        allowed, claim_predicates = allowed_scope(root, premise)
        for row in target_rows:
            claim_predicate = require_string(row, "claim_predicate", f"measurement {row['row_id']}")
            if claim_predicate not in claim_predicates:
                raise ValueError(
                    f"claim predicate mismatch for {claim_id}/{premise_id}: "
                    f"{claim_predicate!r} is not supported by baseline evidence"
                )
            scope = validate_scope(row.get("scope"), f"measurement {row['row_id']}")
            validate_scope_compatibility(scope, allowed, claim_id, premise_id)
            bundle = bundle_from_row(root, manifest_path, manifest, row)
            validate_schema(bundle, EVIDENCE_SCHEMA, f"EvidenceBundle for {row['row_id']}")
            bundle_path = (
                root
                / "evidence"
                / "v1"
                / "examples"
                / safe_filename(manifest["campaign_id"], row["row_id"])
            )
            if bundle_path.exists() and load_object(bundle_path, "EvidenceBundle") != bundle:
                raise ValueError(f"refusing to overwrite different EvidenceBundle {bundle_path}")
            bundles.append((bundle_path, bundle))
            references = premise["bundle_references"]
            if not any(
                reference.get("bundle_id") == bundle["bundle_id"] for reference in references
            ):
                references.append({"bundle_id": bundle["bundle_id"]})

    for claim in claims.values():
        claim["content_hash"] = content_hash(
            {key: value for key, value in claim.items() if key != "content_hash"}
        )
        validate_schema(claim, CLAIM_SCHEMA, f"ClaimContract {claim['claim_id']}")

    with tempfile.TemporaryDirectory(prefix="campaign-ingest-") as temporary_directory:
        staged_root = Path(temporary_directory)
        shutil.copytree(root / "registry" / "claims", staged_root / "registry" / "claims")
        shutil.copytree(
            root / "evidence" / "v1" / "examples",
            staged_root / "evidence" / "v1" / "examples",
        )
        # Campaign manifests participate in the generated snapshot lock.  Keep
        # them in the transactional staging tree so validation compares the
        # same corpus that will be materialized in the real root.
        campaigns = root / "campaigns" / "v1"
        if campaigns.exists():
            shutil.copytree(campaigns, staged_root / "campaigns" / "v1")
        for path, claim in claims.items():
            staged_path = staged_root / path.relative_to(root)
            staged_path.write_text(rendered(claim), encoding="utf-8")
        for path, bundle in bundles:
            staged_path = staged_root / path.relative_to(root)
            staged_path.write_text(rendered(bundle), encoding="utf-8")
        registry, lock = build_documents(staged_root)

    for path, bundle in bundles:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered(bundle), encoding="utf-8")
    for path, claim in claims.items():
        path.write_text(rendered(claim), encoding="utf-8")
    if not materialize(root, root, check=False):
        raise ValueError("assumption generator did not materialize outputs")
    if build_documents(root) != (registry, lock):
        raise ValueError("materialized assumption documents differ from validated staging")
    return [bundle["bundle_id"] for _path, bundle in bundles]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle_ids = ingest(
            args.root.resolve(), args.manifest.resolve(), args.measurements.resolve()
        )
    except (KeyError, TypeError, ValueError) as error:
        print(f"ingestion failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"ingested_bundle_ids": bundle_ids}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
