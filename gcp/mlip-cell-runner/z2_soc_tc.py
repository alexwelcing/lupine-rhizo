"""Spin-orbit / Curie-temperature row for the locked Z2 campaign."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from typing import Any, Protocol

import numpy as np
from ase import Atoms
from z1_barrier import canonical_content_hash, locked_artifact_url

BOLTZMANN_MEV_PER_K = 8.617333262e-2
SOC_TC_ROW_ID = "soc_tc"
PANEL_SCHEMA = "lupine.z2.soc_tc_panel.v1"

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
    """Engine that returns force-theorem energies for one magnetic ordering."""

    def evaluate_ordering(self, material: dict[str, Any], ordering: str) -> dict[str, Any]: ...


def _sha256_lock(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 71 or not value.startswith("sha256:"):
        raise ValueError(f"{label} must be a sha256:<64 lowercase hex> lock")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise ValueError(f"{label} must be a sha256:<64 lowercase hex> lock")
    return value


def validate_panel(panel: dict[str, Any]) -> dict[str, Any]:
    """Fail closed unless a panel contains executable spin/SOC inputs."""
    if panel.get("schema") != PANEL_SCHEMA:
        raise ValueError(f"candidate panel must use {PANEL_SCHEMA}")
    measurement = panel.get("measurement")
    if not isinstance(measurement, dict):
        raise ValueError("candidate panel measurement must be an object")
    minimum_count = measurement.get("minimum_material_count")
    if not isinstance(minimum_count, int) or minimum_count < 5:
        raise ValueError("candidate panel minimum_material_count must be at least five")
    materials = panel.get("materials")
    if not isinstance(materials, list) or len(materials) < minimum_count:
        raise ValueError(f"candidate panel needs at least {minimum_count} materials")
    protocol = panel.get("execution_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("candidate panel execution_protocol must be an object")
    for key in (
        "geometry_force_convergence_ev_per_angstrom",
        "gpaw_plane_wave_cutoff_ev",
        "gpaw_kpoint_density_per_angstrom",
        "gpaw_fermi_width_ev",
        "gpaw_convergence_energy_ev",
    ):
        value = protocol.get(key)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"candidate panel execution_protocol.{key} must be positive")
    for key in ("geometry_maximum_steps", "gpaw_maximum_scf_iterations"):
        value = protocol.get(key)
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"candidate panel execution_protocol.{key} must be positive")
    if protocol.get("failure_policy") != "record failure without imputation":
        raise ValueError("candidate panel must record failures without imputation")
    material_ids: set[str] = set()
    for index, material in enumerate(materials):
        if not isinstance(material, dict):
            raise ValueError(f"candidate panel materials[{index}] must be an object")
        material_id = material.get("material_id")
        if not isinstance(material_id, str) or not material_id or material_id in material_ids:
            raise ValueError(f"candidate panel materials[{index}] needs a unique material_id")
        material_ids.add(material_id)
        structure = material.get("structure")
        if not isinstance(structure, dict) or not structure.get("symbols"):
            raise ValueError(f"candidate panel material {material_id} needs a structure")
        indices = material.get("magnetic_atom_indices")
        signs = material.get("afm_signs")
        if (
            not isinstance(indices, list)
            or not indices
            or not isinstance(signs, list)
            or len(signs) != len(indices)
        ):
            raise ValueError(f"candidate panel material {material_id} needs AFM spin sites")
    return {
        "schema": panel["schema"],
        "panel_id": panel.get("panel_id"),
        "material_count": len(materials),
        "minimum_material_count": minimum_count,
        "release_ready": True,
        "blockers": [],
    }


def load_campaign_panel(
    manifest_url: str,
    mlip_id: str,
    read_url: Callable[[str], bytes],
) -> tuple[dict[str, Any], dict[str, Any], str, dict[str, Any]]:
    """Load and verify the Z2 manifest and its content-addressed panel."""
    manifest = json.loads(read_url(manifest_url).decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("CampaignManifest must be a JSON object")
    expected_manifest_hash = _sha256_lock(
        manifest.get("content_hash"), "CampaignManifest.content_hash"
    )
    actual_manifest_hash = canonical_content_hash(manifest)
    if actual_manifest_hash != expected_manifest_hash:
        raise ValueError(
            f"CampaignManifest content_hash mismatch: expected {expected_manifest_hash}, "
            f"got {actual_manifest_hash}"
        )
    models = manifest.get("available_models")
    if not isinstance(models, list) or mlip_id not in {
        model.get("model_id") for model in models if isinstance(model, dict)
    }:
        raise ValueError(f"mlip_id {mlip_id} is not registered in CampaignManifest.available_models")
    acceptance = manifest.get("acceptance_test")
    if (
        not isinstance(acceptance, dict)
        or acceptance.get("metric") != "magnetocrystalline_anisotropy_rank_correlation"
        or acceptance.get("operator") != "eq"
        or acceptance.get("unit") != "spearman_rho"
        or acceptance.get("threshold") != 1
    ):
        raise ValueError("Z2 acceptance_test must require Spearman rho equal to one")
    execution = manifest.get("execution")
    panel_lock = execution.get("candidate_panel") if isinstance(execution, dict) else None
    if not isinstance(panel_lock, dict):
        raise ValueError("Z2 CampaignManifest execution.candidate_panel lock is required")
    panel_path = panel_lock.get("path")
    if not isinstance(panel_path, str) or not panel_path:
        raise ValueError("Z2 candidate_panel.path is required")
    expected_panel_hash = _sha256_lock(panel_lock.get("sha256"), "candidate_panel.sha256")
    panel_url = locked_artifact_url(manifest_url, panel_path)
    panel_bytes = read_url(panel_url)
    actual_panel_hash = "sha256:" + hashlib.sha256(panel_bytes).hexdigest()
    if actual_panel_hash != expected_panel_hash:
        raise ValueError(
            f"candidate panel sha256 mismatch: expected {expected_panel_hash}, "
            f"got {actual_panel_hash}"
        )
    panel = json.loads(panel_bytes.decode("utf-8"))
    if not isinstance(panel, dict):
        raise ValueError("candidate panel must be a JSON object")
    contract = validate_panel(panel)
    contract.update(
        {
            "campaign_id": manifest.get("campaign_id"),
            "campaign_manifest_hash": expected_manifest_hash,
            "candidate_panel_url": panel_url,
            "candidate_panel_sha256": expected_panel_hash,
        }
    )
    return manifest, panel, expected_manifest_hash, contract


def tc_estimates_k(
    *, exchange_mev: float, exchange_anisotropy: float, spin: float, lattice: str
) -> dict[str, float]:
    """Evaluate Tiwari et al. Eq. (3) for each published fitted method."""
    if lattice not in FIT_PARAMETERS:
        raise ValueError(f"unsupported magnetic lattice: {lattice}")
    if not math.isfinite(exchange_mev) or exchange_mev <= 0:
        raise ValueError("exchange_mev must be finite and positive")
    if not math.isfinite(exchange_anisotropy) or not 0 < exchange_anisotropy <= 0.2:
        raise ValueError("exchange_anisotropy must be in the published fit domain (0, 0.2]")
    if not math.isfinite(spin) or spin <= 0:
        raise ValueError("spin must be finite and positive")

    estimates = {}
    for method, (alpha1, alpha2, theta) in FIT_PARAMETERS[lattice].items():
        denominator = 2.0 * BOLTZMANN_MEV_PER_K * (
            alpha1 - alpha2 * math.log(exchange_anisotropy)
        )
        estimates[method] = exchange_mev * (spin**2 + theta * spin) / denominator
    return estimates


def _finite(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite")
    return float(value)


def atoms_from_structure(record: dict[str, Any]) -> Atoms:
    atoms = Atoms(
        symbols=record["symbols"],
        positions=np.asarray(record["positions_angstrom"], dtype=float),
        cell=np.asarray(record["cell_angstrom"], dtype=float),
        pbc=record["pbc"],
    )
    initial_magmoms = record.get("initial_magmoms")
    if isinstance(initial_magmoms, list) and len(initial_magmoms) == len(atoms):
        atoms.set_initial_magnetic_moments(initial_magmoms)
    return atoms


def _default_optimizer_factory(atoms: Atoms, logfile: Any = None) -> Any:
    from ase.optimize import FIRE

    return FIRE(atoms, logfile=logfile)


def _default_scalar_calculator_factory(
    atoms: Atoms, ordering: str, protocol: dict[str, Any]
) -> Any:
    del atoms, ordering
    from gpaw import GPAW, PW

    return GPAW(
        mode=PW(float(protocol["gpaw_plane_wave_cutoff_ev"])),
        xc="PBE",
        spinpol=True,
        kpts={
            "density": float(protocol["gpaw_kpoint_density_per_angstrom"]),
            "gamma": True,
        },
        occupations={
            "name": "fermi-dirac",
            "width": float(protocol["gpaw_fermi_width_ev"]),
        },
        symmetry="off",
        convergence={"energy": float(protocol["gpaw_convergence_energy_ev"])},
        maxiter=int(protocol["gpaw_maximum_scf_iterations"]),
        txt=None,
    )


def _default_scalar_energy(calc: Any, atoms: Atoms) -> float:
    atoms.calc = calc
    return float(atoms.get_potential_energy())


def _default_soc_band_energy(calc: Any, *, theta: float, phi: float, scale: float) -> float:
    from gpaw.spinorbit import soc_eigenstates

    states = soc_eigenstates(calc, theta=theta, phi=phi, scale=scale)
    return float(states.calculate_band_energy())


class GPAWSpinEnergyEngine:
    """MLIP geometry relaxation followed by GPAW scalar-SCF and SOC force theorem."""

    def __init__(
        self,
        geometry_calculator: Any,
        protocol: dict[str, Any],
        *,
        scalar_calculator_factory: Callable[[Atoms, str, dict[str, Any]], Any] = (
            _default_scalar_calculator_factory
        ),
        scalar_energy: Callable[[Any, Atoms], float] = _default_scalar_energy,
        soc_band_energy: Callable[..., float] = _default_soc_band_energy,
        optimizer_factory: Callable[..., Any] = _default_optimizer_factory,
    ) -> None:
        self.geometry_calculator = geometry_calculator
        self.protocol = protocol
        self.scalar_calculator_factory = scalar_calculator_factory
        self.scalar_energy = scalar_energy
        self.soc_band_energy = soc_band_energy
        self.optimizer_factory = optimizer_factory
        self._relaxed: dict[str, Atoms] = {}
        self._scalar_states: dict[tuple[str, str], tuple[Atoms, Any, float, np.ndarray]] = {}

    def _relaxed_atoms(self, material: dict[str, Any]) -> Atoms:
        material_id = str(material["material_id"])
        cached = self._relaxed.get(material_id)
        if cached is not None:
            return cached.copy()
        atoms = atoms_from_structure(material["structure"])
        atoms.calc = self.geometry_calculator
        optimizer = self.optimizer_factory(atoms, logfile=None)
        converged = bool(
            optimizer.run(
                fmax=float(self.protocol["geometry_force_convergence_ev_per_angstrom"]),
                steps=int(self.protocol["geometry_maximum_steps"]),
            )
        )
        if not converged:
            raise RuntimeError("MLIP geometry relaxation did not converge under frozen protocol")
        atoms.calc = None
        self._relaxed[material_id] = atoms.copy()
        return atoms

    def _scalar_state(
        self, material: dict[str, Any], ordering: str
    ) -> tuple[Atoms, Any, float, np.ndarray]:
        if ordering not in {"fm", "afm"}:
            raise ValueError(f"unsupported magnetic ordering: {ordering}")
        cache_key = (str(material["material_id"]), ordering)
        cached = self._scalar_states.get(cache_key)
        if cached is not None:
            return cached
        atoms = self._relaxed_atoms(material)
        indices = material["magnetic_atom_indices"]
        afm_signs = material["afm_signs"]
        moment = 2.0 * _finite(material.get("spin"), "material.spin")
        # Preserve fixture-provided moments on nonmagnetic atoms; the ordering
        # initialization is authoritative only for explicitly magnetic sites.
        magmoms = np.asarray(atoms.get_initial_magnetic_moments(), dtype=float).copy()
        for position, atom_index in enumerate(indices):
            if not isinstance(atom_index, int) or not 0 <= atom_index < len(atoms):
                raise ValueError("magnetic_atom_indices contains an invalid atom index")
            sign = 1.0 if ordering == "fm" else _finite(afm_signs[position], "afm_sign")
            if sign not in {-1.0, 1.0}:
                raise ValueError("afm_signs must contain only -1 or 1")
            magmoms[atom_index] = moment * sign
        atoms.set_initial_magnetic_moments(magmoms)
        calc = self.scalar_calculator_factory(atoms, ordering, self.protocol)
        scalar_total = _finite(self.scalar_energy(calc, atoms), "GPAW scalar total energy")
        try:
            final_magmoms = np.asarray(calc.get_magnetic_moments(atoms), dtype=float)
        except (AttributeError, NotImplementedError, RuntimeError):
            # SOC-only injected calculators may omit local moments. Keep the
            # scalar state usable for direct SOC tests, but make screening fail
            # closed rather than inventing retained moments.
            final_magmoms = np.full(len(atoms), np.nan, dtype=float)
        if final_magmoms.shape != (len(atoms),):
            raise RuntimeError("GPAW returned invalid final local magnetic moments")
        state = (atoms, calc, scalar_total, final_magmoms)
        self._scalar_states[cache_key] = state
        return state

    def evaluate_screen(self, material: dict[str, Any]) -> dict[str, Any]:
        """Run the mandatory scalar FM/AFM screen without evaluating SOC."""
        fm_atoms, _, fm_energy, fm_moments = self._scalar_state(material, "fm")
        afm_atoms, _, afm_energy, afm_moments = self._scalar_state(material, "afm")
        indices = np.asarray(material["magnetic_atom_indices"], dtype=int)
        initial = np.concatenate(
            (
                np.abs(fm_atoms.get_initial_magnetic_moments()[indices]),
                np.abs(afm_atoms.get_initial_magnetic_moments()[indices]),
            )
        )
        final = np.concatenate((np.abs(fm_moments[indices]), np.abs(afm_moments[indices])))
        if not np.all(np.isfinite(final)):
            raise RuntimeError("scalar backend did not provide finite final local moments")
        if np.any(initial <= 0.0):
            raise RuntimeError("magnetic-site initialization must be nonzero")
        return {
            "fm_scalar_energy_ev": fm_energy,
            "afm_scalar_energy_ev": afm_energy,
            "minimum_final_local_moment_muB": float(np.min(final)),
            "moment_retention_fraction": float(np.mean(final / initial)),
        }

    def evaluate_ordering(self, material: dict[str, Any], ordering: str) -> dict[str, Any]:
        _, calc, scalar_total, _ = self._scalar_state(material, ordering)
        scalar_band = _finite(
            self.soc_band_energy(calc, theta=0.0, phi=0.0, scale=0.0),
            "GPAW scalar band energy",
        )

        def corrected(theta: float, phi: float) -> tuple[float, float]:
            band = _finite(
                self.soc_band_energy(calc, theta=theta, phi=phi, scale=1.0),
                "GPAW SOC band energy",
            )
            return scalar_total + band - scalar_band, band

        x_energy, x_band = corrected(90.0, 0.0)
        y_energy, y_band = corrected(90.0, 90.0)
        z_energy, z_band = corrected(0.0, 0.0)
        return {
            "ordering": ordering,
            "parallel_energy_ev": x_energy,
            "y_energy_ev": y_energy,
            "perpendicular_energy_ev": z_energy,
            "scalar_total_energy_ev": scalar_total,
            "scalar_band_energy_ev": scalar_band,
            "soc_band_energies_ev": {"x": x_band, "y": y_band, "z": z_band},
            "orientation_energies_ev": {
                "x": x_energy,
                "y": y_energy,
                "z": z_energy,
            },
            "soc_method": self.protocol.get(
                "soc_method", "non-selfconsistent_force_theorem"
            ),
            "geometry_method": self.protocol.get(
                "geometry_method", "mlip_fire_relaxation"
            ),
        }


def derive_spin_observables(
    material: dict[str, Any],
    fm: dict[str, Any],
    afm: dict[str, Any],
) -> dict[str, Any]:
    """Derive J, Δ, signed MAE, and Tc from FM/AFM SOC energies.

    ``perpendicular_energy_ev`` is the z-axis force-theorem energy and
    ``parallel_energy_ev`` is the x-axis energy. For the nearest-neighbour
    anisotropic Heisenberg Hamiltonian used by Tiwari et al., the in-plane
    AFM-FM split measures J_parallel and the out-of-plane split measures
    J_perpendicular. The published mapping (Tiwari et al., Eq. 4c–4d) is

        J = (J_parallel + J_perpendicular) / 2
        Δ = (J_perpendicular - J_parallel) / (2 J)

    Note this is NOT J = J_parallel with Δ = B/J — the earlier
    implementation made exactly that error (reviewer-flagged twice).
    """
    spin = _finite(material.get("spin"), "material.spin")
    neighbors = material.get("nearest_neighbors")
    if not isinstance(neighbors, int) or neighbors < 1:
        raise ValueError("material.nearest_neighbors must be a positive integer")
    factor = 2.0 * neighbors * spin**2
    fm_z = _finite(fm.get("perpendicular_energy_ev"), "FM perpendicular energy")
    fm_x = _finite(fm.get("parallel_energy_ev"), "FM parallel energy")
    afm_z = _finite(afm.get("perpendicular_energy_ev"), "AFM perpendicular energy")
    afm_x = _finite(afm.get("parallel_energy_ev"), "AFM parallel energy")

    j_parallel_ev = (afm_x - fm_x) / factor
    j_perpendicular_ev = (afm_z - fm_z) / factor
    exchange_ev = (j_parallel_ev + j_perpendicular_ev) / 2.0
    exchange_mev = exchange_ev * 1000.0
    if exchange_mev <= 0:
        raise ValueError("derived nearest-neighbour exchange must be positive")
    exchange_anisotropy = (j_perpendicular_ev - j_parallel_ev) / (2.0 * exchange_ev)
    tc = tc_estimates_k(
        exchange_mev=exchange_mev,
        exchange_anisotropy=exchange_anisotropy,
        spin=spin,
        lattice=str(material.get("lattice")),
    )
    mae_xz = (fm_z - fm_x) * 1000.0
    fm_y_value = fm.get("y_energy_ev")
    mae_yz = (
        (fm_z - _finite(fm_y_value, "FM y energy")) * 1000.0
        if fm_y_value is not None
        else mae_xz
    )
    return {
        "material_id": material.get("material_id"),
        "formula": material.get("formula"),
        "status": "completed",
        "exchange_mev": exchange_mev,
        "j_parallel_mev": j_parallel_ev * 1000.0,
        "j_perpendicular_mev": j_perpendicular_ev * 1000.0,
        "anisotropic_exchange_mev": (j_perpendicular_ev - j_parallel_ev) * 1000.0,
        "exchange_anisotropy": exchange_anisotropy,
        "mae_xz_mev_per_cell": mae_xz,
        "mae_yz_mev_per_cell": mae_yz,
        "easy_axis": "out_of_plane" if max(mae_xz, mae_yz) < 0.0 else "in_plane",
        "tc_k": tc,
        "ordering_evidence": {"fm": fm, "afm": afm},
    }


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    left_mean = math.fsum(left_ranks) / len(left_ranks)
    right_mean = math.fsum(right_ranks) / len(right_ranks)
    covariance = math.fsum(
        (x - left_mean) * (y - right_mean)
        for x, y in zip(left_ranks, right_ranks, strict=True)
    )
    left_scale = math.sqrt(math.fsum((x - left_mean) ** 2 for x in left_ranks))
    right_scale = math.sqrt(math.fsum((y - right_mean) ** 2 for y in right_ranks))
    if left_scale == 0.0 or right_scale == 0.0:
        return None
    correlation = covariance / (left_scale * right_scale)
    if math.isclose(abs(correlation), 1.0, rel_tol=0.0, abs_tol=1e-12):
        return math.copysign(1.0, correlation)
    return correlation


def run_soc_tc_row(
    manifest: dict[str, Any],
    panel: dict[str, Any],
    engine: SpinEnergyEngine,
    fixture_contract: dict[str, Any],
    checkpoint: Any | None = None,
) -> dict[str, Any]:
    """Execute the locked panel, recording every spin failure without imputation."""
    predictions: list[dict[str, Any]] = []
    for case_index, material in enumerate(panel["materials"]):
        cached = (
            checkpoint.get_prediction(SOC_TC_ROW_ID, case_index, material)
            if checkpoint
            else None
        )
        if cached is not None:
            predictions.append(cached)
            continue
        try:
            fm = engine.evaluate_ordering(material, "fm")
            afm = engine.evaluate_ordering(material, "afm")
            prediction = derive_spin_observables(material, fm, afm)
        except Exception as exc:
            prediction = {
                "material_id": material.get("material_id"),
                "formula": material.get("formula"),
                "status": "failed",
                "error_class": exc.__class__.__name__,
                "error": str(exc),
            }
        else:
            if checkpoint is not None:
                checkpoint.record_prediction(SOC_TC_ROW_ID, case_index, material, prediction)
        predictions.append(prediction)

    completed = [item for item in predictions if item["status"] == "completed"]
    failed_count = len(predictions) - len(completed)
    minimum_count = int(panel["measurement"]["minimum_material_count"])
    measurement_complete = len(completed) >= minimum_count and failed_count == 0
    materials_by_id = {item["material_id"]: item for item in panel["materials"]}
    reference_mae = [
        float(materials_by_id[item["material_id"]]["reference"]["mae_xz_mev_per_cell"])
        for item in completed
    ]
    predicted_mae = [float(item["mae_xz_mev_per_cell"]) for item in completed]
    rank_correlation = _spearman(reference_mae, predicted_mae)
    sign_errors = sum(
        item["easy_axis"]
        != (
            "out_of_plane"
            if max(
                float(materials_by_id[item["material_id"]]["reference"]["mae_xz_mev_per_cell"]),
                float(materials_by_id[item["material_id"]]["reference"]["mae_yz_mev_per_cell"]),
            )
            < 0.0
            else "in_plane"
        )
        for item in completed
    )
    tc_errors = [
        abs(
            float(item["tc_k"]["rnsw"])
            - float(materials_by_id[item["material_id"]]["reference"]["tc_k"]["rnsw"])
        )
        for item in completed
    ]
    tc_rnsw_mae = math.fsum(tc_errors) / len(tc_errors) if tc_errors else None
    covered = 0
    for item in completed:
        low, high = materials_by_id[item["material_id"]]["reference"]["tc_envelope_k"]
        value = float(item["tc_k"]["rnsw"])
        if (
            float(low) <= value <= float(high)
            or math.isclose(value, float(low), rel_tol=0.0, abs_tol=1e-9)
            or math.isclose(value, float(high), rel_tol=0.0, abs_tol=1e-9)
        ):
            covered += 1
    envelope_coverage = covered / len(completed) if completed else None
    threshold = float(manifest["acceptance_test"]["threshold"])
    score = (
        max(0.0, min(1.0, float(rank_correlation)))
        if measurement_complete
        and rank_correlation is not None
        and rank_correlation >= threshold
        and sign_errors == 0
        else 0.0
    )
    metrics = {
        "primary_metric": "magnetocrystalline_anisotropy_rank_correlation",
        "magnetocrystalline_anisotropy_rank_correlation": rank_correlation,
        "easy_axis_sign_errors": sign_errors,
        "tc_rnsw_mae_k": tc_rnsw_mae,
        "tc_envelope_coverage": envelope_coverage,
        "completed_material_count": len(completed),
        "failed_material_count": failed_count,
        "minimum_material_count": minimum_count,
        "measurement_complete": measurement_complete,
        "acceptance_threshold": threshold,
    }
    return {
        "predictions": predictions,
        "score": score,
        "score_unit": "row_native_physical_score",
        "metrics": metrics,
        "row_spec": {
            "row_id": "soc_tc",
            "execution_protocol": panel["execution_protocol"],
            "measurement": panel["measurement"],
        },
        "fixture_contract": fixture_contract,
        "n_structures": len(panel["materials"]),
    }


# The strict v1 fixture runner is kept separate from the legacy locked-panel
# adapter above so already content-addressed Z2 campaign artifacts remain
# readable while new executions use the fail-closed, no-placeholder contract.
import z2_soc_tc_contract as _fixture_runner  # noqa: E402

CellMeasurementError = _fixture_runner.CellMeasurementError
load_fixture = _fixture_runner.load_fixture
run_soc_tc_rows = _fixture_runner.run_soc_tc_rows
validate_fixture = _fixture_runner.validate_fixture
