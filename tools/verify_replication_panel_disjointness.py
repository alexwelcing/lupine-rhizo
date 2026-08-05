#!/usr/bin/env python3
"""Produce a fail-closed overlap report for the proposed Z1 replication panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_PANEL = ROOT / "data/candidates/z1-sign-skew-replication-panel.lock.json"
DEFAULT_CANDIDATE_MANIFEST = (
    ROOT
    / "docs/plans/2026-08-03-protocol-offset-sign-skew-replication-campaign-manifest-draft.json"
)
DEFAULT_Z1_UNION_CAMPAIGN = ROOT / "data/candidates/z1-union-campaign.json"
DEFAULT_OUTPUT = ROOT / "data/candidates/z1-sign-skew-replication-disjointness-report.json"
REPORT_SCHEMA = "lupine.z1.replication_panel_disjointness_report.v1"


def _objects(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an array of objects")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _finite_number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite numeric value")
    return value


def _candidate_rows(candidate_panel: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _objects(candidate_panel.get("paths"), "candidate panel paths")
    for index, row in enumerate(rows):
        _nonempty_string(row.get("path_id"), f"candidate path {index} path_id")
        _nonempty_string(
            row.get("chemical_system"), f"candidate path {index} chemical_system"
        )
        _finite_number(
            row.get("reference_barrier_ev"),
            f"candidate path {index} reference_barrier_ev",
        )
    return rows


def _candidate_models(candidate_manifest: dict[str, Any]) -> list[str]:
    manifest = candidate_manifest.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("candidate manifest must contain a manifest object")
    models = _objects(manifest.get("available_models"), "candidate manifest available_models")
    model_ids = [
        _nonempty_string(model.get("model_id"), f"candidate model {index} model_id")
        for index, model in enumerate(models)
    ]
    if len(model_ids) != len(set(model_ids)):
        raise ValueError("candidate manifest model_id values must be unique")
    return model_ids


def _union_rows(z1_union_campaign: dict[str, Any]) -> list[dict[str, Any]]:
    rows = _objects(z1_union_campaign.get("per_path"), "Z1 union campaign per_path")
    for index, row in enumerate(rows):
        _nonempty_string(row.get("path_id"), f"Z1 union path {index} path_id")
        _nonempty_string(
            row.get("chemical_system"), f"Z1 union path {index} chemical_system"
        )
        _finite_number(
            row.get("reference_barrier_ev"),
            f"Z1 union path {index} reference_barrier_ev",
        )
        per_model = row.get("per_model")
        if not isinstance(per_model, dict) or any(
            not isinstance(model, str) or not model for model in per_model
        ):
            raise ValueError(f"Z1 union path {index} per_model must be an object keyed by model")
        models_present = row.get("models_present")
        if (
            not isinstance(models_present, list)
            or any(not isinstance(model, str) or not model for model in models_present)
            or len(models_present) != len(set(models_present))
        ):
            raise ValueError(
                f"Z1 union path {index} models_present must contain unique model strings"
            )
        if set(models_present) != set(per_model):
            raise ValueError(
                f"Z1 union path {index} models_present must exactly match per_model keys"
            )
    return rows


def build_report(
    *,
    candidate_panel: dict[str, Any],
    candidate_manifest: dict[str, Any],
    z1_union_campaign: dict[str, Any],
    input_locks: dict[str, Any],
) -> dict[str, Any]:
    """Return exact overlaps; malformed inputs raise instead of implying disjointness."""
    candidate_rows = _candidate_rows(candidate_panel)
    candidate_models = _candidate_models(candidate_manifest)
    union_rows = _union_rows(z1_union_campaign)

    path_violations: list[dict[str, Any]] = []
    pair_violations: list[dict[str, Any]] = []
    barrier_violations: list[dict[str, Any]] = []

    for candidate_index, candidate in enumerate(candidate_rows):
        for union_index, union_row in enumerate(union_rows):
            if candidate["path_id"] == union_row["path_id"]:
                path_violations.append(
                    {
                        "path_id": candidate["path_id"],
                        "candidate_path_index": candidate_index,
                        "z1_union_path_index": union_index,
                    }
                )
            shared_models = sorted(set(candidate_models) & set(union_row["per_model"]))
            if candidate["chemical_system"] == union_row["chemical_system"]:
                for model in shared_models:
                    pair_violations.append(
                        {
                            "chemical_system": candidate["chemical_system"],
                            "model": model,
                            "candidate_path_index": candidate_index,
                            "z1_union_path_index": union_index,
                        }
                    )
            if candidate["reference_barrier_ev"] == union_row["reference_barrier_ev"]:
                barrier_violations.append(
                    {
                        "reference_barrier_ev": candidate["reference_barrier_ev"],
                        "candidate_path_index": candidate_index,
                        "z1_union_path_index": union_index,
                    }
                )

    violations = {
        "path_ids": path_violations,
        "chemical_system_model_pairs": pair_violations,
        "reference_barriers": barrier_violations,
    }
    overlap_counts = {key: len(value) for key, value in violations.items()}
    disjoint = all(count == 0 for count in overlap_counts.values())
    return {
        "schema": REPORT_SCHEMA,
        "status": "pass" if disjoint else "refuse",
        "disjoint": disjoint,
        "inputs": input_locks,
        "candidate_path_count": len(candidate_rows),
        "candidate_models": candidate_models,
        "z1_union_path_count": len(union_rows),
        "overlap_counts": overlap_counts,
        "violations": violations,
    }


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _lock(path: Path) -> dict[str, str]:
    absolute = Path(os.path.abspath(path))
    try:
        display_path = str(absolute.relative_to(ROOT))
    except ValueError:
        display_path = str(absolute)
    try:
        digest = hashlib.sha256(absolute.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"cannot hash {path}: {error}") from error
    return {"path": display_path, "sha256": f"sha256:{digest}"}


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-panel", type=Path, default=DEFAULT_CANDIDATE_PANEL)
    parser.add_argument("--candidate-manifest", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--z1-union-campaign", type=Path, default=DEFAULT_Z1_UNION_CAMPAIGN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    try:
        locks = {
            "candidate_panel": _lock(args.candidate_panel),
            "candidate_manifest": _lock(args.candidate_manifest),
            "z1_union_campaign": _lock(args.z1_union_campaign),
        }
        report = build_report(
            candidate_panel=_load_object(args.candidate_panel),
            candidate_manifest=_load_object(args.candidate_manifest),
            z1_union_campaign=_load_object(args.z1_union_campaign),
            input_locks=locks,
        )
    except ValueError as error:
        report = {
            "schema": REPORT_SCHEMA,
            "status": "refuse",
            "disjoint": False,
            "error": str(error),
        }
        _write_report(args.output, report)
        print(f"REFUSE: {error}")
        return 2

    _write_report(args.output, report)
    if report["disjoint"]:
        print(f"PASS: zero overlaps; wrote {args.output}")
        return 0
    print(f"REFUSE: overlaps found; wrote {args.output}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
