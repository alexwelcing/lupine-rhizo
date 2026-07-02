"""Tests for participation ratio and leading-mode extraction (prereg H1/H2).

Analytic anchors: a rank-1 error matrix has PR exactly 1; isotropic noise has
PR near the number of properties; the leading principal mode recovers a
planted property-space direction.
"""

from __future__ import annotations

import numpy as np
import pytest
from lupine_distill.analysis.dimensionality import (
    covariance_eigenvalues,
    leading_mode,
    pairwise_cosine,
    participation_ratio,
)
from lupine_distill.analysis.errors import ComputationError, InputValidationError


def _rank_one(n_materials: int = 6, n_properties: int = 8) -> np.ndarray:
    u = np.array([1.0, -1.1, 0.9, 1.05, -0.95, 1.02])[:n_materials]
    v = np.array([0.08, 0.12, 0.10, 0.35, 0.30, 0.32, 0.28, 0.40])[:n_properties]
    return np.outer(u, v)


def test_participation_ratio_of_rank_one_matrix_is_one():
    pr = participation_ratio(_rank_one())
    assert pr == pytest.approx(1.0, abs=1e-9)


def test_participation_ratio_of_isotropic_noise_is_near_property_count():
    rng = np.random.default_rng(1234)
    values = rng.standard_normal((400, 8))
    pr = participation_ratio(values)
    assert 6.5 < pr <= 8.0


def test_participation_ratio_is_bounded_by_property_count():
    rng = np.random.default_rng(7)
    values = rng.standard_normal((6, 8))
    pr = participation_ratio(values)
    assert 1.0 <= pr <= 8.0


def test_covariance_eigenvalues_are_descending_and_nonnegative():
    rng = np.random.default_rng(3)
    values = rng.standard_normal((10, 5))
    lam = covariance_eigenvalues(values)
    assert lam.shape == (5,)
    assert np.all(lam >= 0.0)
    assert np.all(np.diff(lam) <= 1e-12)


def test_leading_mode_recovers_planted_direction():
    rng = np.random.default_rng(42)
    base = _rank_one()
    noisy = base + 0.005 * rng.standard_normal(base.shape)
    mode = leading_mode(noisy)
    v = np.array([0.08, 0.12, 0.10, 0.35, 0.30, 0.32, 0.28, 0.40])
    v_unit = v / np.linalg.norm(v)
    assert abs(float(mode @ v_unit)) > 0.99
    assert np.linalg.norm(mode) == pytest.approx(1.0)


def test_leading_mode_sign_convention_is_deterministic():
    values = _rank_one()
    mode_a = leading_mode(values)
    mode_b = leading_mode(values.copy())
    np.testing.assert_allclose(mode_a, mode_b)
    # Largest-magnitude component is made positive.
    assert mode_a[int(np.argmax(np.abs(mode_a)))] > 0.0


def test_pairwise_cosine_basics():
    u = np.array([1.0, 0.0])
    v = np.array([0.0, 1.0])
    assert pairwise_cosine(u, v) == pytest.approx(0.0)
    assert pairwise_cosine(u, -u) == pytest.approx(1.0)  # absolute by default
    assert pairwise_cosine(u, -u, absolute=False) == pytest.approx(-1.0)


def test_dimensionality_input_validation():
    with pytest.raises(InputValidationError):
        participation_ratio(np.array([1.0, 2.0]))  # 1-D
    with pytest.raises(InputValidationError):
        participation_ratio(np.array([[1.0, 2.0]]))  # single material
    with pytest.raises(InputValidationError):
        participation_ratio(np.array([[1.0, np.nan], [2.0, 3.0]]))
    with pytest.raises(ComputationError):
        participation_ratio(np.zeros((4, 3)))  # degenerate covariance
    with pytest.raises(InputValidationError):
        pairwise_cosine(np.zeros(3), np.ones(3))
    with pytest.raises(InputValidationError):
        pairwise_cosine(np.ones(3), np.ones(4))
