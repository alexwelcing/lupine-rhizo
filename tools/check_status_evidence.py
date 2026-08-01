#!/usr/bin/env python3
"""Reject status changes that are not backed by a new EvidenceBundle hash."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
STATUS_FIELDS = ("status", "epistemic_status", "assurance")
ONTOLOGY_STATUS_FIELDS = (*STATUS_FIELDS, "readiness")
IDENTITY_FIELDS = (
    "claim_version_id",
    "claim_id",
    "entity_id",
    "subject_id",
    "assumption_id",
    "id",
)
BUNDLE_HASH_FIELDS = {
    "bundle_id",
    "bundle_hash",
    "evidence_bundle_hash",
    "evidence_bundle_id",
}


class CheckError(ValueError):
    """Raised when an input cannot be checked safely."""


def _identity(record: dict[str, Any], source: str) -> str:
    for field in IDENTITY_FIELDS:
        value = record.get(field)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    raise CheckError(f"{source}: record has no stable identity field")


def _status_values(record: dict[str, Any]) -> dict[str, Any]:
    values = {field: record[field] for field in STATUS_FIELDS if field in record}
    if "to_status" in record:
        values["status"] = record["to_status"]
    classification = record.get("classification")
    if isinstance(classification, dict) and "assurance" in classification:
        values["assurance"] = classification["assurance"]
    evidence = record.get("evidence", [])
    if isinstance(evidence, list):
        for index, receipt in enumerate(evidence):
            if not isinstance(receipt, dict):
                continue
            receipt_id = receipt.get("bundle_id", index)
            for field in ("epistemic_status", "assurance"):
                if field in receipt:
                    values[f"evidence[{receipt_id}].{field}"] = receipt[field]
    return values


def _bundle_hashes(value: Any, parent_key: str | None = None) -> set[str]:
    hashes: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            hashes.update(_bundle_hashes(child, key))
    elif isinstance(value, list):
        for child in value:
            hashes.update(_bundle_hashes(child, parent_key))
    elif (
        parent_key in BUNDLE_HASH_FIELDS
        and isinstance(value, str)
        and HASH_PATTERN.fullmatch(value)
    ):
        hashes.add(value)
    return hashes


def _ontology_path_component(value: Any, index: int) -> str:
    if isinstance(value, dict):
        for field in IDENTITY_FIELDS:
            identity = value.get(field)
            if isinstance(identity, (str, int)) and str(identity):
                return f"[{field}={identity}]"
    return f"[{index}]"


def _ontology_states(
    document: Any, source: str
) -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    if not isinstance(document, (dict, list)):
        raise CheckError(f"{source}: ontology atlas must be a JSON object or array")
    statuses: dict[str, dict[str, Any]] = {}
    owners: dict[str, set[str]] = {}

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path in owners:
                raise CheckError(f"{source}: duplicate ontology identity at {path}")
            owners[path] = _bundle_hashes(value)
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in ONTOLOGY_STATUS_FIELDS:
                    statuses[child_path] = {
                        "value": child,
                        "owner": path,
                    }
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}{_ontology_path_component(child, index)}")

    walk(document, "$atlas")
    return statuses, owners


def find_unbacked_ontology_status_changes(
    before: Any, after: Any, *, source: str
) -> list[str]:
    """Return every ontology status change that lacks a new local bundle hash."""
    before_statuses, before_owners = _ontology_states(before, source)
    after_statuses, after_owners = _ontology_states(after, source)
    globally_new_hashes = _bundle_hashes(after) - _bundle_hashes(before)
    violations = []
    for path in sorted(before_statuses.keys() | after_statuses.keys()):
        old = before_statuses.get(path)
        new = after_statuses.get(path)
        if old is not None and new is not None and old["value"] == new["value"]:
            continue
        if new is not None:
            owner = new["owner"]
        elif old is not None:
            owner = old["owner"]
        else:  # Defensive: the path came from the union above.
            continue
        locally_new_hashes = after_owners.get(owner, set()) - before_owners.get(
            owner, set()
        )
        if not locally_new_hashes & globally_new_hashes:
            violations.append(
                f"{source}: {path} changed with no new EvidenceBundle hash "
                "(the authorizing hash must be globally new)"
            )
    return violations


def _records(document: Any, source: str) -> tuple[list[dict[str, Any]], bool]:
    if isinstance(document, list):
        records = document
        is_event_log = "status_event" in source.lower()
    elif isinstance(document, dict):
        if "assumptions" in document:
            records = document["assumptions"]
            is_event_log = False
        elif "status_events" in document:
            records = document["status_events"]
            is_event_log = True
        else:
            raise CheckError(
                f"{source}: expected assumptions or status_events JSON collection"
            )
    else:
        raise CheckError(f"{source}: expected a JSON object or array")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise CheckError(f"{source}: records must be JSON objects")
    return records, is_event_log


def _states(document: Any, source: str) -> dict[str, dict[str, Any]]:
    records, is_event_log = _records(document, source)
    states: dict[str, dict[str, Any]] = {}
    for record in records:
        identity = _identity(record, source)
        statuses = _status_values(record)
        hashes = _bundle_hashes(record)
        if is_event_log:
            state = states.setdefault(identity, {"statuses": {}, "hashes": set()})
            state["statuses"].update(statuses)
            state["hashes"].update(hashes)
        else:
            if identity in states:
                raise CheckError(f"{source}: duplicate record identity {identity}")
            states[identity] = {"statuses": statuses, "hashes": hashes}
    return states


def find_unbacked_status_changes(
    before: Any, after: Any, *, source: str
) -> list[str]:
    """Return violations for existing records whose status changed without new evidence."""
    before_states = _states(before, source)
    after_states = _states(after, source)
    violations = []
    for identity in sorted(before_states.keys() & after_states.keys()):
        old = before_states[identity]
        new = after_states[identity]
        changed_fields = sorted(
            field
            for field in set(old["statuses"]) | set(new["statuses"])
            if old["statuses"].get(field) != new["statuses"].get(field)
        )
        if changed_fields and not new["hashes"] - old["hashes"]:
            violations.append(
                f"{source}: {identity} changed {', '.join(changed_fields)} "
                "with no new EvidenceBundle hash"
            )
    return violations


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CheckError(f"cannot read {path}: {error}") from error


def _load_git(root: Path, revision: str, path: str, *, required: bool) -> Any | None:
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if not required:
            return None
        detail = result.stderr.strip() or "path not found"
        raise CheckError(f"cannot read {path} at {revision}: {detail}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise CheckError(f"invalid JSON in {path} at {revision}: {error}") from error


def _git_pairs(root: Path, base_ref: str, head_ref: str) -> list[str]:
    registry_path = "registry/assumptions.v1.json"
    before_registry = _load_git(root, base_ref, registry_path, required=False)
    after_registry = _load_git(root, head_ref, registry_path, required=False)
    if before_registry is not None and after_registry is None:
        raise CheckError(
            f"{registry_path} was deleted in this change; removing the tracked "
            "registry is not allowed without new evidence"
        )
    violations = []
    if before_registry is not None and after_registry is not None:
        violations.extend(
            find_unbacked_status_changes(
                before_registry, after_registry, source=registry_path
            )
        )

    events_path = "snapshots/status-events.v1.json"
    before_events = _load_git(root, base_ref, events_path, required=False)
    after_events = _load_git(root, head_ref, events_path, required=False)
    if before_events is not None and after_events is None:
        raise CheckError(
            f"{events_path} was deleted in this change; removing the tracked "
            "status-event snapshot is not allowed without new evidence"
        )
    if before_events is not None and after_events is not None:
        violations.extend(
            find_unbacked_status_changes(
                before_events, after_events, source="D1 status_event"
            )
        )

    ontology_path = "registry/ontology/atlas.v1.json"
    before_ontology = _load_git(root, base_ref, ontology_path, required=False)
    after_ontology = _load_git(root, head_ref, ontology_path, required=False)
    if before_ontology is not None and after_ontology is None:
        raise CheckError(
            f"{ontology_path} was deleted in this change; removing the tracked "
            "ontology is not allowed without new evidence"
        )
    if before_ontology is not None and after_ontology is not None:
        violations.extend(
            find_unbacked_ontology_status_changes(
                before_ontology,
                after_ontology,
                source=ontology_path,
            )
        )
    return violations


def _pair(
    before_path: Path | None,
    after_path: Path | None,
    label: str,
) -> Iterable[str]:
    if before_path is None and after_path is None:
        return []
    if before_path is None or after_path is None:
        raise CheckError(f"{label}: both before and after files are required")
    return find_unbacked_status_changes(
        _load(before_path), _load(after_path), source=label
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-registry", type=Path)
    parser.add_argument("--after-registry", type=Path)
    parser.add_argument("--before-status-events", type=Path)
    parser.add_argument("--after-status-events", type=Path)
    parser.add_argument("--git-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref")
    parser.add_argument("--head-ref")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    has_file_pair = any(
        (
            args.before_registry,
            args.after_registry,
            args.before_status_events,
            args.after_status_events,
        )
    )
    has_git_pair = bool(args.base_ref or args.head_ref)
    if has_file_pair and has_git_pair:
        print(
            "anti-laundering check error: choose file pairs or git revisions, not both",
            file=sys.stderr,
        )
        return 2
    if not has_file_pair and not has_git_pair:
        print("anti-laundering check error: no input pairs supplied", file=sys.stderr)
        return 2
    try:
        if has_git_pair:
            if not args.base_ref or not args.head_ref:
                raise CheckError("both --base-ref and --head-ref are required")
            violations = _git_pairs(args.git_root, args.base_ref, args.head_ref)
        else:
            violations = [
                *_pair(
                    args.before_registry,
                    args.after_registry,
                    "registry/assumptions.v1.json",
                ),
                *_pair(
                    args.before_status_events,
                    args.after_status_events,
                    "D1 status_event",
                ),
            ]
    except CheckError as error:
        print(f"anti-laundering check error: {error}", file=sys.stderr)
        return 2
    if violations:
        print("anti-laundering check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("anti-laundering check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
