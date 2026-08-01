#!/usr/bin/env python3
"""Convert LiteratureHypothesis v1 documents into frozen CampaignManifest v1 skeletons.

The v0 converter intentionally supports only the already-preregistered Z1 barrier
contract. It performs no inference: ontology bindings, acceptance criteria, models,
and the nearest panel all come from checked-in allowlisted artifacts.

T1 (protocol-offset) hypotheses analyze recorded union-campaign artifacts instead of
requesting fresh compute; for them the converter swaps in the sign-skew acceptance
test, the matching demotion condition, recorded-panel evidence requirements, and a
declared preregistration.recorded_inputs lock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import rfc8785
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = Path("campaigns/v1/z1.campaign-manifest.v1.json")
LITERATURE_SCHEMA_PATH = ROOT / "schemas" / "literature-hypothesis.v1.schema.json"
CAMPAIGN_SCHEMA_PATH = ROOT / "schemas" / "campaign-manifest.v1.schema.json"
ALLOWED_CHAIN = "C1"
ALLOWED_MATERIAL_CLASS = "MC4"
ALLOWED_ERROR_TYPES = ["T1", "T2", "T3"]  # T1 (reference-method bias) is the barrier contract's native type
ALLOWED_ACCEPTANCE_TEST = "Z1"
ALLOWED_METRIC = "barrier_mae"
ALLOWED_PREDICATE = "barrier_mae_mev<=40"
ALLOWED_PANEL = "data/candidates/z1_nebdft2k_barriers.lock.json"
ALLOWED_STATUSES = {"proposed", "accepted"}
TARGET_PREMISES_BY_CHAIN = {
    "C1": [
        {
            "claim_id": "discovery.z1.barrier-accuracy.v1",
            "premise_id": "chemistry-held-out-neb",
        }
    ]
}
ACCEPTANCE_TEST_BY_ID = {
    "Z1": {
        "metric": "barrier_mae",
        "operator": "lte",
        "threshold": 40,
        "unit": "meV",
    }
}
# T1 (protocol-offset) hypotheses claim a systematic signed offset of the sparse-anchor
# protocol against the reference, not a per-model accuracy level. Their machine-readable
# acceptance test is therefore the sign-skew majority they predict, evaluated on the
# recorded union-campaign panel; they require no fresh held-out compute.
T1_ACCEPTANCE_TEST = {
    "metric": "signed_error_positive_fraction",
    "operator": "gte",
    "threshold": 0.5,
    "unit": "fraction",
}
T1_DEMOTION_CONDITIONS = [
    {
        "action": "demote",
        "condition_id": "demote.z1.protocol-offset-sign-skew",
        "metric": "signed_error_positive_fraction",
        "operator": "lt",
        "threshold": 0.5,
        "unit": "fraction",
    }
]
T1_RECORDED_SOURCE = "data/candidates/z1-union-campaign.json"
# Executed union-campaign rows carrying a usable per-path signed error (of the 23 locked).
T1_RECORDED_PATHS_MINIMUM = 22
T1_EVIDENCE_REQUIREMENTS = [
    {
        "requirement_id": "e.z1.recorded-path-set",
        "artifact_type": "neb-path-set",
        "description": "Recorded per-path sparse-anchor and reference barrier measurements from the locked Z1 union campaign artifact; the analysis reuses recorded rows and requires no fresh held-out compute.",
        "minimum_count": T1_RECORDED_PATHS_MINIMUM,
    },
    {
        "requirement_id": "e.z1.model-results",
        "artifact_type": "model-measurements",
        "description": "Per-path predictions from every available model, including signed errors and failures without imputation.",
        "minimum_count": 1,
    },
]
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ConversionError(ValueError):
    """Raised when an input cannot be mapped without judgment or new vocabulary."""


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConversionError(f"{field} must be an object")
    return value


def _require_exact_list(value: object, expected: str, field: str) -> None:
    if value != [expected]:
        raise ConversionError(f"{field} must be the existing {expected} allowlist")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"cannot load {label} {path}: {error}") from error
    return _require_mapping(value, label)


def _validate_schema(document: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = _load_json(schema_path, f"{label} schema")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "document"
        raise ConversionError(f"{label} schema rejected {location}: {error.message}")


def _repo_artifact_lock(relative_path: str, root: Path) -> dict[str, str]:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ConversionError(f"recorded input must be repo-relative: {relative_path}")
    root_path = root.resolve()
    artifact_path = root_path.joinpath(*relative.parts)
    try:
        resolved = artifact_path.resolve(strict=True)
        resolved.relative_to(root_path)
        artifact_bytes = resolved.read_bytes()
    except ValueError as error:
        raise ConversionError(
            f"recorded input escapes the repository root: {relative_path}"
        ) from error
    except OSError as error:
        raise ConversionError(
            f"recorded input cannot be read: {relative_path}: {error}"
        ) from error
    return {
        "path": relative_path,
        "sha256": "sha256:" + hashlib.sha256(artifact_bytes).hexdigest(),
    }


def _panel_lock(proposed: dict[str, Any], root: Path) -> dict[str, str]:
    panel_ref = proposed.get("panel_ref", ALLOWED_PANEL)
    if panel_ref != ALLOWED_PANEL:
        raise ConversionError(
            f"panel_ref must be the referenced/nearest locked Z1 panel {ALLOWED_PANEL!r}"
        )
    relative = PurePosixPath(panel_ref)
    if relative.is_absolute() or ".." in relative.parts:
        raise ConversionError("panel_ref must be a repo-relative locked artifact")
    root_path = root.resolve()
    panel_path = root_path.joinpath(*relative.parts)
    try:
        resolved_panel = panel_path.resolve(strict=True)
        resolved_panel.relative_to(root_path)
        panel_bytes = resolved_panel.read_bytes()
    except ValueError as error:
        raise ConversionError(f"panel_ref escapes the repository root: {panel_ref}") from error
    except OSError as error:
        raise ConversionError(f"panel_ref cannot be read: {panel_ref}: {error}") from error
    return {
        "path": panel_ref,
        "sha256": "sha256:" + hashlib.sha256(panel_bytes).hexdigest(),
    }


def _content_hash(manifest: dict[str, Any]) -> str:
    canonical = rfc8785.dumps(manifest)
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _registration_timestamp(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as error:
        raise ConversionError("registered_at must be an explicit UTC RFC 3339 timestamp") from error
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hypothesis_lock(
    hypothesis: dict[str, Any], *, hypothesis_id: str, hypothesis_ref: str, root: Path
) -> dict[str, str]:
    expected = f"examples/literature-hypotheses/{hypothesis_id}.json"
    relative = PurePosixPath(hypothesis_ref)
    if relative.is_absolute() or ".." in relative.parts or hypothesis_ref != expected:
        raise ConversionError(f"hypothesis_ref must be the reviewed A3 artifact {expected!r}")
    root_path = root.resolve()
    document_path = root_path.joinpath(*relative.parts)
    try:
        resolved_document = document_path.resolve(strict=True)
        resolved_document.relative_to(root_path)
        document_bytes = resolved_document.read_bytes()
        reviewed = json.loads(document_bytes)
    except ValueError as error:
        raise ConversionError(f"hypothesis_ref escapes the repository root: {hypothesis_ref}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"hypothesis_ref cannot be read: {hypothesis_ref}: {error}") from error
    if rfc8785.dumps(reviewed) != rfc8785.dumps(hypothesis):
        raise ConversionError("hypothesis does not match the reviewed A3 input artifact")
    return {
        "path": hypothesis_ref,
        "sha256": "sha256:" + hashlib.sha256(document_bytes).hexdigest(),
    }


def convert_hypothesis(
    hypothesis: dict[str, Any],
    *,
    hypothesis_id: str,
    hypothesis_ref: str,
    registered_at: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Map one allowlisted hypothesis to a deterministic frozen manifest skeleton."""
    if not isinstance(hypothesis, dict):
        raise ConversionError("hypothesis must be an object")
    _validate_schema(hypothesis, LITERATURE_SCHEMA_PATH, "LiteratureHypothesis")
    if not IDENTIFIER_PATTERN.fullmatch(hypothesis_id):
        raise ConversionError("hypothesis_id must be a lowercase campaign identifier")
    if len(f"prereg.literature.{hypothesis_id}.v1") > 160:
        raise ConversionError("hypothesis_id is too long for the CampaignManifest schema")
    if hypothesis.get("status") not in ALLOWED_STATUSES:
        raise ConversionError("status must be proposed or accepted before conversion")

    source = _require_mapping(hypothesis.get("source"), "source")
    source_url = source.get("url")
    as_of = source.get("asOf")
    claim_text = hypothesis.get("claim_text")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ConversionError("source.url must be an https URL")
    if not isinstance(as_of, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of) is None:
        raise ConversionError("source.asOf must be an ISO date")
    if not isinstance(claim_text, str) or not claim_text.strip():
        raise ConversionError("claim_text must be a non-empty string")

    bindings = _require_mapping(hypothesis.get("bindings"), "bindings")
    declared_types = bindings.get("errorTypes")
    if not isinstance(declared_types, list) or not declared_types or any(
        t not in ALLOWED_ERROR_TYPES for t in declared_types
    ):
        raise ConversionError(
            f"bindings.errorTypes must be a non-empty subset of the existing {ALLOWED_ERROR_TYPES!r} allowlist"
        )
    _require_exact_list(bindings.get("chains"), ALLOWED_CHAIN, "bindings.chains")
    _require_exact_list(
        bindings.get("materialClasses"),
        ALLOWED_MATERIAL_CLASS,
        "bindings.materialClasses",
    )
    _require_exact_list(
        bindings.get("acceptanceTests"),
        ALLOWED_ACCEPTANCE_TEST,
        "bindings.acceptanceTests",
    )

    proposed = _require_mapping(hypothesis.get("proposedExperiment"), "proposedExperiment")
    if proposed.get("metric") != ALLOWED_METRIC:
        raise ConversionError(f"metric must be the existing {ALLOWED_METRIC!r} allowlist")
    if proposed.get("predicate") != ALLOWED_PREDICATE:
        raise ConversionError(
            f"predicate must be the existing typed-measurement {ALLOWED_PREDICATE!r}"
        )
    panel_lock = _panel_lock(proposed, root)
    input_lock = _hypothesis_lock(
        hypothesis,
        hypothesis_id=hypothesis_id,
        hypothesis_ref=hypothesis_ref,
        root=root,
    )

    template = _load_json(root / TEMPLATE_PATH, "Z1 campaign template")
    manifest = deepcopy(template)
    manifest.pop("content_hash", None)
    manifest["campaign_id"] = f"literature.{hypothesis_id}.v1"
    manifest["preregistration_id"] = f"prereg.literature.{hypothesis_id}.v1"
    manifest["preregistration"] = {
        "registered_at": _registration_timestamp(registered_at),
        "source": source_url,
        "source_as_of": as_of,
        "input_document": input_lock,
        "frozen_before_execution": True,
    }
    manifest["frozen_hypotheses"] = [
        {
            "hypothesis_id": f"lit-hypothesis.{hypothesis_id}.v1",
            "statement": claim_text,
            "frozen": True,
        }
    ]
    manifest["target_premises"] = deepcopy(TARGET_PREMISES_BY_CHAIN[ALLOWED_CHAIN])
    manifest["acceptance_test"] = deepcopy(ACCEPTANCE_TEST_BY_ID[ALLOWED_ACCEPTANCE_TEST])
    if "T1" in declared_types:
        manifest["acceptance_test"] = deepcopy(T1_ACCEPTANCE_TEST)
        manifest["demotion_conditions"] = deepcopy(T1_DEMOTION_CONDITIONS)
        manifest["evidence_requirements"] = deepcopy(T1_EVIDENCE_REQUIREMENTS)
        manifest["preregistration"]["recorded_inputs"] = [
            _repo_artifact_lock(T1_RECORDED_SOURCE, root)
        ]
    manifest["execution"] = deepcopy(template["execution"])
    manifest["execution"]["candidate_panel"] = panel_lock
    manifest["content_hash"] = _content_hash(manifest)
    _validate_schema(manifest, CAMPAIGN_SCHEMA_PATH, "CampaignManifest")
    return manifest


def canonical_document(manifest: dict[str, Any]) -> bytes:
    """Serialize fixtures deterministically for review and source control."""
    return (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="LiteratureHypothesis v1 JSON")
    parser.add_argument(
        "--registered-at",
        required=True,
        help="actual preregistration event time as UTC RFC 3339 (YYYY-MM-DDTHH:MM:SSZ)",
    )
    parser.add_argument("--output", type=Path, help="output path (defaults to stdout)")
    parser.add_argument(
        "--hypothesis-id",
        help="identifier stem (defaults to the input filename stem)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        hypothesis = _load_json(args.input, "LiteratureHypothesis")
        manifest = convert_hypothesis(
            hypothesis,
            hypothesis_id=args.hypothesis_id or args.input.stem,
            hypothesis_ref=args.input.resolve().relative_to(ROOT.resolve()).as_posix(),
            registered_at=args.registered_at,
            root=ROOT,
        )
        document = canonical_document(manifest)
        if args.output is None:
            sys.stdout.buffer.write(document)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(document)
    except (ConversionError, ValueError) as error:
        print(f"lit_to_manifest: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
