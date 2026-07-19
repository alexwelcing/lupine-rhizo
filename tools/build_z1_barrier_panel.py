#!/usr/bin/env python3
"""Build the locked Z1 barrier panel from the public LiTraj nebDFT2k corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, cast

from ase.io import read

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "candidates" / "z1_nebdft2k_barriers.lock.json"
SOURCE_URL = "https://bs3u.obs.ru-moscow-1.hc.sbercloud.ru/litraj/nebDFT2k.zip"
SOURCE_SHA256 = "b7a99d89337902e9e1da319f57547170fdb132bf15bf6ffef03a0140e2207d7f"
SOURCE_REVISION = "c3ca5c2afbc13ffc823306f546dcee24486ade2a"
SOURCE_DOI = "10.1038/s41524-025-01571-z"
PANEL_SIZE = 30


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
        raise ValueError(f"nebDFT2k source digest mismatch: expected {SOURCE_SHA256}, got {actual}")


def load_index(archive: zipfile.ZipFile) -> list[dict[str, str]]:
    index_name = next(name for name in archive.namelist() if name.endswith("nebDFT2k_index.csv"))
    return list(csv.DictReader(io.StringIO(archive.read(index_name).decode("utf-8"))))


def chemistry_held_out_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Choose one official-test path per chemistry for the frozen Z1 holdout.

    LiTraj's own split is not the Z1 training split: Z1 evaluates pretrained
    foundation models and reserves this panel from any subsequent barrier-targeted
    fitting or model selection. One path per chemical system prevents a chemistry
    with many symmetry-related hops from dominating the MAE.
    """
    by_chemistry: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["_split"] == "test":
            by_chemistry.setdefault(row["chemsys"], []).append(row)
    return [
        sorted(by_chemistry[chemistry], key=lambda row: (row["material_id"], row["edge_id"]))[0]
        for chemistry in sorted(by_chemistry)
    ]


def trajectory(archive: zipfile.ZipFile, edge_id: str, kind: str) -> list[Any]:
    suffix = f"/{edge_id}_{kind}.xyz"
    member = next(name for name in archive.namelist() if name.endswith(suffix))
    return cast(
        list[Any],
        read(io.StringIO(archive.read(member).decode("utf-8")), index=":", format="extxyz"),
    )


def energy_ev(atoms: Any) -> float:
    if atoms.calc is None:
        raise ValueError("trajectory image lacks a DFT energy")
    return float(atoms.get_potential_energy())


def structure_record(atoms: Any) -> dict[str, Any]:
    return {
        "symbols": atoms.get_chemical_symbols(),
        "cell_angstrom": atoms.cell.array.tolist(),
        "pbc": [bool(value) for value in atoms.pbc],
        "positions_angstrom": atoms.positions.tolist(),
    }


def path_record(archive: zipfile.ZipFile, row: dict[str, str]) -> dict[str, Any]:
    initial = trajectory(archive, row["edge_id"], "init")
    relaxed = trajectory(archive, row["edge_id"], "relaxed")
    energies = [energy_ev(image) for image in relaxed]
    saddle_index = max(range(len(energies)), key=energies.__getitem__)
    barrier_ev = float(row["em_dft"])
    profile_barrier_ev = max(energies) - min(energies)
    if abs(barrier_ev - profile_barrier_ev) > 5e-4:
        raise ValueError(
            f"{row['edge_id']} index/profile barrier mismatch: {barrier_ev} vs {profile_barrier_ev}"
        )
    return {
        "path_id": row["edge_id"],
        "material_id": row["material_id"],
        "chemical_system": row["chemsys"],
        "split": row["_split"],
        "reference_barrier_ev": barrier_ev,
        "input_images": [structure_record(image) for image in initial],
        "reference": {
            "image_count": len(relaxed),
            "saddle_image_index": saddle_index,
            "energies_ev": energies,
            "endpoint_initial": structure_record(relaxed[0]),
            "saddle": structure_record(relaxed[saddle_index]),
            "endpoint_final": structure_record(relaxed[-1]),
        },
    }


def build(source: Path) -> dict[str, Any]:
    acquire(source)
    with zipfile.ZipFile(source) as archive:
        rows = load_index(archive)
        eligible = chemistry_held_out_rows(rows)
        if len(eligible) < PANEL_SIZE:
            raise ValueError(
                f"nebDFT2k has only {len(eligible)} chemistry-held-out test paths; need {PANEL_SIZE}"
            )
        selected = eligible[:PANEL_SIZE]
        paths = [path_record(archive, row) for row in selected]

    selected_chemistries = sorted({path["chemical_system"] for path in paths})
    return {
        "schema": "lupine.z1.neb_barrier_panel.v1",
        "panel_id": "z1-nebdft2k-chemistry-held-out-v1",
        "locked_at": "2026-07-19T00:00:00Z",
        "measurement": {"metric": "barrier_mae", "unit": "meV", "minimum_path_count": 30},
        "holdout": {
            "unit": "chemical_system",
            "selection_rule": "One deterministic path from each of the first 30 lexically ordered chemical systems in the official nebDFT2k test split.",
            "campaign_fit_exclusion": "Every selected chemical system and all of its NEB images are excluded from Z1 barrier-targeted fitting, calibration, model selection, and threshold tuning.",
            "source_split": "test",
            "source_split_scope_note": "LiTraj's train/validation split is not used as the Z1 model-development corpus; the Z1 chemistry holdout begins with this lock.",
            "selected_chemical_systems": selected_chemistries,
        },
        "reference_provenance": {
            "dataset": "LiTraj nebDFT2k",
            "theory": "DFT(PBE) climbing-image NEB",
            "source_url": SOURCE_URL,
            "source_archive_sha256": SOURCE_SHA256,
            "source_repository": "https://github.com/AIRI-Institute/LiTraj",
            "source_revision": SOURCE_REVISION,
            "doi": SOURCE_DOI,
            "license": "MIT; source Materials Project structures CC BY 4.0",
        },
        "execution_protocol": {
            "method": "climbing-image NEB",
            "optimizer": "FIRE",
            "spring_constant_ev_per_angstrom2": 5.0,
            "tangent_method": "improvedtangent",
            "climb": True,
            "endpoint_relaxation": True,
            "maximum_steps": 100,
            "force_convergence_ev_per_angstrom": 0.1,
            "failure_policy": "record failure without imputation",
            "barrier_definition": "max(image_energy_ev) - min(image_energy_ev)",
        },
        "paths": paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("/tmp/nebDFT2k.zip"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()

    acquire(args.source)
    if args.inspect:
        with zipfile.ZipFile(args.source) as archive:
            rows = load_index(archive)
        eligible = chemistry_held_out_rows(rows)
        print(json.dumps({
            "total_rows": len(rows),
            "test_paths": sum(row["_split"] == "test" for row in rows),
            "test_chemical_systems": len({row["chemsys"] for row in rows if row["_split"] == "test"}),
            "eligible_one_per_chemistry_test_paths": len(eligible),
            "eligible_chemical_systems": len({row["chemsys"] for row in eligible}),
            "first_rows": eligible[:5],
        }, indent=2))
        return 0

    panel = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(panel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(args.output)
    sidecar = args.output.with_suffix(args.output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(f"wrote {len(panel['paths'])} paths to {args.output} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
