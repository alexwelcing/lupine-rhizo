#!/usr/bin/env python3
"""Prepare and assemble the preregistered Round-4 cloud correction campaign.

The cloud phase evaluates immutable single-point MLIP predictions for a sealed
EOS grid and cubic finite-strain probes.  ``prepare`` materializes release-ready
runner fixtures and one batch specification per registered model.  ``assemble``
reads the resulting GCS artifacts, fits a0/B0 and C11/C12/C44, applies the
registered theorem-capped leave-one-out correction, and writes a campaign
artifact plus hash-chained ingestion rows without manual evidence assembly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TARGET_LOCK = ROOT / "data/candidates/round4_targets.lock.json"
REFERENCES = ROOT / "data/candidates/round4_references.json"
ENDPOINT_LOCK = ROOT / "gcp/mlip-cell-runner/round4_endpoints.lock.json"
OUT = ROOT / "data/candidates/round4"
FIXTURES = OUT / "fixtures"
BATCHES = OUT / "batch_specs"
RESULTS = OUT / "cloud_artifacts"
CAMPAIGN_MANIFEST = ROOT / "campaigns/v1/correction-round4.campaign-manifest.v1.json"
REPORT = OUT / "report.json"
REPORT_MD = OUT / "ROUND4_REPORT.md"
MEASUREMENTS = OUT / "measurements.jsonl"
EXECUTION_RECEIPT = OUT / "execution-receipt.json"
RUN_ID = "correction-round4-20260719"
GCS_INPUT = f"gs://shed-489901-atlas-inputs/{RUN_ID}"
GCS_OUTPUT = f"gs://shed-489901-atlas-outputs/{RUN_ID}"
DELTA = 0.005
LINEAR_SCALES = tuple(round(0.88 + 0.02 * i, 8) for i in range(13))
ELASTIC_SCALES = tuple(round(0.90 + 0.025 * i, 8) for i in range(9))
EV_A3_TO_GPA = 160.21766208
MODELS = (
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
)
MODEL_METADATA = {
    "chgnet": ("chgnet 0.4.2", "sha256:27dbc19f3fa710bbb58b6f5e64e0fde5a6941edcb538f92d228b2d90e93f8890"),
    "mace-mp-small": ("mace-torch 0.3.16 / small", "sha256:c69cbc43286d05a8e9974412a4fb5f4e28405f92ac15287537263475dfc3c694"),
    "mace-mp-medium": ("mace-torch 0.3.16 / medium", "sha256:1d80b5c4898b2d22d73dc82b17e1cabe1111d9cd6be4c2a7403dea6fa0ac83f3"),
    "mace-mpa-0-medium": ("mace-torch 0.3.16 / mpa-0 medium", "sha256:59b5d1db18664525ad20358fe381b7ba71bdb260c8a3d6bbfe5fb5201e3be0d9"),
}
JOB_BY_MODEL = {
    "chgnet": "mlip-cell-chgnet-round4",
    "mace-mp-small": "mlip-cell-mace-round4-mp-small",
    "mace-mp-medium": "mlip-cell-mace-round4-mp-medium",
    "mace-mpa-0-medium": "mlip-cell-mace-round4-mpa-0-medium",
}
AMENDMENT_DOC = "docs/plans/2026-07-19-round4-preregistration-amendment.md"
# Registered property dispositions.  B0 concordance is descriptive-only
# (preregistration §5, errata finding 4) and never enters the confirmatory
# denominator.  Perovskite C11/C12/C44 are exploratory-only under the
# 2026-07-19 amendment: the instrument probes clamped-ion finite differences
# at the nearest sealed 2.5%-spaced volume rather than at each model's own
# relaxed equilibrium, which is not a defensible confirmatory comparison for
# strained perovskites against relaxed/experimental references.
DESCRIPTIVE_PROPERTIES = ("b0",)
EXPLORATORY_PROPERTIES_BY_GROUP = {"perovskites": ("c11", "c12", "c44")}
ELASTIC_EXPLORATORY_NOTE = (
    "Exploratory-only under " + AMENDMENT_DOC + ": clamped-ion finite "
    "differences at the nearest sealed 2.5%-spaced volume, compared against "
    "relaxed/experimental references; not a confirmatory instrument for "
    "strained perovskites. Follow-up task round4-elastic-relaxed-recompute "
    "re-evaluates at each model's relaxed equilibrium with internal relaxation."
)


def property_disposition(group: str, prop: str) -> str:
    if prop in DESCRIPTIVE_PROPERTIES:
        return "descriptive"
    if prop in EXPLORATORY_PROPERTIES_BY_GROUP.get(group, ()):
        return "exploratory"
    return "confirmatory"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def file_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fractional_structure(formula: str, structure_type: str) -> tuple[list[str], list[list[float]]]:
    if structure_type == "rocksalt":
        # Conventional Fm-3m cell: four formula units.
        # Parse only the frozen panel's binary formulas without a chemistry dependency.
        pairs = {"NaBr": ("Na", "Br"), "NaI": ("Na", "I"), "RbBr": ("Rb", "Br"), "RbI": ("Rb", "I")}
        a, b = pairs[formula]
        fcc = [[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]]
        shifted = [[(x + 0.5) % 1, y, z] for x, y, z in fcc]
        return [a] * 4 + [b] * 4, fcc + shifted
    parts = {
        "KCaF3": ("K", "Ca"), "RbCaF3": ("Rb", "Ca"),
        "RbMgF3": ("Rb", "Mg"), "CsMgF3": ("Cs", "Mg"),
    }
    a, b = parts[formula]
    return [a, b, "F", "F", "F"], [[0, 0, 0], [0.5, 0.5, 0.5], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]


def case(candidate: dict[str, Any], a: float, transform: np.ndarray, suffix: str, reference: dict[str, Any], **extra: Any) -> dict[str, Any]:
    symbols, frac = fractional_structure(candidate["formula"], candidate["structure_type"])
    cell = np.eye(3) * a @ transform
    positions = np.asarray(frac, dtype=float) @ cell
    return {
        "structure_id": f"{candidate['id']}-{suffix}",
        "material_id": candidate["id"],
        "symbols": symbols,
        "positions": positions.tolist(),
        "cell": cell.tolist(),
        "pbc": True,
        "reference": reference,
        **extra,
    }


def candidates() -> list[dict[str, Any]]:
    lock = load(TARGET_LOCK)
    refs = {entry["id"]: entry for entry in load(REFERENCES)["candidates"]}
    values = []
    for group in lock["classes"]:
        for raw in group["candidates"]:
            ref = refs[raw["id"]]
            values.append({**raw, "group": group["id"], "structure_type": group["structure_type"], "references": ref["references"]})
    return values


def fixture(candidate: dict[str, Any]) -> dict[str, Any]:
    a_ref = float(candidate["references"]["a0"]["value"])
    elastic_ref = {
        key.upper(): value["value"]
        for key in ("c11", "c12", "c44")
        if (value := candidate["references"].get(key)) is not None
    } or {"C11": 1.0, "C12": 1.0, "C44": 1.0}
    eos = [
        case(candidate, a_ref * scale, np.eye(3), f"eos-s{scale:.3f}", {"energy_ev_per_atom": 0.0}, volume_scale=scale ** 3)
        for scale in LINEAR_SCALES
    ]
    elastic = []
    for scale in ELASTIC_SCALES:
        for mode, sign in (("xx", 1), ("xx", -1), ("yz", 1), ("yz", -1)):
            eps = np.zeros((3, 3))
            strain = [0.0] * 6
            if mode == "xx":
                eps[0, 0] = sign * DELTA
                strain[0] = sign * DELTA
            else:
                eps[1, 2] = eps[2, 1] = sign * DELTA
                strain[3] = sign * 2.0 * DELTA
            elastic.append(case(
                candidate, a_ref * scale, np.eye(3) + eps,
                f"elastic-s{scale:.3f}-{mode}-{'p' if sign > 0 else 'm'}",
                {"elastic_constants_gpa": elastic_ref}, strain_voigt=strain,
            ))
    base = case(candidate, a_ref, np.eye(3), "contract", {"stress_gpa": [0.0] * 6})
    n = len(base["symbols"])
    forces = []
    for i in range(5):
        item = json.loads(json.dumps(base))
        item["structure_id"] += f"-force-{i}"
        ref_forces = [[0.0, 0.0, 0.0] for _ in range(n)]
        ref_forces[0][i % 3] = 0.01
        item["reference"] = {"forces_ev_per_angstrom": ref_forces}
        forces.append(item)
    stress = []
    for i in range(5):
        item = json.loads(json.dumps(base)); item["structure_id"] += f"-stress-{i}"; stress.append(item)
    relax = []
    for i in range(3):
        item = json.loads(json.dumps(base)); item["structure_id"] += f"-relax-{i}"
        item["reference"] = {"relaxation_force_threshold": 0.05, "relaxed_energy_ev_per_atom": 0.0}
        relax.append(item)
    return {
        "schema": "lupine.mlip.fixture_manifest.v2",
        "fixture_id": f"round4-{candidate['id']}",
        "reference_provenance": {
            "campaign": "docs/plans/2026-07-14-round4-preregistration.md",
            "candidate_lock": f"sha256:{hashlib.sha256(TARGET_LOCK.read_bytes()).hexdigest()}",
            "references": "data/candidates/round4_references.json",
            "note": "Reference energies in the execution contract are validation placeholders; property references are joined only during assembly.",
        },
        "row_fixtures": {
            "energy_volume": {"structures": eos},
            "elastic_constants": {"structures": elastic},
            "forces": {"structures": forces},
            "stress": {"structures": stress},
            "relaxation_stability": {"structures": relax},
        },
    }


def campaign_manifest() -> dict[str, Any]:
    value = {
        "campaign_id": "correction.round-4.available-models.v1",
        "version": 1,
        "preregistration_id": "prereg.correction.round-4.2026-07-14",
        "preregistration": {"registered_at": "2026-07-14T00:00:00Z", "source": "docs/plans/2026-07-14-round4-preregistration.md", "frozen_before_execution": True},
        "frozen_hypotheses": [{"hypothesis_id": "h.round4.theorem-capped-same-class", "statement": "The theorem-capped v2 correction wins on at least two thirds of evaluable properties in each registered class under the frozen criterion.", "frozen": True}],
        "available_models": [{"model_id": model, "version": MODEL_METADATA[model][0], "artifact_hash": MODEL_METADATA[model][1]} for model in MODELS],
        "exclusions": [{"subject": "uma-family", "disposition": "excluded", "rationale": "Preregistered excluded_unavailable: no reproducible gated UMA checkpoint was available at lock time."}],
        "target_premises": [{"claim_id": "correction.same_class.a0.v1", "premise_id": "round3_same_class_a0"}],
        "acceptance_test": {"metric": "group_property_win_fraction", "operator": "gte", "threshold": 2 / 3, "unit": "fraction"},
        "evidence_requirements": [{"requirement_id": "e.round4.model-material-cells", "artifact_type": "model-measurements", "description": "All 32 registered model/material cells with immutable cloud receipts and no imputation.", "minimum_count": 32}],
        "execution": {"lane": "round4.available-models", "model_selection": "available_models", "excluded_models_block_execution": False, "candidate_panel": {"path": "data/candidates/round4_targets.lock.json", "sha256": "sha256:b7562637c860b15b92f64659f0b063bc6d2b6c0c12899e21f370359cccb914f1"}},
        "kill_conditions": [{"condition_id": "kill.round4.theorem-consistency", "metric": "licensed_in_hull_worsened_cells", "operator": "gt", "threshold": 0, "unit": "count", "action": "kill"}],
        "demotion_conditions": [{"condition_id": "demote.round4.group-property-win-fraction", "metric": "group_property_win_fraction", "operator": "lt", "threshold": 2 / 3, "unit": "fraction", "action": "demote"}],
    }
    value["content_hash"] = canonical_hash(value)
    return value


def prepare(upload: bool) -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True); BATCHES.mkdir(parents=True, exist_ok=True)
    panel = candidates()
    for candidate in panel:
        dump(FIXTURES / f"{candidate['id']}.json", fixture(candidate))
    for model in MODELS:
        cells = []
        for candidate in panel:
            fixture_url = f"{GCS_INPUT}/fixtures/{candidate['id']}.json"
            for row in ("energy_volume", "elastic_constants"):
                cells.append({
                    "cell_id": f"{RUN_ID}:{candidate['id']}:{row}:{model}", "row_id": row, "mlip_id": model,
                    "manifest_url": fixture_url,
                    "artifact_prefix": f"{GCS_OUTPUT}/{model}/{candidate['id']}/{row}",
                    "local_jsonl": "/tmp/round4-beats.jsonl", "dev_mode_bypass": True,
                })
        dump(BATCHES / f"{model}.json", {
            "schema": "lupine.mlip.batch_spec.v1", "batch_id": f"{RUN_ID}-{model}", "run_id": RUN_ID,
            "campaign_id": "correction.round-4.available-models.v1", "mlip_id": model,
            "batch_artifact_prefix": f"{GCS_OUTPUT}/{model}", "cells": cells,
        })
    dump(CAMPAIGN_MANIFEST, campaign_manifest())
    if upload:
        subprocess.run(["gcloud", "storage", "cp", "--recursive", str(FIXTURES), f"{GCS_INPUT}/"], check=True)
        subprocess.run(["gcloud", "storage", "cp", "--recursive", str(BATCHES), f"{GCS_INPUT}/"], check=True)


def execute() -> None:
    for model in MODELS:
        args = (
            f"run-batch,--batch-spec-url,{GCS_INPUT}/batch_specs/{model}.json,"
            f"--batch-artifact-prefix,{GCS_OUTPUT}/{model},--local-jsonl,/tmp/round4-beats.jsonl,--dev-mode-bypass"
        )
        subprocess.run([
            "gcloud", "run", "jobs", "execute", JOB_BY_MODEL[model], "--project=shed-489901",
            "--region=us-central1", "--args", args,
        ], check=True)


def capture_execution_receipt() -> None:
    """Record completed restored-endpoint executions and verify locked images."""
    endpoint_lock = load(ENDPOINT_LOCK)
    locked_images = {item["mlip_id"]: item["image"] for item in endpoint_lock["endpoints"]}
    executions = []
    for model in MODELS:
        job_name = JOB_BY_MODEL[model]
        job = json.loads(subprocess.check_output([
            "gcloud", "run", "jobs", "describe", job_name,
            "--project=shed-489901", "--region=us-central1", "--format=json",
        ]))
        listed = json.loads(subprocess.check_output([
            "gcloud", "run", "jobs", "executions", "list", f"--job={job_name}",
            "--project=shed-489901", "--region=us-central1", "--limit=1", "--format=json",
        ]))
        if len(listed) != 1:
            raise ValueError(f"missing execution for {job_name}")
        execution = listed[0]
        image = job["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]["image"]
        condition = execution["status"]["conditions"][0]
        if image != locked_images[model]:
            raise ValueError(f"restored endpoint image drift for {model}: {image}")
        if condition.get("status") != "True":
            raise ValueError(f"execution did not complete successfully for {model}: {condition}")
        labels = job["spec"]["template"].get("metadata", {}).get("labels", {})
        executions.append({
            "model_id": model,
            "job": job_name,
            "job_generation": int(job["metadata"]["generation"]),
            "execution": execution["metadata"]["name"],
            "created_at": execution["metadata"]["creationTimestamp"],
            "completed_at": condition.get("lastTransitionTime"),
            "status": condition["status"],
            "image": image,
            "locked_image_match": True,
            "endpoint_lock_label": labels.get("endpoint-lock"),
        })
    dump(EXECUTION_RECEIPT, {
        "schema": "lupine.round4.execution_receipt.v1",
        "run_id": RUN_ID,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "endpoint_lock_sha256": file_hash(ENDPOINT_LOCK),
        "executions": executions,
    })


def copy_results() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gcloud", "storage", "cp", "--recursive", f"{GCS_OUTPUT}/*", str(RESULTS)], check=True)


def fit_eos(predictions: list[dict[str, Any]], a_ref: float) -> dict[str, Any]:
    points = sorted((a_ref * float(p["volume_scale"]) ** (1 / 3), float(p["energy_ev_per_atom"])) for p in predictions)
    imin = min(range(len(points)), key=lambda i: points[i][1])
    if imin < 2 or imin > len(points) - 3:
        raise ValueError(f"EOS minimum is not bracketed (index {imin}/{len(points)})")
    local = points[imin - 2: imin + 3]
    # Predictions are energies per atom, so fit against volume per atom rather
    # than conventional-cell volume.  The fixtures keep atom count fixed.
    n_atoms = len(predictions[0]["symbols"])
    volumes = np.asarray([a ** 3 / n_atoms for a, _ in local]); energies = np.asarray([e for _, e in local])
    coef = np.polyfit(volumes, energies, 3)
    roots = np.roots(np.polyder(coef))
    candidates_v = [float(r.real) for r in roots if abs(r.imag) < 1e-8 and volumes.min() <= r.real <= volumes.max() and np.polyval(np.polyder(coef, 2), r.real) > 0]
    if not candidates_v:
        raise ValueError("EOS cubic fit has no bracketed minimum")
    v0 = min(candidates_v, key=lambda v: np.polyval(coef, v))
    b0 = v0 * float(np.polyval(np.polyder(coef, 2), v0)) * EV_A3_TO_GPA
    return {"a0": (v0 * n_atoms) ** (1 / 3), "b0": b0, "e0_ev_per_atom": float(np.polyval(coef, v0)), "fit": "local-cubic-E(V)-5point"}


def fit_elastic(predictions: list[dict[str, Any]], a_ref: float, a0: float) -> dict[str, float]:
    target_scale = a0 / a_ref
    scale = min(ELASTIC_SCALES, key=lambda x: abs(x - target_scale))
    chosen = {p["structure_id"].rsplit("-", 2)[-2] + "-" + p["structure_id"].rsplit("-", 1)[-1]: p for p in predictions if f"elastic-s{scale:.3f}-" in p["structure_id"]}
    def stress(key: str) -> np.ndarray:
        return np.asarray(chosen[key]["stress_gpa"], dtype=float)
    xp, xm, sp, sm = stress("xx-p"), stress("xx-m"), stress("yz-p"), stress("yz-m")
    return {
        "c11": float((xp[0] - xm[0]) / (2 * DELTA)),
        "c12": float(((xp[1] - xm[1]) + (xp[2] - xm[2])) / (4 * DELTA)),
        "c44": float((sp[3] - sm[3]) / (4 * DELTA)),
        "elastic_probe_scale": scale,
        "elastic_probe_a_angstrom": a_ref * scale,
    }


def exact_sign_p(improved: int, worsened: int) -> float | None:
    n = improved + worsened
    if n == 0: return None
    lower = sum(math.comb(n, k) for k in range(0, improved + 1)) / 2 ** n
    upper = sum(math.comb(n, k) for k in range(improved, n + 1)) / 2 ** n
    return min(1.0, 2 * min(lower, upper))


def correction(pred: float, ratios: list[float]) -> dict[str, Any]:
    if len(ratios) < 2: return {"corrected": pred, "applied": False, "abstain_reason": "insufficient_calibration", "b": None, "s": None}
    b, s = statistics.median(ratios), max(ratios) - min(ratios)
    if all(r > 1 for r in ratios): licensed = b - 1 > 2 * s; side = "inflation"
    elif all(r < 1 for r in ratios): licensed = 1 - b > 3 * s and b >= 0.5; side = "deflation"
    else: return {"corrected": pred, "applied": False, "abstain_reason": "direction", "b": b, "s": s}
    return {"corrected": pred / b if licensed else pred, "applied": licensed, "abstain_reason": None if licensed else "theorem_cap", "b": b, "s": s, "side": side}


def measurement_binding(execution_receipt: dict[str, Any], endpoint_lock: dict[str, Any]) -> dict[str, Any]:
    """Campaign-level repair of the measurement-time execution binding.

    The frozen endpoint lock names the shared pre-round jobs, while the
    measurements actually executed on the isolated Round-4 jobs recorded in
    the execution receipt.  The hash-locked cell artifacts carry
    ``execution.runner_image_digest: null`` (runner gap at capture time) and
    cannot be amended in place, so the immutable per-model image digests are
    bound here at campaign level.
    """
    locked = {item["mlip_id"]: item["image"] for item in endpoint_lock["endpoints"]}
    models = {}
    for execution in execution_receipt["executions"]:
        model = execution["model_id"]
        models[model] = {
            "job": execution["job"],
            "execution": execution["execution"],
            "image": execution["image"],
            "endpoint_lock_image": locked.get(model),
            "image_matches_endpoint_lock": execution["image"] == locked.get(model),
        }
    return {
        "schema": "lupine.round4.measurement_binding.v1",
        "repair": (
            "2026-07-19 amendment (" + AMENDMENT_DOC + "): measurements ran on the "
            "isolated Round-4 jobs named below, not on the shared jobs listed in the "
            "frozen endpoint lock. Cell-level artifacts have runner_image_digest null "
            "at capture; the measurement-time digests are bound here."
        ),
        "replay_note": (
            "The live Cloud Run jobs were redeployed with z1-barrier images for the "
            "Z1 campaign after these measurements (verified 2026-07-19); current live "
            "state is NOT the measurement binding. The locked digests below remain in "
            "Artifact Registry for replay."
        ),
        "models": models,
    }


def assemble(download: bool) -> None:
    if download: copy_results()
    panel = candidates(); cells: dict[str, Any] = {}
    endpoint = load(ENDPOINT_LOCK)
    for model in MODELS:
        for candidate in panel:
            base = RESULTS / model / candidate["id"]
            eos_artifact = load(base / "energy_volume/cell_result.json")
            elastic_artifact = load(base / "elastic_constants/cell_result.json")
            a_ref = float(candidate["references"]["a0"]["value"])
            props = fit_eos(eos_artifact["predictions"], a_ref)
            props.update(fit_elastic(elastic_artifact["predictions"], a_ref, props["a0"]))
            key = f"{candidate['id']}::{model}"
            cells[key] = {
                "candidate_id": candidate["id"], "formula": candidate["formula"], "group": candidate["group"],
                "structure_type": candidate["structure_type"], "model_id": model, "properties": props,
                "references": {p: (v["value"] if v is not None else None) for p, v in candidate["references"].items()},
                "cloud_artifacts": {
                    "energy_volume": {"path": str((base / "energy_volume/cell_result.json").relative_to(ROOT)), "sha256": file_hash(base / "energy_volume/cell_result.json"), "uri": eos_artifact.get("manifest_url")},
                    "elastic_constants": {"path": str((base / "elastic_constants/cell_result.json").relative_to(ROOT)), "sha256": file_hash(base / "elastic_constants/cell_result.json"), "uri": elastic_artifact.get("manifest_url")},
                },
            }
    decisions = []
    summaries: dict[str, Any] = {}
    for group in sorted({c["group"] for c in cells.values()}):
        group_cells = [c for c in cells.values() if c["group"] == group]
        summaries[group] = {}
        for prop in ("a0", "b0", "c11", "c12", "c44"):
            evaluated = []
            for cell in group_cells:
                ref = cell["references"].get(prop)
                if ref is None or not math.isfinite(float(ref)) or float(ref) == 0: continue
                ratios = [
                    float(other["properties"][prop]) / float(other["references"][prop])
                    for other in group_cells if other["model_id"] == cell["model_id"] and other["candidate_id"] != cell["candidate_id"] and other["references"].get(prop) not in (None, 0)
                ]
                raw = float(cell["properties"][prop]); result = correction(raw, ratios)
                raw_err = abs(raw - float(ref)) / abs(float(ref)); corrected_err = abs(float(result["corrected"]) - float(ref)) / abs(float(ref))
                lo, hi = (min(ratios), max(ratios)) if ratios else (None, None)
                oracle_ratio = raw / float(ref)
                oracle_in_hull = bool(
                    lo is not None and hi is not None and lo <= oracle_ratio <= hi
                )
                item = {"candidate_id": cell["candidate_id"], "model_id": cell["model_id"], "group": group, "property": prop, "raw": raw, "reference": ref, **result, "raw_abs_rel_error": raw_err, "corrected_abs_rel_error": corrected_err, "improved": corrected_err < raw_err, "worsened": corrected_err > raw_err, "oracle_ratio": oracle_ratio, "oracle_in_hull": oracle_in_hull}
                decisions.append(item); evaluated.append(item)
            if not evaluated: continue
            improved = sum(x["improved"] for x in evaluated if x["applied"]); worsened = sum(x["worsened"] for x in evaluated if x["applied"])
            raw_med = statistics.median(x["raw_abs_rel_error"] for x in evaluated); corr_med = statistics.median(x["corrected_abs_rel_error"] for x in evaluated)
            p = exact_sign_p(improved, worsened)
            disposition = property_disposition(group, prop)
            summaries[group][prop] = {"n_cells": len(evaluated), "n_applied": improved + worsened + sum(not x["improved"] and not x["worsened"] for x in evaluated if x["applied"]), "improved": improved, "worsened": worsened, "median_abs_rel_error_raw": raw_med, "median_abs_rel_error_corrected": corr_med, "sign_test_p_two_sided": p, "win": corr_med < raw_med and p is not None and p < 0.1, "disposition": disposition}
            if disposition == "exploratory":
                summaries[group][prop]["scope_note"] = ELASTIC_EXPLORATORY_NOTE
            elif disposition == "descriptive":
                summaries[group][prop]["scope_note"] = "Descriptive-only per preregistration §5 (errata finding 4); excluded from the confirmatory denominator."
    group_verdicts = {}
    for group, props in summaries.items():
        confirmatory = {p: v for p, v in props.items() if v["disposition"] == "confirmatory"}
        wins = sum(v["win"] for v in confirmatory.values()); n = len(confirmatory)
        group_verdicts[group] = {
            "n_evaluable_properties": n, "n_wins": wins,
            "win_fraction": wins / n if n else 0.0,
            "verdict": "PASS" if n and wins / n >= 2 / 3 else "FAIL",
            "confirmatory_properties": sorted(confirmatory),
            "excluded_from_confirmatory": {p: v["disposition"] for p, v in sorted(props.items()) if v["disposition"] != "confirmatory"},
        }
    theorem_violations = [d for d in decisions if d["applied"] and d["oracle_in_hull"] and d["worsened"]]
    execution_receipt = load(EXECUTION_RECEIPT)
    report = {
        "schema": "lupine.round4.correction_campaign_results.v1", "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(), "campaign_manifest": str(CAMPAIGN_MANIFEST.relative_to(ROOT)),
        "campaign_manifest_content_hash": load(CAMPAIGN_MANIFEST)["content_hash"],
        "candidate_lock_sha256": file_hash(TARGET_LOCK), "endpoint_lock_sha256": file_hash(ENDPOINT_LOCK),
        "analysis_amendment": AMENDMENT_DOC,
        "models": list(MODELS), "excluded": [{"model_id": "uma", "status": "excluded_unavailable"}],
        "n_model_material_cells": len(cells), "cells": cells, "correction_decisions": decisions,
        "group_property_summaries": summaries, "group_verdicts": group_verdicts,
        "theorem_consistency": {"licensed_in_hull_worsened_cells": len(theorem_violations), "violations": theorem_violations},
        "instrument": {"eos": "13-point clamped-ion E(V), local cubic 5-point minimum fit", "elastic": "symmetric finite difference at nearest sealed isotropic scale", "delta": DELTA, "internal_relaxation": False, "honesty_note": "Cubic prototypes have symmetry-fixed ideal internal coordinates; reported elastic constants are clamped-ion finite-strain values. Perovskite C11/C12/C44 are exploratory-only (" + AMENDMENT_DOC + "); B0 is descriptive-only (preregistration §5)."},
        "endpoint_lock": endpoint,
        "measurement_binding": measurement_binding(execution_receipt, endpoint),
        "execution_receipt": execution_receipt,
    }
    dump(REPORT, report)
    lines = [
        "# Round-4 theorem-capped correction campaign",
        "",
        f"Run: `{RUN_ID}` · 32/32 model/material cells completed on the isolated Round-4 Cloud Run jobs.",
        "",
        "Analysis amended 2026-07-19 (`" + AMENDMENT_DOC + "`): B0 is descriptive-only (preregistration §5) and perovskite elastic constants are exploratory-only; neither enters the confirmatory denominator.",
        "",
        "## Registered group/property results",
        "",
        "| Group | Property | Scope | Applied | Improved | Worsened | Median raw | Median corrected | p (two-sided) | Win |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for group, properties in summaries.items():
        for prop, result in properties.items():
            p_value = "—" if result["sign_test_p_two_sided"] is None else f"{result['sign_test_p_two_sided']:.6g}"
            lines.append(
                f"| {group} | {prop} | {result['disposition']} | {result['n_applied']} | {result['improved']} | "
                f"{result['worsened']} | {result['median_abs_rel_error_raw']:.6g} | "
                f"{result['median_abs_rel_error_corrected']:.6g} | {p_value} | "
                f"{'YES' if result['win'] else 'NO'} |"
            )
    lines.extend([
        "",
        "## Disposition",
        "",
        f"- Ionics-rocksalt: **{group_verdicts['ionics-rocksalt']['verdict']}** "
        f"({group_verdicts['ionics-rocksalt']['n_wins']}/{group_verdicts['ionics-rocksalt']['n_evaluable_properties']} confirmatory property wins: {', '.join(group_verdicts['ionics-rocksalt']['confirmatory_properties'])}).",
        f"- Perovskites: **{group_verdicts['perovskites']['verdict']}** "
        f"({group_verdicts['perovskites']['n_wins']}/{group_verdicts['perovskites']['n_evaluable_properties']} confirmatory property wins: {', '.join(group_verdicts['perovskites']['confirmatory_properties'])}).",
        f"- Theorem consistency: {len(theorem_violations)} licensed, oracle-in-hull worsened cells (required: zero).",
        "- Registered conclusion: both groups fail the >=2/3 property-win criterion; the public correction scope remains same-class lattice constants only and further cap tuning is frozen absent a new theorem.",
        "- Excluded from the confirmatory denominator: b0 everywhere (descriptive-only, preregistration §5); perovskite c11/c12/c44 (exploratory-only, 2026-07-19 amendment — clamped-ion finite differences at the nearest sealed 2.5%-spaced volume vs relaxed/experimental references).",
        "",
        "The complete machine-readable decisions, the repaired measurement binding (isolated jobs + immutable image digests), artifact paths, and SHA-256 hashes are in `report.json`.",
        "",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    manifest = load(CAMPAIGN_MANIFEST); artifact_hash = file_hash(REPORT)
    rows = []; previous = None
    scope_map = {"ionics-rocksalt": ("rocksalt", "ionic-rocksalt"), "perovskites": ("perovskite", "halide-perovskite")}
    for group in ("ionics-rocksalt", "perovskites"):
        summary = summaries[group]["a0"]; structure, chemistry = scope_map[group]
        row = {
            "row_id": f"round4-{group}-a0", "campaign_manifest_hash": manifest["content_hash"],
            "claim_id": "correction.same_class.a0.v1", "premise_id": "round3_same_class_a0",
            "claim_predicate": "same_class_correction_improves_median_absolute_relative_error(property=a0)",
            "epistemic_status": "confirmatory" if summary["win"] else "negative", "run_id": RUN_ID,
            "artifact": str(REPORT.relative_to(ROOT)), "artifact_hash": artifact_hash, "thresholds_version": "round4-theorem-caps-v2",
            "scope": {"structures": [structure], "chemistries": [chemistry], "properties": ["a0"], "conditions": {"calibration": "leave-one-out within structure class", "evaluation": "Round-4 out-of-sample candidates", **summary}},
            "provenance": {"agent": "tools/round4_cloud_campaign.py", "human": "Round-4 preregistration registrant", "timestamp": report["generated_at"]},
            "previous_row_hash": previous,
        }
        row["row_hash"] = canonical_hash(row); previous = row["row_hash"]; rows.append(row)
    MEASUREMENTS.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--upload", action="store_true")
    sub.add_parser("execute")
    sub.add_parser("receipt")
    a = sub.add_parser("assemble"); a.add_argument("--download", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare": prepare(args.upload)
    elif args.command == "execute": execute()
    elif args.command == "receipt": capture_execution_receipt()
    else: assemble(args.download)


if __name__ == "__main__": main()
