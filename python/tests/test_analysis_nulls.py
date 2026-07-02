"""Tests for the coupling-aware permutation null (prereg section Nulls).

The registered null permutes material labels independently per property
family, preserving within-family structure and destroying only cross-family
alignment. Rank-1 cross-family structure must sit below the null band (H1
pass); isotropic noise must sit inside it (H1 fail); a planted shared mode
must exceed the cosine null (H2 pass). All draws come from a caller-supplied
seeded Generator; determinism is asserted.
"""

from __future__ import annotations

import numpy as np
import pytest
from lupine_distill.analysis.dimensionality import (
    leading_mode,
    pairwise_cosine,
    participation_ratio,
)
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.nulls import (
    leading_mode_cosine_null,
    permute_within_families,
    pr_null_distribution,
)

FCC_PROPS = (
    "a0",
    "b0",
    "b0_prime",
    "e_vac",
    "gamma_100",
    "gamma_110",
    "gamma_111",
    "gamma_sfe",
)

U = np.array([1.0, -1.1, 0.9, 1.05, -0.95, 1.02])
V = np.array([0.08, 0.12, 0.10, 0.35, 0.30, 0.32, 0.28, 0.40])


def test_permutation_preserves_within_family_row_coupling():
    # eos family columns (b0, b0_prime) are coupled: col2 = col1 + 10.
    properties = ("b0", "b0_prime", "e_vac")
    n = 12
    b0 = np.arange(n, dtype=float)
    values = np.column_stack([b0, b0 + 10.0, np.arange(n, dtype=float) * 3.0])
    rng = np.random.default_rng(5)
    permuted = permute_within_families(values, properties, rng=rng)
    # Within-family coupling survives the permutation...
    np.testing.assert_allclose(permuted[:, 1], permuted[:, 0] + 10.0)
    # ...and each family's rows are a permutation of the originals.
    assert sorted(permuted[:, 0].tolist()) == sorted(values[:, 0].tolist())
    assert sorted(permuted[:, 2].tolist()) == sorted(values[:, 2].tolist())
    # Cross-family alignment is broken for at least one draw of this seed.
    assert not np.allclose(permuted, values)


def test_null_requires_seeded_generator_never_global_state():
    values = np.outer(U, V)
    with pytest.raises(InputValidationError):
        pr_null_distribution(values, FCC_PROPS, n_draws=10, rng=42)  # type: ignore[arg-type]
    with pytest.raises(InputValidationError):
        pr_null_distribution(values, FCC_PROPS, n_draws=10, rng=None)  # type: ignore[arg-type]


def test_null_distribution_is_deterministic_for_fixed_seed():
    values = np.outer(U, V) + 0.01 * np.random.default_rng(0).standard_normal((6, 8))
    dist_a = pr_null_distribution(
        values, FCC_PROPS, n_draws=50, rng=np.random.default_rng(99)
    )
    dist_b = pr_null_distribution(
        values, FCC_PROPS, n_draws=50, rng=np.random.default_rng(99)
    )
    assert dist_a.values == dist_b.values
    assert dist_a.p95 == dist_b.p95
    dist_c = pr_null_distribution(
        values, FCC_PROPS, n_draws=50, rng=np.random.default_rng(100)
    )
    assert dist_a.values != dist_c.values
    assert dist_a.n_draws == 50
    assert len(dist_a.values) == 50


def test_h1_rank_one_structure_sits_below_the_null_band():
    """Fixture (a): rank-1 errors across 6 materials x 8 properties."""
    values = np.outer(U, V)
    pr = participation_ratio(values)
    dist = pr_null_distribution(
        values, FCC_PROPS, n_draws=1000, rng=np.random.default_rng(2026)
    )
    assert pr == pytest.approx(1.0, abs=1e-9)
    # H1 pass: PR below the coupling-aware null band (well under p95 too).
    assert pr < dist.p05 <= dist.p95


def test_h1_isotropic_errors_sit_inside_the_null_band():
    """Fixture (b): iid errors -> PR indistinguishable from the null -> fail."""
    values = np.random.default_rng(7).standard_normal((6, 8))
    pr = participation_ratio(values)
    dist = pr_null_distribution(
        values, FCC_PROPS, n_draws=1000, rng=np.random.default_rng(2026)
    )
    assert not pr < dist.p05  # not below the band: H1 fails
    assert pr <= dist.p95  # and inside it (typical draw)


def test_h2_planted_shared_mode_exceeds_cosine_null():
    """Fixture (c): two models share a planted property-space mode."""
    rng_data = np.random.default_rng(11)
    u_b = np.array([0.7, 1.3, -1.0, 0.8, 1.1, -0.9])
    values_a = np.outer(U, V) + 0.01 * rng_data.standard_normal((6, 8))
    values_b = np.outer(u_b, V) + 0.01 * rng_data.standard_normal((6, 8))
    cos = pairwise_cosine(leading_mode(values_a), leading_mode(values_b))
    assert cos > 0.95
    nulls = leading_mode_cosine_null(
        {"modelA": values_a, "modelB": values_b},
        FCC_PROPS,
        n_draws=500,
        rng=np.random.default_rng(31),
    )
    dist = nulls[("modelA", "modelB")]
    assert cos > dist.p95
    assert len(dist.values) == 500


def test_cosine_null_requires_matching_shapes_and_two_models():
    values = np.outer(U, V)
    with pytest.raises(InputValidationError):
        leading_mode_cosine_null(
            {"only": values}, FCC_PROPS, n_draws=10, rng=np.random.default_rng(0)
        )
    with pytest.raises(InputValidationError):
        leading_mode_cosine_null(
            {"a": values, "b": values[:, :5]},
            FCC_PROPS,
            n_draws=10,
            rng=np.random.default_rng(0),
        )


def test_null_rejects_properties_missing_from_family_map():
    values = np.outer(U[:3], V[:2])
    with pytest.raises(InputValidationError):
        pr_null_distribution(
            values, ("a0", "mystery"), n_draws=10, rng=np.random.default_rng(0)
        )
