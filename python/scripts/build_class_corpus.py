"""Class-native calibration corpus + class-stratified thresholds (v3).

The 2026-07-13 halide panel showed that metal-derived per-property thresholds
(thresholds.v2, calibrated on the metal-dominated elastic baseline) refuse
known-good ionic compounds: dispersion distributions differ BY CLASS. This
builder assembles a class-stratified calibration corpus from ALREADY-MEASURED
per-(material, model) property values — no new simulation runs — and derives
per-(class, property) flag/refuse thresholds from each class's OWN dispersion
distribution.

Corpus layout (``data/y_matrix_runs/class_corpus/<class>/``):

* ``metals-fcc`` (9) / ``metals-bcc`` (7): elastic-baseline evidence files
  copied as-is (``data/y_matrix_runs/elastic_baseline``), split by prototype.
* ``covalent-intermetallic`` (3: Si, Ni3Al, NiAl): kept in their own class
  directory so nothing is silently dropped, but n=3 < 5 means NO thresholds
  are derived for it (documented in the artifact notes).
* ``ionics-rocksalt`` (6: LiF/LiCl/LiBr/LiI/NaCl/MgO): re-emitted as
  ``calc_evidence.v1`` from the halide-panel report per_model properties
  (``data/climate_targets/halide_panel/report.json``). The elastic baseline's
  own MgO/NaCl rocksalt cells are deliberately NOT copied into this class:
  the halide panel is a single instrument run covering all six compounds, and
  mixing sources would duplicate (material, model) cells.
* ``perovskites`` (5: CsSnCl3/CsSnBr3/CsSnI3/CsGeI3/CsPbI3): re-emitted from
  the Round-1 candidate-campaign report per_model properties (RAW arm, never
  the bias-corrected arm — the calibration corpus wants unmodified instrument
  readings).

Thresholds: for each (class, property) with >= 5 materials,
``lupine_distill.statics.derive_per_property_thresholds`` runs on that class
directory alone -> ``data/discovery_gates/thresholds.v3.json``
(schema ``lupine.discovery_gates.thresholds.v3``, ``per_class`` keyed).

Run (any Python with lupine_distill deps; no GPU, no calculators load):
    .venv-mlip312/Scripts/python python/scripts/build_class_corpus.py
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from run_elastic_baseline import (  # noqa: E402
    BASELINE_MATERIALS,
    audit_calibration_cells,
)

from lupine_distill.calc_evidence import build_calc_evidence  # noqa: E402
from lupine_distill.schemas import CALC_EVIDENCE_SCHEMA, PropertyValue  # noqa: E402
from lupine_distill.statics import (  # noqa: E402
    DEFAULT_DISPERSION_FLOOR_FRACTION,
    DISPERSION_METRIC_FLOORED_V1,
    ConcordanceThresholds,
    InputValidationError,
    derive_per_property_thresholds,
    load_property_by_material,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("build_class_corpus")

THRESHOLDS_SCHEMA: Final[str] = "lupine.discovery_gates.thresholds.v3"
GATES_REPORT_SCHEMA: Final[str] = "lupine.discovery_gates.v1"
CAMPAIGN_REPORT_SCHEMA: Final[str] = "lupine.candidate_campaign.v1"

#: Corpus class names in a stable presentation order.
CLASS_METALS_FCC: Final[str] = "metals-fcc"
CLASS_METALS_BCC: Final[str] = "metals-bcc"
CLASS_COVALENT: Final[str] = "covalent-intermetallic"
CLASS_IONICS: Final[str] = "ionics-rocksalt"
CLASS_PEROVSKITES: Final[str] = "perovskites"
ALL_CLASSES: Final[tuple[str, ...]] = (
    CLASS_METALS_FCC,
    CLASS_METALS_BCC,
    CLASS_COVALENT,
    CLASS_IONICS,
    CLASS_PEROVSKITES,
)

#: Elastic-baseline prototype -> corpus class. Rocksalt maps to ``None``:
#: the ionics-rocksalt class is sourced from the halide panel instead (see
#: module docstring), so the baseline's MgO/NaCl cells are skipped here.
_CLASS_BY_STRUCTURE: Final[Mapping[str, str | None]] = {
    "fcc": CLASS_METALS_FCC,
    "bcc": CLASS_METALS_BCC,
    "diamond": CLASS_COVALENT,
    "l12": CLASS_COVALENT,
    "b2": CLASS_COVALENT,
    "rocksalt": None,
}

#: material formula -> (corpus class | None) for the elastic-baseline set.
METAL_CLASS_BY_MATERIAL: Final[Mapping[str, str | None]] = {
    formula: _CLASS_BY_STRUCTURE[structure]
    for formula, structure in BASELINE_MATERIALS
}

#: (report property key, evidence property name, unit) — matches
#: statics.gates.PROPERTY_EVIDENCE_NAMES and the elastic-baseline emission.
_REPORT_PROPERTIES: Final[tuple[tuple[str, str, str], ...]] = (
    ("a0", "a0", "Angstrom"),
    ("b0", "B0", "GPa"),
    ("c11", "C11", "GPa"),
    ("c12", "C12", "GPa"),
    ("c44", "C44", "GPa"),
)

#: Honesty notes carried verbatim into thresholds.v3.json.
THRESHOLD_NOTES: Final[tuple[str, ...]] = (
    "Class stratification: each (class, property) threshold is p75/p95 of "
    "that class's OWN measured cross-model dispersion distribution; nothing "
    "is transferred across classes. This answers the 2026-07-13 halide-panel "
    "finding that metal-derived C11/C44 percentiles refuse known-good ionics.",
    "Order-statistic fragility at small n: with n=5-9 materials per class "
    "the p95 'refuse' threshold is dominated by the single largest observed "
    "dispersion and the p75 'flag' threshold by the top two; adding or "
    "removing ONE material can move both substantially. Treat these as "
    "descriptive calibration, not sharp decision boundaries.",
    "Same-instrument guarantee (with one documented caveat): metals and "
    "ionics-rocksalt cells were measured by the run_discovery_gates probe "
    "(compute_lattice recentring EOS scan, BM3 EOS, relaxed-ion stress-strain "
    "elastic constants, elastic_delta=0.005). Perovskite cells come from the "
    "candidate-campaign runner, which relaxes the supplied cell via the "
    "equivalent ev_relax scan and applies the SAME relaxed-ion elastic probe "
    "with the same delta; the lattice leg is atoms-based rather than "
    "formula-based but mirrors the same algorithm.",
    "Model non-independence: mace-mp-small, mace-mp-medium and "
    "mace-mpa-0-medium share architecture (and largely training data), so "
    "the effective number of independent models is below the nominal 4; "
    "dispersions are ensemble spread, not independent-error spread.",
    "covalent-intermetallic (Si, Ni3Al, NiAl) is materialized as a corpus "
    "class so the cells are not silently dropped, but with n=3 < 5 no "
    "thresholds are derived for it.",
    "ionics-rocksalt uses the halide-panel cells only; the elastic "
    "baseline's own MgO/NaCl cells are excluded from this class to keep one "
    "instrument run per class and avoid duplicate (material, model) cells.",
    "Perovskite cells are the RAW per_model arm of the Round-1 campaign "
    "report, never the bias-corrected arm: a calibration corpus must contain "
    "unmodified instrument readings.",
    "PEROVSKITE CLASS IS PROVISIONAL/IN-SAMPLE (2026-07-13 errata finding 6; "
    "Round-3 prereg fix 2): the calibration corpus IS the Round-1 gated "
    "candidate set (same 5 compounds), so any perovskite dispersion-error "
    "license computed on it is circular. No perovskite claim gates on v3 "
    "until Round-3 evidence creates the first out-of-sample perovskite "
    "corpus.",
    "Dispersion metric floored-v1 (Round-3 registered instrument fix 1, "
    "2026-07-13 prereg): per-(class, property) denominator = max(|cross-model "
    "median|, 0.1 x class-median of per-material |median value|). The "
    "unfloored (max-min)/|median| metric is undefined at sign-crossing "
    "medians; the previous artifact is preserved as "
    "thresholds.v3.unfloored.json for diffability.",
    "Calibration-cell audit (V, Cr; metals-bcc): V's C44 cross-model median "
    "is ~0 GPa - the models disagree on the SIGN of V's C44 (sign-crossing "
    "predictions), a calibration-cell pathology, not a usable dispersion "
    "sample; unfloored it produced dispersion 237.7 and a bcc C44 refuse "
    "threshold of 167.6 that could never fire. Cr (next-largest bcc C44/C12 "
    "disperser) is audited alongside. See the calibration_cell_audit block.",
)

#: Per-class status markings carried into the artifact (fix 2: the perovskite
#: class must visibly carry its provisional/in-sample standing).
CLASS_STATUS: Final[Mapping[str, str]] = {
    CLASS_PEROVSKITES: (
        "provisional/in-sample: calibration corpus = the Round-1 gated "
        "candidates (same 5 compounds); no perovskite claim gates on v3 "
        "until an out-of-sample perovskite corpus exists (Round-3 evidence)"
    ),
}


# --------------------------------------------------------------------------
# validation helpers
# --------------------------------------------------------------------------


def _load_report(path: Path, expected_schema: str) -> dict[str, object]:
    """Read + validate a report JSON at a trust boundary (fail fast)."""
    if not path.is_file():
        raise InputValidationError(f"report does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read report {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputValidationError(f"{path}: report root must be a JSON object")
    schema = payload.get("schema")
    if schema != expected_schema:
        raise InputValidationError(
            f"{path}: expected schema {expected_schema!r}, got {schema!r}"
        )
    if not isinstance(payload.get("generated_at"), str):
        raise InputValidationError(f"{path}: missing 'generated_at' string")
    return payload


def _parse_generated_at(payload: Mapping[str, object], path: Path) -> datetime:
    raw = str(payload["generated_at"])
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise InputValidationError(
            f"{path}: generated_at {raw!r} is not ISO-8601"
        ) from exc


def _relpath(path: Path) -> str:
    """Repo-relative posix path when possible (stable provenance strings)."""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _properties_from_record(
    record: Mapping[str, object],
    context: str,
    references: Mapping[str, object] | None = None,
    reference_source: str | None = None,
) -> list[PropertyValue]:
    """a0/B0/C11/C12/C44 PropertyValues from one report per_model record."""
    props = record.get("properties")
    if not isinstance(props, Mapping):
        raise InputValidationError(f"{context}: record has no 'properties' mapping")
    out: list[PropertyValue] = []
    for report_key, evidence_name, unit in _REPORT_PROPERTIES:
        if report_key not in props:
            raise InputValidationError(
                f"{context}: property {report_key!r} missing from record"
            )
        reference = references.get(report_key) if references else None
        out.append(
            PropertyValue(
                name=evidence_name,
                value=float(props[report_key]),  # type: ignore[arg-type]
                unit=unit,
                reference_value=(
                    float(reference) if reference is not None else None  # type: ignore[arg-type]
                ),
                reference_source=reference_source if reference is not None else None,
            )
        )
    return out


# --------------------------------------------------------------------------
# (a) metals: copy elastic-baseline evidence as-is, split by class
# --------------------------------------------------------------------------


def gather_metals(
    baseline_dir: Path, corpus_root: Path
) -> dict[str, list[str]]:
    """Copy elastic-baseline ``*.evidence.json`` cells into class directories.

    Returns ``class -> sorted copied file names``. Rocksalt cells are skipped
    (ionics come from the halide panel); an unknown material fails fast.
    """
    baseline_dir = Path(baseline_dir)
    if not baseline_dir.is_dir():
        raise InputValidationError(
            f"elastic-baseline directory does not exist: {baseline_dir}"
        )
    copied: dict[str, list[str]] = {}
    n_seen = 0
    for path in sorted(baseline_dir.glob("*.evidence.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"cannot read evidence {path}: {exc}") from exc
        if not isinstance(payload, Mapping) or payload.get("schema") != CALC_EVIDENCE_SCHEMA:
            continue
        n_seen += 1
        material = str(payload.get("material", ""))
        if material not in METAL_CLASS_BY_MATERIAL:
            raise InputValidationError(
                f"{path}: material {material!r} is not in the elastic-baseline "
                f"set; known: {', '.join(sorted(METAL_CLASS_BY_MATERIAL))}"
            )
        class_name = METAL_CLASS_BY_MATERIAL[material]
        if class_name is None:  # rocksalt: sourced from the halide panel
            continue
        class_dir = corpus_root / class_name
        class_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, class_dir / path.name)
        copied.setdefault(class_name, []).append(path.name)
    if n_seen == 0:
        raise InputValidationError(
            f"no {CALC_EVIDENCE_SCHEMA} files in {baseline_dir}"
        )
    return {cls: sorted(names) for cls, names in copied.items()}


# --------------------------------------------------------------------------
# (b) ionics-rocksalt: halide-panel report -> calc_evidence.v1
# --------------------------------------------------------------------------


def gather_ionics(report_path: Path, corpus_root: Path) -> dict[str, object]:
    """Emit calc_evidence.v1 cells for every halide-panel rocksalt subject.

    Per_model records carrying an ``error`` key are skipped and reported —
    they hold no property values to calibrate on.
    """
    report_path = Path(report_path)
    payload = _load_report(report_path, GATES_REPORT_SCHEMA)
    computed_at = _parse_generated_at(payload, report_path)
    device = str(payload.get("device", ""))
    if device not in ("cuda", "cpu"):
        raise InputValidationError(
            f"{report_path}: device must be 'cuda' or 'cpu', got {device!r}"
        )
    versions = payload.get("calculator_versions")
    versions = dict(versions) if isinstance(versions, Mapping) else {}
    subjects = payload.get("subjects")
    if not isinstance(subjects, Mapping) or not subjects:
        raise InputValidationError(f"{report_path}: no 'subjects' mapping")
    class_dir = corpus_root / CLASS_IONICS
    class_dir.mkdir(parents=True, exist_ok=True)
    source_rel = _relpath(report_path)
    written: list[str] = []
    skipped: list[str] = []
    for label, subject in sorted(subjects.items()):
        if not isinstance(subject, Mapping):
            raise InputValidationError(f"{report_path}: subject {label!r} malformed")
        structure_type = str(subject.get("structure_type", ""))
        if structure_type != "rocksalt":
            continue
        formula = str(subject.get("formula", ""))
        if not formula:
            raise InputValidationError(f"{report_path}: subject {label!r} lacks formula")
        per_model = subject.get("per_model")
        if not isinstance(per_model, Mapping) or not per_model:
            raise InputValidationError(
                f"{report_path}: subject {label!r} has no per_model records"
            )
        for model_id, record in sorted(per_model.items()):
            context = f"{report_path}:{label}:{model_id}"
            if not isinstance(record, Mapping):
                raise InputValidationError(f"{context}: record must be a mapping")
            if "error" in record:
                skipped.append(f"{label}/{model_id}")
                continue
            properties = _properties_from_record(record, context)
            evidence = build_calc_evidence(
                material=formula,
                model_id=str(model_id),
                device=device,  # type: ignore[arg-type]
                calculator_version=versions.get(model_id),
                inputs={
                    "material": formula,
                    "structure_type": structure_type,
                    "model_id": str(model_id),
                    "device": device,
                    "source_report": source_rel,
                    "source_schema": GATES_REPORT_SCHEMA,
                    "source_generated_at": str(payload["generated_at"]),
                    "source_subject": label,
                },
                properties=properties,
                run_label=f"class-corpus {CLASS_IONICS} from {source_rel}",
                computed_at=computed_at,
            )
            out_path = class_dir / f"{label}_{model_id}.evidence.json"
            out_path.write_text(
                json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2),
                encoding="utf-8",
            )
            written.append(out_path.name)
    if not written:
        raise InputValidationError(
            f"{report_path}: no rocksalt subject produced any evidence cell"
        )
    return {
        "source_report": source_rel,
        "source_generated_at": str(payload["generated_at"]),
        "written": sorted(written),
        "skipped_error_cells": sorted(skipped),
    }


# --------------------------------------------------------------------------
# (c) perovskites: Round-1 campaign report -> calc_evidence.v1
# --------------------------------------------------------------------------


def gather_perovskites(report_path: Path, corpus_root: Path) -> dict[str, object]:
    """Emit calc_evidence.v1 cells for every Round-1 perovskite candidate.

    Only candidates with ``structure_type == 'perovskite'`` are taken; the
    RAW ``per_model`` arm is used (never ``corrected_arm``). Non-null
    reference values from the report's references block are embedded with
    their provenance so the class corpus stays self-contained.
    """
    report_path = Path(report_path)
    payload = _load_report(report_path, CAMPAIGN_REPORT_SCHEMA)
    computed_at = _parse_generated_at(payload, report_path)
    parameters = payload.get("parameters")
    device = (
        str(parameters.get("device", "")) if isinstance(parameters, Mapping) else ""
    )
    if device not in ("cuda", "cpu"):
        raise InputValidationError(
            f"{report_path}: parameters.device must be 'cuda' or 'cpu', got {device!r}"
        )
    candidates = payload.get("candidates")
    if not isinstance(candidates, Mapping) or not candidates:
        raise InputValidationError(f"{report_path}: no 'candidates' mapping")
    class_dir = corpus_root / CLASS_PEROVSKITES
    class_dir.mkdir(parents=True, exist_ok=True)
    source_rel = _relpath(report_path)
    written: list[str] = []
    skipped: list[str] = []
    for candidate_id, candidate in sorted(candidates.items()):
        if not isinstance(candidate, Mapping):
            raise InputValidationError(
                f"{report_path}: candidate {candidate_id!r} malformed"
            )
        if str(candidate.get("structure_type", "")) != "perovskite":
            continue
        formula = str(candidate.get("formula", ""))
        if not formula:
            raise InputValidationError(
                f"{report_path}: candidate {candidate_id!r} lacks formula"
            )
        references = candidate.get("references")
        references = dict(references) if isinstance(references, Mapping) else {}
        per_model = candidate.get("per_model")
        if not isinstance(per_model, Mapping) or not per_model:
            raise InputValidationError(
                f"{report_path}: candidate {candidate_id!r} has no per_model records"
            )
        for model_id, record in sorted(per_model.items()):
            context = f"{report_path}:{candidate_id}:{model_id}"
            if not isinstance(record, Mapping):
                raise InputValidationError(f"{context}: record must be a mapping")
            if "error" in record:
                skipped.append(f"{candidate_id}/{model_id}")
                continue
            properties = _properties_from_record(
                record,
                context,
                references=references,
                reference_source=(
                    f"references block of {source_rel} (candidate {candidate_id})"
                ),
            )
            evidence = build_calc_evidence(
                material=formula,
                model_id=str(model_id),
                device=device,  # type: ignore[arg-type]
                calculator_version=None,  # campaign report carries no versions
                inputs={
                    "material": formula,
                    "structure_type": "perovskite",
                    "model_id": str(model_id),
                    "device": device,
                    "source_report": source_rel,
                    "source_schema": CAMPAIGN_REPORT_SCHEMA,
                    "source_generated_at": str(payload["generated_at"]),
                    "source_candidate": candidate_id,
                    "arm": "per_model (raw, not bias-corrected)",
                },
                properties=properties,
                run_label=f"class-corpus {CLASS_PEROVSKITES} from {source_rel}",
                computed_at=computed_at,
            )
            out_path = class_dir / f"{formula}_perovskite_{model_id}.evidence.json"
            out_path.write_text(
                json.dumps(evidence.model_dump(mode="json", by_alias=True), indent=2),
                encoding="utf-8",
            )
            written.append(out_path.name)
    if not written:
        raise InputValidationError(
            f"{report_path}: no perovskite candidate produced any evidence cell"
        )
    return {
        "source_report": source_rel,
        "source_generated_at": str(payload["generated_at"]),
        "written": sorted(written),
        "skipped_error_cells": sorted(skipped),
    }


# --------------------------------------------------------------------------
# thresholds.v3: per-(class, property) percentiles
# --------------------------------------------------------------------------


def derive_class_thresholds(
    corpus_root: Path,
    *,
    classes: tuple[str, ...] = ALL_CLASSES,
    min_materials: int = 5,
) -> tuple[dict[str, dict[str, ConcordanceThresholds]], dict[str, str]]:
    """Per-class thresholds where the class has >= ``min_materials`` materials.

    Returns ``(per_class, skipped)`` where ``skipped`` maps a class name to
    the reason no thresholds were derived for it.
    """
    if min_materials < 5:
        raise InputValidationError(
            f"min_materials must be >= 5 (percentiles below that are not a "
            f"distribution statement), got {min_materials}"
        )
    corpus_root = Path(corpus_root)
    per_class: dict[str, dict[str, ConcordanceThresholds]] = {}
    skipped: dict[str, str] = {}
    for class_name in classes:
        class_dir = corpus_root / class_name
        if not class_dir.is_dir():
            skipped[class_name] = f"class directory missing: {class_dir.as_posix()}"
            continue
        n_materials = len(load_property_by_material(class_dir, property_name="a0"))
        if n_materials < min_materials:
            skipped[class_name] = (
                f"only {n_materials} material(s) < {min_materials} required "
                f"for percentile thresholds"
            )
            continue
        per_class[class_name] = derive_per_property_thresholds(
            class_dir, floor_fraction=DEFAULT_DISPERSION_FLOOR_FRACTION
        )
    return per_class, skipped


def render_threshold_table(
    per_class: Mapping[str, Mapping[str, ConcordanceThresholds]],
) -> str:
    """Full per-class threshold table (printed and embedded in logs)."""
    lines = [
        "| class | property | flag (p75) | refuse (p95) | n materials |",
        "|---|---|---|---|---|",
    ]
    for class_name in sorted(per_class):
        for prop, t in per_class[class_name].items():
            lines.append(
                f"| {class_name} | {prop} | {t.flag:.4f} | {t.refuse:.4f} "
                f"| {t.n_samples} |"
            )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--elastic-baseline-dir",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "elastic_baseline"),
        help="Metal calc-evidence source (copied as-is, split fcc/bcc)",
    )
    parser.add_argument(
        "--halide-report",
        default=str(
            _REPO_ROOT / "data" / "climate_targets" / "halide_panel" / "report.json"
        ),
        help="Halide-panel discovery-gates report (ionics-rocksalt source)",
    )
    parser.add_argument(
        "--round1-report",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1" / "report.json"),
        help="Round-1 candidate-campaign report (perovskites source)",
    )
    parser.add_argument(
        "--corpus-root",
        default=str(_REPO_ROOT / "data" / "y_matrix_runs" / "class_corpus"),
        help="Class-stratified corpus output root",
    )
    parser.add_argument(
        "--thresholds-out",
        default=str(_REPO_ROOT / "data" / "discovery_gates" / "thresholds.v3.json"),
        help="Class-stratified thresholds artifact path",
    )
    parser.add_argument(
        "--min-materials",
        type=int,
        default=5,
        help="Minimum materials per class for thresholds (>= 5)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    corpus_root = Path(args.corpus_root)
    corpus_root.mkdir(parents=True, exist_ok=True)

    try:
        metals = gather_metals(Path(args.elastic_baseline_dir), corpus_root)
        ionics = gather_ionics(Path(args.halide_report), corpus_root)
        perovskites = gather_perovskites(Path(args.round1_report), corpus_root)
        per_class, skipped = derive_class_thresholds(
            corpus_root, min_materials=args.min_materials
        )
    except InputValidationError as exc:
        log.error("corpus build failed: %s", exc)
        return 1

    for class_name, names in sorted(metals.items()):
        log.info("%s: %d evidence cells copied", class_name, len(names))
    log.info(
        "%s: %d cells emitted from %s (skipped error cells: %d)",
        CLASS_IONICS,
        len(ionics["written"]),
        ionics["source_report"],
        len(ionics["skipped_error_cells"]),
    )
    log.info(
        "%s: %d cells emitted from %s (skipped error cells: %d)",
        CLASS_PEROVSKITES,
        len(perovskites["written"]),
        perovskites["source_report"],
        len(perovskites["skipped_error_cells"]),
    )
    for class_name, reason in sorted(skipped.items()):
        log.info("thresholds NOT derived for %s: %s", class_name, reason)

    try:
        bcc_audit = audit_calibration_cells(corpus_root / CLASS_METALS_BCC)
    except InputValidationError as exc:
        log.error("calibration-cell audit failed: %s", exc)
        return 1

    artifact = {
        "schema": THRESHOLDS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_root": _relpath(corpus_root),
        "dispersion_metric": {
            "version": DISPERSION_METRIC_FLOORED_V1,
            "definition": (
                "(max - min) / max(|cross-model median|, floor_fraction * "
                "class-median of per-material |median value|), per "
                "(class, property)"
            ),
            "floor_fraction": DEFAULT_DISPERSION_FLOOR_FRACTION,
            "registered_in": "docs/plans/2026-07-13-round3-preregistration.md",
        },
        "per_class": {
            class_name: {
                "evidence_dir": _relpath(corpus_root / class_name),
                "n_materials": next(
                    iter(per_class[class_name].values())
                ).n_samples,
                **(
                    {"status": CLASS_STATUS[class_name]}
                    if class_name in CLASS_STATUS
                    else {}
                ),
                "per_property": {
                    prop: t.to_dict() for prop, t in per_class[class_name].items()
                },
            }
            for class_name in sorted(per_class)
        },
        "calibration_cell_audit": {CLASS_METALS_BCC: bcc_audit},
        "classes_without_thresholds": dict(sorted(skipped.items())),
        "provenance": {
            CLASS_METALS_FCC: (
                f"evidence copied as-is from {_relpath(Path(args.elastic_baseline_dir))} "
                f"(fcc metals; same files thresholds.v2 was derived from)"
            ),
            CLASS_METALS_BCC: (
                f"evidence copied as-is from {_relpath(Path(args.elastic_baseline_dir))} "
                f"(bcc metals; same files thresholds.v2 was derived from)"
            ),
            CLASS_COVALENT: (
                f"evidence copied as-is from {_relpath(Path(args.elastic_baseline_dir))} "
                f"(Si diamond + Ni3Al L12 + NiAl B2; n=3, no thresholds)"
            ),
            CLASS_IONICS: (
                f"calc_evidence.v1 emitted from {ionics['source_report']} "
                f"(generated_at {ionics['source_generated_at']}) per_model properties"
            ),
            CLASS_PEROVSKITES: (
                f"calc_evidence.v1 emitted from {perovskites['source_report']} "
                f"(generated_at {perovskites['source_generated_at']}) per_model "
                f"properties (raw arm)"
            ),
        },
        "notes": list(THRESHOLD_NOTES),
    }
    thresholds_path = Path(args.thresholds_out)
    thresholds_path.parent.mkdir(parents=True, exist_ok=True)
    thresholds_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    log.info("thresholds.v3 -> %s", thresholds_path)
    log.info("\n%s", render_threshold_table(per_class))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
