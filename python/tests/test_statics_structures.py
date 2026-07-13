"""Unit tests for lupine_distill.statics.structures.

Pure structure building + input validation: no calculator, no GPU.
"""

from __future__ import annotations

import numpy as np
import pytest

from lupine_distill.statics import (
    SUPPORTED_STRUCTURE_TYPES,
    InputValidationError,
    build_structure,
    estimate_lattice_constant,
)

pytestmark = pytest.mark.unit


class TestBuildStructure:
    def test_fcc_conventional_cell(self) -> None:
        atoms = build_structure("Ni", "fcc", 3.52)
        assert len(atoms) == 4
        assert np.allclose(atoms.cell.array, 3.52 * np.eye(3))
        assert all(atoms.pbc)
        assert set(atoms.get_chemical_symbols()) == {"Ni"}

    def test_bcc_conventional_cell(self) -> None:
        atoms = build_structure("Fe", "bcc", 2.87)
        assert len(atoms) == 2
        assert np.allclose(atoms.cell.array, 2.87 * np.eye(3))

    def test_diamond_conventional_cell(self) -> None:
        atoms = build_structure("Si", "diamond", 5.43)
        assert len(atoms) == 8
        assert np.allclose(atoms.cell.array, 5.43 * np.eye(3))

    def test_rocksalt_conventional_cell(self) -> None:
        atoms = build_structure("NaCl", "rocksalt", 5.64)
        assert len(atoms) == 8
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("Na") == 4
        assert symbols.count("Cl") == 4

    def test_b2_cell(self) -> None:
        atoms = build_structure("NiAl", "b2", 2.88)
        assert len(atoms) == 2
        assert set(atoms.get_chemical_symbols()) == {"Ni", "Al"}
        assert np.allclose(atoms.cell.array, 2.88 * np.eye(3))

    def test_l12_cell(self) -> None:
        atoms = build_structure("Ni3Al", "l12", 3.57)
        assert len(atoms) == 4
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("Ni") == 3
        assert symbols.count("Al") == 1
        assert np.allclose(atoms.cell.array, 3.57 * np.eye(3))
        # Minority species sits on the cube corner.
        corner = np.argmin(np.linalg.norm(atoms.get_positions(), axis=1))
        assert symbols[corner] == "Al"

    def test_antifluorite_conventional_cell(self) -> None:
        atoms = build_structure("Li2S", "antifluorite", 5.7)
        assert len(atoms) == 12
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("Li") == 8
        assert symbols.count("S") == 4
        assert np.allclose(atoms.cell.array, 5.7 * np.eye(3))
        assert all(atoms.pbc)
        # Minority species (S) sits on the fcc corner site.
        corner = np.argmin(np.linalg.norm(atoms.get_positions(), axis=1))
        assert symbols[corner] == "S"
        # Nearest-neighbour Li-S distance is a*sqrt(3)/4 (tetrahedral holes).
        distances = atoms.get_all_distances(mic=True)
        np.fill_diagonal(distances, np.inf)
        assert distances.min() == pytest.approx(5.7 * np.sqrt(3.0) / 4.0)

    def test_antifluorite_formula_order_does_not_matter(self) -> None:
        atoms = build_structure("SLi2", "antifluorite", 5.7)
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("Li") == 8
        assert symbols.count("S") == 4

    def test_perovskite_conventional_cell(self) -> None:
        atoms = build_structure("CsSnI3", "perovskite", 6.22)
        assert len(atoms) == 5
        symbols = atoms.get_chemical_symbols()
        assert symbols.count("Cs") == 1
        assert symbols.count("Sn") == 1
        assert symbols.count("I") == 3
        assert np.allclose(atoms.cell.array, 6.22 * np.eye(3))
        assert all(atoms.pbc)
        # First singleton (A site, 12-coordinate) sits on the cube corner.
        corner = np.argmin(np.linalg.norm(atoms.get_positions(), axis=1))
        assert symbols[corner] == "Cs"
        # B-X (octahedral) nearest-neighbour distance is a/2.
        distances = atoms.get_all_distances(mic=True)
        np.fill_diagonal(distances, np.inf)
        assert distances.min() == pytest.approx(6.22 / 2.0)

    def test_perovskite_first_singleton_takes_a_site(self) -> None:
        # Formula order is semantic: the first count-1 element is the A site.
        atoms = build_structure("SnCsI3", "perovskite", 6.22)
        symbols = atoms.get_chemical_symbols()
        corner = np.argmin(np.linalg.norm(atoms.get_positions(), axis=1))
        assert symbols[corner] == "Sn"

    def test_structure_type_is_case_insensitive(self) -> None:
        assert len(build_structure("NiAl", "B2", 2.88)) == 2
        assert len(build_structure("Ni", "FCC", 3.52)) == 4

    def test_supported_structures_constant(self) -> None:
        assert set(SUPPORTED_STRUCTURE_TYPES) == {
            "fcc",
            "bcc",
            "diamond",
            "rocksalt",
            "b2",
            "l12",
            "antifluorite",
            "perovskite",
        }


class TestBuildStructureValidation:
    def test_unknown_structure_type(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Ni", "hcp", 3.52)

    def test_fcc_rejects_compound(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("NiAl", "fcc", 3.52)

    def test_rocksalt_rejects_element(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Ni", "rocksalt", 4.2)

    def test_rocksalt_rejects_off_stoichiometry(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Ni2O", "rocksalt", 4.2)

    def test_l12_rejects_wrong_stoichiometry(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("NiAl", "l12", 3.57)

    def test_antifluorite_rejects_1_1_stoichiometry(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("LiS", "antifluorite", 5.7)

    def test_antifluorite_rejects_element(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Li", "antifluorite", 5.7)

    def test_rocksalt_rejects_2_1_stoichiometry(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Li2S", "rocksalt", 5.2)

    def test_perovskite_rejects_binary(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("SnI3", "perovskite", 6.2)

    def test_perovskite_rejects_wrong_anion_count(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("CsSnI2", "perovskite", 6.2)

    def test_perovskite_rejects_two_singletons_missing(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Cs2SnI3", "perovskite", 6.2)

    def test_nonpositive_lattice_constant(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Ni", "fcc", 0.0)
        with pytest.raises(InputValidationError):
            build_structure("Ni", "fcc", -1.0)

    def test_absurd_lattice_constant(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Ni", "fcc", 500.0)

    def test_bad_formula_string(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Q!x", "fcc", 3.5)

    def test_empty_formula(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("", "fcc", 3.5)

    def test_unknown_element_symbol(self) -> None:
        with pytest.raises(InputValidationError):
            build_structure("Zz", "fcc", 3.5)


class TestEstimateLatticeConstant:
    def test_ni_fcc_uses_reference_state(self) -> None:
        assert estimate_lattice_constant("Ni", "fcc") == pytest.approx(3.52, abs=0.01)

    def test_fe_bcc_uses_reference_state(self) -> None:
        assert estimate_lattice_constant("Fe", "bcc") == pytest.approx(2.87, abs=0.02)

    def test_b2_nial_guess_is_reasonable(self) -> None:
        a = estimate_lattice_constant("NiAl", "b2")
        assert 2.5 < a < 3.3

    def test_l12_ni3al_guess_is_reasonable(self) -> None:
        a = estimate_lattice_constant("Ni3Al", "l12")
        assert 3.1 < a < 4.0

    def test_antifluorite_li2s_guess_is_reasonable(self) -> None:
        # Li2S antifluorite (mp-1153-like) has a0 ~ 5.7 A; the covalent-radius
        # guess only needs to land within the EOS recentring budget.
        a = estimate_lattice_constant("Li2S", "antifluorite")
        assert 4.5 < a < 6.5

    def test_perovskite_cssni3_guess_is_reasonable(self) -> None:
        # CsSnI3 cubic perovskite (mp-27381-like) has a0 ~ 6.22 A; the B-X
        # covalent-radius guess only needs to land within the recentring budget.
        a = estimate_lattice_constant("CsSnI3", "perovskite")
        assert 5.0 < a < 7.0

    def test_unknown_structure_raises(self) -> None:
        with pytest.raises(InputValidationError):
            estimate_lattice_constant("Ni", "hcp")

    def test_composition_validated(self) -> None:
        with pytest.raises(InputValidationError):
            estimate_lattice_constant("Ni3Al", "b2")
