"""Unit tests for lupine_distill.statics.migration (vacancy-hop CI-NEB), EMT-only.

EMT has no halides, so the NEB machinery is exercised on the elemental fcc
vacancy hop (``build_fcc_vacancy_hop``) — EMT Al vacancy migration is a
classic (~0.4-0.6 eV). The rocksalt cation-hop builder is tested on geometry
and validation only (no EMT energetics for LiF). Tests check MACHINERY:
deterministic site selection, endpoint bookkeeping, barrier identities,
fail-fast validation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    InputValidationError,
    MigrationBarrierResult,
    build_cation_vacancy_hop,
    build_fcc_vacancy_hop,
    compute_migration_barrier,
    endpoint_band_minimum_check,
)

pytestmark = pytest.mark.unit

_AL_A0 = 4.05
_LIF_A0 = 4.09


@pytest.fixture(scope="module")
def al_hop():
    """Unrelaxed Al fcc vacancy-hop endpoints (2x2x2, 32 -> 31 atoms)."""
    return build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=2)


@pytest.fixture(scope="module")
def al_barrier(al_hop) -> MigrationBarrierResult:
    """One shared EMT CI-NEB run (module-scoped: the expensive fixture)."""
    initial, final, _ = al_hop
    return compute_migration_barrier(
        EMT(), initial, final, n_images=3, fmax=0.05, max_steps=300, climb=True
    )


class TestFccVacancyHopBuilder:
    def test_endpoint_bookkeeping(self, al_hop) -> None:
        initial, final, hop_distance = al_hop
        assert len(initial) == 31  # 2x2x2 fcc conventional = 32 atoms - 1
        assert len(final) == 31
        assert initial.get_chemical_symbols() == final.get_chemical_symbols()
        assert np.allclose(initial.get_cell()[:], final.get_cell()[:])
        assert hop_distance == pytest.approx(_AL_A0 / math.sqrt(2.0))

    def test_exactly_one_atom_moves(self, al_hop) -> None:
        initial, final, hop_distance = al_hop
        displacements = np.linalg.norm(
            final.get_positions() - initial.get_positions(), axis=1
        )
        moved = np.flatnonzero(displacements > 1.0e-9)
        assert len(moved) == 1
        assert displacements[moved[0]] == pytest.approx(hop_distance)

    def test_deterministic_endpoints(self) -> None:
        first = build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=2)
        second = build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=2)
        assert np.array_equal(first[0].get_positions(), second[0].get_positions())
        assert np.array_equal(first[1].get_positions(), second[1].get_positions())
        assert first[2] == second[2]

    def test_tuple_supercell_accepted(self) -> None:
        initial, _, _ = build_fcc_vacancy_hop(
            "Al", lattice_constant=_AL_A0, supercell=(2, 2, 3)
        )
        assert len(initial) == 4 * 2 * 2 * 3 - 1

    def test_rejects_compound_formula(self) -> None:
        with pytest.raises(InputValidationError):
            build_fcc_vacancy_hop("NiAl", lattice_constant=_AL_A0)

    def test_rejects_supercell_below_two(self) -> None:
        with pytest.raises(InputValidationError):
            build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=1)
        with pytest.raises(InputValidationError):
            build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=(2, 2, 1))

    def test_rejects_bad_lattice_constant(self) -> None:
        with pytest.raises(InputValidationError):
            build_fcc_vacancy_hop("Al", lattice_constant=-4.05)


class TestCationVacancyHopBuilder:
    def test_rocksalt_geometry(self) -> None:
        initial, final, hop_distance = build_cation_vacancy_hop(
            "LiF", lattice_constant=_LIF_A0
        )
        # 2x2x2 rocksalt conventional = 64 atoms; one Li vacancy -> 63.
        assert len(initial) == 63
        symbols = initial.get_chemical_symbols()
        assert symbols.count("Li") == 31
        assert symbols.count("F") == 32
        # The <110> same-sublattice hop: a0/sqrt(2).
        assert hop_distance == pytest.approx(_LIF_A0 / math.sqrt(2.0))
        displacements = np.linalg.norm(
            final.get_positions() - initial.get_positions(), axis=1
        )
        moved = np.flatnonzero(displacements > 1.0e-9)
        assert len(moved) == 1
        assert symbols[moved[0]] == "Li"  # the hopper is a cation

    def test_first_formula_species_is_the_cation(self) -> None:
        initial, _, _ = build_cation_vacancy_hop("NaCl", lattice_constant=5.6)
        assert initial.get_chemical_symbols().count("Na") == 31

    def test_deterministic_endpoints(self) -> None:
        first = build_cation_vacancy_hop("LiF", lattice_constant=_LIF_A0)
        second = build_cation_vacancy_hop("LiF", lattice_constant=_LIF_A0)
        assert np.array_equal(first[0].get_positions(), second[0].get_positions())
        assert np.array_equal(first[1].get_positions(), second[1].get_positions())
        assert first[2] == second[2]

    def test_rejects_non_rocksalt_structure(self) -> None:
        with pytest.raises(InputValidationError):
            build_cation_vacancy_hop("LiF", "b2", lattice_constant=_LIF_A0)

    def test_rejects_non_1_1_composition(self) -> None:
        with pytest.raises(InputValidationError):
            build_cation_vacancy_hop("Li2S", lattice_constant=5.7)
        with pytest.raises(InputValidationError):
            build_cation_vacancy_hop("Al", lattice_constant=_AL_A0)

    def test_rejects_supercell_below_two(self) -> None:
        with pytest.raises(InputValidationError):
            build_cation_vacancy_hop("LiF", lattice_constant=_LIF_A0, supercell=1)


class TestComputeMigrationBarrier:
    def test_emt_al_barrier_in_physical_band(self, al_barrier) -> None:
        # EMT Al vacancy migration is a classic ~0.4-0.6 eV hop.
        assert 0.2 < al_barrier.forward_barrier_ev < 1.2
        assert 0.2 < al_barrier.backward_barrier_ev < 1.2

    def test_symmetric_hop_asymmetry(self, al_barrier) -> None:
        assert al_barrier.barrier_asymmetry_ev < 0.05
        assert al_barrier.barrier_asymmetry_ev == pytest.approx(
            abs(al_barrier.forward_barrier_ev - al_barrier.backward_barrier_ev)
        )

    def test_barrier_identities(self, al_barrier) -> None:
        assert al_barrier.forward_barrier_ev == pytest.approx(
            al_barrier.e_saddle_ev - al_barrier.e_initial_ev
        )
        assert al_barrier.backward_barrier_ev == pytest.approx(
            al_barrier.e_saddle_ev - al_barrier.e_final_ev
        )

    def test_band_shape_and_saddle(self, al_barrier) -> None:
        band = al_barrier.band_energies_ev
        assert len(band) == al_barrier.n_images + 2
        assert band[0] == pytest.approx(al_barrier.e_initial_ev)
        assert band[-1] == pytest.approx(al_barrier.e_final_ev)
        assert 0 < al_barrier.saddle_image_index < len(band) - 1  # interior saddle
        assert band[al_barrier.saddle_image_index] == max(band)

    def test_bookkeeping_fields(self, al_barrier) -> None:
        assert al_barrier.n_atoms == 31
        assert al_barrier.climb is True
        assert al_barrier.neb_method == "improvedtangent"
        assert al_barrier.interpolation_method == "idpp"
        assert al_barrier.n_relax_steps_initial >= 0
        assert al_barrier.n_relax_steps_final >= 0
        assert al_barrier.n_neb_steps >= al_barrier.n_pre_climb_steps > 0
        assert al_barrier.n_force_calls > 0
        assert al_barrier.wall_time_seconds > 0.0
        # Relaxed endpoints still separated by roughly the <110> hop.
        assert 2.0 < al_barrier.hop_distance_angstrom < 3.5

    def test_does_not_mutate_inputs(self, al_hop, al_barrier) -> None:
        initial, final, hop_distance = al_hop
        rebuilt = build_fcc_vacancy_hop("Al", lattice_constant=_AL_A0, supercell=2)
        assert np.array_equal(initial.get_positions(), rebuilt[0].get_positions())
        assert np.array_equal(final.get_positions(), rebuilt[1].get_positions())
        assert initial.calc is None and final.calc is None

    def test_to_dict_envelope(self, al_barrier) -> None:
        payload = al_barrier.to_dict()
        assert payload["property"] == "migration_barrier"
        assert payload["units"]["forward_barrier_ev"] == "eV"
        assert payload["canonical_inputs"]["n_images"] == 3
        assert payload["canonical_inputs"]["climb"] is True
        assert payload["values"]["saddle_image_index"] == al_barrier.saddle_image_index
        assert "wall_time_seconds" not in payload["canonical_inputs"]

    def test_endpoint_band_minimum_recorded_healthy(self, al_barrier) -> None:
        """Registered Round-3 fix: convergence check is warn-AND-record."""
        assert al_barrier.endpoint_below_band is True
        assert al_barrier.endpoint_vs_band_min_delta_ev >= 0.0
        assert al_barrier.endpoint_vs_band_min_delta_ev == pytest.approx(
            min(al_barrier.band_energies_ev[1:-1])
            - min(al_barrier.e_initial_ev, al_barrier.e_final_ev)
        )
        payload = al_barrier.to_dict()
        assert payload["values"]["endpoint_below_band"] is True
        assert payload["units"]["endpoint_vs_band_min_delta_ev"] == "eV"

    def test_rejects_bad_n_images(self, al_hop) -> None:
        initial, final, _ = al_hop
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, n_images=0)
        # climb=True needs >= 3 interior images.
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, n_images=2, climb=True)

    def test_rejects_mismatched_endpoints(self, al_hop) -> None:
        initial, final, _ = al_hop
        short = final.copy()
        del short[0]
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, short)

    def test_rejects_identical_endpoints(self, al_hop) -> None:
        initial, _, _ = al_hop
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, initial.copy())

    def test_rejects_bad_parameters(self, al_hop) -> None:
        initial, final, _ = al_hop
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, fmax=0.0)
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, optimizer="CG")
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, max_steps=0)
        with pytest.raises(InputValidationError):
            compute_migration_barrier(EMT(), initial, final, interpolation="spline")


class TestEndpointBandMinimumCheck:
    """Endpoint-vs-band-minimum convergence check (Round-3 registered fix:
    replaces the symmetric-asymmetry identity as convergence evidence)."""

    def test_healthy_band_passes(self) -> None:
        ok, delta = endpoint_band_minimum_check((-10.0, -9.6, -9.4, -9.6, -10.0))
        assert ok is True
        assert delta == pytest.approx(0.4)

    def test_interior_image_below_endpoint_flagged(self) -> None:
        # The LiI/mace-mp-medium defect shape: an image ~3 meV below the
        # endpoints, invisible to the asymmetry identity.
        ok, delta = endpoint_band_minimum_check((-10.0, -10.003, -9.5, -10.0))
        assert ok is False
        assert delta == pytest.approx(-0.003)

    def test_asymmetric_endpoints_use_the_lower_one(self) -> None:
        # Interior dips below the HIGHER endpoint but not the lower: healthy.
        ok, delta = endpoint_band_minimum_check((-10.0, -9.9, -9.0, -9.5))
        assert ok is True
        assert delta == pytest.approx(0.1)

    def test_boundary_equality_is_healthy(self) -> None:
        ok, delta = endpoint_band_minimum_check((-10.0, -10.0, -10.0))
        assert ok is True
        assert delta == pytest.approx(0.0)

    def test_validation(self) -> None:
        with pytest.raises(InputValidationError):
            endpoint_band_minimum_check((-10.0, -9.5))  # no interior image
        with pytest.raises(InputValidationError):
            endpoint_band_minimum_check((-10.0, math.nan, -10.0))
