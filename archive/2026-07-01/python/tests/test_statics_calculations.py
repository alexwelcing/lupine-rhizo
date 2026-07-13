"""Unit tests for lupine_distill.statics.calculations with the ASE EMT calculator.

EMT is deterministic, CPU-only, and parameterised for Ni/Cu/Al -- ideal for
asserting physical sanity of the Tier-1 statics core without a GPU.
"""

from __future__ import annotations

import json
import math

import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    InputValidationError,
    compute_formation_enthalpy,
    compute_lattice,
    compute_vacancy_formation,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def ni_lattice():
    """Relaxed EMT Ni fcc lattice, shared across the module (deterministic)."""
    return compute_lattice(EMT(), "Ni", "fcc")


class TestLattice:
    def test_ni_fcc_lattice_constant(self, ni_lattice) -> None:
        assert 3.4 < ni_lattice.a0_angstrom < 3.7

    def test_ni_cohesive_energy_positive_and_sane(self, ni_lattice) -> None:
        assert 3.0 < ni_lattice.cohesive_energy_ev_per_atom < 6.0

    def test_result_records_parameters(self, ni_lattice) -> None:
        assert ni_lattice.volume_span == pytest.approx(0.06)
        assert ni_lattice.n_points == 11
        assert ni_lattice.wall_time_seconds >= 0.0

    def test_canonical_inputs_deterministic(self, ni_lattice) -> None:
        again = compute_lattice(EMT(), "Ni", "fcc")
        c1, c2 = ni_lattice.canonical_inputs(), again.canonical_inputs()
        assert c1 == c2
        assert json.dumps(c1, sort_keys=True) == json.dumps(c2, sort_keys=True)
        assert "wall_time_seconds" not in c1
        assert ni_lattice.a0_angstrom == pytest.approx(again.a0_angstrom, abs=1e-10)

    def test_to_dict_is_json_serializable(self, ni_lattice) -> None:
        blob = json.dumps(ni_lattice.to_dict())
        parsed = json.loads(blob)
        assert parsed["property"] == "lattice"
        assert "units" in parsed and "values" in parsed and "canonical_inputs" in parsed

    def test_lattice_input_validation(self) -> None:
        with pytest.raises(InputValidationError):
            compute_lattice(EMT(), "Ni", "fcc", volume_span=-0.1)
        with pytest.raises(InputValidationError):
            compute_lattice(EMT(), "Ni", "fcc", n_points=2)
        with pytest.raises(InputValidationError):
            compute_lattice(EMT(), "Ni", "notastructure")


class TestVacancy:
    def test_ni_vacancy_formation_energy(self, ni_lattice) -> None:
        result = compute_vacancy_formation(EMT(), "Ni", "fcc", ni_lattice.a0_angstrom)
        assert result.vacancy_formation_ev > 0.0
        assert 1.0 < result.vacancy_formation_ev < 2.0
        assert result.n_atoms_perfect == 108  # 3x3x3 conventional fcc
        assert result.vacancy_species == "Ni"
        assert result.n_relax_steps >= 1

    def test_vacancy_input_validation(self, ni_lattice) -> None:
        a0 = ni_lattice.a0_angstrom
        with pytest.raises(InputValidationError):
            compute_vacancy_formation(EMT(), "Ni", "fcc", a0, supercell=(0, 3, 3))
        with pytest.raises(InputValidationError):
            compute_vacancy_formation(EMT(), "Ni", "fcc", a0, vacancy_index=100000)
        with pytest.raises(InputValidationError):
            compute_vacancy_formation(EMT(), "Ni", "fcc", a0, fmax=-0.01)
        with pytest.raises(InputValidationError):
            compute_vacancy_formation(EMT(), "Ni", "fcc", a0, optimizer="ADAM")
        with pytest.raises(InputValidationError):
            compute_vacancy_formation(EMT(), "Ni", "fcc", a0, max_steps=0)

    def test_vacancy_canonical_inputs_deterministic(self, ni_lattice) -> None:
        a0 = ni_lattice.a0_angstrom
        r1 = compute_vacancy_formation(EMT(), "Ni", "fcc", a0, supercell=(2, 2, 2))
        r2 = compute_vacancy_formation(EMT(), "Ni", "fcc", a0, supercell=(2, 2, 2))
        assert r1.canonical_inputs() == r2.canonical_inputs()
        assert r1.vacancy_formation_ev == pytest.approx(r2.vacancy_formation_ev, abs=1e-8)
        blob = json.dumps(r1.canonical_inputs(), sort_keys=True)
        assert "supercell" in blob


class TestFormationEnthalpy:
    def test_b2_nial_formation_enthalpy_finite(self) -> None:
        result = compute_formation_enthalpy(EMT(), "NiAl", "b2")
        assert math.isfinite(result.formation_enthalpy_ev_per_atom)
        refs = dict(result.references)
        assert refs == {"Ni": "fcc", "Al": "fcc"}
        elemental = dict(result.elemental_energies_ev_per_atom)
        assert set(elemental) == {"Ni", "Al"}
        assert result.wall_time_seconds >= 0.0

    def test_formation_enthalpy_rejects_element(self) -> None:
        with pytest.raises(InputValidationError):
            compute_formation_enthalpy(EMT(), "Ni", "fcc")

    def test_formation_canonical_inputs_deterministic(self) -> None:
        r1 = compute_formation_enthalpy(EMT(), "NiAl", "b2")
        r2 = compute_formation_enthalpy(EMT(), "NiAl", "b2")
        assert r1.canonical_inputs() == r2.canonical_inputs()
        assert json.dumps(r1.canonical_inputs(), sort_keys=True) == json.dumps(
            r2.canonical_inputs(), sort_keys=True
        )
