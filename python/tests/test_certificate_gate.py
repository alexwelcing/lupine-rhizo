"""Run-time certificate gate: Lean tier-2 refusals exclude cells from correction.

The gate (`lupine_distill_runtime.policy_engine.CertificateGate`) indexes the
env-field binding report's refusal certificates and the wrapping engine strips
the support model for matching (model, material) predictions — the correction
is never applied where the Lean layer proved the directional field
inadmissible. These tests run against the REAL repo report so the gate is
pinned to the same corpus the Lean `#guard` locks verify.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lupine_distill_runtime.policy_engine import (
    CertificateGate,
    CertificateGatedPolicyEngine,
    PythonPolicyEngine,
    build_policy_engine,
)
from lupine_distill_runtime.session import DistillSession

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT = _REPO_ROOT / "data" / "y_matrix_runs" / "env_field_binding_report.json"


class _BiasSupportModel:
    """Minimal support model: +0.1 eV/atom energy correction, one action."""

    def correct_prediction(self, prediction):
        corrected = dict(prediction)
        corrected["energy_ev_per_atom"] = float(prediction["energy_ev_per_atom"]) + 0.1
        return corrected, [{"action": "delta_correct", "field": "energy_ev_per_atom"}]

    def correction_evidence(self):
        return {"energy_bias_ev_per_atom": 0.1}


def _gated_engine() -> CertificateGatedPolicyEngine:
    gate = CertificateGate.load(REPORT)
    assert gate is not None and gate.refusals
    return CertificateGatedPolicyEngine(PythonPolicyEngine("accuracy"), gate)


def test_gate_indexes_repo_refusals():
    gate = CertificateGate.load(REPORT)
    assert gate is not None
    assert gate.corpus_sha256_12
    # chgnet: Ca/Pt/Sr (fcc) and Nb/Ta/V (bcc) are tier-2 refused.
    chgnet = sorted(m for (model, m) in gate.refusals if model == "chgnet")
    assert chgnet == ["ca", "nb", "pt", "sr", "ta", "v"]
    # every indexed entry is a refusal, never a tier-2 cell
    assert all(
        entry["certificate"].tier == "measured_field"
        for entry in gate.refusals.values()
    )


def test_gate_missing_report_is_disabled():
    assert CertificateGate.load("/nonexistent/report.json") is None


def test_refused_cell_is_excluded_from_correction():
    engine = _gated_engine()
    decision = engine.decide(
        row_id="energy_volume",
        mlip_id="chgnet",
        prediction={"material_id": "Pt-fcc-conventional", "energy_ev_per_atom": -6.0},
        support_model=_BiasSupportModel(),
    )
    # the correction was never applied — not applied-then-reverted
    assert decision.corrected_prediction["energy_ev_per_atom"] == -6.0
    skip = [a for a in decision.actions if a.get("action") == "skip_correction"]
    assert len(skip) == 1
    assert skip[0]["theorem_ref"].endswith("AnchoredField.mkMeasuredField")
    assert skip[0]["lean_name"] == "chgnet_Pt"
    assert decision.theorem_hooks["env_field_certificate"]["structure"] == "fcc"
    # the prediction itself is NOT refused; only its correction is skipped
    assert not decision.refused


def test_admissible_cell_still_corrected():
    engine = _gated_engine()
    decision = engine.decide(
        row_id="energy_volume",
        mlip_id="chgnet",
        prediction={"material_id": "Ni-fcc-conventional", "energy_ev_per_atom": -5.0},
        support_model=_BiasSupportModel(),
    )
    assert decision.corrected_prediction["energy_ev_per_atom"] == pytest.approx(-4.9)
    assert not any(a.get("action") == "skip_correction" for a in decision.actions)


def test_single_species_symbols_match_bcc_refusal():
    engine = _gated_engine()
    decision = engine.decide(
        row_id="energy_volume",
        mlip_id="chgnet",
        prediction={"symbols": ["Ta", "Ta"], "energy_ev_per_atom": -11.0},
        support_model=_BiasSupportModel(),
    )
    skip = [a for a in decision.actions if a.get("action") == "skip_correction"]
    assert len(skip) == 1
    assert skip[0]["structure"] == "bcc"
    assert skip[0]["theorem_ref"].endswith("AnchoredField.mkMeasuredFieldBcc")


def test_decide_many_preserves_order_with_mixed_batch():
    engine = _gated_engine()
    predictions = [
        {"material_id": "Ni-fcc", "energy_ev_per_atom": -5.0},
        {"material_id": "Pt-fcc", "energy_ev_per_atom": -6.0},
        {"material_id": "Cu-fcc", "energy_ev_per_atom": -3.0},
    ]
    decisions = engine.decide_many(
        row_id="energy_volume",
        mlip_id="chgnet",
        predictions=predictions,
        support_model=_BiasSupportModel(),
    )
    assert len(decisions) == 3
    assert decisions[0].corrected_prediction["energy_ev_per_atom"] == pytest.approx(-4.9)
    assert decisions[1].corrected_prediction["energy_ev_per_atom"] == -6.0
    assert decisions[2].corrected_prediction["energy_ev_per_atom"] == pytest.approx(-2.9)
    assert any(a.get("action") == "skip_correction" for a in decisions[1].actions)


def test_runtime_alias_gates_mace_mp_0():
    """The runner's `mace-mp-0` loads mace_mp(model="medium") — the binder's
    `mace-mp-medium` — so its refusal certificates must gate `mace-mp-0`
    predictions (Codex P1 on PR #17)."""
    gate = CertificateGate.load(REPORT)
    assert any(model == "mace-mp-0" for (model, _m) in gate.refusals)
    engine = CertificateGatedPolicyEngine(PythonPolicyEngine("accuracy"), gate)
    decision = engine.decide(
        row_id="energy_volume",
        mlip_id="mace-mp-0",
        prediction={"symbols": ["W", "W"], "energy_ev_per_atom": -13.0},
        support_model=_BiasSupportModel(),
    )
    skip = [a for a in decision.actions if a.get("action") == "skip_correction"]
    assert len(skip) == 1
    assert skip[0]["lean_name"] == "mace_mp_medium_W"
    assert decision.corrected_prediction["energy_ev_per_atom"] == -13.0


def test_unbound_model_is_inert():
    engine = _gated_engine()
    decision = engine.decide(
        row_id="energy_volume",
        mlip_id="uma-s-1p1",
        prediction={"material_id": "Pt-fcc", "energy_ev_per_atom": -6.0},
        support_model=_BiasSupportModel(),
    )
    assert decision.corrected_prediction["energy_ev_per_atom"] == pytest.approx(-5.9)


def test_build_policy_engine_wraps_and_disables():
    gated = build_policy_engine(
        "python", profile="accuracy", env_field_report_path=str(REPORT)
    )
    assert isinstance(gated, CertificateGatedPolicyEngine)
    bare = build_policy_engine("python", profile="accuracy", env_field_report_path=None)
    assert isinstance(bare, PythonPolicyEngine)


def test_session_summary_carries_gate_provenance():
    session = DistillSession(
        profile="accuracy",
        run_id="run",
        cell_id="cell",
        row_id="energy_volume",
        mlip_id="chgnet",
        env_field_report_path=str(REPORT),
    )
    gate_summary = session.summary()["certificate_gate"]
    assert gate_summary is not None
    assert gate_summary["refusal_cells"] > 0
    assert gate_summary["corpus_sha256_12"]
