from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "data" / "candidates" / "z2_soc_tc_panel.lock.json"
SIDECAR = PANEL.with_suffix(PANEL.suffix + ".sha256")
PROVENANCE = ROOT / "data" / "candidates" / "z2_soc_tc_panel.provenance.json"
PROVENANCE_SIDECAR = PROVENANCE.with_suffix(PROVENANCE.suffix + ".sha256")
MANIFEST = ROOT / "campaigns" / "v1" / "z2.campaign-manifest.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_z2_panel_is_content_addressed_and_wired_to_campaign() -> None:
    digest = hashlib.sha256(PANEL.read_bytes()).hexdigest()
    assert SIDECAR.read_text(encoding="utf-8").split()[0] == digest
    manifest = load(MANIFEST)
    assert manifest["execution"]["candidate_panel"] == {
        "path": "data/candidates/z2_soc_tc_panel.lock.json",
        "sha256": f"sha256:{digest}",
    }


def test_z2_provenance_manifest_is_locked_and_covers_every_panel_entry() -> None:
    panel = load(PANEL)
    provenance = load(PROVENANCE)
    provenance_digest = hashlib.sha256(PROVENANCE.read_bytes()).hexdigest()
    assert PROVENANCE_SIDECAR.read_text(encoding="utf-8").split()[0] == provenance_digest
    assert provenance["panel"] == {
        "path": "data/candidates/z2_soc_tc_panel.lock.json",
        "sha256": f"sha256:{hashlib.sha256(PANEL.read_bytes()).hexdigest()}",
    }
    assert provenance["source_artifacts"]["supplement"]["doi"] == (
        "10.1103/PhysRevResearch.3.043024"
    )
    assert provenance["source_artifacts"]["supplement"]["locator"] == (
        "Supplemental Table 1"
    )
    assert provenance["source_artifacts"]["c2db_mae_method"]["doi"] == (
        "10.1088/2053-1583/ab2c43"
    )
    entries = provenance["entries"]
    assert {entry["material_id"] for entry in entries} == {
        material["material_id"] for material in panel["materials"]
    }
    for entry in entries:
        assert entry["method_class"] == "published_high_level_theory"
        assert entry["reference_values"]["mca"]["unit"] == "meV/unit_cell"
        assert set(entry["reference_values"]["mca"]["components"]) == {"xz", "yz"}
        assert entry["reference_values"]["tc"]["unit"] == "K"
        assert set(entry["reference_values"]["tc"]["values"]) == {
            "green", "mc", "rnsw"
        }
        assert entry["tc_exchange_source"]["doi"] == "10.1103/PhysRevResearch.3.043024"
        assert entry["tc_exchange_source"]["table"] == "Supplemental Table 1"
        assert entry["mae_source"]["doi"] == "10.1088/2053-1583/ab2c43"
        assert entry["mae_source"]["url"].startswith("https://c2db.fysik.dtu.dk/material/")
        assert entry["mae_source"]["fields"] == [
            "Magnetic anisotropy energy, xz [meV/unit cell]",
            "Magnetic anisotropy energy, yz [meV/unit cell]",
        ]
        assert entry["uncertainty"]["tc_k"]["kind"] == "published_method_envelope"
        assert entry["uncertainty"]["mae_mev_per_cell"] == {
            "confidence_level": None,
            "kind": "source_display_rounding_proxy",
            "physical_error_bar_available": False,
            "plus_minus": 0.0005,
            "scope_note": (
                "Half of the C2DB page's 0.001 meV/unit-cell display increment; this only "
                "bounds transcription rounding and is not a DFT or model-form uncertainty."
            ),
        }
        assert (
            entry["reference_values"]["mca"]["uncertainty"]
            == entry["uncertainty"]["mae_mev_per_cell"]
        )
        assert (
            entry["reference_values"]["tc"]["uncertainty"]
            == entry["uncertainty"]["tc_k"]
        )
        assert entry["extraction_note"]


def test_z2_provenance_discloses_easy_axis_class_limitation() -> None:
    provenance = load(PROVENANCE)
    assert provenance["panel_scope"]["easy_axis_classes"] == ["out_of_plane"]
    assert provenance["panel_scope"]["supports_two_class_discrimination"] is False


def test_z2_panel_has_seven_executable_published_reference_materials() -> None:
    panel = load(PANEL)
    materials = panel["materials"]
    assert panel["schema"] == "lupine.z2.soc_tc_panel.v1"
    assert len(materials) == len({item["material_id"] for item in materials}) == 7
    assert panel["measurement"]["minimum_material_count"] == 5
    assert panel["reference_provenance"]["doi"] == "10.1103/PhysRevResearch.3.043024"
    assert panel["reference_provenance"]["supplement_sha256"] == (
        "sha256:e403103e413d1c240a668bca14d6ec62e1cc3ff117aa8126dc54ab16f2c48b8f"
    )
    assert panel["execution_protocol"] == {
        "exchange_definition": "in-plane AFM-FM split gives J; out-of-plane split gives J+B; delta=B/J",
        "failure_policy": "record failure without imputation",
        "geometry_force_convergence_ev_per_angstrom": 0.05,
        "geometry_maximum_steps": 200,
        "geometry_stage": "MLIP FIRE relaxation under frozen force and step limits",
        "gpaw_convergence_energy_ev": 1e-06,
        "gpaw_fermi_width_ev": 0.05,
        "gpaw_kpoint_density_per_angstrom": 6.0,
        "gpaw_maximum_scf_iterations": 200,
        "gpaw_plane_wave_cutoff_ev": 500.0,
        "soc_axes_degrees": {"x": [90.0, 0.0], "y": [90.0, 90.0], "z": [0.0, 0.0]},
        "soc_method": "GPAW PBE scalar FM/AFM states plus non-selfconsistent force-theorem SOC at x, y, z axes",
        "tc_model": "Tiwari et al. Eq. (3) nearest-neighbour analytical fits",
    }
    for material in materials:
        structure = material["structure"]
        assert len(structure["symbols"]) == len(structure["positions_angstrom"])
        assert len(structure["initial_magmoms"]) == len(structure["symbols"])
        assert structure["pbc"] == [True, True, False]
        assert len(material["magnetic_atom_indices"]) == len(material["afm_signs"]) == 2
        assert material["source_structure"]["sha256"].startswith("sha256:")


def test_z2_references_preserve_published_tc_method_envelope() -> None:
    by_formula = {item["formula"]: item for item in load(PANEL)["materials"]}
    assert by_formula["CrI3"]["reference"]["tc_k"] == {
        "green": 41.3,
        "mc": 30.9,
        "rnsw": 21.4,
    }
    assert by_formula["Fe2F2"]["reference"]["tc_k"] == {
        "green": 726.4,
        "mc": 962.3,
        "rnsw": 486.7,
    }
    for material in by_formula.values():
        tc_values = list(material["reference"]["tc_k"].values())
        assert material["reference"]["tc_envelope_k"] == [min(tc_values), max(tc_values)]
        assert material["reference"]["uncertainty"] == {
            "kind": "published_method_envelope",
            "lower_k": min(tc_values),
            "upper_k": max(tc_values),
            "statistical_error_bar_available": False,
        }


@pytest.mark.parametrize(
    ("formula", "exchange_mev", "delta", "mae_xz"),
    [
        ("Fe2F2", 67.47603, 0.000811, -1.332),
        ("CrI3", 2.048469, 0.068308, -1.708),
        ("CrBr3", 1.932402, 0.0162, -0.419),
        ("CrCl3", 1.388498, 0.001722, -0.065),
        ("W2S4", 17.16775, 0.165444, -33.793),
        ("V2Te4", 43.92472, 0.016081, -4.365),
        ("Co2Br6", 21.1372, 0.036505, -8.598),
    ],
)
def test_z2_reference_values_are_frozen(
    formula: str, exchange_mev: float, delta: float, mae_xz: float
) -> None:
    material = next(item for item in load(PANEL)["materials"] if item["formula"] == formula)
    assert material["reference"]["exchange_mev"] == exchange_mev
    assert material["reference"]["exchange_anisotropy"] == delta
    assert material["reference"]["mae_xz_mev_per_cell"] == mae_xz
