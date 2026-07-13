"""Unit tests for lupine_distill.statics.elastic (cubic elastic constants).

The Voigt shear convention is the critical correctness risk, so it is tested
two independent ways:

1. A synthetic linear-elastic calculator with a KNOWN cubic stiffness tensor
   (Hooke's law, ``sigma_yz = 2*C44*eps_yz``) must be recovered exactly.
2. EMT Cu (analytic stress) must satisfy the cubic identity
   ``B0 = (C11 + 2*C12)/3`` against the independent BM3 energy-curvature B0
   from the recentring E-V scan, to a few percent.
"""

from __future__ import annotations

import dataclasses
import json
import math

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes
from ase.calculators.emt import EMT

from lupine_distill.statics import (
    CalculationError,
    CubicElasticResult,
    InputValidationError,
    build_structure,
    compute_cubic_elastic_constants,
    compute_lattice,
)
from lupine_distill.statics.units import EV_PER_A3_TO_GPA

pytestmark = pytest.mark.unit


class _LinearElasticCalculator(Calculator):
    """Analytic Hooke's-law calculator with a known cubic stiffness tensor.

    Stress follows from the symmetric tensor strain relative to a reference
    cell using the Voigt engineering-shear convention
    ``sigma_yz = C44 * gamma_yz = 2 * C44 * eps_yz``. Energy and forces are
    zero: only the stress-strain pathway is exercised.
    """

    implemented_properties = ["energy", "forces", "stress"]

    def __init__(
        self, reference_cell: np.ndarray, c11_gpa: float, c12_gpa: float, c44_gpa: float
    ) -> None:
        super().__init__()
        self._ref_inv = np.linalg.inv(np.asarray(reference_cell, dtype=float))
        self._c11 = c11_gpa / EV_PER_A3_TO_GPA
        self._c12 = c12_gpa / EV_PER_A3_TO_GPA
        self._c44 = c44_gpa / EV_PER_A3_TO_GPA

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        deform = self._ref_inv @ self.atoms.get_cell().array
        eps = 0.5 * (deform + deform.T) - np.eye(3)
        diag = np.array(
            [
                self._c11 * eps[0, 0] + self._c12 * (eps[1, 1] + eps[2, 2]),
                self._c11 * eps[1, 1] + self._c12 * (eps[0, 0] + eps[2, 2]),
                self._c11 * eps[2, 2] + self._c12 * (eps[0, 0] + eps[1, 1]),
            ]
        )
        shear = 2.0 * self._c44 * np.array([eps[1, 2], eps[0, 2], eps[0, 1]])
        self.results = {
            "energy": 0.0,
            "forces": np.zeros((len(self.atoms), 3)),
            "stress": np.concatenate([diag, shear]),
        }


class _NoStressCalculator(Calculator):
    """Energy/forces only; used to test the stress-capability failure path."""

    implemented_properties = ["energy", "forces"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        self.results = {"energy": 0.0, "forces": np.zeros((len(self.atoms), 3))}


class TestKnownStiffnessRoundtrip:
    def test_recovers_known_cubic_constants_exactly(self) -> None:
        a0 = 3.6
        reference = build_structure("Cu", "fcc", a0)
        calc = _LinearElasticCalculator(
            reference.get_cell().array, c11_gpa=110.0, c12_gpa=60.0, c44_gpa=30.0
        )
        result = compute_cubic_elastic_constants(calc, "Cu", "fcc", a0)
        assert result.c11_gpa == pytest.approx(110.0, rel=1e-7)
        assert result.c12_gpa == pytest.approx(60.0, rel=1e-7)
        assert result.c44_gpa == pytest.approx(30.0, rel=1e-7)
        assert result.bulk_modulus_from_cij_gpa == pytest.approx(
            (110.0 + 2.0 * 60.0) / 3.0, rel=1e-7
        )

    def test_voigt_factor_two_would_be_visible(self) -> None:
        # If the implementation dropped the engineering-shear factor of two,
        # C44 would come out at exactly half or double the known value; this
        # pins the convention.
        a0 = 4.0
        reference = build_structure("Al", "fcc", a0)
        calc = _LinearElasticCalculator(
            reference.get_cell().array, c11_gpa=100.0, c12_gpa=50.0, c44_gpa=40.0
        )
        result = compute_cubic_elastic_constants(calc, "Al", "fcc", a0)
        assert result.c44_gpa == pytest.approx(40.0, rel=1e-7)
        assert not result.c44_gpa == pytest.approx(20.0, rel=1e-3)
        assert not result.c44_gpa == pytest.approx(80.0, rel=1e-3)

    def test_delta_insensitivity_for_linear_material(self) -> None:
        a0 = 3.6
        reference = build_structure("Cu", "fcc", a0)
        calc = _LinearElasticCalculator(
            reference.get_cell().array, c11_gpa=110.0, c12_gpa=60.0, c44_gpa=30.0
        )
        r_small = compute_cubic_elastic_constants(calc, "Cu", "fcc", a0, delta=1e-3)
        r_large = compute_cubic_elastic_constants(calc, "Cu", "fcc", a0, delta=1e-2)
        assert r_small.c11_gpa == pytest.approx(r_large.c11_gpa, rel=1e-6)
        assert r_small.c44_gpa == pytest.approx(r_large.c44_gpa, rel=1e-6)


class TestEmtConsistency:
    def test_cu_bulk_modulus_matches_energy_curvature(self) -> None:
        lattice = compute_lattice(EMT(), "Cu", "fcc")
        elastic = compute_cubic_elastic_constants(
            EMT(), "Cu", "fcc", lattice.a0_angstrom
        )
        # Cubic identity B0 = (C11 + 2 C12)/3 vs the independent BM3 fit.
        assert elastic.bulk_modulus_from_cij_gpa == pytest.approx(
            lattice.b0_gpa, rel=0.05
        )
        assert elastic.c11_gpa > elastic.c12_gpa > 0.0
        assert elastic.c44_gpa > 0.0

    def test_relax_internal_is_noop_for_symmetric_fcc(self) -> None:
        lattice = compute_lattice(EMT(), "Cu", "fcc")
        clamped = compute_cubic_elastic_constants(
            EMT(), "Cu", "fcc", lattice.a0_angstrom, relax_internal=False
        )
        relaxed = compute_cubic_elastic_constants(
            EMT(), "Cu", "fcc", lattice.a0_angstrom, relax_internal=True
        )
        # fcc elemental cells have no free internal coordinates: forces vanish
        # by symmetry, so the relaxed-ion constants must match clamped-ion.
        assert relaxed.c11_gpa == pytest.approx(clamped.c11_gpa, rel=1e-6)
        assert relaxed.c44_gpa == pytest.approx(clamped.c44_gpa, rel=1e-6)
        assert relaxed.n_relax_steps_total == 0


class TestValidationAndEnvelope:
    def test_rejects_nonpositive_delta(self) -> None:
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "fcc", 3.6, delta=0.0)
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "fcc", 3.6, delta=-0.01)

    def test_rejects_absurd_delta(self) -> None:
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "fcc", 3.6, delta=0.5)

    def test_rejects_nonfinite_delta(self) -> None:
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "fcc", 3.6, delta=math.nan)

    def test_rejects_unknown_structure_type(self) -> None:
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "hcp", 3.6)

    def test_rejects_bad_lattice_constant(self) -> None:
        with pytest.raises(InputValidationError):
            compute_cubic_elastic_constants(EMT(), "Cu", "fcc", -1.0)

    def test_stress_incapable_calculator_fails_clearly(self) -> None:
        with pytest.raises(CalculationError, match="stress"):
            compute_cubic_elastic_constants(_NoStressCalculator(), "Cu", "fcc", 3.6)

    def test_result_is_frozen(self) -> None:
        a0 = 3.6
        reference = build_structure("Cu", "fcc", a0)
        calc = _LinearElasticCalculator(reference.get_cell().array, 110.0, 60.0, 30.0)
        result = compute_cubic_elastic_constants(calc, "Cu", "fcc", a0)
        assert isinstance(result, CubicElasticResult)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.c11_gpa = 0.0  # type: ignore[misc]

    def test_to_dict_envelope_and_canonical_inputs(self) -> None:
        a0 = 3.6
        reference = build_structure("Cu", "fcc", a0)
        calc = _LinearElasticCalculator(reference.get_cell().array, 110.0, 60.0, 30.0)
        result = compute_cubic_elastic_constants(calc, "Cu", "fcc", a0, delta=0.005)
        block = result.to_dict()
        assert block["property"] == "cubic_elastic"
        assert set(block) == {
            "property",
            "values",
            "units",
            "canonical_inputs",
            "wall_time_seconds",
        }
        assert block["values"]["c11_gpa"] == pytest.approx(110.0, rel=1e-7)
        assert block["units"]["c44_gpa"] == "GPa"
        canonical = block["canonical_inputs"]
        assert canonical["property"] == "cubic_elastic"
        assert canonical["delta"] == 0.005
        assert "voigt_convention" in canonical
        assert "wall_time" not in canonical
        json.dumps(block)  # must be JSON-serializable
