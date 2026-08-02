#!/usr/bin/env python3
"""Deterministic converter: Z1 union campaign -> lupine.visualization-bundle.v1.

Phase 0 of `docs/plans/2026-07-24-visualization-pipeline-plan.md` ("science
contract and golden bundles"). Builds one immutable visualization bundle for a
single Z1 path from the verified sources only:

- campaign record  `data/candidates/z1-union-campaign.json`        (no coordinates)
- barrier panel    `data/candidates/z1_nebdft2k_barriers.lock.json` (coordinates)
- anchor receipts  `<anchors-root>/path-<i>/anchor-<j>.json`        (GPAW + VASP energies)
- model artifacts  `<models-root>/<model>/cell_result.json`         (uMLIP provenance/profiles)
- path-0 only      `<diagnostics-root>/img3-adopted.{json,txt}`, `img3-h018.{json,txt}`

Contract highlights (the plan is law):

- Canonical JSON: sorted keys, 2-space indent, single trailing newline, no
  NaN/Infinity anywhere. Missingness is always ``{"status": ..., "value": null}``.
- ``bundle_id`` = SHA-256 over the canonical manifest with the ``bundle_id``
  field omitted during hashing. Zero-based image indices are mandatory.
- NEB images are a reaction-path sequence, never time. Nothing here may label
  an image index as time, dynamics, or temperature.
- Fail closed: hash/byte/schema/finite-number failure, frame/profile
  cardinality mismatch, changed atom identity/species/order across frames,
  absent cell or undeclared units, non-monotone declared path coordinate,
  derived scalars that do not recompute, evaluated anchors outside the allowed
  image set, missing source pointers, or a diagnostic that does not bind.

Derived scalars are recomputed from the raw sources with the frozen protocol
(`select_extrema` / `build_anchor_set` mirrored from
`gcp/mlip-cell-runner/z1_sparse_dft.py`; T1 gate reused from
`tools/analysis/t1_wander.py`) and cross-checked EXACTLY against the campaign
record of record. Any disagreement refuses the build.

Usage:
  python tools/analysis/build_visualization_bundle.py --path-index 16 \
      [--outdir data/visualization/bundles] [--dry-run]
  python tools/analysis/build_visualization_bundle.py --verify \
      data/visualization/bundles/sha256/<first2>/<digest>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import jsonschema

# tools/analysis is not a package; this script's own directory holds t1_wander.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from t1_wander import (  # noqa: E402
    VERDICT_CONTAMINATED,
    analyze_offsets,
)

SCHEMA_ID = "lupine.visualization-bundle.v1"
TOOL_VERSION = "1.1.0"  # 1.1.0: verify dereferences series source pointers, derives verdicts from numeric errors, and revalidates diagnostic receipts; diagnostic source assets are digest-bound
TOOL_PATH = "tools/analysis/build_visualization_bundle.py"

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas" / "visualization" / "lupine.visualization-bundle.v1.schema.json"
DEFAULT_PANEL = REPO_ROOT / "data" / "candidates" / "z1_nebdft2k_barriers.lock.json"
DEFAULT_CAMPAIGN = REPO_ROOT / "data" / "candidates" / "z1-union-campaign.json"
DEFAULT_ANCHORS_ROOT = Path("/tmp/z1-union-local/anchors")
DEFAULT_MODELS_ROOT = Path("/tmp/z1-union-local/inputs")
DEFAULT_DIAGNOSTICS_ROOT = Path("/tmp/z1-diagnose")
DEFAULT_OUTDIR = REPO_ROOT / "data" / "visualization" / "bundles"

CAMPAIGN_SCHEMA = "lupine.z1.union_pilot.campaign.v1"
PANEL_SCHEMA = "lupine.z1.neb_barrier_panel.v1"
ANCHOR_SCHEMA = "lupine.z1.union_pilot.anchor.v1"
MODEL_CELL_SCHEMA = "lupine.mlip.cell_artifact.v1"

# Model directory names, fixed order (same as tools/analysis/union_anchor_economics.py).
MODELS = ["chgnet", "mace-mp-small", "mace-mp-medium", "mace-mpa-0-medium"]
MODEL_PACKAGE_KEY = {
    "chgnet": "chgnet",
    "mace-mp-small": "mace-torch",
    "mace-mp-medium": "mace-torch",
    "mace-mpa-0-medium": "mace-torch",
}
MODEL_GCS_RESULT = "gs://shed-489901-atlas-outputs/z1/campaign-float64/{model}/cell_result.json"

# Frozen protocol constants (gcp/mlip-cell-runner/z1_sparse_dft.py and
# gcp/sparse-dft-pilot/union_pilot.py). Mirrored, not imported, so this tool
# stays stdlib-only; behavior must remain byte-equivalent.
SHORT_PATH_IMAGE_THRESHOLD = 6
DENSE_EXTENSION_IMAGE_THRESHOLD = 7
USABLE_RECEIPT_STATUSES = {"completed", "imported"}

# Path-0 electronic diagnostics (metallic-saddle SCF evidence). Bound ONLY for
# path 0; every other path records diagnostics as absent.
DIAGNOSTIC_PATH_INDEX = 0
DIAGNOSTIC_IMAGE_INDEX = 3
DIAGNOSTIC_FILES = (
    ("adopted_h0.20", "img3-adopted.json", "img3-adopted.txt"),
    ("sensitivity_h0.18", "img3-h018.json", "img3-h018.txt"),
)

UNITS_ANGSTROM = "angstrom"
REACTION_COORDINATE_DEFINITION = (
    "Zero-based NEB image index over the reaction-path sequence. Images are "
    "climbing-image NEB structures along a reaction coordinate; the index is "
    "NOT time, NOT dynamics, and implies no equal elapsed time."
)

VERDICT_RANK = {"strong_win": 0, "win": 1, "loss": 2, "incomplete": 3}


class BundleError(RuntimeError):
    """Any fail-closed refusal (build or verify)."""


# --- Canonical JSON + hashing ---------------------------------------------------

def canonical_json(obj: dict | list) -> bytes:
    """Canonical manifest bytes: sorted keys, 2-space indent, trailing newline.

    `allow_nan=False` makes NaN/Infinity a hard error — missingness must use
    status+null, never an undocumented non-finite float.
    """
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return (text + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def digest_id(hex_digest: str) -> str:
    return f"sha256:{hex_digest}"


def load_json_strict(path: Path) -> dict | list:
    """Parse JSON, refusing NaN/Infinity tokens (fail closed)."""
    def _reject(value: str):
        raise BundleError(f"{path}: non-finite JSON number {value!r} is not representable")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject,
        )
    except json.JSONDecodeError as exc:
        raise BundleError(f"{path}: invalid JSON: {exc}") from exc


# --- Frozen protocol logic, mirrored from z1_sparse_dft.py -----------------------
# Keep these byte-equivalent in behavior to the frozen source (same mirroring
# pattern as tools/analysis/union_anchor_economics.py).

def select_extrema(energies: list[float]) -> tuple[int, int]:
    """(min_index, max_index) with deterministic first-occurrence tie-break."""
    if not energies:
        raise BundleError("cannot select extrema of an empty energy profile")
    min_index = min(range(len(energies)), key=lambda i: (energies[i], i))
    max_index = max(range(len(energies)), key=lambda i: (energies[i], -i))
    return min_index, max_index


def build_anchor_set(image_count: int, model_min_index: int, model_max_index: int) -> dict:
    """Frozen anchor set: endpoints + model-min + (model-max ± window)."""
    if image_count < 3:
        raise BundleError(f"a path needs at least 3 images; got {image_count}")
    short_path_fallback = image_count <= SHORT_PATH_IMAGE_THRESHOLD
    window = 2 if short_path_fallback else 1
    anchors = {0, image_count - 1, model_min_index}
    anchors.update(
        index
        for index in range(model_max_index - window, model_max_index + window + 1)
        if 0 <= index < image_count
    )
    return {
        "anchor_indices": sorted(anchors),
        "window": window,
        "short_path_fallback": short_path_fallback,
    }


def missing(status: str, note: str | None = None) -> dict:
    """Missingness encoding: a status and a null value, never NaN/Infinity."""
    entry = {"status": status, "value": None}
    if note is not None:
        entry["note"] = note
    return entry


# --- Source loading + sidecar verification ----------------------------------------

def verify_sidecar(path: Path) -> None:
    """Fail closed when a `<file>.sha256` sidecar disagrees with the file."""
    sidecar = path.with_name(path.name + ".sha256")
    if not sidecar.is_file():
        return
    expected = sidecar.read_text(encoding="utf-8").split()[0].strip()
    actual = sha256_file(path)
    if expected != actual:
        raise BundleError(
            f"source hash changed: {path} hashes to {actual}, sidecar says {expected}"
        )


def git_commit_for(path: Path) -> str | None:
    """Last commit touching a repo-tracked file; None outside git."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def git_head() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def artifact_uri(path: Path) -> str:
    """Deterministic, checkout-independent locator: repo-relative when possible.

    External artifacts fall back to their last two components so identically
    named files from different parents (e.g. per-model cell_result.json)
    remain distinguishable.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        parts = path.parts
        return "/".join(parts[-2:]) if len(parts) >= 2 else path.name


def source_artifact(role: str, uri: str, path: Path, schema: str | None) -> dict:
    payload = path.read_bytes()
    return {
        "role": role,
        "uri": uri,
        "bytes": len(payload),
        "sha256": digest_id(sha256_bytes(payload)),
        "schema": schema,
        "git_commit": git_commit_for(path) if path.is_relative_to(REPO_ROOT) else None,
    }


def load_campaign(path: Path) -> dict:
    verify_sidecar(path)
    campaign = load_json_strict(path)
    if campaign.get("schema") != CAMPAIGN_SCHEMA:
        raise BundleError(
            f"{path}: expected schema {CAMPAIGN_SCHEMA}, got {campaign.get('schema')!r}"
        )
    return campaign


def load_panel(path: Path) -> dict:
    verify_sidecar(path)
    panel = load_json_strict(path)
    if panel.get("schema") != PANEL_SCHEMA:
        raise BundleError(
            f"{path}: expected schema {PANEL_SCHEMA}, got {panel.get('schema')!r}"
        )
    return panel


def load_receipts(anchors_root: Path, path_index: int, path_id: str, image_count: int) -> dict[int, dict]:
    """Read anchor receipts for one path; fail closed on identity violations."""
    receipt_dir = anchors_root / f"path-{path_index}"
    if not receipt_dir.is_dir():
        raise BundleError(f"{receipt_dir}: no anchor receipt directory for path {path_index}")
    receipts: dict[int, dict] = {}
    for file in sorted(receipt_dir.glob("anchor-*.json")):
        match = re.fullmatch(r"anchor-(\d+)\.json", file.name)
        if match is None:
            raise BundleError(f"{file}: unreconized anchor receipt name")
        index = int(match.group(1))
        receipt = load_json_strict(file)
        if receipt.get("schema") != ANCHOR_SCHEMA:
            raise BundleError(f"{file}: expected schema {ANCHOR_SCHEMA}")
        if receipt.get("path_index") != path_index or receipt.get("path_id") != path_id:
            raise BundleError(
                f"{file}: receipt identity {receipt.get('path_index')}/"
                f"{receipt.get('path_id')} does not match path {path_index}/{path_id}"
            )
        if receipt.get("anchor_index") != index:
            raise BundleError(f"{file}: anchor_index field disagrees with filename")
        if not 0 <= index < image_count:
            raise BundleError(
                f"{file}: evaluated anchor {index} outside the allowed image set "
                f"[0, {image_count})"
            )
        if index in receipts:
            raise BundleError(f"{file}: duplicate receipt for image {index}")
        receipt["__file__"] = file
        receipts[index] = receipt
    return receipts


# --- Coordinates -------------------------------------------------------------------

def _finite_matrix(matrix, shape: tuple[int, ...], what: str) -> None:
    if not isinstance(matrix, list) or len(matrix) != shape[0]:
        raise BundleError(f"{what}: expected {shape[0]} rows")
    for row in matrix:
        if not isinstance(row, list) or len(row) != shape[1]:
            raise BundleError(f"{what}: expected rows of length {shape[1]}")
        for value in row:
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise BundleError(f"{what}: non-finite or non-numeric entry {value!r}")


def build_coordinates(panel_path: dict) -> dict:
    """Coordinates block from the panel's input_images (wrapped source values)."""
    images = panel_path.get("input_images")
    if not isinstance(images, list) or not images:
        raise BundleError("panel path has no input_images")
    species_reference: list[str] | None = None
    frames = []
    for i, image in enumerate(images):
        symbols = image.get("symbols")
        positions = image.get("positions_angstrom")
        cell = image.get("cell_angstrom")
        pbc = image.get("pbc")
        if positions is None or cell is None:
            raise BundleError(
                f"image {i}: coordinate units undeclared (positions_angstrom/"
                "cell_angstrom missing) — refusing to guess units"
            )
        # Any *other* positions/cell key would mean undeclared units.
        for key in image:
            if key.startswith("positions_") and key != "positions_angstrom":
                raise BundleError(f"image {i}: undeclared coordinate units in key {key!r}")
            if key.startswith("cell_") and key != "cell_angstrom":
                raise BundleError(f"image {i}: undeclared cell units in key {key!r}")
        if not isinstance(symbols, list) or not symbols or not all(
            isinstance(s, str) and s for s in symbols
        ):
            raise BundleError(f"image {i}: absent or invalid species list")
        if species_reference is None:
            species_reference = list(symbols)
        elif list(symbols) != species_reference:
            raise BundleError(
                f"image {i}: atom identity/species/order changed across frames "
                "(frame 0 is the identity reference)"
            )
        _finite_matrix(positions, (len(symbols), 3), f"image {i} positions_angstrom")
        _finite_matrix(cell, (3, 3), f"image {i} cell_angstrom")
        if not (isinstance(pbc, list) and len(pbc) == 3 and all(isinstance(b, bool) for b in pbc)):
            raise BundleError(f"image {i}: absent or invalid PBC state")
        frames.append(
            {
                "image_index": i,
                "lattice_angstrom": cell,
                "pbc": pbc,
                "positions_angstrom": positions,
            }
        )
    reaction_values = list(range(len(frames)))
    if reaction_values != sorted(reaction_values) or reaction_values[0] != 0:
        raise BundleError("declared path coordinate is not zero-based monotone")
    return {
        "units": UNITS_ANGSTROM,
        "atom_count": len(species_reference),
        "atom_ids": [f"a{i:03d}" for i in range(len(species_reference))],
        "species": species_reference,
        "atom_order_convention": (
            "Source panel order. Atom id a<NNN> binds (index, species) and is "
            "stable across every frame of the reaction-path sequence."
        ),
        "wrapped_convention": (
            "Positions are the as-published wrapped source coordinates; no "
            "unwrapping or minimum-image transform has been applied."
        ),
        "unwrapped": missing(
            "not_derived",
            "unwrapped display coordinates are a presentation-layer derivative "
            "and are not part of this bundle",
        ),
        "migrating_atom_ids": missing(
            "not_recorded", "no migrating-atom annotation exists in the bound sources"
        ),
        "reaction_coordinate": {
            "definition": REACTION_COORDINATE_DEFINITION,
            "unit": "image_index",
            "values": reaction_values,
        },
        "frames": frames,
    }


# --- Series ------------------------------------------------------------------------

def gpaw_pool(
    receipts: dict[int, dict], reference_energies: list[float], campaign_gpaw_params: dict
) -> tuple[dict[int, dict], dict[int, str]]:
    """Usable GPAW pool + per-image status, mirroring union_pilot.pool_for_plan.

    A receipt is usable only when its status is trustworthy, its energy is a
    finite number, and its recorded gpaw_params equal the campaign's adopted
    settings; otherwise the image is missing with an explicit status.
    """
    pool: dict[int, dict] = {}
    status: dict[int, str] = {}
    for index, receipt in receipts.items():
        energy = receipt.get("gpaw_energy_ev")
        reference = receipt.get("reference_energy_ev")
        if reference != reference_energies[index]:
            raise BundleError(
                f"anchor {index}: receipt reference_energy_ev {reference!r} disagrees "
                f"with the panel reference energy {reference_energies[index]!r}"
            )
        if receipt.get("status") not in USABLE_RECEIPT_STATUSES:
            status[index] = "failed"
            continue
        if not isinstance(energy, (int, float)) or not math.isfinite(energy):
            status[index] = "failed"
            continue
        if receipt.get("gpaw_params") != campaign_gpaw_params:
            status[index] = "rejected_params_mismatch"
            continue
        pool[index] = receipt
        status[index] = "evaluated"
    return pool, status


def build_series(
    image_count: int,
    pool: dict[int, dict],
    pool_status: dict[int, str],
    reference_energies: list[float],
    model_predictions: dict[str, dict | None],
    anchor_asset_digests: dict[int, str],
    panel_excerpt_digest: str,
    model_excerpt_digests: dict[str, str],
) -> list[dict]:
    """Energy series with per-value status and source pointers."""
    indices = list(range(image_count))

    gpaw_values = [pool[i]["gpaw_energy_ev"] if i in pool else None for i in indices]
    gpaw_status = [pool_status.get(i, "missing") for i in indices]
    gpaw_sources = [
        {"asset_sha256": anchor_asset_digests[i], "json_pointer": "/gpaw_energy_ev"}
        if i in pool
        else None
        for i in indices
    ]
    series = [
        {
            "series_id": "gpaw_total_energy",
            "quantity": "total_energy",
            "engine_or_model": "gpaw",
            "kind": "dft_single_point",
            "absolute_or_relative": "absolute",
            "unit": "eV",
            "zero_convention": (
                "Absolute GPAW total energy as recorded in the anchor receipts; "
                "no re-zeroing applied. Display layers may re-zero per engine "
                "path minimum but must retain these absolute values."
            ),
            "image_indices": indices,
            "values": gpaw_values,
            "value_status": gpaw_status,
            "value_sources": gpaw_sources,
            "note": "GPAW single-point evaluations on the reaction-path sequence.",
        },
        {
            "series_id": "vasp_reference_total_energy",
            "quantity": "total_energy",
            "engine_or_model": "vasp",
            "kind": "reference",
            "absolute_or_relative": "absolute",
            "unit": "eV",
            "zero_convention": (
                "Absolute VASP reference total energy from the locked nebDFT2k "
                "panel; no re-zeroing applied."
            ),
            "image_indices": indices,
            "values": list(reference_energies),
            "value_status": ["evaluated"] * image_count,
            "value_sources": [
                {
                    "asset_sha256": panel_excerpt_digest,
                    "json_pointer": f"/reference/energies_ev/{i}",
                }
                for i in indices
            ],
            "note": "Reference energies for the same reaction-path sequence.",
        },
    ]
    for model in MODELS:
        prediction = model_predictions.get(model)
        if prediction is None:
            continue
        energies = prediction["predicted_image_energies_ev"]
        series.append(
            {
                "series_id": f"model_total_energy/{model}",
                "quantity": "total_energy",
                "engine_or_model": model,
                "kind": "model",
                "absolute_or_relative": "absolute",
                "unit": "eV",
                "zero_convention": (
                    "Absolute model-predicted image energies as recorded in the "
                    "model cell artifact; no re-zeroing applied."
                ),
                "image_indices": indices,
                "values": list(energies),
                "value_status": ["evaluated"] * image_count,
                "value_sources": [
                    {
                        "asset_sha256": model_excerpt_digests[model],
                        "json_pointer": f"/prediction/predicted_image_energies_ev/{i}",
                    }
                    for i in indices
                ],
                "note": "uMLIP CI-NEB image energies guiding anchor nomination.",
            }
        )
    return series


# --- Selection ---------------------------------------------------------------------

def build_selection(
    image_count: int,
    model_predictions: dict[str, dict | None],
    pool: dict[int, dict],
    dense_energies: list[float] | None,
) -> dict:
    """Anchor-selection record: frozen rule, sets, guidance misses/deficits."""
    per_model: dict[str, dict] = {}
    union_set: set[int] = set()
    for model in MODELS:
        prediction = model_predictions.get(model)
        if prediction is None:
            continue
        profile = prediction["predicted_image_energies_ev"]
        model_min, model_max = select_extrema(profile)
        anchor = build_anchor_set(image_count, model_min, model_max)
        nominated = anchor["anchor_indices"]
        union_set.update(nominated)
        evaluated = sorted(i for i in nominated if i in pool)
        complete = len(evaluated) == len(nominated)
        entry = {
            "nominated": nominated,
            "evaluated": evaluated,
            "complete": complete,
            "model_min_index": model_min,
            "model_max_index": model_max,
            "window": anchor["window"],
            "short_path_fallback": anchor["short_path_fallback"],
        }
        if complete:
            sparse = max(pool[i]["gpaw_energy_ev"] for i in nominated) - min(
                pool[i]["gpaw_energy_ev"] for i in nominated
            )
            entry["sparse_barrier_ev"] = sparse
        per_model[model] = entry

    dense_extension_applied = image_count <= DENSE_EXTENSION_IMAGE_THRESHOLD
    universe = set(union_set)
    if dense_extension_applied:
        universe.update(range(image_count))

    dense_extrema = None
    guidance_misses: dict[str, list[int]] = {}
    guidance_deficits: dict[str, dict] = {}
    if dense_energies is not None:
        dmin, dmax = select_extrema(dense_energies)
        dense_extrema = {"argmin": dmin, "argmax": dmax}
        dense_barrier = dense_energies[dmax] - dense_energies[dmin]
        for model, entry in per_model.items():
            nominated = set(entry["nominated"])
            guidance_misses[model] = sorted({dmin, dmax} - nominated)
            if "sparse_barrier_ev" in entry:
                signed = (entry["sparse_barrier_ev"] - dense_barrier) * 1000.0
                guidance_deficits[model] = {
                    "sparse_barrier_ev": entry["sparse_barrier_ev"],
                    "dense_barrier_ev": dense_barrier,
                    "same_engine_signed_error_mev": signed,
                    "same_engine_abs_error_mev": abs(signed),
                }

    return {
        "rule_id": "lupine.z1.union_anchor_rule.v1",
        "rule_version": "z1_sparse_dft.py select_extrema/build_anchor_set (frozen, preregistered)",
        "rule_source": {
            "path": "gcp/mlip-cell-runner/z1_sparse_dft.py",
            "git_commit": git_commit_for(Path("gcp/mlip-cell-runner/z1_sparse_dft.py")),
        },
        "extrema_tie_policy": (
            "First occurrence (lowest image index) for both argmin and argmax."
        ),
        "window_rule": (
            f"anchors = {{0, n-1, model-min}} ∪ {{model-max-window .. model-max+window}}, "
            f"clamped to [0, n) and de-duplicated; window = 2 when image_count <= "
            f"{SHORT_PATH_IMAGE_THRESHOLD} else 1"
        ),
        "subset_theorem": (
            "Exact barrier recovery follows when the evaluated set contains both "
            "dense-profile extrema (barrier_eq_barrier_of_extrema_mem)."
        ),
        "per_model": per_model,
        "nominated_union": sorted(union_set),
        "evaluated": sorted(pool),
        "anchor_universe": sorted(universe),
        "dense_extension": {
            "applied": dense_extension_applied,
            "image_threshold": DENSE_EXTENSION_IMAGE_THRESHOLD,
            "supplied_indices": sorted(universe - union_set),
            "note": (
                "Dense extension evaluates every image on short paths; supplied "
                "indices are evaluated images no guiding model nominated."
            ),
        },
        "dense_profile_extrema": dense_extrema
        if dense_extrema is not None
        else missing("dense_profile_incomplete", "not every image has an evaluated GPAW value"),
        "guidance_misses": guidance_misses,
        "guidance_deficits_mev": guidance_deficits,
    }


# --- Quality gates -------------------------------------------------------------------

def path_verdict(abs_error_mev: float | None, complete: bool) -> str:
    if not complete or abs_error_mev is None:
        return "incomplete"
    if abs_error_mev <= 15.0:
        return "strong_win"
    if abs_error_mev <= 40.0:
        return "win"
    return "loss"


def build_quality_gates(
    campaign_thresholds: dict,
    image_count: int,
    pool: dict[int, dict],
    reference_energies: list[float],
    reference_barrier_ev: float,
    selection: dict,
) -> dict:
    dense_complete = len(pool) == image_count
    dense_energies = None
    dense_barrier = None
    if dense_complete:
        dense_energies = [pool[i]["gpaw_energy_ev"] for i in range(image_count)]
        dense_barrier = max(dense_energies) - min(dense_energies)

    per_model_same: dict[str, dict] = {}
    per_model_cross: dict[str, dict] = {}
    for model, entry in selection["per_model"].items():
        if "sparse_barrier_ev" not in entry:
            per_model_same[model] = {"complete": False, "verdict": "incomplete"}
            continue
        sparse = entry["sparse_barrier_ev"]
        vasp_signed = (sparse - reference_barrier_ev) * 1000.0
        per_model_cross[model] = {
            "sparse_barrier_ev": sparse,
            "vasp_signed_error_mev": vasp_signed,
            "vasp_abs_error_mev": abs(vasp_signed),
        }
        if dense_barrier is not None:
            se_signed = (sparse - dense_barrier) * 1000.0
            per_model_same[model] = {
                "complete": True,
                "sparse_barrier_ev": sparse,
                "dense_barrier_ev": dense_barrier,
                "same_engine_signed_error_mev": se_signed,
                "same_engine_abs_error_mev": abs(se_signed),
                "verdict": path_verdict(abs(se_signed), True),
            }
        else:
            per_model_same[model] = {"complete": True, "verdict": "incomplete"}

    gate = analyze_offsets(
        [
            (i, pool[i]["gpaw_energy_ev"], reference_energies[i])
            for i in sorted(pool)
        ],
        gate_mev=float(campaign_thresholds["t1_gate_mev"]),
    )
    t1_verdict = gate["verdict"]

    if not selection["per_model"]:
        same_engine_verdict = "no_guidance"
    else:
        same_engine_verdict = max(
            (m["verdict"] for m in per_model_same.values()),
            key=lambda v: VERDICT_RANK[v],
        )
    cross_engine_contaminated = t1_verdict == VERDICT_CONTAMINATED
    label = f"{same_engine_verdict}_t1_{t1_verdict}"

    return {
        "thresholds_mev": {
            "win": float(campaign_thresholds["win_mev"]),
            "strong_win": float(campaign_thresholds["strong_win_mev"]),
            "t1_gate": float(campaign_thresholds["t1_gate_mev"]),
        },
        "denominator_policy": (
            "Errors are computed only over evaluated values; missing values are "
            "never imputed and never counted as observations."
        ),
        "same_engine": {
            "basis": campaign_thresholds["basis"],
            "primary": True,
            "dense_complete": dense_complete,
            "dense_barrier_ev": dense_barrier,
            "per_model": per_model_same,
        },
        "cross_engine": {
            "primary": False,
            "reference_engine": "vasp",
            "reference_barrier_ev": reference_barrier_ev,
            "dense_vs_reference_signed_error_mev": (
                (dense_barrier - reference_barrier_ev) * 1000.0
                if dense_barrier is not None
                else None
            ),
            "dense_vs_reference_abs_error_mev": (
                abs(dense_barrier - reference_barrier_ev) * 1000.0
                if dense_barrier is not None
                else None
            ),
            "per_model": per_model_cross,
            "contamination_note": (
                "Cross-engine evidence is secondary and contaminated whenever "
                "the T1 wander gate fails; the same-engine basis is primary."
            ),
        },
        "t1": {
            "offset_definition": (
                "E_GPAW(i) - E_VASP(i) per evaluated image of the reaction-path "
                "sequence, in meV."
            ),
            "offset_series_mev": [
                {"image_index": row["index"], "offset_mev": row["offset_mev"]}
                for row in gate["per_image"]
            ],
            "offset_mean_mev": gate["offset_mean_mev"],
            "offset_min_mev": gate["offset_min_mev"],
            "offset_max_mev": gate["offset_max_mev"],
            "wander_mev": gate["offset_wander_mev"],
            "driver_pair": gate["driver_pair"],
            "gate_mev": gate["gate_mev"],
            "verdict": t1_verdict,
        },
        "verdict": {
            "same_engine": same_engine_verdict,
            "t1": t1_verdict,
            "cross_engine_contaminated": cross_engine_contaminated,
            "label": label,
            "interpretation": (
                "The label combines the primary same-engine basis with the T1 "
                "convention-wander gate. A contaminated T1 verdict means the "
                "cross-engine numbers measure engine-convention luck; e.g. "
                "'strong_win_t1_contaminated' is NOT a plain cross-engine win."
            ),
        },
    }


# --- Campaign cross-check -------------------------------------------------------------

def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError(f"campaign cross-check failed: {message}")


def crosscheck_campaign(
    record: dict,
    path_index: int,
    image_count: int,
    pool: dict[int, dict],
    model_predictions: dict[str, dict | None],
    models_missing: dict[str, str],
    selection: dict,
    gates: dict,
    reference_barrier_ev: float,
) -> None:
    """Every derived scalar must equal the campaign record of record, exactly."""
    _expect(record.get("path_index") == path_index, "path_index mismatch")
    _expect(record.get("image_count") == image_count, "image_count mismatch")
    _expect(record.get("anchors_evaluated") == sorted(pool), "anchors_evaluated mismatch")
    _expect(
        record.get("anchor_universe") == selection["anchor_universe"],
        "anchor_universe mismatch",
    )
    _expect(
        record.get("union_model_anchor_indices") == selection["nominated_union"],
        "union_model_anchor_indices mismatch",
    )
    _expect(
        record.get("anchors_missing")
        == [i for i in selection["anchor_universe"] if i not in pool],
        "anchors_missing mismatch",
    )
    _expect(
        record.get("models_present") == sorted(selection["per_model"]),
        "models_present mismatch",
    )
    _expect(record.get("models_missing") == models_missing, "models_missing mismatch")
    _expect(
        record.get("dense_extension_applied") == selection["dense_extension"]["applied"],
        "dense_extension_applied mismatch",
    )
    _expect(
        record.get("dense_complete") == gates["same_engine"]["dense_complete"],
        "dense_complete mismatch",
    )
    _expect(
        record.get("dense_barrier_ev") == gates["same_engine"]["dense_barrier_ev"],
        "dense_barrier_ev mismatch",
    )
    _expect(
        record.get("dense_vs_vasp_signed_error_mev")
        == gates["cross_engine"]["dense_vs_reference_signed_error_mev"],
        "dense_vs_vasp_signed_error_mev mismatch",
    )
    _expect(
        record.get("reference_barrier_ev") == reference_barrier_ev,
        "reference_barrier_ev mismatch",
    )
    for model, expected in record.get("per_model", {}).items():
        got = selection["per_model"][model]
        _expect(got["nominated"] == expected["anchor_indices"], f"{model}: anchor_indices")
        _expect(got["evaluated"] == expected["anchors_evaluated"], f"{model}: anchors_evaluated")
        _expect(got["complete"] == expected["complete"], f"{model}: complete")
        _expect(got["model_min_index"] == expected["model_min_index"], f"{model}: model_min_index")
        _expect(got["model_max_index"] == expected["model_max_index"], f"{model}: model_max_index")
        _expect(got["window"] == expected["window"], f"{model}: window")
        _expect(
            got["short_path_fallback"] == expected["short_path_fallback"],
            f"{model}: short_path_fallback",
        )
        same = gates["same_engine"]["per_model"].get(model, {})
        cross = gates["cross_engine"]["per_model"].get(model, {})
        _expect(
            same.get("sparse_barrier_ev") == expected.get("sparse_barrier_ev"),
            f"{model}: sparse_barrier_ev",
        )
        _expect(
            same.get("same_engine_signed_error_mev")
            == expected.get("same_engine_signed_error_mev"),
            f"{model}: same_engine_signed_error_mev",
        )
        _expect(
            same.get("same_engine_abs_error_mev") == expected.get("same_engine_abs_error_mev"),
            f"{model}: same_engine_abs_error_mev",
        )
        _expect(
            cross.get("vasp_signed_error_mev") == expected.get("vasp_signed_error_mev"),
            f"{model}: vasp_signed_error_mev",
        )
        _expect(
            cross.get("vasp_abs_error_mev") == expected.get("vasp_abs_error_mev"),
            f"{model}: vasp_abs_error_mev",
        )
    t1 = record.get("t1", {})
    _expect(t1.get("evaluated_image_count") == len(pool), "t1 evaluated_image_count")
    _expect(t1.get("offset_mean_mev") == gates["t1"]["offset_mean_mev"], "t1 offset_mean_mev")
    _expect(
        t1.get("offset_wander_mev") == gates["t1"]["wander_mev"], "t1 offset_wander_mev"
    )
    t1_gate = record.get("t1_gate", {})
    _expect(t1_gate.get("wander_mev") == gates["t1"]["wander_mev"], "t1_gate wander_mev")
    _expect(t1_gate.get("verdict") == gates["t1"]["verdict"], "t1_gate verdict")
    _expect(t1_gate.get("driver_pair") == gates["t1"]["driver_pair"], "t1_gate driver_pair")


# --- Path-0 electronic diagnostics ------------------------------------------------------

def _parse_float(pattern: str, text: str, what: str) -> float:
    match = re.search(pattern, text)
    if match is None:
        raise BundleError(f"diagnostic log: could not parse {what}")
    return float(match.group(1))


def _parse_int(pattern: str, text: str, what: str) -> int:
    match = re.search(pattern, text)
    if match is None:
        raise BundleError(f"diagnostic log: could not parse {what}")
    return int(match.group(1))


def parse_diagnostic_log(text: str) -> dict:
    """Extract SCF/electronic facts from one GPAW log. Parse failure is fatal."""
    converged_match = re.search(r"Converged in (\d+) steps", text)
    if converged_match is None:
        raise BundleError("diagnostic log: SCF convergence line missing")
    return {
        "gpaw_version": re.search(r"\|__\|\|  \| \|\|/\\\| - ([\d.]+)", text).group(1)
        if re.search(r"\|__\|\|  \| \|\|/\\\| - ([\d.]+)", text)
        else None,
        "scf": {
            "converged": True,
            "steps": int(converged_match.group(1)),
            "max_iterations": _parse_int(r"maximum number of iterations: (\d+)", text, "max iterations"),
            "density_criterion_electrons": _parse_float(
                r"absolute \[dens\]ity change: (\S+)", text, "density convergence criterion"
            ),
            "eigenstate_criterion_ev2": _parse_float(
                r"absolute \[eigenst\]ate change: (\S+)", text, "eigenstate convergence criterion"
            ),
        },
        "gap_ev": _parse_float(r"Gap: ([-\d.]+) eV", text, "band gap"),
        "fermi_level_ev": _parse_float(r"Fermi level: ([-\d.]+)", text, "Fermi level"),
        "spin": {
            "components": _parse_int(r"Spin-components: (\d+)", text, "spin components"),
            "degeneracy": _parse_int(r"Spin-degeneracy: (\d+)", text, "spin degeneracy"),
            "policy": "collinear, spin-components 1 (spin-unpolarized)",
        },
        "occupations": {
            "type": "Fermi-Dirac",
            "width_ev": _parse_float(r"Fermi-Dirac:\s*\n\s*width: ([-\d.]+)", text, "smearing width"),
        },
        "charge_e": _parse_float(r"Charge: ([-\d.]+)\s*# \|e\|", text, "total charge"),
    }


def build_diagnostics(
    path_index: int,
    diagnostics_root: Path | None,
    pool: dict[int, dict],
) -> tuple[dict, list[tuple[str, Path, str]]]:
    """Path-0 metallic-saddle SCF evidence; absent (status+null) otherwise.

    Returns (diagnostics_block, [(role, file, media_type)]) with the files to
    freeze. Any other path than DIAGNOSTIC_PATH_INDEX records absent.
    """
    if path_index != DIAGNOSTIC_PATH_INDEX:
        return (
            missing(
                "absent",
                "no separately bound diagnostic receipts for this path; electronic "
                "diagnostics must not be inferred from the campaign record",
            ),
            [],
        )
    if diagnostics_root is None:
        raise BundleError("path 0 requires --diagnostics-root with the bound receipts")

    runs = []
    files: list[tuple[str, Path, str]] = []
    for label, json_name, txt_name in DIAGNOSTIC_FILES:
        json_path = diagnostics_root / json_name
        txt_path = diagnostics_root / txt_name
        if not json_path.is_file() or not txt_path.is_file():
            raise BundleError(f"path 0 diagnostic receipt missing: {json_path} / {txt_path}")
        energy_record = load_json_strict(json_path)
        log_text = txt_path.read_text(encoding="utf-8")
        parsed = parse_diagnostic_log(log_text)
        energy_ev = energy_record.get("energy_ev")
        if not isinstance(energy_ev, (int, float)) or not math.isfinite(energy_ev):
            raise BundleError(f"{json_path}: absent or non-finite energy_ev")
        runs.append(
            {
                "label": label,
                "params": energy_record.get("params"),
                "energy_ev": energy_ev,
                **parsed,
                "source_assets": [
                    {
                        "filename": json_name,
                        "media_type": "application/json",
                        "sha256": digest_id(sha256_file(json_path)),
                    },
                    {
                        "filename": txt_name,
                        "media_type": "text/plain",
                        "sha256": digest_id(sha256_file(txt_path)),
                    },
                ],
            }
        )
        files.append(("electronic_diagnostic", json_path, "application/json"))
        files.append(("electronic_diagnostic", txt_path, "text/plain"))

    # The adopted-settings receipt must bind to the campaign's image-3 anchor.
    adopted = runs[0]
    anchor3 = pool.get(DIAGNOSTIC_IMAGE_INDEX)
    if anchor3 is None:
        raise BundleError("path 0 image 3 anchor missing; cannot bind diagnostics")
    if adopted["energy_ev"] != anchor3["gpaw_energy_ev"]:
        raise BundleError(
            f"adopted diagnostic energy {adopted['energy_ev']} does not bind to "
            f"anchor-3 GPAW energy {anchor3['gpaw_energy_ev']}"
        )
    return (
        {
            "status": "bound",
            "image_index": DIAGNOSTIC_IMAGE_INDEX,
            "note": (
                "Separately bound diagnostic receipts for path-0 image 3 "
                "(metallic-saddle SCF evidence). These are NOT part of the "
                "campaign record and are bound only for path 0."
            ),
            "runs": runs,
        },
        files,
    )


# --- Model artifacts -----------------------------------------------------------------

def load_model_predictions(
    models_root: Path | None, path_id: str, image_count: int
) -> tuple[dict[str, dict | None], dict[str, str], dict[str, dict], list[tuple[str, bytes, str]]]:
    """Per-model prediction for this path + provenance excerpts to freeze.

    Mirrors union_pilot.plan_path: a model is present only with a completed,
    finite profile of exactly image_count values; otherwise it lands in
    models_missing with the protocol's reason string.
    """
    predictions: dict[str, dict | None] = {}
    missing_models: dict[str, str] = {}
    provenance: dict[str, dict] = {}
    freeze: list[tuple[str, bytes, str]] = []
    for model in MODELS:
        artifact_path = (models_root / model / "cell_result.json") if models_root else None
        if artifact_path is None or not artifact_path.is_file():
            missing_models[model] = "no prediction record"
            provenance[model] = {
                "model": model,
                "status": "missing",
                "failure_reason": "model cell artifact not provided to the converter",
            }
            continue
        artifact = load_json_strict(artifact_path)
        if artifact.get("schema") != MODEL_CELL_SCHEMA:
            raise BundleError(f"{artifact_path}: expected schema {MODEL_CELL_SCHEMA}")
        prediction = next(
            (p for p in artifact.get("predictions", []) if p.get("path_id") == path_id),
            None,
        )
        provenance_info = {k: v for k, v in artifact.items() if k != "predictions"}
        excerpt = canonical_json({"provenance": provenance_info, "prediction": prediction})
        freeze.append((f"model_cell_excerpt/{model}", excerpt, "application/json"))

        package_key = MODEL_PACKAGE_KEY[model]
        versions = artifact.get("versions") or {}
        provenance[model] = {
            "model": model,
            "mlip_id": artifact.get("mlip_id"),
            "run_id": artifact.get("run_id"),
            "campaign_id": artifact.get("campaign_id"),
            "checkpoint": {
                "summary_schema": (artifact.get("checkpoint") or {}).get("schema"),
                "source_url": (artifact.get("checkpoint") or {}).get("url"),
                "artifact_url": MODEL_GCS_RESULT.format(model=model),
                "manifest_url": artifact.get("manifest_url"),
                "manifest_hash": artifact.get("manifest_hash"),
            },
            "package": package_key,
            "package_version": versions.get(package_key),
            "versions": versions,
            "dtype": "float64",
            "dtype_source": "campaign-float64 artifact layout (run_id z1-campaign-f64-*)",
            "device": versions.get("cuda_device"),
            "receipt_excerpt_sha256": digest_id(sha256_bytes(excerpt)),
        }

        profile = prediction.get("predicted_image_energies_ev") if prediction else None
        completed = (
            prediction is not None
            and prediction.get("status") == "completed"
            and isinstance(profile, list)
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in profile)
        )
        if not completed or len(profile) != image_count:
            reason = (
                "no prediction record"
                if prediction is None
                else str(prediction.get("status") or "profile_length_mismatch")
            )
            if completed and len(profile) != image_count:
                reason = "profile_length_mismatch"
            missing_models[model] = reason
            provenance[model]["status"] = "failed"
            provenance[model]["failure_reason"] = (
                prediction.get("error") if prediction else "no prediction record for this path"
            )
            if prediction and prediction.get("error_class"):
                provenance[model]["failure_class"] = prediction["error_class"]
            predictions[model] = None
            continue
        provenance[model]["status"] = "completed"
        provenance[model]["failure_reason"] = None
        predictions[model] = prediction
    return predictions, missing_models, provenance, freeze


# --- Method / provenance ---------------------------------------------------------------

def build_method(campaign: dict, panel: dict) -> dict:
    params = campaign["gpaw_params"]
    protocol = panel["execution_protocol"]
    return {
        "engine": "gpaw",
        "code": "GPAW",
        "code_version": missing(
            "not_recorded",
            "the campaign record does not carry the GPAW build; path-0 diagnostic "
            "logs report their own version inside diagnostics",
        ),
        "xc": params["xc"],
        "paw_setups": missing("not_recorded", "PAW setup identities are not in the campaign record"),
        "basis_grid": {
            "mode": params["mode"],
            "grid_spacing_h_angstrom": params["h"],
            "cutoff": missing("not_recorded", "fd mode: no plane-wave cutoff"),
        },
        "k_points": {"kpts": params["kpts"], "units": "monkhorst_pack_grid"},
        "charge": missing("not_recorded", "total charge is not in the campaign record"),
        "spin": missing("not_recorded", "spin policy is not in the campaign record"),
        "occupations_smearing": missing(
            "not_recorded", "occupation/smearing policy is not in the campaign record"
        ),
        "convergence": missing(
            "not_recorded",
            "SCF convergence criteria are not in the campaign record; anchor "
            "receipts carry per-evaluation status only",
        ),
        "neb": {
            "scope": (
                "Protocol that generated the reference reaction-path sequence "
                "(locked nebDFT2k panel, DFT(PBE) climbing-image NEB). The GPAW "
                "anchors in this bundle are single-point evaluations on these "
                "images; images are a reaction-path sequence, not time."
            ),
            "method": protocol["method"],
            "optimizer": protocol["optimizer"],
            "tangent": protocol["tangent_method"],
            "spring_constant_ev_per_angstrom2": protocol["spring_constant_ev_per_angstrom2"],
            "climbing_image": protocol["climb"],
            "fmax_ev_per_angstrom": protocol["force_convergence_ev_per_angstrom"],
            "max_steps": protocol["maximum_steps"],
            "endpoint_relaxation": protocol["endpoint_relaxation"],
            "barrier_definition": protocol["barrier_definition"],
            "failure_policy": protocol["failure_policy"],
        },
    }


def build_provenance(campaign: dict, panel: dict) -> dict:
    reference = panel["reference_provenance"]
    return {
        "creators": missing("not_recorded", "the bound sources do not name individual creators"),
        "organization": missing("not_recorded", "the bound sources do not name an organization"),
        "citation": {
            "dataset": reference["dataset"],
            "doi": reference["doi"],
            "source_repository": reference["source_repository"],
            "source_url": reference["source_url"],
            "theory": reference["theory"],
        },
        "license": reference["license"],
        "source_revision": {
            "reference_dataset_revision": reference["source_revision"],
            "reference_source_archive_sha256": reference["source_archive_sha256"],
            "converter_git_commit": git_head(),
        },
        "preregistration": campaign["preregistration"],
        "amendments": [campaign["amendment"]],
        "claim_evidence_ids": missing(
            "not_recorded", "no claim/evidence IDs are bound at Phase 0"
        ),
    }


# --- Asset freezing ---------------------------------------------------------------------

def bundle_asset_path(bundle_dir: Path, hex_digest: str, ext: str) -> Path:
    return bundle_dir / "assets" / "sha256" / hex_digest[:2] / f"{hex_digest}.{ext}"


def freeze_assets(
    bundle_dir: Path,
    payloads: list[tuple[dict, bytes, str]],
) -> None:
    """Write content-addressed assets + .sha256 sidecars (manifest goes LAST)."""
    for entry, payload, ext in payloads:
        hex_digest = sha256_bytes(payload)
        assert entry["sha256"] == digest_id(hex_digest)
        dest = bundle_asset_path(bundle_dir, hex_digest, ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        dest.with_name(dest.name + ".sha256").write_text(
            f"{hex_digest}  {dest.name}\n", encoding="utf-8"
        )


# --- Verification -------------------------------------------------------------------------

def _resolve_json_pointer(document, pointer: str):
    """RFC 6901 resolution into a parsed JSON document."""
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise BundleError(f"not a JSON pointer: {pointer!r}")
    node = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(token)]
        elif isinstance(node, dict):
            node = node[token]
        else:
            raise BundleError(f"JSON pointer {pointer!r} walks through a scalar")
    return node


def _dereference_series_sources(manifest: dict, bundle_dir: Path, check) -> None:
    """P1-1: every displayed series value must match its declared source bytes.

    A resealed manifest that edits a series while leaving the frozen source
    asset untouched is rejected here: the pointer is resolved into the frozen
    asset and compared to the stored value.
    """
    assets_by_digest = {a["sha256"]: a for a in manifest["assets"]}
    documents: dict[str, object] = {}
    for series in manifest["series"]:
        series_id = series["series_id"]
        for i, pointer in enumerate(series["value_sources"]):
            if pointer is None:
                continue
            if i >= len(series["values"]):
                check(
                    False,
                    f"{series_id}: value_sources longer than values — "
                    "trajectory/profile cardinality mismatch",
                )
                continue
            asset = assets_by_digest.get(pointer["asset_sha256"])
            if asset is None:
                continue  # already reported as an unresolved source pointer
            target = bundle_dir / asset["uri"]
            if not target.is_file():
                continue  # already reported as a missing asset
            digest = pointer["asset_sha256"]
            if digest not in documents:
                try:
                    documents[digest] = json.loads(target.read_bytes())
                except (OSError, json.JSONDecodeError) as exc:
                    check(False, f"{series_id}: source asset {asset['uri']} unreadable: {exc}")
                    continue
            try:
                sourced = _resolve_json_pointer(documents[digest], pointer["json_pointer"])
            except (KeyError, IndexError, ValueError, BundleError):
                check(
                    False,
                    f"{series_id}: source pointer {pointer['json_pointer']} does not "
                    f"resolve in frozen asset {asset['uri']}",
                )
                continue
            check(
                sourced == series["values"][i],
                f"{series_id}: displayed value at image {i} "
                f"({series['values'][i]!r}) does not match its declared source "
                f"({sourced!r} at {pointer['json_pointer']})",
            )


def _verify_diagnostics(manifest: dict, bundle_dir: Path, check) -> None:
    """P1-3: revalidate bound diagnostic receipts against the frozen assets.

    Runs the same binding validation as the build: each run's parsed electronic
    facts must re-parse from its digest-bound frozen receipts, and the adopted
    run's energy must bind to the stored GPAW series at the diagnostic image.
    """
    diagnostics = manifest["diagnostics"]
    if not isinstance(diagnostics, dict) or diagnostics.get("status") != "bound":
        return
    check(
        manifest["path_index"] == DIAGNOSTIC_PATH_INDEX,
        f"diagnostics bound for path {manifest['path_index']}; only path "
        f"{DIAGNOSTIC_PATH_INDEX} may carry bound electronic diagnostics",
    )
    assets_by_digest = {a["sha256"]: a for a in manifest["assets"]}
    gpaw = next(s for s in manifest["series"] if s["series_id"] == "gpaw_total_energy")
    image_index = diagnostics["image_index"]
    adopted_seen = False
    for run in diagnostics["runs"]:
        label = run.get("label", "?")
        receipt_docs: dict[str, bytes] = {}
        for source in run["source_assets"]:
            asset = assets_by_digest.get(source.get("sha256"))
            check(
                asset is not None,
                f"diagnostic {label}: source asset {source.get('sha256')} is not "
                "a frozen bundle asset",
            )
            if asset is None:
                continue
            check(
                asset["role"] == "electronic_diagnostic",
                f"diagnostic {label}: source asset {asset['uri']} has role "
                f"{asset['role']!r}, not electronic_diagnostic",
            )
            target = bundle_dir / asset["uri"]
            if target.is_file():
                receipt_docs[source["media_type"]] = target.read_bytes()
        energy_doc = receipt_docs.get("application/json")
        if energy_doc is not None:
            try:
                record = json.loads(energy_doc)
            except json.JSONDecodeError as exc:
                check(False, f"diagnostic {label}: energy receipt is not JSON: {exc}")
                record = {}
            check(
                record.get("energy_ev") == run["energy_ev"],
                f"diagnostic {label}: energy_ev {run['energy_ev']!r} does not match "
                f"the frozen receipt ({record.get('energy_ev')!r})",
            )
            check(
                record.get("params") == run["params"],
                f"diagnostic {label}: params do not match the frozen receipt",
            )
        log_doc = receipt_docs.get("text/plain")
        if log_doc is not None:
            try:
                parsed = parse_diagnostic_log(log_doc.decode("utf-8"))
            except (BundleError, UnicodeDecodeError) as exc:
                check(False, f"diagnostic {label}: log does not re-parse: {exc}")
                parsed = None
            if parsed is not None:
                for key in ("gap_ev", "fermi_level_ev", "gpaw_version", "charge_e"):
                    check(
                        run.get(key) == parsed[key],
                        f"diagnostic {label}: {key} {run.get(key)!r} does not "
                        f"re-parse from the frozen log ({parsed[key]!r})",
                    )
                for key in ("scf", "spin", "occupations"):
                    check(
                        run.get(key) == parsed[key],
                        f"diagnostic {label}: {key} does not re-parse from the frozen log",
                    )
        if str(label).startswith("adopted"):
            adopted_seen = True
            check(
                gpaw["values"][image_index] == run["energy_ev"],
                f"diagnostic {label}: adopted energy {run['energy_ev']!r} does not "
                f"bind to the stored GPAW value at image {image_index} "
                f"({gpaw['values'][image_index]!r})",
            )
    check(adopted_seen, "diagnostics: no adopted-settings run is bound")


def _checks_from_stored(manifest: dict, bundle_dir: Path | None = None) -> list[str]:
    """Recompute every derived scalar from the manifest's stored arrays.

    With bundle_dir (frozen-bundle verification), also dereference every series
    source pointer against the frozen asset bytes and revalidate any bound
    diagnostic receipts. Returns a list of failure strings; empty means the
    bundle reproduces.
    """
    failures = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    coordinates = manifest["coordinates"]
    frames = coordinates["frames"]
    n = len(frames)
    check(coordinates["units"] == UNITS_ANGSTROM, "coordinates.units is not angstrom")
    species = coordinates["species"]
    check(len(species) == coordinates["atom_count"], "species/atom_count mismatch")
    reaction = coordinates["reaction_coordinate"]["values"]
    check(reaction == list(range(n)), "reaction coordinate is not zero-based contiguous")
    check(
        all(reaction[i] < reaction[i + 1] for i in range(len(reaction) - 1)),
        "declared path coordinate is non-monotone",
    )
    for frame in frames:
        try:
            _finite_matrix(frame["positions_angstrom"], (len(species), 3), "positions")
            _finite_matrix(frame["lattice_angstrom"], (3, 3), "cell")
        except BundleError as exc:
            failures.append(f"frame {frame.get('image_index')}: {exc}")
        check(
            isinstance(frame.get("pbc"), list) and len(frame["pbc"]) == 3,
            f"frame {frame.get('image_index')}: invalid PBC state",
        )

    series_by_id = {s["series_id"]: s for s in manifest["series"]}
    for series in manifest["series"]:
        check(series["image_indices"] == list(range(n)), f"{series['series_id']}: image_indices")
        check(
            len(series["values"]) == n and len(series["value_status"]) == n,
            f"{series['series_id']}: trajectory/profile cardinality mismatch",
        )
        for value, status in zip(series["values"], series["value_status"], strict=True):
            if status == "evaluated":
                check(
                    isinstance(value, (int, float)) and math.isfinite(value),
                    f"{series['series_id']}: evaluated value missing/non-finite",
                )
            else:
                check(value is None, f"{series['series_id']}: missing value not null")

    gpaw = series_by_id["gpaw_total_energy"]
    vasp = series_by_id["vasp_reference_total_energy"]
    evaluated = [i for i, s in enumerate(gpaw["value_status"]) if s == "evaluated"]
    gates = manifest["quality_gates"]
    selection = manifest["selection"]

    check(selection["evaluated"] == evaluated, "selection.evaluated does not recompute")
    pool_energies = {i: gpaw["values"][i] for i in evaluated}
    dense_complete = len(evaluated) == n
    check(
        gates["same_engine"]["dense_complete"] == dense_complete,
        "dense_complete does not recompute",
    )
    if dense_complete:
        dense_energies = [gpaw["values"][i] for i in range(n)]
        dense_barrier = max(dense_energies) - min(dense_energies)
        check(
            gates["same_engine"]["dense_barrier_ev"] == dense_barrier,
            "dense barrier does not recompute from stored gpaw series",
        )
        dmin, dmax = select_extrema(dense_energies)
        check(
            selection["dense_profile_extrema"] == {"argmin": dmin, "argmax": dmax},
            "dense-profile extrema do not recompute (tie policy: first occurrence)",
        )
    reference_barrier = max(vasp["values"]) - min(vasp["values"])
    check(
        gates["cross_engine"]["reference_barrier_ev"] == reference_barrier,
        "reference barrier does not recompute from stored vasp series",
    )
    if dense_complete:
        signed = (dense_barrier - reference_barrier) * 1000.0
        check(
            gates["cross_engine"]["dense_vs_reference_signed_error_mev"] == signed,
            "dense-vs-reference signed error does not recompute",
        )

    union_set: set[int] = set()
    for model, entry in selection["per_model"].items():
        model_series = series_by_id.get(f"model_total_energy/{model}")
        check(model_series is not None, f"model {model}: series missing")
        if model_series is None:
            continue
        profile = model_series["values"]
        mmin, mmax = select_extrema(profile)
        anchor = build_anchor_set(n, mmin, mmax)
        check(entry["model_min_index"] == mmin, f"{model}: model_min_index")
        check(entry["model_max_index"] == mmax, f"{model}: model_max_index")
        check(entry["nominated"] == anchor["anchor_indices"], f"{model}: nominated set")
        check(entry["window"] == anchor["window"], f"{model}: window")
        union_set.update(entry["nominated"])
        missing_pool = [i for i in entry["nominated"] if i not in pool_energies]
        if entry["complete"] and missing_pool:
            check(False, f"{model}: nominated anchors {missing_pool} lack evaluated values")
        if entry["complete"] and not missing_pool:
            sparse = max(pool_energies[i] for i in entry["nominated"]) - min(
                pool_energies[i] for i in entry["nominated"]
            )
            check(
                entry["sparse_barrier_ev"] == sparse,
                f"{model}: sparse barrier does not recompute",
            )
            if dense_complete:
                se_signed = (sparse - dense_barrier) * 1000.0
                deficit = selection["guidance_deficits_mev"].get(model, {})
                check(
                    deficit.get("same_engine_signed_error_mev") == se_signed,
                    f"{model}: guidance deficit does not recompute",
                )
                same = gates["same_engine"]["per_model"].get(model, {})
                check(
                    same.get("same_engine_abs_error_mev") == abs(se_signed),
                    f"{model}: same-engine error does not recompute",
                )
            cross_signed = (sparse - reference_barrier) * 1000.0
            cross = gates["cross_engine"]["per_model"].get(model, {})
            check(
                cross.get("vasp_signed_error_mev") == cross_signed,
                f"{model}: cross-engine error does not recompute",
            )
    check(selection["nominated_union"] == sorted(union_set), "union set does not recompute")
    universe = set(union_set)
    if selection["dense_extension"]["applied"]:
        universe.update(range(n))
    check(
        selection["anchor_universe"] == sorted(universe), "anchor universe does not recompute"
    )
    check(
        selection["dense_extension"]["supplied_indices"] == sorted(universe - union_set),
        "dense-extension supplied set does not recompute",
    )
    if dense_complete:
        dmin, dmax = select_extrema(dense_energies)
        for model, entry in selection["per_model"].items():
            expected_misses = sorted({dmin, dmax} - set(entry["nominated"]))
            check(
                selection["guidance_misses"].get(model) == expected_misses,
                f"{model}: guidance misses do not recompute",
            )

    gate = analyze_offsets(
        [(i, pool_energies[i], vasp["values"][i]) for i in sorted(pool_energies)],
        gate_mev=float(gates["thresholds_mev"]["t1_gate"]),
    )
    check(gates["t1"]["wander_mev"] == gate["offset_wander_mev"], "T1 wander does not recompute")
    check(gates["t1"]["driver_pair"] == gate["driver_pair"], "T1 driver pair does not recompute")
    check(gates["t1"]["verdict"] == gate["verdict"], "T1 verdict does not recompute")
    check(
        gates["t1"]["offset_mean_mev"] == gate["offset_mean_mev"],
        "T1 offset mean does not recompute",
    )
    check(
        gates["t1"]["offset_series_mev"]
        == [
            {"image_index": row["index"], "offset_mev": row["offset_mev"]}
            for row in gate["per_image"]
        ],
        "T1 offset series does not recompute",
    )

    # P1-2: verdicts are derived strictly from the stored numeric errors and
    # the frozen 15/40 thresholds — never trusted from the recorded strings.
    per_model_expected: dict[str, str] = {}
    for model, same in gates["same_engine"]["per_model"].items():
        expected_model_verdict = path_verdict(
            same.get("same_engine_abs_error_mev"), same.get("complete", False)
        )
        per_model_expected[model] = expected_model_verdict
        check(
            same.get("verdict") == expected_model_verdict,
            f"{model}: recorded verdict {same.get('verdict')!r} does not follow "
            f"from the stored same-engine abs error "
            f"{same.get('same_engine_abs_error_mev')!r} (expected "
            f"{expected_model_verdict!r} under the frozen thresholds)",
        )
    if not selection["per_model"]:
        expected_se = "no_guidance"
    else:
        expected_se = max(per_model_expected.values(), key=lambda v: VERDICT_RANK[v])
    expected_label = f"{expected_se}_t1_{gate['verdict']}"
    check(
        gates["verdict"]["same_engine"] == expected_se,
        f"recorded same-engine verdict {gates['verdict']['same_engine']!r} does "
        f"not recompute from the stored numeric errors ({expected_se!r})",
    )
    check(
        gates["verdict"]["t1"] == gate["verdict"],
        "recorded T1 verdict does not recompute from the stored offset series",
    )
    check(
        gates["verdict"]["cross_engine_contaminated"]
        == (gate["verdict"] == VERDICT_CONTAMINATED),
        "cross_engine_contaminated flag does not follow from the recomputed T1 verdict",
    )
    check(
        gates["verdict"]["label"] == expected_label,
        f"verdict label {gates['verdict']['label']!r} does not recompute ({expected_label!r})",
    )

    # Source pointers resolve to frozen assets.
    asset_digests = {a["sha256"] for a in manifest["assets"]}
    for series in manifest["series"]:
        for pointer in series["value_sources"]:
            if pointer is None:
                continue
            check(
                pointer["asset_sha256"] in asset_digests,
                f"{series['series_id']}: source pointer {pointer['asset_sha256']} unresolved",
            )
    if bundle_dir is not None:
        _dereference_series_sources(manifest, bundle_dir, check)
        _verify_diagnostics(manifest, bundle_dir, check)
    return failures


def verify_bundle(bundle_dir: Path) -> list[str]:
    """Fail-closed verification of a frozen bundle directory."""
    failures: list[str] = []
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return [f"{bundle_dir}: no manifest.json"]
    raw = manifest_path.read_bytes()
    try:
        manifest = json.loads(
            raw.decode("utf-8"), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v))
        )
    except (ValueError, UnicodeDecodeError) as exc:
        return [f"manifest is not valid strict JSON: {exc}"]
    if canonical_json(manifest) != raw:
        failures.append("manifest is not canonical JSON (sorted keys, 2-space indent, trailing newline)")
    digest = sha256_bytes(raw)
    sidecar = manifest_path.with_name("manifest.json.sha256")
    if not sidecar.is_file() or sidecar.read_text(encoding="utf-8").split()[0] != digest:
        failures.append("manifest .sha256 sidecar missing or mismatched")
    identity = {k: v for k, v in manifest.items() if k != "bundle_id"}
    expected_id = digest_id(sha256_bytes(canonical_json(identity)))
    if manifest.get("bundle_id") != expected_id:
        failures.append(
            f"bundle_id {manifest.get('bundle_id')} does not recompute ({expected_id})"
        )
    if bundle_dir.name != expected_id.removeprefix("sha256:"):
        failures.append("bundle directory name does not match the recomputed digest")
    if bundle_dir.parent.name != expected_id.removeprefix("sha256:")[:2]:
        failures.append("bundle directory shard does not match the digest prefix")

    if SCHEMA_PATH.is_file():
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(manifest, schema)
        except jsonschema.ValidationError as exc:
            failures.append(f"schema validation failed: {exc.message}")
    else:
        failures.append(f"schema file missing: {SCHEMA_PATH}")

    if not failures:
        for asset in manifest.get("assets", []):
            target = bundle_dir / asset["uri"]
            if not target.is_file():
                failures.append(f"asset missing: {asset['uri']}")
                continue
            payload = target.read_bytes()
            if len(payload) != asset["bytes"]:
                failures.append(f"asset {asset['uri']}: byte count changed")
            hex_digest = sha256_bytes(payload)
            if digest_id(hex_digest) != asset["sha256"]:
                failures.append(f"asset {asset['uri']}: source hash changed")
            asset_sidecar = target.with_name(target.name + ".sha256")
            if not asset_sidecar.is_file() or asset_sidecar.read_text(
                encoding="utf-8"
            ).split()[0] != hex_digest:
                failures.append(f"asset {asset['uri']}: .sha256 sidecar missing/mismatched")
        try:
            failures.extend(_checks_from_stored(manifest, bundle_dir))
        except Exception as exc:  # fail closed: a crashed recompute is a failure
            failures.append(f"stored-array recomputation error: {exc!r}")
    return failures


# --- Build -----------------------------------------------------------------------------

def build_bundle(
    path_index: int,
    panel_path: Path,
    campaign_path: Path,
    anchors_root: Path,
    models_root: Path | None,
    diagnostics_root: Path | None,
) -> tuple[dict, list[tuple[dict, bytes, str]]]:
    campaign = load_campaign(campaign_path)
    panel = load_panel(panel_path)

    record = next(
        (p for p in campaign["per_path"] if p["path_index"] == path_index),
        None,
    )
    if record is None:
        raise BundleError(f"path_index {path_index} is not an active campaign path")
    path_id = record["path_id"]
    panel_paths = panel["paths"]
    if not 0 <= path_index < len(panel_paths):
        raise BundleError(f"path_index {path_index} outside the panel")
    panel_entry = panel_paths[path_index]
    if panel_entry["path_id"] != path_id:
        raise BundleError(
            f"panel path at index {path_index} is {panel_entry['path_id']}, "
            f"campaign expects {path_id} — trajectory/profile identity mismatch"
        )
    image_count = len(panel_entry["input_images"])
    if record["image_count"] != image_count:
        raise BundleError("campaign/panel image_count mismatch")
    reference_energies = panel_entry["reference"]["energies_ev"]
    if len(reference_energies) != image_count:
        raise BundleError(
            f"reference profile length {len(reference_energies)} != image count "
            f"{image_count} — trajectory/profile frame mismatch"
        )
    reference_barrier_ev = float(panel_entry["reference_barrier_ev"])
    recomputed_reference_barrier = max(reference_energies) - min(reference_energies)
    if recomputed_reference_barrier != reference_barrier_ev:
        raise BundleError("panel reference barrier does not recompute from its profile")

    receipts = load_receipts(anchors_root, path_index, path_id, image_count)
    pool, pool_status = gpaw_pool(receipts, reference_energies, campaign["gpaw_params"])

    model_predictions, models_missing, model_provenance, model_freeze = load_model_predictions(
        models_root, path_id, image_count
    )

    dense_energies = (
        [pool[i]["gpaw_energy_ev"] for i in range(image_count)]
        if len(pool) == image_count
        else None
    )
    coordinates = build_coordinates(panel_entry)
    selection = build_selection(image_count, model_predictions, pool, dense_energies)
    gates = build_quality_gates(
        campaign["thresholds"],
        image_count,
        pool,
        reference_energies,
        reference_barrier_ev,
        selection,
    )
    diagnostics, diagnostic_files = build_diagnostics(path_index, diagnostics_root, pool)

    # Fail closed: every derived scalar must equal the campaign record.
    crosscheck_campaign(
        record,
        path_index,
        image_count,
        pool,
        model_predictions,
        models_missing,
        selection,
        gates,
        reference_barrier_ev,
    )

    # --- Assets (frozen BEFORE the manifest; publication discipline) ---
    asset_payloads: list[tuple[dict, bytes, str]] = []

    def add_asset(role: str, payload: bytes, media_type: str, ext: str) -> str:
        hex_digest = sha256_bytes(payload)
        entry = {
            "role": role,
            "media_type": media_type,
            "format": ext,
            "bytes": len(payload),
            "sha256": digest_id(hex_digest),
            "uri": f"assets/sha256/{hex_digest[:2]}/{hex_digest}.{ext}",
        }
        asset_payloads.append((entry, payload, ext))
        return entry["sha256"]

    add_asset("campaign_record", campaign_path.read_bytes(), "application/json", "json")
    panel_excerpt_digest = add_asset(
        "panel_path_excerpt", canonical_json(panel_entry), "application/json", "json"
    )
    anchor_asset_digests: dict[int, str] = {}
    for index in sorted(receipts):
        anchor_asset_digests[index] = add_asset(
            "anchor_receipt",
            receipts[index]["__file__"].read_bytes(),
            "application/json",
            "json",
        )
    model_excerpt_digests: dict[str, str] = {}
    for role, payload, media_type in model_freeze:
        model = role.split("/", 1)[1]
        model_excerpt_digests[model] = add_asset(role, payload, media_type, "json")
    for role, file, media_type in diagnostic_files:
        add_asset(role, file.read_bytes(), media_type, file.suffix.lstrip("."))

    series = build_series(
        image_count,
        pool,
        pool_status,
        reference_energies,
        model_predictions,
        anchor_asset_digests,
        panel_excerpt_digest,
        model_excerpt_digests,
    )

    checks = [
        {"name": "source_sidecar_hash", "status": "pass",
         "detail": "campaign + panel bytes match their .sha256 sidecars"},
        {"name": "atom_identity_consistent", "status": "pass",
         "detail": "species/order identical across all frames"},
        {"name": "cell_and_units_declared", "status": "pass",
         "detail": "every frame has a 3x3 finite cell, PBC, angstrom units"},
        {"name": "reaction_coordinate_monotone", "status": "pass",
         "detail": "zero-based contiguous image indices"},
        {"name": "profile_cardinality", "status": "pass",
         "detail": "reference/model profiles match the frame count; GPAW per-value status"},
        {"name": "evaluated_anchors_within_universe", "status": "pass",
         "detail": "every evaluated anchor lies inside the declared anchor universe"},
        {"name": "campaign_record_crosscheck", "status": "pass",
         "detail": "all derived scalars recompute exactly to the campaign record"},
        {"name": "source_pointers_resolve", "status": "pass",
         "detail": "every displayed value carries a frozen-asset JSON pointer"},
    ]
    warnings = []
    if gates["t1"]["verdict"] == VERDICT_CONTAMINATED:
        warnings.append(
            "T1 convention-wander gate FAILED: cross-engine (VASP-referenced) "
            "numbers are convention-contaminated; the same-engine basis is "
            "primary (amendment A1)."
        )
    if selection["dense_extension"]["applied"]:
        warnings.append(
            f"Dense extension active on a <= {DENSE_EXTENSION_IMAGE_THRESHOLD}-image "
            "path: sparse ≡ nearly dense by construction; same-engine verdicts "
            "are partly structural (gate-power caveat)."
        )
    if path_index == DIAGNOSTIC_PATH_INDEX and diagnostics.get("status") == "bound":
        warnings.append(
            "Metallic-saddle mechanism suspected; see bound image-3 electronic "
            "diagnostics (docs/analysis/t1-wander-mechanism.md)."
        )
    warnings.append(
        "Images are a reaction-path sequence (NEB image index); never display "
        "the index as time, dynamics, or temperature."
    )

    manifest = {
        "schema": SCHEMA_ID,
        "bundle_id": None,  # replaced after canonical hashing
        "campaign_id": "z1-union-pilot",
        "campaign_version": campaign["schema"],
        "campaign_sha256": campaign["campaign_sha256"],
        "run_id": anchors_root.parent.name,
        "path_id": path_id,
        "path_index": path_index,
        "chemical_system": record["chemical_system"],
        "image_count": image_count,
        "created_at": campaign["recorded_at"],
        "status": "active",
        "supersedes": None,
        "retraction": None,
        "source_artifacts": [
            source_artifact(
                "campaign_record", artifact_uri(campaign_path), campaign_path, CAMPAIGN_SCHEMA
            ),
            source_artifact("barrier_panel", artifact_uri(panel_path), panel_path, PANEL_SCHEMA),
            *(
                source_artifact(
                    "anchor_receipt",
                    artifact_uri(receipts[i]["__file__"]),
                    receipts[i]["__file__"],
                    ANCHOR_SCHEMA,
                )
                for i in sorted(receipts)
            ),
            *(
                source_artifact(
                    "model_cell_result",
                    artifact_uri(models_root / model / "cell_result.json"),
                    models_root / model / "cell_result.json",
                    MODEL_CELL_SCHEMA,
                )
                for model in MODELS
                if models_root is not None and (models_root / model / "cell_result.json").is_file()
            ),
            *(
                source_artifact("electronic_diagnostic", artifact_uri(file), file, None)
                for _, file, _ in diagnostic_files
            ),
        ],
        "producer": {
            "tool": TOOL_PATH,
            "version": TOOL_VERSION,
            "git_commit": git_head(),
            "container_digest": missing(
                "not_containerized", "Phase 0 runs the converter directly, not in a pinned container"
            ),
            "normalized_parameters": {
                "path_index": path_index,
                "panel_sha256": digest_id(sha256_file(panel_path)),
                "campaign_sha256": digest_id(sha256_file(campaign_path)),
                "anchor_receipt_sha256": {
                    str(i): digest_id(sha256_file(receipts[i]["__file__"])) for i in sorted(receipts)
                },
                "t1_gate_mev": float(campaign["thresholds"]["t1_gate_mev"]),
                "schema": SCHEMA_ID,
                "canonicalization": "json sorted keys, 2-space indent, trailing newline",
            },
        },
        "method": build_method(campaign, panel),
        "model_provenance": [model_provenance[m] for m in MODELS if m in model_provenance],
        "coordinates": coordinates,
        "series": series,
        "selection": selection,
        "quality_gates": gates,
        "diagnostics": diagnostics,
        "assets": [entry for entry, _, _ in asset_payloads],
        "provenance": build_provenance(campaign, panel),
        "quality": {
            "state": "verified",
            "checks": checks,
            "warnings": warnings,
        },
    }

    identity = {k: v for k, v in manifest.items() if k != "bundle_id"}
    manifest["bundle_id"] = digest_id(sha256_bytes(canonical_json(identity)))

    # Schema validation is a build-time gate: an invalid manifest is refused.
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as exc:
        raise BundleError(f"manifest failed schema validation: {exc.message}") from exc

    # Self-verify the in-memory bundle before anything hits disk.
    failures = _checks_from_stored(manifest)
    if failures:
        raise BundleError("bundle self-verification failed: " + "; ".join(failures))
    return manifest, asset_payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path-index", type=int, help="Z1 panel/campaign path index")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR,
                        help="bundle root (default: data/visualization/bundles)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate only; write nothing")
    parser.add_argument("--verify", type=Path, metavar="BUNDLE_DIR",
                        help="verify a frozen bundle directory and exit")
    parser.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    parser.add_argument("--campaign", type=Path, default=DEFAULT_CAMPAIGN)
    parser.add_argument("--anchors-root", type=Path, default=DEFAULT_ANCHORS_ROOT)
    parser.add_argument("--models-root", type=Path, default=DEFAULT_MODELS_ROOT)
    parser.add_argument("--diagnostics-root", type=Path, default=DEFAULT_DIAGNOSTICS_ROOT)
    args = parser.parse_args()

    if args.verify is not None:
        failures = verify_bundle(args.verify)
        if failures:
            for failure in failures:
                print(f"FAIL {failure}", file=sys.stderr)
            return 1
        print(json.dumps({"bundle": str(args.verify), "verified": True}))
        return 0

    if args.path_index is None:
        parser.error("--path-index is required for a build")

    try:
        manifest, asset_payloads = build_bundle(
            args.path_index,
            args.panel,
            args.campaign,
            args.anchors_root,
            args.models_root,
            args.diagnostics_root,
        )
    except BundleError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    hex_digest = manifest["bundle_id"].removeprefix("sha256:")
    bundle_dir = args.outdir / "sha256" / hex_digest[:2] / hex_digest
    summary = {
        "path_index": args.path_index,
        "path_id": manifest["path_id"],
        "bundle_id": manifest["bundle_id"],
        "verdict": manifest["quality_gates"]["verdict"]["label"],
        "assets": len(asset_payloads),
    }
    if args.dry_run:
        summary["dry_run"] = True
        print(json.dumps(summary, indent=1, sort_keys=True))
        return 0

    # Publication discipline: assets (+ sidecars) first, manifest LAST.
    bundle_dir.mkdir(parents=True, exist_ok=True)
    freeze_assets(bundle_dir, asset_payloads)
    raw = canonical_json(manifest)
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_bytes(raw)
    manifest_path.with_name("manifest.json.sha256").write_text(
        f"{sha256_bytes(raw)}  manifest.json\n", encoding="utf-8"
    )
    summary["bundle_dir"] = str(bundle_dir)
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
