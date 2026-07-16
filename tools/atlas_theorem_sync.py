"""Validated ATLAS theorem manifest construction and D1 synchronization.

The synchronizer consumes build evidence. It never treats a source filename or
the presence of a theorem declaration as proof that Lean accepted the theorem.
It can apply parameterized statements to a DB-API SQLite connection or render a
reviewable, safely escaped D1 SQL script; it never opens a remote database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FACETS = {"causal", "experiment", "manifold", "theorist"}
STATUSES = {"imported", "verified", "extended", "failed"}
VERIFIED_STATUSES = {"verified", "extended"}

PROOF_REPOSITORY = "lupine-science/open-distillation-factory"
# Fallback formal authority, used only when neither the reviewed registry pin
# (config/atlas_theorem_registry.v1.json authority.proof_revision), nor the
# ATLAS_PROOF_REVISION environment variable, nor an explicit --proof-revision
# override supplies one. The registry pin is the single source of truth:
# re-pinning after a rebase or squash-merge is a one-file, reviewable change.
FORMAL_PROOF_REVISION = "8c0ccf7b31ad54d6beb3363698750d9a081cb796"
LEAN_VERSION = "4.29.0"
MATHLIB_REVISION = "8a178386ffc0f5fef0b77738bb5449d50efeea95"
ATLAS_REVISION = "c5a10f1a95de31e5476484c8bb3856ee7f164ea0"
VISION_LEGACY_COUNT = 284
VISION_UNIVERSAL_CORRECTION_COUNT = 164
VISION_EPISTEMIC_GAP_COUNT = 5

BUILD_EVIDENCE_SCHEMA = "lupine.lean-build-evidence.v1"
REGISTRY_SCHEMA = "lupine.atlas-theorem-registry.v1"
SYNC_SCHEMA = "lupine.atlas-theorem-sync.v1"
STATE_SCHEMA_VERSION = 2
INVENTORY_SCHEMA_VERSION = 2

_REPO = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = _REPO / "config" / "atlas_theorem_registry.v1.json"
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _require_git_commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _GIT_COMMIT.fullmatch(value):
        raise ManifestError(f"{label} must be a 40-character lowercase git commit")
    return value


def resolve_proof_revision(
    override: str | None = None,
    registry_pin: str | None = None,
) -> str:
    """Resolve the formal authority revision by precedence.

    1. explicit override (``--proof-revision`` / keyword argument)
    2. ``ATLAS_PROOF_REVISION`` environment variable
    3. the reviewed registry pin (``authority.proof_revision``)
    4. the module fallback constant

    Every candidate is validated as a git commit; an invalid override or
    environment value is an error, never silently skipped.
    """
    if override is not None:
        return _require_git_commit(override, "proof revision override")
    env_value = os.environ.get("ATLAS_PROOF_REVISION")
    if env_value:
        return _require_git_commit(env_value, "ATLAS_PROOF_REVISION")
    if registry_pin is not None:
        return _require_git_commit(registry_pin, "registry proof_revision")
    return FORMAL_PROOF_REVISION


class ManifestError(ValueError):
    """The registry, build evidence, or requested synchronization is invalid."""


@dataclass(frozen=True)
class TheoremSelection:
    facet: str
    theorem_name: str
    module: str
    status: str = "verified"
    used_in_hypotheses: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> TheoremSelection:
        facet = str(value.get("facet", ""))
        status = str(value.get("status", "verified"))
        theorem_name = str(value.get("theorem_name", "")).strip()
        module = str(value.get("module", "")).strip()
        used = value.get("used_in_hypotheses", 0)
        if facet not in FACETS:
            raise ManifestError(f"invalid facet {facet!r}; expected canonical lowercase facet")
        if status not in STATUSES:
            raise ManifestError(f"invalid status {status!r}; expected one of {sorted(STATUSES)}")
        if not theorem_name or "." not in theorem_name or any(c.isspace() for c in theorem_name):
            raise ManifestError(f"theorem_name must be fully qualified: {theorem_name!r}")
        if not module or any(c.isspace() for c in module):
            raise ManifestError(f"module must be a non-empty Lean module: {module!r}")
        if not isinstance(used, int) or isinstance(used, bool) or used < 0:
            raise ManifestError("used_in_hypotheses must be a non-negative integer")
        return cls(facet, theorem_name, module, status, used)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def canonical_manifest_hash(manifest: Mapping[str, Any]) -> str:
    """Hash a manifest without its self-referential top-level manifest_hash."""

    payload = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HEX_64.fullmatch(value):
        raise ManifestError(f"{label} must be a lowercase SHA-256 hash")
    return value


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestError(f"{label} must be an object")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ManifestError(f"{label} must be an array")
    return value


def _authority_values(proof_revision: str) -> dict[str, Any]:
    return {
        "proof_repository": PROOF_REPOSITORY,
        "proof_revision": proof_revision,
        "lean_version": LEAN_VERSION,
        "mathlib_revision": MATHLIB_REVISION,
        "atlas_revision": ATLAS_REVISION,
        "vision_legacy_count": VISION_LEGACY_COUNT,
        "vision_universal_correction_count": VISION_UNIVERSAL_CORRECTION_COUNT,
        "vision_epistemic_gap_count": VISION_EPISTEMIC_GAP_COUNT,
    }


def load_registry(
    path: Path = DEFAULT_REGISTRY_PATH,
    *,
    expected_proof_revision: str | None = None,
) -> dict[str, Any]:
    """Load and validate the reviewed operational theorem-to-facet registry.

    The registry's ``authority.proof_revision`` is the single source of truth
    for the formal commit. When ``expected_proof_revision`` is supplied (CLI
    override or ``ATLAS_PROOF_REVISION``), the registry pin must match it —
    re-pinning is a deliberate, reviewable edit of the registry file.
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != REGISTRY_SCHEMA:
        raise ManifestError(f"registry schema must be {REGISTRY_SCHEMA}")
    if payload.get("schema_version") != 1:
        raise ManifestError("unsupported registry schema_version")
    authority = _require_mapping(payload.get("authority"), "registry authority")
    registry_pin = _require_git_commit(authority.get("proof_revision"), "registry proof_revision")
    if expected_proof_revision is not None and registry_pin != expected_proof_revision:
        raise ManifestError(
            "registry authority proof_revision does not match the requested formal "
            "authority; re-pin authority.proof_revision in the registry"
        )
    for key, expected in _authority_values(registry_pin).items():
        if authority.get(key) != expected:
            raise ManifestError(f"registry authority {key} does not match formal authority")

    managed_facets = _require_sequence(payload.get("managed_facets"), "managed_facets")
    if any(facet not in FACETS for facet in managed_facets) or len(set(managed_facets)) != len(
        managed_facets
    ):
        raise ManifestError("managed_facets contains an invalid or duplicate facet")

    selections = [
        TheoremSelection.from_mapping(item)
        for item in _require_sequence(payload.get("theorems"), "theorems")
        if isinstance(item, Mapping)
    ]
    if len(selections) != len(payload["theorems"]):
        raise ManifestError("every registry theorem must be an object")
    identities = [(item.facet, item.theorem_name, item.module) for item in selections]
    if len(identities) != len(set(identities)):
        raise ManifestError("registry contains a duplicate theorem identity")

    policy = _require_mapping(payload.get("extension_policy"), "extension_policy")
    policy_facets = _require_sequence(policy.get("facets"), "extension_policy.facets")
    prefixes = _require_sequence(policy.get("module_prefixes"), "extension_policy.module_prefixes")
    if any(facet not in FACETS for facet in policy_facets):
        raise ManifestError("extension_policy contains an invalid facet")
    if not prefixes or any(not isinstance(prefix, str) or not prefix for prefix in prefixes):
        raise ManifestError("extension_policy module prefixes must be non-empty strings")
    return payload


def _gate_passed(gates: Mapping[str, Any], name: str) -> bool:
    gate = _require_mapping(gates.get(name), f"gates.{name}")
    return gate.get("passed") is True


def _validate_build_evidence(evidence: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    if evidence.get("schema") != BUILD_EVIDENCE_SCHEMA or evidence.get("schema_version") != 1:
        raise ManifestError(f"build evidence must use {BUILD_EVIDENCE_SCHEMA}")
    supplied_hash = _require_hash(evidence.get("manifest_hash"), "manifest_hash")
    if supplied_hash != canonical_manifest_hash(evidence):
        raise ManifestError("build evidence manifest_hash does not match its canonical content")

    for key, expected in {
        "proof_repository": PROOF_REPOSITORY,
        "lean_version": LEAN_VERSION,
        "mathlib_revision": MATHLIB_REVISION,
        "atlas_revision": ATLAS_REVISION,
    }.items():
        if evidence.get(key) != expected:
            raise ManifestError(f"build evidence {key} does not match formal authority")

    gates = _require_mapping(evidence.get("gates"), "gates")
    lake = _require_mapping(gates.get("lake_build"), "gates.lake_build")
    zero_sorry = _require_mapping(gates.get("zero_sorry"), "gates.zero_sorry")
    vision = _require_mapping(gates.get("vision"), "gates.vision")
    if (
        not isinstance(lake.get("passed"), bool)
        or not isinstance(zero_sorry.get("passed"), bool)
        or not isinstance(vision.get("passed"), bool)
    ):
        raise ManifestError("build gate passed values must be booleans")
    if not isinstance(lake.get("command"), str) or not lake["command"].strip():
        raise ManifestError("lake build gate must record its command")
    if not isinstance(lake.get("exit_code"), int) or isinstance(lake.get("exit_code"), bool):
        raise ManifestError("lake build gate must record an integer exit_code")
    if lake["passed"] != (lake["exit_code"] == 0):
        raise ManifestError("lake build gate passed and exit_code disagree")
    sorry_count = zero_sorry.get("sorry_count")
    if not isinstance(sorry_count, int) or isinstance(sorry_count, bool) or sorry_count < 0:
        raise ManifestError("zero-sorry gate must record a non-negative sorry_count")
    if zero_sorry["passed"] != (sorry_count == 0):
        raise ManifestError("zero-sorry gate passed and sorry_count disagree")
    if vision.get("legacy_theorems") != VISION_LEGACY_COUNT:
        raise ManifestError("Vision legacy theorem count does not match authority")
    if vision.get("universal_correction_theorems") != VISION_UNIVERSAL_CORRECTION_COUNT:
        raise ManifestError("Vision Universal Correction count does not match authority")
    if vision.get("epistemic_gaps") != VISION_EPISTEMIC_GAP_COUNT:
        raise ManifestError("Vision epistemic gap count does not match authority")

    inventory: dict[tuple[str, str], dict[str, str]] = {}
    seen_modules: set[str] = set()
    for raw_module in _require_sequence(evidence.get("modules"), "modules"):
        module_entry = _require_mapping(raw_module, "module inventory entry")
        module = module_entry.get("module")
        if not isinstance(module, str) or not module or module in seen_modules:
            raise ManifestError("source/build inventory has an invalid or duplicate module")
        seen_modules.add(module)
        source_path = module_entry.get("source_path")
        if not isinstance(source_path, str) or not source_path:
            raise ManifestError(f"source/build inventory for {module} is missing source_path")
        source_hash = _require_hash(module_entry.get("source_hash"), f"{module} source_hash")
        built = module_entry.get("built")
        if not isinstance(built, bool):
            raise ManifestError(f"source/build inventory for {module} must record built")
        for raw_theorem in _require_sequence(module_entry.get("theorems"), f"{module}.theorems"):
            theorem = _require_mapping(raw_theorem, f"{module} theorem")
            name = theorem.get("name")
            namespace = theorem.get("namespace")
            if not isinstance(name, str) or not name or not isinstance(namespace, str):
                raise ManifestError(f"source/build inventory for {module} has an invalid theorem")
            if not name.startswith(namespace + "."):
                raise ManifestError(f"namespace mismatch for theorem {name!r} in module {module}")
            key = (module, name)
            if key in inventory:
                raise ManifestError(f"source/build inventory duplicates theorem {name}")
            inventory[key] = {
                "namespace": namespace,
                "statement_hash": _require_hash(
                    theorem.get("statement_hash"), f"{name} statement_hash"
                ),
                "source_hash": source_hash,
                "source_path": source_path,
                "built": "true" if built else "false",
            }
    return inventory


def _validate_extension(
    selection: TheoremSelection, extension_policy: Mapping[str, Any] | None
) -> None:
    if extension_policy is None:
        raise ManifestError("extensions require an explicit extension_policy")
    facets = extension_policy.get("facets")
    prefixes = extension_policy.get("module_prefixes")
    if not isinstance(facets, list) or selection.facet not in facets:
        raise ManifestError(f"extension facet {selection.facet!r} is not allowed")
    if not isinstance(prefixes, list) or not any(
        isinstance(prefix, str) and selection.module.startswith(prefix) for prefix in prefixes
    ):
        raise ManifestError(f"extension module {selection.module!r} is not allowed")


def _all_build_gates_pass(evidence: Mapping[str, Any]) -> bool:
    gates = _require_mapping(evidence.get("gates"), "gates")
    return all(_gate_passed(gates, name) for name in ("lake_build", "zero_sorry", "vision"))


def build_sync_manifest(
    evidence: Mapping[str, Any],
    selections: Iterable[Mapping[str, Any] | TheoremSelection],
    *,
    extensions: Iterable[Mapping[str, Any] | TheoremSelection] = (),
    extension_policy: Mapping[str, Any] | None = None,
    managed_facets: Iterable[str] | None = None,
    expected_proof_revision: str | None = None,
) -> dict[str, Any]:
    """Validate build evidence and materialize rows for synchronization."""

    authority_revision = resolve_proof_revision(expected_proof_revision)
    selected = [
        item if isinstance(item, TheoremSelection) else TheoremSelection.from_mapping(item)
        for item in selections
    ]
    extension_items = [
        item if isinstance(item, TheoremSelection) else TheoremSelection.from_mapping(item)
        for item in extensions
    ]
    for extension in extension_items:
        _validate_extension(extension, extension_policy)
    selected.extend(extension_items)

    inventory = _validate_build_evidence(evidence)
    verified_requested = any(item.status in VERIFIED_STATUSES for item in selected)
    proof_revision = evidence.get("proof_revision")
    if verified_requested and (
        not isinstance(proof_revision, str)
        or not _GIT_COMMIT.fullmatch(proof_revision)
        or proof_revision != authority_revision
        or not _all_build_gates_pass(evidence)
    ):
        raise ManifestError(
            "verified output requires the immutable formal commit and all passing build gates"
        )
    if proof_revision != authority_revision:
        raise ManifestError("build evidence proof_revision does not match formal authority")

    facets = (
        list(managed_facets) if managed_facets is not None else sorted({x.facet for x in selected})
    )
    if len(facets) != len(set(facets)) or any(facet not in FACETS for facet in facets):
        raise ManifestError("managed facets must be unique canonical lowercase facets")
    if any(item.facet not in facets for item in selected):
        raise ManifestError("every selected theorem facet must be managed by this synchronization")

    identities: set[tuple[str, str, str]] = set()
    rows: list[dict[str, Any]] = []
    for item in selected:
        identity = (item.facet, item.theorem_name, item.module)
        if identity in identities:
            raise ManifestError(f"duplicate selected theorem {item.theorem_name}")
        identities.add(identity)
        source = inventory.get((item.module, item.theorem_name))
        if source is None:
            raise ManifestError(
                f"theorem {item.theorem_name!r} and module {item.module!r} "
                "do not match the source/build inventory"
            )
        if item.status in VERIFIED_STATUSES and source["built"] != "true":
            raise ManifestError(
                f"verified output requires built module inventory for {item.theorem_name}"
            )
        rows.append(
            {
                "facet": item.facet,
                "theorem_name": item.theorem_name,
                "module": item.module,
                "revision": proof_revision,
                "proof_repository": evidence["proof_repository"],
                "proof_revision": proof_revision,
                "atlas_revision": evidence["atlas_revision"],
                "mathlib_revision": evidence["mathlib_revision"],
                "statement_hash": source["statement_hash"],
                "source_hash": source["source_hash"],
                "build_manifest_hash": evidence["manifest_hash"],
                "status": item.status,
                "lifecycle_status": "active",
                "used_in_hypotheses": item.used_in_hypotheses,
            }
        )

    rows.sort(key=lambda row: (row["facet"], row["module"], row["theorem_name"]))
    return {
        "schema": SYNC_SCHEMA,
        "schema_version": 1,
        "state_schema_version": STATE_SCHEMA_VERSION,
        "inventory_schema_version": INVENTORY_SCHEMA_VERSION,
        "build_gates_passed": _all_build_gates_pass(evidence),
        "proof_repository": evidence["proof_repository"],
        "proof_revision": proof_revision,
        "atlas_revision": evidence["atlas_revision"],
        "mathlib_revision": evidence["mathlib_revision"],
        "lean_version": evidence["lean_version"],
        "build_manifest_hash": evidence["manifest_hash"],
        "managed_facets": sorted(facets),
        "theorems": rows,
    }


def _validate_sync_manifest(
    manifest: Mapping[str, Any],
    *,
    expected_proof_revision: str | None = None,
) -> None:
    authority_revision = resolve_proof_revision(expected_proof_revision)
    if manifest.get("schema") != SYNC_SCHEMA or manifest.get("schema_version") != 1:
        raise ManifestError(f"sync manifest must use {SYNC_SCHEMA}")
    if (
        manifest.get("state_schema_version") != STATE_SCHEMA_VERSION
        or manifest.get("inventory_schema_version") != INVENTORY_SCHEMA_VERSION
    ):
        raise ManifestError("sync manifest metadata versions are unsupported")
    if not isinstance(manifest.get("build_gates_passed"), bool):
        raise ManifestError("sync manifest must record whether build gates passed")
    _require_hash(manifest.get("build_manifest_hash"), "build_manifest_hash")
    if (
        manifest.get("proof_repository") != PROOF_REPOSITORY
        or manifest.get("proof_revision") != authority_revision
    ):
        raise ManifestError("sync manifest proof authority is invalid")
    for row in _require_sequence(manifest.get("theorems"), "theorems"):
        selection = TheoremSelection.from_mapping(_require_mapping(row, "theorem row"))
        if selection.status in VERIFIED_STATUSES and not manifest["build_gates_passed"]:
            raise ManifestError("verified output requires passing build gates")
        authority = {
            "revision": manifest["proof_revision"],
            "proof_repository": manifest["proof_repository"],
            "proof_revision": manifest["proof_revision"],
            "atlas_revision": manifest["atlas_revision"],
            "mathlib_revision": manifest["mathlib_revision"],
            "build_manifest_hash": manifest["build_manifest_hash"],
        }
        for key, expected in authority.items():
            if row.get(key) != expected:
                raise ManifestError(f"theorem row {key} does not match sync manifest authority")
        if row.get("lifecycle_status") != "active":
            raise ManifestError("synchronized theorem rows must be active")
        for key in ("statement_hash", "source_hash", "build_manifest_hash"):
            _require_hash(row.get(key), f"{selection.theorem_name} {key}")


def _facet_inventory(manifest: Mapping[str, Any], facet: str) -> dict[str, Any]:
    rows = [row for row in manifest["theorems"] if row["facet"] == facet]
    counts = Counter(row["status"] for row in rows)
    return {
        "schema": "lupine.atlas-facet-inventory.v2",
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "producer": SYNC_SCHEMA,
        "facet": facet,
        "total": len(rows),
        "by_status": {status: counts.get(status, 0) for status in sorted(STATUSES)},
        "proof_repository": manifest["proof_repository"],
        "proof_revision": manifest["proof_revision"],
        "build_manifest_hash": manifest["build_manifest_hash"],
        "theorems": [
            {
                "theorem": row["theorem_name"],
                "module": row["module"],
                "revision": row["revision"],
                "status": row["status"],
            }
            for row in rows
        ],
    }


def _previous_inventory(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, str):
        return []
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or payload.get("producer") != SYNC_SCHEMA:
        return []
    theorems = payload.get("theorems")
    if not isinstance(theorems, list):
        return []
    return [item for item in theorems if isinstance(item, dict)]


_THEOREM_UPSERT = """
INSERT INTO atlas_theorems (
  facet, theorem_name, module, revision, proof_repository, proof_revision,
  atlas_revision, mathlib_revision, statement_hash, source_hash,
  build_manifest_hash, status, lifecycle_status, superseded_by_id,
  used_in_hypotheses
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL, ?)
ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE SET
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  statement_hash = excluded.statement_hash,
  source_hash = excluded.source_hash,
  build_manifest_hash = excluded.build_manifest_hash,
  status = excluded.status,
  lifecycle_status = 'active',
  superseded_by_id = NULL,
  used_in_hypotheses = excluded.used_in_hypotheses,
  updated_at = CURRENT_TIMESTAMP
"""

_FACET_STATE_UPSERT = """
INSERT INTO atlas_facet_state (
  facet, proof_repository, proof_revision, atlas_revision, mathlib_revision,
  theorem_inventory, build_manifest_hash, state_schema_version,
  inventory_schema_version, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
ON CONFLICT(facet) DO UPDATE SET
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  theorem_inventory = excluded.theorem_inventory,
  build_manifest_hash = excluded.build_manifest_hash,
  state_schema_version = excluded.state_schema_version,
  inventory_schema_version = excluded.inventory_schema_version,
  updated_at = CURRENT_TIMESTAMP
"""


def _row_parameters(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row["facet"],
        row["theorem_name"],
        row["module"],
        row["revision"],
        row["proof_repository"],
        row["proof_revision"],
        row["atlas_revision"],
        row["mathlib_revision"],
        row["statement_hash"],
        row["source_hash"],
        row["build_manifest_hash"],
        row["status"],
        row["used_in_hypotheses"],
    )


def synchronize_connection(
    connection: sqlite3.Connection,
    manifest: Mapping[str, Any],
    *,
    expected_proof_revision: str | None = None,
) -> None:
    """Apply one manifest with parameters; removed prior shared rows are retired."""

    _validate_sync_manifest(manifest, expected_proof_revision=expected_proof_revision)
    with connection:
        for facet in manifest["managed_facets"]:
            current = {
                (row["theorem_name"], row["module"], row["revision"])
                for row in manifest["theorems"]
                if row["facet"] == facet
            }
            state = connection.execute(
                "SELECT theorem_inventory FROM atlas_facet_state WHERE facet = ?", (facet,)
            ).fetchone()
            prior = _previous_inventory(state[0] if state else None)
            for item in prior:
                identity = (item.get("theorem"), item.get("module"), item.get("revision"))
                if identity not in current and all(isinstance(part, str) for part in identity):
                    connection.execute(
                        "UPDATE atlas_theorems SET lifecycle_status = 'retired', "
                        "superseded_by_id = NULL, updated_at = CURRENT_TIMESTAMP "
                        "WHERE facet = ? AND theorem_name = ? AND module = ? AND revision = ? "
                        "AND lifecycle_status = 'active'",
                        (facet, *identity),
                    )

        for row in manifest["theorems"]:
            connection.execute(_THEOREM_UPSERT, _row_parameters(row))

        for facet in manifest["managed_facets"]:
            inventory = _canonical_json(_facet_inventory(manifest, facet))
            connection.execute(
                _FACET_STATE_UPSERT,
                (
                    facet,
                    manifest["proof_repository"],
                    manifest["proof_revision"],
                    manifest["atlas_revision"],
                    manifest["mathlib_revision"],
                    inventory,
                    manifest["build_manifest_hash"],
                    STATE_SCHEMA_VERSION,
                    INVENTORY_SCHEMA_VERSION,
                ),
            )


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _render_retirement(manifest: Mapping[str, Any], facet: str) -> str:
    current = [row for row in manifest["theorems"] if row["facet"] == facet]
    keep = " OR\n    ".join(
        "(theorem_name = {name} AND module = {module} AND revision = {revision})".format(
            name=_sql_literal(row["theorem_name"]),
            module=_sql_literal(row["module"]),
            revision=_sql_literal(row["revision"]),
        )
        for row in current
    )
    keep_clause = f"\n  AND NOT (\n    {keep}\n  )" if keep else ""
    facet_sql = _sql_literal(facet)
    producer_sql = _sql_literal(SYNC_SCHEMA)
    return f"""UPDATE atlas_theorems
SET lifecycle_status = 'retired', superseded_by_id = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE facet = {facet_sql}
  AND lifecycle_status = 'active'
  AND EXISTS (
    SELECT 1
    FROM atlas_facet_state AS prior_state,
         json_each(prior_state.theorem_inventory, '$.theorems') AS prior
    WHERE prior_state.facet = {facet_sql}
      AND json_extract(prior_state.theorem_inventory, '$.producer') = {producer_sql}
      AND json_extract(prior.value, '$.theorem') = atlas_theorems.theorem_name
      AND json_extract(prior.value, '$.module') = atlas_theorems.module
      AND json_extract(prior.value, '$.revision') = atlas_theorems.revision
  ){keep_clause};"""


def _render_theorem_upsert(row: Mapping[str, Any]) -> str:
    values = [
        row["facet"],
        row["theorem_name"],
        row["module"],
        row["revision"],
        row["proof_repository"],
        row["proof_revision"],
        row["atlas_revision"],
        row["mathlib_revision"],
        row["statement_hash"],
        row["source_hash"],
        row["build_manifest_hash"],
        row["status"],
        row["used_in_hypotheses"],
    ]
    return f"""INSERT INTO atlas_theorems (
  facet, theorem_name, module, revision, proof_repository, proof_revision,
  atlas_revision, mathlib_revision, statement_hash, source_hash,
  build_manifest_hash, status, lifecycle_status, superseded_by_id,
  used_in_hypotheses
) VALUES (
  {", ".join(_sql_literal(value) for value in values[:-1])}, 'active', NULL,
  {_sql_literal(values[-1])}
)
ON CONFLICT(facet, theorem_name, module, revision) DO UPDATE SET
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  statement_hash = excluded.statement_hash,
  source_hash = excluded.source_hash,
  build_manifest_hash = excluded.build_manifest_hash,
  status = excluded.status,
  lifecycle_status = 'active',
  superseded_by_id = NULL,
  used_in_hypotheses = excluded.used_in_hypotheses,
  updated_at = CURRENT_TIMESTAMP;"""


def build_ad_hoc_rows(
    theorems: Iterable[Mapping[str, Any]],
    *,
    module_sources: Mapping[str, str],
    module_results: Mapping[str, bool],
) -> list[dict[str, Any]]:
    """Build inspectable, never-verified rows for an uncommitted generator run.

    A local one-file Lean invocation is useful feedback but is not the immutable
    successful build manifest required for ``verified``. Passing modules are
    therefore ``imported``; the generic extension path promotes them only after
    a successful authoritative build manifest names the same theorem/module.
    """

    rows: list[dict[str, Any]] = []
    for raw in theorems:
        requested = dict(raw)
        module = str(requested.get("module", ""))
        compiled = module_results.get(module) is True
        requested["status"] = "imported" if compiled else "failed"
        selection = TheoremSelection.from_mapping(requested)
        source = module_sources.get(module)
        statement = raw.get("statement")
        if not isinstance(source, str):
            raise ManifestError(f"ad hoc theorem module {module!r} is missing generated source")
        if not isinstance(statement, str) or not statement.strip():
            raise ManifestError(f"ad hoc theorem {selection.theorem_name!r} is missing statement")
        rows.append(
            {
                "facet": selection.facet,
                "theorem_name": selection.theorem_name,
                "module": selection.module,
                "revision": "uncommitted-generated-evidence",
                "proof_repository": PROOF_REPOSITORY,
                "proof_revision": None,
                "atlas_revision": ATLAS_REVISION,
                "mathlib_revision": MATHLIB_REVISION,
                "statement_hash": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                "source_hash": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "build_manifest_hash": None,
                "status": selection.status,
                "lifecycle_status": "active",
                "used_in_hypotheses": selection.used_in_hypotheses,
            }
        )
    return sorted(rows, key=lambda row: (row["facet"], row["module"], row["theorem_name"]))


def render_ad_hoc_sql(rows: Iterable[Mapping[str, Any]]) -> str:
    """Render safely escaped upserts for non-verified generator observations."""

    rendered = [
        "-- Generated theorem observations; not verified without an immutable build manifest.",
    ]
    for row in rows:
        selection = TheoremSelection.from_mapping(row)
        if selection.status in VERIFIED_STATUSES:
            raise ManifestError("ad hoc SQL cannot emit verified or extended theorem status")
        _require_hash(row.get("statement_hash"), f"{selection.theorem_name} statement_hash")
        _require_hash(row.get("source_hash"), f"{selection.theorem_name} source_hash")
        if row.get("build_manifest_hash") is not None or row.get("proof_revision") is not None:
            raise ManifestError("ad hoc rows cannot claim build or immutable proof evidence")
        rendered.append(_render_theorem_upsert(row))
    return "\n\n".join(rendered) + "\n"


def write_extension_manifest(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write theorem references for later promotion through build_sync_manifest."""

    theorems = []
    for row in rows:
        selection = TheoremSelection.from_mapping(row)
        theorem = {
            "facet": selection.facet,
            "theorem_name": selection.theorem_name,
            "module": selection.module,
            "used_in_hypotheses": selection.used_in_hypotheses,
        }
        if selection.status == "failed":
            theorem["status"] = "failed"
        theorems.append(theorem)
    payload = {
        "schema": "lupine.atlas-theorem-extension.v1",
        "schema_version": 1,
        "theorems": theorems,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _render_facet_state(manifest: Mapping[str, Any], facet: str) -> str:
    inventory = _canonical_json(_facet_inventory(manifest, facet))
    values = [
        facet,
        manifest["proof_repository"],
        manifest["proof_revision"],
        manifest["atlas_revision"],
        manifest["mathlib_revision"],
        inventory,
        manifest["build_manifest_hash"],
        STATE_SCHEMA_VERSION,
        INVENTORY_SCHEMA_VERSION,
    ]
    return f"""INSERT INTO atlas_facet_state (
  facet, proof_repository, proof_revision, atlas_revision, mathlib_revision,
  theorem_inventory, build_manifest_hash, state_schema_version,
  inventory_schema_version, updated_at
) VALUES ({", ".join(_sql_literal(value) for value in values)}, CURRENT_TIMESTAMP)
ON CONFLICT(facet) DO UPDATE SET
  proof_repository = excluded.proof_repository,
  proof_revision = excluded.proof_revision,
  atlas_revision = excluded.atlas_revision,
  mathlib_revision = excluded.mathlib_revision,
  theorem_inventory = excluded.theorem_inventory,
  build_manifest_hash = excluded.build_manifest_hash,
  state_schema_version = excluded.state_schema_version,
  inventory_schema_version = excluded.inventory_schema_version,
  updated_at = CURRENT_TIMESTAMP;"""


def render_sync_sql(
    manifest: Mapping[str, Any],
    *,
    expected_proof_revision: str | None = None,
) -> str:
    """Render a reviewable D1 script with escaped literals and atomic upserts."""

    _validate_sync_manifest(manifest, expected_proof_revision=expected_proof_revision)
    statements = [
        "-- Generated by tools/atlas_theorem_sync.py; review before local ingestion.",
        "-- This script does not connect to D1.",
        "BEGIN TRANSACTION;",
    ]
    statements.extend(_render_retirement(manifest, facet) for facet in manifest["managed_facets"])
    statements.extend(_render_theorem_upsert(row) for row in manifest["theorems"])
    statements.extend(_render_facet_state(manifest, facet) for facet in manifest["managed_facets"])
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def write_sync_outputs(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    sql_path: Path,
    *,
    expected_proof_revision: str | None = None,
) -> None:
    """Write the reviewed JSON synchronization manifest and escaped SQL artifact."""

    _validate_sync_manifest(manifest, expected_proof_revision=expected_proof_revision)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    sql_path.write_text(
        render_sync_sql(manifest, expected_proof_revision=expected_proof_revision),
        encoding="utf-8",
    )


def _load_extension_paths(paths: Sequence[Path]) -> list[Mapping[str, Any]]:
    extensions: list[Mapping[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and (
            payload.get("schema") != "lupine.atlas-theorem-extension.v1"
            or payload.get("schema_version") != 1
        ):
            raise ManifestError(f"extension manifest {path} has an unsupported schema")
        raw = payload.get("theorems") if isinstance(payload, dict) else payload
        for item in _require_sequence(raw, f"extensions in {path}"):
            extensions.append(_require_mapping(item, f"extension in {path}"))
    return extensions


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--extension-manifest", type=Path, action="append", default=[])
    parser.add_argument("--out-manifest", type=Path, required=True)
    parser.add_argument("--out-sql", type=Path, required=True)
    parser.add_argument(
        "--proof-revision",
        default=None,
        help=(
            "formal authority commit; defaults to ATLAS_PROOF_REVISION, then the "
            "reviewed registry pin. A value that differs from the registry pin is "
            "rejected — re-pin the registry file deliberately."
        ),
    )
    args = parser.parse_args(argv)

    requested_revision = None
    if args.proof_revision is not None or os.environ.get("ATLAS_PROOF_REVISION"):
        requested_revision = resolve_proof_revision(args.proof_revision)
    registry = load_registry(args.registry, expected_proof_revision=requested_revision)
    authority_revision = (
        requested_revision
        if requested_revision is not None
        else resolve_proof_revision(registry_pin=registry["authority"]["proof_revision"])
    )
    evidence = json.loads(args.build_manifest.read_text(encoding="utf-8"))
    manifest = build_sync_manifest(
        evidence,
        registry["theorems"],
        extensions=_load_extension_paths(args.extension_manifest),
        extension_policy=registry["extension_policy"],
        managed_facets=registry["managed_facets"],
        expected_proof_revision=authority_revision,
    )
    write_sync_outputs(
        manifest, args.out_manifest, args.out_sql, expected_proof_revision=authority_revision
    )
    print(
        f"validated {len(manifest['theorems'])} theorem(s); "
        f"manifest -> {args.out_manifest}; SQL -> {args.out_sql}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
