from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from lupine_distill.fixture_contract import run_row, validate_manifest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from ingest_campaign_results import (  # pyright: ignore[reportMissingImports]  # noqa: E402
    allowed_scope,
    validate_scope_compatibility,
)

PANEL = ROOT / "data" / "candidates" / "z3_catbench_bm_adsorption.lock.json"
SPLIT = ROOT / "data" / "candidates" / "z3_catbench_bm_delta_splits.lock.json"
CHECKPOINT = (
    ROOT / "data" / "candidates" / "z3_catbench_bm_delta_checkpoint.fixture.json"
)
MANIFEST = ROOT / "campaigns" / "v1" / "z3.campaign-manifest.v1.json"
CLAIM = ROOT / "registry" / "claims" / "discovery.z3.adsorption-accuracy.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_sidecar(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    assert sidecar.read_text(encoding="utf-8") == f"{digest}  {path.name}\n"
    return digest


def candidate_fixture(candidate: dict, panel: dict) -> dict:
    return {
        "schema": "lupine.mlip.fixture_manifest.v2",
        "fixture_id": f"{panel['panel_id']}:{candidate['candidate_id']}",
        "manifest_hash": "sha256:test-derived-from-locked-panel",
        "reference_provenance": panel["reference_provenance"],
        "row_specs": {
            "adsorption_energy": {
                "min_cases": 1,
                "max_cases": 1,
                "error_tolerance": 0.1,
                "error_unit": "eV",
            }
        },
        "row_fixtures": {"adsorption_energy": {"structures": [candidate]}},
    }


class AtomCountEnergyCalculator(Calculator):
    implemented_properties = ["energy"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        if atoms is None:
            raise ValueError("atoms are required")
        atom_count = len(atoms)
        self.results = {"energy": -float(atom_count), "forces": np.zeros((atom_count, 3))}


def test_z3_panel_and_delta_fixtures_are_locked_and_wired() -> None:
    panel_digest = assert_sidecar(PANEL)
    assert_sidecar(SPLIT)
    assert_sidecar(CHECKPOINT)

    manifest = load(MANIFEST)
    panel_lock = manifest["execution"]["candidate_panel"]
    assert ROOT / panel_lock["path"] == PANEL
    assert panel_lock["sha256"] == f"sha256:{panel_digest}"

    requirement = next(
        item
        for item in manifest["evidence_requirements"]
        if item["requirement_id"] == "e.z3.published-dft-references"
    )
    panel = load(PANEL)
    confirmatory = [
        candidate for candidate in panel["candidates"] if candidate["split"] == "confirmatory_test"
    ]
    assert len(confirmatory) >= requirement["minimum_count"] == 20

    claim = load(CLAIM)
    target = manifest["target_premises"][0]
    assert target["claim_id"] == claim["claim_id"]
    premise = next(item for item in claim["premises"] if item["premise_id"] == target["premise_id"])
    assert "published DFT references" in premise["statement"]
    assert "experimental references" not in premise["statement"]


def test_z3_measurement_scopes_pass_baseline_ingestion_gates() -> None:
    panel = load(PANEL)
    manifest = load(MANIFEST)
    claim = load(CLAIM)
    target = manifest["target_premises"][0]
    premise = next(item for item in claim["premises"] if item["premise_id"] == target["premise_id"])

    assert target == {
        "claim_id": "discovery.z3.adsorption-accuracy.v1",
        "premise_id": "hard_materials_z3_adsorption_mae",
    }
    allowed, predicates = allowed_scope(ROOT, premise)
    assert predicates == {"adsorption_energy_mae<=0.1"}
    assert allowed == {
        "structures": {candidate["structure_id"] for candidate in panel["candidates"]},
        "chemistries": {
            system["system_id"]
            for candidate in panel["candidates"]
            for system in candidate["systems"]
        },
        "properties": {"adsorption_energy"},
    }

    for candidate in panel["candidates"]:
        validate_scope_compatibility(
            {
                "structures": [candidate["structure_id"]],
                "chemistries": [system["system_id"] for system in candidate["systems"]],
                "properties": ["adsorption_energy"],
                "conditions": {"candidate_id": candidate["candidate_id"]},
            },
            allowed,
            target["claim_id"],
            target["premise_id"],
        )


def test_z3_panel_has_honest_published_dft_provenance_and_frozen_splits() -> None:
    panel = load(PANEL)
    provenance = panel["reference_provenance"]
    candidates = panel["candidates"]

    assert panel["schema"] == "lupine.z3.adsorption_reference_panel.v1"
    assert len(candidates) == len({candidate["candidate_id"] for candidate in candidates}) == 32
    assert provenance["dataset_doi"] == "10.5281/zenodo.17157086"
    assert provenance["original_publication_doi"] == "10.1038/s43588-023-00437-y"
    assert provenance["source_artifact_sha256"] == (
        "72d44b03c53b4262f3bb5b69d960b33f53a2cfb243416b44a9755dfbe0f6d100"
    )
    assert provenance["license"] == "CC BY 4.0"
    assert provenance["theory"] == "VASP 5.4.4 DFT(PBE) with D2 reparameterized for metals"
    assert "not assert" in panel["holdout"]["scope_note"]
    assert Counter(candidate["split"] for candidate in candidates) == Counter(
        {"delta_train": 6, "delta_validation": 6, "confirmatory_test": 20}
    )

    split_lock = load(SPLIT)
    assert split_lock["panel_id"] == panel["panel_id"]
    assert {
        split: set(candidate_ids) for split, candidate_ids in split_lock["splits"].items()
    } == {
        split: {
            candidate["candidate_id"] for candidate in candidates if candidate["split"] == split
        }
        for split in ("delta_train", "delta_validation", "confirmatory_test")
    }
    all_split_ids = [candidate_id for ids in split_lock["splits"].values() for candidate_id in ids]
    assert len(all_split_ids) == len(set(all_split_ids)) == 32

    checkpoint = load(CHECKPOINT)
    assert checkpoint["state"] == "unfitted_fixture"
    assert checkpoint["panel_id"] == panel["panel_id"]
    assert checkpoint["required_payload"]["correction_model"] is None
    assert set(checkpoint["required_payload"]["fit_candidate_ids"]) == set(
        split_lock["splits"]["delta_train"]
    )
    assert set(checkpoint["required_payload"]["confirmatory_candidate_ids"]) == set(
        split_lock["splits"]["confirmatory_test"]
    )
    assert any("Do not read confirmatory_test" in rule for rule in checkpoint["rules"])


@pytest.mark.parametrize(
    "candidate",
    load(PANEL)["candidates"],
    ids=lambda candidate: candidate["candidate_id"],
)
def test_z3_candidate_is_executable_balanced_and_condition_scoped(candidate: dict) -> None:
    panel = load(PANEL)
    validation = validate_manifest(candidate_fixture(candidate, panel))
    assert validation["release_ready"] is True, validation["blockers"]
    assert validation["row_blockers"]["adsorption_energy"] == []

    assert candidate["role_counts"] == {
        "adsorbate_slab": 1,
        "clean_slab": 1,
        "reference": 1,
    }
    assert candidate["stoichiometry"] == {"element_balanced": True, "residual": {}}
    assert candidate["surface_facet"] in {"fcc(111)", "hcp(0001)"}
    conditions = candidate["conditions"]
    assert conditions["temperature"]["value_k"] == 0.0
    assert "no vibrational" in conditions["temperature"]["interpretation"]
    assert conditions["coverage"]["adsorbates_per_periodic_cell"] == 1
    assert conditions["coverage"]["surface_cell_area_angstrom2"] > 0
    assert conditions["coverage"]["molecules_per_square_nanometer"] > 0
    assert "reconstruction label is published" in conditions["surface_state"]
    assert "not published" in conditions["adsorption_site"]

    reference = candidate["reference"]
    assert math.isfinite(reference["adsorption_energy_ev"])
    assert reference["uncertainty_ev"] == pytest.approx(3e-5)
    assert reference["confidence_level"] is None
    assert "not a statistical interval" in reference["scope_note"]
    reaction_sum = math.fsum(
        system["stoichiometric_coefficient"] * system["reference_total_energy_ev"]
        for system in candidate["systems"]
    )
    assert reference["adsorption_energy_ev"] == pytest.approx(reaction_sum, abs=5e-8)

    for system in candidate["systems"]:
        atom_count = len(system["symbols"])
        assert atom_count > 0
        assert len(system["positions"]) == atom_count
        assert len(system["cell"]) == 3
        assert all(len(vector) == 3 for vector in system["cell"])
        assert len(system["pbc"]) == 3


def test_z3_panel_aggregate_metadata_matches_rows() -> None:
    panel = load(PANEL)
    candidates = panel["candidates"]
    aggregate = panel["aggregate_metadata"]
    assert aggregate["candidate_count"] == len(candidates) == 32
    assert aggregate["role_counts"] == {
        "adsorbate_slab": 32,
        "clean_slab": 32,
        "reference": 32,
    }
    assert aggregate["surface_counts"] == dict(
        sorted(Counter(candidate["surface_element"] for candidate in candidates).items())
    )
    assert aggregate["application_counts"] == {
        "biomass": 10,
        "plastics": 7,
        "polyurethanes": 15,
    }


def test_z3_candidate_executes_through_adsorption_runner_contract() -> None:
    panel = load(PANEL)
    candidate = panel["candidates"][0]
    fixture = candidate_fixture(candidate, panel)
    assert validate_manifest(fixture)["release_ready"] is True

    result = run_row("adsorption_energy", fixture, AtomCountEnergyCalculator())

    assert result["n_structures"] == 1
    assert result["fixture_contract"]["release_ready"] is True
    assert len(result["predictions"]) == 1
    prediction = result["predictions"][0]
    # Atom-count energy cancels exactly because the source reaction is element balanced.
    assert prediction["adsorption_energy_ev"] == pytest.approx(0.0)
    assert result["metrics"]["adsorption_energy_mae"] == pytest.approx(
        abs(candidate["reference"]["adsorption_energy_ev"])
    )
