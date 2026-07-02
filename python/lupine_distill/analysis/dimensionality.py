"""Participation ratio and leading-mode extraction (prereg H1/H2).

The registered H1 statistic is the participation ratio of the
material-by-property error covariance:

    PR = (sum(lambda))^2 / sum(lambda^2)

over the eigenvalues of the property-space covariance (columns centered
across materials). PR = 1 for a rank-1 error structure and approaches the
number of properties for isotropic errors. The leading principal mode (unit
eigenvector of the largest eigenvalue, property space) feeds H2's pairwise
cosine similarity across models; eigenvector sign is arbitrary, so cosines
are compared in absolute value by default and the mode sign is fixed
deterministically for reporting.
"""

from __future__ import annotations

import numpy as np

from lupine_distill.analysis.errors import ComputationError, InputValidationError


def _validated(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise InputValidationError(
            f"expected a 2-D materials-by-properties matrix, got ndim={array.ndim}"
        )
    n_materials, n_properties = array.shape
    if n_materials < 2:
        raise InputValidationError(
            f"need >= 2 materials for a covariance, got {n_materials}"
        )
    if n_properties < 1:
        raise InputValidationError("need >= 1 property column")
    if not np.all(np.isfinite(array)):
        raise InputValidationError("error matrix contains non-finite values")
    return array


def _covariance(values: np.ndarray) -> np.ndarray:
    array = _validated(values)
    centered = array - array.mean(axis=0, keepdims=True)
    return centered.T @ centered / float(array.shape[0] - 1)


def covariance_eigenvalues(values: np.ndarray) -> np.ndarray:
    """Descending, non-negative eigenvalues of the property-space covariance."""
    eigenvalues = np.linalg.eigvalsh(_covariance(values))[::-1]
    return np.clip(eigenvalues, 0.0, None)


def participation_ratio(values: np.ndarray) -> float:
    """Registered H1 statistic: PR = (sum(lambda))^2 / sum(lambda^2)."""
    eigenvalues = covariance_eigenvalues(values)
    total = float(np.sum(eigenvalues))
    total_sq = float(np.sum(eigenvalues**2))
    if total_sq <= 0.0:
        raise ComputationError(
            "degenerate covariance (all eigenvalues zero): PR undefined"
        )
    return total * total / total_sq


def leading_mode(values: np.ndarray) -> np.ndarray:
    """Unit eigenvector of the largest covariance eigenvalue (property space).

    Sign convention: the largest-magnitude component is made positive so the
    returned mode is deterministic; H2 cosines are sign-invariant anyway.
    """
    covariance = _covariance(values)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    if float(eigenvalues[-1]) <= 0.0:
        raise ComputationError("degenerate covariance: leading mode undefined")
    mode = eigenvectors[:, -1]
    pivot = int(np.argmax(np.abs(mode)))
    if mode[pivot] < 0.0:
        mode = -mode
    mode = np.array(mode, dtype=float, copy=True)
    mode.setflags(write=False)
    return mode


def pairwise_cosine(
    u: np.ndarray, v: np.ndarray, *, absolute: bool = True
) -> float:
    """Cosine similarity between two modes (absolute by default: H2 usage)."""
    u_arr = np.asarray(u, dtype=float)
    v_arr = np.asarray(v, dtype=float)
    if u_arr.ndim != 1 or v_arr.ndim != 1 or u_arr.shape != v_arr.shape:
        raise InputValidationError(
            f"modes must be 1-D and same-shaped, got {u_arr.shape} and {v_arr.shape}"
        )
    if not (np.all(np.isfinite(u_arr)) and np.all(np.isfinite(v_arr))):
        raise InputValidationError("modes contain non-finite values")
    norm_u = float(np.linalg.norm(u_arr))
    norm_v = float(np.linalg.norm(v_arr))
    if norm_u <= 0.0 or norm_v <= 0.0:
        raise InputValidationError("cosine undefined for zero-norm mode")
    cosine = float(u_arr @ v_arr) / (norm_u * norm_v)
    return abs(cosine) if absolute else cosine


__all__ = [
    "covariance_eigenvalues",
    "leading_mode",
    "pairwise_cosine",
    "participation_ratio",
]
