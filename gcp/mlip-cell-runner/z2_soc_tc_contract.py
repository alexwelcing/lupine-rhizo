"""Strict multi-fidelity fixture execution for the Z2 SOC/Tc campaign."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np

BOLTZMANN_MEV_PER_K = 8.617333262e-2
FIXTURE_SCHEMA = "lupine.z2.soc_tc_fixture.v1"
MINIMUM_MATERIAL_COUNT = 5
TC_ERROR_TOLERANCE_K = 50.0
AXES = ("x", "y", "z")
FIT_PARAMETERS = {
    "honeycomb": {
        "mc": (0.49, 0.14, 0.0),
        "green": (0.07, 0.37, 1.0),
        "rnsw": (0.40, 0.62, 1.0),
    },
    "hexagonal": {
        "mc": (0.24, 0.045, 0.0),
        "green": (0.24, 0.14, 1.0),
        "rnsw": (0.32, 0.21, 1.0),
    },
    "square": {
        "mc": (0.37, 0.08, 0.0),
        "green": (0.34, 0.24, 1.0),
        "rnsw": (0.43, 0.36, 1.0),
    },
}


class SpinEnergyEngine(Protocol):
    def evaluate_screen(self, material: dict[str, Any]) -> dict[str, Any]: ...

    def evaluate_ordering(self, material: dict[str, Any], ordering: str) -> dict[str, Any]: ...


class CellMeasurementError(RuntimeError):
    """The fixture failed atomically, so no measurement row may be serialized."""


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} keys mismatch; missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _positive(value: Any, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{label} must be a positive int64")
    return value


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 71
        or not value.startswith("sha256:")
        or any(character not in "0123456789abcdef" for character in value[7:])
    ):
        raise ValueError(f"{label} must be a sha256:<64 lowercase hex> lock")
    return value


def validate_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Validate every fixture field, rejecting misspellings and implicit coercions."""
    root = _exact_keys(
        fixture,
        {
            "schema",
            "fixture_id",
            "requested_tier",
            "measurement_modes",
            "materials",
            "execution_protocol",
            "reference_provenance",
        },
        "fixture",
    )
    if root["schema"] != FIXTURE_SCHEMA:
        raise ValueError(f"fixture must use {FIXTURE_SCHEMA}")
    if not isinstance(root["fixture_id"], str) or not root["fixture_id"]:
        raise ValueError("fixture.fixture_id must be a non-empty string")
    tier = root["requested_tier"]
    if tier not in {"low_collinear", "high_soc", "auto"}:
        raise ValueError("fixture.requested_tier is unsupported")
    modes = root["measurement_modes"]
    if not isinstance(modes, list) or not modes or len(modes) != len(set(modes)):
        raise ValueError("fixture.measurement_modes must be non-empty and unique")
    if tier == "low_collinear":
        if modes != ["screening"]:
            raise ValueError("low_collinear tier is legal only with exactly [screening]")
    else:
        canonical = [mode for mode in ("mae_ranking", "tc_prediction") if mode in modes]
        if modes != canonical or not set(modes) <= {"mae_ranking", "tc_prediction"}:
            raise ValueError(
                "auto/high_soc modes must be canonical mae_ranking, tc_prediction, or both"
            )

    provenance = _exact_keys(
        root["reference_provenance"],
        {"source_id", "source_url", "sha256"},
        "reference_provenance",
    )
    if not isinstance(provenance["source_id"], str) or not provenance["source_id"]:
        raise ValueError("reference_provenance.source_id must be non-empty")
    if not isinstance(provenance["source_url"], str) or not provenance["source_url"].startswith(
        "https://"
    ):
        raise ValueError("reference_provenance.source_url must be an absolute https URL")
    _sha256(provenance["sha256"], "reference_provenance.sha256")

    protocol = _exact_keys(
        root["execution_protocol"],
        {
            "geometry_force_convergence_ev_per_angstrom",
            "geometry_maximum_steps",
            "geometry_method",
            "gpaw_plane_wave_cutoff_ev",
            "gpaw_kpoint_density_per_angstrom",
            "gpaw_fermi_width_ev",
            "gpaw_convergence_energy_ev",
            "gpaw_maximum_scf_iterations",
            "minimum_local_moment_muB",
            "minimum_moment_retention_fraction",
            "orientation_tie_tolerance_mev",
            "scalar_method",
            "soc_axes_degrees",
            "soc_method",
            "tc_model",
            "failure_policy",
        },
        "execution_protocol",
    )
    for key in (
        "geometry_force_convergence_ev_per_angstrom",
        "gpaw_plane_wave_cutoff_ev",
        "gpaw_kpoint_density_per_angstrom",
        "gpaw_fermi_width_ev",
        "gpaw_convergence_energy_ev",
        "minimum_local_moment_muB",
        "minimum_moment_retention_fraction",
        "orientation_tie_tolerance_mev",
    ):
        _positive(protocol[key], f"execution_protocol.{key}")
    if float(protocol["minimum_moment_retention_fraction"]) > 1.0:
        raise ValueError("minimum_moment_retention_fraction must be in (0, 1]")
    for key in ("geometry_maximum_steps", "gpaw_maximum_scf_iterations"):
        _positive_int(protocol[key], f"execution_protocol.{key}")
    expected_protocol = {
        "geometry_method": "mlip_fire_relaxation",
        "scalar_method": "gpaw_pbe_collinear_spin_polarized",
        "soc_method": "gpaw_nonselfconsistent_force_theorem_xyz",
        "tc_model": "tiwari_eq3_eq4_nearest_neighbor",
        "failure_policy": "fail cell without measurement-row serialization",
    }
    for key, expected in expected_protocol.items():
        if protocol[key] != expected:
            raise ValueError(f"execution_protocol.{key} must be {expected!r}")
    axes = _exact_keys(protocol["soc_axes_degrees"], set(AXES), "soc_axes_degrees")
    for axis in AXES:
        pair = axes[axis]
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"soc_axes_degrees.{axis} must be [theta, phi]")
        _finite(pair[0], f"soc_axes_degrees.{axis}[0]")
        _finite(pair[1], f"soc_axes_degrees.{axis}[1]")

    materials = root["materials"]
    if not isinstance(materials, list) or not materials:
        raise ValueError("fixture.materials must be non-empty")
    ids: set[str] = set()
    for index, value in enumerate(materials):
        _validate_material(value, index, ids)
    return {
        "schema": FIXTURE_SCHEMA,
        "fixture_id": root["fixture_id"],
        "material_count": len(materials),
        "minimum_material_count": MINIMUM_MATERIAL_COUNT,
        "release_ready": True,
        "blockers": [],
    }


def load_fixture(
    fixture_url: str, read_url: Callable[[str], bytes]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a synthetic or remote fixture through the same validated contract path."""
    try:
        fixture = json.loads(read_url(fixture_url).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"fixture {fixture_url} is not valid UTF-8 JSON") from exc
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a JSON object")
    return fixture, validate_fixture(fixture)


def _validate_material(value: Any, index: int, ids: set[str]) -> None:
    label = f"materials[{index}]"
    material = _exact_keys(
        value,
        {
            "material_id",
            "formula",
            "lattice",
            "spin",
            "nearest_neighbors",
            "magnetic_atom_indices",
            "afm_signs",
            "structure",
            "reference",
        },
        label,
    )
    material_id = material["material_id"]
    if not isinstance(material_id, str) or not material_id or material_id in ids:
        raise ValueError(f"{label}.material_id must be non-empty and unique")
    ids.add(material_id)
    if not isinstance(material["formula"], str) or not material["formula"]:
        raise ValueError(f"{label}.formula must be non-empty")
    if material["lattice"] not in FIT_PARAMETERS:
        raise ValueError(f"{label}.lattice is unsupported")
    _positive(material["spin"], f"{label}.spin")
    _positive_int(material["nearest_neighbors"], f"{label}.nearest_neighbors")

    structure = _exact_keys(
        material["structure"],
        {"symbols", "positions_angstrom", "cell_angstrom", "pbc", "initial_magmoms"},
        f"{label}.structure",
    )
    symbols = structure["symbols"]
    if not isinstance(symbols, list) or not symbols or not all(
        isinstance(symbol, str) and symbol for symbol in symbols
    ):
        raise ValueError(f"{label}.structure.symbols must be non-empty strings")
    atom_count = len(symbols)
    try:
        positions = np.asarray(structure["positions_angstrom"], dtype=float)
        cell = np.asarray(structure["cell_angstrom"], dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}.structure coordinates must be numeric") from exc
    if positions.shape != (atom_count, 3) or not np.all(np.isfinite(positions)):
        raise ValueError(f"{label}.structure.positions_angstrom must be finite Nx3")
    if cell.shape != (3, 3) or not np.all(np.isfinite(cell)) or abs(np.linalg.det(cell)) <= 1e-12:
        raise ValueError(f"{label}.structure.cell_angstrom must be finite and nonsingular")
    if not isinstance(structure["pbc"], list) or len(structure["pbc"]) != 3 or not all(
        isinstance(item, bool) for item in structure["pbc"]
    ):
        raise ValueError(f"{label}.structure.pbc must contain three booleans")
    magmoms = structure["initial_magmoms"]
    if not isinstance(magmoms, list) or len(magmoms) != atom_count:
        raise ValueError(f"{label}.structure.initial_magmoms must match symbols")
    for moment_index, moment in enumerate(magmoms):
        _finite(moment, f"{label}.structure.initial_magmoms[{moment_index}]")

    indices = material["magnetic_atom_indices"]
    signs = material["afm_signs"]
    if (
        not isinstance(indices, list)
        or not indices
        or len(indices) != len(set(indices))
        or any(
            isinstance(item, bool) or not isinstance(item, int) or not 0 <= item < atom_count
            for item in indices
        )
    ):
        raise ValueError(f"{label}.magnetic_atom_indices is invalid")
    if not isinstance(signs, list) or len(signs) != len(indices) or set(signs) != {-1, 1}:
        raise ValueError(f"{label}.afm_signs must match indices and contain both signs")

    reference = _exact_keys(
        material["reference"],
        {
            "mae_xz_mev_per_cell",
            "mae_yz_mev_per_cell",
            "exchange_mev",
            "exchange_anisotropy",
            "tc_k",
            "tc_envelope_k",
        },
        f"{label}.reference",
    )
    _finite(reference["mae_xz_mev_per_cell"], f"{label}.reference.mae_xz_mev_per_cell")
    _finite(reference["mae_yz_mev_per_cell"], f"{label}.reference.mae_yz_mev_per_cell")
    _positive(reference["exchange_mev"], f"{label}.reference.exchange_mev")
    delta = _positive(reference["exchange_anisotropy"], f"{label}.reference.exchange_anisotropy")
    if delta > 0.2:
        raise ValueError(f"{label}.reference.exchange_anisotropy exceeds 0.2")
    tc = _exact_keys(reference["tc_k"], {"green", "mc", "rnsw"}, f"{label}.reference.tc_k")
    for method, estimate in tc.items():
        _positive(estimate, f"{label}.reference.tc_k.{method}")
    envelope = reference["tc_envelope_k"]
    if not isinstance(envelope, list) or len(envelope) != 2:
        raise ValueError(f"{label}.reference.tc_envelope_k must be [low, high]")
    low = _positive(envelope[0], f"{label}.reference.tc_envelope_k[0]")
    high = _positive(envelope[1], f"{label}.reference.tc_envelope_k[1]")
    if low > high:
        raise ValueError(f"{label}.reference.tc_envelope_k must be ordered")


def tc_estimates_k(
    *, exchange_mev: float, exchange_anisotropy: float, spin: float, lattice: str
) -> dict[str, float]:
    if lattice not in FIT_PARAMETERS:
        raise ValueError(f"unsupported magnetic lattice: {lattice}")
    exchange = _positive(exchange_mev, "exchange_mev")
    delta = _positive(exchange_anisotropy, "exchange_anisotropy")
    if delta > 0.2:
        raise ValueError("exchange_anisotropy must be in the published fit domain (0, 0.2]")
    spin_value = _positive(spin, "spin")
    estimates: dict[str, float] = {}
    for method, (alpha1, alpha2, theta) in FIT_PARAMETERS[lattice].items():
        denominator = 2.0 * BOLTZMANN_MEV_PER_K * (alpha1 - alpha2 * math.log(delta))
        estimates[method] = _positive(
            exchange * (spin_value**2 + theta * spin_value) / denominator,
            f"Tc.{method}",
        )
    return estimates


def _ordering_evidence(raw: dict[str, Any], ordering: str, protocol: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("ordering") != ordering:
        raise ValueError(f"{ordering} ordering evidence is malformed")
    scalar_total = _finite(raw.get("scalar_total_energy_ev"), f"{ordering}.scalar_total_energy_ev")
    scalar_band = _finite(raw.get("scalar_band_energy_ev"), f"{ordering}.scalar_band_energy_ev")
    bands_raw = _exact_keys(raw.get("soc_band_energies_ev"), set(AXES), f"{ordering}.soc bands")
    bands = {axis: _finite(bands_raw[axis], f"{ordering}.soc_band.{axis}") for axis in AXES}
    corrected = {axis: scalar_total + bands[axis] - scalar_band for axis in AXES}
    supplied = raw.get("orientation_energies_ev")
    if supplied is not None:
        supplied = _exact_keys(supplied, set(AXES), f"{ordering}.orientation energies")
        for axis in AXES:
            if not math.isclose(
                _finite(supplied[axis], f"{ordering}.orientation.{axis}"),
                corrected[axis],
                rel_tol=0.0,
                abs_tol=1e-10,
            ):
                raise ValueError(f"{ordering} corrected {axis} energy is inconsistent")
    if raw.get("soc_method") != protocol["soc_method"]:
        raise ValueError(f"{ordering}.soc_method does not match the frozen protocol")
    if raw.get("geometry_method") != protocol["geometry_method"]:
        raise ValueError(f"{ordering}.geometry_method does not match the frozen protocol")
    return {
        "ordering": ordering,
        "scalar_total_energy_ev": scalar_total,
        "scalar_band_energy_ev": scalar_band,
        "soc_band_energies_ev": bands,
        "orientation_energies_ev": corrected,
        "soc_method": protocol["soc_method"],
        "geometry_method": protocol["geometry_method"],
    }


def _orientation_order(
    energies: dict[str, float], tolerance_mev: float
) -> tuple[list[str], dict[str, float]]:
    ordered: list[str] = sorted(AXES, key=lambda axis: (energies[axis], AXES.index(axis)))
    ranks: dict[str, float] = {}
    start = 0
    tolerance_ev = tolerance_mev / 1000.0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and energies[ordered[end]] - energies[ordered[start]] <= tolerance_ev:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for axis in ordered[start:end]:
            ranks[axis] = average_rank
        start = end
    return ordered, {axis: ranks[axis] for axis in AXES}


def derive_spin_observables(
    material: dict[str, Any],
    fm_raw: dict[str, Any],
    afm_raw: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    fm = _ordering_evidence(fm_raw, "fm", protocol)
    afm = _ordering_evidence(afm_raw, "afm", protocol)
    spin = _positive(material["spin"], "material.spin")
    neighbors = _positive_int(material["nearest_neighbors"], "material.nearest_neighbors")
    factor = 2.0 * neighbors * spin**2
    fm_energies = fm["orientation_energies_ev"]
    afm_energies = afm["orientation_energies_ev"]
    j_parallel = 1000.0 * (afm_energies["x"] - fm_energies["x"]) / factor
    j_perpendicular = 1000.0 * (afm_energies["z"] - fm_energies["z"]) / factor
    exchange = (j_parallel + j_perpendicular) / 2.0
    if not math.isfinite(exchange) or exchange <= 0.0:
        raise ValueError("derived nearest-neighbour exchange must be positive")
    delta = (j_perpendicular - j_parallel) / (2.0 * exchange)
    tc = tc_estimates_k(
        exchange_mev=exchange,
        exchange_anisotropy=delta,
        spin=spin,
        lattice=material["lattice"],
    )
    ranked, ranks = _orientation_order(
        fm_energies, float(protocol["orientation_tie_tolerance_mev"])
    )
    return {
        "orientation_energies_ev": dict(fm_energies),
        "mae_xz_mev_per_cell": 1000.0 * (fm_energies["z"] - fm_energies["x"]),
        "mae_yz_mev_per_cell": 1000.0 * (fm_energies["z"] - fm_energies["y"]),
        "ranked_orientations": ranked,
        "orientation_ranks": ranks,
        "easy_axis": ranked[0],
        "exchange_parallel_mev": j_parallel,
        "exchange_perpendicular_mev": j_perpendicular,
        "exchange_mev": exchange,
        "exchange_anisotropy": delta,
        "tc_green_k": tc["green"],
        "tc_mc_k": tc["mc"],
        "tc_rnsw_k": tc["rnsw"],
        "ordering_evidence": {"fm": fm, "afm": afm},
    }


def _screen_prediction(
    material: dict[str, Any], raw: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, Any]:
    fm = _finite(raw.get("fm_scalar_energy_ev"), "screen.fm_scalar_energy_ev")
    afm = _finite(raw.get("afm_scalar_energy_ev"), "screen.afm_scalar_energy_ev")
    minimum_moment = _finite(
        raw.get("minimum_final_local_moment_muB"), "screen.minimum_final_local_moment_muB"
    )
    retention = _finite(raw.get("moment_retention_fraction"), "screen.moment_retention_fraction")
    spin = _positive(material["spin"], "material.spin")
    neighbors = _positive_int(material["nearest_neighbors"], "material.nearest_neighbors")
    exchange = 1000.0 * (afm - fm) / (2.0 * neighbors * spin**2)
    reasons: list[str] = []
    if minimum_moment < float(protocol["minimum_local_moment_muB"]):
        reasons.append("local_moment_below_threshold")
    if retention < float(protocol["minimum_moment_retention_fraction"]):
        reasons.append("moment_retention_below_threshold")
    if exchange <= 0.0:
        reasons.append("nonferromagnetic_exchange")
    return {
        "material_id": material["material_id"],
        "formula": material["formula"],
        "status": "completed",
        "fidelity_tier_used": "low_collinear",
        "fm_scalar_energy_ev": fm,
        "afm_scalar_energy_ev": afm,
        "collinear_exchange_screen_mev": exchange,
        "minimum_final_local_moment_muB": minimum_moment,
        "moment_retention_fraction": retention,
        "promotable_to_high_soc": not reasons,
        "screening_reasons": reasons,
    }


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("Spearman ranking requires at least two complete materials")
    x = _average_ranks(left)
    y = _average_ranks(right)
    x_mean = math.fsum(x) / len(x)
    y_mean = math.fsum(y) / len(y)
    covariance = math.fsum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    x_scale = math.sqrt(math.fsum((a - x_mean) ** 2 for a in x))
    y_scale = math.sqrt(math.fsum((b - y_mean) ** 2 for b in y))
    if x_scale == 0.0 or y_scale == 0.0:
        raise ValueError("Spearman ranking is undefined for a constant series")
    result = covariance / (x_scale * y_scale)
    if math.isclose(abs(result), 1.0, rel_tol=0.0, abs_tol=1e-12):
        return math.copysign(1.0, result)
    return result


def _reference_easy_axis(material: dict[str, Any], tolerance_mev: float) -> str:
    reference = material["reference"]
    z = float(reference["mae_xz_mev_per_cell"]) / 1000.0
    energies = {
        "x": 0.0,
        "z": z,
        "y": z - float(reference["mae_yz_mev_per_cell"]) / 1000.0,
    }
    return _orientation_order(energies, tolerance_mev)[0][0]


def _row_spec(fixture: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "mae_ranking":
        measurement = {
            "metric": "magnetocrystalline_anisotropy_rank_correlation",
            "unit": "spearman_rho",
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
            "acceptance_threshold": 1.0,
        }
    elif mode == "tc_prediction":
        measurement = {
            "metric": "tc_rnsw_mae_k",
            "unit": "K",
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
            "tc_error_tolerance_k": TC_ERROR_TOLERANCE_K,
        }
    else:
        measurement = {
            "metric": "promotable_fraction",
            "unit": "fraction",
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
        }
    return {
        "row_id": "soc_tc",
        "measurement_mode": mode,
        "requested_tier": fixture["requested_tier"],
        "execution_protocol": fixture["execution_protocol"],
        "measurement": measurement,
    }


def _envelope(
    fixture: dict[str, Any], contract: dict[str, Any], mode: str, predictions: list[dict[str, Any]]
) -> dict[str, Any]:
    material_count = len(fixture["materials"])
    if mode == "screening":
        promotable = sum(item["promotable_to_high_soc"] for item in predictions)
        fraction = float(promotable / material_count)
        metrics = {
            "primary_metric": "promotable_fraction",
            "promotable_fraction": fraction,
            "completed_material_count": material_count,
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
            "measurement_complete": True,
        }
        score = fraction
    elif mode == "mae_ranking":
        reference = [
            float(material["reference"]["mae_xz_mev_per_cell"])
            for material in fixture["materials"]
        ]
        predicted = [float(item["mae_xz_mev_per_cell"]) for item in predictions]
        rho = _spearman(reference, predicted)
        tolerance = float(fixture["execution_protocol"]["orientation_tie_tolerance_mev"])
        easy_axis_errors = sum(
            item["easy_axis"] != _reference_easy_axis(material, tolerance)
            for item, material in zip(predictions, fixture["materials"], strict=True)
        )
        metrics = {
            "primary_metric": "magnetocrystalline_anisotropy_rank_correlation",
            "magnetocrystalline_anisotropy_rank_correlation": rho,
            "easy_axis_errors": easy_axis_errors,
            "completed_material_count": material_count,
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
            "measurement_complete": True,
            "acceptance_threshold": 1.0,
        }
        score = 1.0 if rho == 1.0 and easy_axis_errors == 0 else 0.0
    else:
        errors = [
            abs(float(item["tc_rnsw_k"]) - float(material["reference"]["tc_k"]["rnsw"]))
            for item, material in zip(predictions, fixture["materials"], strict=True)
        ]
        mae = float(math.fsum(errors) / material_count)
        covered = sum(
            float(material["reference"]["tc_envelope_k"][0])
            <= float(item["tc_rnsw_k"])
            <= float(material["reference"]["tc_envelope_k"][1])
            for item, material in zip(predictions, fixture["materials"], strict=True)
        )
        metrics = {
            "primary_metric": "tc_rnsw_mae_k",
            "tc_rnsw_mae_k": mae,
            "tc_envelope_coverage": float(covered / material_count),
            "completed_material_count": material_count,
            "minimum_material_count": MINIMUM_MATERIAL_COUNT,
            "measurement_complete": True,
        }
        score = max(0.0, 1.0 - mae / TC_ERROR_TOLERANCE_K)
    row = {
        "predictions": predictions,
        "score": float(score),
        "score_unit": "row_native_physical_score",
        "metrics": metrics,
        "row_spec": _row_spec(fixture, mode),
        "fixture_contract": contract,
        "n_structures": material_count,
    }
    _forbid_placeholders(row)
    return row


def _forbid_placeholders(value: Any, path: str = "row") -> None:
    if value is None:
        raise ValueError(f"{path} contains null")
    if isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if isinstance(value, str):
        if not value or value.lower() in {"failed", "abstained", "null", "nan", "placeholder"}:
            raise ValueError(f"{path} contains a forbidden placeholder token")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{path} contains an invalid key")
            _forbid_placeholders(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _forbid_placeholders(item, f"{path}[{index}]")


def run_soc_tc_rows(
    fixture: dict[str, Any], engine: SpinEnergyEngine
) -> list[dict[str, Any]]:
    """Execute all requested modes; return rows only after the whole fixture succeeds."""
    contract = validate_fixture(fixture)
    if len(fixture["materials"]) < MINIMUM_MATERIAL_COUNT:
        raise CellMeasurementError(
            f"fixture requires at least {MINIMUM_MATERIAL_COUNT} materials for serialization"
        )
    protocol = fixture["execution_protocol"]
    screens: list[dict[str, Any]] = []
    derived: list[dict[str, Any]] = []
    try:
        for material in fixture["materials"]:
            try:
                screen = _screen_prediction(material, engine.evaluate_screen(material), protocol)
                screens.append(screen)
                if fixture["requested_tier"] == "auto" and not screen["promotable_to_high_soc"]:
                    reasons = ", ".join(screen["screening_reasons"])
                    raise ValueError(f"automatic low-tier screen was not promotable: {reasons}")
                if fixture["requested_tier"] != "low_collinear":
                    fm = engine.evaluate_ordering(material, "fm")
                    afm = engine.evaluate_ordering(material, "afm")
                    derived.append(derive_spin_observables(material, fm, afm, protocol))
            except Exception as exc:
                raise CellMeasurementError(
                    f"material {material['material_id']} failed: {exc.__class__.__name__}: {exc}"
                ) from exc

        rows: list[dict[str, Any]] = []
        for mode in fixture["measurement_modes"]:
            if mode == "screening":
                predictions = screens
            elif mode == "mae_ranking":
                predictions = [
                    {
                        "material_id": material["material_id"],
                        "formula": material["formula"],
                        "status": "completed",
                        "fidelity_tier_used": "high_soc",
                        "orientation_energies_ev": result["orientation_energies_ev"],
                        "mae_xz_mev_per_cell": result["mae_xz_mev_per_cell"],
                        "mae_yz_mev_per_cell": result["mae_yz_mev_per_cell"],
                        "ranked_orientations": result["ranked_orientations"],
                        "orientation_ranks": result["orientation_ranks"],
                        "easy_axis": result["easy_axis"],
                        "ordering_evidence": result["ordering_evidence"],
                    }
                    for material, result in zip(fixture["materials"], derived, strict=True)
                ]
            else:
                predictions = [
                    {
                        "material_id": material["material_id"],
                        "formula": material["formula"],
                        "status": "completed",
                        "fidelity_tier_used": "high_soc",
                        "exchange_parallel_mev": result["exchange_parallel_mev"],
                        "exchange_perpendicular_mev": result["exchange_perpendicular_mev"],
                        "exchange_mev": result["exchange_mev"],
                        "exchange_anisotropy": result["exchange_anisotropy"],
                        "tc_green_k": result["tc_green_k"],
                        "tc_mc_k": result["tc_mc_k"],
                        "tc_rnsw_k": result["tc_rnsw_k"],
                        "ordering_evidence": result["ordering_evidence"],
                    }
                    for material, result in zip(fixture["materials"], derived, strict=True)
                ]
            rows.append(_envelope(fixture, contract, mode, predictions))
        return rows
    except CellMeasurementError:
        raise
    except Exception as exc:
        raise CellMeasurementError(f"fixture {fixture['fixture_id']} failed: {exc}") from exc
