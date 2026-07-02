"""Skip helpers for tools tests that depend on machine-local benchmark artifacts."""

from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data" / "mlip_benchmarks" / "manifest_sources.json"
MISHIN_POTENTIAL = "atlas-distill/lammps_runs/Ni_Mishin-1999/Ni99.eam.alloy"


def manifest_local_paths(
    fields: tuple[str, ...] = ("local_dir", "potential_file", "result_json"),
) -> list[str]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    paths: list[str] = []
    for baseline in manifest.get("local_ni_classical_inventory", []):
        if not isinstance(baseline, dict):
            continue
        for field in fields:
            value = baseline.get(field)
            if isinstance(value, str) and value.strip():
                paths.append(value)
    return paths


def requires_local_artifact(*relative_paths: str) -> None:
    missing = [
        path for path in relative_paths if not (ROOT / pathlib.PurePosixPath(path)).exists()
    ]
    if missing:
        pytest.skip(
            "local artifact missing: "
            + ", ".join(missing)
            + "; run tools/fetch_potentials.py"
        )
