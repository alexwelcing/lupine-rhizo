#!/usr/bin/env python3
"""Produce a fail-closed overlap report for the proposed Z1 replication panel.

The candidate panel is compared against BOTH frozen Z1 artifacts: the full
30-path baseline panel lock and the 23-row union campaign that recorded model
results for a subset of it. Comparing only the campaign would let a candidate
reuse one of the seven baseline paths that never reached a model run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, NamedTuple, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_PANEL = ROOT / "data/candidates/z1-sign-skew-replication-panel.lock.json"
DEFAULT_CANDIDATE_MANIFEST = (
    ROOT
    / "docs/plans/2026-08-03-protocol-offset-sign-skew-replication-campaign-manifest-draft.json"
)
DEFAULT_Z1_BASELINE_PANEL = ROOT / "data/candidates/z1_nebdft2k_barriers.lock.json"
DEFAULT_Z1_UNION_CAMPAIGN = ROOT / "data/candidates/z1-union-campaign.json"
DEFAULT_OUTPUT = ROOT / "data/candidates/z1-sign-skew-replication-disjointness-report.json"
REPORT_SCHEMA = "lupine.z1.replication_panel_disjointness_report.v2"


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


def _panel_rows(panel: dict[str, Any], label: str) -> list[dict[str, Any]]:
    rows = _objects(panel.get("paths"), f"{label} paths")
    for index, row in enumerate(rows):
        _nonempty_string(row.get("path_id"), f"{label} path {index} path_id")
        _nonempty_string(
            row.get("chemical_system"), f"{label} path {index} chemical_system"
        )
        _finite_number(
            row.get("reference_barrier_ev"),
            f"{label} path {index} reference_barrier_ev",
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


class FrozenSource(NamedTuple):
    """One frozen Z1 artifact reduced to the fields disjointness is defined over."""

    name: str
    rows: list[dict[str, Any]]
    declares_model_results: bool


def _comparable_row(row: dict[str, Any], models: tuple[str, ...]) -> dict[str, Any]:
    return {
        "path_id": row["path_id"],
        "chemical_system": row["chemical_system"],
        "reference_barrier_ev": row["reference_barrier_ev"],
        "models": models,
    }


def _frozen_sources(
    *, z1_baseline_panel: dict[str, Any], z1_union_campaign: dict[str, Any]
) -> list[FrozenSource]:
    """Both frozen Z1 artifacts; neither may be skipped and neither may be empty."""
    baseline_rows = _panel_rows(z1_baseline_panel, "Z1 baseline panel")
    union_rows = _union_rows(z1_union_campaign)
    if not baseline_rows:
        raise ValueError("Z1 baseline panel declares no paths to compare against")
    if not union_rows:
        raise ValueError("Z1 union campaign declares no paths to compare against")
    return [
        # The baseline lock records the frozen panel definition only; it carries no
        # per-model results, so model-pair overlap cannot be derived from it and
        # chemistry/path/barrier overlap must carry the refusal on its own.
        FrozenSource(
            name="z1_baseline_panel",
            rows=[_comparable_row(row, ()) for row in baseline_rows],
            declares_model_results=False,
        ),
        FrozenSource(
            name="z1_union_campaign",
            rows=[
                _comparable_row(row, tuple(sorted(row["per_model"]))) for row in union_rows
            ],
            declares_model_results=True,
        ),
    ]


def build_report(
    *,
    candidate_panel: dict[str, Any],
    candidate_manifest: dict[str, Any],
    z1_baseline_panel: dict[str, Any],
    z1_union_campaign: dict[str, Any],
    input_locks: dict[str, Any],
) -> dict[str, Any]:
    """Return exact overlaps; malformed inputs raise instead of implying disjointness."""
    candidate_rows = _panel_rows(candidate_panel, "candidate panel")
    candidate_models = _candidate_models(candidate_manifest)
    frozen_sources = _frozen_sources(
        z1_baseline_panel=z1_baseline_panel, z1_union_campaign=z1_union_campaign
    )

    path_violations: list[dict[str, Any]] = []
    system_violations: list[dict[str, Any]] = []
    pair_violations: list[dict[str, Any]] = []
    barrier_violations: list[dict[str, Any]] = []

    for candidate_index, candidate in enumerate(candidate_rows):
        for source in frozen_sources:
            for frozen_index, frozen_row in enumerate(source.rows):
                origin = {
                    "candidate_path_index": candidate_index,
                    "frozen_artifact": source.name,
                    "frozen_path_index": frozen_index,
                }
                if candidate["path_id"] == frozen_row["path_id"]:
                    path_violations.append({"path_id": candidate["path_id"], **origin})
                if candidate["chemical_system"] == frozen_row["chemical_system"]:
                    # A chemistry collision is a violation in its own right. Model
                    # results may be absent (deferred or failed Z1 rows), and the
                    # absence of a model pair must never imply the systems are
                    # disjoint, so record the system overlap before deriving pairs.
                    system_violations.append(
                        {"chemical_system": candidate["chemical_system"], **origin}
                    )
                    shared_models = sorted(
                        set(candidate_models) & set(frozen_row["models"])
                    )
                    for model in shared_models:
                        pair_violations.append(
                            {
                                "chemical_system": candidate["chemical_system"],
                                "model": model,
                                **origin,
                            }
                        )
                if candidate["reference_barrier_ev"] == frozen_row["reference_barrier_ev"]:
                    barrier_violations.append(
                        {
                            "reference_barrier_ev": candidate["reference_barrier_ev"],
                            **origin,
                        }
                    )

    violations = {
        "path_ids": path_violations,
        "chemical_systems": system_violations,
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
        "frozen_sources": [
            {
                "name": source.name,
                "path_count": len(source.rows),
                "declares_model_results": source.declares_model_results,
            }
            for source in frozen_sources
        ],
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
    parser.add_argument("--z1-baseline-panel", type=Path, default=DEFAULT_Z1_BASELINE_PANEL)
    parser.add_argument("--z1-union-campaign", type=Path, default=DEFAULT_Z1_UNION_CAMPAIGN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    try:
        locks = {
            "candidate_panel": _lock(args.candidate_panel),
            "candidate_manifest": _lock(args.candidate_manifest),
            "z1_baseline_panel": _lock(args.z1_baseline_panel),
            "z1_union_campaign": _lock(args.z1_union_campaign),
        }
        report = build_report(
            candidate_panel=_load_object(args.candidate_panel),
            candidate_manifest=_load_object(args.candidate_manifest),
            z1_baseline_panel=_load_object(args.z1_baseline_panel),
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
