"""Derive per-model multiplicative calibration biases from EXISTING evidence.

CPU-only, no calculator runs: this script only reads JSON artifacts already
on disk.

* a0 / B0: from a calc-evidence directory (default
  ``data/y_matrix_runs/bound``) whose property entries carry both ``value``
  and ``reference_value``. For each model, property, and material class the
  bias is ``median(predicted / reference)`` over the class's calibration
  materials; the campaign de-biases with ``corrected = raw / bias``.
* C11 / C12 / C44: the only per-material Cij prediction artifact available
  (``mlip-elastic-benchmark/direction-shift-validation-2026-07-13/
  results.json``) is a SINGLE-model (TensorNet) study whose predictions are
  not keyed by the local model ids this campaign runs (chgnet / mace-*), so
  no per-local-model Cij calibration exists. The output records that fact
  explicitly and emits NO Cij biases -- the campaign then leaves Cij
  uncorrected, which is the honest arm.

Output: ``data/candidates/model_biases.v1.json`` with full provenance.

Run (reads JSONs only, safe anywhere):
    .venv-mlip312/Scripts/python python/scripts/derive_model_biases.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

import numpy as np

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parents[1]), str(_HERE.parents[2])):  # python/ ; repo root
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from lupine_distill.statics import InputValidationError  # noqa: E402
from lupine_distill.statics.gates import EVIDENCE_SCHEMA_ID  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("derive_model_biases")

BIASES_SCHEMA: Final[str] = "lupine.model_biases.v1"

#: Bias property key (campaign-side, lowercase) -> evidence property name.
SCALAR_BIAS_PROPERTIES: Final[Mapping[str, str]] = {"a0": "a0", "b0": "B0"}

#: Local model ids a Cij calibration would need per-model predictions for.
LOCAL_MODEL_IDS: Final[tuple[str, ...]] = (
    "chgnet",
    "mace-mp-small",
    "mace-mp-medium",
    "mace-mpa-0-medium",
)

#: Calibration material classes (class key -> member material labels).
CLASS_DEFINITIONS: Final[Mapping[str, tuple[str, ...] | None]] = {
    "fcc-metals": ("Ag", "Al", "Au", "Ca", "Cu", "Ni", "Pd", "Pt", "Sr"),
    # None means "every material present in the evidence directory".
    "all-21": None,
}

BIAS_FORMULA: Final[str] = (
    "bias[model][property][class] = median(predicted_value / reference_value) "
    "over the class's calibration materials; de-bias with corrected = raw / bias"
)


def load_prediction_ratios(
    evidence_dir: Path, evidence_property: str
) -> dict[str, dict[str, float]]:
    """``material -> {model_id: predicted/reference}`` from calc-evidence JSONs.

    Only ``lupine.mlip.calc_evidence.v1`` payloads whose requested property
    carries a finite ``value`` AND a finite non-zero ``reference_value``
    contribute; everything else is skipped (no reference means no ratio).
    """
    directory = Path(evidence_dir)
    if not directory.is_dir():
        raise InputValidationError(f"evidence directory does not exist: {directory}")
    ratios: dict[str, dict[str, float]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"cannot read evidence file {path}: {exc}") from exc
        if not isinstance(payload, Mapping) or payload.get("schema") != EVIDENCE_SCHEMA_ID:
            continue
        material = str(payload.get("material", ""))
        source = payload.get("source")
        model_id = str(source.get("model_id", "")) if isinstance(source, Mapping) else ""
        if not material or not model_id:
            raise InputValidationError(f"{path}: missing material or source.model_id")
        for prop in payload.get("properties", []):
            if not isinstance(prop, Mapping) or prop.get("name") != evidence_property:
                continue
            value = prop.get("value")
            reference = prop.get("reference_value")
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise InputValidationError(
                    f"{path}: non-finite {evidence_property} value {value!r}"
                )
            if (
                not isinstance(reference, (int, float))
                or isinstance(reference, bool)
                or not math.isfinite(float(reference))
                or float(reference) == 0.0
            ):
                continue  # no usable reference -> this cell cannot calibrate
            if model_id in ratios.get(material, {}):
                raise InputValidationError(
                    f"duplicate ({material}, {model_id}) {evidence_property} in {path}"
                )
            ratios.setdefault(material, {})[model_id] = float(value) / float(reference)
    return ratios


def class_members(
    class_key: str, available_materials: tuple[str, ...]
) -> tuple[str, ...]:
    """Materials of ``class_key`` present in the calibration set."""
    if class_key not in CLASS_DEFINITIONS:
        raise InputValidationError(
            f"unknown material class {class_key!r}; known: "
            f"{', '.join(sorted(CLASS_DEFINITIONS))}"
        )
    definition = CLASS_DEFINITIONS[class_key]
    if definition is None:
        return tuple(sorted(available_materials))
    return tuple(sorted(set(definition) & set(available_materials)))


def derive_scalar_biases(
    evidence_dir: Path,
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, dict[str, dict[str, int]]]]:
    """Per-model a0/B0 biases; returns ``(biases, sample_counts)``.

    ``biases[model][property][class] = median(pred/ref)`` over the class's
    calibration materials that have that model's prediction and a reference.
    A (model, property, class) cell with zero samples is an error: silent
    empties would turn into silent non-corrections downstream.
    """
    biases: dict[str, dict[str, dict[str, float]]] = {}
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for bias_key, evidence_name in SCALAR_BIAS_PROPERTIES.items():
        ratios = load_prediction_ratios(evidence_dir, evidence_name)
        if not ratios:
            raise InputValidationError(
                f"no {evidence_name!r} entries with reference values in "
                f"{evidence_dir}; cannot calibrate {bias_key!r}"
            )
        materials = tuple(sorted(ratios))
        models = sorted({m for by_model in ratios.values() for m in by_model})
        for class_key in CLASS_DEFINITIONS:
            members = class_members(class_key, materials)
            if not members:
                raise InputValidationError(
                    f"class {class_key!r} has no calibration materials in "
                    f"{evidence_dir} for {evidence_name!r}"
                )
            for model in models:
                sample = [
                    ratios[material][model]
                    for material in members
                    if model in ratios.get(material, {})
                ]
                if not sample:
                    raise InputValidationError(
                        f"model {model!r} has no {evidence_name!r} calibration "
                        f"samples in class {class_key!r}"
                    )
                biases.setdefault(model, {}).setdefault(bias_key, {})[class_key] = float(
                    np.median(sample)
                )
                counts.setdefault(model, {}).setdefault(bias_key, {})[class_key] = len(
                    sample
                )
    return biases, counts


def inspect_cij_calibration(results_path: Path) -> dict[str, object]:
    """Honest availability check for per-local-model Cij calibration data.

    The direction-shift-validation artifact carries per-material Cij
    predictions and reconstructed targets, but for ONE model (TensorNet):
    its ``arms[*].predictions`` are keyed by material, never by the local
    model ids the campaign runs. Per-local-model Cij biases therefore cannot
    be derived from it, and this function records exactly why.
    """
    path = Path(results_path)
    if not path.is_file():
        return {
            "available": False,
            "inspected": path.as_posix(),
            "reason": f"results file not found: {path}",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "inspected": path.as_posix(),
            "reason": f"results file unreadable: {exc}",
        }
    found_locals = sorted(
        model
        for model in LOCAL_MODEL_IDS
        if _mentions_model_predictions(payload, model)
    )
    if found_locals:
        # Data exists but this script does not yet implement its extraction:
        # refuse rather than guess at an untested parser.
        return {
            "available": False,
            "inspected": path.as_posix(),
            "reason": (
                f"results file mentions local model ids {found_locals} but "
                f"derive_model_biases.py has no validated extractor for that "
                f"layout; extend the script before trusting Cij biases"
            ),
        }
    return {
        "available": False,
        "inspected": path.as_posix(),
        "reason": (
            "single-model study (TensorNet direction-shift validation): "
            "arms[*].predictions are keyed by material only, with no "
            f"per-model predictions for any local model id {list(LOCAL_MODEL_IDS)}; "
            "per-local-model C11/C12/C44 calibration is not derivable from it, "
            "so the campaign leaves Cij raw (uncorrected)"
        ),
    }


def _mentions_model_predictions(payload: object, model_id: str) -> bool:
    """True when ``model_id`` appears as a mapping key anywhere in the payload."""
    if isinstance(payload, Mapping):
        if model_id in payload:
            return True
        return any(_mentions_model_predictions(v, model_id) for v in payload.values())
    if isinstance(payload, list):
        return any(_mentions_model_predictions(v, model_id) for v in payload)
    return False


def build_biases_artifact(
    evidence_dir: Path, elastic_results: Path
) -> dict[str, object]:
    """Assemble the full model_biases.v1 payload (pure; no file writes)."""
    biases, counts = derive_scalar_biases(evidence_dir)
    a0_materials = tuple(sorted(load_prediction_ratios(evidence_dir, "a0")))
    return {
        "schema": BIASES_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "evidence_dir": Path(evidence_dir).as_posix(),
            "evidence_schema": EVIDENCE_SCHEMA_ID,
            "formula": BIAS_FORMULA,
            "class_definitions": {
                class_key: list(class_members(class_key, a0_materials))
                for class_key in CLASS_DEFINITIONS
            },
            "sample_counts": counts,
        },
        "biases": biases,
        "cij": inspect_cij_calibration(elastic_results),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--evidence-dir",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "bound"),
        help="Calc-evidence directory with value + reference_value entries",
    )
    parser.add_argument(
        "--elastic-results",
        default=str(
            _REPO_ROOT
            / "mlip-elastic-benchmark"
            / "direction-shift-validation-2026-07-13"
            / "results.json"
        ),
        help="Cij benchmark results to inspect for per-model calibration data",
    )
    parser.add_argument(
        "--out",
        default=str(_REPO_ROOT / "data" / "candidates" / "model_biases.v1.json"),
        help="Output biases artifact path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = build_biases_artifact(Path(args.evidence_dir), Path(args.elastic_results))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    for model, per_prop in sorted(artifact["biases"].items()):
        for prop, per_class in per_prop.items():
            for class_key, bias in per_class.items():
                log.info("bias %s %s %s = %.5f", model, prop, class_key, bias)
    log.info("cij: available=%s (%s)", artifact["cij"]["available"], artifact["cij"]["reason"])
    log.info("biases -> %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
