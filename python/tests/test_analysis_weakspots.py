"""Tests for the H3 weak-spot statistic (defect-family vs bulk-family errors).

Fixture (d): planted 3x defect-family errors -> pass (ratio >= 2.0); planted
1x -> kill (ratio < 1.5); in between -> inconclusive. Also covers the
exploratory-quarantine cell exclusion ((Ni, mace-mp-small) per prereg) and
seeded-bootstrap determinism.
"""

from __future__ import annotations

import numpy as np
import pytest
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.vectors import ErrorCell
from lupine_distill.analysis.weakspots import CellExclusion, weak_spot_statistic

DEFECT_PROPS = ("e_vac", "gamma_sfe", "gamma_100", "gamma_110", "gamma_111")
BULK_PROPS = ("a0", "b0", "dh_f")
MATERIALS = ("M1", "M2", "M3", "M4", "M5", "M6")


def _cell(material: str, prop: str, err: float, model: str = "modelA") -> ErrorCell:
    return ErrorCell(
        material=material,
        model_id=model,
        property_name=prop,
        predicted=1.0 + err,
        reference_value=1.0,
        reference_method="DFT-PBE",
        normalized_error=err,
        guard_engaged=False,
    )


def _planted_cells(defect_scale: float, bulk_scale: float, model: str = "modelA"):
    """Cells with |error| ~= scale, slight per-material variation, mixed sign."""
    cells = []
    for i, mat in enumerate(MATERIALS):
        wobble = 1.0 + 0.05 * (i - 2.5)
        sign = -1.0 if i % 2 else 1.0
        for prop in ("a0", "b0"):  # dh_f intentionally absent (elemental runs)
            cells.append(_cell(mat, prop, sign * bulk_scale * wobble, model))
        for prop in DEFECT_PROPS:
            cells.append(_cell(mat, prop, -sign * defect_scale * wobble, model))
    return tuple(cells)


def test_h3_planted_3x_defect_errors_passes():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells, model_id="modelA", rng=np.random.default_rng(17), n_bootstrap=500
    )
    assert result.ratio == pytest.approx(3.0, rel=0.05)
    assert result.verdict == "pass"
    assert result.ci_low <= result.ratio <= result.ci_high
    assert result.ci_low > 1.5
    assert result.n_defect_cells == 6 * len(DEFECT_PROPS)
    assert result.n_bulk_cells == 6 * 2


def test_h3_planted_1x_defect_errors_kills():
    cells = _planted_cells(defect_scale=0.10, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells, model_id="modelA", rng=np.random.default_rng(17), n_bootstrap=500
    )
    assert result.ratio == pytest.approx(1.0, rel=0.05)
    assert result.verdict == "kill"


def test_h3_between_thresholds_is_inconclusive():
    cells = _planted_cells(defect_scale=0.17, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells, model_id="modelA", rng=np.random.default_rng(17), n_bootstrap=500
    )
    assert 1.5 <= result.ratio < 2.0
    assert result.verdict == "inconclusive"


def test_h3_quarantine_excludes_material_model_cells():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells,
        model_id="modelA",
        excluded_cells=(CellExclusion(material="M1", model_id="modelA"),),
        rng=np.random.default_rng(17),
        n_bootstrap=500,
    )
    assert result.n_defect_cells == 5 * len(DEFECT_PROPS)
    assert result.n_bulk_cells == 5 * 2
    assert ("M1", "modelA", "*") in result.excluded_cells


def test_h3_property_scoped_exclusion_only_drops_that_property():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells,
        model_id="modelA",
        excluded_cells=(
            CellExclusion(material="M1", model_id="modelA", property_name="gamma_sfe"),
        ),
        rng=np.random.default_rng(17),
        n_bootstrap=500,
    )
    assert result.n_defect_cells == 6 * len(DEFECT_PROPS) - 1
    assert result.n_bulk_cells == 6 * 2


def test_h3_exclusion_for_other_model_is_inert():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    result = weak_spot_statistic(
        cells,
        model_id="modelA",
        excluded_cells=(CellExclusion(material="M1", model_id="modelZ"),),
        rng=np.random.default_rng(17),
        n_bootstrap=500,
    )
    assert result.n_defect_cells == 6 * len(DEFECT_PROPS)


def test_h3_bootstrap_is_deterministic_for_fixed_seed():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    result_a = weak_spot_statistic(
        cells, model_id="modelA", rng=np.random.default_rng(23), n_bootstrap=300
    )
    result_b = weak_spot_statistic(
        cells, model_id="modelA", rng=np.random.default_rng(23), n_bootstrap=300
    )
    assert (result_a.ci_low, result_a.ci_high) == (result_b.ci_low, result_b.ci_high)


def test_h3_validation_errors():
    cells = _planted_cells(defect_scale=0.30, bulk_scale=0.10)
    with pytest.raises(InputValidationError):
        weak_spot_statistic(
            cells, model_id="missing-model", rng=np.random.default_rng(0)
        )
    bulk_only = tuple(c for c in cells if c.property_name in BULK_PROPS)
    with pytest.raises(InputValidationError):
        weak_spot_statistic(bulk_only, model_id="modelA", rng=np.random.default_rng(0))
    with pytest.raises(InputValidationError):
        weak_spot_statistic(cells, model_id="modelA", rng=1234)  # type: ignore[arg-type]
