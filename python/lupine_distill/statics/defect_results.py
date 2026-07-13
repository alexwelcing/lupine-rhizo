"""Result dataclasses for compound-defect calculations (Schottky, referenced vacancy)."""

from __future__ import annotations

from dataclasses import dataclass

from lupine_distill.statics.report import result_dict


@dataclass(frozen=True)
class SchottkyFormationResult:
    """Charge-balanced Schottky-pair formation energy in a 1:1 binary."""

    formula: str
    structure_type: str
    a0_angstrom: float
    supercell: tuple[int, int, int]
    removed_indices: tuple[int, int]
    removed_species: tuple[str, str]
    pair_separation_angstrom: float
    n_atoms_perfect: int
    e_bulk_ev: float
    e_defect_ev: float
    schottky_pair_ev: float
    schottky_per_vacancy_ev: float
    n_relax_steps: int
    fmax: float
    optimizer: str
    max_steps: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "schottky_formation",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "a0_angstrom": self.a0_angstrom,
            "supercell": self.supercell,
            "removed_indices": self.removed_indices,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "schottky_pair_ev": self.schottky_pair_ev,
            "schottky_per_vacancy_ev": self.schottky_per_vacancy_ev,
            "removed_species": self.removed_species,
            "pair_separation_angstrom": self.pair_separation_angstrom,
            "n_atoms_perfect": self.n_atoms_perfect,
            "e_bulk_ev": self.e_bulk_ev,
            "e_defect_ev": self.e_defect_ev,
            "n_relax_steps": self.n_relax_steps,
        }
        units = {
            "schottky_pair_ev": "eV",
            "schottky_per_vacancy_ev": "eV",
            "pair_separation_angstrom": "Angstrom",
            "e_bulk_ev": "eV",
            "e_defect_ev": "eV",
        }
        return result_dict(
            "schottky_formation", values, units, self.canonical_inputs(), self.wall_time_seconds
        )


@dataclass(frozen=True)
class ReferencedVacancyFormationResult:
    """Single-species vacancy in a compound, referenced to the elemental bulk."""

    formula: str
    structure_type: str
    a0_angstrom: float
    supercell: tuple[int, int, int]
    vacancy_index: int
    vacancy_species: str
    reference_structure: str
    mu_ev_per_atom: float
    n_atoms_perfect: int
    e_bulk_ev: float
    e_defect_ev: float
    vacancy_formation_ev: float
    n_relax_steps: int
    fmax: float
    optimizer: str
    max_steps: int
    volume_span: float
    n_points: int
    max_recenter: int
    wall_time_seconds: float

    def canonical_inputs(self) -> dict[str, object]:
        return {
            "property": "referenced_vacancy_formation",
            "formula": self.formula,
            "structure_type": self.structure_type,
            "a0_angstrom": self.a0_angstrom,
            "supercell": self.supercell,
            "vacancy_index": self.vacancy_index,
            "vacancy_species": self.vacancy_species,
            "reference_structure": self.reference_structure,
            "fmax": self.fmax,
            "optimizer": self.optimizer,
            "max_steps": self.max_steps,
            "volume_span": self.volume_span,
            "n_points": self.n_points,
            "max_recenter": self.max_recenter,
        }

    def to_dict(self) -> dict[str, object]:
        values = {
            "vacancy_formation_ev": self.vacancy_formation_ev,
            "vacancy_species": self.vacancy_species,
            "reference_structure": self.reference_structure,
            "mu_ev_per_atom": self.mu_ev_per_atom,
            "n_atoms_perfect": self.n_atoms_perfect,
            "e_bulk_ev": self.e_bulk_ev,
            "e_defect_ev": self.e_defect_ev,
            "n_relax_steps": self.n_relax_steps,
        }
        units = {
            "vacancy_formation_ev": "eV",
            "mu_ev_per_atom": "eV/atom",
            "e_bulk_ev": "eV",
            "e_defect_ev": "eV",
        }
        return result_dict(
            "referenced_vacancy_formation",
            values,
            units,
            self.canonical_inputs(),
            self.wall_time_seconds,
        )


__all__ = [
    "ReferencedVacancyFormationResult",
    "SchottkyFormationResult",
]
