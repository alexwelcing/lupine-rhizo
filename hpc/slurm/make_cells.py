#!/usr/bin/env python3
"""Explode a lupine.mlip.batch_spec.v1 JSON into cells.jsonl for a SLURM array.

Each output line is itself a complete, single-cell batch spec (same schema as
the input, with a one-element ``cells`` array). hpc/slurm/run_cells.sbatch maps
SLURM_ARRAY_TASK_ID -> line N+1 -> ``mlip_cell_runner.py run-batch`` on that
single-cell spec, so cell merging semantics (defaults, variant -> distill
profile, checkpoints) stay identical to the managed GCP lane.

Standard library only; runs on any cluster login node with python3.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("batch_spec", help="Path to a lupine.mlip.batch_spec.v1 JSON file")
    parser.add_argument(
        "--out",
        default="cells.jsonl",
        help="Output JSONL path; one single-cell batch spec per line (default: cells.jsonl)",
    )
    parser.add_argument(
        "--artifact-root",
        default=None,
        help=(
            "Optional local directory. Cells without an explicit artifact_prefix "
            "(and no defaults.artifact_prefix) get <artifact-root>/<cell_id>."
        ),
    )
    return parser.parse_args(argv)


def explode(spec: dict, artifact_root: str | None) -> list[dict]:
    cells = spec.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("batch spec must include a non-empty cells array")
    defaults = spec.get("defaults") if isinstance(spec.get("defaults"), dict) else {}
    header = {key: value for key, value in spec.items() if key != "cells"}
    singles: list[dict] = []
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict):
            raise ValueError(f"cells[{index}] must be a JSON object")
        cell = dict(cell)
        has_prefix = cell.get("artifact_prefix") or defaults.get("artifact_prefix")
        if artifact_root and not has_prefix:
            cell_id = str(cell.get("cell_id") or f"cell-{index:05d}")
            cell["artifact_prefix"] = str(
                pathlib.Path(artifact_root) / cell_id.replace("/", "_")
            )
        single = dict(header)
        single["source_cell_index"] = index
        single["cells"] = [cell]
        singles.append(single)
    return singles


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    spec = json.loads(pathlib.Path(args.batch_spec).read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("batch spec must be a JSON object")
    singles = explode(spec, args.artifact_root)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for single in singles:
            handle.write(json.dumps(single, sort_keys=True) + "\n")
    count = len(singles)
    print(f"wrote {count} cells to {out_path}")
    print(f"submit with: sbatch --array=0-{count - 1} hpc/slurm/run_cells.sbatch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
