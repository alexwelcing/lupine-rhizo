#!/usr/bin/env python3
"""Build deterministic multi-configuration A6 manifests from locked parquet inputs."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pyarrow.parquet as pq
from ase.data import chemical_symbols

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "manifests"
CANONICAL = Path(
    "/home/alex/Dev/lupine/lupine-rhizo/gcp/mlip-cell-runner/fixtures/"
    "canonical_structures_v2_mptrj.json"
)
SALT = "a6-decide-v1"
N_BLOCKS = 50
N_CONFIGS = 8
MIN_BLOCKS = 30
MIN_CONFIGURATIONS = 240
MAX_ATOMS = 80
MAX_ATOMIC_NUMBER = 83
MPTRJ_REVISION = "f88fbe46e16524223210654bad9e1b05a15c2adb"
SOURCE_IDENTITIES: dict[str, dict[str, str]] = {
    "mptrj": {
        "frozen_source_identity": "MPtrj test",
        "resolved_split": "test",
        "dataset_revision": MPTRJ_REVISION,
    },
    "matpes-pbe-2025.2": {},
    "omat24-validation-aimd-pbe-1000-nvt": {},
}


def plain(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def finite_array(value: Any, shape_tail: tuple[int, ...] = ()) -> bool:
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return False
    return bool(arr.size and np.all(np.isfinite(arr)) and (not shape_tail or arr.shape[-len(shape_tail) :] == shape_tail))


def symbols_from_numbers(numbers: Any) -> list[str] | None:
    try:
        zs = [int(z) for z in numbers]
    except (TypeError, ValueError):
        return None
    if not zs or min(zs) < 1 or max(zs) > MAX_ATOMIC_NUMBER:
        return None
    return [chemical_symbols[z] for z in zs]


def hash_rank(source: str, block_id: str) -> str:
    return hashlib.sha256(f"{SALT}|{source}|{block_id}".encode()).hexdigest()


def evenly_spaced(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    rows = sorted(
        rows,
        key=lambda row: (
            int(row["metadata"]["trajectory_step"]),
            str(row["config_id"]),
        ),
    )
    if len(rows) == count:
        return rows
    indices = np.linspace(0, len(rows) - 1, count, dtype=int)
    if len(set(indices.tolist())) != count:
        raise ValueError("even-spacing produced duplicate indices")
    return [rows[int(i)] for i in indices]


def build_case(
    *,
    source: str,
    block_id: str,
    config_id: str,
    step: int,
    symbols: list[str],
    positions: Any,
    cell: Any,
    pbc: Any,
    energy_total_ev: float,
    forces: Any,
    source_row: int,
    extra: dict[str, Any],
) -> dict[str, Any]:
    n_atoms = len(symbols)
    return {
        "structure_id": f"a6-{source}-{config_id}",
        "material_id": f"{source}:{block_id}",
        "config_id": config_id,
        "row_id": "forces",
        "symbols": symbols,
        "positions": plain(positions),
        "cell": plain(cell),
        "pbc": plain(pbc),
        "metadata": {
            "source_dataset": source,
            "source_row": source_row,
            "trajectory_block": block_id,
            "trajectory_step": step,
            **plain(extra),
        },
        "reference": {
            "energy_ev_per_atom": float(energy_total_ev) / n_atoms,
            "forces_ev_per_angstrom": plain(forces),
        },
    }


def collect_mptrj(path: Path) -> dict[str, list[dict[str, Any]]]:
    parquet = pq.ParquetFile(path)
    counts: dict[str, int] = defaultdict(int)
    count_columns = ["numbers", "forces", "energy", "task_id", "num_atoms"]
    for batch in parquet.iter_batches(batch_size=4096, columns=count_columns):
        for row in batch.to_pylist():
            symbols = symbols_from_numbers(row.get("numbers"))
            forces = row.get("forces")
            if (
                symbols is not None
                and int(row.get("num_atoms") or 0) == len(symbols)
                and len(symbols) <= MAX_ATOMS
                and finite_array(forces, (3,))
                and np.max(np.abs(np.asarray(forces, dtype=float))) > 1e-8
                and math.isfinite(float(row.get("energy") or math.nan))
            ):
                counts[str(row["task_id"])] += 1
    # The frozen MPtrj test shard is small enough to retain every valid block.
    # Main applies the preregistered >=8-config gate and deterministic ranking;
    # keeping sub-threshold blocks here preserves exact fail-closed diagnostics.
    selected = set(counts)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    columns = [
        "numbers", "positions", "forces", "cell", "pbc", "energy", "mp_id",
        "task_id", "calc_id", "ionic_step", "num_atoms",
    ]
    source_row = -1
    for batch in parquet.iter_batches(batch_size=2048, columns=columns):
        for row in batch.to_pylist():
            source_row += 1
            block_id = str(row["task_id"])
            if block_id not in selected:
                continue
            symbols = symbols_from_numbers(row.get("numbers"))
            forces = row.get("forces")
            if (
                symbols is None
                or int(row.get("num_atoms") or 0) != len(symbols)
                or len(symbols) > MAX_ATOMS
                or not finite_array(row.get("positions"), (3,))
                or not finite_array(row.get("cell"), (3, 3))
                or not finite_array(forces, (3,))
                or np.max(np.abs(np.asarray(forces, dtype=float))) <= 1e-8
                or not math.isfinite(float(row.get("energy") or math.nan))
            ):
                continue
            step = int(row["ionic_step"])
            config_id = f"{block_id}-step{step}-row{source_row}"
            groups[block_id].append(build_case(
                source="mptrj", block_id=block_id, config_id=config_id, step=step,
                symbols=symbols, positions=row["positions"], cell=row["cell"],
                pbc=row.get("pbc", [True, True, True]), energy_total_ev=float(row["energy"]),
                forces=forces, source_row=source_row,
                extra={"calc_id": row.get("calc_id"), "mp_id": row.get("mp_id")},
            ))
    return groups


def matpes_identity(row: dict[str, Any]) -> tuple[str, int]:
    metadata = row.get("metadata")
    parsed = json.loads(metadata) if isinstance(metadata, str) else (metadata or {})
    provenance = parsed.get("provenance") or {}
    block_id = provenance.get("original_mp_id")
    step = provenance.get("md_step")
    if block_id is not None and step is not None:
        return str(block_id), int(step)
    name = str((row.get("names") or [""])[0])
    match = re.search(r"matpes-\d+_(\d+)_(\d+)$", name)
    if not match:
        raise ValueError(f"cannot parse MatPES identity: {name}")
    return f"mp-{match.group(1)}", int(match.group(2))


def collect_matpes(path: Path) -> dict[str, list[dict[str, Any]]]:
    parquet = pq.ParquetFile(path)
    counts: dict[str, int] = defaultdict(int)
    count_columns = ["names", "metadata", "nsites", "atomic_numbers", "energy", "atomic_forces"]
    for batch in parquet.iter_batches(batch_size=4096, columns=count_columns):
        for row in batch.to_pylist():
            try:
                block_id, _ = matpes_identity(row)
                symbols = symbols_from_numbers(row.get("atomic_numbers"))
                forces = row.get("atomic_forces")
                valid = math.isfinite(float(row["energy"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if symbols is not None and len(symbols) <= MAX_ATOMS and finite_array(forces, (3,)) and np.max(np.abs(np.asarray(forces, dtype=float))) > 1e-8 and valid:
                counts[block_id] += 1
    selected = set(sorted(
        (block for block, count in counts.items() if count >= N_CONFIGS),
        key=lambda block: (hash_rank("matpes-pbe-2025.2", block), block),
    )[:N_BLOCKS])
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    columns = [
        "names", "metadata", "nsites", "atomic_numbers", "positions", "cell",
        "pbc", "energy", "atomic_forces", "method", "property_id", "configuration_id",
    ]
    source_row = -1
    for batch in parquet.iter_batches(batch_size=2048, columns=columns):
        for row in batch.to_pylist():
            source_row += 1
            try:
                block_id, step = matpes_identity(row)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if block_id not in selected:
                continue
            symbols = symbols_from_numbers(row.get("atomic_numbers"))
            forces = row.get("atomic_forces")
            if (
                symbols is None
                or int(row.get("nsites") or 0) != len(symbols)
                or len(symbols) > MAX_ATOMS
                or not finite_array(row.get("positions"), (3,))
                or not finite_array(row.get("cell"), (3, 3))
                or not finite_array(forces, (3,))
                or np.max(np.abs(np.asarray(forces, dtype=float))) <= 1e-8
                or not math.isfinite(float(row.get("energy") or math.nan))
            ):
                continue
            config_id = str(row.get("configuration_id") or f"{block_id}-step{step}-row{source_row}")
            groups[block_id].append(build_case(
                source="matpes-pbe-2025.2", block_id=block_id, config_id=config_id, step=step,
                symbols=symbols, positions=row["positions"], cell=row["cell"],
                pbc=row.get("pbc", [True, True, True]), energy_total_ev=float(row["energy"]),
                forces=forces, source_row=source_row,
                extra={"method": row.get("method"), "property_id": row.get("property_id")},
            ))
    return groups


OMAT_NAME = re.compile(r"OMat24__(.+)_([0-9]+)__file_ix_([0-9]+)$")


def collect_omat24(path: Path) -> dict[str, list[dict[str, Any]]]:
    parquet = pq.ParquetFile(path)
    counts: dict[str, int] = defaultdict(int)
    count_columns = ["names", "nsites", "atomic_numbers", "energy", "atomic_forces"]
    for batch in parquet.iter_batches(batch_size=4096, columns=count_columns):
        for row in batch.to_pylist():
            match = OMAT_NAME.match(str((row.get("names") or [""])[0]))
            symbols = symbols_from_numbers(row.get("atomic_numbers"))
            forces = row.get("atomic_forces")
            if match is not None and symbols is not None and len(symbols) <= MAX_ATOMS and finite_array(forces, (3,)) and np.max(np.abs(np.asarray(forces, dtype=float))) > 1e-8 and math.isfinite(float(row.get("energy") or math.nan)):
                counts[match.group(1)] += 1
    selected = set(sorted(
        (block for block, count in counts.items() if count >= N_CONFIGS),
        key=lambda block: (hash_rank("omat24-validation-aimd-pbe-1000-nvt", block), block),
    )[:N_BLOCKS])
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    columns = [
        "names", "nsites", "atomic_numbers", "positions", "cell", "pbc", "energy",
        "atomic_forces", "method", "property_id", "configuration_id",
    ]
    source_row = -1
    for batch in parquet.iter_batches(batch_size=2048, columns=columns):
        for row in batch.to_pylist():
            source_row += 1
            match = OMAT_NAME.match(str((row.get("names") or [""])[0]))
            if match is None or match.group(1) not in selected:
                continue
            block_id, step_text, file_ix = match.groups()
            step = int(step_text)
            symbols = symbols_from_numbers(row.get("atomic_numbers"))
            forces = row.get("atomic_forces")
            if (
                symbols is None
                or int(row.get("nsites") or 0) != len(symbols)
                or len(symbols) > MAX_ATOMS
                or not finite_array(row.get("positions"), (3,))
                or not finite_array(row.get("cell"), (3, 3))
                or not finite_array(forces, (3,))
                or np.max(np.abs(np.asarray(forces, dtype=float))) <= 1e-8
                or not math.isfinite(float(row.get("energy") or math.nan))
            ):
                continue
            config_id = str(row.get("configuration_id") or f"{block_id}-step{step}-file{file_ix}")
            groups[block_id].append(build_case(
                source="omat24-validation-aimd-pbe-1000-nvt", block_id=block_id,
                config_id=config_id, step=step, symbols=symbols, positions=row["positions"],
                cell=row["cell"], pbc=row.get("pbc", [True, True, True]),
                energy_total_ev=float(row["energy"]), forces=forces, source_row=source_row,
                extra={"method": row.get("method"), "property_id": row.get("property_id")},
            ))
    return groups


SOURCES: list[tuple[str, Path, Callable[[Path], dict[str, list[dict[str, Any]]]], str, str]] = [
    (
        "mptrj",
        INPUTS / "mptrj-test.parquet",
        collect_mptrj,
        "nimashoghi/mptrj",
        f"https://huggingface.co/datasets/nimashoghi/mptrj/resolve/{MPTRJ_REVISION}/data/test-00000-of-00001.parquet",
    ),
    (
        "matpes-pbe-2025.2",
        INPUTS / "matpes-pbe-2025.2.parquet",
        collect_matpes,
        "colabfit/MatPES-PBE-2025.2",
        "https://huggingface.co/datasets/colabfit/MatPES-PBE-2025.2/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet",
    ),
    (
        "omat24-validation-aimd-pbe-1000-nvt",
        INPUTS / "omat24-validation-aimd-pbe-1000-nvt.parquet",
        collect_omat24,
        "colabfit/OMat24_validation_aimd-from-PBE-1000-nvt",
        "https://huggingface.co/datasets/colabfit/OMat24_validation_aimd-from-PBE-1000-nvt/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet",
    ),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_manifest_hash(manifest: dict[str, Any]) -> str:
    unlocked = dict(manifest)
    unlocked.pop("manifest_hash", None)
    payload = json.dumps(unlocked, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    canonical = json.loads(CANONICAL.read_text())
    lock: dict[str, Any] = {
        "schema": "lupine.a6_decide.input_lock.v1",
        "sampling": {
            "salt": SALT,
            "eligible_block_rule": f">={N_CONFIGS} finite nonzero-force configs, <= {MAX_ATOMS} atoms, Z <= {MAX_ATOMIC_NUMBER}",
            "block_selection": f"lowest SHA-256({SALT}|source|block_id), first {N_BLOCKS}",
            "config_selection": f"{N_CONFIGS} evenly spaced configurations in trajectory-step order",
        },
        "sources": {},
    }
    for source, path, collector, dataset_id, url in SOURCES:
        groups = collector(path)
        eligible = {block: rows for block, rows in groups.items() if len(rows) >= N_CONFIGS}
        ranked = sorted(eligible, key=lambda block: (hash_rank(source, block), block))
        if len(ranked) < N_BLOCKS:
            if source == "mptrj":
                valid_counts = [len(rows) for rows in groups.values()]
                lock["sources"][source] = {
                    "dataset": dataset_id,
                    "url": url,
                    **SOURCE_IDENTITIES[source],
                    "parquet_path": str(path.relative_to(ROOT)),
                    "parquet_sha256": sha256_file(path),
                    "status": "inconclusive",
                    "failed_gate": (
                        f"MPtrj test has {len(eligible)} trajectory blocks with >= {N_CONFIGS} "
                        f"eligible configurations; frozen minimum is {MIN_BLOCKS} independently "
                        f"bootstrappable blocks with >= {N_CONFIGS} configurations per retained "
                        f"block and >= {MIN_CONFIGURATIONS} total configurations; deterministic "
                        f"sampling target is {N_BLOCKS} blocks"
                    ),
                    "eligible_blocks": len(eligible),
                    "valid_blocks": len(groups),
                    "valid_configurations": sum(valid_counts),
                    "maximum_valid_configurations_per_block": max(valid_counts, default=0),
                    "selected_blocks": [],
                    "selected_configs": 0,
                    "manifest_path": None,
                    "manifest_sha256": None,
                    "manifest_content_hash": None,
                }
                print(json.dumps({
                    "source": source,
                    "status": "inconclusive",
                    "eligible_blocks": len(eligible),
                    "valid_blocks": len(groups),
                    "valid_configurations": sum(valid_counts),
                    "maximum_valid_configurations_per_block": max(valid_counts, default=0),
                }, sort_keys=True))
                continue
            raise RuntimeError(f"{source}: only {len(ranked)} eligible blocks")
        selected_blocks = ranked[:N_BLOCKS]
        cases = [case for block in selected_blocks for case in evenly_spaced(eligible[block], N_CONFIGS)]
        if len(cases) != N_BLOCKS * N_CONFIGS:
            raise AssertionError(f"{source}: wrong case count")
        manifest = json.loads(json.dumps(canonical))
        manifest["fixture_id"] = f"a6-decide-{source}-v1"
        manifest["title"] = f"A6-DECIDE deterministic multi-config force fixture: {source}"
        manifest["description"] = "Preregistered force-residual trajectory sample for the A6 configuration-space bridge decision."
        manifest["reference_provenance"] = {
            "a6_source": {
                "dataset": dataset_id,
                "parquet_url": url,
                "parquet_sha256": sha256_file(path),
                "sampling_salt": SALT,
                "selected_blocks": selected_blocks,
                **SOURCE_IDENTITIES[source],
            },
            "inherited_nonexecuted_rows": canonical["reference_provenance"],
        }
        manifest["row_fixtures"]["forces"] = {"structures": cases}
        manifest["row_specs"]["forces"]["min_cases"] = N_BLOCKS * N_CONFIGS
        manifest["metadata"] = {
            "source": source,
            "structure_count": sum(len(group["structures"]) for group in manifest["row_fixtures"].values()),
            "force_structure_count": len(cases),
            "trajectory_block_count": len(selected_blocks),
            "configs_per_block": N_CONFIGS,
            "max_atoms": MAX_ATOMS,
            "max_atomic_number": MAX_ATOMIC_NUMBER,
            "sampling_salt": SALT,
        }
        manifest["manifest_hash"] = "sha256:" + canonical_manifest_hash(manifest)
        output = OUTPUTS / f"{source}.manifest.json"
        output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        lock["sources"][source] = {
            "dataset": dataset_id,
            "url": url,
            **SOURCE_IDENTITIES[source],
            "parquet_path": str(path.relative_to(ROOT)),
            "parquet_sha256": sha256_file(path),
            "eligible_blocks": len(eligible),
            "selected_blocks": selected_blocks,
            "selected_configs": len(cases),
            "manifest_path": str(output.relative_to(ROOT)),
            "manifest_sha256": sha256_file(output),
            "manifest_content_hash": manifest["manifest_hash"],
        }
        print(json.dumps({"source": source, "eligible_blocks": len(eligible), "blocks": len(selected_blocks), "configs": len(cases), "manifest": str(output)}, sort_keys=True))
    lock_path = OUTPUTS / "input-lock.json"
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(lock_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
