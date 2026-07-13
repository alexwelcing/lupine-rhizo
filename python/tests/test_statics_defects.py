"""Unit tests for lupine_distill.statics.defects (compound defects) with EMT.

EMT is not a physical model for these compounds; the tests check machinery
(stoichiometry bookkeeping, site selection, references, validation), not
chemistry.
"""

from __future__ import annotations

import numpy as np
import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    InputValidationError,
    compute_referenced_vacancy_formation,
    compute_schottky_formation,
)

pytestmark = pytest.mark.unit

_A0_NICU_B2 = 2.9
_A0_NI3AL_L12 = 3.57


class TestSchottkyFormation:
    def test_b2_pair_removal_bookkeeping(self) -> None:
        result = compute_schottky_formation(
            EMT(), "NiCu", "b2", _A0_NICU_B2, supercell=(3, 3, 3)
        )
        assert result.n_atoms_perfect == 54
        assert set(result.removed_species) == {"Ni", "Cu"}
        assert len(set(result.removed_indices)) == 2
        # The two vacancies are pushed apart, not adjacent (a 3x3x3 cell has
        # non-nearest anion shells under minimum image; 2x2x2 would not).
        assert result.pair_separation_angstrom > _A0_NICU_B2
        assert np.isfinite(result.schottky_pair_ev)
        assert result.schottky_per_vacancy_ev == pytest.approx(
            result.schottky_pair_ev / 2.0
        )
        assert result.wall_time_seconds > 0.0

    def test_to_dict_envelope(self) -> None:
        result = compute_schottky_formation(
            EMT(), "NiCu", "b2", _A0_NICU_B2, supercell=(2, 2, 2)
        )
        payload = result.to_dict()
        assert payload["property"] == "schottky_formation"
        assert payload["units"]["schottky_pair_ev"] == "eV"
        assert payload["canonical_inputs"]["supercell"] == (2, 2, 2)

    def test_rejects_elemental_structure(self) -> None:
        with pytest.raises(InputValidationError):
            compute_schottky_formation(EMT(), "Ni", "fcc", 3.52)

    def test_rejects_non_1_1_structure(self) -> None:
        with pytest.raises(InputValidationError):
            compute_schottky_formation(EMT(), "Ni3Al", "l12", _A0_NI3AL_L12)

    def test_rejects_bad_supercell(self) -> None:
        with pytest.raises(InputValidationError):
            compute_schottky_formation(
                EMT(), "NiCu", "b2", _A0_NICU_B2, supercell=(0, 2, 2)
            )


class TestReferencedVacancyFormation:
    def test_l12_minority_vacancy(self) -> None:
        result = compute_referenced_vacancy_formation(
            EMT(),
            "Ni3Al",
            "l12",
            _A0_NI3AL_L12,
            vacancy_species="Al",
            supercell=(2, 2, 2),
        )
        assert result.vacancy_species == "Al"
        assert result.reference_structure == "fcc"
        assert result.n_atoms_perfect == 32
        assert np.isfinite(result.mu_ev_per_atom)
        assert np.isfinite(result.vacancy_formation_ev)
        # Identity: E_vac = E_defect + mu - E_bulk.
        assert result.vacancy_formation_ev == pytest.approx(
            result.e_defect_ev + result.mu_ev_per_atom - result.e_bulk_ev
        )

    def test_reference_structure_override(self) -> None:
        result = compute_referenced_vacancy_formation(
            EMT(),
            "Ni3Al",
            "l12",
            _A0_NI3AL_L12,
            vacancy_species="Al",
            supercell=(2, 2, 2),
            reference_structure="bcc",
        )
        assert result.reference_structure == "bcc"

    def test_to_dict_envelope(self) -> None:
        result = compute_referenced_vacancy_formation(
            EMT(),
            "Ni3Al",
            "l12",
            _A0_NI3AL_L12,
            vacancy_species="Al",
            supercell=(2, 2, 2),
        )
        payload = result.to_dict()
        assert payload["property"] == "referenced_vacancy_formation"
        assert payload["values"]["vacancy_species"] == "Al"

    def test_rejects_species_not_in_formula(self) -> None:
        with pytest.raises(InputValidationError):
            compute_referenced_vacancy_formation(
                EMT(), "Ni3Al", "l12", _A0_NI3AL_L12, vacancy_species="Cu"
            )

    def test_rejects_elemental_formula(self) -> None:
        with pytest.raises(InputValidationError):
            compute_referenced_vacancy_formation(
                EMT(), "Ni", "fcc", 3.52, vacancy_species="Ni"
            )

    def test_rejects_unsupported_reference_override(self) -> None:
        with pytest.raises(InputValidationError):
            compute_referenced_vacancy_formation(
                EMT(),
                "Ni3Al",
                "l12",
                _A0_NI3AL_L12,
                vacancy_species="Al",
                reference_structure="l12",
            )
