"""Frozen result dataclasses for the bulk statics calculations.

Each result carries the physical values, every convergence parameter, and the
wall time of the run. ``canonical_inputs()`` is the deterministic,
JSON-serializable identity of the calculation (never timing); ``to_dict()``
wraps everything in the shared property/values/units envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

from lupine_distill.statics.report import result_dict


@dataclass(frozen=True)
class LatticeResult:
    """Relaxed lattice constant + cohesive energy from a recentring EOS scan."""

    formula: str
    structure_type: str
    a0_angstrom: float
    e0_ev_per_atom: float
    v0_a3_per_atom: float
    b0_gpa: float
    b0_prime: float
    cohesive_energy_ev_per_atom: float
    isolated_atom_energies_ev: tuple[tuple[str, float], ...]
    n_atoms_cell: int
    initial_a_angstrom: float
    volume_span: float
    n_points: int
    max_recenter: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "lattice",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "initial_a_angstrom": self.initial_a_angstrom,
            "volume_span": self.volume_span,
            "n_points": self.n_points,
            "max_recenter": self.max_recenter,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "a0_angstrom": self.a0_angstrom,
            "e0_ev_per_atom": self.e0_ev_per_atom,
            "v0_a3_per_atom": self.v0_a3_per_atom,
            "b0_gpa": self.b0_gpa,
            "b0_prime": self.b0_prime,
            "cohesive_energy_ev_per_atom": self.cohesive_energy_ev_per_atom,
            "isolated_atom_energies_ev": self.isolated_atom_energies_ev,
            "n_atoms_cell": self.n_atoms_cell,
        }
        units = {
            "a0_angstrom": "Angstrom",
            "e0_ev_per_atom": "eV/atom",
            "v0_a3_per_atom": "A^3/atom",
            "b0_gpa": "GPa",
            "b0_prime": "dimensionless",
            "cohesive_energy_ev_per_atom": "eV/atom",
            "isolated_atom_energies_ev": "eV",
        }
        return result_dict("lattice", values, units, self.canonical_inputs(), self.wall_time_seconds)


@dataclass(frozen=True)
class EosResult:
    """Birch-Murnaghan EOS at a fixed, caller-supplied lattice constant."""

    formula: str
    structure_type: str
    a0_angstrom: float
    volume_span: float
    n_points: int
    n_atoms_cell: int
    volumes_a3: tuple[float, ...]
    energies_ev: tuple[float, ...]
    e0_ev: float
    v0_a3: float
    v0_a3_per_atom: float
    b0_gpa: float
    b0_prime: float
    rms_residual_ev: float
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "eos",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "a0_angstrom": self.a0_angstrom,
            "volume_span": self.volume_span,
            "n_points": self.n_points,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "b0_gpa": self.b0_gpa,
            "b0_prime": self.b0_prime,
            "v0_a3_per_atom": self.v0_a3_per_atom,
            "e0_ev": self.e0_ev,
            "rms_residual_ev": self.rms_residual_ev,
            "volumes_a3": self.volumes_a3,
            "energies_ev": self.energies_ev,
            "n_atoms_cell": self.n_atoms_cell,
        }
        units = {
            "b0_gpa": "GPa",
            "b0_prime": "dimensionless",
            "v0_a3_per_atom": "A^3/atom",
            "e0_ev": "eV",
            "rms_residual_ev": "eV",
            "volumes_a3": "A^3",
            "energies_ev": "eV",
        }
        return result_dict("eos", values, units, self.canonical_inputs(), self.wall_time_seconds)


@dataclass(frozen=True)
class VacancyFormationResult:
    """Vacancy formation energy from a relaxed defective supercell."""

    formula: str
    structure_type: str
    a0_angstrom: float
    supercell: tuple[int, int, int]
    vacancy_index: int
    vacancy_species: str
    n_atoms_perfect: int
    e_bulk_ev: float
    e_defect_ev: float
    vacancy_formation_ev: float
    n_relax_steps: int
    fmax: float
    optimizer: str
    max_steps: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "vacancy_formation",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "a0_angstrom": self.a0_angstrom,
            "supercell": self.supercell,
            "vacancy_index": self.vacancy_index,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "vacancy_formation_ev": self.vacancy_formation_ev,
            "vacancy_species": self.vacancy_species,
            "n_atoms_perfect": self.n_atoms_perfect,
            "e_bulk_ev": self.e_bulk_ev,
            "e_defect_ev": self.e_defect_ev,
            "n_relax_steps": self.n_relax_steps,
        }
        units = {
            "vacancy_formation_ev": "eV",
            "e_bulk_ev": "eV",
            "e_defect_ev": "eV",
        }
        return result_dict(
            "vacancy_formation", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


@dataclass(frozen=True)
class FormationEnthalpyResult:
    """Formation enthalpy vs same-calculator relaxed elemental references."""

    formula: str
    structure_type: str
    references: tuple[tuple[str, str], ...]
    elemental_energies_ev_per_atom: tuple[tuple[str, float], ...]
    compound_a0_angstrom: float
    compound_e0_ev_per_atom: float
    formation_enthalpy_ev_per_atom: float
    n_atoms_cell: int
    volume_span: float
    n_points: int
    max_recenter: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "formation_enthalpy",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "references": self.references,
            "volume_span": self.volume_span,
            "n_points": self.n_points,
            "max_recenter": self.max_recenter,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "formation_enthalpy_ev_per_atom": self.formation_enthalpy_ev_per_atom,
            "compound_a0_angstrom": self.compound_a0_angstrom,
            "compound_e0_ev_per_atom": self.compound_e0_ev_per_atom,
            "elemental_energies_ev_per_atom": self.elemental_energies_ev_per_atom,
            "references": self.references,
            "n_atoms_cell": self.n_atoms_cell,
        }
        units = {
            "formation_enthalpy_ev_per_atom": "eV/atom",
            "compound_a0_angstrom": "Angstrom",
            "compound_e0_ev_per_atom": "eV/atom",
            "elemental_energies_ev_per_atom": "eV/atom",
        }
        return result_dict(
            "formation_enthalpy", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


__all__ = [
    "EosResult",
    "FormationEnthalpyResult",
    "LatticeResult",
    "VacancyFormationResult",
]
