#!/usr/bin/env python3
"""Fail-closed pre-execution gate for the protocol-offset replication campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import rfc8785
from ase.io import read
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PANEL_PATHS = 30
MINIMUM_MEASURED_PATHS = 22
EXPECTED_CAMPAIGN_ID = "literature.protocol-offset-sign-skew.replication.v1"
EXPECTED_PANEL_PATH = "data/candidates/z1-sign-skew-replication-panel.lock.json"
EXPECTED_MANIFEST_PATH = (
    "campaigns/v1/literature-protocol-offset-sign-skew-replication.campaign-manifest.v1.json"
)
BASELINE_PANEL_PATH = "data/candidates/z1_nebdft2k_barriers.lock.json"
BASELINE_CAMPAIGN_PATH = "data/candidates/z1-union-campaign.json"
CAMPAIGN_REGISTRY_PATH = "registry/campaigns.v1.json"
CANDIDATE_PANEL_SCHEMA_PATH = "schemas/sign-skew-replication-panel.v1.schema.json"
SOURCE_ARCHIVE_PATH = "data/reference/litraj/nebDFT2k.zip"
EXPECTED_PANEL_SCHEMA = "lupine.z1.sign_skew_replication_panel.v1"
EXPECTED_PANEL_ID = "z1-sign-skew-replication-v1"
EXPECTED_INPUT_DOCUMENT_PATH = (
    "docs/plans/2026-08-03-protocol-offset-sign-skew-replication-preregistration.md"
)
EXPECTED_INPUT_STATUS = "**Status:** REVIEWED / READY TO REGISTER"
EXPECTED_PREREGISTRATION_ID = "prereg.literature.protocol-offset-sign-skew.replication.v1"
EXPECTED_TARGET_PREMISES = (
    {
        "claim_id": "discovery.z1.barrier-accuracy.v1",
        "premise_id": "chemistry-held-out-neb",
    },
)
EXPECTED_SELECTION_RULE = (
    "One deterministic official-test path from each of the first 30 lexically "
    "ordered chemical systems remaining after excluding every path ID, chemical "
    "system, and exact reference barrier in the frozen Z1 panel."
)
EXPECTED_REFERENCE_PROVENANCE = {
    "dataset": "LiTraj nebDFT2k",
    "doi": "10.1038/s41524-025-01571-z",
    "source_archive_sha256": "b7a99d89337902e9e1da319f57547170fdb132bf15bf6ffef03a0140e2207d7f",
    "source_repository": "https://github.com/AIRI-Institute/LiTraj",
    "source_revision": "c3ca5c2afbc13ffc823306f546dcee24486ade2a",
}
EXPECTED_ACCEPTANCE_TEST = {
    "metric": "signed_error_positive",
    "operator": "gt",
    "threshold": 0.5,
    "unit": "fraction",
}
EXPECTED_HYPOTHESES = (
    {
        "hypothesis_id": "lit-hypothesis.protocol-offset-sign-skew.replication.h1.v1",
        "statement": "After taking the median available signed error across the four locked models for each measured path, more than half of measured path medians are positive.",
        "frozen": True,
    },
    {
        "hypothesis_id": "lit-hypothesis.protocol-offset-sign-skew.replication.h2.v1",
        "statement": "After taking the median available signed error across the four locked models for each measured path, the median across measured paths is between +400 meV and +600 meV inclusive.",
        "frozen": True,
    },
)
EXPECTED_DEMOTIONS = (
    {
        "condition_id": "demote.replication.sign-fraction",
        "metric": "signed_error_positive",
        "operator": "lte",
        "threshold": 0.5,
        "unit": "fraction",
        "action": "demote",
    },
    {
        "condition_id": "demote.replication.median-low",
        "metric": "median_signed_error_mev",
        "operator": "lt",
        "threshold": 400,
        "unit": "meV",
        "action": "demote",
    },
    {
        "condition_id": "demote.replication.median-high",
        "metric": "median_signed_error_mev",
        "operator": "gt",
        "threshold": 600,
        "unit": "meV",
        "action": "demote",
    },
)
EXPECTED_EVIDENCE_REQUIREMENTS = (
    {
        "requirement_id": "e.replication.measured-paths",
        "artifact_type": "neb-path-set",
        "description": "At least 22 measured paths, each reduced to the median available signed error across the four locked models; record every failure without imputation.",
        "minimum_count": MINIMUM_MEASURED_PATHS,
    },
    {
        "requirement_id": "e.replication.terminal-candidate-records",
        "artifact_type": "campaign-terminal-records",
        "description": "All 30 registered candidates have an explicit terminal measured-or-failed record; no missing candidate may be omitted or imputed.",
        "minimum_count": EXPECTED_PANEL_PATHS,
    },
)
EXPECTED_KILL_CONDITIONS = (
    {
        "condition_id": "kill.replication.integrity",
        "metric": "integrity_violations",
        "operator": "gt",
        "threshold": 0,
        "unit": "count",
        "action": "kill",
    },
)
CANONICAL_MODELS = (
    {
        "artifact_hash": "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890",
        "model_id": "chgnet",
        "version": "chgnet 0.4.2",
    },
    {
        "artifact_hash": "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694",
        "model_id": "mace-mp-small",
        "version": "mace-torch 0.3.16 / small",
    },
    {
        "artifact_hash": "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3",
        "model_id": "mace-mp-medium",
        "version": "mace-torch 0.3.16 / medium",
    },
    {
        "artifact_hash": "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9",
        "model_id": "mace-mpa-0-medium",
        "version": "mace-torch 0.3.16 / mpa-0 medium",
    },
)


def require_repo_path_no_symlinks(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(path))
    root = Path(os.path.abspath(ROOT))
    try:
        relative = absolute.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must stay inside the repository") from error
    component = root
    for part in relative.parts:
        component /= part
        if component.is_symlink():
            raise ValueError(f"{label} repository path must not contain symlinks")
    return absolute


def load_object(path: Path) -> dict[str, Any]:
    path = require_repo_path_no_symlinks(path, "JSON artifact")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_lock(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_content_hash(manifest: dict[str, Any]) -> str:
    unhashed = {key: value for key, value in manifest.items() if key != "content_hash"}
    canonical = rfc8785.dumps(unhashed)
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def locked_repo_file_hash(lock: Any) -> str:
    if not isinstance(lock, dict) or set(lock) != {"path", "sha256"}:
        raise ValueError("preregistration.input_document must be an exact artifact lock")
    relative = lock.get("path")
    if relative != EXPECTED_INPUT_DOCUMENT_PATH:
        raise ValueError(
            f"preregistration.input_document path must be {EXPECTED_INPUT_DOCUMENT_PATH}"
        )
    candidate = require_repo_path_no_symlinks(
        ROOT / relative, "preregistration.input_document"
    )
    if not candidate.is_file():
        raise ValueError(f"preregistration.input_document does not exist: {relative}")
    source_text = candidate.read_text(encoding="utf-8")
    status_declarations: list[str] = []
    for line in source_text.splitlines():
        normalized = line.strip().casefold().replace("**", "").lstrip("#*>-_ ")
        if normalized.startswith(("status:", "registration status:")) or normalized in {
            "draft",
            "work in progress",
            "not registered",
        }:
            status_declarations.append(normalized)
    if status_declarations != ["status: reviewed / ready to register"]:
        raise ValueError(
            f"preregistration.input_document must declare only {EXPECTED_INPUT_STATUS}"
        )
    for line in source_text.splitlines():
        without_non_draft = re.sub(
            r"\bnon(?:[^a-z0-9]*)draft\b", "", line.casefold()
        )
        compact = re.sub(r"[^a-z]+", "", without_non_draft)
        words = re.sub(r"[^a-z]+", " ", without_non_draft)
        if (
            "draft" in compact
            or "workinprogress" in compact
            or "notregistered" in compact
            or re.search(r"\b(?:wip|w\s+i\s+p)\b", words)
        ):
            raise ValueError(
                "preregistration.input_document contains a contradictory draft marker"
            )
    return sha256_lock(candidate)


def require_canonical_repo_argument(argument: Path, relative: str, label: str) -> Path:
    expected = ROOT / relative
    if Path(os.path.abspath(argument)) != Path(os.path.abspath(expected)):
        raise ValueError(f"{label} must be repository path {relative}")
    return require_repo_path_no_symlinks(expected, label)


def validate_sha256_sidecar(path: Path) -> None:
    path = require_repo_path_no_symlinks(path, "hashed artifact")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    sidecar = require_repo_path_no_symlinks(sidecar, "SHA-256 sidecar")
    if not sidecar.is_file():
        raise ValueError(f"candidate panel SHA-256 sidecar is missing: {sidecar}")
    fields = sidecar.read_text(encoding="utf-8").split()
    expected = sha256_lock(path).removeprefix("sha256:")
    allowed_names = {path.name}
    try:
        allowed_names.add(str(path.resolve().relative_to(ROOT)))
    except ValueError:
        pass
    if len(fields) != 2 or fields[0] != expected or fields[1] not in allowed_names:
        raise ValueError("candidate panel SHA-256 sidecar is stale or malformed")


def _trajectory(archive: zipfile.ZipFile, edge_id: str, kind: str) -> list[Any]:
    suffix = f"/{edge_id}_{kind}.xyz"
    try:
        member = next(name for name in archive.namelist() if name.endswith(suffix))
    except StopIteration as error:
        raise ValueError(f"nebDFT2k source archive lacks {edge_id}_{kind}.xyz") from error
    return cast(
        list[Any],
        read(
            io.StringIO(archive.read(member).decode("utf-8")),
            index=":",
            format="extxyz",
        ),
    )


def _structure_record(atoms: Any) -> dict[str, Any]:
    return {
        "symbols": atoms.get_chemical_symbols(),
        "cell_angstrom": atoms.cell.array.tolist(),
        "pbc": [bool(value) for value in atoms.pbc],
        "positions_angstrom": atoms.positions.tolist(),
    }


def _source_path_record(
    archive: zipfile.ZipFile, row: dict[str, str]
) -> dict[str, Any]:
    initial = _trajectory(archive, row["edge_id"], "init")
    relaxed = _trajectory(archive, row["edge_id"], "relaxed")
    energies: list[float] = []
    for image in relaxed:
        if image.calc is None:
            raise ValueError(f"{row['edge_id']} source image lacks a DFT energy")
        energies.append(float(image.get_potential_energy()))
    saddle_index = max(range(len(energies)), key=energies.__getitem__)
    barrier_ev = float(row["em_dft"])
    if abs(barrier_ev - (max(energies) - min(energies))) > 5e-4:
        raise ValueError(f"{row['edge_id']} source index/profile barrier mismatch")
    return {
        "path_id": row["edge_id"],
        "material_id": row["material_id"],
        "chemical_system": row["chemsys"],
        "split": row["_split"],
        "reference_barrier_ev": barrier_ev,
        "input_images": [_structure_record(image) for image in initial],
        "reference": {
            "image_count": len(relaxed),
            "saddle_image_index": saddle_index,
            "energies_ev": energies,
            "endpoint_initial": _structure_record(relaxed[0]),
            "saddle": _structure_record(relaxed[saddle_index]),
            "endpoint_final": _structure_record(relaxed[-1]),
        },
    }


def expected_replication_rows(
    source_archive: Path, baseline_panel: dict[str, Any]
) -> list[dict[str, Any]]:
    expected_digest = "sha256:" + EXPECTED_REFERENCE_PROVENANCE["source_archive_sha256"]
    if sha256_lock(source_archive) != expected_digest:
        raise ValueError("nebDFT2k source archive digest mismatch")

    baseline_paths = _paths(baseline_panel, "baseline_panel")
    baseline_ids = set(_path_field(baseline_paths, "path_id", "baseline"))
    baseline_systems = set(_path_field(baseline_paths, "chemical_system", "baseline"))
    baseline_barriers = set(
        _path_field(baseline_paths, "reference_barrier_ev", "baseline")
    )

    with zipfile.ZipFile(source_archive) as archive:
        try:
            index_name = next(
                name for name in archive.namelist() if name.endswith("nebDFT2k_index.csv")
            )
        except StopIteration as error:
            raise ValueError("nebDFT2k source archive lacks nebDFT2k_index.csv") from error
        rows = list(
            csv.DictReader(io.StringIO(archive.read(index_name).decode("utf-8")))
        )

        by_chemistry: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            if row.get("_split") == "test":
                by_chemistry.setdefault(row["chemsys"], []).append(row)
        eligible = [
            sorted(
                by_chemistry[chemistry],
                key=lambda row: (row["material_id"], row["edge_id"]),
            )[0]
            for chemistry in sorted(by_chemistry)
        ]
        selected = [
            row
            for row in eligible
            if row["edge_id"] not in baseline_ids
            and row["chemsys"] not in baseline_systems
            and float(row["em_dft"]) not in baseline_barriers
        ][:EXPECTED_PANEL_PATHS]
        if len(selected) != EXPECTED_PANEL_PATHS:
            raise ValueError(
                f"nebDFT2k has only {len(selected)} fully disjoint official-test rows; "
                f"need {EXPECTED_PANEL_PATHS}"
            )
        return [_source_path_record(archive, row) for row in selected]


def _paths(document: dict[str, Any], label: str) -> list[dict[str, Any]]:
    paths = document.get("paths")
    if not isinstance(paths, list) or any(not isinstance(item, dict) for item in paths):
        raise ValueError(f"{label}.paths must be an array of objects")
    return paths


def _path_field(paths: list[dict[str, Any]], field: str, label: str) -> list[Any]:
    values = [path.get(field) for path in paths]
    if any(value is None or value == "" for value in values):
        raise ValueError(f"every {label} path must declare {field}")
    return values


def validate_replication(
    *,
    candidate_panel: dict[str, Any],
    candidate_panel_hash: str,
    baseline_panel: dict[str, Any],
    baseline_campaign: dict[str, Any],
    source_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    manifest_schema: dict[str, Any],
    input_document_hash: str,
    registry: dict[str, Any],
) -> list[str]:
    """Return every refusal reason; an empty list is the only passing state."""
    errors: list[str] = []
    try:
        candidate_schema = load_object(ROOT / CANDIDATE_PANEL_SCHEMA_PATH)
    except (OSError, ValueError) as error:
        return [f"candidate-panel schema is unavailable: {error}"]
    candidate_validator = Draft202012Validator(candidate_schema)
    for error in sorted(candidate_validator.iter_errors(candidate_panel), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"candidate panel fails schema at {location}: {error.message}")
    try:
        candidate_paths = _paths(candidate_panel, "candidate_panel")
        baseline_paths = _paths(baseline_panel, "baseline_panel")
        candidate_ids = _path_field(candidate_paths, "path_id", "candidate")
        candidate_systems = _path_field(candidate_paths, "chemical_system", "candidate")
        candidate_barriers = _path_field(candidate_paths, "reference_barrier_ev", "candidate")
        baseline_ids = set(_path_field(baseline_paths, "path_id", "baseline"))
        baseline_systems = set(_path_field(baseline_paths, "chemical_system", "baseline"))
        baseline_barriers = set(_path_field(baseline_paths, "reference_barrier_ev", "baseline"))
    except ValueError as error:
        return [str(error)]

    if candidate_panel.get("schema") != EXPECTED_PANEL_SCHEMA:
        errors.append(f"candidate panel schema must be {EXPECTED_PANEL_SCHEMA}")
    if candidate_panel.get("panel_id") != EXPECTED_PANEL_ID:
        errors.append(f"candidate panel ID must be {EXPECTED_PANEL_ID}")

    holdout = candidate_panel.get("holdout")
    if not isinstance(holdout, dict):
        errors.append("candidate panel holdout must be an object")
    else:
        if holdout.get("unit") != "chemical_system":
            errors.append("candidate panel holdout unit must be chemical_system")
        if holdout.get("source_split") != "test":
            errors.append("candidate panel must use the official test split")
        if holdout.get("selection_rule") != EXPECTED_SELECTION_RULE:
            errors.append("candidate panel selection rule is not the frozen disjoint rule")
        if holdout.get("selected_chemical_systems") != sorted(candidate_systems):
            errors.append("holdout selected_chemical_systems does not match candidate paths")

    provenance = candidate_panel.get("reference_provenance")
    if not isinstance(provenance, dict) or any(
        provenance.get(key) != value for key, value in EXPECTED_REFERENCE_PROVENANCE.items()
    ):
        errors.append("candidate panel LiTraj source provenance is missing or mismatched")

    execution_protocol = candidate_panel.get("execution_protocol")
    if not isinstance(execution_protocol, dict):
        errors.append("candidate panel execution_protocol must be an object")
    else:
        if execution_protocol.get("failure_policy") != "record failure without imputation":
            errors.append("candidate panel failure policy must forbid imputation")
        if execution_protocol.get("barrier_definition") != (
            "max(image_energy_ev) - min(image_energy_ev)"
        ):
            errors.append("candidate panel barrier definition is not frozen")

    if len(candidate_paths) != EXPECTED_PANEL_PATHS:
        errors.append(
            f"candidate panel has {len(candidate_paths)} paths; need exactly {EXPECTED_PANEL_PATHS}"
        )
    if any(not isinstance(value, str) or not value for value in candidate_ids):
        errors.append("candidate path IDs must be non-empty strings")
        candidate_ids = []
    if any(not isinstance(value, str) or not value for value in candidate_systems):
        errors.append("candidate chemical systems must be non-empty strings")
        candidate_systems = []
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in candidate_barriers
    ):
        errors.append("candidate reference barriers must be finite numbers")
        candidate_barriers = []

    for index, path in enumerate(candidate_paths):
        if not isinstance(path.get("material_id"), str) or not path.get("material_id"):
            errors.append(f"candidate path {index} must declare material_id")
        if path.get("split") != "test":
            errors.append(f"candidate path {index} is not from the official test split")
        images = path.get("input_images")
        if not isinstance(images, list) or not images or any(
            not isinstance(image, dict) for image in images
        ):
            errors.append(f"candidate path {index} lacks executable input_images")
        else:
            expected_topology: tuple[Any, ...] | None = None
            for image in images:
                symbols = image.get("symbols")
                positions = image.get("positions_angstrom")
                cell = image.get("cell_angstrom")
                pbc = image.get("pbc")
                valid_positions = (
                    isinstance(symbols, list)
                    and bool(symbols)
                    and all(isinstance(symbol, str) and symbol for symbol in symbols)
                    and isinstance(positions, list)
                    and len(positions) == len(symbols)
                    and all(
                        isinstance(position, list)
                        and len(position) == 3
                        and all(
                            not isinstance(value, bool)
                            and isinstance(value, (int, float))
                            and math.isfinite(value)
                            for value in position
                        )
                        for position in positions
                    )
                )
                valid_cell = (
                    isinstance(cell, list)
                    and len(cell) == 3
                    and all(
                        isinstance(vector, list)
                        and len(vector) == 3
                        and all(
                            not isinstance(value, bool)
                            and isinstance(value, (int, float))
                            and math.isfinite(value)
                            for value in vector
                        )
                        for vector in cell
                    )
                )
                valid_pbc = (
                    isinstance(pbc, list)
                    and len(pbc) == 3
                    and all(isinstance(value, bool) for value in pbc)
                )
                nonsingular_periodic_cell = True
                if valid_cell and valid_pbc and any(pbc):
                    determinant = (
                        cell[0][0]
                        * (cell[1][1] * cell[2][2] - cell[1][2] * cell[2][1])
                        - cell[0][1]
                        * (cell[1][0] * cell[2][2] - cell[1][2] * cell[2][0])
                        + cell[0][2]
                        * (cell[1][0] * cell[2][1] - cell[1][1] * cell[2][0])
                    )
                    nonsingular_periodic_cell = abs(determinant) > 1e-12
                if (
                    not valid_positions
                    or not valid_cell
                    or not valid_pbc
                    or not nonsingular_periodic_cell
                ):
                    errors.append(f"candidate path {index} has a malformed input image")
                    break
                topology = (
                    tuple(symbols),
                    tuple(pbc),
                    tuple(tuple(vector) for vector in cell),
                )
                if expected_topology is None:
                    expected_topology = topology
                elif topology != expected_topology:
                    errors.append(
                        f"candidate path {index} changes atom identity/order, PBC, or cell "
                        "across input images"
                    )
                    break
        reference = path.get("reference")
        energies = reference.get("energies_ev") if isinstance(reference, dict) else None
        if not isinstance(energies, list) or len(energies) < 2 or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in energies
        ):
            errors.append(f"candidate path {index} lacks finite reference energies")
        elif isinstance(path.get("reference_barrier_ev"), (int, float)) and not isinstance(
            path.get("reference_barrier_ev"), bool
        ):
            profile_barrier = max(energies) - min(energies)
            if abs(float(path["reference_barrier_ev"]) - profile_barrier) > 5e-4:
                errors.append(
                    f"candidate path {index} reference barrier disagrees with its energy profile"
                )

    if candidate_paths != source_rows:
        errors.append(
            "candidate paths and scientific payloads do not match the pinned "
            "deterministic source selection"
        )

    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("candidate path IDs are not unique")
    if len(candidate_systems) != len(set(candidate_systems)):
        errors.append("candidate chemical systems are not unique")

    shared_ids = sorted(set(candidate_ids) & baseline_ids)
    if shared_ids:
        errors.append(f"shared path IDs with the frozen Z1 panel: {shared_ids}")
    shared_systems = sorted(set(candidate_systems) & baseline_systems)
    if shared_systems:
        errors.append(f"shared chemical systems with the frozen Z1 panel: {shared_systems}")
    shared_barriers = sorted(set(candidate_barriers) & baseline_barriers)
    if shared_barriers:
        errors.append(f"shared reference barriers with the frozen Z1 panel: {shared_barriers}")

    baseline_rows = baseline_campaign.get("per_path")
    if not isinstance(baseline_rows, list) or any(not isinstance(row, dict) for row in baseline_rows):
        errors.append("baseline campaign per_path must be an array of objects")
    else:
        campaign_ids = {row.get("path_id") for row in baseline_rows}
        campaign_systems = {row.get("chemical_system") for row in baseline_rows}
        campaign_barriers = {row.get("reference_barrier_ev") for row in baseline_rows}
        if set(candidate_ids) & campaign_ids:
            errors.append("candidate path IDs overlap z1-union-campaign.json")
        if set(candidate_systems) & campaign_systems:
            errors.append("candidate chemical systems overlap z1-union-campaign.json")
        if set(candidate_barriers) & campaign_barriers:
            errors.append("candidate reference barriers overlap z1-union-campaign.json")

    schema_errors = sorted(
        Draft202012Validator(
            manifest_schema, format_checker=FormatChecker()
        ).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if schema_errors:
        errors.append(
            "manifest fails campaign-manifest.v1.schema.json: "
            + "; ".join(error.message for error in schema_errors)
        )

    if manifest.get("campaign_id") != EXPECTED_CAMPAIGN_ID:
        errors.append(f"manifest campaign_id must be {EXPECTED_CAMPAIGN_ID}")
    if manifest.get("preregistration_id") != EXPECTED_PREREGISTRATION_ID:
        errors.append(f"manifest preregistration_id must be {EXPECTED_PREREGISTRATION_ID}")
    if tuple(manifest.get("target_premises", ())) != EXPECTED_TARGET_PREMISES:
        errors.append("manifest target premises are not the exact frozen replication premise")
    if tuple(manifest.get("available_models", ())) != CANONICAL_MODELS:
        errors.append("manifest does not bind the four canonical models by exact id/hash/version")
    if manifest.get("acceptance_test") != EXPECTED_ACCEPTANCE_TEST:
        errors.append("manifest does not freeze H1 signed_error_positive > 0.5")
    if tuple(manifest.get("frozen_hypotheses", ())) != EXPECTED_HYPOTHESES:
        errors.append("manifest does not freeze the exact H1/H2 path-median hypotheses")
    if tuple(manifest.get("demotion_conditions", ())) != EXPECTED_DEMOTIONS:
        errors.append("manifest does not freeze H1/H2 demotion bounds")
    if tuple(manifest.get("evidence_requirements", ())) != EXPECTED_EVIDENCE_REQUIREMENTS:
        errors.append(
            f"manifest does not freeze the {MINIMUM_MEASURED_PATHS}-path median/no-imputation requirement"
        )
    if manifest.get("exclusions") != []:
        errors.append("manifest exclusions must remain exactly empty for the four-model scope")
    if tuple(manifest.get("kill_conditions", ())) != EXPECTED_KILL_CONDITIONS:
        errors.append("manifest does not freeze the exact integrity stop condition")

    execution = manifest.get("execution")
    expected_lock = {"path": EXPECTED_PANEL_PATH, "sha256": candidate_panel_hash}
    expected_execution = {
        "candidate_panel": expected_lock,
        "lane": "literature.protocol-offset-sign-skew.replication",
        "model_selection": "available_models",
        "excluded_models_block_execution": False,
    }
    if execution != expected_execution:
        errors.append("manifest execution block is not the exact frozen replication lane")

    preregistration = manifest.get("preregistration")
    recorded_inputs = preregistration.get("recorded_inputs") if isinstance(preregistration, dict) else None
    if not isinstance(recorded_inputs, list) or expected_lock not in recorded_inputs:
        errors.append("preregistration.recorded_inputs does not contain the replication panel lock")
    if not isinstance(preregistration, dict) or preregistration.get("source") != (
        "https://doi.org/10.1038/s41524-025-01571-z"
    ):
        errors.append("preregistration source DOI is not frozen")
    input_document = preregistration.get("input_document") if isinstance(preregistration, dict) else None
    if (
        not isinstance(input_document, dict)
        or input_document.get("path") != EXPECTED_INPUT_DOCUMENT_PATH
        or input_document.get("sha256") != input_document_hash
    ):
        errors.append("preregistration.input_document is not the locked reviewed source")
    if isinstance(preregistration, dict):
        registered_at = preregistration.get("registered_at")
        if not isinstance(registered_at, str):
            errors.append("preregistration.registered_at must be a valid UTC timestamp")
        else:
            try:
                parsed_registered_at = datetime.fromisoformat(
                    registered_at.replace("Z", "+00:00")
                )
            except ValueError:
                errors.append("preregistration.registered_at must be a valid UTC timestamp")
            else:
                if parsed_registered_at.utcoffset() != timedelta(0):
                    errors.append("preregistration.registered_at must use a zero UTC offset")
        expected_preregistration = {
            "registered_at": registered_at,
            "source": "https://doi.org/10.1038/s41524-025-01571-z",
            "frozen_before_execution": True,
            "recorded_inputs": [expected_lock],
            "input_document": {
                "path": EXPECTED_INPUT_DOCUMENT_PATH,
                "sha256": input_document_hash,
            },
        }
        if preregistration != expected_preregistration:
            errors.append("manifest preregistration block is not the exact frozen registration")

    expected_content_hash = manifest_content_hash(manifest)
    if manifest.get("content_hash") != expected_content_hash:
        errors.append("manifest content_hash is stale or non-canonical")
    registered = any(entry == manifest for entry in registry.get("campaigns", []))
    if not registered:
        errors.append("manifest is not registered byte-for-byte in registry/campaigns.v1.json")

    models = [model["model_id"] for model in CANONICAL_MODELS]
    baseline_pairs = {(system, model) for system in baseline_systems for model in models}
    candidate_pairs = {(system, model) for system in candidate_systems for model in models}
    if baseline_pairs & candidate_pairs:
        errors.append("candidate (chemical_system, model) pairs overlap the frozen Z1 panel")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-panel", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    try:
        expected_candidate_path = require_canonical_repo_argument(
            args.candidate_panel, EXPECTED_PANEL_PATH, "candidate panel"
        )
        expected_manifest_path = require_canonical_repo_argument(
            args.manifest, EXPECTED_MANIFEST_PATH, "manifest"
        )
        expected_source_archive = require_canonical_repo_argument(
            args.source_archive, SOURCE_ARCHIVE_PATH, "source archive"
        )
        validate_sha256_sidecar(expected_candidate_path)
        validate_sha256_sidecar(ROOT / BASELINE_PANEL_PATH)
        validate_sha256_sidecar(ROOT / BASELINE_CAMPAIGN_PATH)
        candidate_panel = load_object(args.candidate_panel)
        baseline_panel = load_object(ROOT / BASELINE_PANEL_PATH)
        manifest = load_object(args.manifest)
        preregistration = manifest.get("preregistration")
        input_document = (
            preregistration.get("input_document") if isinstance(preregistration, dict) else None
        )
        errors = validate_replication(
            candidate_panel=candidate_panel,
            candidate_panel_hash=sha256_lock(args.candidate_panel),
            baseline_panel=baseline_panel,
            baseline_campaign=load_object(ROOT / BASELINE_CAMPAIGN_PATH),
            source_rows=expected_replication_rows(expected_source_archive, baseline_panel),
            manifest=manifest,
            manifest_schema=load_object(ROOT / "schemas/campaign-manifest.v1.schema.json"),
            input_document_hash=locked_repo_file_hash(input_document),
            registry=load_object(ROOT / CAMPAIGN_REGISTRY_PATH),
        )
    except (OSError, ValueError) as error:
        errors = [str(error)]

    if errors:
        print("REFUSE sign-skew replication registration:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("PASS sign-skew replication registration and overlap guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
