#!/usr/bin/env python3
"""Validate the versioned Lupine ontology and its cross-links."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

READINESS_PATTERN = re.compile(r"^(?P<grade>[HML])(?: \((?P<annotation>[^()]+)\))?$")
EXPECTED_CLASS_CHAINS: dict[str, tuple[str, ...]] = {
    "MC1": ("C8",),
    "MC2": ("C9",),
    "MC3": ("C4",),
    "MC4": ("C1",),
    "MC5": ("C3",),
    "MC6": ("C2",),
    "MC7": ("C7",),
    "MC8": ("C5",),
    "MC9": ("C6", "C11"),
}
RELATION_NAMESPACE_ALIASES = {"any": "ontology", "CorrectionLever": "lever"}
ONTOLOGY_DATE = "2026-07-30"
LOCK_VERSION = 2
# Legacy artifact filenames are immutable source identities, not current API names.
ONTOLOGY_ARTIFACT = "registry/ontology/atlas.v2.json"
ONTOLOGY_LOCK_PATH = "snapshots/ontology.lock.json"
ONTOLOGY_VERSION_HASHES = {
    "atlas.v1.json": (
        "sha256:e75a6825f78ad4ae6c32631fa7fa8ab649a62334f8fe9b646ede936611f1c46b"
    ),
    "atlas.v2.json": None,
}
SOURCE_SHA256 = (
    "sha256:a3bbd74bbbac8fe506bfe70f60bdb8acd5f0eae99cad1f73db7cd1735475df5b"
)
TRANSFORMATION_CONTRACT = {
    "id": "add-namespaced-relation-labels-v1",
    "sourceSerialization": {
        "format": "json",
        "indent": 2,
        "ensureAscii": False,
        "trailingNewline": False,
    },
    "generatedFields": ["relations[].label", "relations[].inverseLabel"],
}


class OntologyError(ValueError):
    """Raised when the ontology cannot be validated safely."""


def parse_readiness(value: object) -> tuple[str, str | None]:
    """Parse a readiness grade with an optional parenthetical annotation."""
    if not isinstance(value, str):
        raise OntologyError(f"readiness must be a string, got {type(value).__name__}")
    match = READINESS_PATTERN.fullmatch(value)
    if match is None:
        raise OntologyError(f"invalid readiness grade {value!r}")
    annotation = match.group("annotation")
    if annotation is not None and (not annotation.strip() or annotation != annotation.strip()):
        raise OntologyError(f"invalid readiness annotation {annotation!r}")
    return match.group("grade"), annotation


def _records(ontology: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = ontology.get(key)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise OntologyError(f"{key} must be an array of objects")
    return value


def _ids(records: list[dict[str, Any]], section: str) -> set[str]:
    values = [row.get("id") for row in records]
    if any(not isinstance(value, str) or not value for value in values):
        raise OntologyError(f"{section} records must have non-empty string ids")
    if len(set(values)) != len(values):
        raise OntologyError(f"{section} contains duplicate ids")
    return {str(value) for value in values}


def _chain_values(value: object, material_id: str) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and value and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise OntologyError(f"materialClasses {material_id} has an invalid chain binding")


def _validate_readiness_values(value: object, path: str = "ontology") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "readiness":
                try:
                    parse_readiness(child)
                except OntologyError as error:
                    raise OntologyError(f"{child_path}: {error}") from error
            else:
                _validate_readiness_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_readiness_values(child, f"{path}[{index}]")


def _relation_namespace(domain: object) -> str:
    if not isinstance(domain, str) or not domain:
        raise OntologyError("relation domain must be a non-empty string")
    owner = domain.split("/", 1)[0]
    namespace = RELATION_NAMESPACE_ALIASES.get(owner, owner[:1].lower() + owner[1:])
    if re.fullmatch(r"[a-z][A-Za-z0-9]*", namespace) is None:
        raise OntologyError(f"relation domain {domain!r} cannot form a namespace")
    return namespace


def _validate_relations(ontology: dict[str, Any]) -> None:
    relations = _records(ontology, "relations")
    labels: set[str] = set()
    for index, relation in enumerate(relations):
        name = relation.get("name")
        if not isinstance(name, str) or not name:
            raise OntologyError(f"relations[{index}].name must be a non-empty string")
        namespace = _relation_namespace(relation.get("domain"))
        expected_label = f"{namespace}.{name}"
        if relation.get("label") != expected_label:
            raise OntologyError(
                f"relations[{index}] must use namespaced label {expected_label!r}"
            )
        if expected_label in labels:
            raise OntologyError(f"duplicate namespaced relation label {expected_label!r}")
        labels.add(expected_label)
        inverse = relation.get("inverse")
        if inverse is not None:
            expected_inverse = f"{namespace}.{inverse}"
            if relation.get("inverseLabel") != expected_inverse:
                raise OntologyError(
                    f"relations[{index}] must use namespaced inverse label "
                    f"{expected_inverse!r}"
                )


def _source_projection_bytes(ontology: dict[str, Any]) -> bytes:
    """Reverse the declared additive transformation to reproduce source bytes."""
    source_projection = json.loads(json.dumps(ontology, ensure_ascii=False))
    relations = source_projection.get("relations")
    if not isinstance(relations, list):
        raise OntologyError("relations must be an array for source projection")
    for index, relation in enumerate(relations):
        if not isinstance(relation, dict):
            raise OntologyError(f"relations[{index}] must be an object")
        relation.pop("label", None)
        relation.pop("inverseLabel", None)
    return json.dumps(source_projection, indent=2, ensure_ascii=False).encode()


def validate_lock(ontology_bytes: bytes, ontology: object, lock: object) -> None:
    """Validate the immutable ontology hash and its source/freshness provenance."""
    if not isinstance(ontology, dict) or not isinstance(lock, dict):
        raise OntologyError("ontology and ontology lock must be JSON objects")
    expected_hash = "sha256:" + hashlib.sha256(ontology_bytes).hexdigest()
    if lock.get("sha256") != expected_hash:
        raise OntologyError(f"sha256 mismatch: expected {expected_hash}")
    if lock.get("version") != LOCK_VERSION:
        raise OntologyError(f"version must be {LOCK_VERSION}")
    if lock.get("artifact") != ONTOLOGY_ARTIFACT:
        raise OntologyError(f"artifact must be {ONTOLOGY_ARTIFACT}")
    if lock.get("transformation") != TRANSFORMATION_CONTRACT:
        raise OntologyError(
            "transformation must declare the additive relation-label contract"
        )
    source = lock.get("source")
    if not isinstance(source, dict) or source.get("sha256") != SOURCE_SHA256:
        raise OntologyError(
            f"source.sha256 must match PROVENANCE.sha256 ({SOURCE_SHA256})"
        )
    projected_source_hash = "sha256:" + hashlib.sha256(
        _source_projection_bytes(ontology)
    ).hexdigest()
    if projected_source_hash != source.get("sha256"):
        raise OntologyError(
            "source.sha256 does not match the ontology after reversing the declared "
            f"transformation (got {projected_source_hash})"
        )
    if source.get("path") != "lupine-ledger/content/ontology/lupine-ontology.json":
        raise OntologyError("source.path does not identify lupine-ontology.json")
    if source.get("provenance") != "lupine-ledger/content/ontology/PROVENANCE.sha256":
        raise OntologyError("source.provenance does not identify PROVENANCE.sha256")
    metadata = ontology.get("metadata")
    compiled = metadata.get("compiled") if isinstance(metadata, dict) else None
    freshness = ontology.get("freshnessLayer")
    # Frozen source/lock documents retain the legacy atlasDate field verbatim.
    if lock.get("atlasDate") != ONTOLOGY_DATE or compiled != ONTOLOGY_DATE:
        raise OntologyError(f"ontology date and metadata.compiled must equal {ONTOLOGY_DATE}")
    if not isinstance(freshness, dict) or freshness.get("atlasDate") != ONTOLOGY_DATE:
        raise OntologyError(f"freshnessLayer date must equal {ONTOLOGY_DATE}")
    if lock.get("freshnessLayer") != freshness:
        raise OntologyError("freshnessLayer does not match the versioned ontology")


def validate_ontology(ontology: object) -> None:
    """Validate ontology identifiers and all cross-section links."""
    if not isinstance(ontology, dict):
        raise OntologyError("ontology must be a JSON object")
    readiness_ids = _ids(_records(ontology, "readinessGrades"), "readinessGrades")
    if readiness_ids != {"H", "M", "L"}:
        raise OntologyError("readinessGrades must define exactly H, M, and L")
    _validate_readiness_values(ontology)
    _validate_relations(ontology)
    chains = _records(ontology, "discoveryChains")
    chain_ids = _ids(chains, "discoveryChains")
    expected_chain_ids = {f"C{index}" for index in range(1, 12)}
    if chain_ids != expected_chain_ids:
        raise OntologyError("discoveryChains ids do not preserve A1 parity (C1–C11)")
    for chain in chains:
        if "readiness" not in chain:
            raise OntologyError(f"discoveryChains {chain['id']} must declare readiness")
    materials = _records(ontology, "materialClasses")
    material_ids = _ids(materials, "materialClasses")
    if material_ids != set(EXPECTED_CLASS_CHAINS):
        raise OntologyError("materialClasses ids do not preserve A1 parity (MC1–MC9)")
    for material in materials:
        material_id = material["id"]
        bound_chains = _chain_values(material.get("chain"), material_id)
        missing = sorted(set(bound_chains) - chain_ids)
        if missing:
            raise OntologyError(
                f"materialClasses {material_id} references missing chain {', '.join(missing)}"
            )
        if bound_chains != EXPECTED_CLASS_CHAINS[material_id]:
            raise OntologyError(
                f"materialClasses {material_id} violates the A1 mapping: "
                f"expected {EXPECTED_CLASS_CHAINS[material_id]}, got {bound_chains}"
            )

    acceptance_tests = _records(ontology, "acceptanceTests")
    acceptance_ids = _ids(acceptance_tests, "acceptanceTests")
    expected_acceptance_ids = {f"Z{index}" for index in range(1, 12)}
    if acceptance_ids != expected_acceptance_ids:
        raise OntologyError("acceptanceTests ids must preserve Z1–Z11 parity")
    acceptance_chains = [row.get("chain") for row in acceptance_tests]
    if (
        any(not isinstance(chain, str) for chain in acceptance_chains)
        or len(set(acceptance_chains)) != len(acceptance_chains)
        or set(acceptance_chains) != chain_ids
    ):
        raise OntologyError(
            "acceptanceTests.chain must be a one-to-one mapping with discoveryChains"
        )
    for acceptance in acceptance_tests:
        expected_chain = f"C{acceptance['id'][1:]}"
        if acceptance["chain"] != expected_chain:
            raise OntologyError(
                f"acceptanceTests {acceptance['id']} must bind to {expected_chain}"
            )


def _load_json(path: Path) -> tuple[bytes, object]:
    try:
        content = path.read_bytes()
        return content, json.loads(content)
    except (OSError, json.JSONDecodeError) as error:
        raise OntologyError(f"cannot read {path}: {error}") from error


def validate_versioned_ontology_inventory(registry_path: Path) -> None:
    """Fail closed on unknown versions and mutations of historical ontologies."""
    ontology_paths = sorted(registry_path.glob("atlas.v*.json"))
    actual_names = {path.name for path in ontology_paths}
    expected_names = set(ONTOLOGY_VERSION_HASHES)
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unsupported = sorted(actual_names - expected_names)
        details = []
        if missing:
            details.append(f"missing versioned ontology: {', '.join(missing)}")
        if unsupported:
            details.append(f"unsupported ontology version: {', '.join(unsupported)}")
        raise OntologyError("; ".join(details))

    for ontology_path in ontology_paths:
        expected_hash = ONTOLOGY_VERSION_HASHES[ontology_path.name]
        if expected_hash is None:
            continue
        actual_hash = (
            "sha256:" + hashlib.sha256(ontology_path.read_bytes()).hexdigest()
        )
        if actual_hash != expected_hash:
            raise OntologyError(
                f"historical ontology {ontology_path.name} is not immutable: "
                f"expected {expected_hash}, got {actual_hash}"
            )


def check_files(ontology_path: Path, lock_path: Path) -> None:
    ontology_bytes, ontology = _load_json(ontology_path)
    _, lock = _load_json(lock_path)
    validate_ontology(ontology)
    validate_lock(ontology_bytes, ontology, lock)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--ontology", type=Path, dest="ontology")
    # Read-only CLI compatibility for retained automation invocations.
    source.add_argument("--atlas", type=Path, dest="ontology", help=argparse.SUPPRESS)
    parser.set_defaults(ontology=Path(ONTOLOGY_ARTIFACT))
    parser.add_argument(
        "--lock", type=Path, default=Path(ONTOLOGY_LOCK_PATH)
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.ontology == Path(ONTOLOGY_ARTIFACT) and args.lock == Path(ONTOLOGY_LOCK_PATH):
            validate_versioned_ontology_inventory(args.ontology.parent)
        check_files(args.ontology, args.lock)
    except OntologyError as error:
        print(f"ontology link check failed: {error}", file=sys.stderr)
        return 1
    print("ontology link check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
