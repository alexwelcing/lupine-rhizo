from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "data" / "candidates" / "round4_targets.lock.json"
SIDECAR = LOCK.with_suffix(LOCK.suffix + ".sha256")


def _thresholds() -> dict:
    return json.loads(
        (ROOT / "data" / "discovery_gates" / "thresholds.v3.json").read_text()
    )


def _materials_from_thresholds() -> set[str]:
    artifact = _thresholds()
    materials: set[str] = set()
    for class_data in artifact["per_class"].values():
        for property_data in class_data["per_property"].values():
            materials.update(name for name, _value in property_data["sample_dispersions"])
    return materials


def _prior_candidates() -> set[str]:
    materials: set[str] = set()
    for name in ("round1_targets.json", "round3_targets.json"):
        artifact = json.loads((ROOT / "data" / "candidates" / name).read_text())
        materials.update(candidate["formula"] for candidate in artifact["candidates"])
    return materials


def test_round4_lock_is_reference_blind_and_out_of_sample() -> None:
    lock = json.loads(LOCK.read_text())
    candidates = [
        candidate
        for class_data in lock["classes"]
        for candidate in class_data["candidates"]
    ]
    formulas = {candidate["formula"] for candidate in candidates}
    class_ids = {class_data["id"] for class_data in lock["classes"]}

    assert len(lock["classes"]) >= 2
    assert class_ids <= set(_thresholds()["per_class"])
    assert len(candidates) == len(formulas)
    assert formulas.isdisjoint(_materials_from_thresholds())
    assert formulas.isdisjoint(_prior_candidates())
    assert lock["reference_blind"] is True
    assert lock["reference_fields_present"] is False
    assert all(
        set(candidate) == {"id", "formula", "composition"}
        for candidate in candidates
    )
    assert lock["model_set"] == [
        "chgnet",
        "mace-mp-small",
        "mace-mp-medium",
        "mace-mpa-0-medium",
    ]


def test_round4_lock_digest_matches_sidecar() -> None:
    expected = SIDECAR.read_text().split()[0]
    assert hashlib.sha256(LOCK.read_bytes()).hexdigest() == expected
