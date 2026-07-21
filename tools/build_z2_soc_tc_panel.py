#!/usr/bin/env python3
"""Build the locked Z2 SOC/Tc panel from published C2DB references."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from ase.io import read

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = Path("/tmp/z2-c2db")
DEFAULT_OUTPUT = ROOT / "data" / "candidates" / "z2_soc_tc_panel.lock.json"
SUPPLEMENT_URL = (
    "https://journals.aps.org/prresearch/supplement/10.1103/PhysRevResearch.3.043024/"
    "Supplementary-document.pdf"
)
SUPPLEMENT_SHA256 = "e403103e413d1c240a668bca14d6ec62e1cc3ff117aa8126dc54ab16f2c48b8f"
DOI = "10.1103/PhysRevResearch.3.043024"

# J, Δ, and Tc are transcribed from published Supplemental Table 1. MAE xz/yz
# is the C2DB PBE force-theorem reference attached to the mapped current UID.
REFERENCES: tuple[dict[str, Any], ...] = (
    {
        "formula": "Fe2F2", "old_id": "F2Fe2-3c50b5e0d85d", "uid": "2FFe-2",
        "xyz_sha256": "f04884703978fd6e09fbca26206e7fe8a217ece87c2ca10d51abeb53f09d7a66",
        "magnetic_atom_indices": [2, 3], "exchange_mev": 67.47603, "delta": 0.000811,
        "spin": 1.5, "neighbors": 4, "mae_xz": -1.332, "mae_yz": -1.332,
        "tc": {"green": 726.4, "mc": 962.3, "rnsw": 486.7},
    },
    {
        "formula": "CrI3", "old_id": "Cr2I6-462e253dd5f0", "uid": "2CrI3-1",
        "xyz_sha256": "8bcdce59b207dce2adfb856d581355d9946da1d459e30b36c42dac982a11f4dd",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 2.048469, "delta": 0.068308,
        "spin": 1.5, "neighbors": 3, "mae_xz": -1.708, "mae_yz": -1.705,
        "tc": {"green": 41.3, "mc": 30.9, "rnsw": 21.4},
    },
    {
        "formula": "CrBr3", "old_id": "Cr2Br6-e406fd4547de", "uid": "2CrBr3-1",
        "xyz_sha256": "95344e04e7660ee528804dfd2228b16029379688f4d497fc4f3aaefa0804c997",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 1.932402, "delta": 0.0162,
        "spin": 1.5, "neighbors": 3, "mae_xz": -0.419, "mae_yz": -0.419,
        "tc": {"green": 26.0, "mc": 23.7, "rnsw": 14.1},
    },
    {
        "formula": "CrCl3", "old_id": "Cr2Cl6-9f9e75488d50", "uid": "2CrCl3-1",
        "xyz_sha256": "22e969a7d61cf756db97390e46e9e30c3b66404cf0408db245c05dbb0b724380",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 1.388498, "delta": 0.001722,
        "spin": 1.5, "neighbors": 3, "mae_xz": -0.065, "mae_yz": -0.065,
        "tc": {"green": 12.3, "mc": 13.2, "rnsw": 6.9},
    },
    {
        "formula": "W2S4", "old_id": "W2S4-0728bb0ff0b4", "uid": "2WS2-2",
        "xyz_sha256": "aa83ca1ce2e24a57f29cc3c11ca930d33b8d1ccfa73e013fefefddf43bff7ba6",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 17.16775, "delta": 0.165444,
        "spin": 1.0, "neighbors": 4, "mae_xz": -33.793, "mae_yz": -34.028,
        "tc": {"green": 260.7, "mc": 195.9, "rnsw": 182.6},
    },
    {
        "formula": "V2Te4", "old_id": "V2Te4-31bf29ee1828", "uid": "2VTe2-3",
        "xyz_sha256": "6508d8cbaedce53eee65674b75159e567824df9309eed1f50d0cd5e9a65cfc24",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 43.92472, "delta": 0.016081,
        "spin": 1.0, "neighbors": 4, "mae_xz": -4.365, "mae_yz": -4.357,
        "tc": {"green": 387.6, "mc": 371.1, "rnsw": 263.4},
    },
    {
        "formula": "Co2Br6", "old_id": "Co2Br6-26f91951e231", "uid": "2CoBr3-2",
        "xyz_sha256": "0465926a4c5ff22d742a2349c7c279fcffa8cf4a4cc7bbe607066feb47642b94",
        "magnetic_atom_indices": [0, 1], "exchange_mev": 21.1372, "delta": 0.036505,
        "spin": 1.5, "neighbors": 3, "mae_xz": -8.598, "mae_yz": -8.591,
        "tc": {"green": 349.7, "mc": 290.1, "rnsw": 185.6},
    },
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def acquire_xyz(source_dir: Path, record: dict[str, Any]) -> Path:
    source_dir.mkdir(parents=True, exist_ok=True)
    path = source_dir / f"{record['uid']}.xyz"
    if not path.exists():
        urllib.request.urlretrieve(
            f"https://c2db.fysik.dtu.dk/material/{record['uid']}/download/xyz", path
        )
    actual = sha256_file(path)
    if actual != record["xyz_sha256"]:
        raise ValueError(
            f"C2DB structure digest mismatch for {record['uid']}: "
            f"expected {record['xyz_sha256']}, got {actual}"
        )
    return path


def structure_record(path: Path) -> dict[str, Any]:
    atoms = read(path, format="extxyz")
    magmoms = atoms.get_initial_magnetic_moments()
    return {
        "symbols": atoms.get_chemical_symbols(),
        "positions_angstrom": atoms.positions.tolist(),
        "cell_angstrom": atoms.cell.array.tolist(),
        "pbc": [bool(value) for value in atoms.pbc],
        "initial_magmoms": magmoms.tolist(),
    }


def material_record(source_dir: Path, source: dict[str, Any]) -> dict[str, Any]:
    tc = source["tc"]
    lower, upper = min(tc.values()), max(tc.values())
    uid = source["uid"]
    return {
        "material_id": source["old_id"],
        "formula": source["formula"],
        "c2db_uid": uid,
        "lattice": {3: "honeycomb", 4: "square", 6: "hexagonal"}[source["neighbors"]],
        "spin": source["spin"],
        "nearest_neighbors": source["neighbors"],
        "magnetic_atom_indices": source["magnetic_atom_indices"],
        "afm_signs": [1, -1],
        "source_structure": {
            "url": f"https://c2db.fysik.dtu.dk/material/{uid}/download/xyz",
            "sha256": f"sha256:{source['xyz_sha256']}",
        },
        "structure": structure_record(acquire_xyz(source_dir, source)),
        "reference": {
            "exchange_mev": source["exchange_mev"],
            "exchange_anisotropy": source["delta"],
            "mae_xz_mev_per_cell": source["mae_xz"],
            "mae_yz_mev_per_cell": source["mae_yz"],
            "tc_k": tc,
            "tc_envelope_k": [lower, upper],
            "uncertainty": {
                "kind": "published_method_envelope",
                "lower_k": lower,
                "upper_k": upper,
                "statistical_error_bar_available": False,
            },
        },
    }


def build(source_dir: Path) -> dict[str, Any]:
    return {
        "schema": "lupine.z2.soc_tc_panel.v1",
        "panel_id": "z2-tiwari-c2db-soc-tc-v1",
        "locked_at": "2026-07-21T00:00:00Z",
        "measurement": {
            "primary_metric": "magnetocrystalline_anisotropy_rank_correlation",
            "secondary_metrics": ["easy_axis_sign_errors", "tc_rnsw_mae_k", "tc_envelope_coverage"],
            "minimum_material_count": 5,
        },
        "holdout": {
            "selection_rule": "Seven materials with verified old-ID to current-C2DB structure mappings, spanning honeycomb and square magnetic lattices, selected before runner execution.",
            "campaign_fit_exclusion": "All seven materials are excluded from Z2-specific fitting, threshold tuning, and model selection.",
        },
        "reference_provenance": {
            "article": "Computing Curie temperature of two-dimensional ferromagnets in the presence of exchange anisotropy",
            "authors": "Tiwari et al.",
            "doi": DOI,
            "supplement_url": SUPPLEMENT_URL,
            "supplement_sha256": f"sha256:{SUPPLEMENT_SHA256}",
            "supplement_table": "Supplemental Table 1",
            "c2db": "https://c2db.fysik.dtu.dk/",
            "c2db_mae_method": "PBE non-selfconsistent spin-orbit force theorem with magnetic field aligned x, y, and z",
            "limitations": [
                "Published Tc values have no statistical error bars; the Green/MC/RNSW spread is retained as a method envelope.",
                "The Tc fit is a nearest-neighbour Heisenberg model and omits long-range interactions.",
                "Fe2F2 is metallic and the source article labels its Tc a rough first-level estimate.",
                "The article body quotes a conservative Fe2F2 Tc of 403 K while Supplemental Table 1 reports RNSW 486.7 K; this panel preserves the table value without reconciliation.",
                "C2DB is mutable; exact downloaded structure bytes and the derived panel bytes are SHA-256 locked.",
            ],
        },
        "execution_protocol": {
            "geometry_stage": "MLIP FIRE relaxation under frozen force and step limits",
            "geometry_force_convergence_ev_per_angstrom": 0.05,
            "geometry_maximum_steps": 200,
            "soc_method": "GPAW PBE scalar FM/AFM states plus non-selfconsistent force-theorem SOC at x, y, z axes",
            "soc_axes_degrees": {
                "x": [90.0, 0.0],
                "y": [90.0, 90.0],
                "z": [0.0, 0.0],
            },
            "gpaw_plane_wave_cutoff_ev": 500.0,
            "gpaw_kpoint_density_per_angstrom": 6.0,
            "gpaw_fermi_width_ev": 0.05,
            "gpaw_convergence_energy_ev": 1e-6,
            "gpaw_maximum_scf_iterations": 200,
            "tc_model": "Tiwari et al. Eq. (3) nearest-neighbour analytical fits",
            "exchange_definition": "in-plane AFM-FM split gives J; out-of-plane split gives J+B; delta=B/J",
            "failure_policy": "record failure without imputation",
        },
        "materials": [material_record(source_dir, source) for source in REFERENCES],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    panel = build(args.source_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(panel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(args.output)
    sidecar = args.output.with_suffix(args.output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(f"wrote {len(panel['materials'])} materials to {args.output} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
