"""Locked Z1 CampaignManifest loading and row-native CI-NEB execution."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import urllib.parse
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np
from ase import Atoms

BARRIER_ROW_ID = "barrier"
PANEL_SCHEMA = "lupine.z1.neb_barrier_panel.v1"
SUPPORTED_PROTOCOL = {
    "barrier_definition": "max(image_energy_ev) - min(image_energy_ev)",
    "climb": True,
    "endpoint_relaxation": True,
    "failure_policy": "record failure without imputation",
    "method": "climbing-image NEB",
    "optimizer": "FIRE",
    "tangent_method": "improvedtangent",
}


class PredictionCheckpoint(Protocol):
    def get_prediction(
        self, row_id: str, case_index: int, case: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    def record_prediction(
        self,
        row_id: str,
        case_index: int,
        case: dict[str, Any],
        prediction: dict[str, Any],
    ) -> None: ...


def stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_content_hash(document: dict[str, Any], hash_field: str = "content_hash") -> str:
    unhashed = {key: value for key, value in document.items() if key != hash_field}
    return "sha256:" + hashlib.sha256(stable_json_bytes(unhashed)).hexdigest()


def locked_artifact_url(manifest_url: str, locked_path: str) -> str:
    """Resolve a repo-relative campaign artifact without weakening its lock."""
    relative = pathlib.PurePosixPath(locked_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"candidate_panel.path must be repo-relative: {locked_path}")
    if manifest_url.startswith("file://"):
        parsed_file = urllib.parse.urlparse(manifest_url)
        if parsed_file.netloc not in ("", "localhost"):
            raise ValueError(f"unsupported file:// host in URL: {manifest_url}")
        manifest_url = urllib.parse.unquote(parsed_file.path)
    if not manifest_url.startswith(("gs://", "http://", "https://")):
        manifest_path = pathlib.Path(manifest_url).resolve()
        for root in (manifest_path.parent, *manifest_path.parents):
            candidate = root.joinpath(*relative.parts)
            if candidate.is_file():
                return str(candidate)
        raise FileNotFoundError(
            f"locked candidate panel {locked_path} was not found above {manifest_path}"
        )

    parsed = urllib.parse.urlsplit(manifest_url)
    marker = "/campaigns/"
    if marker not in parsed.path:
        raise ValueError(
            "remote CampaignManifest URL must contain /campaigns/ so repo-relative "
            "candidate_panel.path can be resolved"
        )
    root_path = parsed.path.split(marker, 1)[0].rstrip("/")
    artifact_path = root_path + "/" + "/".join(relative.parts)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, artifact_path, "", ""))


def _sha256_lock(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{label} must be a sha256:<64 lowercase hex> lock")
    digest = value[7:]
    if any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{label} must be a sha256:<64 lowercase hex> lock")
    return value


def validate_panel(panel: dict[str, Any]) -> dict[str, Any]:
    if panel.get("schema") != PANEL_SCHEMA:
        raise ValueError(f"candidate panel must use {PANEL_SCHEMA}")
    measurement = panel.get("measurement")
    if not isinstance(measurement, dict):
        raise ValueError("candidate panel measurement must be an object")
    if measurement.get("metric") != "barrier_mae" or measurement.get("unit") != "meV":
        raise ValueError("candidate panel measurement must be barrier_mae in meV")
    minimum_path_count = measurement.get("minimum_path_count")
    if not isinstance(minimum_path_count, int) or minimum_path_count < 1:
        raise ValueError("candidate panel minimum_path_count must be a positive integer")
    protocol = panel.get("execution_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("candidate panel execution_protocol must be an object")
    mismatches = [
        key for key, expected in SUPPORTED_PROTOCOL.items() if protocol.get(key) != expected
    ]
    if mismatches:
        raise ValueError(
            "unsupported frozen Z1 execution protocol fields: " + ", ".join(mismatches)
        )
    for key in (
        "force_convergence_ev_per_angstrom",
        "spring_constant_ev_per_angstrom2",
    ):
        value = protocol.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or float(value) <= 0:
            raise ValueError(f"candidate panel execution_protocol.{key} must be positive")
    maximum_steps = protocol.get("maximum_steps")
    if not isinstance(maximum_steps, int) or maximum_steps < 1:
        raise ValueError("candidate panel execution_protocol.maximum_steps must be positive")
    paths = panel.get("paths")
    if not isinstance(paths, list) or len(paths) < minimum_path_count:
        count = len(paths) if isinstance(paths, list) else 0
        raise ValueError(
            f"candidate panel needs at least {minimum_path_count} paths; found {count}"
        )
    path_ids: set[str] = set()
    for index, path in enumerate(paths):
        if not isinstance(path, dict):
            raise ValueError(f"candidate panel paths[{index}] must be an object")
        path_id = path.get("path_id")
        if not isinstance(path_id, str) or not path_id or path_id in path_ids:
            raise ValueError(f"candidate panel paths[{index}] needs a unique path_id")
        path_ids.add(path_id)
        reference = path.get("reference_barrier_ev")
        if not isinstance(reference, (int, float)) or not math.isfinite(reference):
            raise ValueError(f"candidate panel path {path_id} needs reference_barrier_ev")
        images = path.get("input_images")
        if not isinstance(images, list) or len(images) < 3:
            raise ValueError(f"candidate panel path {path_id} needs at least three input_images")
    return {
        "schema": panel["schema"],
        "panel_id": panel.get("panel_id"),
        "path_count": len(paths),
        "minimum_path_count": minimum_path_count,
        "release_ready": True,
        "blockers": [],
    }


def load_campaign_panel(
    manifest_url: str,
    mlip_id: str,
    read_url: Callable[[str], bytes],
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    manifest = json.loads(read_url(manifest_url).decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("CampaignManifest must be a JSON object")
    expected_manifest_hash = _sha256_lock(
        manifest.get("content_hash"), "CampaignManifest.content_hash"
    )
    actual_manifest_hash = canonical_content_hash(manifest)
    if actual_manifest_hash != expected_manifest_hash:
        raise ValueError(
            f"CampaignManifest content_hash mismatch: expected {expected_manifest_hash}, "
            f"got {actual_manifest_hash}"
        )
    available_models = manifest.get("available_models")
    if not isinstance(available_models, list) or mlip_id not in {
        model.get("model_id") for model in available_models if isinstance(model, dict)
    }:
        raise ValueError(
            f"mlip_id {mlip_id} is not registered in CampaignManifest.available_models"
        )
    acceptance = manifest.get("acceptance_test")
    if (
        not isinstance(acceptance, dict)
        or acceptance.get("metric") != "barrier_mae"
        or acceptance.get("unit") != "meV"
        or acceptance.get("operator") != "lte"
        or not isinstance(acceptance.get("threshold"), (int, float))
    ):
        raise ValueError(
            "Z1 CampaignManifest acceptance_test must be a numeric barrier_mae lte in meV"
        )
    execution = manifest.get("execution")
    panel_lock = execution.get("candidate_panel") if isinstance(execution, dict) else None
    if not isinstance(panel_lock, dict):
        raise ValueError("Z1 CampaignManifest execution.candidate_panel lock is required")
    panel_path = panel_lock.get("path")
    if not isinstance(panel_path, str) or not panel_path:
        raise ValueError("Z1 CampaignManifest candidate_panel.path is required")
    expected_panel_hash = _sha256_lock(
        panel_lock.get("sha256"), "candidate_panel.sha256"
    )
    panel_url = locked_artifact_url(manifest_url, panel_path)
    panel_bytes = read_url(panel_url)
    actual_panel_hash = "sha256:" + hashlib.sha256(panel_bytes).hexdigest()
    if actual_panel_hash != expected_panel_hash:
        raise ValueError(
            f"candidate panel sha256 mismatch: expected {expected_panel_hash}, "
            f"got {actual_panel_hash}"
        )
    panel = json.loads(panel_bytes.decode("utf-8"))
    if not isinstance(panel, dict):
        raise ValueError("candidate panel must be a JSON object")
    contract = validate_panel(panel)
    contract.update(
        {
            "campaign_id": manifest.get("campaign_id"),
            "campaign_manifest_hash": expected_manifest_hash,
            "candidate_panel_url": panel_url,
            "candidate_panel_sha256": expected_panel_hash,
        }
    )
    return manifest, panel, expected_manifest_hash, contract


def atoms_from_image(record: dict[str, Any]) -> Atoms:
    return Atoms(
        symbols=record["symbols"],
        positions=np.asarray(record["positions_angstrom"], dtype=float),
        cell=np.asarray(record["cell_angstrom"], dtype=float),
        pbc=record["pbc"],
    )


def run_barrier_path(
    path: dict[str, Any], calc: Any, protocol: dict[str, Any]
) -> dict[str, Any]:
    from ase.mep import NEB
    from ase.optimize import FIRE

    images = [atoms_from_image(record) for record in path["input_images"]]
    fmax = float(protocol["force_convergence_ev_per_angstrom"])
    maximum_steps = int(protocol["maximum_steps"])
    images[0].calc = calc
    endpoint_initial_converged = bool(
        FIRE(images[0], logfile=None).run(fmax=fmax, steps=maximum_steps)
    )
    images[-1].calc = calc
    endpoint_final_converged = bool(
        FIRE(images[-1], logfile=None).run(fmax=fmax, steps=maximum_steps)
    )
    if not endpoint_initial_converged or not endpoint_final_converged:
        raise RuntimeError("endpoint relaxation did not converge under the frozen protocol")
    for image in images:
        image.calc = calc
    neb = NEB(
        images,
        k=float(protocol["spring_constant_ev_per_angstrom2"]),
        climb=True,
        method="improvedtangent",
        allow_shared_calculator=True,
    )
    neb_converged = bool(
        FIRE(neb, logfile=None).run(fmax=fmax, steps=maximum_steps)
    )
    if not neb_converged:
        raise RuntimeError("CI-NEB did not converge under the frozen protocol")
    energies = [float(image.get_potential_energy()) for image in images]
    predicted_barrier = max(energies) - min(energies)
    reference_barrier = float(path["reference_barrier_ev"])
    signed_error_mev = (predicted_barrier - reference_barrier) * 1000.0
    return {
        "path_id": path["path_id"],
        "material_id": path.get("material_id"),
        "chemical_system": path.get("chemical_system"),
        "status": "completed",
        "reference_barrier_ev": reference_barrier,
        "predicted_barrier_ev": predicted_barrier,
        "signed_error_mev": signed_error_mev,
        "absolute_error_mev": abs(signed_error_mev),
        "predicted_image_energies_ev": energies,
        "endpoint_initial_converged": endpoint_initial_converged,
        "endpoint_final_converged": endpoint_final_converged,
        "neb_converged": neb_converged,
    }


def run_barrier_row(
    manifest: dict[str, Any],
    panel: dict[str, Any],
    calc: Any,
    fixture_contract: dict[str, Any],
    checkpoint: PredictionCheckpoint | None = None,
) -> dict[str, Any]:
    protocol = panel["execution_protocol"]
    predictions: list[dict[str, Any]] = []
    for case_index, path in enumerate(panel["paths"]):
        cached = (
            checkpoint.get_prediction(BARRIER_ROW_ID, case_index, path)
            if checkpoint
            else None
        )
        if cached is not None:
            predictions.append(cached)
            continue
        try:
            prediction = run_barrier_path(path, calc, protocol)
        except Exception as exc:
            prediction = {
                "path_id": path.get("path_id"),
                "material_id": path.get("material_id"),
                "chemical_system": path.get("chemical_system"),
                "status": "failed",
                "reference_barrier_ev": path.get("reference_barrier_ev"),
                "error_class": exc.__class__.__name__,
                "error": str(exc),
            }
        else:
            if checkpoint is not None:
                checkpoint.record_prediction(BARRIER_ROW_ID, case_index, path, prediction)
        predictions.append(prediction)
    completed = [
        prediction for prediction in predictions if prediction["status"] == "completed"
    ]
    failed_count = len(predictions) - len(completed)
    minimum_path_count = int(panel["measurement"]["minimum_path_count"])
    measurement_complete = len(completed) >= minimum_path_count and failed_count == 0
    mae_mev = (
        float(np.mean([prediction["absolute_error_mev"] for prediction in completed]))
        if completed
        else None
    )
    threshold_mev = float(manifest["acceptance_test"]["threshold"])
    score = (
        max(0.0, min(1.0, 1.0 - mae_mev / max(threshold_mev, 1e-12)))
        if measurement_complete and mae_mev is not None
        else 0.0
    )
    metrics = {
        "primary_metric": "barrier_mae_mev",
        "barrier_mae_mev": mae_mev,
        "completed_path_count": len(completed),
        "failed_path_count": failed_count,
        "minimum_path_count": minimum_path_count,
        "measurement_complete": measurement_complete,
        "acceptance_threshold_mev": threshold_mev,
    }
    return {
        "predictions": predictions,
        "score": score,
        "score_unit": "row_native_physical_score",
        "metrics": metrics,
        "row_spec": {
            "execution_protocol": protocol,
            "measurement": panel["measurement"],
        },
        "fixture_contract": fixture_contract,
        "n_structures": len(panel["paths"]),
    }
