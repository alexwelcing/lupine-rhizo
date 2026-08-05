from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/verify_replication_panel_disjointness.py"
SPEC = importlib.util.spec_from_file_location("verify_replication_panel_disjointness", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def panel(*paths: dict) -> dict:
    return {"paths": list(paths)}


def manifest(*models: str) -> dict:
    return {"manifest": {"available_models": [{"model_id": model} for model in models]}}


def union(*rows: dict) -> dict:
    return {"per_path": list(rows)}


def path(path_id: str, chemical_system: str, barrier: float) -> dict:
    return {
        "path_id": path_id,
        "chemical_system": chemical_system,
        "reference_barrier_ev": barrier,
    }


def row(
    path_id: str, chemical_system: str, barrier: float, *models: str
) -> dict:
    return {
        "path_id": path_id,
        "chemical_system": chemical_system,
        "reference_barrier_ev": barrier,
        "models_present": list(models),
        "per_model": {model: {} for model in models},
    }


def test_clean_report_has_zero_overlaps() -> None:
    report = MODULE.build_report(
        candidate_panel=panel(path("new", "Li-O", 1.25)),
        candidate_manifest=manifest("model-a", "model-b"),
        z1_union_campaign=union(row("old", "Na-O", 0.75, "model-a", "model-b")),
        input_locks={
            "candidate_panel": {"path": "candidate.json", "sha256": "sha256:a"},
            "candidate_manifest": {"path": "manifest.json", "sha256": "sha256:b"},
            "z1_union_campaign": {"path": "union.json", "sha256": "sha256:c"},
        },
    )

    assert report["status"] == "pass"
    assert report["disjoint"] is True
    assert report["overlap_counts"] == {
        "path_ids": 0,
        "chemical_system_model_pairs": 0,
        "reference_barriers": 0,
    }
    assert report["violations"] == {
        "path_ids": [],
        "chemical_system_model_pairs": [],
        "reference_barriers": [],
    }


def test_report_lists_every_exact_offending_entry() -> None:
    report = MODULE.build_report(
        candidate_panel=panel(
            path("shared-path", "Shared-Chem", 1.5),
            path("candidate-2", "Shared-Chem", 2.5),
        ),
        candidate_manifest=manifest("shared-model", "candidate-only-model"),
        z1_union_campaign=union(
            row("shared-path", "Shared-Chem", 1.5, "shared-model", "union-only-model")
        ),
        input_locks={},
    )

    assert report["status"] == "refuse"
    assert report["disjoint"] is False
    assert report["overlap_counts"] == {
        "path_ids": 1,
        "chemical_system_model_pairs": 2,
        "reference_barriers": 1,
    }
    assert report["violations"]["path_ids"] == [
        {
            "path_id": "shared-path",
            "candidate_path_index": 0,
            "z1_union_path_index": 0,
        }
    ]
    assert report["violations"]["chemical_system_model_pairs"] == [
        {
            "chemical_system": "Shared-Chem",
            "model": "shared-model",
            "candidate_path_index": 0,
            "z1_union_path_index": 0,
        },
        {
            "chemical_system": "Shared-Chem",
            "model": "shared-model",
            "candidate_path_index": 1,
            "z1_union_path_index": 0,
        },
    ]
    assert report["violations"]["reference_barriers"] == [
        {
            "reference_barrier_ev": 1.5,
            "candidate_path_index": 0,
            "z1_union_path_index": 0,
        }
    ]


@pytest.mark.parametrize(
    ("candidate_panel", "candidate_manifest", "campaign", "message"),
    [
        ({"paths": "not-a-list"}, manifest("m"), union(), "candidate panel paths"),
        (panel(path("p", "C", True)), manifest("m"), union(), "finite numeric"),
        (panel(path("p", "C", 1.0)), manifest(""), union(), "model_id"),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            union(
                {
                    **row("old", "D", 2.0, "m"),
                    "models_present": ["different"],
                }
            ),
            "models_present must exactly match per_model keys",
        ),
    ],
)
def test_malformed_inputs_fail_closed(
    candidate_panel: dict, candidate_manifest: dict, campaign: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        MODULE.build_report(
            candidate_panel=candidate_panel,
            candidate_manifest=candidate_manifest,
            z1_union_campaign=campaign,
            input_locks={},
        )


def test_cli_writes_report_and_refuses_on_overlap(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    manifest_path = tmp_path / "manifest.json"
    union_path = tmp_path / "union.json"
    report_path = tmp_path / "report.json"
    candidate_path.write_text(
        json.dumps(panel(path("same", "C", 1.0))), encoding="utf-8"
    )
    manifest_path.write_text(json.dumps(manifest("m")), encoding="utf-8")
    union_path.write_text(
        json.dumps(union(row("same", "D", 2.0, "m"))), encoding="utf-8"
    )

    exit_code = MODULE.main(
        [
            "--candidate-panel",
            str(candidate_path),
            "--candidate-manifest",
            str(manifest_path),
            "--z1-union-campaign",
            str(union_path),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 2
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "refuse"
