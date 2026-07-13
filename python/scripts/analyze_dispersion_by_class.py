"""Class-stratified dispersion-vs-true-error check (gate-license input).

Extends analyze_dispersion_vs_error.py (all-materials Spearman rho between
per-material cross-model dispersion and median |relative error|) by
stratifying per CLASS, wherever references exist:

* metals-fcc / metals-bcc: from the reference-bound Y-matrix evidence
  (``data/y_matrix_runs/bound``), properties a0 and B0 (the two carried with
  references for all 21 materials).
* perovskites: from the Round-1 campaign report references (a0/b0 where
  non-null; b0 has n=5, a0 only n=4 because CsGeI3 lacks an a0 reference).

Output: ``data/discovery_gates/dispersion_vs_error_by_class.json``
(descriptive; regenerated in full on every run — it is derived data). This
feeds the gate-license design: a class where rho ~ 0 gets no license to treat
concordance as an uncertainty statement (it remains a normality test).

Run (no GPU, no calculators load):
    .venv-mlip312/Scripts/python python/scripts/analyze_dispersion_by_class.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

import numpy as np

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from analyze_dispersion_vs_error import load_bound, spearman  # noqa: E402
from build_class_corpus import (  # noqa: E402
    CAMPAIGN_REPORT_SCHEMA,
    CLASS_METALS_BCC,
    CLASS_METALS_FCC,
    CLASS_PEROVSKITES,
    METAL_CLASS_BY_MATERIAL,
    _load_report,
)

from lupine_distill.statics import InputValidationError, relative_dispersion  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("dispersion_by_class")

ARTIFACT_SCHEMA: Final[str] = "lupine.discovery_gates.dispersion_vs_error_by_class.v1"

#: Bound-evidence properties carrying references for every metal.
METAL_PROPERTIES: Final[tuple[str, ...]] = ("a0", "B0")

#: Round-1 report property keys with (sometimes) non-null references.
PEROVSKITE_PROPERTIES: Final[tuple[str, ...]] = ("a0", "b0")

#: Below this many materials a rank correlation is pure noise; entries with
#: n under the *comfortable* floor of 5 are still reported (the task needs
#: the perovskite a0 n=4 number) but carry an explicit small-n warning.
MIN_MATERIALS: Final[int] = 4


def _rho_entry(
    materials: list[str], dispersions: list[float], median_errors: list[float]
) -> dict[str, object]:
    entry: dict[str, object] = {
        "n_materials": len(materials),
        "spearman_rho_dispersion_vs_median_rel_error": spearman(
            dispersions, median_errors
        ),
        "per_material": {
            m: {"dispersion": d, "median_rel_error": e}
            for m, d, e in zip(materials, dispersions, median_errors)
        },
    }
    if len(materials) < 5:
        entry["small_n_warning"] = (
            f"n={len(materials)} < 5: a single material determines the rank "
            f"ordering; treat this rho as anecdote, not calibration"
        )
    return entry


def metals_by_class(bound_dir: Path) -> dict[str, dict[str, dict[str, object]]]:
    """class -> property -> rho entry, from the reference-bound metals."""
    bound_dir = Path(bound_dir)
    if not bound_dir.is_dir():
        raise InputValidationError(f"bound evidence directory missing: {bound_dir}")
    data = load_bound(bound_dir)
    results: dict[str, dict[str, dict[str, object]]] = {}
    for prop in METAL_PROPERTIES:
        by_material = data.get(prop, {})
        per_class: dict[str, tuple[list[str], list[float], list[float]]] = {}
        for material, by_model in sorted(by_material.items()):
            class_name = METAL_CLASS_BY_MATERIAL.get(material)
            if class_name not in (CLASS_METALS_FCC, CLASS_METALS_BCC):
                continue
            if len(by_model) < 2:
                continue
            values = [rec["value"] for rec in by_model.values()]
            try:
                disp = relative_dispersion(values)
            except InputValidationError:
                continue
            rel_errors = [
                abs(rec["value"] - rec["reference"]) / abs(rec["reference"])
                for rec in by_model.values()
            ]
            mats, disps, errs = per_class.setdefault(class_name, ([], [], []))
            mats.append(material)
            disps.append(disp)
            errs.append(float(np.median(rel_errors)))
        for class_name, (mats, disps, errs) in per_class.items():
            if len(mats) < MIN_MATERIALS:
                continue
            results.setdefault(class_name, {})[prop] = _rho_entry(mats, disps, errs)
    return results


def perovskites_from_report(report_path: Path) -> dict[str, dict[str, object]]:
    """property -> rho entry for Round-1 perovskites with non-null references."""
    payload = _load_report(Path(report_path), CAMPAIGN_REPORT_SCHEMA)
    candidates = payload.get("candidates")
    if not isinstance(candidates, Mapping) or not candidates:
        raise InputValidationError(f"{report_path}: no 'candidates' mapping")
    results: dict[str, dict[str, object]] = {}
    for prop in PEROVSKITE_PROPERTIES:
        materials: list[str] = []
        dispersions: list[float] = []
        median_errors: list[float] = []
        for candidate_id, candidate in sorted(candidates.items()):
            if not isinstance(candidate, Mapping):
                continue
            if str(candidate.get("structure_type", "")) != "perovskite":
                continue
            references = candidate.get("references")
            reference = (
                references.get(prop) if isinstance(references, Mapping) else None
            )
            if reference is None or float(reference) == 0.0:
                continue
            per_model = candidate.get("per_model", {})
            values = [
                float(rec["properties"][prop])
                for rec in per_model.values()
                if isinstance(rec, Mapping) and "error" not in rec
            ]
            if len(values) < 2:
                continue
            try:
                disp = relative_dispersion(values)
            except InputValidationError:
                continue
            rel_errors = [
                abs(v - float(reference)) / abs(float(reference)) for v in values
            ]
            materials.append(str(candidate.get("formula", candidate_id)))
            dispersions.append(disp)
            median_errors.append(float(np.median(rel_errors)))
        if len(materials) >= MIN_MATERIALS:
            results[prop] = _rho_entry(materials, dispersions, median_errors)
    if not results:
        raise InputValidationError(
            f"{report_path}: no perovskite property had >= {MIN_MATERIALS} "
            f"referenced materials"
        )
    return results


def render_rho_table(by_class: Mapping[str, Mapping[str, Mapping[str, object]]]) -> str:
    lines = [
        "| class | property | n | Spearman rho (dispersion vs median |rel err|) |",
        "|---|---|---|---|",
    ]
    for class_name in sorted(by_class):
        for prop, entry in sorted(by_class[class_name].items()):
            rho = entry["spearman_rho_dispersion_vs_median_rel_error"]
            flag = " (small n)" if "small_n_warning" in entry else ""
            lines.append(
                f"| {class_name} | {prop} | {entry['n_materials']} "
                f"| {rho:.3f}{flag} |"
            )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--bound-dir",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "bound"),
        help="Reference-bound metal calc-evidence directory",
    )
    parser.add_argument(
        "--round1-report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1" / "report.json"),
        help="Round-1 campaign report (perovskite references)",
    )
    parser.add_argument(
        "--out",
        default=str(
            _REPO_ROOT
            / "data"
            / "discovery_gates"
            / "dispersion_vs_error_by_class.json"
        ),
        help="Output artifact path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        by_class = metals_by_class(Path(args.bound_dir))
        by_class[CLASS_PEROVSKITES] = perovskites_from_report(
            Path(args.round1_report)
        )
    except InputValidationError as exc:
        log.error("analysis failed: %s", exc)
        return 1
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "metals": Path(args.bound_dir).as_posix(),
            "perovskites": Path(args.round1_report).as_posix(),
        },
        "note": (
            "Class-stratified extension of dispersion_vs_error.json: per "
            "(class, property), Spearman rank correlation between "
            "per-material cross-model relative dispersion and per-material "
            "median |relative error| vs the bound/report reference. Feeds "
            "the gate-license design: a class-property with rho ~ 0 earns no "
            "license to read concordance as an uncertainty statement. "
            "Caveats: N=4 models with three non-independent MACE/CHGNet-era "
            "variants sharing training data; median-of-models error; "
            "perovskite a0 has only n=4 referenced materials; small-n rank "
            "correlations are fragile to a single material."
        ),
        "by_class": by_class,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    log.info("\n%s", render_rho_table(by_class))
    log.info("-> %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
