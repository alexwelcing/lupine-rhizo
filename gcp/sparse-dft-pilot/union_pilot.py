#!/usr/bin/env python3
"""Union-anchor sparse-DFT pilot driver (Amendment 01, 2026-07-21).

Implements docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md on top of
the frozen base protocol (docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md):

- Per active path (the 30-path locked panel minus the seven deferred
  large-cell paths), the anchor universe is the UNION of all available
  models' frozen anchor sets (selection logic imported verbatim from
  gcp/mlip-cell-runner/z1_sparse_dft.py), EXTENDED to every image index
  when the path has <= DENSE_EXTENSION_IMAGE_THRESHOLD images (A3.2).
- Each unique anchor is evaluated ONCE (GPAW single-point, frozen fd/h=0.18/
  kpts=(2,2,2)/PBE settings), serially, checkpointed per anchor under
  <workdir>/anchors/path-<i>/anchor-<j>.json. Re-runs skip completed
  anchors (idempotent resume); existing run_pilot.py receipts are
  IMPORTED, never recomputed.
- Assembly (offline, also standalone via --assemble-only): per model per
  path, sparse barrier from the shared pool via the frozen selection;
  dense same-engine barrier (max-min over all images' GPAW energies);
  same-engine (primary, A1) and VASP-referenced (secondary) errors; T1
  offset mean/wander per path plus the T1 convention-wander gate verdict
  (clean / contaminated / insufficient_data — REPORTED per path, never a
  refusal; tools/analysis/t1_wander.py); WIN/strong-WIN verdicts at
  <=40/<=15 meV vs the same-engine basis.
- Memory guard: an anchor is skipped with status "skipped-memory" when
  MemAvailable is under --min-free-gb, rather than crashing. Serial
  execution only — one GPAW evaluation at a time, ever.
- Settings overrides (pending amendment 02): --kpts / --h replace the frozen
  k-point mesh / grid spacing for the whole run — everything else stays
  frozen. Gamma-only example:
      python union_pilot.py --kpts 1,1,1 --dry-run
  Every checkpoint records the params it was produced under and is trusted
  only when those equal the active params — a checkpoint is never silently
  reused across different parameter sets. Receipts whose
  summary.gpaw_params differ from the active params are rejected wholesale.

This driver supersedes run_pilot.py for the remaining paths; run_pilot.py's
completed results remain valid receipts and are imported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
for _candidate in (_HERE.parent, _HERE.parents[1] / "mlip-cell-runner"):
    if (_candidate / "z1_sparse_dft.py").exists():
        sys.path.insert(0, str(_candidate))
        break
for _candidate in (_REPO_ROOT / "tools" / "analysis", _HERE.parent):
    if (_candidate / "t1_wander.py").exists():
        sys.path.insert(0, str(_candidate))
        break

from t1_wander import analyze_offsets  # noqa: E402

from z1_sparse_dft import (  # noqa: E402
    FROZEN_GPAW_PARAMS,
    STRONG_WIN_THRESHOLD_MEV,
    WIN_THRESHOLD_MEV,
    build_anchor_set,
    select_extrema,
)

SCHEMA_ANCHOR = "lupine.z1.union_pilot.anchor.v1"
SCHEMA_CAMPAIGN = "lupine.z1.union_pilot.campaign.v1"
PREREGISTRATION = "docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md"
AMENDMENT = "docs/plans/2026-07-21-sparse-dft-pilot-amendment-01.md"

GCS_PANEL = "gs://shed-489901-atlas-inputs/z1/data/candidates/z1_nebdft2k_barriers.lock.json"
GCS_RESULT = "gs://shed-489901-atlas-outputs/z1/campaign-float64/{model}/cell_result.json"
MODELS = ["chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium"]

DEFAULT_DEFERRED_JSON = _REPO_ROOT / "data/candidates/z1-sparse-dft-deferred.json"
DEFAULT_RECEIPTS_DIR = Path("/tmp/z1-sparse-local/chgnet")

# Amendment A3.2: paths this short extend the anchor universe to every image.
DENSE_EXTENSION_IMAGE_THRESHOLD = 7
DEFAULT_MIN_FREE_GB = 3.0
DEFAULT_MINUTES_PER_ANCHOR = 90.0  # measured path-16 pace ~1.5-2 h/anchor
REFERENCE_MATCH_TOLERANCE_EV = 1e-6

# Checkpoint statuses. Only USABLE_STATUSES carry a trustworthy energy and
# are skipped on resume; "failed"/"skipped-memory" anchors are retried.
STATUS_COMPLETED = "completed"
STATUS_IMPORTED = "imported"
STATUS_FAILED = "failed"
STATUS_SKIPPED_MEMORY = "skipped-memory"
USABLE_STATUSES = {STATUS_COMPLETED, STATUS_IMPORTED}

# Provenance recorded in campaign.json whenever the active settings deviate
# from the preregistration-frozen ones (pending amendment 02 adopts Gamma
# k-points after the revalidation moved the barrier -4.72 meV, within the
# <=5 meV criterion).
SETTINGS_OVERRIDE_PROVENANCE = "adopted per amendment 02"

# Active GPAW params for this process: FROZEN_GPAW_PARAMS plus any overrides
# from set_active_params. The frozen dict itself is never mutated.
_ACTIVE_PARAMS: dict = dict(FROZEN_GPAW_PARAMS)


def set_active_params(kpts: tuple | None = None, h: float | None = None) -> None:
    """Set the process-wide active GPAW params: the frozen preregistration
    settings plus the given overrides. Every knob not passed here stays at
    its frozen value; calling with no arguments restores the frozen settings.
    """
    global _ACTIVE_PARAMS
    _ACTIVE_PARAMS = dict(FROZEN_GPAW_PARAMS)
    if kpts is not None:
        if len(kpts) != 3:
            raise ValueError(f"kpts must be a 3-tuple, got {kpts!r}")
        _ACTIVE_PARAMS["kpts"] = tuple(int(v) for v in kpts)
    if h is not None:
        _ACTIVE_PARAMS["h"] = float(h)


def _normalize_value(value):
    return list(value) if isinstance(value, (tuple, list)) else value


def _normalize_params(params: dict) -> dict:
    return {key: _normalize_value(value) for key, value in params.items()}


def gpaw_params_json() -> dict:
    return _normalize_params(_ACTIVE_PARAMS)


def active_params_overridden() -> bool:
    return _normalize_params(_ACTIVE_PARAMS) != _normalize_params(FROZEN_GPAW_PARAMS)


def settings_note() -> str:
    """Human-readable provenance for a run whose active params deviate from
    the frozen preregistration settings, e.g.
    'adopted per amendment 02: kpts=(1,1,1)'."""
    overrides = ", ".join(
        f"{key}={_format_setting(_ACTIVE_PARAMS[key])}"
        for key in sorted(_ACTIVE_PARAMS)
        if _normalize_value(_ACTIVE_PARAMS[key])
        != _normalize_value(FROZEN_GPAW_PARAMS.get(key))
    )
    return f"{SETTINGS_OVERRIDE_PROVENANCE}: {overrides}"


def _format_setting(value) -> str:
    if isinstance(value, (tuple, list)):
        return "(" + ",".join(str(v) for v in value) + ")"
    return repr(value)


def params_match(checkpoint: dict | None) -> bool:
    """True only when the checkpoint's recorded gpaw_params equal the active
    params (tuples/lists normalized) — checkpoints are never silently
    trusted across different parameter sets."""
    if checkpoint is None:
        return False
    recorded = checkpoint.get("gpaw_params")
    if not isinstance(recorded, dict):
        return False
    return _normalize_params(recorded) == gpaw_params_json()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Inputs --------------------------------------------------------------------

def gsutil_cp(uri: str, dest: Path) -> None:
    """Fetch a gs:// object via the gsutil CLI (works with this box's ADC)."""
    gsutil = shutil.which("gsutil")
    if gsutil is None:
        raise RuntimeError("gsutil is not on PATH; use --local with pre-downloaded inputs")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([gsutil, "-q", "cp", uri, str(dest)], check=True)


def load_deferred_indices(path: Path) -> list[int]:
    record = json.loads(path.read_text(encoding="utf-8"))
    return sorted(p["index"] for p in record.get("deferred_paths", []))


def load_inputs(workdir: Path, local: Path | None) -> tuple[dict, dict[str, dict]]:
    """Return (panel, {model: cell_result}); downloads are cached under workdir."""
    if local is not None:
        root = local
    else:
        root = workdir / "inputs"
        panel_path = root / "panel.lock.json"
        if not panel_path.is_file():
            gsutil_cp(GCS_PANEL, panel_path)
        for model in MODELS:
            dest = root / model / "cell_result.json"
            if not dest.is_file():
                gsutil_cp(GCS_RESULT.format(model=model), dest)
    panel = json.loads((root / "panel.lock.json").read_text(encoding="utf-8"))
    artifacts = {}
    for model in MODELS:
        candidate = root / model / "cell_result.json"
        if candidate.is_file():
            artifacts[model] = json.loads(candidate.read_text(encoding="utf-8"))
    if not artifacts:
        raise RuntimeError(f"no model cell_result.json found under {root}")
    return panel, artifacts


# --- Planning (frozen selection + union + dense extension) ----------------------

def completed_profile(prediction: dict) -> list[float] | None:
    """Completed + finite energy list only (mirror of run_pilot.guided_paths)."""
    energies = prediction.get("predicted_image_energies_ev")
    if prediction.get("status") != "completed":
        return None
    if not isinstance(energies, list) or not all(
        isinstance(v, (int, float)) and math.isfinite(v) for v in energies
    ):
        return None
    return [float(v) for v in energies]


def plan_path(path_index: int, path: dict, artifacts: dict[str, dict]) -> dict:
    """Anchor universe for one path: union of model anchor sets, extended to
    every image when the path is short enough (amendment A3.2)."""
    image_count = len(path["input_images"])
    per_model: dict[str, dict] = {}
    models_missing: dict[str, str] = {}
    for model, artifact in artifacts.items():
        prediction = next(
            (p for p in artifact.get("predictions", []) if p.get("path_id") == path["path_id"]),
            None,
        )
        profile = completed_profile(prediction) if prediction is not None else None
        if profile is None or len(profile) != image_count:
            models_missing[model] = (
                "no prediction record"
                if prediction is None
                else str(prediction.get("status") or "profile_length_mismatch")
            )
            continue
        model_min, model_max = select_extrema(profile)
        anchor = build_anchor_set(image_count, model_min, model_max)
        per_model[model] = {
            "model_min_index": model_min,
            "model_max_index": model_max,
            "window": anchor["window"],
            "short_path_fallback": anchor["short_path_fallback"],
            "anchor_indices": anchor["anchor_indices"],
        }
    union_set: set[int] = set()
    for info in per_model.values():
        union_set.update(info["anchor_indices"])
    dense_extension = image_count <= DENSE_EXTENSION_IMAGE_THRESHOLD
    universe = set(union_set)
    if dense_extension:
        universe.update(range(image_count))
    return {
        "path_index": path_index,
        "path_id": path["path_id"],
        "chemical_system": path.get("chemical_system"),
        "image_count": image_count,
        "reference_energies_ev": [float(v) for v in path["reference"]["energies_ev"]],
        "reference_barrier_ev": float(path["reference_barrier_ev"]),
        "per_model": per_model,
        "models_missing": models_missing,
        "union_model_anchor_indices": sorted(union_set),
        "dense_extension_applied": dense_extension,
        "anchor_universe": sorted(universe),
    }


def build_plans(
    panel: dict, artifacts: dict[str, dict], deferred_indices: list[int]
) -> list[dict]:
    deferred = set(deferred_indices)
    return [
        plan_path(i, path, artifacts)
        for i, path in enumerate(panel["paths"])
        if i not in deferred
    ]


# --- Per-anchor checkpoints ------------------------------------------------------

def anchor_checkpoint_path(workdir: Path, path_index: int, anchor_index: int) -> Path:
    return workdir / "anchors" / f"path-{path_index}" / f"anchor-{anchor_index}.json"


def read_checkpoint(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def usable_energy(checkpoint: dict | None) -> float | None:
    """Energy from a checkpoint when its status makes it trustworthy."""
    if checkpoint is None or checkpoint.get("status") not in USABLE_STATUSES:
        return None
    energy = checkpoint.get("gpaw_energy_ev")
    if not isinstance(energy, (int, float)) or not math.isfinite(energy):
        return None
    return float(energy)


def write_checkpoint(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def anchor_record(
    plan: dict,
    anchor_index: int,
    status: str,
    energy: float | None,
    wall_seconds: float | None,
    source: str,
    error: str | None = None,
    params: dict | None = None,
) -> dict:
    reference = plan["reference_energies_ev"][anchor_index]
    record = {
        "schema": SCHEMA_ANCHOR,
        "path_index": plan["path_index"],
        "path_id": plan["path_id"],
        "anchor_index": anchor_index,
        "status": status,
        "gpaw_energy_ev": energy,
        "reference_energy_ev": reference,
        "offset_ev": (energy - reference) if energy is not None else None,
        "wall_seconds": wall_seconds,
        "gpaw_params": gpaw_params_json() if params is None else _normalize_params(params),
        "source": source,
        "recorded_at": utc_now(),
    }
    if error is not None:
        record["error"] = error
    return record


# --- Receipt import ---------------------------------------------------------------

def import_receipt(receipt_path: Path, plan: dict, workdir: Path) -> dict:
    """Map a run_pilot.py path receipt into per-anchor checkpoints.

    Validates path identity and per-anchor reference energies against the
    locked panel; never overwrites an existing usable checkpoint. The whole
    receipt is rejected when its summary.gpaw_params are missing or differ
    from the active params — energies computed under different settings are
    never imported. On a match the RECEIPT's params are stored in the
    imported checkpoint records.
    """
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    stats = {"imported": [], "skipped_existing": [], "rejected": []}
    receipt_params = (receipt.get("summary") or {}).get("gpaw_params")
    if not isinstance(receipt_params, dict):
        stats["rejected"].append(
            "receipt summary.gpaw_params missing — cannot verify settings, "
            "refusing to import"
        )
        return stats
    if _normalize_params(receipt_params) != gpaw_params_json():
        stats["rejected"].append(
            f"receipt gpaw_params {receipt_params} != active params "
            f"{gpaw_params_json()} — refusing to import across settings"
        )
        return stats
    for row in receipt.get("rows", []):
        if row.get("status") != "completed":
            continue
        if row.get("path_id") != plan["path_id"]:
            stats["rejected"].append(
                f"path_id mismatch: receipt has {row.get('path_id')}"
            )
            continue
        for anchor in row.get("anchors", []):
            index = anchor.get("index")
            energy = anchor.get("gpaw_energy_ev")
            reference = anchor.get("reference_energy_ev")
            if (
                not isinstance(index, int)
                or not 0 <= index < plan["image_count"]
                or not isinstance(energy, (int, float))
                or not math.isfinite(energy)
            ):
                stats["rejected"].append(f"malformed anchor entry: {anchor!r}")
                continue
            panel_reference = plan["reference_energies_ev"][index]
            if not isinstance(reference, (int, float)) or abs(
                float(reference) - panel_reference
            ) > REFERENCE_MATCH_TOLERANCE_EV:
                stats["rejected"].append(
                    f"anchor {index}: reference {reference} != panel {panel_reference}"
                )
                continue
            dest = anchor_checkpoint_path(workdir, plan["path_index"], index)
            existing = read_checkpoint(dest)
            if usable_energy(existing) is not None and params_match(existing):
                stats["skipped_existing"].append(index)
                continue
            write_checkpoint(
                dest,
                anchor_record(
                    plan,
                    index,
                    STATUS_IMPORTED,
                    float(energy),
                    None,  # per-anchor wall time is not recorded in receipts
                    source=f"import:{receipt_path}",
                    params=receipt_params,
                ),
            )
            stats["imported"].append(index)
    for key in ("imported", "skipped_existing"):
        stats[key] = sorted(stats[key])
    return stats


def import_receipts(receipts_dir: Path, plans: list[dict], workdir: Path) -> dict:
    """Import every path-<i>.json receipt matching an active path."""
    results = {}
    if not receipts_dir.is_dir():
        return results
    by_index = {plan["path_index"]: plan for plan in plans}
    for receipt in sorted(receipts_dir.glob("path-*.json")):
        match = re.fullmatch(r"path-(\d+)\.json", receipt.name)
        if match is None:
            continue
        plan = by_index.get(int(match.group(1)))
        if plan is None:
            continue
        results[plan["path_index"]] = import_receipt(receipt, plan, workdir)
    return results


# --- Memory guard -------------------------------------------------------------------

def available_memory_bytes(meminfo: Path = Path("/proc/meminfo")) -> int | None:
    try:
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


# --- GPAW evaluation (lazy; the only place gpaw is touched) --------------------------

def gpaw_energy(image_record: dict) -> float:
    from gpaw import GPAW

    from z1_barrier import atoms_from_image

    atoms = atoms_from_image(image_record)
    atoms.calc = GPAW(**_ACTIVE_PARAMS)
    energy = float(atoms.get_potential_energy())
    if not math.isfinite(energy):
        raise RuntimeError("GPAW produced a non-finite energy")
    return energy


# --- Compute loop (serial, checkpoint-per-anchor, resumable) -------------------------

def compute_anchors(
    plans: list[dict],
    panel: dict,
    workdir: Path,
    min_free_bytes: int,
    energy_fn=gpaw_energy,
    log=print,
) -> dict:
    """Evaluate every missing anchor once, serially, checkpointing immediately."""
    totals = {"computed": 0, "resumed": 0, "failed": 0, "skipped_memory": 0}
    for plan in plans:
        images = panel["paths"][plan["path_index"]]["input_images"]
        for anchor_index in plan["anchor_universe"]:
            dest = anchor_checkpoint_path(workdir, plan["path_index"], anchor_index)
            checkpoint = read_checkpoint(dest)
            if usable_energy(checkpoint) is not None:
                if params_match(checkpoint):
                    totals["resumed"] += 1
                    continue
                log(f"  path-{plan['path_index']} anchor-{anchor_index}: "
                    "checkpoint params differ from active params; recomputing")
            free = available_memory_bytes()
            if free is not None and free < min_free_bytes:
                write_checkpoint(
                    dest,
                    anchor_record(
                        plan,
                        anchor_index,
                        STATUS_SKIPPED_MEMORY,
                        None,
                        None,
                        source="gpaw",
                        error=(
                            f"MemAvailable {free / 1024**3:.2f} GiB under "
                            f"threshold {min_free_bytes / 1024**3:.2f} GiB"
                        ),
                    ),
                )
                totals["skipped_memory"] += 1
                log(f"  path-{plan['path_index']} anchor-{anchor_index}: "
                    f"skipped-memory ({free / 1024**3:.2f} GiB free)")
                continue
            started = time.time()
            try:
                energy = float(energy_fn(images[anchor_index]))
            except Exception as error:  # noqa: BLE001 — recorded, never imputed
                write_checkpoint(
                    dest,
                    anchor_record(
                        plan,
                        anchor_index,
                        STATUS_FAILED,
                        None,
                        round(time.time() - started, 1),
                        source="gpaw",
                        error=f"{error.__class__.__name__}: {error}",
                    ),
                )
                totals["failed"] += 1
                log(f"  path-{plan['path_index']} anchor-{anchor_index}: FAILED {error}")
                continue
            write_checkpoint(
                dest,
                anchor_record(
                    plan,
                    anchor_index,
                    STATUS_COMPLETED,
                    energy,
                    round(time.time() - started, 1),
                    source="gpaw",
                ),
            )
            totals["computed"] += 1
            log(f"  path-{plan['path_index']} anchor-{anchor_index}: "
                f"{energy:.6f} eV ({time.time() - started:.0f}s)")
    return totals


# --- Assembly (offline, from the anchor pool) -----------------------------------------

def pool_for_plan(plan: dict, workdir: Path) -> dict[int, dict]:
    """All usable checkpoints for a path, keyed by anchor index. A checkpoint
    recorded under different params than the active ones is treated as
    missing, never as usable."""
    pool: dict[int, dict] = {}
    for anchor_index in range(plan["image_count"]):
        checkpoint = read_checkpoint(
            anchor_checkpoint_path(workdir, plan["path_index"], anchor_index)
        )
        energy = usable_energy(checkpoint)
        if energy is not None and params_match(checkpoint):
            pool[anchor_index] = checkpoint
    return pool


def assemble(plan: dict, workdir: Path) -> dict:
    """Per-path assembly: per-model sparse barriers, dense same-engine barrier,
    VASP-referenced errors, and T1 offset statistics — all from the pool."""
    pool = pool_for_plan(plan, workdir)
    reference_barrier = plan["reference_barrier_ev"]

    dense_complete = len(pool) == plan["image_count"]
    dense_barrier = None
    if dense_complete:
        energies = [pool[i]["gpaw_energy_ev"] for i in range(plan["image_count"])]
        dense_barrier = max(energies) - min(energies)

    per_model = {}
    for model, info in plan["per_model"].items():
        indices = info["anchor_indices"]
        complete = all(i in pool for i in indices)
        record = {
            **info,
            "anchors_evaluated": sorted(i for i in indices if i in pool),
            "complete": complete,
        }
        if complete:
            energies = [pool[i]["gpaw_energy_ev"] for i in indices]
            sparse = max(energies) - min(energies)
            record["sparse_barrier_ev"] = sparse
            record["vasp_signed_error_mev"] = (sparse - reference_barrier) * 1000.0
            record["vasp_abs_error_mev"] = abs(record["vasp_signed_error_mev"])
            if dense_barrier is not None:
                record["same_engine_signed_error_mev"] = (sparse - dense_barrier) * 1000.0
                record["same_engine_abs_error_mev"] = abs(
                    record["same_engine_signed_error_mev"]
                )
        per_model[model] = record

    # T1 (amendment A1): per-path offset mean/wander AND the convention-
    # wander gate verdict from the same pool. The gate is a reported line
    # item (clean / contaminated / insufficient_data), never a refusal.
    gate = analyze_offsets(
        [
            (i, pool[i]["gpaw_energy_ev"], plan["reference_energies_ev"][i])
            for i in sorted(pool)
        ],
        gate_mev=WIN_THRESHOLD_MEV,
    )
    t1 = {
        "evaluated_image_count": len(pool),
        "offset_mean_mev": gate["offset_mean_mev"],
        "offset_wander_mev": gate["offset_wander_mev"],
    }
    t1_gate = {
        "wander_mev": gate["offset_wander_mev"],
        "verdict": gate["verdict"],
        "driver_pair": gate["driver_pair"],
    }

    return {
        "path_index": plan["path_index"],
        "path_id": plan["path_id"],
        "chemical_system": plan["chemical_system"],
        "image_count": plan["image_count"],
        "anchor_universe": plan["anchor_universe"],
        "union_model_anchor_indices": plan["union_model_anchor_indices"],
        "dense_extension_applied": plan["dense_extension_applied"],
        "models_present": sorted(plan["per_model"]),
        "models_missing": plan["models_missing"],
        "anchors_evaluated": sorted(pool),
        "anchors_missing": [i for i in plan["anchor_universe"] if i not in pool],
        "per_model": per_model,
        "dense_complete": dense_complete,
        "dense_barrier_ev": dense_barrier,
        "dense_vs_vasp_signed_error_mev": (
            (dense_barrier - reference_barrier) * 1000.0 if dense_barrier is not None else None
        ),
        "reference_barrier_ev": reference_barrier,
        "t1": t1,
        "t1_gate": t1_gate,
    }


def mean_mev(values: list[float]) -> float | None:
    if not values:
        return None
    result = math.fsum(values) / len(values)
    return result if math.isfinite(result) else None


def verdict_of(mae_mev: float | None, complete: bool) -> str:
    if not complete or mae_mev is None:
        return "incomplete"
    if mae_mev <= STRONG_WIN_THRESHOLD_MEV:
        return "strong_win"
    if mae_mev <= WIN_THRESHOLD_MEV:
        return "win"
    return "loss"


def assemble_campaign(
    plans: list[dict], workdir: Path, deferred_indices: list[int]
) -> dict:
    per_path = [assemble(plan, workdir) for plan in plans]

    per_model_summary = {}
    for model in MODELS:
        guided = [p for p in per_path if model in p["per_model"]]
        # Primary (A1): same-engine basis — needs the model's anchors AND the
        # dense profile, so a path counts only when both are complete.
        se_errors = [
            p["per_model"][model]["same_engine_abs_error_mev"]
            for p in guided
            if p["per_model"][model].get("same_engine_abs_error_mev") is not None
        ]
        vasp_errors = [
            p["per_model"][model]["vasp_abs_error_mev"]
            for p in guided
            if p["per_model"][model].get("vasp_abs_error_mev") is not None
        ]
        se_mae = mean_mev(se_errors)
        complete = len(se_errors) == len(guided) and len(guided) > 0
        per_model_summary[model] = {
            "paths_guided": len(guided),
            "paths_with_same_engine_error": len(se_errors),
            "paths_with_vasp_error": len(vasp_errors),
            "same_engine_mae_mev": se_mae,
            "vasp_mae_mev": mean_mev(vasp_errors),
            "win": complete and se_mae is not None and se_mae <= WIN_THRESHOLD_MEV,
            "strong_win": (
                complete and se_mae is not None and se_mae <= STRONG_WIN_THRESHOLD_MEV
            ),
            "verdict": verdict_of(se_mae, complete),
            "basis": "same-engine dense GPAW profile (primary, amendment A1); "
                     "VASP reference secondary",
        }

    wanders = [p["t1"]["offset_wander_mev"] for p in per_path
               if p["t1"]["offset_wander_mev"] is not None]
    contaminated = [p["path_index"] for p in per_path
                    if p["t1_gate"]["verdict"] == "contaminated"]
    anchors_total = sum(len(p["anchor_universe"]) for p in per_path)
    anchors_done = sum(len(p["anchors_evaluated"]) for p in per_path)
    campaign = {
        "schema": SCHEMA_CAMPAIGN,
        "recorded_at": utc_now(),
        "preregistration": PREREGISTRATION,
        "amendment": AMENDMENT,
        "gpaw_params": gpaw_params_json(),
        "thresholds": {
            "win_mev": WIN_THRESHOLD_MEV,
            "strong_win_mev": STRONG_WIN_THRESHOLD_MEV,
            "t1_gate_mev": WIN_THRESHOLD_MEV,
            "basis": "same-engine (sparse GPAW vs dense same-engine GPAW profile)",
        },
        "deferred_path_indices": deferred_indices,
        "active_path_indices": [p["path_index"] for p in plans],
        "per_path": per_path,
        "per_model_summary": per_model_summary,
        "t1_summary": {
            "paths_with_offsets": len(wanders),
            "paths_contaminated": len(contaminated),
            "contaminated_path_indices": contaminated,
            "mean_offset_wander_mev": mean_mev(wanders),
            "max_offset_wander_mev": max(wanders) if wanders else None,
        },
        "cost": {
            "anchors_total": anchors_total,
            "anchors_evaluated": anchors_done,
            "anchors_remaining": anchors_total - anchors_done,
        },
    }
    if active_params_overridden():
        campaign["settings_note"] = settings_note()
    return campaign


def print_summary(campaign: dict, log=print) -> None:
    log("== union-anchor pilot assembly ==")
    cost = campaign["cost"]
    log(f"anchors: {cost['anchors_evaluated']}/{cost['anchors_total']} evaluated "
        f"({cost['anchors_remaining']} remaining)")
    log(f"{'model':<20} {'guided':>6} {'done':>5} {'MAE-se':>9} {'MAE-vasp':>9}  verdict")
    for model, summary in campaign["per_model_summary"].items():
        se = summary["same_engine_mae_mev"]
        va = summary["vasp_mae_mev"]
        log(f"{model:<20} {summary['paths_guided']:>6} "
            f"{summary['paths_with_same_engine_error']:>5} "
            f"{f'{se:9.1f}' if se is not None else '      n/a'} "
            f"{f'{va:9.1f}' if va is not None else '      n/a'}  {summary['verdict']}")
    log("(MAE-se = same-engine basis, primary; MAE-vasp = VASP-referenced, secondary; meV)")
    t1 = campaign["t1_summary"]
    mean_wander = t1["mean_offset_wander_mev"]
    max_wander = t1["max_offset_wander_mev"]
    log(f"T1 offset wander: mean {mean_wander:.1f} meV, max {max_wander:.1f} meV "
        f"over {t1['paths_with_offsets']} paths; "
        f"contaminated: {t1['contaminated_path_indices'] or 'none'}"
        if mean_wander is not None and max_wander is not None
        else "T1 offset wander: n/a (no anchors evaluated yet)")
    for p in campaign["per_path"]:
        missing = p["anchors_missing"]
        t1p = p["t1"]
        wander = t1p["offset_wander_mev"]
        log(f"  path-{p['path_index']:<3} {p['path_id']:<26} "
            f"imgs={p['image_count']} eval={len(p['anchors_evaluated'])}/{p['image_count']} "
            f"models={len(p['models_present'])} "
            f"wander={f'{wander:6.1f}' if wander is not None else '   n/a'}"
            f" t1_gate={p['t1_gate']['verdict']}"
            + (f" missing={missing}" if missing else ""))


# --- Dry run ----------------------------------------------------------------------------

def dry_run(plans: list[dict], workdir: Path, minutes_per_anchor: float, log=print) -> dict:
    """Report per-path anchor coverage and remaining cost without touching GPAW."""
    total_remaining = 0
    total_anchors = 0
    rows = []
    log(f"active GPAW params: {gpaw_params_json()}"
        + (f" [{settings_note()}]" if active_params_overridden() else ""))
    log(f"{'path':>5} {'imgs':>4} {'models':>6} {'union':>5} {'univ':>4} "
        f"{'done':>4} {'todo':>4}  est.h  anchors-to-compute")
    for plan in plans:
        done = []
        todo = []
        for anchor_index in plan["anchor_universe"]:
            checkpoint = read_checkpoint(
                anchor_checkpoint_path(workdir, plan["path_index"], anchor_index)
            )
            (done
             if usable_energy(checkpoint) is not None and params_match(checkpoint)
             else todo).append(anchor_index)
        total_remaining += len(todo)
        total_anchors += len(plan["anchor_universe"])
        hours = len(todo) * minutes_per_anchor / 60.0
        rows.append({
            "path_index": plan["path_index"],
            "image_count": plan["image_count"],
            "models_present": sorted(plan["per_model"]),
            "union_model_anchor_indices": plan["union_model_anchor_indices"],
            "anchor_universe": plan["anchor_universe"],
            "anchors_done": done,
            "anchors_to_compute": todo,
            "estimated_hours": round(hours, 1),
        })
        note = ""
        if not plan["per_model"]:
            note = "  [no model guidance — dense extension covers all images]"
        log(f"{plan['path_index']:>5} {plan['image_count']:>4} "
            f"{len(plan['per_model']):>6} "
            f"{len(plan['union_model_anchor_indices']):>5} "
            f"{len(plan['anchor_universe']):>4} {len(done):>4} {len(todo):>4} "
            f"{hours:5.1f}  {todo}{note}")
    total_hours = total_remaining * minutes_per_anchor / 60.0
    log(f"total: {total_anchors} anchors in universe over {len(plans)} active paths, "
        f"{total_remaining} to compute, ETA {total_hours:.1f} h "
        f"({total_hours / 24.0:.1f} days serial) at {minutes_per_anchor:.0f} min/anchor")
    return {
        "active_paths": len(plans),
        "anchors_total": total_anchors,
        "anchors_to_compute": total_remaining,
        "estimated_hours": round(total_hours, 1),
        "gpaw_params": gpaw_params_json(),
        "per_path": rows,
    }


# --- CLI ---------------------------------------------------------------------------------

def parse_paths_filter(spec: str) -> set[int]:
    if "-" in spec:
        lo, hi = (int(x) for x in spec.split("-"))
        return set(range(lo, hi + 1))
    return {int(x) for x in spec.split(",")}


def parse_kpts(spec: str) -> tuple[int, int, int]:
    """Parse a --kpts comma triple like '1,1,1' (Gamma-only sampling)."""
    try:
        parts = tuple(int(x) for x in spec.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--kpts expects three comma-separated integers, got {spec!r}"
        ) from None
    if len(parts) != 3 or any(v < 1 for v in parts):
        raise argparse.ArgumentTypeError(
            f"--kpts expects three positive comma-separated integers, got {spec!r}"
        )
    return parts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, default=Path("/tmp/z1-union-local"),
                        help="checkpoint + input-cache root")
    parser.add_argument("--local", type=Path,
                        help="offline input dir with panel.lock.json + <model>/cell_result.json")
    parser.add_argument("--paths", help="active path indices, e.g. '0-29' or '7,16'")
    parser.add_argument("--kpts", type=parse_kpts, default=FROZEN_GPAW_PARAMS["kpts"],
                        metavar="I,J,K",
                        help="k-point mesh triple (frozen default 2,2,2; '1,1,1' = Gamma-only)")
    parser.add_argument("--h", type=float, default=FROZEN_GPAW_PARAMS["h"],
                        help="fd grid spacing in Angstrom (frozen default 0.18)")
    parser.add_argument("--out", type=Path, default=None,
                        help="campaign JSON path (default <workdir>/campaign.json)")
    parser.add_argument("--receipts-dir", type=Path, default=DEFAULT_RECEIPTS_DIR,
                        help="directory of run_pilot.py path-<i>.json receipts to import")
    parser.add_argument("--no-import", action="store_true", help="skip receipt import")
    parser.add_argument("--min-free-gb", type=float, default=DEFAULT_MIN_FREE_GB,
                        help="skip an anchor when MemAvailable is under this (GiB)")
    parser.add_argument("--minutes-per-anchor", type=float, default=DEFAULT_MINUTES_PER_ANCHOR,
                        help="dry-run cost rate (measured path-16 pace: 90-120)")
    parser.add_argument("--deferred", type=Path, default=DEFAULT_DEFERRED_JSON,
                        help="deferred-paths record (indices stay out of the active set)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report anchor coverage and cost; do not touch GPAW")
    parser.add_argument("--assemble-only", action="store_true",
                        help="assemble campaign.json from the existing anchor pool only")
    args = parser.parse_args(argv)

    # Settings overrides apply to everything below: planning, receipt import,
    # compute, and assembly all see the active params, and checkpoints
    # recorded under different params are never trusted.
    set_active_params(kpts=args.kpts, h=args.h)
    banner = f"union-pilot: active GPAW params {gpaw_params_json()}"
    if active_params_overridden():
        banner += f" [{settings_note()}]"
    print(banner)

    workdir = args.workdir
    workdir.mkdir(parents=True, exist_ok=True)
    out_path = args.out or (workdir / "campaign.json")

    panel, artifacts = load_inputs(workdir, args.local)
    deferred_indices = load_deferred_indices(args.deferred)
    plans = build_plans(panel, artifacts, deferred_indices)
    if args.paths:
        wanted = parse_paths_filter(args.paths)
        plans = [p for p in plans if p["path_index"] in wanted]
    if not plans:
        raise SystemExit("no active paths selected")

    if not args.no_import:
        results = import_receipts(args.receipts_dir, plans, workdir)
        for path_index, stats in results.items():
            if stats["imported"] or stats["rejected"]:
                print(f"import path-{path_index}: imported={stats['imported']} "
                      f"existing={stats['skipped_existing']} rejected={stats['rejected']}")

    if args.dry_run:
        report = dry_run(plans, workdir, args.minutes_per_anchor)
        print(json.dumps({k: v for k, v in report.items() if k != "per_path"}, indent=1))
        return 0

    if not args.assemble_only:
        totals = compute_anchors(
            plans,
            panel,
            workdir,
            min_free_bytes=int(args.min_free_gb * 1024**3),
        )
        print(f"compute: {json.dumps(totals)}")

    campaign = assemble_campaign(plans, workdir, deferred_indices)
    payload = json.dumps(campaign, indent=1, sort_keys=True) + "\n"
    campaign["campaign_sha256"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(campaign, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print_summary(campaign)
    print(f"campaign written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
