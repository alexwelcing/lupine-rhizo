"""Reference-free discovery gates for new/unproven crystal structures.

Every gate returns a frozen :class:`GateVerdict` (passed flag, measured
values, explicit criteria with provenance, human-readable detail). Honesty
rules for thresholds:

* **Born stability** is exact physics: the necessary mechanical-stability
  conditions of a cubic lattice under zero external stress (M. Born &
  K. Huang, *Dynamical Theory of Crystal Lattices*, 1954; F. Mouhat &
  F.-X. Coudert, Phys. Rev. B 90, 224104 (2014)).
* **Concordance** thresholds are never invented: they are percentiles of a
  *measured* cross-model dispersion distribution (see
  :func:`derive_concordance_thresholds`), with the source recorded in the
  verdict.
* **Dynamic return** is a finite-rattle basin-return probe — NOT a phonon
  calculation — and says so in its verdict detail.
* **Facet ordering** gates only on surface-energy positivity (exact:
  a negative gamma means the crystal cleaves spontaneously); the ordering
  itself is reported descriptively, never gated.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final, Mapping, Sequence

import numpy as np
from ase import Atoms
from ase.calculators.calculator import Calculator
from ase.geometry import find_mic

from lupine_distill.statics.errors import ConvergenceError, InputValidationError
from lupine_distill.statics.relax import relax_positions, single_point_energy

EVIDENCE_SCHEMA_ID: Final[str] = "lupine.mlip.calc_evidence.v1"

BORN_PROVENANCE: Final[str] = (
    "Necessary mechanical-stability conditions for a cubic lattice under zero "
    "external stress: C11 - C12 > 0, C11 + 2*C12 > 0, C44 > 0. M. Born & "
    "K. Huang, Dynamical Theory of Crystal Lattices (1954); F. Mouhat & "
    "F.-X. Coudert, Phys. Rev. B 90, 224104 (2014)."
)

DYNAMIC_RETURN_LIMITS: Final[str] = (
    "Finite-rattle basin-return probe, NOT a phonon calculation: it can only "
    "detect instabilities commensurate with the supplied cell and reachable "
    "at the rattle amplitude; passing is necessary-but-not-sufficient "
    "evidence of local dynamical stability."
)

_MIN_THRESHOLD_SAMPLES: Final[int] = 5
_MEDIAN_FLOOR: Final[float] = 1.0e-12


@dataclass(frozen=True)
class GateVerdict:
    """Outcome of one reference-free gate (frozen, JSON-serializable)."""

    gate: str
    passed: bool
    values: Mapping[str, object]
    criteria: Mapping[str, object]
    detail: str
    wall_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))
        object.__setattr__(self, "criteria", MappingProxyType(dict(self.criteria)))

    def to_dict(self) -> dict[str, object]:
        return {
            "gate": self.gate,
            "passed": self.passed,
            "values": dict(self.values),
            "criteria": dict(self.criteria),
            "detail": self.detail,
            "wall_time_seconds": self.wall_time_seconds,
        }


def _require_finite(name: str, value: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a number, got {value!r}") from exc
    if not math.isfinite(v):
        raise InputValidationError(f"{name} must be finite, got {v!r}")
    return v


# --------------------------------------------------------------------------
# Born stability (exact physics)
# --------------------------------------------------------------------------


def born_stability_cubic(c11_gpa: float, c12_gpa: float, c44_gpa: float) -> GateVerdict:
    """Born mechanical-stability gate for a cubic crystal (exact conditions)."""
    t0 = time.perf_counter()
    c11 = _require_finite("c11_gpa", c11_gpa)
    c12 = _require_finite("c12_gpa", c12_gpa)
    c44 = _require_finite("c44_gpa", c44_gpa)
    checks = {
        "C11 - C12 > 0": c11 - c12 > 0.0,
        "C11 + 2*C12 > 0": c11 + 2.0 * c12 > 0.0,
        "C44 > 0": c44 > 0.0,
    }
    failed = [name for name, ok in checks.items() if not ok]
    detail = (
        "all Born stability conditions satisfied"
        if not failed
        else "violated: " + "; ".join(failed)
    )
    return GateVerdict(
        gate="born_stability_cubic",
        passed=not failed,
        values={
            "c11_gpa": c11,
            "c12_gpa": c12,
            "c44_gpa": c44,
            "c11_minus_c12_gpa": c11 - c12,
            "c11_plus_2c12_gpa": c11 + 2.0 * c12,
            "checks": {name: bool(ok) for name, ok in checks.items()},
        },
        criteria={"conditions": list(checks), "provenance": BORN_PROVENANCE},
        detail=detail,
        wall_time_seconds=time.perf_counter() - t0,
    )


# --------------------------------------------------------------------------
# Facet ordering (optional; gates only on positivity, which is exact)
# --------------------------------------------------------------------------


def facet_ordering(gammas_j_per_m2: Mapping[str, float]) -> GateVerdict:
    """Surface-energy positivity gate; facet ordering reported descriptively."""
    t0 = time.perf_counter()
    if not isinstance(gammas_j_per_m2, Mapping) or not gammas_j_per_m2:
        raise InputValidationError(
            "gammas_j_per_m2 must be a non-empty mapping of miller -> gamma"
        )
    gammas = {
        str(miller): _require_finite(f"gamma_{miller}", value)
        for miller, value in gammas_j_per_m2.items()
    }
    negative = sorted(miller for miller, g in gammas.items() if g <= 0.0)
    ordering = " <= ".join(
        f"({miller}) {gamma:.3f}" for miller, gamma in sorted(gammas.items(), key=lambda kv: kv[1])
    )
    detail = (
        f"all surface energies positive; ordering (descriptive, not gated): {ordering}"
        if not negative
        else f"non-positive surface energy for facet(s) {negative}; "
        f"ordering: {ordering}"
    )
    return GateVerdict(
        gate="facet_ordering",
        passed=not negative,
        values={"gammas_j_per_m2": gammas, "nonpositive_facets": negative},
        criteria={
            "condition": "gamma > 0 for every computed facet",
            "provenance": "exact: gamma <= 0 means the bulk is unstable "
            "against spontaneous cleaving; the relative facet ordering has no "
            "exact law and is reported descriptively only",
        },
        detail=detail,
        wall_time_seconds=time.perf_counter() - t0,
    )


# --------------------------------------------------------------------------
# Dynamic return (basin-return proxy)
# --------------------------------------------------------------------------


def dynamic_return(
    calculator: Calculator,
    atoms: Atoms,
    *,
    rattle_amplitude: float = 0.05,
    seed: int = 0,
    fmax: float = 0.02,
    optimizer: str = "FIRE",
    max_steps: int = 1000,
    energy_tol_ev_per_atom: float = 2.0e-3,
    displacement_tol_a: float = 0.25,
) -> GateVerdict:
    """Rattle-and-relax basin-return gate (cheap dynamical-stability proxy).

    Rattles a copy of ``atoms`` (Gaussian, ``stdev=rattle_amplitude``,
    deterministic ``seed``), FIRE-relaxes at fixed cell, and checks that the
    relaxed configuration returns to the original structure: per-atom energy
    within ``energy_tol_ev_per_atom`` of the unrattled reference AND maximum
    minimum-image displacement below ``displacement_tol_a``. The tolerances
    are numerical identity-of-minimum criteria (they must absorb the
    optimizer's fmax residual), not physical thresholds. A relaxation that
    exhausts its step budget is reported as a failed verdict, not an
    exception. See :data:`DYNAMIC_RETURN_LIMITS` for what this gate cannot
    see.
    """
    t0 = time.perf_counter()
    if not isinstance(atoms, Atoms) or len(atoms) == 0:
        raise InputValidationError("atoms must be a non-empty ase.Atoms object")
    amplitude = _require_finite("rattle_amplitude", rattle_amplitude)
    if not 0.0 < amplitude <= 1.0:
        raise InputValidationError(
            f"rattle_amplitude must be in (0, 1] Angstrom, got {amplitude}"
        )
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise InputValidationError(f"seed must be a non-negative integer, got {seed!r}")
    energy_tol = _require_finite("energy_tol_ev_per_atom", energy_tol_ev_per_atom)
    displacement_tol = _require_finite("displacement_tol_a", displacement_tol_a)
    if energy_tol <= 0.0 or displacement_tol <= 0.0:
        raise InputValidationError(
            "energy_tol_ev_per_atom and displacement_tol_a must be > 0, got "
            f"{energy_tol} and {displacement_tol}"
        )

    n_atoms = len(atoms)
    reference_positions = atoms.get_positions().copy()
    e_reference = single_point_energy(atoms, calculator)

    rattled = atoms.copy()
    rattled.rattle(stdev=amplitude, seed=seed)

    criteria = {
        "abs_energy_return_ev_per_atom_max": energy_tol,
        "max_mic_displacement_a_max": displacement_tol,
        "note": DYNAMIC_RETURN_LIMITS,
    }
    base_values = {
        "n_atoms": n_atoms,
        "rattle_amplitude_a": amplitude,
        "seed": seed,
        "fmax": fmax,
        "max_steps": max_steps,
        "e_reference_ev": e_reference,
    }
    try:
        relaxed, e_relaxed, n_steps = relax_positions(
            rattled, calculator, fmax=fmax, optimizer=optimizer, max_steps=max_steps
        )
    except ConvergenceError as exc:
        return GateVerdict(
            gate="dynamic_return",
            passed=False,
            values=base_values,
            criteria=criteria,
            detail=(
                f"relaxation of the rattled cell did not converge within "
                f"{max_steps} steps ({exc}); no return to the original minimum "
                f"was demonstrated. {DYNAMIC_RETURN_LIMITS}"
            ),
            wall_time_seconds=time.perf_counter() - t0,
        )

    delta_positions = relaxed.get_positions() - reference_positions
    _, mic_distances = find_mic(delta_positions, relaxed.get_cell(), pbc=True)
    max_displacement = float(np.max(mic_distances))
    energy_delta = (e_relaxed - e_reference) / n_atoms

    energy_ok = abs(energy_delta) <= energy_tol
    displacement_ok = max_displacement <= displacement_tol
    passed = energy_ok and displacement_ok
    problems = []
    if not energy_ok:
        problems.append(
            f"|dE| = {abs(energy_delta):.3e} eV/atom > {energy_tol:.1e}"
            + (" (relaxed BELOW reference: original was not a minimum)"
               if energy_delta < 0 else "")
        )
    if not displacement_ok:
        problems.append(
            f"max displacement {max_displacement:.3f} A > {displacement_tol}"
        )
    detail = (
        f"rattled structure returned to the original minimum in {n_steps} steps. "
        if passed
        else "rattled structure did NOT return: " + "; ".join(problems) + ". "
    ) + DYNAMIC_RETURN_LIMITS
    return GateVerdict(
        gate="dynamic_return",
        passed=passed,
        values={
            **base_values,
            "e_relaxed_ev": e_relaxed,
            "energy_delta_ev_per_atom": energy_delta,
            "max_displacement_a": max_displacement,
            "n_relax_steps": n_steps,
        },
        criteria=criteria,
        detail=detail,
        wall_time_seconds=time.perf_counter() - t0,
    )


# --------------------------------------------------------------------------
# Cross-model concordance (data-derived thresholds)
# --------------------------------------------------------------------------


def relative_dispersion(values: Sequence[float]) -> float:
    """Relative cross-model dispersion ``(max - min) / |median|``."""
    data = [
        _require_finite(f"values[{index}]", value) for index, value in enumerate(values)
    ]
    if len(data) < 2:
        raise InputValidationError(
            f"relative dispersion needs at least 2 values, got {len(data)}"
        )
    median = float(np.median(data))
    if abs(median) < _MEDIAN_FLOOR:
        raise InputValidationError(
            f"median magnitude {median!r} too small for a relative dispersion"
        )
    return float((max(data) - min(data)) / abs(median))


@dataclass(frozen=True)
class ConcordanceThresholds:
    """Flag/refuse dispersion thresholds derived from a measured baseline."""

    flag: float
    refuse: float
    flag_percentile: float
    refuse_percentile: float
    n_samples: int
    source: str
    sample_dispersions: tuple[tuple[str, float], ...] = field(default=())

    def to_dict(self) -> dict[str, object]:
        return {
            "flag": self.flag,
            "refuse": self.refuse,
            "flag_percentile": self.flag_percentile,
            "refuse_percentile": self.refuse_percentile,
            "n_samples": self.n_samples,
            "source": self.source,
            "sample_dispersions": [list(item) for item in self.sample_dispersions],
        }


def derive_concordance_thresholds(
    dispersions: Mapping[str, float],
    *,
    flag_percentile: float = 75.0,
    refuse_percentile: float = 95.0,
    source: str,
) -> ConcordanceThresholds:
    """Flag/refuse thresholds as percentiles of measured baseline dispersions.

    ``dispersions`` maps a sample label (e.g. material) to its measured
    cross-model relative dispersion. Percentiles use numpy's default linear
    interpolation. At least ``5`` samples are required — below that a single
    sample dominates both percentiles and the thresholds stop being a
    distribution statement.
    """
    if not isinstance(dispersions, Mapping) or not dispersions:
        raise InputValidationError("dispersions must be a non-empty mapping")
    values = {
        str(label): _require_finite(f"dispersions[{label}]", value)
        for label, value in dispersions.items()
    }
    if len(values) < _MIN_THRESHOLD_SAMPLES:
        raise InputValidationError(
            f"need at least {_MIN_THRESHOLD_SAMPLES} baseline dispersions to "
            f"derive percentile thresholds, got {len(values)}"
        )
    flag_pct = _require_finite("flag_percentile", flag_percentile)
    refuse_pct = _require_finite("refuse_percentile", refuse_percentile)
    if not 0.0 < flag_pct < refuse_pct <= 100.0:
        raise InputValidationError(
            f"need 0 < flag_percentile < refuse_percentile <= 100, "
            f"got {flag_pct} and {refuse_pct}"
        )
    if not isinstance(source, str) or not source.strip():
        raise InputValidationError("source must be a non-empty provenance string")
    sample = np.array(sorted(values.values()))
    return ConcordanceThresholds(
        flag=float(np.percentile(sample, flag_pct)),
        refuse=float(np.percentile(sample, refuse_pct)),
        flag_percentile=flag_pct,
        refuse_percentile=refuse_pct,
        n_samples=len(values),
        source=source,
        sample_dispersions=tuple(sorted(values.items())),
    )


def concordance(
    property_name: str,
    values_by_model: Mapping[str, float],
    thresholds: ConcordanceThresholds,
) -> GateVerdict:
    """Cross-model concordance gate on one property.

    Level ``pass`` below the flag threshold, ``flag`` in between (warns but
    passes), ``refuse`` at/above the refuse threshold (fails). Thresholds and
    their provenance travel in the verdict criteria.
    """
    t0 = time.perf_counter()
    if not isinstance(property_name, str) or not property_name.strip():
        raise InputValidationError("property_name must be a non-empty string")
    if not isinstance(values_by_model, Mapping) or len(values_by_model) < 2:
        raise InputValidationError(
            "values_by_model must map at least 2 model ids to values"
        )
    values = {
        str(model): _require_finite(f"values_by_model[{model}]", value)
        for model, value in values_by_model.items()
    }
    dispersion = relative_dispersion(list(values.values()))
    if dispersion >= thresholds.refuse:
        level = "refuse"
    elif dispersion >= thresholds.flag:
        level = "flag"
    else:
        level = "pass"
    return GateVerdict(
        gate="concordance",
        passed=level != "refuse",
        values={
            "property": property_name,
            "values_by_model": values,
            "dispersion": dispersion,
            "level": level,
        },
        criteria={
            "dispersion_metric": "(max - min) / |median| across models",
            "flag_at": thresholds.flag,
            "refuse_at": thresholds.refuse,
            "thresholds_source": thresholds.source,
        },
        detail=(
            f"{property_name}: cross-model dispersion {dispersion:.3f} -> {level} "
            f"(flag >= {thresholds.flag:.3f} = p{thresholds.flag_percentile:g}, "
            f"refuse >= {thresholds.refuse:.3f} = p{thresholds.refuse_percentile:g} "
            f"of {thresholds.n_samples} baseline samples)"
        ),
        wall_time_seconds=time.perf_counter() - t0,
    )


# --------------------------------------------------------------------------
# Baseline loading (calc-evidence directory -> per-material model values)
# --------------------------------------------------------------------------


def load_property_by_material(
    directory: Path, *, property_name: str = "B0"
) -> dict[str, dict[str, float]]:
    """Extract ``material -> {model_id: value}`` from a calc-evidence directory.

    Only ``lupine.mlip.calc_evidence.v1`` payloads are read; files without
    the requested property contribute nothing; duplicate (material, model)
    cells are an error.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise InputValidationError(f"evidence directory does not exist: {directory}")
    values: dict[str, dict[str, float]] = {}
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
            if not isinstance(prop, Mapping) or prop.get("name") != property_name:
                continue
            value = _require_finite(f"{path}:{property_name}", prop.get("value"))
            if model_id in values.get(material, {}):
                raise InputValidationError(
                    f"duplicate ({material}, {model_id}) {property_name} in {path}"
                )
            values.setdefault(material, {})[model_id] = value
    return values


def dispersions_by_material(
    values_by_material: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """Per-material cross-model relative dispersion (fails on <2 models)."""
    dispersions: dict[str, float] = {}
    for material, by_model in values_by_material.items():
        if len(by_model) < 2:
            raise InputValidationError(
                f"material {material!r} has {len(by_model)} model value(s); "
                f"need >= 2 for a cross-model dispersion"
            )
        dispersions[str(material)] = relative_dispersion(list(by_model.values()))
    return dispersions


__all__ = [
    "BORN_PROVENANCE",
    "ConcordanceThresholds",
    "DYNAMIC_RETURN_LIMITS",
    "EVIDENCE_SCHEMA_ID",
    "GateVerdict",
    "born_stability_cubic",
    "concordance",
    "derive_concordance_thresholds",
    "dispersions_by_material",
    "dynamic_return",
    "facet_ordering",
    "load_property_by_material",
    "relative_dispersion",
]
