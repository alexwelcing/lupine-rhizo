#!/usr/bin/env python3
"""Convergence-loosening revalidation runner for the Z1 sparse-DFT pilot (path 16).

Governing documents: docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md
(§A4: convergence-loosening requires this one-path revalidation as its own
future amendment) on top of the frozen base protocol
(docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md). Machinery
(panel loading, checkpoint idiom, memory guard, frozen selection logic) is
reused from gcp/sparse-dft-pilot/union_pilot.py and
gcp/mlip-cell-runner/z1_sparse_dft.py.

WHAT THIS DOES
--------------
Once the frozen-setting sweep lands path 16's anchors — receipt expected at
/tmp/z1-sparse-local/chgnet/path-16.json (schema: rows[].anchors[] with
index/gpaw_energy_ev/reference_energy_ev, rows[].sparse_barrier_ev, plus
model_min_index/model_max_index/window/short_path_fallback; see path-7.json
in the same directory for a complete example) — this runner re-evaluates
THE SAME anchor images under two single-knob loosenings of the frozen GPAW
settings (mode=fd, h=0.18, kpts=(2,2,2), xc=PBE):

- variant-g: Gamma-point only, kpts=(1,1,1); every other setting frozen.
- variant-h: grid spacing h=0.20; every other setting frozen.

The receipt's anchor set is validated against the frozen selection logic
(build_anchor_set over the receipt's own model_min_index/model_max_index)
and against the cached panel's reference profile, so both barriers are
max−min over exactly the same anchor indices, honoring the receipt's
window/short_path_fallback semantics.

Adoption criterion (pilot plan): |variant sparse barrier − frozen sparse
barrier| <= 5 meV → the loosening is adoptable, judged SEPARATELY per
variant. The frozen barrier comes from the receipt (validated for internal
consistency); nothing frozen-setting is recomputed.

Checkpoints: /tmp/z1-revalidation/<variant>/anchor-<j>.json — idempotent
resume (completed anchors are skipped; failed/skipped-memory are retried),
serial execution (one GPAW evaluation at a time, ever), same memory guard
as union_pilot.py (skip-and-record when MemAvailable < --min-free-gb).
The verdict report lands at /tmp/z1-revalidation/revalidation-report.json.

OPERATOR USAGE (run from the repo root, /home/alex/Dev/lupine/lupine-rhizo)
---------------------------------------------------------------------------
1. Dry run — lists what would be computed per variant, touches no GPAW:

   .venv/bin/python gcp/sparse-dft-pilot/revalidate_convergence.py \
       --receipt /tmp/z1-sparse-local/chgnet/path-16.json \
       --local /tmp/z1-union-local/inputs \
       --dry-run

2. Real run — serial GPAW single-points (all of variant-g, then variant-h),
   checkpointing per anchor; safe to interrupt and re-run:

   .venv/bin/python gcp/sparse-dft-pilot/revalidate_convergence.py \
       --receipt /tmp/z1-sparse-local/chgnet/path-16.json \
       --local /tmp/z1-union-local/inputs

3. Assemble-only — recompute the verdict from existing checkpoints (no GPAW):

   .venv/bin/python gcp/sparse-dft-pilot/revalidate_convergence.py \
       --receipt /tmp/z1-sparse-local/chgnet/path-16.json \
       --local /tmp/z1-union-local/inputs \
       --assemble-only

All defaults already point at the expected locations, so once path-16.json
has landed the bare forms also work:

   .venv/bin/python gcp/sparse-dft-pilot/revalidate_convergence.py --dry-run
   .venv/bin/python gcp/sparse-dft-pilot/revalidate_convergence.py

GPAW is imported lazily inside the energy function only; --dry-run,
--assemble-only, and the test suite never touch it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

import union_pilot as up  # noqa: E402  (its import wires z1_sparse_dft onto sys.path)
from z1_sparse_dft import FROZEN_GPAW_PARAMS, build_anchor_set  # noqa: E402

SCHEMA_ANCHOR = "lupine.z1.revalidation.anchor.v1"
SCHEMA_REPORT = "lupine.z1.revalidation.report.v1"
AMENDMENT = "docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md"

DEFAULT_RECEIPT = Path("/tmp/z1-sparse-local/chgnet/path-16.json")
DEFAULT_LOCAL = Path("/tmp/z1-union-local/inputs")
DEFAULT_WORKDIR = Path("/tmp/z1-revalidation")
DEFAULT_PATH_INDEX = 16

# Adoption criterion (pilot plan): the loosened-setting sparse barrier must
# stay within this many meV of the frozen-setting sparse barrier.
ADOPTION_THRESHOLD_MEV = 5.0

# Barrier/barrier consistency checks are exact-recompute comparisons; the
# tolerance only covers float round-trips through JSON.
BARRIER_MATCH_TOLERANCE_EV = 1e-6

VARIANTS: dict[str, dict] = {
    "variant-g": {
        "label": "G",
        "description": "Gamma-point only (kpts=(1,1,1)); all other settings frozen",
        "overrides": {"kpts": (1, 1, 1)},
    },
    "variant-h": {
        "label": "H",
        "description": "grid spacing h=0.20 (frozen: 0.18); all other settings frozen",
        "overrides": {"h": 0.20},
    },
    "variant-gh": {
        "label": "GH",
        "description": "combined Gamma + h=0.20 (kpts=(1,1,1), h=0.20); all other settings frozen",
        "overrides": {"kpts": (1, 1, 1), "h": 0.20},
    },
}


class ReceiptError(ValueError):
    """The path receipt failed validation against the panel/frozen protocol."""


def variant_params(variant: str) -> dict:
    """Frozen GPAW params with exactly one knob loosened, computed at call time."""
    params = dict(FROZEN_GPAW_PARAMS)
    params.update(VARIANTS[variant]["overrides"])
    return params


def params_json(params: dict) -> dict:
    return {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in params.items()
    }


# --- Inputs --------------------------------------------------------------------

def load_panel(local: Path) -> dict:
    """The cached locked panel (model artifacts are not needed here)."""
    panel_path = local / "panel.lock.json"
    if not panel_path.is_file():
        raise SystemExit(f"panel cache not found: {panel_path}")
    return json.loads(panel_path.read_text(encoding="utf-8"))


def load_revalidation_target(receipt_path: Path, panel: dict, path_index: int) -> dict:
    """Validate the path receipt against the panel and the frozen selection.

    Fail-closed: any identity, schema, or consistency problem raises
    ReceiptError — a revalidation computed on a mismatched anchor set would
    be worse than none. Returns the validated target summary.
    """
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(
            f"receipt not found: {receipt_path} — the frozen-setting sweep "
            "has not landed this path yet; re-run once it completes"
        )
    except json.JSONDecodeError as error:
        raise ReceiptError(f"{receipt_path}: not valid JSON: {error}")

    paths = panel.get("paths", [])
    if not 0 <= path_index < len(paths):
        raise SystemExit(
            f"panel has {len(paths)} paths; --path-index {path_index} is out of range"
        )
    path = paths[path_index]
    path_id = path["path_id"]
    images = path["input_images"]
    image_count = len(images)
    reference = path.get("reference", {}).get("energies_ev")
    if (
        not isinstance(reference, list)
        or len(reference) != image_count
        or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in reference)
    ):
        raise ReceiptError(
            f"panel path {path_index} ({path_id}) lacks a reference.energies_ev "
            "profile aligned with input_images"
        )
    reference = [float(v) for v in reference]

    rows = receipt.get("rows")
    if not isinstance(rows, list):
        raise ReceiptError(f"{receipt_path}: missing 'rows' list")
    matching = [r for r in rows if isinstance(r, dict) and r.get("path_id") == path_id]
    if not matching:
        seen = [r.get("path_id") for r in rows if isinstance(r, dict)]
        raise ReceiptError(
            f"no row with path_id {path_id!r} (panel path {path_index}); "
            f"receipt rows carry: {seen}"
        )
    if len(matching) > 1:
        raise ReceiptError(f"{len(matching)} rows claim path_id {path_id!r}; ambiguous")
    row = matching[0]
    if row.get("status") != "completed":
        raise ReceiptError(f"receipt row status is {row.get('status')!r}, not 'completed'")

    anchors = row.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise ReceiptError("receipt row carries no anchors")
    by_index: dict[int, dict] = {}
    for anchor in anchors:
        index = anchor.get("index")
        energy = anchor.get("gpaw_energy_ev")
        anchor_reference = anchor.get("reference_energy_ev")
        if (
            not isinstance(index, int)
            or not 0 <= index < image_count
            or not isinstance(energy, (int, float))
            or not math.isfinite(energy)
        ):
            raise ReceiptError(f"malformed anchor entry: {anchor!r}")
        if index in by_index:
            raise ReceiptError(f"duplicate anchor index {index}")
        if not isinstance(anchor_reference, (int, float)) or abs(
            float(anchor_reference) - reference[index]
        ) > up.REFERENCE_MATCH_TOLERANCE_EV:
            raise ReceiptError(
                f"anchor {index}: reference {anchor_reference} != panel {reference[index]}"
            )
        by_index[index] = {
            "gpaw_energy_ev": float(energy),
            "reference_energy_ev": float(anchor_reference),
        }

    # The anchor set must be exactly what the frozen selection logic produces
    # from the receipt's own declared extrema — same window, same fallback.
    model_min = row.get("model_min_index")
    model_max = row.get("model_max_index")
    if not all(isinstance(v, int) and 0 <= v < image_count for v in (model_min, model_max)):
        raise ReceiptError(
            f"model_min_index/model_max_index missing or out of range: "
            f"{model_min!r}/{model_max!r}"
        )
    expected = build_anchor_set(image_count, model_min, model_max)
    if sorted(by_index) != expected["anchor_indices"]:
        raise ReceiptError(
            f"anchor set {sorted(by_index)} != frozen selection "
            f"{expected['anchor_indices']} for model_min={model_min}, "
            f"model_max={model_max}, images={image_count}"
        )
    if row.get("window") != expected["window"]:
        raise ReceiptError(
            f"receipt window {row.get('window')!r} != frozen {expected['window']}"
        )
    if row.get("short_path_fallback") != expected["short_path_fallback"]:
        raise ReceiptError(
            f"receipt short_path_fallback {row.get('short_path_fallback')!r} "
            f"!= frozen {expected['short_path_fallback']}"
        )

    frozen_barrier = row.get("sparse_barrier_ev")
    if not isinstance(frozen_barrier, (int, float)) or not math.isfinite(frozen_barrier):
        raise ReceiptError(f"missing/non-finite sparse_barrier_ev: {frozen_barrier!r}")
    recomputed = (
        max(a["gpaw_energy_ev"] for a in by_index.values())
        - min(a["gpaw_energy_ev"] for a in by_index.values())
    )
    if abs(float(frozen_barrier) - recomputed) > BARRIER_MATCH_TOLERANCE_EV:
        raise ReceiptError(
            f"receipt sparse_barrier_ev {frozen_barrier} != max-min over its "
            f"anchors {recomputed}"
        )

    return {
        "path_index": path_index,
        "path_id": path_id,
        "chemical_system": path.get("chemical_system"),
        "image_count": image_count,
        "anchor_indices": sorted(by_index),
        "anchors": by_index,
        "model_min_index": model_min,
        "model_max_index": model_max,
        "window": expected["window"],
        "short_path_fallback": expected["short_path_fallback"],
        "frozen_barrier_ev": float(frozen_barrier),
        "reference_barrier_ev": float(path["reference_barrier_ev"]),
    }


# --- Per-anchor checkpoints ------------------------------------------------------

def anchor_checkpoint_path(workdir: Path, variant: str, anchor_index: int) -> Path:
    return workdir / variant / f"anchor-{anchor_index}.json"


def usable_variant_energy(checkpoint: dict | None) -> float | None:
    """Energy from a checkpoint when its status makes it trustworthy."""
    if checkpoint is None or checkpoint.get("status") not in up.USABLE_STATUSES:
        return None
    energy = checkpoint.get("variant_energy_ev")
    if not isinstance(energy, (int, float)) or not math.isfinite(energy):
        return None
    return float(energy)


def checkpoint_identity_ok(
    checkpoint: dict | None,
    target: dict,
    variant: str,
    anchor_index: int,
) -> bool:
    """True only when the checkpoint provably belongs to this target/variant/
    anchor with the params this run would execute — guards stale-workdir reuse."""
    if checkpoint is None:
        return False
    if checkpoint.get("path_id") != target["path_id"]:
        return False
    if checkpoint.get("path_index") != target["path_index"]:
        return False
    if checkpoint.get("anchor_index") != anchor_index:
        return False
    if checkpoint.get("variant") != variant:
        return False
    return checkpoint.get("gpaw_params") == params_json(variant_params(variant))


def variant_record(
    target: dict,
    variant: str,
    anchor_index: int,
    status: str,
    energy: float | None,
    wall_seconds: float | None,
    source: str,
    error: str | None = None,
) -> dict:
    anchor = target["anchors"][anchor_index]
    frozen = anchor["gpaw_energy_ev"]
    record = {
        "schema": SCHEMA_ANCHOR,
        "path_index": target["path_index"],
        "path_id": target["path_id"],
        "anchor_index": anchor_index,
        "variant": variant,
        "variant_label": VARIANTS[variant]["label"],
        "status": status,
        "variant_energy_ev": energy,
        "frozen_gpaw_energy_ev": frozen,
        "reference_energy_ev": anchor["reference_energy_ev"],
        "shift_vs_frozen_ev": (energy - frozen) if energy is not None else None,
        "wall_seconds": wall_seconds,
        "gpaw_params": params_json(variant_params(variant)),
        "source": source,
        "recorded_at": up.utc_now(),
    }
    if error is not None:
        record["error"] = error
    return record


# --- GPAW evaluation (lazy; the only place gpaw is touched) --------------------------

def gpaw_energy(image_record: dict, params: dict) -> float:
    from gpaw import GPAW

    from z1_barrier import atoms_from_image

    atoms = atoms_from_image(image_record)
    atoms.calc = GPAW(**params)
    energy = float(atoms.get_potential_energy())
    if not math.isfinite(energy):
        raise RuntimeError("GPAW produced a non-finite energy")
    return energy


# --- Compute loop (serial, checkpoint-per-anchor, resumable) -------------------------

def compute_variants(
    target: dict,
    panel: dict,
    workdir: Path,
    min_free_bytes: int,
    variants: list[str],
    energy_fn=gpaw_energy,
    log=print,
) -> dict:
    """Evaluate every missing variant anchor once, serially, checkpointing."""
    totals = {
        v: {"computed": 0, "resumed": 0, "failed": 0, "skipped_memory": 0}
        for v in variants
    }
    images = panel["paths"][target["path_index"]]["input_images"]
    for variant in variants:
        params = variant_params(variant)
        for anchor_index in target["anchor_indices"]:
            dest = anchor_checkpoint_path(workdir, variant, anchor_index)
            existing = up.read_checkpoint(dest)
            if (
                usable_variant_energy(existing) is not None
                and checkpoint_identity_ok(existing, target, variant, anchor_index)
            ):
                totals[variant]["resumed"] += 1
                continue
            free = up.available_memory_bytes()
            if free is not None and free < min_free_bytes:
                up.write_checkpoint(
                    dest,
                    variant_record(
                        target,
                        variant,
                        anchor_index,
                        up.STATUS_SKIPPED_MEMORY,
                        None,
                        None,
                        source="gpaw",
                        error=(
                            f"MemAvailable {free / 1024**3:.2f} GiB under "
                            f"threshold {min_free_bytes / 1024**3:.2f} GiB"
                        ),
                    ),
                )
                totals[variant]["skipped_memory"] += 1
                log(f"  {variant} anchor-{anchor_index}: "
                    f"skipped-memory ({free / 1024**3:.2f} GiB free)")
                continue
            started = time.time()
            try:
                energy = float(energy_fn(images[anchor_index], params))
            except Exception as error:  # noqa: BLE001 — recorded, never imputed
                up.write_checkpoint(
                    dest,
                    variant_record(
                        target,
                        variant,
                        anchor_index,
                        up.STATUS_FAILED,
                        None,
                        round(time.time() - started, 1),
                        source="gpaw",
                        error=f"{error.__class__.__name__}: {error}",
                    ),
                )
                totals[variant]["failed"] += 1
                log(f"  {variant} anchor-{anchor_index}: FAILED {error}")
                continue
            up.write_checkpoint(
                dest,
                variant_record(
                    target,
                    variant,
                    anchor_index,
                    up.STATUS_COMPLETED,
                    energy,
                    round(time.time() - started, 1),
                    source="gpaw",
                ),
            )
            totals[variant]["computed"] += 1
            log(f"  {variant} anchor-{anchor_index}: "
                f"{energy:.6f} eV ({time.time() - started:.0f}s)")
    return totals


# --- Assembly (offline, from the checkpoint pool) -----------------------------------------

def assemble_variant(target: dict, workdir: Path, variant: str) -> dict:
    """One variant's sparse barrier from its checkpoints, over the receipt's
    exact anchor indices, and the 5 meV adoption verdict vs the frozen barrier."""
    table = []
    energies: dict[int, float] = {}
    missing = []
    for anchor_index in target["anchor_indices"]:
        anchor = target["anchors"][anchor_index]
        checkpoint = up.read_checkpoint(anchor_checkpoint_path(workdir, variant, anchor_index))
        energy = (
            usable_variant_energy(checkpoint)
            if checkpoint_identity_ok(checkpoint, target, variant, anchor_index)
            else None
        )
        if energy is None:
            missing.append(anchor_index)
        else:
            energies[anchor_index] = energy
        table.append({
            "anchor_index": anchor_index,
            "reference_energy_ev": anchor["reference_energy_ev"],
            "frozen_energy_ev": anchor["gpaw_energy_ev"],
            "variant_energy_ev": energy,
            "shift_vs_frozen_mev": (
                (energy - anchor["gpaw_energy_ev"]) * 1000.0 if energy is not None else None
            ),
            "status": checkpoint.get("status") if checkpoint else "missing",
        })

    complete = not missing
    barrier = None
    delta_mev = None
    if complete:
        barrier = max(energies.values()) - min(energies.values())
        delta_mev = (barrier - target["frozen_barrier_ev"]) * 1000.0
    if not complete:
        verdict = "incomplete"
    elif abs(delta_mev) <= ADOPTION_THRESHOLD_MEV:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return {
        "label": VARIANTS[variant]["label"],
        "description": VARIANTS[variant]["description"],
        "gpaw_params": params_json(variant_params(variant)),
        "anchors": table,
        "anchors_evaluated": sorted(energies),
        "anchors_missing": missing,
        "complete": complete,
        "sparse_barrier_ev": barrier,
        "delta_vs_frozen_mev": delta_mev,
        "abs_delta_vs_frozen_mev": abs(delta_mev) if delta_mev is not None else None,
        "adoptable": (abs(delta_mev) <= ADOPTION_THRESHOLD_MEV) if complete else None,
        "verdict": verdict,
    }


def build_report(
    target: dict,
    workdir: Path,
    variants: list[str],
    receipt_path: Path,
    local: Path,
) -> dict:
    per_variant = {v: assemble_variant(target, workdir, v) for v in variants}
    verdicts = [info["verdict"] for info in per_variant.values()]
    both_adoptable = (
        all(info["adoptable"] for info in per_variant.values())
        if set(variants) == set(VARIANTS) and all(v != "incomplete" for v in verdicts)
        else None
    )
    return {
        "schema": SCHEMA_REPORT,
        "recorded_at": up.utc_now(),
        "amendment": AMENDMENT,
        "purpose": "one-path convergence-loosening revalidation (amendment §A4)",
        "inputs": {
            "receipt": str(receipt_path),
            "panel": str(local / "panel.lock.json"),
        },
        "path_index": target["path_index"],
        "path_id": target["path_id"],
        "chemical_system": target["chemical_system"],
        "image_count": target["image_count"],
        "anchor_indices": target["anchor_indices"],
        "model_min_index": target["model_min_index"],
        "model_max_index": target["model_max_index"],
        "window": target["window"],
        "short_path_fallback": target["short_path_fallback"],
        "adoption_threshold_mev": ADOPTION_THRESHOLD_MEV,
        "frozen": {
            "gpaw_params": params_json(dict(FROZEN_GPAW_PARAMS)),
            "sparse_barrier_ev": target["frozen_barrier_ev"],
            "source": f"receipt:{receipt_path}",
        },
        "reference_barrier_ev": target["reference_barrier_ev"],
        "variants": per_variant,
        "both_adoptable": both_adoptable,
    }


def print_summary(report: dict, log=print) -> None:
    log(f"== convergence revalidation: path-{report['path_index']} "
        f"{report['path_id']} ({report['chemical_system']}, "
        f"{report['image_count']} images) ==")
    log(f"anchors {report['anchor_indices']} (window={report['window']}, "
        f"short_path_fallback={report['short_path_fallback']})")
    log(f"frozen sparse barrier: {report['frozen']['sparse_barrier_ev']:.6f} eV "
        f"(from receipt; reference barrier {report['reference_barrier_ev']:.6f} eV)")
    for variant, info in report["variants"].items():
        barrier = info["sparse_barrier_ev"]
        delta = info["delta_vs_frozen_mev"]
        if barrier is None:
            log(f"{variant}: incomplete — missing anchors {info['anchors_missing']}")
            continue
        log(f"{variant}: barrier {barrier:.6f} eV, delta {delta:+.1f} meV "
            f"-> {info['verdict']} "
            f"({'adoptable' if info['adoptable'] else 'NOT adoptable'}; "
            f"{info['description']})")
    header = (f"{'anchor':>6} {'reference':>12} {'frozen':>12}"
              + "".join(f" {v + ' energy':>14} {v + ' shift':>10}"
                        for v in report["variants"]))
    log(header + "   (energies eV, shifts meV vs frozen)")
    per_anchor = {v: {a["anchor_index"]: a for a in info["anchors"]}
                  for v, info in report["variants"].items()}
    first = next(iter(report["variants"]))
    for anchor_index in report["anchor_indices"]:
        base = per_anchor[first][anchor_index]
        line = (f"{anchor_index:>6} {base['reference_energy_ev']:>12.6f} "
                f"{base['frozen_energy_ev']:>12.6f}")
        for variant in report["variants"]:
            entry = per_anchor[variant][anchor_index]
            energy = entry["variant_energy_ev"]
            shift = entry["shift_vs_frozen_mev"]
            line += (f" {energy:>14.6f} {shift:>+10.2f}"
                     if energy is not None else f" {'—':>14} {'—':>10}")
        log(line)


# --- Dry run ----------------------------------------------------------------------------

def dry_run(
    target: dict, workdir: Path, variants: list[str], minutes_per_anchor: float, log=print
) -> dict:
    """Report per-variant anchor coverage and remaining cost without touching GPAW."""
    per_variant = {}
    total_todo = 0
    log(f"path-{target['path_index']} {target['path_id']}: "
        f"anchors {target['anchor_indices']} "
        f"(window={target['window']}, short_path_fallback={target['short_path_fallback']})")
    for variant in variants:
        done = []
        todo = []
        for anchor_index in target["anchor_indices"]:
            checkpoint = up.read_checkpoint(
                anchor_checkpoint_path(workdir, variant, anchor_index)
            )
            (done if (
                usable_variant_energy(checkpoint) is not None
                and checkpoint_identity_ok(checkpoint, target, variant, anchor_index)
            ) else todo).append(
                anchor_index
            )
        total_todo += len(todo)
        per_variant[variant] = {
            "anchors_done": done,
            "anchors_to_compute": todo,
            "estimated_hours": round(len(todo) * minutes_per_anchor / 60.0, 1),
        }
        log(f"{variant} ({VARIANTS[variant]['description']}): "
            f"done={done} todo={todo} "
            f"ETA {len(todo) * minutes_per_anchor / 60.0:.1f} h")
    total_hours = total_todo * minutes_per_anchor / 60.0
    log(f"total: {total_todo} GPAW evaluations to compute, ETA {total_hours:.1f} h "
        f"serial at {minutes_per_anchor:.0f} min/evaluation "
        f"(checkpoints under {workdir}/<variant>/)")
    return {
        "path_index": target["path_index"],
        "anchors_per_variant": len(target["anchor_indices"]),
        "evaluations_to_compute": total_todo,
        "estimated_hours": round(total_hours, 1),
        "per_variant": per_variant,
    }


# --- CLI ---------------------------------------------------------------------------------

def parse_variants(spec: str) -> list[str]:
    variants = [v.strip() for v in spec.split(",") if v.strip()]
    unknown = [v for v in variants if v not in VARIANTS]
    if unknown:
        raise SystemExit(f"unknown variant(s) {unknown}; known: {sorted(VARIANTS)}")
    if not variants:
        raise SystemExit("no variants selected")
    return variants


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT,
                        help="path receipt from the frozen-setting sweep "
                             f"(default {DEFAULT_RECEIPT})")
    parser.add_argument("--local", type=Path, default=DEFAULT_LOCAL,
                        help="offline input dir with panel.lock.json "
                             f"(default {DEFAULT_LOCAL})")
    parser.add_argument("--path-index", type=int, default=DEFAULT_PATH_INDEX,
                        help=f"panel index of the revalidated path (default {DEFAULT_PATH_INDEX})")
    parser.add_argument("--workdir", type=Path, default=DEFAULT_WORKDIR,
                        help=f"checkpoint + report root (default {DEFAULT_WORKDIR})")
    parser.add_argument("--variants", default=",".join(VARIANTS),
                        help="comma list of variants to run "
                             f"(default: all — {','.join(VARIANTS)})")
    parser.add_argument("--out", type=Path, default=None,
                        help="report JSON path (default <workdir>/revalidation-report.json)")
    parser.add_argument("--min-free-gb", type=float, default=up.DEFAULT_MIN_FREE_GB,
                        help="skip an anchor when MemAvailable is under this (GiB)")
    parser.add_argument("--minutes-per-anchor", type=float,
                        default=up.DEFAULT_MINUTES_PER_ANCHOR,
                        help="dry-run cost rate (measured path-16 pace: 90-120)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report anchor coverage and cost; do not touch GPAW")
    parser.add_argument("--assemble-only", action="store_true",
                        help="recompute the verdict from existing checkpoints only")
    args = parser.parse_args()

    workdir = args.workdir
    workdir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or (workdir / "revalidation-report.json")
    variants = parse_variants(args.variants)

    panel = load_panel(args.local)
    try:
        target = load_revalidation_target(args.receipt, panel, args.path_index)
    except ReceiptError as error:
        raise SystemExit(f"receipt invalid: {error}")

    if args.dry_run:
        report = dry_run(target, workdir, variants, args.minutes_per_anchor)
        print(json.dumps({k: v for k, v in report.items() if k != "per_variant"}, indent=1))
        return 0

    if not args.assemble_only:
        totals = compute_variants(
            target,
            panel,
            workdir,
            min_free_bytes=int(args.min_free_gb * 1024**3),
            variants=variants,
            energy_fn=gpaw_energy,
        )
        print(f"compute: {json.dumps(totals)}")

    report = build_report(target, workdir, variants, args.receipt, args.local)
    payload = json.dumps(report, indent=1, sort_keys=True) + "\n"
    report["report_sha256"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print_summary(report)
    print(f"report written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
