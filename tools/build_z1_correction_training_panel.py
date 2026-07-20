#!/usr/bin/env python3
"""Build the Round-5 Z1-correction training panel (disjoint chemistries, hash-locked).

Per docs/plans/2026-07-20-round5-z1-correction-preregistration.md: <=12 DFT-NEB
paths from the LiTraj TRAINING split, one per chemical system, with every
chemistry disjoint from the frozen 30-path Z1 test panel. Same source pin and
record conventions as tools/build_z1_barrier_panel.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from build_z1_barrier_panel import (  # noqa: E402
    SOURCE_SHA256,
    SOURCE_DOI,
    SOURCE_REVISION,
    SOURCE_URL,
    acquire,
    load_index,
    path_record,
)

PANEL_SIZE = 12
TEST_PANEL = Path("data/candidates/z1_nebdft2k_barriers.lock.json")
OUT = Path("data/candidates/z1r5_correction_train.lock.json")


def eligible_rows(rows: list[dict[str, str]], test_chemistries: set[str]) -> list[dict[str, str]]:
    """One train-split path per chemical system, disjoint from every test chemistry."""
    by_chemistry: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["_split"] != "train":
            continue
        if row["chemsys"] in test_chemistries:
            continue
        by_chemistry.setdefault(row["chemsys"], []).append(row)
    ordered = sorted(
        by_chemistry,
        key=lambda chem: hashlib.sha256(chem.encode("utf-8")).hexdigest(),
    )
    chosen = []
    for chem in ordered[:PANEL_SIZE]:
        candidates = sorted(by_chemistry[chem], key=lambda row: (row["material_id"], row["edge_id"]))
        chosen.append(candidates[0])
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/tmp/litraj-z1/nebDFT2k.zip"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    test_panel = json.loads(TEST_PANEL.read_text(encoding="utf-8"))
    test_chemistries = {p["chemical_system"] for p in test_panel["paths"]}
    test_materials = {p["material_id"] for p in test_panel["paths"]}

    acquire(args.source)
    with zipfile.ZipFile(args.source) as archive:
        rows = load_index(archive)
        chosen = eligible_rows(rows, test_chemistries)
        if len(chosen) < PANEL_SIZE:
            raise ValueError(f"only {len(chosen)} disjoint train chemistries; need {PANEL_SIZE}")
        paths = []
        seen_materials: set[str] = set()
        for row in chosen:
            if row["material_id"] in test_materials:
                raise ValueError(f"material leakage: {row['material_id']} appears in the test panel")
            if row["material_id"] in seen_materials:
                raise ValueError(f"duplicate material in training panel: {row['material_id']}")
            seen_materials.add(row["material_id"])
            paths.append(path_record(archive, row))

    panel = {
        "schema": "lupine.z1.neb_barrier_panel.v1",
        "panel_id": "z1r5-correction-train-disjoint-v1",
        "locked_at": "2026-07-20T00:00:00Z",
        "holdout": {
            "kind": "chemistry-disjoint-training",
            "disjoint_from": "data/candidates/z1_nebdft2k_barriers.lock.json",
            "disjoint_from_sha256": "sha256:192fe54a5579cc421f6644d5d76fb442c6dfb985f014dc4741549e29052efb68",
            "note": "Training-split paths, one per chemical system, zero overlap with the frozen Z1 test panel chemistries or material ids; deterministic SHA-256 ordering.",
        },
        "reference_provenance": {
            "dataset": "LiTraj nebDFT2k",
            "doi": SOURCE_DOI,
            "source_revision": SOURCE_REVISION,
            "source_url": SOURCE_URL,
            "source_archive_sha256": SOURCE_SHA256,
            "source_split": "train",
        },
        "measurement": {
            "metric": "barrier_mae",
            "unit": "meV",
            "minimum_path_count": PANEL_SIZE,
            "role": "correction_fit_only",
        },
        "execution_protocol": test_panel["execution_protocol"],
        "paths": paths,
    }
    payload = (json.dumps(panel, indent=1, sort_keys=True) + "\n").encode("utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    args.out.with_name(args.out.name + ".sha256").write_text(f"{digest}  {args.out.name}\n")
    print(json.dumps({
        "paths": len(paths),
        "chemistries": sorted({p["chemical_system"] for p in paths}),
        "sha256": digest,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
