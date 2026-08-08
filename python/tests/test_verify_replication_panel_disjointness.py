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
        z1_baseline_panel=panel(path("old", "Na-O", 0.75), path("deferred", "K-O", 0.5)),
        z1_union_campaign=union(row("old", "Na-O", 0.75, "model-a", "model-b")),
        input_locks={
            "candidate_panel": {"path": "candidate.json", "sha256": "sha256:a"},
            "candidate_manifest": {"path": "manifest.json", "sha256": "sha256:b"},
            "z1_baseline_panel": {"path": "baseline.json", "sha256": "sha256:c"},
            "z1_union_campaign": {"path": "union.json", "sha256": "sha256:d"},
        },
    )

    assert report["status"] == "pass"
    assert report["disjoint"] is True
    assert report["overlap_counts"] == {
        "path_ids": 0,
        "chemical_systems": 0,
        "chemical_system_model_pairs": 0,
        "reference_barriers": 0,
    }
    assert report["violations"] == {
        "path_ids": [],
        "chemical_systems": [],
        "chemical_system_model_pairs": [],
        "reference_barriers": [],
    }
    assert report["frozen_sources"] == [
        {
            "name": "z1_baseline_panel",
            "path_count": 2,
            "declares_model_results": False,
        },
        {
            "name": "z1_union_campaign",
            "path_count": 1,
            "declares_model_results": True,
        },
    ]
    assert set(report["inputs"]) == {
        "candidate_panel",
        "candidate_manifest",
        "z1_baseline_panel",
        "z1_union_campaign",
    }


def test_report_lists_every_exact_offending_entry() -> None:
    report = MODULE.build_report(
        candidate_panel=panel(
            path("shared-path", "Shared-Chem", 1.5),
            path("candidate-2", "Shared-Chem", 2.5),
        ),
        candidate_manifest=manifest("shared-model", "candidate-only-model"),
        z1_baseline_panel=panel(path("baseline-only", "Baseline-Chem", 9.5)),
        z1_union_campaign=union(
            row("shared-path", "Shared-Chem", 1.5, "shared-model", "union-only-model")
        ),
        input_locks={},
    )

    assert report["status"] == "refuse"
    assert report["disjoint"] is False
    assert report["overlap_counts"] == {
        "path_ids": 1,
        "chemical_systems": 2,
        "chemical_system_model_pairs": 2,
        "reference_barriers": 1,
    }
    assert report["violations"]["path_ids"] == [
        {
            "path_id": "shared-path",
            "candidate_path_index": 0,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        }
    ]
    assert report["violations"]["chemical_systems"] == [
        {
            "chemical_system": "Shared-Chem",
            "candidate_path_index": 0,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        },
        {
            "chemical_system": "Shared-Chem",
            "candidate_path_index": 1,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        },
    ]
    assert report["violations"]["chemical_system_model_pairs"] == [
        {
            "chemical_system": "Shared-Chem",
            "model": "shared-model",
            "candidate_path_index": 0,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        },
        {
            "chemical_system": "Shared-Chem",
            "model": "shared-model",
            "candidate_path_index": 1,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        },
    ]
    assert report["violations"]["reference_barriers"] == [
        {
            "reference_barrier_ev": 1.5,
            "candidate_path_index": 0,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        }
    ]


def test_baseline_only_path_reuse_is_refused() -> None:
    """A frozen baseline path that never reached a model run is still off limits.

    Seven of the 30 paths in ``z1_nebdft2k_barriers.lock.json`` are absent from
    the 23-row union campaign, so comparing against the campaign alone reported
    zero overlaps for a candidate that reused one of them.
    """
    report = MODULE.build_report(
        candidate_panel=panel(path("deferred-path", "Deferred-Chem", 0.485935)),
        candidate_manifest=manifest("model-a"),
        z1_baseline_panel=panel(
            path("measured-path", "Measured-Chem", 1.0),
            path("deferred-path", "Deferred-Chem", 0.485935),
        ),
        z1_union_campaign=union(row("measured-path", "Measured-Chem", 1.0, "model-a")),
        input_locks={},
    )

    assert report["status"] == "refuse"
    assert report["overlap_counts"] == {
        "path_ids": 1,
        "chemical_systems": 1,
        "chemical_system_model_pairs": 0,
        "reference_barriers": 1,
    }
    for category in ("path_ids", "chemical_systems", "reference_barriers"):
        assert [entry["frozen_artifact"] for entry in report["violations"][category]] == [
            "z1_baseline_panel"
        ]
        assert [entry["frozen_path_index"] for entry in report["violations"][category]] == [1]


def test_chemistry_overlap_without_model_results_is_refused() -> None:
    """An overlapping chemistry refuses even when the frozen row has no model results.

    Union row ``mp-756912_1_1_1_0_0`` carries an empty ``per_model``; deriving the
    violation from shared models alone let its chemistry be reused silently.
    """
    report = MODULE.build_report(
        candidate_panel=panel(path("candidate-path", "Shared-Chem", 1.0)),
        candidate_manifest=manifest("model-a", "model-b"),
        z1_baseline_panel=panel(path("baseline-only", "Baseline-Chem", 9.5)),
        z1_union_campaign=union(row("union-path", "Shared-Chem", 2.0)),
        input_locks={},
    )

    assert report["status"] == "refuse"
    assert report["overlap_counts"] == {
        "path_ids": 0,
        "chemical_systems": 1,
        "chemical_system_model_pairs": 0,
        "reference_barriers": 0,
    }
    assert report["violations"]["chemical_systems"] == [
        {
            "chemical_system": "Shared-Chem",
            "candidate_path_index": 0,
            "frozen_artifact": "z1_union_campaign",
            "frozen_path_index": 0,
        }
    ]


@pytest.mark.parametrize(
    ("candidate_panel", "candidate_manifest", "baseline", "campaign", "message"),
    [
        (
            {"paths": "not-a-list"},
            manifest("m"),
            panel(path("b", "B", 3.0)),
            union(row("old", "D", 2.0, "m")),
            "candidate panel paths",
        ),
        (
            panel(path("p", "C", True)),
            manifest("m"),
            panel(path("b", "B", 3.0)),
            union(row("old", "D", 2.0, "m")),
            "finite numeric",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest(""),
            panel(path("b", "B", 3.0)),
            union(row("old", "D", 2.0, "m")),
            "model_id",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            {"paths": [{"path_id": "b", "chemical_system": "B"}]},
            union(row("old", "D", 2.0, "m")),
            "Z1 baseline panel path 0 reference_barrier_ev",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            {},
            union(row("old", "D", 2.0, "m")),
            "Z1 baseline panel paths",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            panel(),
            union(row("old", "D", 2.0, "m")),
            "Z1 baseline panel declares no paths",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            panel(path("b", "B", 3.0)),
            union(),
            "Z1 union campaign declares no paths",
        ),
        (
            panel(path("p", "C", 1.0)),
            manifest("m"),
            panel(path("b", "B", 3.0)),
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
    candidate_panel: dict,
    candidate_manifest: dict,
    baseline: dict,
    campaign: dict,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        MODULE.build_report(
            candidate_panel=candidate_panel,
            candidate_manifest=candidate_manifest,
            z1_baseline_panel=baseline,
            z1_union_campaign=campaign,
            input_locks={},
        )


def test_build_report_requires_the_baseline_panel() -> None:
    """The full frozen panel is a required input, never an optional extra."""
    with pytest.raises(TypeError):
        MODULE.build_report(  # type: ignore[call-arg]
            candidate_panel=panel(path("p", "C", 1.0)),
            candidate_manifest=manifest("m"),
            z1_union_campaign=union(row("old", "D", 2.0, "m")),
            input_locks={},
        )


def test_cli_writes_report_and_refuses_on_overlap(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.json"
    manifest_path = tmp_path / "manifest.json"
    baseline_path = tmp_path / "baseline.json"
    union_path = tmp_path / "union.json"
    report_path = tmp_path / "report.json"
    candidate_path.write_text(
        json.dumps(panel(path("same", "C", 1.0))), encoding="utf-8"
    )
    manifest_path.write_text(json.dumps(manifest("m")), encoding="utf-8")
    baseline_path.write_text(
        json.dumps(panel(path("unrelated", "E", 3.0))), encoding="utf-8"
    )
    union_path.write_text(
        json.dumps(union(row("same", "D", 2.0, "m"))), encoding="utf-8"
    )

    exit_code = MODULE.main(
        [
            "--candidate-panel",
            str(candidate_path),
            "--candidate-manifest",
            str(manifest_path),
            "--z1-baseline-panel",
            str(baseline_path),
            "--z1-union-campaign",
            str(union_path),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 2
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "refuse"


def test_cli_locks_the_baseline_panel_by_path_and_digest(tmp_path: Path) -> None:
    """The report must record which baseline bytes the comparison actually used."""
    report_path = tmp_path / "report.json"

    exit_code = MODULE.main(["--output", str(report_path)])

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert report["status"] == "pass"
    baseline_lock = report["inputs"]["z1_baseline_panel"]
    assert baseline_lock["path"] == "data/candidates/z1_nebdft2k_barriers.lock.json"
    assert baseline_lock["sha256"] == MODULE._lock(MODULE.DEFAULT_Z1_BASELINE_PANEL)["sha256"]
    assert report["frozen_sources"][0] == {
        "name": "z1_baseline_panel",
        "path_count": 30,
        "declares_model_results": False,
    }
