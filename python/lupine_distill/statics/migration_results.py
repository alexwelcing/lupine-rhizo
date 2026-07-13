"""Result dataclass for migration-barrier (CI-NEB) calculations."""

from __future__ import annotations

from dataclasses import dataclass

from lupine_distill.statics.report import result_dict


@dataclass(frozen=True)
class MigrationBarrierResult:
    """CI-NEB vacancy-hop migration barrier between two relaxed endpoints.

    ``forward_barrier_ev = e_saddle_ev - e_initial_ev`` and
    ``backward_barrier_ev = e_saddle_ev - e_final_ev``; for a symmetric hop
    (both endpoints the same minimum by symmetry) the two should match and
    ``barrier_asymmetry_ev`` measures the numerical residual — a symmetry
    identity, NOT convergence evidence. The convergence check is
    endpoint-vs-band-minimum (registered Round-3 fix, errata finding 12):
    ``endpoint_vs_band_min_delta_ev = min(interior) - min(endpoints)`` must
    be >= 0 (``endpoint_below_band``); an interior image below the lower
    relaxed endpoint means that endpoint missed its minimum and the barrier
    is untrustworthy (warned and recorded, never raised).
    """

    formula: str
    n_atoms: int
    n_images: int
    climb: bool
    neb_method: str
    interpolation_method: str
    optimizer: str
    fmax: float
    max_steps: int
    hop_distance_angstrom: float
    e_initial_ev: float
    e_final_ev: float
    e_saddle_ev: float
    forward_barrier_ev: float
    backward_barrier_ev: float
    barrier_asymmetry_ev: float
    endpoint_below_band: bool
    endpoint_vs_band_min_delta_ev: float
    saddle_image_index: int
    band_energies_ev: tuple[float, ...]
    n_relax_steps_initial: int
    n_relax_steps_final: int
    n_neb_steps: int
    n_pre_climb_steps: int
    n_force_calls: int | None
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "migration_barrier",
            "formula": self.formula,
            "n_atoms": self.n_atoms,
            "n_images": self.n_images,
            "climb": self.climb,
            "neb_method": self.neb_method,
            "interpolation_method": self.interpolation_method,
            "optimizer": self.optimizer,
            "fmax": self.fmax,
            "max_steps": self.max_steps,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "forward_barrier_ev": self.forward_barrier_ev,
            "backward_barrier_ev": self.backward_barrier_ev,
            "barrier_asymmetry_ev": self.barrier_asymmetry_ev,
            "endpoint_below_band": self.endpoint_below_band,
            "endpoint_vs_band_min_delta_ev": self.endpoint_vs_band_min_delta_ev,
            "e_initial_ev": self.e_initial_ev,
            "e_final_ev": self.e_final_ev,
            "e_saddle_ev": self.e_saddle_ev,
            "saddle_image_index": self.saddle_image_index,
            "band_energies_ev": self.band_energies_ev,
            "hop_distance_angstrom": self.hop_distance_angstrom,
            "n_relax_steps_initial": self.n_relax_steps_initial,
            "n_relax_steps_final": self.n_relax_steps_final,
            "n_neb_steps": self.n_neb_steps,
            "n_pre_climb_steps": self.n_pre_climb_steps,
            "n_force_calls": self.n_force_calls,
        }
        units = {
            "forward_barrier_ev": "eV",
            "backward_barrier_ev": "eV",
            "barrier_asymmetry_ev": "eV",
            "endpoint_vs_band_min_delta_ev": "eV",
            "e_initial_ev": "eV",
            "e_final_ev": "eV",
            "e_saddle_ev": "eV",
            "band_energies_ev": "eV",
            "hop_distance_angstrom": "Angstrom",
        }
        return result_dict(
            "migration_barrier", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


__all__ = ["MigrationBarrierResult"]
