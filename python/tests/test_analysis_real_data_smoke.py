"""Real-data smoke test: descriptive (reference-free) mode on the actual
Y-matrix sweep output in data/y_matrix_runs/.

No reference targets are consumed here: descriptive mode builds cross-model
disagreement vectors (deviation from the cross-model mean prediction), i.e.
the ensemble-spread analysis. Assertions are deliberately loose on counts
because a second sweep is still landing files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from lupine_distill.analysis.descriptive import assemble_descriptive_matrices
from lupine_distill.analysis.loading import load_run_directory
from lupine_distill.analysis.report import build_descriptive_report

RUNS_DIR = Path(__file__).resolve().parents[2] / "data" / "y_matrix_runs"
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
THREE_MODELS = ("chgnet", "mace-mp-medium", "mace-mp-small")

pytestmark = pytest.mark.skipif(
    not RUNS_DIR.is_dir(), reason="y_matrix_runs data directory not present"
)


def test_run_directory_loads_and_skips_evidence_files():
    records = load_run_directory(RUNS_DIR)
    assert len(records) >= 24
    keys = {(r.material, r.model_id) for r in records}
    assert ("Ni", "mace-mp-small") in keys
    ni = next(
        r for r in records if r.material == "Ni" and r.model_id == "mace-mp-small"
    )
    for prop in FCC_PROPS:
        assert prop in ni.predictions


def test_descriptive_matrices_assemble_from_real_sweep():
    records = load_run_directory(RUNS_DIR)
    matrices = assemble_descriptive_matrices(
        records,
        model_ids=THREE_MODELS,
        properties=FCC_PROPS,
        excluded_materials=("Fe",),  # deviations log 2026-07-01, caller-supplied
        near_zero_epsilon=1.0,
    )
    assert len(matrices) == 3
    first = matrices[0]
    assert set(first.materials) >= {"Al", "Cu", "Ni"}
    assert "Fe" not in first.materials
    for matrix in matrices:
        assert matrix.mode == "descriptive"
        assert matrix.materials == first.materials
        assert matrix.values.shape == (len(first.materials), len(FCC_PROPS))


def test_descriptive_report_runs_on_real_sweep_and_is_serializable():
    records = load_run_directory(RUNS_DIR)
    report = build_descriptive_report(
        records,
        model_ids=THREE_MODELS,
        properties=FCC_PROPS,
        excluded_materials=("Fe",),
        near_zero_epsilon=1.0,
    )
    assert report["mode"] == "descriptive"
    assert 1.0 <= report["pooled_pr"] <= float(len(FCC_PROPS))
    assert report["n_materials"] >= 2
    assert "Fe" not in report["matched_materials"]
    json.dumps(report)
