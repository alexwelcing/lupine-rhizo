"""Derive the gate-license registry (licenses.v1.json) from measured data.

Turns ``data/discovery_gates/dispersion_vs_error_by_class.json`` (per-class
Spearman rho between cross-model dispersion and median |relative error|)
plus the pooled ``dispersion_vs_error.json`` (recorded as descriptive
context only) into the structured license registry the report runners load
(see ``lupine_distill.statics.licenses`` and the registered design
``docs/design/2026-07-13-gate-license-layer.md``):

* statuses via the registered rule (licensed: rho >= +0.5, n >= 5,
  reference-bound; anti-correlated: rho <= -0.5, n >= 5, reference-bound;
  descriptive: the fail-closed default for everything else),
* the B0 ``license_ceiling`` program override (errata finding 4 / Round-3
  prereg fix 6): B0 concordance descriptive program-wide, while the fcc B0
  anti-correlated warning is preserved (a ceiling caps positive licensing
  only),
* rho/n recorded VERBATIM per entry even when the status ignores them, so
  the reader sees exactly what was refused and why,
* provenance (derived_from paths/schemas/timestamps) and the update
  discipline (reference-bound corpora only; immutable versioned registries;
  upgrades only by registered decision).

Registries are immutable once written: rederivation belongs in
``licenses.v2.json`` etc., so this script refuses to overwrite an existing
output unless ``--force`` is given.

Run (no GPU, no calculators load):
    .venv-mlip312/Scripts/python python/scripts/derive_gate_licenses.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from lupine_distill.statics import InputValidationError  # noqa: E402
from lupine_distill.statics.licenses import (  # noqa: E402
    ANTI_CORRELATED_MAX_RHO,
    CORPUS_IN_SAMPLE,
    CORPUS_REFERENCE_BOUND,
    LICENSED_MIN_RHO,
    LICENSES_SCHEMA_ID,
    LICENSE_MIN_SAMPLES,
    STATUS_ANTI_CORRELATED,
    STATUS_DESCRIPTIVE,
    ceiling_for_property,
    derive_status,
    load_license_registry,
)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("derive_gate_licenses")

BY_CLASS_SCHEMA: Final[str] = "lupine.discovery_gates.dispersion_vs_error_by_class.v1"
POOLED_SCHEMA: Final[str] = "lupine.discovery_gates.dispersion_vs_error.v1"

#: Which by_class ``sources`` key feeds each class, and what kind of corpus
#: it is. The metals rho values are measured on the reference-bound Y-matrix
#: evidence (external references); the perovskite rho values are measured on
#: the Round-1 gated candidates themselves -- the errata-finding-6
#: circularity -- so they are ``in-sample`` and can never confer status.
#: A class absent from this registration falls back to ``in-sample``
#: (fail-closed: unregistered corpora confer nothing).
CORPUS_BY_CLASS: Final[Mapping[str, tuple[str, str]]] = {
    "metals-fcc": ("metals", CORPUS_REFERENCE_BOUND),
    "metals-bcc": ("metals", CORPUS_REFERENCE_BOUND),
    "perovskites": ("perovskites", CORPUS_IN_SAMPLE),
}

MODEL_FAMILY_CAVEAT: Final[str] = (
    "4 models with three non-independent MACE/CHGNet-era variants sharing "
    "training data"
)

IN_SAMPLE_CAVEAT: Final[str] = (
    "circular: rho computed on the gated candidates themselves (errata "
    "finding 6); in-sample data is recorded but confers no status"
)

#: Errata finding 4 / Round-3 prereg fix 6, verbatim from the design.
B0_PROGRAM_OVERRIDE: Final[Mapping[str, str]] = {
    "property": "b0",
    "license_ceiling": STATUS_DESCRIPTIVE,
    "provenance": (
        "2026-07-13 errata finding 4; Round-3 prereg fix 6 (fcc B0 "
        "rho=-0.63): B0 concordance descriptive program-wide"
    ),
    "lift_requires": "registered decision citing new reference-bound evidence",
}

UPDATE_DISCIPLINE: Final[tuple[str, ...]] = (
    "License statuses are (re)derived ONLY from reference-bound corpora "
    "(external, non-null references); corpus_kind 'in-sample' records data "
    "from gated subjects while barring it from conferring status.",
    "Registries are immutable and versioned: rederivation writes "
    "licenses.v2.json, v3, ...; existing files are never mutated, and "
    "reports pin the registry version they used.",
    "Upgrades (descriptive -> licensed) require an out-of-sample "
    "reference-bound corpus, n >= 5, rho >= +0.5, and a derivation "
    "registered BEFORE the new corpus is measured; downgrades are "
    "fail-safe and may be applied as soon as evidence exists.",
    "Program overrides lift only by registered decision citing new "
    "reference-bound evidence.",
    "A gated subject that later acquires external references may join a "
    "future corpus version; the registry entry documents the transition.",
)

_RHO_KEY: Final[str] = "spearman_rho_dispersion_vs_median_rel_error"


def _load_artifact(path: Path, expected_schema: str) -> Mapping[str, object]:
    if not path.is_file():
        raise InputValidationError(f"input artifact does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != expected_schema:
        raise InputValidationError(
            f"{path}: expected schema {expected_schema!r}, got "
            f"{payload.get('schema') if isinstance(payload, Mapping) else payload!r}"
        )
    return payload


def _relativize(path_text: str, root: Path | None) -> str:
    """Repo-relative POSIX form of a recorded source path where possible."""
    if root is None:
        return path_text
    try:
        return Path(path_text).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path_text


def _license_entry(
    class_name: str,
    prop: str,
    rho_entry: Mapping[str, object],
    *,
    corpus: str,
    corpus_kind: str,
    registered_corpus: bool,
    ceiling: str | None,
) -> dict[str, object]:
    if not isinstance(rho_entry, Mapping):
        raise InputValidationError(
            f"by_class[{class_name!r}][{prop!r}] must be an object, got {rho_entry!r}"
        )
    rho_raw = rho_entry.get(_RHO_KEY)
    rho = float(rho_raw) if isinstance(rho_raw, (int, float)) else None
    n_raw = rho_entry.get("n_materials")
    if not isinstance(n_raw, int) or isinstance(n_raw, bool) or n_raw < 0:
        raise InputValidationError(
            f"by_class[{class_name!r}][{prop!r}]: n_materials must be a "
            f"non-negative integer, got {n_raw!r}"
        )
    status = derive_status(rho, n_raw, corpus_kind, ceiling=ceiling)
    caveats: list[str] = [f"n={n_raw}; {MODEL_FAMILY_CAVEAT}"]
    small_n = rho_entry.get("small_n_warning")
    if isinstance(small_n, str) and small_n:
        caveats.append(small_n)
    if not registered_corpus:
        caveats.append(
            "corpus kind unregistered for this class; treated as in-sample "
            "(fail-closed)"
        )
    if corpus_kind == CORPUS_IN_SAMPLE:
        caveats.append(IN_SAMPLE_CAVEAT)
    if ceiling is not None:
        caveats.append(
            f"program override: {prop} license_ceiling={ceiling} caps "
            f"positive licensing (never erases an anti-correlated warning)"
        )
    if status == STATUS_ANTI_CORRELATED:
        caveats.append(
            "low dispersion must NOT be read as low error (errata finding 4)"
        )
    return {
        "status": status,
        "rho": rho,
        "n": n_raw,
        "corpus": corpus,
        "corpus_kind": corpus_kind,
        "caveats": caveats,
    }


def build_registry(
    by_class_payload: Mapping[str, object],
    pooled_payload: Mapping[str, object],
    *,
    by_class_path: str,
    pooled_path: str,
    repo_root: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    """Pure derivation: input artifacts -> licenses.v1 registry payload."""
    by_class = by_class_payload.get("by_class")
    if not isinstance(by_class, Mapping) or not by_class:
        raise InputValidationError(f"{by_class_path}: no 'by_class' mapping")
    sources = by_class_payload.get("sources")
    if not isinstance(sources, Mapping):
        raise InputValidationError(f"{by_class_path}: no 'sources' mapping")
    overrides = [dict(B0_PROGRAM_OVERRIDE)]
    registry_by_class: dict[str, dict[str, object]] = {}
    for class_name in sorted(by_class):
        per_prop = by_class[class_name]
        if not isinstance(per_prop, Mapping):
            raise InputValidationError(
                f"{by_class_path}: by_class[{class_name!r}] must be an object"
            )
        registered = str(class_name) in CORPUS_BY_CLASS
        source_key, corpus_kind = CORPUS_BY_CLASS.get(
            str(class_name), (None, CORPUS_IN_SAMPLE)
        )
        corpus = (
            _relativize(str(sources.get(source_key, "")), repo_root)
            if source_key is not None
            else "unregistered"
        )
        entries: dict[str, object] = {}
        for prop_raw in sorted(per_prop, key=str.lower):
            prop = str(prop_raw).lower()
            if prop in entries:
                raise InputValidationError(
                    f"{by_class_path}: duplicate property {prop!r} in class "
                    f"{class_name!r} after lowercasing"
                )
            entries[prop] = _license_entry(
                str(class_name),
                prop,
                per_prop[prop_raw],
                corpus=corpus,
                corpus_kind=corpus_kind,
                registered_corpus=registered,
                ceiling=ceiling_for_property(overrides, prop),
            )
        registry_by_class[str(class_name)] = entries

    pooled_properties = pooled_payload.get("properties")
    if not isinstance(pooled_properties, Mapping):
        raise InputValidationError(f"{pooled_path}: no 'properties' mapping")
    pooled_context = {
        str(prop): {
            "rho": entry.get(_RHO_KEY),
            "n": entry.get("n_materials"),
        }
        for prop, entry in sorted(pooled_properties.items())
        if isinstance(entry, Mapping)
    }

    return {
        "schema": LICENSES_SCHEMA_ID,
        "generated_at": generated_at
        or datetime.now(timezone.utc).isoformat(),
        "generated_by": "python/scripts/derive_gate_licenses.py",
        "derived_from": {
            "path": _relativize(by_class_path, repo_root),
            "schema": BY_CLASS_SCHEMA,
            "generated_at": str(by_class_payload.get("generated_at", "")),
            "pooled_path": _relativize(pooled_path, repo_root),
            "pooled_schema": POOLED_SCHEMA,
            "pooled_generated_at": str(pooled_payload.get("generated_at", "")),
        },
        "derivation_rule": {
            "rho_metric": _RHO_KEY,
            "licensed_min_rho": LICENSED_MIN_RHO,
            "anti_correlated_max_rho": ANTI_CORRELATED_MAX_RHO,
            "n_min": LICENSE_MIN_SAMPLES,
            "corpus_kind_required_for_status": CORPUS_REFERENCE_BOUND,
            "note": "descriptive is the fail-closed default for every other case",
        },
        "update_discipline": list(UPDATE_DISCIPLINE),
        "program_overrides": overrides,
        "by_class": registry_by_class,
        "pooled_context": {
            "note": (
                "Pooled (all-classes) rho/n from dispersion_vs_error.json, "
                "recorded for context ONLY: pooling masks class-level "
                "structure (the fcc B0 anti-correlation vanishes in the "
                "pooled rho) and confers no status."
            ),
            "corpus": _relativize(
                str(pooled_payload.get("evidence_dir", "")), repo_root
            ),
            "properties": pooled_context,
        },
    }


def render_license_table(registry: Mapping[str, object]) -> str:
    lines = [
        "| class | property | status | rho | n | corpus_kind |",
        "|---|---|---|---|---|---|",
    ]
    for class_name, per_prop in registry["by_class"].items():
        for prop, entry in per_prop.items():
            rho = entry["rho"]
            rho_text = f"{rho:+.3f}" if isinstance(rho, (int, float)) else "-"
            lines.append(
                f"| {class_name} | {prop} | {entry['status']} | {rho_text} "
                f"| {entry['n']} | {entry['corpus_kind']} |"
            )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--by-class",
        default=str(
            _REPO_ROOT / "data" / "discovery_gates" / "dispersion_vs_error_by_class.json"
        ),
        help="Class-stratified dispersion-vs-error artifact",
    )
    parser.add_argument(
        "--pooled",
        default=str(_REPO_ROOT / "data" / "discovery_gates" / "dispersion_vs_error.json"),
        help="Pooled dispersion-vs-error artifact (recorded as context)",
    )
    parser.add_argument(
        "--out",
        default=str(_REPO_ROOT / "data" / "discovery_gates" / "licenses.v1.json"),
        help="Output registry path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing registry (update discipline: prefer a "
        "new version file instead)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        log.error(
            "refusing to overwrite %s: registries are immutable and "
            "versioned (write licenses.v2.json, or pass --force)",
            out_path,
        )
        return 1
    try:
        by_class_payload = _load_artifact(Path(args.by_class), BY_CLASS_SCHEMA)
        pooled_payload = _load_artifact(Path(args.pooled), POOLED_SCHEMA)
        registry = build_registry(
            by_class_payload,
            pooled_payload,
            by_class_path=Path(args.by_class).as_posix(),
            pooled_path=Path(args.pooled).as_posix(),
            repo_root=_REPO_ROOT,
        )
    except InputValidationError as exc:
        log.error("derivation failed: %s", exc)
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    try:
        load_license_registry(out_path)  # round-trip: never ship a bad registry
    except InputValidationError as exc:
        out_path.unlink(missing_ok=True)
        log.error("generated registry failed validation (removed): %s", exc)
        return 1
    log.info("\n%s", render_license_table(registry))
    log.info("-> %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
