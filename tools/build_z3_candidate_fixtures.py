#!/usr/bin/env python3
"""Build single-candidate Z3 adsorption fixtures from the locked panel.

Each of the 32 candidates in ``data/candidates/z3_catbench_bm_adsorption.lock.json``
becomes one ``lupine.mlip.fixture_manifest.v2`` fixture containing exactly one
``adsorption_energy`` case, matching the runner contract enforced by
``lupine_distill.fixture_contract._adsorption_system_blockers`` (one
``adsorbate_slab`` with coefficient 1, one ``clean_slab`` and at least one
``reference`` system with negative coefficients, element-balanced
stoichiometry, finite positions, finite ``reference.adsorption_energy_ev``).

Every fixture is content-addressed: the file name embeds the SHA-256 of its
exact bytes as ``<candidate_id>.sha256-<hex>.json``, the same convention as
``gcp/mlip-cell-runner/fixtures/adsorption_single_candidate_v2.sha256-*.json``.
Serialization is deterministic (sorted keys, fixed indent, trailing newline),
so a rebuild from the same panel is byte-identical.

A machine-checkable manifest (``z3-candidate-fixtures.manifest.json``) maps
each candidate_id to its fixture filename and SHA-256, records the candidate
split, and binds the set to the panel's own SHA-256.

Upload location (32 fixtures + manifest):

    gs://shed-489901-atlas-inputs/z3-campaign/catbench-bm-v1/

The default output directory is under the gitignored ``build/`` tree; the
generator plus the locked panel are the durable record, and the test suite
rebuilds the fixtures in a temporary directory for validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "data" / "candidates" / "z3_catbench_bm_adsorption.lock.json"
DEFAULT_OUTPUT_DIR = ROOT / "build" / "z3-campaign" / "catbench-bm-v1"
DEFAULT_GCS_BASE = "gs://shed-489901-atlas-inputs/z3-campaign/catbench-bm-v1/"
MANIFEST_NAME = "z3-candidate-fixtures.manifest.json"
FIXTURE_SCHEMA = "lupine.mlip.fixture_manifest.v2"
MANIFEST_SCHEMA = "lupine.z3.candidate_fixture_manifest.v1"
ROW_ID = "adsorption_energy"
ROW_SPEC = {
    "min_cases": 1,
    "max_cases": 1,
    "error_tolerance": 0.1,
    "error_unit": "eV",
}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fixture_bytes(fixture: dict[str, Any]) -> bytes:
    """Deterministic serialization: sorted keys, fixed indent, trailing newline."""

    return (json.dumps(fixture, indent=2, sort_keys=True) + "\n").encode("utf-8")


def fixture_filename(candidate_id: str, digest: str) -> str:
    return f"{candidate_id}.sha256-{digest}.json"


def build_fixture(candidate: dict[str, Any], panel: dict[str, Any]) -> dict[str, Any]:
    """Wrap one panel candidate in the runner's single-candidate fixture shape."""

    candidate_id = str(candidate["candidate_id"])
    provenance = dict(panel.get("reference_provenance") or {})
    provenance["panel_id"] = panel.get("panel_id")
    provenance["panel_locked_at"] = panel.get("locked_at")
    return {
        "schema": FIXTURE_SCHEMA,
        "fixture_id": f"z3-catbench-bm-v1-{candidate_id}",
        "reference_provenance": provenance,
        "metadata": {
            "candidate_id": candidate_id,
            "split": candidate.get("split"),
            "row_id": ROW_ID,
            "application_family": candidate.get("application_family"),
            "surface_element": candidate.get("surface_element"),
            "surface_facet": candidate.get("surface_facet"),
            "adsorbate_formula": candidate.get("adsorbate_formula"),
            "conditions": candidate.get("conditions"),
        },
        "row_specs": {ROW_ID: dict(ROW_SPEC)},
        "row_fixtures": {
            ROW_ID: {
                "structures": [
                    {
                        "candidate_id": candidate_id,
                        "structure_id": candidate.get("structure_id", candidate_id),
                        "reference": candidate["reference"],
                        "systems": candidate["systems"],
                    }
                ]
            }
        },
    }


def build_all(
    panel: dict[str, Any],
    panel_sha256: str,
    panel_path: Path,
    gcs_base: str = DEFAULT_GCS_BASE,
) -> tuple[list[tuple[str, str, str, bytes]], dict[str, Any]]:
    """Return (fixture entries, manifest) for every candidate in the panel.

    Each fixture entry is ``(candidate_id, filename, sha256, content_bytes)``.
    """

    candidates = panel.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("panel contains no candidates")
    entries: list[tuple[str, str, str, bytes]] = []
    manifest_candidates: dict[str, Any] = {}
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in seen:
            raise ValueError(f"duplicate candidate_id in panel: {candidate_id}")
        seen.add(candidate_id)
        content = fixture_bytes(build_fixture(candidate, panel))
        digest = sha256_hex(content)
        filename = fixture_filename(candidate_id, digest)
        entries.append((candidate_id, filename, digest, content))
        manifest_candidates[candidate_id] = {
            "fixture": filename,
            "sha256": digest,
            "split": candidate.get("split"),
        }
    try:
        panel_rel = str(panel_path.resolve().relative_to(ROOT))
    except ValueError:
        panel_rel = str(panel_path)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "panel": {
            "path": panel_rel,
            "panel_id": panel.get("panel_id"),
            "sha256": panel_sha256,
        },
        "gcs_base": gcs_base,
        "candidate_count": len(entries),
        "candidates": manifest_candidates,
    }
    return entries, manifest


def write_outputs(entries: list[tuple[str, str, str, bytes]], manifest: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for _candidate_id, filename, _digest, content in entries:
        (output_dir / filename).write_bytes(content)
    manifest_path = output_dir / MANIFEST_NAME
    manifest_path.write_bytes(fixture_bytes(manifest))
    return manifest_path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--panel", type=Path, default=DEFAULT_PANEL, help="Locked Z3 adsorption panel JSON.")
    result.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Destination for fixtures and manifest.")
    result.add_argument("--gcs-base", default=DEFAULT_GCS_BASE, help="GCS base URI recorded in the manifest.")
    return result


def main() -> None:
    args = parser().parse_args()
    gcs_base = args.gcs_base if args.gcs_base.endswith("/") else args.gcs_base + "/"
    panel_bytes = args.panel.read_bytes()
    panel = json.loads(panel_bytes)
    entries, manifest = build_all(panel, sha256_hex(panel_bytes), args.panel, gcs_base)
    manifest_path = write_outputs(entries, manifest, args.output_dir)
    print(f"wrote {len(entries)} fixtures + {MANIFEST_NAME} to {args.output_dir}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
