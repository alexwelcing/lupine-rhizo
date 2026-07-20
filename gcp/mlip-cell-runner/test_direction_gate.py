"""Tests for the runtime direction gate port (H3a) and overhead
instrumentation (H3b).

The golden-replication classes pin the runtime gate to the proven offline
reference implementations on identical inputs:

- Round-3 frozen rule (``python/scripts/run_round3_analysis.py``,
  ``apply_frozen_rule``) under ``cap_version="round3-frozen"`` — the ratio
  sets are the ones pinned in ``python/tests/test_run_round3_analysis.py``.
- Round-4 theorem caps (``tools/round4_cloud_campaign.py``, ``correction``)
  under the default ``cap_version="round4-v2"``.

The remaining classes cover class-aware gating in ``DistillSupportModel``,
abstention event payloads, back-compat with unlabeled support sets,
cap-version selection, and the session overhead/theorem-hooks surfaces.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from lupine_distill_runtime import DistillSession, DistillSupportModel
from lupine_distill_runtime.direction_gate import (
    DEFAULT_CAP_VERSION,
    ROUND3_FROZEN_CAP_VERSION,
    direction_gated_correction,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "python" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_round3_analysis as r3  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "round4_cloud_campaign",
    _REPO_ROOT / "tools" / "round4_cloud_campaign.py",
)
assert _spec is not None and _spec.loader is not None
_round4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_round4)


THEOREM_WRONG_DIRECTION_INFLATION = "Shapes.Certificates wrong_direction_inflation_worsens"
THEOREM_WRONG_DIRECTION_DEFLATION = "Shapes.Certificates wrong_direction_deflation_worsens"
THEOREM_CAPPED_INHULL_INFLATION = "Shapes.Certificates capped_inhull_correction_helps_inflation"
THEOREM_CAPPED_INHULL_DEFLATION = "Shapes.Certificates capped_inhull_correction_helps_deflation"


# --------------------------------------------------------------------------
# golden replication: runtime gate vs offline Round-3 frozen rule
# --------------------------------------------------------------------------

# (pred, ratios) cases pinned by python/tests/test_run_round3_analysis.py.
ROUND3_CASES = [
    (200.0, (1.05, 1.25)),  # |b-1| = 0.15 <= s = 0.20 -> magnitude_cap
    (10.0, (1.25, 1.75)),  # |b-1| == s exactly -> not strictly > -> magnitude_cap
    (10.0, (0.9, 1.1)),  # mixed sides -> direction
    (10.0, (1.0, 1.2)),  # ratio exactly 1 is not strict -> direction
    (10.0, ()),  # insufficient_calibration
    (10.0, (1.5,)),  # insufficient_calibration
    (155.0, (1.5, 1.6)),  # apply, corrected = 100
    (52.5, (0.5, 0.55)),  # deflation side apply, corrected = 100
    (150.0, (1.5, 1.5)),  # zero scatter applies, corrected = 100
]

#: The offline Round-3 rule names the cap abstention "magnitude_cap"; the
#: runtime port's reason vocabulary folds both cap versions into
#: "theorem_cap" (the cap_version field keeps them distinguishable).
_ROUND3_REASON_MAP = {"magnitude_cap": "theorem_cap"}


class TestGoldenReplicationRound3Frozen:
    @pytest.mark.parametrize(("pred", "ratios"), ROUND3_CASES)
    def test_matches_apply_frozen_rule(self, pred, ratios):
        offline = r3.apply_frozen_rule(pred, ratios)
        gated = direction_gated_correction(ratios, cap_version=ROUND3_FROZEN_CAP_VERSION)

        assert gated.applied == offline["applied"]
        assert gated.b == offline["b"]
        assert gated.s == offline["s"]
        assert gated.n_calibration == offline["n_calibration"]
        expected_reason = _ROUND3_REASON_MAP.get(
            offline["abstain_reason"], offline["abstain_reason"]
        )
        assert gated.abstain_reason == expected_reason
        assert gated.corrected_value(pred) == pytest.approx(offline["corrected"])
        assert gated.cap_version == ROUND3_FROZEN_CAP_VERSION


# --------------------------------------------------------------------------
# golden replication: runtime gate vs offline Round-4 theorem caps
# --------------------------------------------------------------------------

ROUND4_CASES = [
    (1.0, (1.3, 1.4)),  # inflation: b-1 = 0.35 > 2s = 0.2 -> apply
    (1.0, (1.1, 1.2)),  # inflation: 0.15 <= 0.2 -> theorem_cap
    (1.0, (0.5, 0.55)),  # deflation: 1-b = 0.475 > 3s = 0.15, b >= 0.5 -> apply
    (1.0, (0.7, 0.8)),  # deflation: 0.25 <= 0.3 -> theorem_cap
    (1.0, (0.3, 0.32)),  # deflation below the b >= 0.5 floor -> theorem_cap
    (1.0, (0.9, 1.1)),  # mixed sides -> direction
    (1.0, (1.2,)),  # insufficient_calibration
    (1.0, ()),  # insufficient_calibration
]


class TestGoldenReplicationRound4:
    @pytest.mark.parametrize(("pred", "ratios"), ROUND4_CASES)
    def test_matches_round4_correction(self, pred, ratios):
        offline = _round4.correction(pred, list(ratios))
        gated = direction_gated_correction(ratios)

        assert gated.applied == offline["applied"]
        assert gated.abstain_reason == offline["abstain_reason"]
        assert gated.b == offline["b"]
        assert gated.s == offline["s"]
        assert gated.cap_version == DEFAULT_CAP_VERSION == "round4-v2"
        if gated.applied:
            assert gated.corrected_value(pred) == pytest.approx(offline["corrected"])
        else:
            assert gated.corrected_value(pred) == pred


# --------------------------------------------------------------------------
# gate semantics: theorem refs, cap-version selection, multiplicative value
# --------------------------------------------------------------------------


class TestGateSemantics:
    def test_direction_abstain_refs_follow_median_sign(self):
        inflation = direction_gated_correction((1.2, 0.9))  # b = 1.05 > 1
        assert inflation.abstain_reason == "direction"
        assert inflation.theorem_refs == (THEOREM_WRONG_DIRECTION_INFLATION,)

        deflation = direction_gated_correction((0.8, 1.05))  # b = 0.925 < 1
        assert deflation.abstain_reason == "direction"
        assert deflation.theorem_refs == (THEOREM_WRONG_DIRECTION_DEFLATION,)

        balanced = direction_gated_correction((0.9, 1.1))  # b == 1.0 exactly
        assert balanced.abstain_reason == "direction"
        assert balanced.theorem_refs == (
            THEOREM_WRONG_DIRECTION_INFLATION,
            THEOREM_WRONG_DIRECTION_DEFLATION,
        )

    def test_theorem_cap_refs_follow_side(self):
        inflation = direction_gated_correction((1.1, 1.2))
        assert inflation.abstain_reason == "theorem_cap"
        assert inflation.theorem_refs == (THEOREM_CAPPED_INHULL_INFLATION,)

        deflation = direction_gated_correction((0.7, 0.8))
        assert deflation.abstain_reason == "theorem_cap"
        assert deflation.theorem_refs == (THEOREM_CAPPED_INHULL_DEFLATION,)

    def test_applied_correction_carries_no_theorem_refs(self):
        gated = direction_gated_correction((1.5, 1.6))
        assert gated.applied is True
        assert gated.abstain_reason is None
        assert gated.theorem_refs == ()

    def test_cap_version_selection_changes_borderline_outcome(self):
        # b = 1.2, s = 0.1: frozen cap 0.2 > 0.1 applies; theorem cap
        # requires b - 1 > 2s i.e. 0.2 > 0.2, which fails.
        frozen = direction_gated_correction((1.15, 1.25), cap_version=ROUND3_FROZEN_CAP_VERSION)
        v2 = direction_gated_correction((1.15, 1.25), cap_version="round4-v2")
        assert frozen.applied is True
        assert v2.applied is False
        assert v2.abstain_reason == "theorem_cap"

    def test_unknown_cap_version_rejected(self):
        with pytest.raises(ValueError, match="cap_version"):
            direction_gated_correction((1.5, 1.6), cap_version="round9")

    def test_corrected_value_is_multiplicative_not_additive(self):
        gated = direction_gated_correction((1.5, 1.6))
        assert gated.corrected_value(155.0) == pytest.approx(100.0)
        assert gated.corrected_value(155.0) != pytest.approx(155.0 - 0.55)

    def test_nonfinite_ratios_are_dropped_like_the_offline_prefilter(self):
        gated = direction_gated_correction((1.5, float("nan"), 1.6, float("inf")))
        assert gated.applied is True
        assert gated.n_calibration == 2
        assert gated.b == pytest.approx(1.55)


# --------------------------------------------------------------------------
# support-model wiring: class-aware gated fit + multiplicative correction
# --------------------------------------------------------------------------


def _energy_support(pred_value, ref_value, label=None, structure_id="s", label_key="class"):
    record = {
        "structure_id": structure_id,
        "energy_ev_per_atom": pred_value,
        "reference": {"energy_ev_per_atom": ref_value},
    }
    if label is not None:
        record[label_key] = label
    return record


def _gated_support_predictions():
    return [
        # class A: ratios 1.5, 1.6 -> b = 1.55, s = 0.1 -> applies (0.55 > 0.2)
        _energy_support(1.5, 1.0, "A", "a1"),
        _energy_support(3.2, 2.0, "A", "a2"),
        # class B: ratios 1.1, 1.2 -> b = 1.15, s = 0.1 -> theorem_cap (0.15 <= 0.2)
        _energy_support(1.1, 1.0, "B", "b1"),
        _energy_support(2.4, 2.0, "B", "b2"),
    ]


class TestGatedSupportModel:
    def test_fit_groups_ratios_by_class_and_gates(self):
        model = DistillSupportModel.fit("energy_volume", _gated_support_predictions())

        cells = model.gated["energy_ev_per_atom"]
        assert set(cells) == {"A", "B"}
        assert cells["A"].applied is True
        assert cells["A"].b == pytest.approx(1.55)
        assert cells["B"].applied is False
        assert cells["B"].abstain_reason == "theorem_cap"
        assert cells["B"].theorem_refs == (THEOREM_CAPPED_INHULL_INFLATION,)
        # Gated mode supersedes the un-gated additive path.
        assert model.correction == {}
        assert "energy_bias_ev_per_atom" not in model.candidate_correction
        assert model.diagnostics["energy_correction_gate"] == "superseded_by_direction_gate"
        gate_block = model.diagnostics["direction_gate"]
        assert gate_block["schema"] == "lupine.distill.direction_gate.v1"
        assert gate_block["cap_version"] == "round4-v2"
        assert gate_block["cells"]["energy_ev_per_atom"]["B"]["n_calibration"] == 2

    def test_correct_prediction_scales_gated_class_multiplicatively(self):
        model = DistillSupportModel.fit("energy_volume", _gated_support_predictions())

        corrected, interventions = model.correct_prediction(
            {"structure_id": "e1", "class": "A", "energy_ev_per_atom": 7.75}
        )

        assert corrected["energy_ev_per_atom"] == pytest.approx(5.0)  # 7.75 / 1.55
        [action] = interventions
        assert action["action"] == "scale_correct"
        assert action["field"] == "energy_ev_per_atom"
        assert action["class"] == "A"
        assert action["b"] == pytest.approx(1.55)
        assert action["n_calibration"] == 2
        assert action["cap_version"] == "round4-v2"

    def test_correct_prediction_abstains_with_full_payload(self):
        model = DistillSupportModel.fit("energy_volume", _gated_support_predictions())

        corrected, interventions = model.correct_prediction(
            {"structure_id": "e2", "class": "B", "energy_ev_per_atom": 5.0}
        )

        assert corrected["energy_ev_per_atom"] == 5.0
        [action] = interventions
        assert action["action"] == "skip_correction"
        assert action["gate"] == "direction_gate"
        assert action["abstain_reason"] == "theorem_cap"
        assert action["b"] == pytest.approx(1.15)
        assert action["s"] == pytest.approx(0.1)
        assert action["n_calibration"] == 2
        assert action["theorem_refs"] == [THEOREM_CAPPED_INHULL_INFLATION]
        assert action["cap_version"] == "round4-v2"

    def test_unknown_eval_class_abstains_insufficient_calibration(self):
        model = DistillSupportModel.fit("energy_volume", _gated_support_predictions())

        corrected, interventions = model.correct_prediction(
            {"structure_id": "e3", "class": "Z", "energy_ev_per_atom": 5.0}
        )

        assert corrected["energy_ev_per_atom"] == 5.0
        [action] = interventions
        assert action["action"] == "skip_correction"
        assert action["abstain_reason"] == "insufficient_calibration"
        assert action["n_calibration"] == 0
        assert action["b"] is None

    def test_group_label_synonym_and_default_class(self):
        predictions = [
            _energy_support(1.5, 1.0, "A", "a1", label_key="group"),
            _energy_support(3.2, 2.0, "A", "a2", label_key="group"),
            _energy_support(1.5, 1.0, None, "u1"),  # unlabeled -> default class
            _energy_support(3.2, 2.0, None, "u2"),
        ]
        model = DistillSupportModel.fit("energy_volume", predictions)

        cells = model.gated["energy_ev_per_atom"]
        assert set(cells) == {"A", "default"}
        assert cells["A"].applied is True
        assert cells["default"].applied is True

        corrected, interventions = model.correct_prediction(
            {"structure_id": "e4", "energy_ev_per_atom": 7.75}
        )
        assert corrected["energy_ev_per_atom"] == pytest.approx(5.0)
        assert interventions[0]["class"] == "default"

    def test_fit_cap_version_selection(self):
        # ratios 1.15, 1.25 -> applies under round3-frozen, theorem_cap under round4-v2
        predictions = [
            _energy_support(1.15, 1.0, "A", "a1"),
            _energy_support(2.5, 2.0, "A", "a2"),
        ]
        model_v2 = DistillSupportModel.fit("energy_volume", predictions)
        model_frozen = DistillSupportModel.fit(
            "energy_volume", predictions, cap_version=ROUND3_FROZEN_CAP_VERSION
        )

        cell_v2 = model_v2.gated["energy_ev_per_atom"]["A"]
        cell_frozen = model_frozen.gated["energy_ev_per_atom"]["A"]
        assert cell_v2.applied is False
        assert cell_v2.abstain_reason == "theorem_cap"
        assert cell_v2.cap_version == "round4-v2"
        assert cell_frozen.applied is True
        assert cell_frozen.cap_version == ROUND3_FROZEN_CAP_VERSION


class TestUnlabeledBackCompat:
    def test_unlabeled_support_set_keeps_legacy_additive_path(self):
        model = DistillSupportModel.fit(
            "energy_volume",
            [
                {"energy_ev_per_atom": 2.0, "reference": {"energy_ev_per_atom": 1.5}},
                {"energy_ev_per_atom": 4.0, "reference": {"energy_ev_per_atom": 3.5}},
            ],
        )

        assert model.gated == {}
        assert model.correction == {"energy_bias_ev_per_atom": pytest.approx(-0.5)}
        assert "direction_gate" not in model.diagnostics
        assert model.diagnostics["energy_correction_gate"] == "passed"

        corrected, interventions = model.correct_prediction({"energy_ev_per_atom": 8.0})
        assert corrected["energy_ev_per_atom"] == pytest.approx(7.5)
        assert interventions == [{"action": "delta_correct", "field": "energy_ev_per_atom"}]

    def test_unlabeled_fit_support_emits_no_gate_events(self):
        session = DistillSession(
            profile="accuracy",
            run_id="run",
            cell_id="cell",
            row_id="energy_volume",
            mlip_id="mock-mlip",
            support_manifest={"schema": "test", "structures": []},
        )
        predictions = [
            {"energy_ev_per_atom": 2.0, "reference": {"energy_ev_per_atom": 1.5}},
            {"energy_ev_per_atom": 4.0, "reference": {"energy_ev_per_atom": 3.5}},
        ]

        session.fit_support(None, lambda row_id, manifest, calc: {"predictions": predictions})

        assert session.support_model is not None
        assert session.support_model.gated == {}
        assert not any(
            event["kind"] == "policy.direction_gate" for event in session.event_log.events
        )


# --------------------------------------------------------------------------
# session wiring: policy events, summary overhead, theorem hooks
# --------------------------------------------------------------------------


def _gated_session() -> DistillSession:
    session = DistillSession(
        profile="accuracy",
        run_id="run",
        cell_id="cell",
        row_id="energy_volume",
        mlip_id="mock-mlip",
        support_manifest={"schema": "test", "structures": []},
    )
    session.fit_support(
        None,
        lambda row_id, manifest, calc: {"predictions": _gated_support_predictions()},
    )
    return session


class TestSessionGateEvents:
    def test_fit_support_emits_policy_event_per_cell(self):
        session = _gated_session()

        gate_events = [
            event for event in session.event_log.events if event["kind"] == "policy.direction_gate"
        ]
        assert len(gate_events) == 2
        by_class = {event["class_label"]: event for event in gate_events}
        assert by_class["A"]["applied"] is True
        assert by_class["A"]["abstain_reason"] is None
        assert by_class["A"]["b"] == pytest.approx(1.55)
        assert by_class["B"]["applied"] is False
        assert by_class["B"]["abstain_reason"] == "theorem_cap"
        assert by_class["B"]["theorem_refs"] == [THEOREM_CAPPED_INHULL_INFLATION]
        assert by_class["B"]["n_calibration"] == 2
        assert by_class["B"]["cap_version"] == "round4-v2"
        assert by_class["B"]["field"] == "energy_ev_per_atom"
        # The whole event stream must stay JSON-serializable for distill_events.jsonl.
        json.dumps(session.event_log.events, sort_keys=True)

    def test_apply_row_policy_flows_abstain_into_distill_block(self):
        session = _gated_session()

        [prediction] = session.apply_row_policy(
            [{"structure_id": "e2", "class": "B", "energy_ev_per_atom": 5.0}]
        )

        assert prediction["energy_ev_per_atom"] == 5.0
        actions = prediction["distill"]["interventions"]
        skip = next(action for action in actions if action.get("gate") == "direction_gate")
        assert skip["action"] == "skip_correction"
        assert skip["abstain_reason"] == "theorem_cap"
        assert skip["b"] == pytest.approx(1.15)
        assert skip["theorem_refs"] == [THEOREM_CAPPED_INHULL_INFLATION]
        assert any(
            intervention.get("gate") == "direction_gate"
            and intervention["abstain_reason"] == "theorem_cap"
            for intervention in session.interventions
        )
        json.dumps(session.summary(), sort_keys=True)

    def test_apply_row_policy_scales_gated_class(self):
        session = _gated_session()

        [prediction] = session.apply_row_policy(
            [{"structure_id": "e1", "class": "A", "energy_ev_per_atom": 7.75}]
        )

        assert prediction["energy_ev_per_atom"] == pytest.approx(5.0)
        actions = prediction["distill"]["interventions"]
        assert any(action["action"] == "scale_correct" for action in actions)


class TestOverheadInstrumentation:
    def test_summary_exposes_overhead_keys(self):
        session = _gated_session()
        session.apply_row_policy([{"structure_id": "e1", "class": "A", "energy_ev_per_atom": 7.75}])

        overhead = session.summary()["overhead"]
        assert set(overhead) == {"support_fit_s", "correction_s", "guards_s"}
        assert all(isinstance(value, float) for value in overhead.values())
        assert overhead["support_fit_s"] > 0.0
        assert overhead["correction_s"] >= 0.0
        assert overhead["guards_s"] >= 0.0

    def test_session_overhead_defaults_present_without_support(self):
        session = DistillSession(
            profile="off",
            run_id="run",
            cell_id="cell",
            row_id="energy_volume",
            mlip_id="mock-mlip",
        )
        overhead = session.summary()["overhead"]
        assert set(overhead) == {"support_fit_s", "correction_s", "guards_s"}
        assert all(value == 0.0 for value in overhead.values())

    def test_theorem_hooks_null_speedup_carries_reason(self):
        session = DistillSession(
            profile="off",
            run_id="run",
            cell_id="cell",
            row_id="energy_volume",
            mlip_id="mock-mlip",
        )

        hooks = session.theorem_hooks(duration_s=2.0)
        assert hooks["observed_speedup"] is None
        assert hooks["observed_speedup_reason"] == "no_baseline_duration"

        hooks = session.theorem_hooks(duration_s=2.0, baseline_duration_s=4.0)
        assert hooks["observed_speedup"] == pytest.approx(2.0)
        assert hooks["observed_speedup_reason"] is None


# --------------------------------------------------------------------------
# runner artifact: overhead keys + gated distill block end-to-end
# --------------------------------------------------------------------------

import mlip_cell_runner as runner  # noqa: E402
import numpy as np  # noqa: E402
from ase.calculators.calculator import Calculator, all_changes  # noqa: E402

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "canonical_structures_v2_mptrj.json"


class _ConstantEnergyCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        n = len(atoms)
        self.results = {
            "energy": -1.0 * n,
            "forces": np.zeros((n, 3)),
            "stress": np.zeros(6),
        }


def _labeled_support_manifest() -> dict:
    def structure(structure_id, cls, ref):
        return {
            "structure_id": structure_id,
            "class": cls,
            "symbols": ["Al"],
            "positions": [[0.0, 0.0, 0.0]],
            "cell": [[4.0, 0.0, 0.0], [0.0, 4.0, 0.0], [0.0, 0.0, 4.0]],
            "pbc": True,
            "reference": {"energy_ev_per_atom": ref},
        }

    # The mock calculator predicts -1.0 eV/atom everywhere, so the support
    # calibration ratios are 1.5/1.6 for class A (applies) and 1.1/1.2 for
    # class B (theorem_cap).
    return {
        "schema": "lupine.mlip.fixture_manifest.v2",
        "fixture_id": "direction-gate-support",
        "row_fixtures": {
            "energy_volume": {
                "structures": [
                    structure("sup-a1", "A", -2.0 / 3.0),
                    structure("sup-a2", "A", -0.625),
                    structure("sup-a3", "A", -1.0 / 1.55),
                    structure("sup-b1", "B", -1.0 / 1.1),
                    structure("sup-b2", "B", -1.0 / 1.2),
                ]
            }
        },
    }


@pytest.mark.integration
def test_runner_artifact_surfaces_overhead_and_gate(tmp_path, monkeypatch, capsys):
    def refuse_network(*_args, **_kwargs):
        raise AssertionError("offline run attempted a network call")

    monkeypatch.setattr(
        runner, "load_calculator", lambda mlip_id, **_kwargs: _ConstantEnergyCalculator()
    )
    monkeypatch.setattr(runner.requests, "request", refuse_network)
    monkeypatch.setattr(runner.requests, "get", refuse_network)
    monkeypatch.setattr(runner.requests, "post", refuse_network)

    support_path = tmp_path / "support.json"
    support_path.write_text(json.dumps(_labeled_support_manifest()), encoding="utf-8")
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(
        "sys.argv",
        [
            "mlip_cell_runner.py",
            "run-cell",
            "--run-id", "direction-gate-run",
            "--cell-id", "direction-gate-run:gated:energy_volume:mock:s000",
            "--row-id", "energy_volume",
            "--mlip-id", "mock-mlip",
            "--manifest-url", FIXTURE_PATH.as_uri(),
            "--support-manifest-url", support_path.as_uri(),
            "--distill-profile", "accuracy",
            "--artifact-prefix", str(artifacts),
            "--checkpoint-mode", "off",
        ],
    )

    rc = runner.main()

    assert rc == 0
    metrics = json.loads(capsys.readouterr().out)
    artifact = json.loads((artifacts / "cell_result.json").read_text(encoding="utf-8"))

    # H3b: overhead keys surface in the artifact and the runner metrics.
    distill_runtime = artifact["distill_runtime"]
    overhead = distill_runtime["overhead"]
    assert set(overhead) == {"support_fit_s", "correction_s", "guards_s"}
    assert overhead["support_fit_s"] > 0.0
    assert metrics["distill_runtime"]["overhead"] == overhead

    # H3b: no distill-off baseline -> null speedup WITH a reason.
    hooks = artifact["theorem_hooks"]
    assert hooks["observed_speedup"] is None
    assert hooks["observed_speedup_reason"] == "no_baseline_duration"
    assert metrics["theorem_hooks"]["observed_speedup_reason"] == "no_baseline_duration"

    # H3a: the labeled support manifest drives gated cells end-to-end.
    gate_block = distill_runtime["support_model"]["diagnostics"]["direction_gate"]
    assert gate_block["cap_version"] == "round4-v2"
    cells = gate_block["cells"]["energy_ev_per_atom"]
    assert cells["A"]["applied"] is True
    assert cells["A"]["b"] == pytest.approx(1.55)
    assert cells["B"]["abstain_reason"] == "theorem_cap"

    # Unlabeled eval predictions abstain fail-closed and carry the payload in
    # the artifact's per-prediction distill block.
    prediction = artifact["predictions"][0]
    skip = next(
        action
        for action in prediction["distill"]["interventions"]
        if action.get("gate") == "direction_gate"
    )
    assert skip["action"] == "skip_correction"
    assert skip["abstain_reason"] == "insufficient_calibration"
    assert skip["n_calibration"] == 0

    # The per-cell gate decisions land in distill_events.jsonl.
    events_path = artifacts / "distill_events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    gate_events = [event for event in events if event["kind"] == "policy.direction_gate"]
    assert len(gate_events) == 2
    by_class = {event["class_label"]: event for event in gate_events}
    assert by_class["A"]["applied"] is True
    assert by_class["B"]["abstain_reason"] == "theorem_cap"
    assert by_class["B"]["theorem_refs"] == [THEOREM_CAPPED_INHULL_INFLATION]
