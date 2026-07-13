"""End-to-end tests for the confirmatory report (prereg H1/H2/H3) and the
descriptive (ensemble-spread) report.

The synthetic world plants a rank-1, cross-family, model-shared error mode
with 3x defect-family amplification, so every registered hypothesis passes;
a flattened variant drives the H3 kill branch. Reports must be
JSON-serializable, self-describing (exclusions + n counts), and bitwise
deterministic for a fixed seed.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.loading import ReferenceEntry, RunRecord
from lupine_distill.analysis.report import (
    build_confirmatory_report,
    build_descriptive_report,
)
from lupine_distill.analysis.weakspots import CellExclusion

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
MODELS = ("modelA", "modelB", "modelC")
MATERIALS = ("M1", "M2", "M3", "M4", "M5", "M6")
REF_BASE = {
    "a0": 4.0,
    "b0": 100.0,
    "b0_prime": 4.5,
    "e_vac": 1.2,
    "gamma_100": 2.0,
    "gamma_110": 2.2,
    "gamma_111": 1.8,
    "gamma_sfe": 120.0,
}
U_BY_MODEL = {
    "modelA": (1.0, -1.1, 0.9, 1.05, -0.95, 1.02),
    "modelB": (0.7, 1.3, -1.0, 0.8, 1.1, -0.9),
    "modelC": (-1.2, 0.85, 1.1, -0.9, 1.0, 0.95),
}
V_SHARED = {
    "a0": 0.08,
    "b0": 0.12,
    "b0_prime": 0.10,
    "e_vac": 0.35,
    "gamma_100": 0.30,
    "gamma_110": 0.32,
    "gamma_111": 0.28,
    "gamma_sfe": 0.40,
}


def _references() -> tuple[ReferenceEntry, ...]:
    refs = []
    for i, mat in enumerate(MATERIALS + ("M7", "FeX")):
        for prop, base in REF_BASE.items():
            refs.append(
                ReferenceEntry(
                    material=mat,
                    structure="fcc",
                    property_name=prop,
                    value=base * (1.0 + 0.02 * i),
                    unit="arb",
                    method="DFT-PBE",
                    uncertainty=None,
                    citation="synthetic",
                    family_label="synthetic",
                )
            )
    return tuple(refs)


def _runs(v_by_prop: dict) -> tuple[RunRecord, ...]:
    rng = np.random.default_rng(555)
    refs_by_key = {(r.material, r.property_name): r.value for r in _references()}
    runs = []
    for model in MODELS:
        u = U_BY_MODEL[model]
        for i, mat in enumerate(MATERIALS):
            preds = {}
            for prop in FCC_PROPS:
                err = u[i] * v_by_prop[prop] + 0.002 * rng.standard_normal()
                preds[prop] = refs_by_key[(mat, prop)] * (1.0 + err)
            runs.append(
                RunRecord(
                    material=mat,
                    structure_type="fcc",
                    model_id=model,
                    predictions=preds,
                    source_path="<synthetic>",
                )
            )
        # M7 is incomplete (no gamma_sfe): matched-n must drop it.
        preds_m7 = {
            p: refs_by_key[("M7", p)] * 1.01 for p in FCC_PROPS if p != "gamma_sfe"
        }
        runs.append(
            RunRecord(
                material="M7",
                structure_type="fcc",
                model_id=model,
                predictions=preds_m7,
                source_path="<synthetic>",
            )
        )
        # FeX is complete but excluded by the caller (deviations-log analog).
        preds_fe = {p: refs_by_key[("FeX", p)] * 1.05 for p in FCC_PROPS}
        runs.append(
            RunRecord(
                material="FeX",
                structure_type="fcc",
                model_id=model,
                predictions=preds_fe,
                source_path="<synthetic>",
            )
        )
    return tuple(runs)


def _build(v_by_prop: dict, seed: int = 20260701) -> dict:
    return build_confirmatory_report(
        _runs(v_by_prop),
        _references(),
        model_ids=MODELS,
        properties=FCC_PROPS,
        excluded_materials=("FeX",),
        h3_excluded_cells=(CellExclusion(material="M1", model_id="modelA"),),
        near_zero_epsilon=1e-6,
        seed=seed,
        n_null_draws=400,
        n_bootstrap=300,
    )


def test_confirmatory_report_planted_structure_passes_all_hypotheses():
    report = _build(V_SHARED)
    assert report["schema"] == "lupine.y_matrix.confirmatory_report.v1"
    assert report["mode"] == "confirmatory"
    assert sorted(report["matched_materials"]) == list(MATERIALS)
    assert report["n_materials"] == 6
    assert report["n_properties"] == 8
    # Exclusions are recorded, self-describingly.
    assert "FeX" in report["excluded_materials"]
    assert "M7" in json.dumps(report["material_exclusions"])
    # H1: PR below the coupling-aware null band for every model.
    for model in MODELS:
        h1 = report["h1"][model]
        assert h1["pr"] < 1.2
        assert h1["pass"] is True
        assert h1["pr"] < h1["null_p05"] <= h1["null_p95"]
        assert "null" in h1["criterion"]
    # H2: shared mode across all three pairs.
    assert report["h2"]["threshold"] == pytest.approx(0.7)
    assert len(report["h2"]["pairs"]) == 3
    for pair in report["h2"]["pairs"].values():
        assert pair["cosine"] > 0.9
        assert pair["cosine"] > pair["null_p95"]
        assert pair["pass"] is True
    assert report["h2"]["pass"] is True
    # H3: 3x planted defect amplification.
    for model in MODELS:
        h3 = report["h3"]["per_model"][model]
        assert h3["ratio"] > 2.0
        assert h3["verdict"] == "pass"
        assert h3["ci95"][0] <= h3["ratio"] <= h3["ci95"][1]
        assert h3["n_defect_cells"] > 0 and h3["n_bulk_cells"] > 0
    assert report["h3"]["pass"] is True
    assert report["h3"]["kill"] is False
    # Quarantine recorded and effective: modelA lost M1's cells.
    assert report["h3"]["excluded_cells"] == [["M1", "modelA", "*"]]
    n_a = report["h3"]["per_model"]["modelA"]["n_defect_cells"]
    n_b = report["h3"]["per_model"]["modelB"]["n_defect_cells"]
    assert n_a < n_b


def test_confirmatory_report_flat_errors_trigger_h3_kill():
    v_flat = dict.fromkeys(FCC_PROPS, 0.1)
    report = _build(v_flat)
    for model in MODELS:
        h3 = report["h3"]["per_model"][model]
        assert h3["ratio"] < 1.5
        assert h3["verdict"] == "kill"
    assert report["h3"]["pass"] is False
    assert report["h3"]["kill"] is True


def test_confirmatory_report_is_json_serializable_and_deterministic():
    report_a = _build(V_SHARED, seed=42)
    report_b = _build(V_SHARED, seed=42)
    dump_a = json.dumps(report_a, sort_keys=True)
    dump_b = json.dumps(report_b, sort_keys=True)
    assert dump_a == dump_b
    report_c = _build(V_SHARED, seed=43)
    assert json.dumps(report_c, sort_keys=True) != dump_a


def test_confirmatory_report_requires_at_least_two_models():
    with pytest.raises(InputValidationError):
        build_confirmatory_report(
            _runs(V_SHARED),
            _references(),
            model_ids=("modelA",),
            properties=FCC_PROPS,
            excluded_materials=(),
            near_zero_epsilon=1e-6,
            seed=1,
        )


def test_descriptive_report_labels_itself_and_reports_ensemble_spread_pr():
    report = build_descriptive_report(
        _runs(V_SHARED),
        model_ids=MODELS,
        properties=FCC_PROPS,
        excluded_materials=("FeX",),
        near_zero_epsilon=1e-6,
    )
    assert report["mode"] == "descriptive"
    assert "disagreement" in report["statistic"].lower()
    assert "h1" not in report and "h2" not in report and "h3" not in report
    assert report["n_properties"] == 8
    assert 1.0 <= report["pooled_pr"] <= 8.0
    for model in MODELS:
        assert 1.0 <= report["per_model_pr"][model] <= 8.0
    # M7 lacks gamma_sfe in every model: matched-n drops it here too.
    assert sorted(report["matched_materials"]) == list(MATERIALS)
    assert "M7" in json.dumps(report["material_exclusions"])
    json.dumps(report)  # must be serializable
