"""Tests for the H4 correction-transfer operator (prereg H4, binding
addendum 2026-07-02).

Synthetic fixtures per the registered spec: planted uniform softening (all
predictions = 0.8 x ref) -> LOO scalar s = 1.25, every family improves, H4
pass; planted family-local softening (B0 soft, defect families wrong by
independent large factors) -> EOS improves while defect families degrade ->
H4 kill; LOO correctness (a held-out material's own B0 never enters its own
scalar); bitwise determinism for the registered seed. A real-data smoke test
mirrors the confirmatory primary config (15 metals, 3 models, seed 20260702)
and, when the saved artifact exists, requires the rebuild to reproduce it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from lupine_distill.analysis.errors import InputValidationError
from lupine_distill.analysis.loading import (
    ReferenceEntry,
    RunRecord,
    load_run_directory,
    load_targets_directory,
)
from lupine_distill.analysis.operator import (
    CORRECTED_PROPERTIES,
    H4_SCHEMA_ID,
    H4_TARGET_PROPERTY_MAP,
    REGISTERED_SEED,
    FamilyTransfer,
    build_h4_transfer_report,
    family_transfer_statistic,
    h4_model_verdict,
    loo_stiffness_scalars,
)

MODEL = "modelA"
FCC_MATERIALS = ("M1", "M2", "M3", "M4", "M5", "M6")
FCC_REF_BASE = {
    "a0": 4.0,
    "b0": 100.0,
    "e_vac": 1.2,
    "gamma_100": 2.0,
    "gamma_110": 2.2,
    "gamma_111": 1.8,
    "gamma_sfe": 120.0,
}
BCC_REF_BASE = {
    "a0": 3.0,
    "b0": 180.0,
    "e_vac": 2.5,
    "gamma_100": 2.9,
    "gamma_110": 2.6,
}
NON_EOS_FAMILIES = ("point_defect", "surfaces", "planar_fault")


def _references(
    materials=FCC_MATERIALS, ref_base=FCC_REF_BASE, structure="fcc"
) -> tuple[ReferenceEntry, ...]:
    refs = []
    for i, mat in enumerate(materials):
        for prop, base in ref_base.items():
            refs.append(
                ReferenceEntry(
                    material=mat,
                    structure=structure,
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


def _world(
    factors: dict[str, float],
    materials=FCC_MATERIALS,
    ref_base=FCC_REF_BASE,
    structure="fcc",
    model=MODEL,
) -> tuple[RunRecord, ...]:
    """Runs whose prediction = factors[prop] x reference for every material."""
    refs = {
        (r.material, r.property_name): r.value
        for r in _references(materials, ref_base, structure)
    }
    return tuple(
        RunRecord(
            material=mat,
            structure_type=structure,
            model_id=model,
            predictions={
                prop: refs[(mat, prop)] * factor for prop, factor in factors.items()
            },
            source_path="<synthetic>",
        )
        for mat in materials
    )


def _build(runs, references, materials=FCC_MATERIALS, **overrides):
    kwargs = dict(
        model_ids=(MODEL,),
        materials=materials,
        near_zero_epsilon=1e-6,
        seed=REGISTERED_SEED,
        n_bootstrap=200,
    )
    kwargs.update(overrides)
    return build_h4_transfer_report(runs, references, **kwargs)


def _family_result(
    family: str,
    verdict: str,
    *,
    n_cells: int = 5,
    delta: float | None = -0.1,
) -> FamilyTransfer:
    no_cells = verdict == "no_cells"
    return FamilyTransfer(
        model_id=MODEL,
        family=family,
        properties=("p",),
        n_cells=0 if no_cells else n_cells,
        median_abs_error_before=None if no_cells else 0.5,
        median_abs_error_after=None if no_cells else 0.5 + (delta or 0.0),
        delta=None if no_cells else delta,
        ci_low=None if no_cells else 0.0,
        ci_high=None if no_cells else 0.0,
        ci_half_width=None if no_cells else 0.0,
        n_bootstrap=200,
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# LOO scalar fit
# ---------------------------------------------------------------------------


def test_loo_scalars_exclude_held_out_material():
    # Ratios ref/pred: A -> 2.0, B -> 1.25, C -> 1.25.
    folds = loo_stiffness_scalars(
        b0_ref={"A": 100.0, "B": 100.0, "C": 100.0},
        b0_pred={"A": 50.0, "B": 80.0, "C": 80.0},
    )
    by_material = {fold.material: fold for fold in folds}
    assert set(by_material) == {"A", "B", "C"}
    # A's own ratio (2.0) never enters its scalar: median(1.25, 1.25) = 1.25.
    assert by_material["A"].scalar == pytest.approx(1.25)
    # B and C see A's 2.0 in their donor pools: median(2.0, 1.25) = 1.625.
    assert by_material["B"].scalar == pytest.approx(1.625)
    assert by_material["C"].scalar == pytest.approx(1.625)
    assert all(fold.n_donors == 2 for fold in folds)


def test_loo_scalars_validation():
    with pytest.raises(InputValidationError):
        loo_stiffness_scalars(b0_ref={"A": 1.0}, b0_pred={"A": 1.0, "B": 1.0})
    with pytest.raises(InputValidationError):
        loo_stiffness_scalars(b0_ref={"A": 1.0}, b0_pred={"A": 1.0})
    with pytest.raises(InputValidationError):
        loo_stiffness_scalars(
            b0_ref={"A": 1.0, "B": 1.0}, b0_pred={"A": 0.0, "B": 1.0}
        )
    with pytest.raises(InputValidationError):
        loo_stiffness_scalars(
            b0_ref={"A": float("nan"), "B": 1.0}, b0_pred={"A": 1.0, "B": 1.0}
        )


# ---------------------------------------------------------------------------
# Family transfer statistic
# ---------------------------------------------------------------------------


def test_family_statistic_unchanged_when_delta_is_zero():
    before = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60)
    after = (0.25, 0.05, 0.45, 0.25, 0.65, 0.45)  # same median, mixed shifts
    result = family_transfer_statistic(
        before,
        after,
        model_id=MODEL,
        family="surfaces",
        properties=("gamma_100",),
        rng=np.random.default_rng(7),
        n_bootstrap=300,
    )
    assert result.delta == pytest.approx(0.0)
    assert result.verdict == "unchanged"


def test_family_statistic_degrades_when_delta_exceeds_half_width():
    before = (0.1, 0.1, 0.1, 0.1, 0.1)
    after = (0.3, 0.3, 0.3, 0.3, 0.3)
    result = family_transfer_statistic(
        before,
        after,
        model_id=MODEL,
        family="point_defect",
        properties=("e_vac",),
        rng=np.random.default_rng(7),
        n_bootstrap=300,
    )
    assert result.delta == pytest.approx(0.2)
    assert result.ci_half_width == pytest.approx(0.0)
    assert result.verdict == "degrades"


def test_family_statistic_empty_family_reports_no_cells():
    result = family_transfer_statistic(
        (),
        (),
        model_id=MODEL,
        family="compound_stability",
        properties=("dh_f",),
        rng=np.random.default_rng(7),
        n_bootstrap=300,
    )
    assert result.n_cells == 0
    assert result.verdict == "no_cells"
    assert result.median_abs_error_before is None
    assert result.delta is None


def test_family_statistic_validation():
    rng = np.random.default_rng(0)
    with pytest.raises(InputValidationError):
        family_transfer_statistic(
            (0.1, 0.2), (0.1,), model_id=MODEL, family="eos",
            properties=("b0",), rng=rng, n_bootstrap=10,
        )
    with pytest.raises(InputValidationError):
        family_transfer_statistic(
            (-0.1,), (0.1,), model_id=MODEL, family="eos",
            properties=("b0",), rng=rng, n_bootstrap=10,
        )
    with pytest.raises(InputValidationError):
        family_transfer_statistic(
            (0.1,), (0.1,), model_id=MODEL, family="eos",
            properties=("b0",), rng=rng, n_bootstrap=0,
        )
    with pytest.raises(InputValidationError):
        family_transfer_statistic(
            (0.1,), (0.1,), model_id=MODEL, family="eos",
            properties=("b0",), rng=1234, n_bootstrap=10,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Registered verdict logic
# ---------------------------------------------------------------------------


def test_verdict_requires_eos_family_with_cells():
    with pytest.raises(InputValidationError):
        h4_model_verdict(
            (_family_result("point_defect", "improves"),), model_id=MODEL
        )
    with pytest.raises(InputValidationError):
        h4_model_verdict(
            (
                _family_result("eos", "no_cells"),
                _family_result("point_defect", "improves"),
            ),
            model_id=MODEL,
        )


def test_verdict_ambiguous_when_pass_and_kill_both_fire():
    # 4 non-EOS families: 2 improve, 2 unchanged, EOS improves ->
    # pass condition (>= half improve, none degrade) AND kill condition
    # (EOS improves, >= half degrade-or-unchanged) both hold.
    families = (
        _family_result("eos", "improves"),
        _family_result("point_defect", "improves"),
        _family_result("surfaces", "improves"),
        _family_result("planar_fault", "unchanged", delta=0.0),
        _family_result("compound_stability", "unchanged", delta=0.0),
    )
    verdict = h4_model_verdict(families, model_id=MODEL)
    assert verdict.pass_condition and verdict.kill_condition
    assert verdict.verdict == "ambiguous"


# ---------------------------------------------------------------------------
# Planted pipeline scenarios (registered synthetic tests)
# ---------------------------------------------------------------------------


def test_uniform_softening_everything_improves_h4_pass():
    factors = {prop: 0.8 for prop in FCC_REF_BASE}
    report = _build(_world(factors), _references())
    model = report["per_model"][MODEL]
    for fold in model["loo_folds"]:
        assert fold["scalar"] == pytest.approx(1.25)
        assert fold["n_donors"] == len(FCC_MATERIALS) - 1
    assert model["scalar_median"] == pytest.approx(1.25)
    for family in ("eos",) + NON_EOS_FAMILIES:
        result = model["families"][family]
        assert result["median_abs_error_before"] == pytest.approx(0.2)
        assert result["median_abs_error_after"] == pytest.approx(0.0, abs=1e-12)
        assert result["delta"] == pytest.approx(-0.2)
        assert result["verdict"] == "improves"
    assert model["families"]["compound_stability"]["verdict"] == "no_cells"
    assert model["families"]["compound_stability"]["n_cells"] == 0
    assert model["verdict"]["pass_condition"] is True
    assert model["verdict"]["kill_condition"] is False
    assert model["verdict"]["verdict"] == "pass"
    assert report["overall"]["verdict"] == "pass"


def test_family_local_softening_h4_kill():
    factors = {
        "a0": 1.0,
        "b0": 0.8,  # soft EOS: the operator is fitted to fix exactly this
        "e_vac": 1.6,  # defect families wrong by independent large factors
        "gamma_100": 1.8,
        "gamma_110": 1.8,
        "gamma_111": 1.8,
        "gamma_sfe": 2.2,
    }
    report = _build(_world(factors), _references())
    model = report["per_model"][MODEL]
    assert model["scalar_median"] == pytest.approx(1.25)
    eos = model["families"]["eos"]
    assert eos["verdict"] == "improves"
    assert eos["delta"] == pytest.approx(-0.2)
    for family in NON_EOS_FAMILIES:
        result = model["families"][family]
        assert result["verdict"] == "degrades"
        assert result["delta"] > 0.0
    verdict = model["verdict"]
    assert verdict["eos_family_verdict"] == "improves"
    assert verdict["n_degrade"] == len(NON_EOS_FAMILIES)
    assert verdict["pass_condition"] is False
    assert verdict["kill_condition"] is True
    assert verdict["verdict"] == "kill"
    assert report["overall"]["verdict"] == "kill"


def test_bcc_availability_follows_data():
    factors = {prop: 0.8 for prop in BCC_REF_BASE}
    runs = _world(factors, ref_base=BCC_REF_BASE, structure="bcc")
    refs = _references(ref_base=BCC_REF_BASE, structure="bcc")
    report = _build(runs, refs)
    model = report["per_model"][MODEL]
    assert model["families"]["planar_fault"]["verdict"] == "no_cells"
    assert model["families"]["compound_stability"]["verdict"] == "no_cells"
    # Only point_defect and surfaces carry non-EOS cells; both improve.
    assert model["verdict"]["n_non_eos_families_with_cells"] == 2
    assert model["verdict"]["verdict"] == "pass"


def test_missing_b0_fails_fast():
    factors = {prop: 0.8 for prop in FCC_REF_BASE if prop != "b0"}
    with pytest.raises(InputValidationError, match="b0"):
        _build(_world(factors), _references())


def test_material_without_run_fails_fast():
    factors = {prop: 0.8 for prop in FCC_REF_BASE}
    runs = tuple(r for r in _world(factors) if r.material != "M3")
    with pytest.raises(InputValidationError, match="M3"):
        _build(runs, _references())


def test_report_is_deterministic_and_serializable():
    factors = {prop: 0.9 for prop in FCC_REF_BASE}
    report_a = _build(_world(factors), _references())
    report_b = _build(_world(factors), _references())
    assert json.dumps(report_a, sort_keys=True) == json.dumps(
        report_b, sort_keys=True
    )


def test_report_is_self_describing():
    factors = {prop: 0.8 for prop in FCC_REF_BASE}
    report = _build(_world(factors), _references(), deviations=("example",))
    assert report["schema"] == H4_SCHEMA_ID
    assert report["hypothesis"] == "H4"
    assert "addendum" in report and "2026-07-02" in report["addendum"]
    assert report["seed"] == REGISTERED_SEED
    assert report["materials"] == list(FCC_MATERIALS)
    assert "b0" in report["corrected_properties"]
    assert "a0" not in report["corrected_properties"]
    assert report["deviations"] == ["example"]
    assert any("dh_f" in note for note in report["notes"])
    assert "a0" in " ".join(report["notes"])


def test_corrected_properties_registered_set():
    assert CORRECTED_PROPERTIES == (
        "b0",
        "e_vac",
        "gamma_100",
        "gamma_110",
        "gamma_111",
        "gamma_sfe",
        "dh_f",
    )
    assert H4_TARGET_PROPERTY_MAP["bulk_modulus_0K_extrapolated"] == "b0"
    assert H4_TARGET_PROPERTY_MAP["lattice_constant_a"] == "a0"


# ---------------------------------------------------------------------------
# Real-data smoke: registered H4 run configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUNS_DIR = DATA_DIR / "y_matrix_runs"
TARGETS_DIR = DATA_DIR / "y_matrix_targets"
ARTIFACT = RUNS_DIR / "analysis" / "h4_transfer.json"
PRIMARY_MATCHED_SET = (
    "Ag", "Al", "Au", "Ca", "Cu", "Fe", "Mo", "Nb",
    "Ni", "Pd", "Pt", "Sr", "Ta", "V", "W",
)
SWEEP_MODELS = ("mace-mp-small", "mace-mp-medium", "chgnet")


@pytest.mark.skipif(
    not (RUNS_DIR.is_dir() and TARGETS_DIR.is_dir()),
    reason="y_matrix data directories not present",
)
def test_h4_real_data_run_matches_saved_artifact():
    runs = load_run_directory(RUNS_DIR)
    targets = load_targets_directory(
        TARGETS_DIR, property_map=H4_TARGET_PROPERTY_MAP
    )
    report = build_h4_transfer_report(
        runs,
        targets.entries,
        model_ids=SWEEP_MODELS,
        materials=PRIMARY_MATCHED_SET,
        near_zero_epsilon=1e-6,
        seed=REGISTERED_SEED,
        n_bootstrap=1000,
    )
    assert report["materials"] == list(PRIMARY_MATCHED_SET)
    for model in SWEEP_MODELS:
        per_model = report["per_model"][model]
        assert len(per_model["loo_folds"]) == len(PRIMARY_MATCHED_SET)
        assert per_model["scalar_median"] > 0.0
        assert per_model["families"]["compound_stability"]["verdict"] == "no_cells"
        assert per_model["verdict"]["verdict"] in (
            "pass", "kill", "inconclusive", "ambiguous"
        )
    if ARTIFACT.is_file():
        saved = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        # The CLI runner adds provenance keys on top of the library report.
        for runner_key in ("config_source", "unmapped_target_properties"):
            saved.pop(runner_key, None)
        assert saved == report, "saved h4_transfer.json is not reproducible"
