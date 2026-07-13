"""Dispersion-vs-true-error calibration check for the concordance gates.

PROBE (arXiv:2605.00640) reports that raw ensemble disagreement can correlate
weakly with per-prediction error, which would make dispersion gating a
normality test rather than an uncertainty statement. This script measures,
on OUR reference-bound corpus, whether per-material cross-model dispersion
predicts per-material true error: for every property with reference values
in the bound Y-matrix evidence, it computes per-material (a) cross-model
relative dispersion and (b) median |relative error| across models, and
reports the Spearman rank correlation per property.

Output: data/discovery_gates/dispersion_vs_error.json (descriptive; no
thresholds are changed by this analysis).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from lupine_distill.statics import relative_dispersion  # noqa: E402

EVIDENCE_SCHEMA = "lupine.mlip.calc_evidence.v1"


def spearman(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation (average ranks for ties)."""
    def ranks(v: list[float]) -> np.ndarray:
        arr = np.asarray(v, dtype=float)
        order = arr.argsort()
        r = np.empty_like(arr)
        r[order] = np.arange(1, len(arr) + 1, dtype=float)
        # average ranks for exact ties
        for value in np.unique(arr):
            mask = arr == value
            if mask.sum() > 1:
                r[mask] = r[mask].mean()
        return r
    rx, ry = ranks(x), ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def load_bound(directory: Path) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
    """property -> material -> model -> {value, reference}."""
    out: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != EVIDENCE_SCHEMA:
            continue
        material = payload["material"]
        model = payload["source"]["model_id"]
        for prop in payload.get("properties", []):
            name = prop["name"]
            ref = prop.get("reference_value")
            value = prop.get("value")
            if ref is None or value is None or ref == 0:
                continue
            out.setdefault(name, {}).setdefault(material, {})[model] = {
                "value": float(value),
                "reference": float(ref),
            }
    return out


def main() -> int:
    bound_dir = _REPO_ROOT / "data" / "y_matrix_runs" / "bound"
    data = load_bound(bound_dir)
    results: dict[str, object] = {}
    for prop, by_material in sorted(data.items()):
        dispersions: list[float] = []
        median_errors: list[float] = []
        materials: list[str] = []
        for material, by_model in sorted(by_material.items()):
            if len(by_model) < 2:
                continue
            values = [rec["value"] for rec in by_model.values()]
            try:
                disp = relative_dispersion(values)
            except Exception:
                continue
            rel_errors = [
                abs(rec["value"] - rec["reference"]) / abs(rec["reference"])
                for rec in by_model.values()
            ]
            dispersions.append(disp)
            median_errors.append(float(np.median(rel_errors)))
            materials.append(material)
        if len(materials) < 5:
            continue
        rho = spearman(dispersions, median_errors)
        results[prop] = {
            "n_materials": len(materials),
            "spearman_rho_dispersion_vs_median_rel_error": rho,
            "per_material": {
                m: {"dispersion": d, "median_rel_error": e}
                for m, d, e in zip(materials, dispersions, median_errors)
            },
        }
        print(
            f"{prop}: n={len(materials)}, Spearman rho(dispersion, "
            f"median |rel err|) = {rho:.3f}"
        )
    artifact = {
        "schema": "lupine.discovery_gates.dispersion_vs_error.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_dir": bound_dir.as_posix(),
        "note": (
            "Descriptive calibration check answering the PROBE critique "
            "(arXiv:2605.00640): does cross-model dispersion track true "
            "error on the reference-bound corpus? Spearman rank correlation "
            "per property between per-material cross-model relative "
            "dispersion and per-material median |relative error| vs the "
            "bound reference. No thresholds were changed by this analysis. "
            "Caveats: N=4 models with two non-independent MACE variants; "
            "median-of-models error, not per-model."
        ),
        "properties": results,
    }
    out_path = _REPO_ROOT / "data" / "discovery_gates" / "dispersion_vs_error.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
