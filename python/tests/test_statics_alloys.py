"""Unit tests for lupine_distill.statics.alloys (RSS supercell builder).

Pure structure building + input validation: no calculator, no GPU.
"""

from __future__ import annotations

import numpy as np
import pytest
from ase.data import atomic_numbers, reference_states

from lupine_distill.statics import (
    InputValidationError,
    build_rss_supercell,
    estimate_rss_lattice_constant,
    site_counts_for_supercell,
)

pytestmark = pytest.mark.unit


class TestSiteCounts:
    def test_equiatomic_binary_fcc(self) -> None:
        counts = site_counts_for_supercell({"Ni": 1, "Cu": 1}, "fcc", 2)
        assert counts == {"Ni": 16, "Cu": 16}

    def test_ratio_scales_exactly(self) -> None:
        counts = site_counts_for_supercell({"Ni": 3, "Cu": 1}, "fcc", 2)
        assert counts == {"Ni": 24, "Cu": 8}

    def test_quinary_hea_fcc(self) -> None:
        composition = {"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1}
        # 4 * 5^3 = 500 sites -> 100 each.
        counts = site_counts_for_supercell(composition, "fcc", 5)
        assert all(n == 100 for n in counts.values())

    def test_indivisible_composition_errors(self) -> None:
        # 4 * 2^3 = 32 sites cannot realize a 1:1:1 ternary exactly.
        with pytest.raises(InputValidationError, match="cannot realize"):
            site_counts_for_supercell({"Co": 1, "Cr": 1, "Ni": 1}, "fcc", 2)

    def test_bcc_sites_per_cell(self) -> None:
        counts = site_counts_for_supercell({"Fe": 1, "Cr": 1}, "bcc", 2)
        assert counts == {"Fe": 8, "Cr": 8}


class TestBuildRssSupercell:
    def test_counts_exact_and_total_sites(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 42)
        symbols = atoms.get_chemical_symbols()
        assert len(atoms) == 32
        assert symbols.count("Ni") == 16
        assert symbols.count("Cu") == 16

    def test_cell_and_pbc(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 42)
        assert np.allclose(atoms.cell.array, 2 * 3.56 * np.eye(3))
        assert all(atoms.pbc)

    def test_bcc_cell(self) -> None:
        atoms = build_rss_supercell({"Fe": 1, "Cr": 1}, "bcc", 2.87, 3, 0)
        assert len(atoms) == 2 * 27
        assert np.allclose(atoms.cell.array, 3 * 2.87 * np.eye(3))

    def test_deterministic_per_seed(self) -> None:
        a = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 7)
        b = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 7)
        assert a.get_chemical_symbols() == b.get_chemical_symbols()
        assert np.allclose(a.get_positions(), b.get_positions())

    def test_different_seeds_differ(self) -> None:
        a = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 1)
        b = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 2)
        assert a.get_chemical_symbols() != b.get_chemical_symbols()
        # Same lattice, only occupation differs.
        assert np.allclose(a.get_positions(), b.get_positions())

    def test_sites_are_mixed_not_blocked(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, 42)
        symbols = atoms.get_chemical_symbols()
        # A permutation should not leave the composition-ordered block intact.
        assert symbols != ["Ni"] * 16 + ["Cu"] * 16

    def test_repeat_one(self) -> None:
        atoms = build_rss_supercell({"Ni": 1, "Cu": 3}, "fcc", 3.60, 1, 0)
        assert len(atoms) == 4
        assert atoms.get_chemical_symbols().count("Ni") == 1


class TestBuildValidation:
    def test_unknown_structure_type(self) -> None:
        with pytest.raises(InputValidationError, match="structure_type"):
            build_rss_supercell({"Ni": 1, "Cu": 1}, "hcp", 3.56, 2, 0)

    def test_unknown_element(self) -> None:
        with pytest.raises(InputValidationError, match="unknown element"):
            build_rss_supercell({"Xx": 1, "Cu": 1}, "fcc", 3.56, 2, 0)

    def test_empty_composition(self) -> None:
        with pytest.raises(InputValidationError, match="non-empty"):
            build_rss_supercell({}, "fcc", 3.56, 2, 0)

    def test_nonpositive_count(self) -> None:
        with pytest.raises(InputValidationError, match="positive integer"):
            build_rss_supercell({"Ni": 0, "Cu": 1}, "fcc", 3.56, 2, 0)

    def test_bad_lattice_constant(self) -> None:
        with pytest.raises(InputValidationError, match="lattice_constant"):
            build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", -1.0, 2, 0)

    def test_bad_repeat(self) -> None:
        with pytest.raises(InputValidationError, match="repeat"):
            build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 0, 0)

    def test_bad_seed(self) -> None:
        with pytest.raises(InputValidationError, match="seed"):
            build_rss_supercell({"Ni": 1, "Cu": 1}, "fcc", 3.56, 2, -1)

    def test_indivisible_errors(self) -> None:
        with pytest.raises(InputValidationError, match="cannot realize"):
            build_rss_supercell({"Ni": 1, "Cu": 1, "Pd": 1}, "fcc", 3.7, 2, 0)


class TestEstimateRssLatticeConstant:
    def test_pure_element_matches_reference(self) -> None:
        ref_a = float(reference_states[atomic_numbers["Ni"]]["a"])
        assert estimate_rss_lattice_constant({"Ni": 1}, "fcc") == pytest.approx(ref_a)

    def test_vegard_between_endpoints(self) -> None:
        a_ni = estimate_rss_lattice_constant({"Ni": 1}, "fcc")
        a_cu = estimate_rss_lattice_constant({"Cu": 1}, "fcc")
        a_mix = estimate_rss_lattice_constant({"Ni": 1, "Cu": 1}, "fcc")
        assert a_mix == pytest.approx((a_ni + a_cu) / 2.0)
        assert min(a_ni, a_cu) <= a_mix <= max(a_ni, a_cu)

    def test_composition_weighting(self) -> None:
        a_ni = estimate_rss_lattice_constant({"Ni": 1}, "fcc")
        a_cu = estimate_rss_lattice_constant({"Cu": 1}, "fcc")
        a_31 = estimate_rss_lattice_constant({"Ni": 3, "Cu": 1}, "fcc")
        assert a_31 == pytest.approx((3 * a_ni + a_cu) / 4.0)

    def test_covalent_fallback_for_wrong_symmetry(self) -> None:
        # Cu's reference ground state is fcc, not bcc: bcc must use the
        # covalent-radius nearest-neighbour fallback, not the fcc table value.
        a_bcc = estimate_rss_lattice_constant({"Cu": 1}, "bcc")
        a_fcc = estimate_rss_lattice_constant({"Cu": 1}, "fcc")
        assert a_bcc != pytest.approx(a_fcc)
        assert 2.0 < a_bcc < 4.0

    def test_validation_errors(self) -> None:
        with pytest.raises(InputValidationError):
            estimate_rss_lattice_constant({}, "fcc")
        with pytest.raises(InputValidationError):
            estimate_rss_lattice_constant({"Ni": 1}, "perovskite")
