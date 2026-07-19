#!/usr/bin/env python3
"""Build the locked Z3 adsorption panel from the published CatBench BM dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from ase.data import chemical_symbols
from ase.io.jsonio import decode

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "candidates" / "z3_catbench_bm_adsorption.lock.json"
DEFAULT_SPLIT_OUTPUT = ROOT / "data" / "candidates" / "z3_catbench_bm_delta_splits.lock.json"
DEFAULT_CHECKPOINT_OUTPUT = (
    ROOT / "data" / "candidates" / "z3_catbench_bm_delta_checkpoint.fixture.json"
)
SOURCE_URL = (
    "https://zenodo.org/api/records/17157086/files/BM_dataset_adsorption.json/content"
)
SOURCE_SHA256 = "72d44b03c53b4262f3bb5b69d960b33f53a2cfb243416b44a9755dfbe0f6d100"
SOURCE_MD5 = "ef2d57ef9f92047dec62c3222c33aeb6"
SOURCE_DOI = "10.5281/zenodo.17157086"
ORIGINAL_DOI = "10.1038/s43588-023-00437-y"
PANEL_ID = "z3-catbench-bm-published-dft-v1"
LOCKED_AT = "2026-07-19T00:00:00Z"
DFT_ENERGY_CONVERGENCE_EV = 1e-5
SURFACE_FACETS = {
    "Ag": "fcc(111)",
    "Au": "fcc(111)",
    "Cu": "fcc(111)",
    "Ni": "fcc(111)",
    "Pt": "fcc(111)",
    "Ru": "hcp(0001)",
}
REGISTERED_MODELS = (
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
)
SPLIT_NAMES = ("delta_train", "delta_validation", "confirmatory_test")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire(source: Path) -> None:
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        with urllib.request.urlopen(SOURCE_URL, timeout=120) as response, source.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
    actual = sha256_file(source)
    if actual != SOURCE_SHA256:
        raise ValueError(
            f"CatBench BM source digest mismatch: expected {SOURCE_SHA256}, got {actual}"
        )


def source_structure(atoms_json: str) -> dict[str, Any]:
    decoded = decode(atoms_json)
    records = [value for key, value in decoded.items() if isinstance(key, int)]
    if len(records) != 1:
        raise ValueError(f"expected one ASE row in atoms_json, found {len(records)}")
    record = records[0]
    numbers = np.asarray(record["numbers"], dtype=int)
    return {
        "symbols": [chemical_symbols[int(number)] for number in numbers],
        "positions": np.asarray(record["positions"], dtype=float).tolist(),
        "cell": np.asarray(record["cell"], dtype=float).tolist(),
        "pbc": [bool(value) for value in np.asarray(record["pbc"], dtype=bool)],
    }


def formula(symbols: list[str]) -> str:
    counts = Counter(symbols)
    order: list[str] = []
    if "C" in counts:
        order.append("C")
    if "H" in counts:
        order.append("H")
    order.extend(sorted(symbol for symbol in counts if symbol not in {"C", "H"}))
    return "".join(symbol + (str(counts[symbol]) if counts[symbol] != 1 else "") for symbol in order)


def surface_area_angstrom2(cell: list[list[float]]) -> float:
    return float(np.linalg.norm(np.cross(np.asarray(cell[0]), np.asarray(cell[1]))))


def application(candidate_id: str) -> str:
    prefix = candidate_id.split("_", 1)[0]
    if prefix not in {"biomass", "plastics", "polyurethanes"}:
        raise ValueError(f"unsupported BM application prefix: {prefix}")
    return prefix


def split_assignments(candidate_ids: list[str]) -> dict[str, str]:
    """Freeze a family-stratified, identifier-hash-ordered 6/6/20 split."""
    assignments: dict[str, str] = {}
    by_application: dict[str, list[str]] = {}
    for candidate_id in candidate_ids:
        by_application.setdefault(application(candidate_id), []).append(candidate_id)
    for family in sorted(by_application):
        ordered = sorted(
            by_application[family],
            key=lambda candidate_id: (hashlib.sha256(candidate_id.encode()).hexdigest(), candidate_id),
        )
        if len(ordered) < 5:
            raise ValueError(f"{family} has too few candidates for a 2/2/test split")
        for candidate_id in ordered[:2]:
            assignments[candidate_id] = "delta_train"
        for candidate_id in ordered[2:4]:
            assignments[candidate_id] = "delta_validation"
        for candidate_id in ordered[4:]:
            assignments[candidate_id] = "confirmatory_test"
    counts = Counter(assignments.values())
    if counts != Counter({"delta_train": 6, "delta_validation": 6, "confirmatory_test": 20}):
        raise ValueError(f"unexpected split counts: {dict(counts)}")
    return assignments


def role_for(source_key: str, coefficient: float) -> str:
    if coefficient > 0:
        return "adsorbate_slab"
    if source_key == "star":
        return "clean_slab"
    if source_key.lower().endswith("gas"):
        return "reference"
    raise ValueError(f"cannot assign a runner role to source system {source_key!r}")


def candidate_record(
    candidate_id: str, row: dict[str, Any], split: str
) -> dict[str, Any]:
    source_systems = row.get("raw")
    if not isinstance(source_systems, dict):
        raise ValueError(f"{candidate_id} has no raw system mapping")

    systems: list[dict[str, Any]] = []
    balance: dict[str, float] = {}
    role_counts: Counter[str] = Counter()
    source_energy_terms: list[float] = []
    clean_symbols: list[str] | None = None
    gas_symbols: list[str] | None = None
    adsorbate_slab: dict[str, Any] | None = None
    for source_key in sorted(source_systems):
        source_system = source_systems[source_key]
        coefficient = float(source_system["stoi"])
        role = role_for(source_key, coefficient)
        structure = source_structure(source_system["atoms_json"])
        system = {
            "system_id": f"{candidate_id}:{source_key}",
            "source_system_key": source_key,
            "role": role,
            "stoichiometric_coefficient": coefficient,
            "reference_total_energy_ev": float(source_system["energy_ref"]),
            **structure,
        }
        systems.append(system)
        role_counts[role] += 1
        source_energy_terms.append(coefficient * float(source_system["energy_ref"]))
        for symbol in structure["symbols"]:
            balance[symbol] = balance.get(symbol, 0.0) + coefficient
        if role == "clean_slab":
            clean_symbols = structure["symbols"]
        elif role == "reference":
            gas_symbols = structure["symbols"]
        elif role == "adsorbate_slab":
            adsorbate_slab = structure

    expected_roles = Counter({"adsorbate_slab": 1, "clean_slab": 1, "reference": 1})
    if role_counts != expected_roles:
        raise ValueError(f"{candidate_id} has incompatible role counts: {dict(role_counts)}")
    residual = {
        symbol: coefficient
        for symbol, coefficient in balance.items()
        if not math.isclose(coefficient, 0.0, abs_tol=1e-8)
    }
    if residual:
        raise ValueError(f"{candidate_id} is not element-balanced: {residual}")
    if clean_symbols is None or gas_symbols is None or adsorbate_slab is None:
        raise ValueError(f"{candidate_id} is missing a required reaction structure")
    surface_elements = sorted(set(clean_symbols))
    if len(surface_elements) != 1 or surface_elements[0] not in SURFACE_FACETS:
        raise ValueError(f"{candidate_id} has unsupported surface composition: {surface_elements}")
    surface_element = surface_elements[0]
    area = surface_area_angstrom2(adsorbate_slab["cell"])
    reference_energy = round(math.fsum(source_energy_terms), 8)
    source_reference = float(row["ref_ads_eng"])
    if not math.isclose(reference_energy, source_reference, abs_tol=5e-8):
        raise ValueError(
            f"{candidate_id} source reaction sum mismatch: {reference_energy} vs {source_reference}"
        )

    # The paper publishes an electronic convergence threshold, not a statistical
    # confidence interval. This per-row value is therefore explicitly scoped as
    # a worst-case three-term SCF-threshold propagation proxy, not total DFT error.
    uncertainty_ev = len(systems) * DFT_ENERGY_CONVERGENCE_EV
    return {
        "candidate_id": candidate_id,
        "structure_id": candidate_id,
        "row_id": "adsorption_energy",
        "split": split,
        "application_family": application(candidate_id),
        "adsorbate_formula": formula(gas_symbols),
        "surface_element": surface_element,
        "surface_facet": SURFACE_FACETS[surface_element],
        "conditions": {
            "energy_definition": "E(adsorbate+slab) - E(clean slab) - E(gas-phase adsorbate)",
            "temperature": {
                "value_k": 0.0,
                "interpretation": "DFT electronic energy; no vibrational, entropic, or finite-temperature correction",
            },
            "coverage": {
                "adsorbates_per_periodic_cell": 1,
                "surface_cell_area_angstrom2": round(area, 12),
                "molecules_per_square_angstrom": round(1.0 / area, 12),
                "molecules_per_square_nanometer": round(100.0 / area, 12),
                "derivation": "one source adsorbate divided by the source periodic surface-cell area",
            },
            "facet": SURFACE_FACETS[surface_element],
            "surface_state": "source DFT-relaxed slab; no independent reconstruction label is published",
            "adsorption_site": "source lowest-energy relaxed configuration; site label is not published",
        },
        "reference": {
            "adsorption_energy_ev": reference_energy,
            "uncertainty_ev": uncertainty_ev,
            "uncertainty_kind": "three-term electronic-convergence proxy bound",
            "confidence_level": None,
            "scope_note": (
                "Three times the published 1e-5 eV electronic convergence threshold. "
                "This is not a statistical interval and excludes functional, slab, k-point, "
                "geometry, dispersion, and model-form uncertainty."
            ),
        },
        "role_counts": dict(sorted(role_counts.items())),
        "stoichiometry": {"element_balanced": True, "residual": {}},
        "source_row": {
            "key": candidate_id,
            "ref_ads_eng_unrounded_ev": source_reference,
            "adsorbate_indices": row.get("adsorbate_indices"),
        },
        "systems": systems,
    }


def build(source: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    acquire(source)
    source_rows = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(source_rows, dict) or len(source_rows) != 32:
        raise ValueError(f"expected 32 CatBench BM rows, found {len(source_rows)}")
    candidate_ids = sorted(source_rows)
    assignments = split_assignments(candidate_ids)
    candidates = [
        candidate_record(candidate_id, source_rows[candidate_id], assignments[candidate_id])
        for candidate_id in candidate_ids
    ]
    split_counts = Counter(candidate["split"] for candidate in candidates)
    role_counts = Counter(
        system["role"] for candidate in candidates for system in candidate["systems"]
    )
    panel = {
        "schema": "lupine.z3.adsorption_reference_panel.v1",
        "panel_id": PANEL_ID,
        "locked_at": LOCKED_AT,
        "measurement": {
            "metric": "adsorption_energy_mae",
            "unit": "eV",
            "minimum_confirmatory_count": 20,
            "confirmatory_split": "confirmatory_test",
        },
        "reference_provenance": {
            "dataset": "CatBench BM_dataset adsorption benchmark",
            "source_url": SOURCE_URL,
            "source_artifact": "BM_dataset_adsorption.json",
            "source_artifact_sha256": SOURCE_SHA256,
            "source_artifact_md5_published_by_zenodo": SOURCE_MD5,
            "dataset_doi": SOURCE_DOI,
            "original_publication_doi": ORIGINAL_DOI,
            "license": "CC BY 4.0",
            "theory": "VASP 5.4.4 DFT(PBE) with D2 reparameterized for metals",
            "theory_details": {
                "plane_wave_cutoff_ev": 450,
                "electronic_convergence_ev": DFT_ENERGY_CONVERGENCE_EV,
                "force_convergence_ev_per_angstrom": 0.03,
                "pseudopotential": "projector augmented wave",
                "facet_policy": "lowest-surface-energy facets: fcc(111) and hcp(0001) for panel metals",
            },
        },
        "holdout": {
            "unit": "adsorbate-surface pair",
            "selection_rule": (
                "Within each application family, order candidate IDs by SHA-256(ID), assign "
                "the first two to delta_train, next two to delta_validation, and all remaining "
                "rows to confirmatory_test."
            ),
            "campaign_fit_exclusion": (
                "Confirmatory-test reference energies may not be used for delta fitting, "
                "model selection, correction selection, threshold tuning, or checkpoint construction."
            ),
            "scope_note": (
                "This lock establishes a Z3 delta-learning holdout; it does not assert that these "
                "public structures were absent from every foundation model's pretraining corpus."
            ),
            "split_counts": dict(sorted(split_counts.items())),
        },
        "delta_protocol": {
            "split_lock_path": "data/candidates/z3_catbench_bm_delta_splits.lock.json",
            "checkpoint_fixture_path": (
                "data/candidates/z3_catbench_bm_delta_checkpoint.fixture.json"
            ),
            "raw_prediction_checkpoint_scope": "all per-system raw energies before correction",
            "failure_policy": "record failure without imputation",
        },
        "aggregate_metadata": {
            "candidate_count": len(candidates),
            "role_counts": dict(sorted(role_counts.items())),
            "surface_counts": dict(
                sorted(Counter(candidate["surface_element"] for candidate in candidates).items())
            ),
            "application_counts": dict(
                sorted(Counter(candidate["application_family"] for candidate in candidates).items())
            ),
        },
        "candidates": candidates,
    }
    split_lock = {
        "schema": "lupine.z3.delta_split.v1",
        "split_id": "z3-catbench-bm-family-stratified-v1",
        "panel_id": PANEL_ID,
        "locked_at": LOCKED_AT,
        "selection_rule": panel["holdout"]["selection_rule"],
        "fit_exclusion": panel["holdout"]["campaign_fit_exclusion"],
        "splits": {
            split: [candidate_id for candidate_id in candidate_ids if assignments[candidate_id] == split]
            for split in SPLIT_NAMES
        },
    }
    checkpoint_fixture = {
        "schema": "lupine.z3.delta_checkpoint_fixture.v1",
        "checkpoint_fixture_id": "z3-catbench-bm-raw-and-delta-v1",
        "panel_id": PANEL_ID,
        "split_id": split_lock["split_id"],
        "state": "unfitted_fixture",
        "registered_model_ids": list(REGISTERED_MODELS),
        "required_payload": {
            "schema": "lupine.z3.delta_checkpoint.v1",
            "model_id": None,
            "candidate_panel_sha256": None,
            "split_lock_sha256": None,
            "raw_prediction_checkpoint_sha256": None,
            "fit_candidate_ids": split_lock["splits"]["delta_train"],
            "validation_candidate_ids": split_lock["splits"]["delta_validation"],
            "confirmatory_candidate_ids": split_lock["splits"]["confirmatory_test"],
            "correction_model": None,
            "fit_metrics": None,
            "validation_metrics": None,
            "created_at": None,
        },
        "rules": [
            "Write raw per-system energies before fitting any correction.",
            "Fit only on delta_train candidate references.",
            "Use delta_validation only for frozen correction selection.",
            "Do not read confirmatory_test reference energies until the checkpoint is finalized.",
            "Record failed candidates without imputation.",
        ],
    }
    return panel, split_lock, checkpoint_fixture


def write_locked(path: Path, document: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/tmp/BM_dataset_adsorption.json"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--split-output", type=Path, default=DEFAULT_SPLIT_OUTPUT)
    parser.add_argument("--checkpoint-output", type=Path, default=DEFAULT_CHECKPOINT_OUTPUT)
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()

    panel, split_lock, checkpoint_fixture = build(args.source)
    if args.inspect:
        print(
            json.dumps(
                {
                    "candidate_count": len(panel["candidates"]),
                    "aggregate_metadata": panel["aggregate_metadata"],
                    "split_counts": panel["holdout"]["split_counts"],
                    "energy_range_ev": [
                        min(
                            candidate["reference"]["adsorption_energy_ev"]
                            for candidate in panel["candidates"]
                        ),
                        max(
                            candidate["reference"]["adsorption_energy_ev"]
                            for candidate in panel["candidates"]
                        ),
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    outputs = (
        (args.output, panel),
        (args.split_output, split_lock),
        (args.checkpoint_output, checkpoint_fixture),
    )
    for path, document in outputs:
        digest = write_locked(path, document)
        print(f"wrote {path} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
