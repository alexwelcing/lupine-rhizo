from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "candidates" / "z1_nebdft2k_barriers.lock.json"
SIDECAR = PANEL.with_suffix(PANEL.suffix + ".sha256")
MANIFEST = ROOT / "campaigns" / "v1" / "z1.campaign-manifest.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_z1_panel_is_locked_and_wired_to_campaign() -> None:
    digest = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    assert SIDECAR.read_text(encoding="utf-8").split()[0] == digest

    manifest = load(MANIFEST)
    panel_lock = manifest["execution"]["candidate_panel"]
    assert ROOT / panel_lock["path"] == PANEL
    assert panel_lock["sha256"] == f"sha256:{digest}"

    requirement = next(
        item
        for item in manifest["evidence_requirements"]
        if item["requirement_id"] == "e.z1.held-out-paths"
    )
    assert len(load(PANEL)["paths"]) >= requirement["minimum_count"]


def test_z1_panel_has_30_distinct_chemistry_held_out_dft_neb_paths() -> None:
    panel = load(PANEL)
    paths = panel["paths"]
    path_ids = {path["path_id"] for path in paths}
    chemistries = {path["chemical_system"] for path in paths}

    assert panel["schema"] == "lupine.z1.neb_barrier_panel.v1"
    assert len(paths) == len(path_ids) == len(chemistries) == 30
    assert all(path["split"] == "test" for path in paths)
    assert panel["holdout"]["unit"] == "chemical_system"
    assert set(panel["holdout"]["selected_chemical_systems"]) == chemistries
    assert "excluded" in panel["holdout"]["campaign_fit_exclusion"]
    assert panel["reference_provenance"]["theory"] == "DFT(PBE) climbing-image NEB"
    assert panel["reference_provenance"]["source_archive_sha256"] == (
        "b7a99d89337902e9e1da319f57547170fdb132bf15bf6ffef03a0140e2207d7f"
    )


@pytest.mark.parametrize("path", load(PANEL)["paths"], ids=lambda path: path["path_id"])
def test_z1_path_has_executable_images_and_consistent_reference(path: dict) -> None:
    input_images = path["input_images"]
    reference = path["reference"]
    energies = reference["energies_ev"]
    saddle_index = reference["saddle_image_index"]

    assert len(input_images) == reference["image_count"] >= 3
    assert len(energies) == reference["image_count"]
    assert saddle_index == max(range(len(energies)), key=energies.__getitem__)
    assert path["reference_barrier_ev"] == pytest.approx(max(energies) - min(energies), abs=5e-4)

    for structure in [
        *input_images,
        reference["endpoint_initial"],
        reference["saddle"],
        reference["endpoint_final"],
    ]:
        atom_count = len(structure["symbols"])
        assert atom_count > 0
        assert len(structure["positions_angstrom"]) == atom_count
        assert len(structure["cell_angstrom"]) == 3
        assert all(len(vector) == 3 for vector in structure["cell_angstrom"])
        assert structure["pbc"] == [True, True, True]


def test_z1_execution_protocol_is_frozen() -> None:
    protocol = load(PANEL)["execution_protocol"]
    assert protocol == {
        "barrier_definition": "max(image_energy_ev) - min(image_energy_ev)",
        "climb": True,
        "endpoint_relaxation": True,
        "failure_policy": "record failure without imputation",
        "force_convergence_ev_per_angstrom": 0.1,
        "maximum_steps": 100,
        "method": "climbing-image NEB",
        "optimizer": "FIRE",
        "spring_constant_ev_per_angstrom2": 5.0,
        "tangent_method": "improvedtangent",
    }
