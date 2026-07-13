#!/usr/bin/env python3
"""Build the Round-1 candidate fixture manifest for cloud promotion (scope P1).

Emits a `lupine.mlip.fixture_manifest.v2` manifest consumed by
`gcp/mlip-cell-runner/mlip_cell_runner.py` via the fail-closed
`lupine_distill.fixture_contract`. Two rows are populated:

- `elastic_constants`: the candidates with non-null literature Cij references,
  13 finite-strain cases each (zero + +/-0.5% on the 6 Voigt modes) on a FIXED
  builder-supplied lattice (reference/guess a0). This is the declared protocol
  deviation of the promotion packet (`protocol=fixed_lattice`): good for wiring
  and coarse Cij dispersion, not claim-grade for the prereg Cij leg.
- `relaxation_stability`: all frozen Round-1 candidates from perturbed starts.

The unused contract rows (`energy_volume`, `forces`, `stress`) are explicitly
emptied with `min_cases: 0` so the full-manifest release gate stays honest:
no placeholder references are ever invented (freeze declaration).

Configuration is pinned to the local Round-1 campaign
(`data/candidates/round1/report.json`): RSS seed 20260713, 3x3x3 conventional
fcc supercell (108 atoms), strain delta 0.5e-2, rattle stdev 0.05 A.

Governing doc: docs/promotion/2026-07-13-six-model-promotion-packet.md (3.1).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

import numpy as np
from ase import Atoms

from lupine_distill.statics import build_rss_supercell
from lupine_distill.statics.structures import build_structure

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = REPO_ROOT / "data" / "candidates" / "round1_targets.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "candidates" / "round1_cloud" / "manifest.json"

TARGETS_SCHEMA = "lupine.campaign_targets.v1"
MANIFEST_SCHEMA = "lupine.mlip.fixture_manifest.v2"
FIXTURE_ID = "round1-candidates-v1"

RSS_SEED = 20260713
RSS_REPEAT = 3
STRAIN_DELTA = 0.5e-2
RATTLE_STDEV = 0.05
FORCE_THRESHOLD = 0.05
RELAX_MAX_STEPS = 200

CIJ_KEYS = ("c11", "c12", "c44")

# Prereg: CsSnI3 Cij references are weak (computed at an overestimated GGA-PBE
# volume) and stay excluded from headline success criteria.
HEADLINE_EXCLUDED_CIJ = frozenset({"hp-cssni3"})


def load_targets(path: pathlib.Path | str) -> dict[str, Any]:
    """Load and validate the frozen Round-1 targets file."""
    payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"targets file {path} must contain a JSON object")
    if payload.get("schema") != TARGETS_SCHEMA:
        raise ValueError(
            f"targets file {path} has schema {payload.get('schema')!r}; "
            f"expected {TARGETS_SCHEMA!r}"
        )
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError(f"targets file {path} has no candidates")
    for candidate in candidates:
        for key in ("id", "formula", "structure_type", "lattice_guess_angstrom"):
            if key not in candidate:
                raise ValueError(f"candidate {candidate.get('id')!r} missing {key!r}")
    return payload


def candidate_atoms(candidate: dict[str, Any]) -> Atoms:
    """Initial cell for a candidate, identical to the local Round-1 build.

    fcc-rss: 3x3x3 conventional fcc RSS supercell (108 atoms), RNG seed
    20260713; formula types (perovskite): conventional cell at the frozen
    `lattice_guess_angstrom`.
    """
    structure_type = candidate["structure_type"]
    a_guess = float(candidate["lattice_guess_angstrom"])
    if structure_type == "fcc-rss":
        return build_rss_supercell(
            candidate["composition"], "fcc", a_guess, RSS_REPEAT, RSS_SEED
        )
    return build_structure(candidate["formula"], structure_type, a_guess)


def atoms_record(atoms: Atoms) -> dict[str, Any]:
    return {
        "symbols": [str(s) for s in atoms.get_chemical_symbols()],
        "positions": np.asarray(atoms.positions, dtype=float).tolist(),
        "cell": np.asarray(atoms.cell.array, dtype=float).tolist(),
        "pbc": [True, True, True],
    }


def strain_matrix(strain_voigt: np.ndarray) -> np.ndarray:
    """Symmetric tensor strain from a Voigt vector (engineering shear halved)."""
    v = np.asarray(strain_voigt, dtype=float)
    return np.array(
        [
            [v[0], 0.5 * v[5], 0.5 * v[4]],
            [0.5 * v[5], v[1], 0.5 * v[3]],
            [0.5 * v[4], 0.5 * v[3], v[2]],
        ],
        dtype=float,
    )


def elastic_modes(delta: float) -> list[tuple[str, np.ndarray]]:
    modes: list[tuple[str, np.ndarray]] = [("zero", np.zeros(6, dtype=float))]
    for index, basis in enumerate(np.eye(6), start=1):
        modes.append((f"mode{index}-pos", basis * delta))
        modes.append((f"mode{index}-neg", basis * -delta))
    return modes


def cij_reference_gpa(candidate: dict[str, Any]) -> dict[str, float]:
    """Non-null literature Cij values in GPa; nulls are excluded, never filled."""
    references = candidate.get("references") or {}
    out: dict[str, float] = {}
    for key in CIJ_KEYS:
        entry = references.get(key)
        if isinstance(entry, dict) and isinstance(entry.get("value"), (int, float)):
            out[key.upper()] = float(entry["value"])
    return out


def cij_kinds(candidate: dict[str, Any]) -> dict[str, str]:
    references = candidate.get("references") or {}
    return {
        key.upper(): str(references[key].get("kind"))
        for key in CIJ_KEYS
        if isinstance(references.get(key), dict)
    }


def elastic_cases(candidate: dict[str, Any], delta: float) -> list[dict[str, Any]]:
    reference_cij = cij_reference_gpa(candidate)
    if not reference_cij:
        return []
    base = candidate_atoms(candidate)
    base_cell = np.asarray(base.cell.array, dtype=float)
    cases: list[dict[str, Any]] = []
    for label, strain_voigt in elastic_modes(delta):
        strained = base.copy()
        deformation = np.eye(3) + strain_matrix(strain_voigt)
        strained.set_cell(base_cell @ deformation, scale_atoms=True)
        cases.append(
            {
                "structure_id": f"round1-{candidate['id']}-elastic-{label}",
                "material_id": candidate["id"],
                "row_id": "elastic_constants",
                **atoms_record(strained),
                "strain_voigt": strain_voigt.tolist(),
                "metadata": {
                    "group": candidate.get("group"),
                    "formula": candidate["formula"],
                    "structure_type": candidate["structure_type"],
                    "protocol": "fixed_lattice",
                    "lattice_angstrom": float(candidate["lattice_guess_angstrom"]),
                    "strain_delta": delta,
                    "reference_kinds": cij_kinds(candidate),
                    "headline_eligible": candidate["id"] not in HEADLINE_EXCLUDED_CIJ,
                },
                "reference": {"elastic_constants_gpa": reference_cij},
            }
        )
    return cases


def relaxation_case(
    candidate: dict[str, Any], candidate_index: int
) -> dict[str, Any]:
    base = candidate_atoms(candidate)
    rng = np.random.default_rng([RSS_SEED, candidate_index])
    displacements = rng.normal(loc=0.0, scale=RATTLE_STDEV, size=(len(base), 3))
    perturbed = base.copy()
    perturbed.positions = base.positions + displacements
    return {
        "structure_id": f"round1-{candidate['id']}-relax-perturbed",
        "material_id": candidate["id"],
        "row_id": "relaxation_stability",
        **atoms_record(perturbed),
        "metadata": {
            "group": candidate.get("group"),
            "formula": candidate["formula"],
            "structure_type": candidate["structure_type"],
            "lattice_angstrom": float(candidate["lattice_guess_angstrom"]),
            "perturbation": {
                "distribution": "normal",
                "stdev_angstrom": RATTLE_STDEV,
                "seed": [RSS_SEED, candidate_index],
                "max_displacement_angstrom": float(
                    np.max(np.linalg.norm(displacements, axis=1))
                ),
            },
        },
        "reference": {"relaxation_force_threshold": FORCE_THRESHOLD},
    }


def provenance_block(targets: dict[str, Any], targets_path: str) -> dict[str, Any]:
    """Verbatim per-candidate reference provenance plus builder declaration."""
    per_candidate: dict[str, Any] = {}
    for candidate in targets["candidates"]:
        entry: dict[str, Any] = {"references": candidate.get("references")}
        for extra in ("cij_null_reason", "a0_null_reason", "mp_id", "mp_id_caveat"):
            if extra in candidate:
                entry[extra] = candidate[extra]
        per_candidate[candidate["id"]] = entry
    return {
        "round1_targets": {
            "path": targets_path,
            "schema": targets.get("schema"),
            "generated_at": targets.get("generated_at"),
            "notes": targets.get("notes"),
            "per_candidate": per_candidate,
        },
        "builder": {
            "tool": "tools/build_candidate_manifest.py",
            "packet": "docs/promotion/2026-07-13-six-model-promotion-packet.md",
            "rss": {"supercell": RSS_REPEAT, "seed": RSS_SEED},
            "strain_delta": STRAIN_DELTA,
            "relaxation_perturbation": {
                "distribution": "normal",
                "stdev_angstrom": RATTLE_STDEV,
                "seed_root": RSS_SEED,
            },
            "protocol_deviation": (
                "elastic_constants cases strain a FIXED builder-supplied lattice "
                "(reference/guess a0), not each model's own relaxed cell as the "
                "local run_candidate_campaign.py does. Cells are labeled "
                "protocol=fixed_lattice and stay out of headline Cij claims "
                "until the candidate_statics runner row lands (packet GAP-1)."
            ),
        },
    }


def build_manifest(
    targets: dict[str, Any], targets_path: str = "data/candidates/round1_targets.json"
) -> dict[str, Any]:
    candidates = targets["candidates"]
    elastic_structures = [
        case for candidate in candidates for case in elastic_cases(candidate, STRAIN_DELTA)
    ]
    relaxation_structures = [
        relaxation_case(candidate, index) for index, candidate in enumerate(candidates)
    ]
    if not elastic_structures or not relaxation_structures:
        raise ValueError("targets produced an empty row; refusing to emit manifest")

    empty_row_note = (
        "row intentionally empty: no honest per-point references exist for the "
        "Round-1 candidates (freeze declaration; packet GAP-1). min_cases=0 keeps "
        "the full-manifest release gate truthful without inventing placeholders."
    )
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "fixture_id": FIXTURE_ID,
        "title": "Round-1 candidate statics fixture (cloud promotion P1)",
        "description": (
            "Frozen Round-1 candidates (4 HEA fcc-RSS + 5 halide perovskites) for "
            "the six-model promotion: fixed-lattice finite-strain Cij cases vs "
            "literature references, and perturbed-start relaxation stability."
        ),
        "reference_provenance": provenance_block(targets, targets_path),
        "row_specs": {
            "elastic_constants": {
                "min_cases": 6,
                "error_tolerance": 50.0,
                "error_unit": "gpa_mae",
            },
            "relaxation_stability": {
                "min_cases": 3,
                "force_threshold": FORCE_THRESHOLD,
                "max_steps": RELAX_MAX_STEPS,
                "error_tolerance": 0.10,
                "error_unit": "relaxation_penalty",
            },
            "energy_volume": {"min_cases": 0, "note": empty_row_note},
            "forces": {"min_cases": 0, "note": empty_row_note},
            "stress": {"min_cases": 0, "note": empty_row_note},
        },
        "row_fixtures": {
            "elastic_constants": {"structures": elastic_structures},
            "relaxation_stability": {"structures": relaxation_structures},
        },
        "metadata": {
            "structure_count": len(elastic_structures) + len(relaxation_structures),
            "targets_generated_at": targets.get("generated_at"),
            "rss_seed": RSS_SEED,
            "rss_supercell": RSS_REPEAT,
            "strain_delta": STRAIN_DELTA,
            "rattle_stdev_angstrom": RATTLE_STDEV,
        },
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["manifest_hash"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    targets = load_targets(args.targets)
    targets_rel = pathlib.Path(args.targets)
    try:
        targets_rel = targets_rel.resolve().relative_to(REPO_ROOT)
    except ValueError:
        pass
    manifest = build_manifest(targets, targets_path=targets_rel.as_posix())

    output = pathlib.Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    print(
        json.dumps(
            {
                "fixture_id": manifest["fixture_id"],
                "manifest_hash": manifest["manifest_hash"],
                "row_counts": {
                    row_id: len(group["structures"])
                    for row_id, group in manifest["row_fixtures"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
