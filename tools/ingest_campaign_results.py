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
import math
import statistics
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
# The sign-skew family's frozen panel: 22 measured paths from the locked Z1 union
# campaign. The floor is pinned here, not derived from a caller-controlled manifest.
FROZEN_PANEL_PATH_MINIMUM = 22
# The family's single canonical recorded source. A caller-supplied manifest may not
# substitute its own file: consistency is proven only against this locked source.
CANONICAL_RECORDED_SOURCE = "data/candidates/z1-union-campaign.json"
CANONICAL_RECORDED_DIGEST = (
    "sha256:af8a02ad5a663de2433b78917569af01f12a10f54ac8d94b33e934cfedc8a3f2"
)
# The frozen family's single campaign identity. Cloned manifests under a fresh
# campaign_id would count as independent replication in readiness grading.
CANONICAL_CAMPAIGN_ID = "literature.protocol-offset-sign-skew.v1"
# The frozen family measures all four models; a reduced panel is not the claim.
CANONICAL_MODEL_IDS = frozenset(
    {"chgnet", "mace-mp-medium", "mace-mp-small", "mace-mpa-0-medium"}
)
# Model ids are caller-controlled; bind the full provenance triple so a manifest
# keeping the ids but altering hashes or versions is rejected exactly as in the
# nightly feedback authenticator.
CANONICAL_MODEL_ENTRIES = frozenset(
    {
        ("chgnet", "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890", "chgnet 0.4.2"),
        ("mace-mp-small", "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694", "mace-torch 0.3.16 / small"),
        ("mace-mp-medium", "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3", "mace-torch 0.3.16 / medium"),
        ("mace-mpa-0-medium", "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9", "mace-torch 0.3.16 / mpa-0 medium"),
    }
)
# The canonical dataset file the near-clone guard compares against; independent
# from the identity-lock constant so tests can override them separately.
DEDUPE_CANONICAL_SOURCE = "data/candidates/z1-union-campaign.json"
# Content fingerprint of the canonical dataset's observations (status and value
# per path/model), so a reserialized copy is recognized as the same dataset.
CANONICAL_SOURCE_FINGERPRINT = (
    "sha256:b9137ff7830c50cfdc59ec837ef2bb099326657c5d5e2d2ae158143360653989"
)


def _measured_observations(source: Any) -> set[tuple[str, str, float]]:
    observations: set[tuple[str, str, float]] = set()
    if not isinstance(source, dict):
        return observations
    for entry in source.get("per_path", []):
        if not isinstance(entry, dict):
            continue
        identity = entry.get("path_id")
        for model, record in (entry.get("per_model") or {}).items():
            value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
            if (
                value is not None
                and record.get("complete", False)
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
            ):
                observations.add((identity, model, round(float(value), 4)))
    return observations


def _source_fingerprint(source: Any) -> str | None:
    if not isinstance(source, dict):
        return None
    observations = []
    identities = []
    indices = []
    for entry in source.get("per_path", []):
        if not isinstance(entry, dict):
            continue
        identity = entry.get("path_id")
        identities.append(identity)
        indices.append(entry.get("path_index"))
        for model, record in (entry.get("per_model") or {}).items():
            value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
            if value is not None and record.get("complete", False):
                observations.append([identity, model, "measured", round(float(value), 4)])
    if len(identities) != len(set(identities)) or len(indices) != len(set(indices)):
        raise ValueError("locked source contains duplicate stable path identities")
    observations.sort()
    canonical = json.dumps(observations, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()
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
        enforce_predicate_manifest_alignment(manifest, bundle, row_id)
    dataset_fingerprint = enforce_path_minimums(root, manifest, bundle, artifact, row_id)
    if dataset_fingerprint is not None:
        bundle["evidence_refs"][0]["dataset_fingerprint"] = dataset_fingerprint
    bundle["bundle_id"] = content_hash(bundle)
    return bundle


PREDICATE_SHAPE_RE = re.compile(
    r"^(?P<metric>[a-z0-9_]+)_(?P<unit>mev|fraction)(?P<comparator><=|>)(?P<threshold>[0-9]+(?:\.[0-9]+)?)$"
)
PREDICATE_OPERATORS = {"<=": "lte", ">": "gt"}


def enforce_predicate_manifest_alignment(
    manifest: dict[str, Any], bundle: dict[str, Any], row_id: str
) -> None:
    """Bind a typed row's claim predicate to its manifest's acceptance test."""
    predicate = bundle.get("claim_predicate")
    match = PREDICATE_SHAPE_RE.fullmatch(predicate) if isinstance(predicate, str) else None
    if match is None:
        return
    acceptance = manifest.get("acceptance_test")
    expected = {
        "metric": match.group("metric"),
        "operator": PREDICATE_OPERATORS[match.group("comparator")],
        "threshold": float(match.group("threshold")),
        "unit": match.group("unit"),
    }
    actual = (
        {
            "metric": acceptance.get("metric"),
            "operator": acceptance.get("operator"),
            "threshold": float(acceptance.get("threshold", -1)),
            "unit": str(acceptance.get("unit", "")).lower(),
        }
        if isinstance(acceptance, dict)
        else {}
    )
    if actual != expected:
        raise ValueError(
            f"measurement {row_id} predicate {predicate!r} does not match the "
            "manifest's acceptance test"
        )


def _coverage(document: Any) -> tuple[set[int], set[str], set[tuple[int, str]], list[dict]] | None:
    """Derive (path indices, models, disclosed pairs, rows) from artifact rows.

    Every row must be a terminal record — measured with a numeric signed error
    or an explicit failure — and each (path, model) pair may appear once.
    """
    if not isinstance(document, dict):
        return None
    rows = document.get("per_row") or document.get("per_path")
    if not isinstance(rows, list) or not rows:
        return None
    paths: set[int] = set()
    models: set[str] = set()
    pairs: set[tuple[int, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("coverage rows must be objects")
        index = row.get("path_index")
        model = row.get("model")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not isinstance(model, str)
        ):
            raise ValueError("coverage rows require a path_index and a model")
        status = row.get("status")
        value = row.get("signed_error_mev")
        if status == "measured":
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(
                    f"measured row for path {index} model {model} requires a finite numeric signed_error_mev"
                )
        elif status != "failed":
            raise ValueError(
                f"row for path {index} model {model} must be measured or an explicit failure"
            )
        if (index, model) in pairs:
            raise ValueError(f"duplicate observation for path {index} model {model}")
        pairs.add((index, model))
        paths.add(index)
        models.add(model)
    return paths, models, pairs, rows


def _recompute_path_statistics(rows: list[dict]) -> tuple[int, float, float] | None:
    """Reduce measured rows to the path-level claim statistics."""
    per_path: dict[int, list[float]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("status") == "failed":
            continue
        value = row.get("signed_error_mev")
        index = row.get("path_index")
        if (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isinstance(index, int)
        ):
            per_path.setdefault(index, []).append(float(value))
    if not per_path:
        return None
    path_values = [statistics.median(values) for values in per_path.values()]
    fraction = sum(1 for value in path_values if value > 0) / len(path_values)
    return len(per_path), fraction, statistics.median(path_values)


def enforce_path_minimums(
    root: Path, manifest: dict[str, Any], bundle: dict[str, Any], artifact: Path, row_id: str
) -> str | None:
    """Fail closed when a panel-level receipt under-covers a declared path minimum.

    Panel-level predicates (the sign-skew family) define their acceptance over
    the whole recorded panel, so the cited artifact's own rows must document at
    least the manifest's neb-path-set minimum of DISTINCT paths, must cover
    every model the manifest declares available, and any self-reported n_paths
    aggregate must agree with the rows. Per-model barrier receipts instead
    disclose honest per-path failures, so they are not gated here. Returns the
    dataset fingerprint for persistence on the generated bundle, or None when
    the family gate does not apply.
    """
    predicate = bundle.get("claim_predicate")
    if not isinstance(predicate, str) or not predicate.startswith(
        "signed_error_positive_fraction"
    ):
        return None
    registry_path = root / "registry" / "campaigns.v1.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"measurement {row_id} cannot read the campaign registry: {error}"
        ) from error
    registered = {
        campaign.get("content_hash")
        for campaign in registry.get("campaigns", [])
        if isinstance(campaign, dict)
    }
    if manifest.get("content_hash") not in registered:
        raise ValueError(
            f"measurement {row_id} manifest is not registered in campaigns.v1.json; "
            "unreviewed caller manifests cannot prove independence"
        )
    minimums = [
        requirement["minimum_count"]
        for requirement in manifest.get("evidence_requirements", [])
        if isinstance(requirement, dict)
        and requirement.get("artifact_type") == "neb-path-set"
        and isinstance(requirement.get("minimum_count"), int)
    ]
    if not minimums:
        raise ValueError(
            f"measurement {row_id} manifest lacks the canonical neb-path-set "
            "requirement; the frozen sign-skew panel cannot be proven"
        )
    preregistration = manifest.get("preregistration")
    recorded_inputs = (
        preregistration.get("recorded_inputs")
        if isinstance(preregistration, dict)
        else None
    )
    if not (isinstance(recorded_inputs, list) and recorded_inputs):
        raise ValueError(
            f"measurement {row_id} requires a manifest with locked "
            "preregistration.recorded_inputs for the sign-skew family; an "
            "omitted lock is not proof of fresh compute"
        )
    if len(recorded_inputs) != 1:
        raise ValueError(
            f"measurement {row_id} requires exactly one locked recorded input; "
            f"the sign-skew family cannot reconcile {len(recorded_inputs)}"
        )
    declared_input = recorded_inputs[0]
    declared_pair = (
        declared_input.get("path") if isinstance(declared_input, dict) else None,
        declared_input.get("sha256") if isinstance(declared_input, dict) else None,
    )
    if declared_pair == (CANONICAL_RECORDED_SOURCE, CANONICAL_RECORDED_DIGEST):
        # Retrospective reuse of the canonical dataset is identity-locked: the
        # same locked rows may only support the canonical campaign.
        if manifest.get("campaign_id") != CANONICAL_CAMPAIGN_ID:
            raise ValueError(
                f"measurement {row_id} manifest campaign {manifest.get('campaign_id')!r} "
                f"is not the canonical {CANONICAL_CAMPAIGN_ID!r}; cloned campaigns do "
                "not count as independent replication"
            )
    else:
        if declared_pair[0] == CANONICAL_RECORDED_SOURCE or declared_pair[1] == CANONICAL_RECORDED_DIGEST:
            raise ValueError(
                f"measurement {row_id} recorded input partially matches the canonical "
                "locked source; declare it exactly or use a distinct dataset"
            )
        # A distinct locked dataset is an independent campaign: its digest is
        # verified and every row binds to it below.
    floor = max(minimums)
    if floor != FROZEN_PANEL_PATH_MINIMUM:
        raise ValueError(
            f"measurement {row_id} manifest declares a neb-path-set minimum of {floor}; "
            f"the frozen sign-skew claim requires exactly {FROZEN_PANEL_PATH_MINIMUM}"
        )
    try:
        document = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(
            f"measurement {row_id} cites an artifact that cannot prove path coverage: {error}"
        ) from error
    coverage = _coverage(document)
    if coverage is None:
        raise ValueError(
            f"measurement {row_id} cites an artifact with no per-path rows; "
            "self-reported aggregates cannot prove coverage"
        )
    paths, models, pairs, rows = coverage
    # Always true after the recorded-input checks above: bind every coverage row
    # to the declared locked source's identity, status, and values.
    if recorded_inputs:
        # Bind every coverage row to the locked source's path identity, recorded
        # status, and recorded value, so the receipt demonstrably measures the
        # frozen panel and nothing else. The source bytes must match the
        # preregistered digest before they are read.
        source_path = root / recorded_inputs[0]["path"]
        expected_digest = recorded_inputs[0].get("sha256")
        actual_digest = bytes_hash(source_path)
        if expected_digest != actual_digest:
            raise ValueError(
                f"measurement {row_id} locked recorded input digest mismatch: "
                f"expected {expected_digest}, found {actual_digest}"
            )
        try:
            source = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError) as error:
            raise ValueError(
                f"measurement {row_id} cannot read the locked recorded input: {error}"
            ) from error
        if declared_pair != (CANONICAL_RECORDED_SOURCE, CANONICAL_RECORDED_DIGEST):
            fingerprint = _source_fingerprint(source)
            if fingerprint == CANONICAL_SOURCE_FINGERPRINT:
                raise ValueError(
                    f"measurement {row_id} recorded input reserializes the canonical "
                    "dataset; independence requires distinct observations"
                )
            try:
                canonical_source = json.loads(
                    (root / DEDUPE_CANONICAL_SOURCE).read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"measurement {row_id} cannot read the canonical recorded source: {error}"
                ) from error
            canonical_measured = _measured_observations(canonical_source)
            candidate_measured = _measured_observations(source)
            if candidate_measured < canonical_measured or canonical_measured < candidate_measured:
                raise ValueError(
                    f"measurement {row_id} recorded input clones canonical observations; "
                    "independence requires new observations, not a subset or superset"
                )
        else:
            fingerprint = CANONICAL_SOURCE_FINGERPRINT
        examples_dir = root / "evidence" / "v1" / "examples"
        if examples_dir.is_dir():
            for prior_path in sorted(examples_dir.glob("*.json")):
                try:
                    prior = json.loads(prior_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                prior_predicate = prior.get("claim_predicate")
                if not isinstance(prior_predicate, str) or not prior_predicate.startswith(
                    "signed_error_positive_fraction"
                ):
                    continue
                for reference in prior.get("evidence_refs", []):
                    if (
                        isinstance(reference, dict)
                        and reference.get("campaign") != manifest.get("campaign_id")
                        and reference.get("dataset_fingerprint") == fingerprint
                    ):
                        raise ValueError(
                            f"measurement {row_id} dataset already supports campaign "
                            f"{reference.get('campaign')!r}; one dataset is not independent replication"
                        )
        locked = {}
        expected: dict[tuple[int, str], tuple[str, float | None]] = {}
        seen_identities: set[str] = set()
        for entry in source.get("per_path", []):
            if not isinstance(entry, dict):
                continue
            index = entry.get("path_index")
            identity = entry.get("path_id")
            if identity in seen_identities or index in locked:
                raise ValueError(
                    "locked source contains duplicate stable path identities"
                )
            seen_identities.add(identity)
            locked[index] = identity
            for model, record in (entry.get("per_model") or {}).items():
                value = record.get("vasp_signed_error_mev") if isinstance(record, dict) else None
                if value is not None and record.get("complete", False):
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                        raise ValueError(
                            f"locked source path {index} model {model} carries a non-finite signed error"
                        )
                    expected[(index, model)] = ("measured", float(value))
            for model in (entry.get("models_missing") or {}):
                expected[(index, model)] = ("failed", None)
        panel_lock = (
            manifest.get("execution", {}).get("candidate_panel")
            if isinstance(manifest.get("execution"), dict)
            else None
        )
        if not (isinstance(panel_lock, dict) and panel_lock.get("path")):
            raise ValueError(
                f"measurement {row_id} manifest lacks the execution.candidate_panel "
                "lock the nightly feedback loop requires"
            )
        if isinstance(panel_lock, dict) and panel_lock.get("path"):
            # Reconcile source identities with the sha-pinned candidate panel, so
            # a renamed clone cannot change its dataset fingerprint.
            panel_path = root / panel_lock["path"]
            if bytes_hash(panel_path) != panel_lock.get("sha256"):
                raise ValueError(
                    f"measurement {row_id} candidate panel digest mismatch with the manifest"
                )
            try:
                panel = json.loads(panel_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(
                    f"measurement {row_id} cannot read the locked candidate panel: {error}"
                ) from error
            panel_rows = panel.get("per_path") or panel.get("paths") or []
            panel_identities = {}
            for position, entry in enumerate(panel_rows):
                if not isinstance(entry, dict):
                    continue
                key = entry.get("path_index", position)
                panel_identities[key] = entry.get("path_id")
            inconsistent = {
                index: (identity, panel_identities.get(index))
                for index, identity in locked.items()
                if panel_identities.get(index) != identity
            }
            if inconsistent:
                index, (identity, expected_identity) = next(iter(inconsistent.items()))
                raise ValueError(
                    f"measurement {row_id} locked source path {index} identity {identity!r} "
                    f"does not match the frozen candidate panel {expected_identity!r}"
                )
        for row in rows:
            index = row["path_index"]
            if index not in locked:
                raise ValueError(
                    f"measurement {row_id} path {index} is outside the locked recorded panel"
                )
            if row.get("path_id") != locked[index]:
                raise ValueError(
                    f"measurement {row_id} path {index} identity {row.get('path_id')!r} "
                    f"does not match the locked panel {locked[index]!r}"
                )
            pair = (index, row["model"])
            wanted = expected.get(pair)
            if wanted is None:
                raise ValueError(
                    f"measurement {row_id} path {index} model {row['model']} has no "
                    "recorded counterpart in the locked source"
                )
            expected_status, source_value = wanted
            if row["status"] != expected_status:
                raise ValueError(
                    f"measurement {row_id} path {index} model {row['model']} status "
                    f"{row['status']!r} disagrees with the locked source {expected_status!r}"
                )
            if expected_status == "measured" and round(row["signed_error_mev"], 4) != round(source_value, 4):
                raise ValueError(
                    f"measurement {row_id} path {index} model {row['model']} value "
                    f"{row['signed_error_mev']} disagrees with the locked source {source_value}"
                )
        undisclosed = sorted(set(expected) - pairs)
        if undisclosed:
            path, model = undisclosed[0]
            raise ValueError(
                f"measurement {row_id} cherry-picks the locked source: path {path} "
                f"model {model} is recorded but not disclosed in the artifact"
            )
    declared = (
        document.get("n_paths_recorded", document.get("n_paths"))
        if isinstance(document, dict)
        else None
    )
    if isinstance(declared, int) and declared != len(paths):
        raise ValueError(
            f"measurement {row_id} artifact declares {declared} recorded paths but its "
            f"rows document {len(paths)} distinct paths"
        )
    if len(paths) < floor:
        raise ValueError(
            f"measurement {row_id} documents {len(paths)} distinct paths, below "
            f"the manifest's recorded-path minimum {floor}"
        )
    required_models = {
        model["model_id"]
        for model in manifest.get("available_models", [])
        if isinstance(model, dict) and isinstance(model.get("model_id"), str)
    }
    declared_entries = {
        (model.get("model_id"), model.get("artifact_hash"), model.get("version"))
        for model in manifest.get("available_models", [])
        if isinstance(model, dict)
    }
    if required_models != CANONICAL_MODEL_IDS or declared_entries != CANONICAL_MODEL_ENTRIES:
        raise ValueError(
            f"measurement {row_id} manifest must declare the full frozen four-model panel"
        )
    missing_models = sorted(required_models - models)
    if missing_models:
        raise ValueError(
            f"measurement {row_id} omits declared available models: {', '.join(missing_models)}"
        )
    if required_models:
        extra_models = sorted(models - required_models)
        if extra_models:
            raise ValueError(
                f"measurement {row_id} includes undeclared models outside "
                f"execution.model_selection: {', '.join(extra_models)}"
            )
    missing_pairs = sorted(
        (path, model) for path in paths for model in required_models if (path, model) not in pairs
    )
    if missing_pairs:
        path, model = missing_pairs[0]
        raise ValueError(
            f"measurement {row_id} omits an observation or disclosed failure for "
            f"path {path} model {model}"
        )
    recomputed = _recompute_path_statistics(rows)
    if recomputed is None:
        raise ValueError(
            f"measurement {row_id} artifact rows carry no measured signed errors to recompute"
        )
    measured_paths, recomputed_fraction, recomputed_median = recomputed
    if measured_paths < floor:
        raise ValueError(
            f"measurement {row_id} has {measured_paths} paths with measurements, below "
            f"the manifest's recorded-path minimum {floor}"
        )
    for measurement in bundle.get("measurements", []):
        if not isinstance(measurement, dict):
            continue
        metric = measurement.get("metric")
        value = measurement.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if not math.isfinite(value):
            raise ValueError(
                f"measurement {row_id} carries a non-finite typed value for {metric}"
            )
        if metric == "signed_error_positive" and abs(float(value) - recomputed_fraction) > 5e-5:
            raise ValueError(
                f"measurement {row_id} fraction {value} does not match the cited "
                f"artifact's recomputed value {recomputed_fraction:.4f}"
            )
        if metric == "median_signed_error" and abs(float(value) - recomputed_median) > 0.01:
            raise ValueError(
                f"measurement {row_id} median {value} does not match the cited "
                f"artifact's recomputed value {recomputed_median:.2f}"
            )
        acceptance = measurement.get("acceptance_test")
        if isinstance(acceptance, dict):
            comparator = acceptance.get("comparator")
            threshold = acceptance.get("threshold")
            asserted = acceptance.get("outcome")
            if (
                isinstance(threshold, (int, float))
                and not isinstance(threshold, bool)
                and asserted in {"pass", "fail"}
            ):
                # Auxiliary thresholds are pinned to the frozen acceptance suite,
                # so ingestion never materializes a bundle the nightly would reject.
                if metric == "signed_error_positive" and (
                    comparator != "greater_than" or float(threshold) != 0.5
                ):
                    raise ValueError(
                        f"measurement {row_id} fraction acceptance must be greater_than 0.5"
                    )
                if metric == "median_signed_error" and (comparator, float(threshold)) not in {
                    ("greater_than_or_equal", 400.0),
                    ("less_than_or_equal", 600.0),
                }:
                    raise ValueError(
                        f"measurement {row_id} median acceptance is outside the frozen 400/600 meV suite"
                    )
                if comparator == "greater_than":
                    expected_outcome = "pass" if value > threshold else "fail"
                elif comparator == "greater_than_or_equal":
                    expected_outcome = "pass" if value >= threshold else "fail"
                elif comparator == "less_than_or_equal":
                    expected_outcome = "pass" if value <= threshold else "fail"
                else:
                    expected_outcome = None
                if expected_outcome is not None and asserted != expected_outcome:
                    raise ValueError(
                        f"measurement {row_id} asserts outcome {asserted!r} but its "
                        f"value {value} {comparator} {threshold} measures {expected_outcome!r}"
                    )
        sample_count = measurement.get("sample_count")
        if isinstance(sample_count, int) and sample_count != measured_paths:
            raise ValueError(
                f"measurement {row_id} sample_count {sample_count} does not equal the "
                f"artifact's {measured_paths} measured paths"
            )
    return fingerprint


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
