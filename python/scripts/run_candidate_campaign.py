"""Round-1 unbiased-accuracy candidate campaign: MLIP leg + Lupine de-bias arm.

For each target candidate (fcc random solid solution or cubic perovskite) x
model this runner:

1. builds the structure (RSS supercell via
   :func:`lupine_distill.statics.build_rss_supercell` at a Vegard guess, or
   the 5-atom perovskite cell via ``build_structure``),
2. relaxes the lattice with a cubic, cell-based E-V scan (recentring +
   BM3 fit, mirroring ``statics.ev_relax`` but on the supplied ``Atoms`` --
   the formula-based ``compute_lattice``/``compute_eos`` cannot accept RSS
   cells), giving a0 (conventional-cell Angstrom), B0, and E per atom,
3. measures cubic C11/C12/C44 on the relaxed cell with the same symmetric
   FD stress-strain probe as ``compute_cubic_elastic_constants``
   (relaxed-ion), which likewise only accepts (formula, structure_type),
4. gates: per-model Born stability, cross-model concordance per property
   (thresholds loaded from --thresholds-file), and optional dynamic-return
   on the relaxed cell of one designated model,
5. de-biases raw values with per-model calibration biases from --bias-file
   (``corrected = raw / bias[model][property][class]``); a missing bias
   leaves the value raw and marks it uncorrected.

Outputs: <out-dir>/report.json + REPORT.md with per-candidate property
tables (reference | per-model raw | per-model corrected | concordance |
Born | verdict) and arm-level metrics (median/mean |rel err| raw vs
corrected per property per group, risk-coverage).

Run (Python 3.12 GPU venv):
    .venv-mlip312/Scripts/python python/scripts/run_candidate_campaign.py \
        --device cuda
"""

from __future__ import annotations

# Dynamo OFF before any torch import (no Triton on Windows); CLI only.
import os

os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")

import argparse
import json
import logging
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Mapping

import numpy as np
from ase import Atoms

_HERE = Path(__file__).resolve()
for _p in (str(_HERE.parent), str(_HERE.parents[1]), str(_HERE.parents[2])):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_REPO_ROOT = _HERE.parents[2]

from run_discovery_gates import (  # noqa: E402
    DEFAULT_MODELS,
    MODEL_REGISTRY,
    build_calculator,
)

from lupine_distill.statics import (  # noqa: E402
    ConcordanceThresholds,
    ConvergenceError,
    InputValidationError,
    StaticsError,
    born_stability_cubic,
    build_rss_supercell,
    build_structure,
    concordance,
    dynamic_return,
    estimate_lattice_constant,
    estimate_rss_lattice_constant,
    fit_birch_murnaghan,
    relax_positions,
    scan_energy_volume,
)
from lupine_distill.statics.elastic import (  # noqa: E402
    DEFAULT_ELASTIC_FMAX,
    DEFAULT_ELASTIC_MAX_STEPS,
    DEFAULT_ELASTIC_OPTIMIZER,
    DEFAULT_STRAIN_DELTA,
    _strained_stress_voigt,
    validate_strain_delta,
)
from lupine_distill.statics.eos import BirchMurnaghanFit  # noqa: E402
from lupine_distill.statics.units import EV_PER_A3_TO_GPA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("candidate_campaign")

REPORT_SCHEMA: Final[str] = "lupine.candidate_campaign.v1"
CAMPAIGN_PROPERTIES: Final[tuple[str, ...]] = ("a0", "b0", "c11", "c12", "c44")
TARGET_STRUCTURE_TYPES: Final[tuple[str, ...]] = ("fcc-rss", "perovskite")

#: Calibration class used to pick the de-bias factor, per structure type.
BIAS_CLASS_BY_STRUCTURE: Final[Mapping[str, str]] = {
    "fcc-rss": "fcc-metals",
    "perovskite": "all-21",
}

DEFAULT_DYNAMIC_MODEL: Final[str] = "mace-mp-medium"
_EV_VOLUME_SPAN: Final[float] = 0.06
_EV_N_POINTS: Final[int] = 11
_EV_MAX_RECENTER: Final[int] = 8


# --------------------------------------------------------------------------
# targets
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """One validated campaign target."""

    id: str
    group: str
    formula: str
    structure_type: str
    composition: tuple[tuple[str, int], ...]
    lattice_guess_angstrom: float | None
    references: tuple[tuple[str, float | None], ...]

    def composition_dict(self) -> dict[str, int]:
        return dict(self.composition)

    def reference(self, prop: str) -> float | None:
        return dict(self.references).get(prop)


def _reference_value(entry: object, candidate_id: str, prop: str) -> float | None:
    if entry is None:
        return None
    if not isinstance(entry, Mapping) or "value" not in entry:
        raise InputValidationError(
            f"candidate {candidate_id!r}: references.{prop} must be null or an "
            f"object with a 'value' key, got {entry!r}"
        )
    value = entry["value"]
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(
        float(value)
    ):
        raise InputValidationError(
            f"candidate {candidate_id!r}: references.{prop}.value must be a "
            f"finite number, got {value!r}"
        )
    return float(value)


def load_targets(path: Path) -> tuple[Candidate, ...]:
    """Load and validate the round-1 targets file."""
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"targets file does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read targets file {path}: {exc}") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("candidates"), list):
        raise InputValidationError(f"{path}: expected an object with a 'candidates' list")
    candidates: list[Candidate] = []
    seen_ids: set[str] = set()
    for raw in payload["candidates"]:
        if not isinstance(raw, Mapping):
            raise InputValidationError(f"{path}: candidate entries must be objects")
        cid = str(raw.get("id", "")).strip()
        if not cid:
            raise InputValidationError(f"{path}: every candidate needs a non-empty id")
        if cid in seen_ids:
            raise InputValidationError(f"{path}: duplicate candidate id {cid!r}")
        seen_ids.add(cid)
        structure_type = str(raw.get("structure_type", "")).strip()
        if structure_type not in TARGET_STRUCTURE_TYPES:
            raise InputValidationError(
                f"candidate {cid!r}: structure_type must be one of "
                f"{TARGET_STRUCTURE_TYPES}, got {structure_type!r}"
            )
        composition = raw.get("composition") or {}
        if not isinstance(composition, Mapping):
            raise InputValidationError(
                f"candidate {cid!r}: composition must be a mapping"
            )
        if structure_type == "fcc-rss" and not composition:
            raise InputValidationError(
                f"candidate {cid!r}: fcc-rss candidates need a composition"
            )
        formula = str(raw.get("formula", "")).strip()
        if structure_type == "perovskite" and not formula:
            raise InputValidationError(
                f"candidate {cid!r}: perovskite candidates need a formula"
            )
        guess = raw.get("lattice_guess_angstrom")
        if guess is not None:
            if not isinstance(guess, (int, float)) or isinstance(guess, bool) or not (
                math.isfinite(float(guess)) and float(guess) > 0.0
            ):
                raise InputValidationError(
                    f"candidate {cid!r}: lattice_guess_angstrom must be a "
                    f"positive finite number or null, got {guess!r}"
                )
            guess = float(guess)
        references_raw = raw.get("references") or {}
        if not isinstance(references_raw, Mapping):
            raise InputValidationError(
                f"candidate {cid!r}: references must be a mapping"
            )
        unknown = sorted(set(references_raw) - set(CAMPAIGN_PROPERTIES))
        if unknown:
            raise InputValidationError(
                f"candidate {cid!r}: unknown reference properties {unknown}; "
                f"known: {list(CAMPAIGN_PROPERTIES)}"
            )
        references = tuple(
            (prop, _reference_value(references_raw.get(prop), cid, prop))
            for prop in CAMPAIGN_PROPERTIES
        )
        candidates.append(
            Candidate(
                id=cid,
                group=str(raw.get("group", "")).strip() or "ungrouped",
                formula=formula,
                structure_type=structure_type,
                composition=tuple((str(k), int(v)) for k, v in composition.items()),
                lattice_guess_angstrom=guess,
                references=references,
            )
        )
    if not candidates:
        raise InputValidationError(f"{path}: candidates list is empty")
    return tuple(candidates)


# --------------------------------------------------------------------------
# thresholds + biases
# --------------------------------------------------------------------------


def load_thresholds_file(path: Path) -> dict[str, ConcordanceThresholds]:
    """Reconstruct per-property ConcordanceThresholds from a thresholds JSON.

    Accepts the ``lupine.discovery_gates.thresholds.v2`` artifact layout
    (top-level ``per_property``) and validates all campaign properties are
    covered.
    """
    path = Path(path)
    if not path.is_file():
        raise InputValidationError(f"thresholds file does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read thresholds file {path}: {exc}") from exc
    per_property = payload.get("per_property") if isinstance(payload, Mapping) else None
    if not isinstance(per_property, Mapping):
        raise InputValidationError(
            f"{path}: expected a 'per_property' mapping (thresholds.v2 layout)"
        )
    thresholds: dict[str, ConcordanceThresholds] = {}
    for prop in CAMPAIGN_PROPERTIES:
        entry = per_property.get(prop)
        if not isinstance(entry, Mapping):
            raise InputValidationError(
                f"{path}: per_property is missing campaign property {prop!r}"
            )
        try:
            thresholds[prop] = ConcordanceThresholds(
                flag=float(entry["flag"]),
                refuse=float(entry["refuse"]),
                flag_percentile=float(entry["flag_percentile"]),
                refuse_percentile=float(entry["refuse_percentile"]),
                n_samples=int(entry["n_samples"]),
                source=str(entry["source"]),
                sample_dispersions=tuple(
                    (str(label), float(value))
                    for label, value in entry.get("sample_dispersions", [])
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InputValidationError(
                f"{path}: malformed thresholds entry for {prop!r}: {exc}"
            ) from exc
    return thresholds


def load_bias_file(path: Path | None) -> tuple[dict[str, object], str]:
    """Load ``model_biases.v1`` biases; returns ``(biases, provenance_note)``.

    A missing file is not an error: the campaign then runs fully
    uncorrected (every corrected value equals raw, marked uncorrected).
    """
    if path is None:
        return {}, "no bias file supplied; all values uncorrected"
    path = Path(path)
    if not path.is_file():
        return {}, f"bias file not found ({path.as_posix()}); all values uncorrected"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"cannot read bias file {path}: {exc}") from exc
    if not isinstance(payload, Mapping) or not isinstance(payload.get("biases"), Mapping):
        raise InputValidationError(
            f"{path}: expected a model_biases.v1 artifact with a 'biases' mapping"
        )
    note = (
        f"biases from {path.as_posix()} (schema {payload.get('schema')}); "
        f"cij available: {payload.get('cij', {}).get('available', False)}"
    )
    return dict(payload["biases"]), note


def apply_bias(
    raw: float,
    model: str,
    prop: str,
    class_key: str,
    biases: Mapping[str, object],
) -> tuple[float, bool]:
    """``corrected = raw / bias[model][prop][class]``; raw when bias missing.

    Returns ``(corrected_value, was_corrected)``.
    """
    per_model = biases.get(model)
    per_prop = per_model.get(prop) if isinstance(per_model, Mapping) else None
    bias = per_prop.get(class_key) if isinstance(per_prop, Mapping) else None
    if (
        isinstance(bias, (int, float))
        and not isinstance(bias, bool)
        and math.isfinite(float(bias))
        and float(bias) > 0.0
    ):
        return raw / float(bias), True
    return raw, False


# --------------------------------------------------------------------------
# cell-based measurement (RSS cells cannot go through the formula-based API)
# --------------------------------------------------------------------------


def build_candidate_atoms(
    candidate: Candidate, repeat: int, seed: int
) -> tuple[Atoms, int, float]:
    """Initial structure for a candidate; returns ``(atoms, n_conv_cells, a_guess)``."""
    if candidate.structure_type == "fcc-rss":
        composition = candidate.composition_dict()
        a_guess = (
            candidate.lattice_guess_angstrom
            if candidate.lattice_guess_angstrom is not None
            else estimate_rss_lattice_constant(composition, "fcc")
        )
        atoms = build_rss_supercell(composition, "fcc", a_guess, repeat, seed)
        return atoms, repeat**3, a_guess
    a_guess = (
        candidate.lattice_guess_angstrom
        if candidate.lattice_guess_angstrom is not None
        else estimate_lattice_constant(candidate.formula, "perovskite")
    )
    atoms = build_structure(candidate.formula, "perovskite", a_guess)
    return atoms, 1, a_guess


def _rescaled_to_volume(atoms: Atoms, v_target: float) -> Atoms:
    """Copy of ``atoms`` isotropically rescaled to total volume ``v_target``."""
    work = atoms.copy()
    factor = (v_target / atoms.get_volume()) ** (1.0 / 3.0)
    work.set_cell(atoms.get_cell().array * factor, scale_atoms=True)
    return work


def relax_cell_ev(
    calculator: object,
    atoms: Atoms,
    *,
    volume_span: float = _EV_VOLUME_SPAN,
    n_points: int = _EV_N_POINTS,
    max_recenter: int = _EV_MAX_RECENTER,
    relax_internal_first: bool = True,
    fmax: float = 0.02,
    optimizer: str = "FIRE",
    max_steps: int = 500,
) -> tuple[BirchMurnaghanFit, Atoms]:
    """Cubic E-V relaxation of a supplied cell; returns ``(fit, relaxed_atoms)``.

    Mirrors ``statics.ev_relax.relax_lattice`` (recentring scan -> BM3 fit ->
    one refinement pass centred on the fitted minimum) but operates on the
    given ``Atoms`` directly by isotropic cell rescaling, because the
    formula-based path cannot represent RSS supercells. For disordered cells
    the internal coordinates are first relaxed once at the starting volume
    (``relax_internal_first``); the E-V scan itself is clamped-ion, exactly
    like ``eos.scan_energy_volume``.
    """
    work = atoms.copy()
    if relax_internal_first:
        work, _, _ = relax_positions(
            work, calculator, fmax=fmax, optimizer=optimizer, max_steps=max_steps
        )
    label = atoms.get_chemical_formula()
    for _ in range(max_recenter + 1):
        volumes, energies = scan_energy_volume(work, calculator, volume_span, n_points)
        idx = int(np.argmin(energies))
        if 0 < idx < len(energies) - 1:
            fit = fit_birch_murnaghan(volumes, energies)
            refined_start = _rescaled_to_volume(work, fit.v0_a3)
            volumes_r, energies_r = scan_energy_volume(
                refined_start, calculator, volume_span, n_points
            )
            idx_r = int(np.argmin(energies_r))
            if not 0 < idx_r < len(energies_r) - 1:
                raise ConvergenceError(
                    f"refinement E-V scan for {label} centred at the fitted "
                    f"minimum V={fit.v0_a3:.2f} A^3 does not bracket it; "
                    f"energy surface inconsistent"
                )
            refined = fit_birch_murnaghan(volumes_r, energies_r)
            return refined, _rescaled_to_volume(work, refined.v0_a3)
        work = _rescaled_to_volume(work, float(volumes[idx]))
    raise ConvergenceError(
        f"E-V scan for {label} failed to bracket a minimum after "
        f"{max_recenter} recenterings"
    )


def cubic_elastic_from_atoms(
    calculator: object,
    atoms: Atoms,
    *,
    delta: float = DEFAULT_STRAIN_DELTA,
    relax_internal: bool = True,
    fmax: float = DEFAULT_ELASTIC_FMAX,
    optimizer: str = DEFAULT_ELASTIC_OPTIMIZER,
    max_steps: int = DEFAULT_ELASTIC_MAX_STEPS,
) -> dict[str, float]:
    """Cubic C11/C12/C44 (GPa) by symmetric FD stress-strain on ``atoms``.

    Replicates the probe of ``compute_cubic_elastic_constants`` (same delta
    semantics, same Voigt convention, same relax_internal meaning) on a
    caller-supplied cell -- the library function only accepts
    ``(formula, structure_type)`` prototypes and cannot take an RSS cell.
    """
    d = validate_strain_delta(delta)

    def stress_at(eps: np.ndarray) -> tuple[np.ndarray, int]:
        return _strained_stress_voigt(
            calculator,
            atoms,
            eps,
            relax_internal=relax_internal,
            fmax=fmax,
            optimizer=optimizer,
            max_steps=max_steps,
        )

    eps_xx = np.zeros((3, 3))
    eps_xx[0, 0] = d
    eps_yz = np.zeros((3, 3))
    eps_yz[1, 2] = eps_yz[2, 1] = d

    s_xx_plus, n1 = stress_at(eps_xx)
    s_xx_minus, n2 = stress_at(-eps_xx)
    s_yz_plus, n3 = stress_at(eps_yz)
    s_yz_minus, n4 = stress_at(-eps_yz)

    c11 = (s_xx_plus[0] - s_xx_minus[0]) / (2.0 * d) * EV_PER_A3_TO_GPA
    c12 = (
        (s_xx_plus[1] - s_xx_minus[1]) + (s_xx_plus[2] - s_xx_minus[2])
    ) / (4.0 * d) * EV_PER_A3_TO_GPA
    c44 = (s_yz_plus[3] - s_yz_minus[3]) / (4.0 * d) * EV_PER_A3_TO_GPA
    for name, value in (("C11", c11), ("C12", c12), ("C44", c44)):
        if not math.isfinite(float(value)):
            raise ConvergenceError(f"{name} is non-finite for {atoms.get_chemical_formula()}")
    return {
        "c11_gpa": float(c11),
        "c12_gpa": float(c12),
        "c44_gpa": float(c44),
        "n_relax_steps_total": int(n1 + n2 + n3 + n4),
    }


def measure_candidate(
    calculator: object,
    candidate: Candidate,
    *,
    repeat: int,
    seed: int,
    delta: float,
) -> tuple[dict[str, object], Atoms]:
    """Full raw measurement of one candidate with one model.

    Returns ``(record, relaxed_atoms)``; the relaxed cell feeds the optional
    dynamic-return gate.
    """
    atoms, n_conv_cells, a_guess = build_candidate_atoms(candidate, repeat, seed)
    t0 = time.perf_counter()
    fit, relaxed = relax_cell_ev(calculator, atoms)
    t_relax = time.perf_counter() - t0
    a0 = (fit.v0_a3 / n_conv_cells) ** (1.0 / 3.0)
    e0_per_atom = fit.e0_ev / len(relaxed)
    log.info("  a0 = %.4f A, B0 = %.1f GPa (%.1fs)", a0, fit.b0_gpa, t_relax)
    t1 = time.perf_counter()
    elastic = cubic_elastic_from_atoms(calculator, relaxed, delta=delta)
    t_elastic = time.perf_counter() - t1
    born = born_stability_cubic(
        elastic["c11_gpa"], elastic["c12_gpa"], elastic["c44_gpa"]
    )
    log.info(
        "  C11 = %.1f, C12 = %.1f, C44 = %.1f GPa (%.1fs); Born: %s",
        elastic["c11_gpa"],
        elastic["c12_gpa"],
        elastic["c44_gpa"],
        t_elastic,
        "PASS" if born.passed else f"FAIL ({born.detail})",
    )
    record = {
        "properties": {
            "a0": a0,
            "b0": fit.b0_gpa,
            "c11": elastic["c11_gpa"],
            "c12": elastic["c12_gpa"],
            "c44": elastic["c44_gpa"],
        },
        "e0_ev_per_atom": e0_per_atom,
        "b0_prime": fit.b0_prime,
        "n_atoms": len(relaxed),
        "n_conventional_cells": n_conv_cells,
        "a_guess_angstrom": a_guess,
        "elastic_n_relax_steps": elastic["n_relax_steps_total"],
        "gates": {"born": born.to_dict()},
        "born_passed": born.passed,
        "wall_time_seconds": {"ev_relax": t_relax, "elastic_plus_born": t_elastic},
    }
    return record, relaxed


# --------------------------------------------------------------------------
# de-bias arm + verdicts + metrics (pure functions, unit-testable)
# --------------------------------------------------------------------------


def corrected_arm(
    per_model: Mapping[str, Mapping[str, object]],
    structure_type: str,
    biases: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Per-model corrected values for one candidate.

    ``corrected[model][prop] = {"value": raw/bias, "corrected": bool}``;
    models with measurement errors are omitted.
    """
    class_key = BIAS_CLASS_BY_STRUCTURE[structure_type]
    arm: dict[str, dict[str, object]] = {}
    for model, record in per_model.items():
        if "error" in record:
            continue
        per_prop: dict[str, object] = {"bias_class": class_key, "values": {}}
        for prop in CAMPAIGN_PROPERTIES:
            raw = float(record["properties"][prop])
            value, was_corrected = apply_bias(raw, model, prop, class_key, biases)
            per_prop["values"][prop] = {"value": value, "corrected": was_corrected}
        arm[model] = per_prop
    return arm


def candidate_verdict(candidate_report: Mapping[str, object]) -> str:
    """REFUSED / FLAGGED / CERTIFIED from the recorded gate outcomes."""
    per_model = candidate_report["per_model"]
    failures = [m for m, r in per_model.items() if "error" in r]
    born_fails = [
        m for m, r in per_model.items() if "error" not in r and not r["born_passed"]
    ]
    levels = {
        prop: gate["values"]["level"]
        for prop, gate in candidate_report["gates"].get("concordance", {}).items()
    }
    refusals = [p for p, level in levels.items() if level == "refuse"]
    flags = [p for p, level in levels.items() if level == "flag"]
    dynamic = candidate_report["gates"].get("dynamic_return")
    dynamic_failed = dynamic is not None and not dynamic["passed"]
    if failures or born_fails or refusals or dynamic_failed:
        return "REFUSED"
    if flags:
        return "FLAGGED"
    return "CERTIFIED"


def arm_error_metrics(
    candidates_report: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, dict[str, object]]]:
    """Median/mean |relative error| raw vs corrected, per group per property.

    Errors pool over (candidate, model) cells where the candidate carries a
    non-null reference for the property and the model measurement succeeded.
    Groups also aggregate into a synthetic "all" group.
    """
    pools: dict[tuple[str, str], dict[str, list[float]]] = {}

    def _push(group: str, prop: str, kind: str, err: float) -> None:
        pools.setdefault((group, prop), {"raw": [], "corrected": []})[kind].append(err)

    for report in candidates_report.values():
        group = str(report["group"])
        references = report["references"]
        arm = report["corrected_arm"]
        for prop in CAMPAIGN_PROPERTIES:
            ref = references.get(prop)
            if ref is None or float(ref) == 0.0:
                continue
            for model, record in report["per_model"].items():
                if "error" in record:
                    continue
                raw = float(record["properties"][prop])
                corrected = float(arm[model]["values"][prop]["value"])
                for g in (group, "all"):
                    _push(g, prop, "raw", abs(raw - ref) / abs(ref))
                    _push(g, prop, "corrected", abs(corrected - ref) / abs(ref))

    metrics: dict[str, dict[str, dict[str, object]]] = {}
    for (group, prop), kinds in sorted(pools.items()):
        entry: dict[str, object] = {"n_cells": len(kinds["raw"])}
        for kind, errors in kinds.items():
            entry[f"median_abs_rel_err_{kind}"] = float(np.median(errors))
            entry[f"mean_abs_rel_err_{kind}"] = float(np.mean(errors))
        metrics.setdefault(group, {})[prop] = entry
    return metrics


def risk_coverage(candidates_report: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    """Issued-vs-refused summary over the candidate panel."""
    verdicts = [str(r["verdict"]) for r in candidates_report.values()]
    n = len(verdicts)
    n_refused = verdicts.count("REFUSED")
    issued = n - n_refused
    return {
        "n_candidates": n,
        "n_certified": verdicts.count("CERTIFIED"),
        "n_flagged": verdicts.count("FLAGGED"),
        "n_refused": n_refused,
        "n_issued": issued,
        "coverage_issued_fraction": issued / n if n else 0.0,
    }


# --------------------------------------------------------------------------
# report assembly + rendering
# --------------------------------------------------------------------------


def assemble_report(
    *,
    candidates: tuple[Candidate, ...],
    per_candidate_models: Mapping[str, Mapping[str, Mapping[str, object]]],
    dynamic_gates: Mapping[str, Mapping[str, object]],
    thresholds: Mapping[str, ConcordanceThresholds],
    biases: Mapping[str, object],
    bias_note: str,
    models: list[str],
    parameters: Mapping[str, object],
) -> dict[str, object]:
    """Pure report assembly from measured records (no I/O, unit-testable)."""
    candidates_report: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        per_model = dict(per_candidate_models.get(candidate.id, {}))
        ok_models = {m: r for m, r in per_model.items() if "error" not in r}
        gates: dict[str, object] = {}
        concordance_gates: dict[str, object] = {}
        if len(ok_models) >= 2:
            for prop in CAMPAIGN_PROPERTIES:
                values_by_model = {
                    m: float(r["properties"][prop]) for m, r in ok_models.items()
                }
                concordance_gates[prop] = concordance(
                    prop, values_by_model, thresholds[prop]
                ).to_dict()
        gates["concordance"] = concordance_gates
        gates["born_aggregate"] = {
            "passed": bool(ok_models)
            and all(r["born_passed"] for r in ok_models.values()),
            "per_model": {m: r["born_passed"] for m, r in ok_models.items()},
        }
        if candidate.id in dynamic_gates:
            gates["dynamic_return"] = dict(dynamic_gates[candidate.id])
        report = {
            "group": candidate.group,
            "formula": candidate.formula,
            "structure_type": candidate.structure_type,
            "composition": candidate.composition_dict(),
            "references": dict(candidate.references),
            "per_model": per_model,
            "corrected_arm": corrected_arm(per_model, candidate.structure_type, biases),
            "gates": gates,
        }
        report["verdict"] = candidate_verdict(report)
        candidates_report[candidate.id] = report

    return {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "parameters": dict(parameters),
        "concordance_thresholds": {
            prop: thresholds[prop].to_dict() for prop in CAMPAIGN_PROPERTIES
        },
        "bias_provenance": bias_note,
        "candidates": candidates_report,
        "arm_metrics": {
            "abs_rel_error_by_group_property": arm_error_metrics(candidates_report),
            "risk_coverage": risk_coverage(candidates_report),
        },
    }


def _fmt(value: float | None, digits: int = 4) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def render_markdown(report: Mapping[str, object]) -> str:
    models: list[str] = list(report["models"])
    lines: list[str] = [
        "# Round-1 candidate campaign - raw vs Lupine-corrected",
        "",
        f"Generated: {report['generated_at']} | models: {', '.join(models)}",
        "",
        f"Bias arm: {report['bias_provenance']}",
        "",
        "## Concordance thresholds",
        "",
        "| property | flag | refuse | baseline n |",
        "|---|---|---|---|",
    ]
    for prop, t in report["concordance_thresholds"].items():
        lines.append(f"| {prop} | {t['flag']:.4f} | {t['refuse']:.4f} | {t['n_samples']} |")
    lines.append("")
    for cid, sub in report["candidates"].items():
        born = sub["gates"]["born_aggregate"]
        lines += [
            f"## {cid} - **{sub['verdict']}**",
            "",
            f"group: {sub['group']} | structure: {sub['structure_type']} | "
            f"formula: {sub['formula'] or '-'} | Born aggregate: "
            f"{'PASS' if born['passed'] else 'FAIL'}",
            "",
            "| property | reference | "
            + " | ".join(f"{m} raw" for m in models)
            + " | "
            + " | ".join(f"{m} corr" for m in models)
            + " | concordance |",
            "|---" * (2 + 2 * len(models) + 1) + "|",
        ]
        references = sub["references"]
        arm = sub["corrected_arm"]
        for prop in CAMPAIGN_PROPERTIES:
            raw_cells = []
            corr_cells = []
            for model in models:
                record = sub["per_model"].get(model, {})
                if "error" in record or "properties" not in record:
                    raw_cells.append("ERR")
                    corr_cells.append("ERR")
                    continue
                raw_cells.append(_fmt(float(record["properties"][prop])))
                corrected = arm[model]["values"][prop]
                mark = "" if corrected["corrected"] else " (uncorr)"
                corr_cells.append(_fmt(float(corrected["value"])) + mark)
            gate = sub["gates"]["concordance"].get(prop)
            level = str(gate["values"]["level"]).upper() if gate else "-"
            lines.append(
                f"| {prop} | {_fmt(references.get(prop))} | "
                + " | ".join(raw_cells)
                + " | "
                + " | ".join(corr_cells)
                + f" | {level} |"
            )
        dynamic = sub["gates"].get("dynamic_return")
        if dynamic is not None:
            dv = dynamic["values"]
            lines += [
                "",
                f"dynamic_return: {'PASS' if dynamic['passed'] else 'FAIL'} "
                f"(dE={dv.get('energy_delta_ev_per_atom', float('nan')):.2e} eV/atom, "
                f"max disp={dv.get('max_displacement_a', float('nan')):.3f} A, "
                f"{dv['n_atoms']} atoms)",
            ]
        errors = {
            m: r["error"] for m, r in sub["per_model"].items() if "error" in r
        }
        for model, message in errors.items():
            lines.append(f"- measurement error ({model}): {message[:160]}")
        lines.append("")
    metrics = report["arm_metrics"]["abs_rel_error_by_group_property"]
    lines += [
        "## Arm metrics: |relative error| vs references (raw vs corrected)",
        "",
        "| group | property | n cells | median raw | median corr | mean raw | mean corr |",
        "|---|---|---|---|---|---|---|",
    ]
    for group, per_prop in metrics.items():
        for prop, entry in per_prop.items():
            lines.append(
                f"| {group} | {prop} | {entry['n_cells']} | "
                f"{entry['median_abs_rel_err_raw'] * 100:.2f}% | "
                f"{entry['median_abs_rel_err_corrected'] * 100:.2f}% | "
                f"{entry['mean_abs_rel_err_raw'] * 100:.2f}% | "
                f"{entry['mean_abs_rel_err_corrected'] * 100:.2f}% |"
            )
    coverage = report["arm_metrics"]["risk_coverage"]
    lines += [
        "",
        "## Risk-coverage",
        "",
        f"- candidates: {coverage['n_candidates']}",
        f"- certified: {coverage['n_certified']}, flagged: {coverage['n_flagged']}, "
        f"refused: {coverage['n_refused']}",
        f"- issued (certified+flagged): {coverage['n_issued']} "
        f"({coverage['coverage_issued_fraction'] * 100:.0f}% coverage)",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--targets",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1_targets.json"),
        help="Round-1 targets JSON",
    )
    parser.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    parser.add_argument(
        "--models",
        default=",".join(DEFAULT_MODELS),
        help=f"Comma-separated model ids (default: {','.join(DEFAULT_MODELS)})",
    )
    parser.add_argument(
        "--out-dir",
        default=str(_REPO_ROOT / "data" / "candidates" / "round1"),
        help="Output directory for report.json / REPORT.md",
    )
    parser.add_argument("--seed", type=int, default=42, help="RSS + rattle seed")
    parser.add_argument(
        "--repeat", type=int, default=2, help="RSS supercell repeat (fcc-rss targets)"
    )
    parser.add_argument(
        "--thresholds-file",
        default=str(_REPO_ROOT / "data" / "discovery_gates" / "thresholds.v2.json"),
        help="Per-property concordance thresholds artifact",
    )
    parser.add_argument(
        "--bias-file",
        default=str(_REPO_ROOT / "data" / "candidates" / "model_biases.v1.json"),
        help="model_biases.v1 artifact from derive_model_biases.py "
        "(missing file -> uncorrected arm)",
    )
    parser.add_argument(
        "--dynamic-model",
        default=DEFAULT_DYNAMIC_MODEL,
        help="Model used for the dynamic-return gate (must be in --models)",
    )
    parser.add_argument(
        "--skip-dynamic", action="store_true", help="Skip the dynamic-return gate"
    )
    parser.add_argument("--delta", type=float, default=0.5e-2, help="Elastic FD strain")
    parser.add_argument("--rattle", type=float, default=0.05, help="Rattle stdev (A)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    if not models:
        raise SystemExit("--models must name at least one model")
    unknown = [m for m in models if m not in MODEL_REGISTRY]
    if unknown:
        raise SystemExit(f"unknown model id(s): {unknown}")
    if not args.skip_dynamic and args.dynamic_model not in models:
        raise SystemExit(
            f"--dynamic-model {args.dynamic_model!r} must be one of --models {models}"
        )
    if args.repeat < 1:
        raise SystemExit("--repeat must be >= 1")

    try:
        candidates = load_targets(Path(args.targets))
        thresholds = load_thresholds_file(Path(args.thresholds_file))
        biases, bias_note = load_bias_file(Path(args.bias_file) if args.bias_file else None)
    except InputValidationError as exc:
        raise SystemExit(str(exc)) from exc
    log.info(
        "campaign: %d candidates x %d models; %s", len(candidates), len(models), bias_note
    )

    per_candidate_models: dict[str, dict[str, dict[str, object]]] = {
        c.id: {} for c in candidates
    }
    dynamic_gates: dict[str, dict[str, object]] = {}
    calculator_versions: dict[str, str] = {}
    t_run0 = time.perf_counter()
    for model_id in models:
        log.info("loading %s on %s ...", model_id, args.device)
        calculator, version = build_calculator(model_id, args.device)
        calculator_versions[model_id] = version
        log.info("calculator ready: %s", version)
        for candidate in candidates:
            log.info("%s x %s", candidate.id, model_id)
            try:
                record, relaxed = measure_candidate(
                    calculator,
                    candidate,
                    repeat=args.repeat,
                    seed=args.seed,
                    delta=args.delta,
                )
            except StaticsError as exc:
                log.info("  MEASUREMENT FAILED: %s", exc)
                per_candidate_models[candidate.id][model_id] = {
                    "error": f"{type(exc).__name__}: {exc}"
                }
                continue
            per_candidate_models[candidate.id][model_id] = record
            if not args.skip_dynamic and model_id == args.dynamic_model:
                log.info(
                    "  dynamic_return: rattle %.3f A, seed %d, %d atoms ...",
                    args.rattle,
                    args.seed,
                    len(relaxed),
                )
                verdict = dynamic_return(
                    calculator,
                    relaxed,
                    rattle_amplitude=args.rattle,
                    seed=args.seed,
                )
                log.info(
                    "  dynamic_return: %s (%.1fs)",
                    "PASS" if verdict.passed else "FAIL",
                    verdict.wall_time_seconds,
                )
                dynamic_gates[candidate.id] = verdict.to_dict()
        del calculator  # release GPU memory before the next model loads

    parameters = {
        "targets": Path(args.targets).as_posix(),
        "device": args.device,
        "seed": args.seed,
        "repeat": args.repeat,
        "elastic_delta": args.delta,
        "elastic_relax_internal": True,
        "rattle_amplitude_a": args.rattle,
        "dynamic_model": None if args.skip_dynamic else args.dynamic_model,
        "skip_dynamic": bool(args.skip_dynamic),
        "thresholds_file": Path(args.thresholds_file).as_posix(),
        "bias_file": Path(args.bias_file).as_posix() if args.bias_file else None,
        "calculator_versions": calculator_versions,
        "ev_scan": {
            "volume_span": _EV_VOLUME_SPAN,
            "n_points": _EV_N_POINTS,
            "max_recenter": _EV_MAX_RECENTER,
        },
    }
    report = assemble_report(
        candidates=candidates,
        per_candidate_models=per_candidate_models,
        dynamic_gates=dynamic_gates,
        thresholds=thresholds,
        biases=biases,
        bias_note=bias_note,
        models=models,
        parameters=parameters,
    )
    report["total_wall_time_seconds"] = time.perf_counter() - t_run0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_json = out_dir / "report.json"
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_md = out_dir / "REPORT.md"
    report_md.write_text(render_markdown(report), encoding="utf-8")
    for cid, sub in report["candidates"].items():
        log.info("%s -> %s", cid, sub["verdict"])
    log.info("report -> %s ; %s", report_json, report_md)
    log.info("total wall time: %.1f s", report["total_wall_time_seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
