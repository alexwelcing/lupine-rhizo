"""Frozen result dataclasses for surface energies and the stacking fault.

Same contract as :mod:`lupine_distill.statics.results`: physical values plus
all convergence parameters, deterministic JSON-serializable
``canonical_inputs()`` (never timing), and the shared ``to_dict()`` envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

from lupine_distill.statics.report import result_dict


@dataclass(frozen=True)
class SurfaceEnergyResult:
    """Relaxed surface energy for one Miller plane."""

    formula: str
    structure_type: str
    miller: str
    a0_angstrom: float
    layers: int
    vacuum_angstrom: float
    n_atoms_slab: int
    area_a2: float
    e_slab_ev: float
    e_bulk_ev_per_atom: float
    gamma_j_per_m2: float
    n_relax_steps: int
    fmax: float
    optimizer: str
    max_steps: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "surface_energy",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "miller": self.miller,
            "a0_angstrom": self.a0_angstrom,
            "layers": self.layers,
            "vacuum_angstrom": self.vacuum_angstrom,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "gamma_j_per_m2": self.gamma_j_per_m2,
            "miller": self.miller,
            "n_atoms_slab": self.n_atoms_slab,
            "area_a2": self.area_a2,
            "e_slab_ev": self.e_slab_ev,
            "e_bulk_ev_per_atom": self.e_bulk_ev_per_atom,
            "n_relax_steps": self.n_relax_steps,
        }
        units = {
            "gamma_j_per_m2": "J/m^2",
            "area_a2": "A^2",
            "e_slab_ev": "eV",
            "e_bulk_ev_per_atom": "eV/atom",
        }
        return result_dict(
            "surface_energy", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


@dataclass(frozen=True)
class StackingFaultResult:
    """Intrinsic stacking-fault energy (fcc) from the displaced-slab method."""

    formula: str
    a0_angstrom: float
    layers: int
    vacuum_angstrom: float
    area_a2: float
    sfe_mj_per_m2: float
    hcp_proxy_mj_per_m2: float
    method: str
    displacement_sign: int
    n_relax_steps: int
    fmax: float
    optimizer: str
    max_steps: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "stacking_fault_energy",
            "formula": self.formula,
            "structure_type": "fcc",
            "method": self.method,
            "a0_angstrom": self.a0_angstrom,
            "layers": self.layers,
            "vacuum_angstrom": self.vacuum_angstrom,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "sfe_mj_per_m2": self.sfe_mj_per_m2,
            "hcp_proxy_mj_per_m2": self.hcp_proxy_mj_per_m2,
            "method": self.method,
            "displacement_sign": self.displacement_sign,
            "area_a2": self.area_a2,
            "n_relax_steps": self.n_relax_steps,
        }
        units = {
            "sfe_mj_per_m2": "mJ/m^2",
            "hcp_proxy_mj_per_m2": "mJ/m^2",
            "area_a2": "A^2",
        }
        return result_dict(
            "stacking_fault_energy", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


__all__ = [
    "StackingFaultResult",
    "SurfaceEnergyResult",
]
