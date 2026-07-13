"""Five-architecture cross-model dispersion merge (packet 2026-07-13 §3.7.5).

Merges the local Round-1 candidate statics report (chgnet, mace-mp-medium,
mace-mpa-0-medium raw per_model values) with the three cloud cell artifacts
(sevennet, orb-v3, uma-s-1p1) and recomputes per-candidate per-property
cross-model relative dispersion (max - min) / |median| — the same statistic
as lupine_distill.statics.gates.relative_dispersion — on two bases:

  local3 : {chgnet, mace-mp-medium, mace-mpa-0-medium}   (3 models, 2 archs)
  arch5  : local3 + {sevennet, orb-v3, uma-s-1p1}        (6 models, 5 archs)

DECLARED PROTOCOL DEVIATION (packet §3.1): the cloud elastic_constants row
strains a FIXED builder-supplied lattice (reference/guess a0), while the
local campaign computes relaxed-ion Cij on each model's own relaxed cell.
Every elastic property row is therefore labeled protocol_mismatch and the
comparison is wiring/coarse-dispersion grade, not claim-grade (GAP-1).

a0/B0 have no cloud counterpart (GAP-1: no candidate_statics row) and are
excluded. relaxation_stability has no local counterpart in round1/report.json
and is reported as a cloud-only descriptive block.

Usage: python compute_five_arch_dispersions.py  (run from this directory)
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
LOCAL_REPORT = HERE.parent / "round1" / "report.json"
OUT_JSON = HERE / "five_arch_dispersions.json"

LOCAL_MODELS = ("chgnet", "mace-mp-medium", "mace-mpa-0-medium")
CLOUD_MODELS = ("sevennet", "orb-v3", "uma-s-1p1")
ELASTIC_PROPS = ("c11", "c12", "c44")
RUN_ID = "mlip-cloud-20260713-cand-r1"


def fail(msg: str) -> None:
    raise SystemExit(f"ERROR: {msg}")


def load_json(path: pathlib.Path) -> dict:
    if not path.is_file():
        fail(f"missing input {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def relative_dispersion(values: list[float]) -> float:
    if len(values) < 2:
        fail(f"need >= 2 values, got {len(values)}")
    med = statistics.median(values)
    if abs(med) < 1e-8:
        fail(f"median {med} too small for relative dispersion")
    return (max(values) - min(values)) / abs(med)


def cubic_from_matrix(matrix: list[list[float]]) -> dict[str, float]:
    """Cubic (c11, c12, c44) via symmetry-averaging the 6x6 Voigt matrix."""
    if len(matrix) != 6 or any(len(row) != 6 for row in matrix):
        fail("expected a 6x6 Voigt matrix")
    c11 = statistics.mean(matrix[i][i] for i in range(3))
    c12 = statistics.mean(
        matrix[i][j] for i in range(3) for j in range(3) if i != j
    )
    c44 = statistics.mean(matrix[i][i] for i in range(3, 6))
    return {"c11": c11, "c12": c12, "c44": c44}


def main() -> int:
    local = load_json(LOCAL_REPORT)
    candidates = local["candidates"]

    cloud_elastic: dict[str, dict[str, dict[str, float]]] = {}  # model -> material -> prop
    cloud_meta: dict[str, dict] = {}
    for model in CLOUD_MODELS:
        art_path = HERE / "baseline" / "elastic_constants" / model / "cell_result.json"
        art = load_json(art_path)
        if art.get("run_id") != RUN_ID:
            fail(f"{art_path} run_id {art.get('run_id')!r} != {RUN_ID!r}")
        by_mat = art["accuracy"]["elastic_constants_gpa_by_material"]
        cloud_elastic[model] = {
            material: cubic_from_matrix(matrix) for material, matrix in by_mat.items()
        }
        cloud_meta[model] = {
            "manifest_hash": art.get("manifest_hash"),
            "cell_id": art.get("cell_id"),
            "accuracy_score": art.get("accuracy", {}).get("score"),
            "gpa_mae": art.get("accuracy", {}).get("error"),
        }

    hashes = {meta["manifest_hash"] for meta in cloud_meta.values()}
    if len(hashes) != 1:
        fail(f"manifest_hash differs across cloud cells: {hashes}")

    elastic_materials = sorted(
        set.intersection(*(set(cloud_elastic[m]) for m in CLOUD_MODELS))
    )

    rows: list[dict] = []
    for material in elastic_materials:
        if material not in candidates:
            fail(f"cloud material {material!r} not in local report")
        per_model_local = candidates[material]["per_model"]
        for prop in ELASTIC_PROPS:
            values: dict[str, float] = {}
            for model in LOCAL_MODELS:
                entry = per_model_local.get(model, {}).get("properties", {})
                if prop not in entry or entry[prop] is None:
                    fail(f"local {material}/{model}/{prop} missing")
                values[model] = float(entry[prop])
            for model in CLOUD_MODELS:
                values[model] = float(cloud_elastic[model][material][prop])
            local3 = [values[m] for m in LOCAL_MODELS]
            arch5 = list(values.values())
            rows.append(
                {
                    "material": material,
                    "property": prop,
                    "unit": "GPa",
                    "values_gpa": values,
                    "reference_gpa": candidates[material]["references"].get(prop),
                    "dispersion_local3": relative_dispersion(local3),
                    "dispersion_arch5": relative_dispersion(arch5),
                    "ratio_arch5_over_local3": (
                        relative_dispersion(arch5) / relative_dispersion(local3)
                    ),
                    "protocol_mismatch": (
                        "local=relaxed_cell_relaxed_ion; cloud=fixed_lattice "
                        "(declared deviation, packet §3.1 — not claim-grade)"
                    ),
                    "headline_excluded": material == "hp-cssni3",
                }
            )

    # Cloud-only relaxation_stability block (no local counterpart in report.json)
    relaxation: dict[str, dict] = {}
    for model in CLOUD_MODELS:
        art_path = HERE / "baseline" / "relaxation_stability" / model / "cell_result.json"
        if not art_path.is_file():
            relaxation[model] = {"status": "artifact_missing"}
            continue
        art = load_json(art_path)
        acc = art.get("accuracy", {})
        relaxation[model] = {
            "score": acc.get("score"),
            "unit": acc.get("unit"),
            "relaxation_penalty": acc.get("error"),
            "error_unit": acc.get("error_unit"),
            "convergence_rate": acc.get("convergence_rate"),
        }

    n_understated = sum(1 for row in rows if row["ratio_arch5_over_local3"] > 1.0)
    payload = {
        "schema": "lupine.mlip.five_arch_dispersions.v1",
        "run_id": RUN_ID,
        "generated_by": "data/candidates/round1_cloud/compute_five_arch_dispersions.py",
        "dispersion_metric": "(max - min) / |median| (gates.relative_dispersion)",
        "bases": {
            "local3": {"models": list(LOCAL_MODELS), "architectures": ["CHGNet", "MACE", "MACE"]},
            "arch5": {
                "models": list(LOCAL_MODELS) + list(CLOUD_MODELS),
                "architectures": ["CHGNet", "MACE", "MACE", "SevenNet", "ORB", "UMA"],
            },
        },
        "protocol_deviation": {
            "elastic_constants": (
                "cloud cells computed on a fixed builder-supplied lattice "
                "(reference/guess a0); local values are relaxed-ion Cij on each "
                "model's own relaxed cell. Declared in packet §3.1; fixed-lattice "
                "cells stay out of headline claims until candidate_statics (GAP-1)."
            ),
            "a0_b0": "no cloud counterpart (GAP-1) — excluded",
            "relaxation_stability": "no local counterpart in round1/report.json — cloud-only descriptive",
        },
        "cloud_cell_meta": cloud_meta,
        "manifest_hash": next(iter(hashes)),
        "elastic_dispersions": rows,
        "relaxation_stability_cloud_only": relaxation,
        "summary": {
            "n_rows": len(rows),
            "n_rows_arch5_exceeds_local3": n_understated,
            "median_ratio_arch5_over_local3": statistics.median(
                row["ratio_arch5_over_local3"] for row in rows
            ),
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT_JSON} ({len(rows)} elastic rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
