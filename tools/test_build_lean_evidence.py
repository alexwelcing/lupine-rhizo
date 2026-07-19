from __future__ import annotations

from pathlib import Path

import build_lean_evidence as evidence


def test_vision_tracks_honest_errors_inventory() -> None:
    counts = evidence._vision_counts()

    assert counts == evidence.EXPECTED_VISION
    assert counts["honest_errors_theorems"] == 49


def test_honest_errors_source_inventory_has_49_theorems() -> None:
    root = evidence._SCAN_ROOT / "HonestErrors"
    paths = sorted(root.rglob("*.lean"))
    inventories = [evidence._module_inventory(path, built=True) for path in paths]

    assert len(paths) == 10
    assert sum(len(module["theorems"]) for module in inventories) == 49
    assert all(module["built"] for module in inventories)
    assert {Path(module["source_path"]).name for module in inventories} == {
        "Acceptance.lean",
        "Endpoint.lean",
        "ErrorBudget.lean",
        "Evidence.lean",
        "Arrhenius.lean",
        "Barrier.lean",
        "BarrierToRate.lean",
        "Quadratic.lean",
        "StageGates.lean",
        "Taxonomy.lean",
    }
