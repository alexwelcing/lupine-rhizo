from __future__ import annotations

from pathlib import Path

import build_lean_evidence as evidence

_FROZEN_VISION_HONEST_ERRORS_SOURCES = {
    Path("Acceptance.lean"),
    Path("Endpoint.lean"),
    Path("ErrorBudget.lean"),
    Path("Evidence.lean"),
    Path("Kinetics/Arrhenius.lean"),
    Path("Response/Barrier.lean"),
    Path("Response/BarrierToRate.lean"),
    Path("Response/Quadratic.lean"),
    Path("StageGates.lean"),
    Path("Taxonomy.lean"),
}
_EXPLORATORY_HONEST_ERRORS_SOURCES = {Path("CorrectionBoundary.lean")}


def test_vision_tracks_49_frozen_honest_errors_contract_declarations() -> None:
    counts = evidence._vision_counts()

    assert counts == evidence.EXPECTED_VISION
    assert counts["honest_errors_theorems"] == 49


def test_frozen_vision_honest_errors_inventory_has_49_declarations() -> None:
    root = evidence._SCAN_ROOT / "HonestErrors"
    paths = sorted(root / path for path in _FROZEN_VISION_HONEST_ERRORS_SOURCES)
    inventories = [evidence._module_inventory(path, built=True) for path in paths]

    assert len(paths) == 10
    assert sum(len(module["theorems"]) for module in inventories) == 49
    assert all(module["built"] for module in inventories)


def test_complete_honest_errors_source_inventory_has_79_declarations() -> None:
    """The 49 Vision contracts exclude 30 exploratory declarations by design."""
    root = evidence._SCAN_ROOT / "HonestErrors"
    paths = sorted(root.rglob("*.lean"))
    relative_paths = {path.relative_to(root) for path in paths}
    inventories = [evidence._module_inventory(path, built=True) for path in paths]

    assert relative_paths == (
        _FROZEN_VISION_HONEST_ERRORS_SOURCES | _EXPLORATORY_HONEST_ERRORS_SOURCES
    )
    assert len(paths) == 11
    assert sum(len(module["theorems"]) for module in inventories) == 79
    assert all(module["built"] for module in inventories)

    exploratory_inventories = [
        evidence._module_inventory(root / path, built=True)
        for path in _EXPLORATORY_HONEST_ERRORS_SOURCES
    ]
    assert sum(len(module["theorems"]) for module in exploratory_inventories) == 30
