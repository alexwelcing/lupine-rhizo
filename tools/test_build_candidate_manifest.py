"""Unit tests for tools/build_candidate_manifest.py (P1 cloud promotion).

The builder must emit a `lupine.mlip.fixture_manifest.v2` manifest that the
cell-runner's fail-closed fixture contract (`lupine_distill.fixture_contract`)
accepts end to end: `validate_manifest` reports `release_ready` and `run_row`
completes on CPU with a synthetic zero calculator for both populated rows.

Configuration is pinned to the local Round-1 campaign (seed 20260713,
3x3x3 fcc RSS supercell, +/-0.5% strains) per
docs/promotion/2026-07-13-six-model-promotion-packet.md section 3.1.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from lupine_distill.fixture_contract import run_row, validate_manifest

import build_candidate_manifest as bcm

pytestmark = pytest.mark.unit

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGETS_PATH = REPO_ROOT / "data" / "candidates" / "round1_targets.json"

EXPECTED_ELASTIC_CANDIDATES = {
    "hea-cocrni",
    "hp-cssncl3",
    "hp-cssnbr3",
    "hp-cssni3",
    "hp-csgei3",
    "hp-cspbi3-control",
}
EXPECTED_ALL_CANDIDATES = EXPECTED_ELASTIC_CANDIDATES | {
    "hea-cocrfeni",
    "hea-coni",
    "hea-feni",
}


class ZeroCalculator(Calculator):
    """Deterministic CPU stand-in: zero energy/forces/stress everywhere."""

    implemented_properties = ["energy", "forces", "stress"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        n = len(atoms)
        self.results = {
            "energy": 0.0,
            "forces": np.zeros((n, 3)),
            "stress": np.zeros(6),
        }


@pytest.fixture(scope="module")
def targets() -> dict:
    return bcm.load_targets(TARGETS_PATH)


@pytest.fixture(scope="module")
def manifest(targets: dict) -> dict:
    return bcm.build_manifest(targets)


def test_targets_file_is_the_frozen_round1_set(targets: dict) -> None:
    assert targets["schema"] == "lupine.campaign_targets.v1"
    assert {c["id"] for c in targets["candidates"]} == EXPECTED_ALL_CANDIDATES


def test_manifest_is_release_ready_for_the_cell_runner(manifest: dict) -> None:
    validation = validate_manifest(manifest)
    assert validation["blockers"] == []
    assert validation["release_ready"] is True
    assert validation["fixture_id"] == bcm.FIXTURE_ID
    assert manifest["schema"] == "lupine.mlip.fixture_manifest.v2"


def test_elastic_row_covers_the_six_cij_candidates(manifest: dict) -> None:
    cases = manifest["row_fixtures"]["elastic_constants"]["structures"]
    by_material: dict[str, list[dict]] = {}
    for case in cases:
        by_material.setdefault(case["material_id"], []).append(case)
    assert set(by_material) == EXPECTED_ELASTIC_CANDIDATES
    for material_id, group in by_material.items():
        # zero strain + (pos, neg) for each of the 6 Voigt modes
        assert len(group) == 13, material_id
        strains = np.asarray([case["strain_voigt"] for case in group], dtype=float)
        assert np.isclose(np.abs(strains).max(), bcm.STRAIN_DELTA)
        assert any(np.allclose(row, 0.0) for row in strains)
        for case in group:
            ref = case["reference"]["elastic_constants_gpa"]
            assert set(ref) <= {"C11", "C12", "C44"}
            assert all(isinstance(v, float) for v in ref.values())


def test_elastic_cases_apply_the_strain_to_the_cell(manifest: dict) -> None:
    cases = [
        case
        for case in manifest["row_fixtures"]["elastic_constants"]["structures"]
        if case["material_id"] == "hp-cssnbr3"
    ]
    zero = next(c for c in cases if np.allclose(c["strain_voigt"], 0.0))
    assert np.allclose(np.asarray(zero["cell"]), np.eye(3) * 5.8)
    mode1 = next(
        c for c in cases if np.allclose(c["strain_voigt"], [bcm.STRAIN_DELTA, 0, 0, 0, 0, 0])
    )
    assert np.isclose(np.asarray(mode1["cell"])[0, 0], 5.8 * (1.0 + bcm.STRAIN_DELTA))


def test_rss_supercell_is_seed_20260713_and_108_atoms(manifest: dict) -> None:
    cases = [
        case
        for case in manifest["row_fixtures"]["elastic_constants"]["structures"]
        if case["material_id"] == "hea-cocrni"
    ]
    symbols = cases[0]["symbols"]
    assert len(symbols) == 108
    assert {s: symbols.count(s) for s in ("Co", "Cr", "Ni")} == {
        "Co": 36,
        "Cr": 36,
        "Ni": 36,
    }
    from lupine_distill.statics import build_rss_supercell

    expected = build_rss_supercell(
        {"Co": 1, "Cr": 1, "Ni": 1}, "fcc", 3.56, bcm.RSS_REPEAT, bcm.RSS_SEED
    )
    assert symbols == expected.get_chemical_symbols()


def test_relaxation_row_covers_all_nine_candidates_perturbed(manifest: dict) -> None:
    cases = manifest["row_fixtures"]["relaxation_stability"]["structures"]
    assert {case["material_id"] for case in cases} == EXPECTED_ALL_CANDIDATES
    assert len(cases) == 9
    for case in cases:
        assert case["reference"]["relaxation_force_threshold"] == bcm.FORCE_THRESHOLD
        perturbation = case["metadata"]["perturbation"]
        assert perturbation["stdev_angstrom"] == bcm.RATTLE_STDEV
        # perturbed starts must not sit on the ideal lattice
        assert perturbation["max_displacement_angstrom"] > 0.0


def test_provenance_is_copied_verbatim_from_targets(manifest: dict, targets: dict) -> None:
    per_candidate = manifest["reference_provenance"]["round1_targets"]["per_candidate"]
    assert set(per_candidate) == EXPECTED_ALL_CANDIDATES
    for candidate in targets["candidates"]:
        assert per_candidate[candidate["id"]]["references"] == candidate["references"]


def test_unused_rows_are_explicitly_emptied_not_defaulted(manifest: dict) -> None:
    for row_id in ("energy_volume", "forces", "stress"):
        assert row_id not in manifest["row_fixtures"]
        assert manifest["row_specs"][row_id]["min_cases"] == 0


def test_manifest_build_is_deterministic(targets: dict, manifest: dict) -> None:
    again = bcm.build_manifest(targets)
    assert again["manifest_hash"] == manifest["manifest_hash"]
    assert json.dumps(again, sort_keys=True) == json.dumps(manifest, sort_keys=True)


def test_run_row_completes_on_cpu_for_both_populated_rows(manifest: dict) -> None:
    elastic = run_row("elastic_constants", manifest, ZeroCalculator())
    assert elastic["n_structures"] == 78
    assert elastic["metrics"]["primary_metric"] == "elastic_cij_mae_gpa"
    assert set(elastic["metrics"]["elastic_constants_gpa_by_material"]) == (
        EXPECTED_ELASTIC_CANDIDATES
    )

    relaxation = run_row("relaxation_stability", manifest, ZeroCalculator())
    assert relaxation["n_structures"] == 9
    assert relaxation["metrics"]["convergence_rate"] == 1.0
