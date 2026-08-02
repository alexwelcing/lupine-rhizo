"""Unit tests for the Distill-to-Phoenix OTLP span mapping.

Pure span-mapping contracts (no OTel SDK, no network): the promotion packet's
gate verdict, metric contract, and Lean field-certificate provenance must land
in root/child span attributes with the corrected metric semantics preserved
(promotion deltas positive-is-better, physical error reductions first-class).
"""

from __future__ import annotations

import pytest
import mlip_phoenix_trace
from mlip_phoenix_trace import (
    certificate_spans,
    cloud_cell_span_to_attributes,
    growth_report_to_spans,
    promotion_packet_to_spans,
    sanitize,
)

pytestmark = pytest.mark.unit


def _packet() -> dict:
    return {
        "schema": "lupine.mlip.local_to_cloud_promotion.v1",
        "cloud_run_id": "mlip-cloud-test",
        "created_at": "2026-07-10T00:00:00Z",
        "local_run_dir": "/runs/demo",
        "gate": {
            "status": "promote_to_gcp_canary",
            "objective": "accuracy",
            "blockers": [],
            "warnings": [],
            "complete_triplets": 2,
            "mean_distill_accuracy_delta": 0.012,
            "state_hypothesis": {
                "hypothesis_id": "distill.energy_state_lifts_lattice_observables",
                "verdict": "confirmed_state_lift",
                "anchor_row_id": "energy_volume",
                "energy_anchor_complete": 1,
                "energy_anchor_mean_delta": 0.012,
                "downstream_complete": 1,
                "downstream_regression_count": 0,
            },
        },
        "odf_gate": {
            "decision": "promote",
            "uplift_band": "promote",
            "formal_fields_present": True,
        },
        "field_certificates": {
            "corpus_sha256_12": "0da8d5b67142",
            "lean_module": (
                "lean-spec/OpenDistillationFactory/Materials/DistillAtlas/"
                "EnvFieldInstances.lean"
            ),
            "models": ["chgnet"],
            "n_cells": 2,
            "n_error_field": 1,
            "n_measured_field_refusals": 1,
            "theorem_refs": [
                "OpenDistillationFactory.Materials.Theory.AnchoredField.mkAnchoredFieldBcc",
                "OpenDistillationFactory.Materials.Theory.AnchoredField.mkMeasuredField",
            ],
            "cells": [
                {
                    "kind": "anchor_admissibility",
                    "material": "Fe",
                    "model_id": "chgnet",
                    "structure": "bcc",
                    "lean_name": "chgnet_Fe",
                    "tier": "error_field",
                    "coordinations": [4, 6, 7],
                    "anchors_scaled": [-4852, -4596, -1697],
                    "violations": [],
                    "theorem_ref": (
                        "OpenDistillationFactory.Materials.Theory.AnchoredField"
                        ".mkAnchoredFieldBcc"
                    ),
                    "reason": "monotone softening holds on the measured anchors",
                },
                {
                    "kind": "anchor_admissibility",
                    "material": "Pt",
                    "model_id": "chgnet",
                    "structure": "fcc",
                    "lean_name": "chgnet_Pt",
                    "tier": "measured_field",
                    "coordinations": [8, 9, 11],
                    "anchors_scaled": [-2766, -1683, 156],
                    "violations": ["P(11) = 156e-4 > 0 (softening)"],
                    "theorem_ref": (
                        "OpenDistillationFactory.Materials.Theory.AnchoredField"
                        ".mkMeasuredField"
                    ),
                    "reason": "tier-2 refusal",
                },
            ],
        },
        "summary": {"cells": 6, "triplets": 2},
        "thresholds": {"objective": "accuracy", "min_accuracy_delta": 0.0},
        "triplets": [
            {
                "triplet_id": "energy_volume:chgnet",
                "row_id": "energy_volume",
                "row_role": "energy_anchor",
                "energy_anchor": True,
                "mlip_id": "chgnet",
                "complete": True,
                "promotion_delta_distill": 0.012,
                "cells": {
                    "baseline": {"accuracy_error": 0.030},
                    "distill_accuracy": {"accuracy_error": 0.018},
                },
            },
        ],
    }


def test_root_span_carries_gate_and_hypothesis():
    root, children = promotion_packet_to_spans(_packet())
    assert root["mlip.gate.status"] == "promote_to_gcp_canary"
    assert root["mlip.hypothesis.verdict"] == "confirmed_state_lift"
    assert root["mlip.metric_contract.promotion_delta_positive_is_better"] is True
    assert len(children) == 1
    assert children[0]["mlip.triplet.promotion_delta_distill"] == 0.012


def test_root_span_carries_certificate_rollup():
    root, _children = promotion_packet_to_spans(_packet())
    assert root["mlip.odf_gate.decision"] == "promote"
    assert root["mlip.field_certificates.corpus_sha256_12"] == "0da8d5b67142"
    assert root["mlip.field_certificates.n_cells"] == 2
    assert root["mlip.field_certificates.n_error_field"] == 1
    assert root["mlip.field_certificates.n_measured_field_refusals"] == 1
    # Lists are JSON-encoded by sanitize so they survive as span attributes.
    assert "mkAnchoredFieldBcc" in root["mlip.field_certificates.theorem_refs"]


def test_certificate_spans_one_per_bound_cell():
    spans = certificate_spans(_packet())
    assert len(spans) == 2
    fe, pt = spans
    assert fe["mlip.certificate.lean_name"] == "chgnet_Fe"
    assert fe["mlip.certificate.tier"] == "error_field"
    assert fe["mlip.certificate.structure"] == "bcc"
    assert "mkAnchoredFieldBcc" in fe["mlip.certificate.theorem_ref"]
    assert pt["mlip.certificate.tier"] == "measured_field"
    assert "softening" in pt["mlip.certificate.violations"]


def test_certificate_spans_absent_block_is_empty():
    packet = _packet()
    packet.pop("field_certificates")
    assert certificate_spans(packet) == []
    root, _ = promotion_packet_to_spans(packet)
    assert "mlip.field_certificates.n_cells" not in root


def test_sanitize_drops_none_and_encodes_lists():
    out = sanitize({"a": None, "b": float("nan"), "c": [1, 2], "d": 1.5})
    assert "a" not in out and "b" not in out
    assert out["c"] == "[1, 2]"
    assert out["d"] == 1.5


def test_growth_report_spans_still_map():
    root, children = growth_report_to_spans({
        "schema": "lupine.mlip.growth_loop.v1",
        "search": {"rounds": 2, "beam_width": 3},
        "case_summary": {"count": 4},
        "results": [
            {
                "objective": "accuracy",
                "promotion_label": "promote",
                "best_candidate": {"accuracy_delta_mean": 0.01, "refusal_rate": 0.0},
            }
        ],
    })
    assert root["mlip.search.rounds"] == 2
    assert children[0]["mlip.objective"] == "accuracy"


def test_cloud_cell_span_matches_local_identity_and_cost_contract():
    attrs = cloud_cell_span_to_attributes({
        "schema": "lupine.mlip.cloud_cell_span.v1",
        "origin": "cloud",
        "correlation_id": "wf-nightly-42",
        "run_id": "baseline-20260801",
        "cell_id": "baseline-20260801:baseline:energy_volume:chgnet",
        "row_id": "energy_volume",
        "mlip_id": "chgnet",
        "schedule_name": "nightly-baseline",
        "dispatch_status": "admitted",
        "target_job": "mlip-cell-chgnet",
        "reserved_gpu_hours": 0.5,
        "reservation_gpu_hours": 0.5,
        "daily_gpu_hour_cap": 2.0,
    })

    assert attrs["mlip.schema"] == "lupine.mlip.cloud_cell_span.v1"
    assert attrs["mlip.origin"] == "cloud"
    assert attrs["mlip.correlation_id"] == "wf-nightly-42"
    assert attrs["mlip.cloud_run_id"] == "baseline-20260801"
    assert attrs["mlip.cell_id"] == "baseline-20260801:baseline:energy_volume:chgnet"
    assert attrs["mlip.triplet.row_id"] == "energy_volume"
    assert attrs["mlip.triplet.mlip_id"] == "chgnet"
    assert attrs["mlip.cost.reserved_gpu_hours"] == 0.5
    assert attrs["mlip.cost.daily_gpu_hour_cap"] == 2.0


def test_unscheduled_cloud_cell_span_matches_rust_and_node_contract():
    attrs = cloud_cell_span_to_attributes({
        "schema": "lupine.mlip.cloud_cell_span.v1",
        "origin": "cloud",
        "correlation_id": "campaign-a",
        "run_id": "run-a",
        "cell_id": "run-a:distill_accuracy:forces:mace-mp-0",
        "row_id": "forces",
        "mlip_id": "mace-mp-0",
        "schedule_name": "unscheduled-campaign",
        "dispatch_status": "admitted",
        "target_job": "mlip-cell-mace",
        "reserved_gpu_hours": 0.0,
        "reservation_gpu_hours": 0.0,
        "daily_gpu_hour_cap": 0.0,
    })

    assert attrs["mlip.correlation_id"] == "campaign-a"
    assert attrs["mlip.schedule.name"] == "unscheduled-campaign"
    assert attrs["mlip.cost.reservation_gpu_hours"] == 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "wrong.v1"),
        ("origin", "local"),
        ("correlation_id", ""),
        ("run_id", None),
        ("cell_id", 42),
        ("reserved_gpu_hours", float("nan")),
        ("reservation_gpu_hours", -0.1),
        ("daily_gpu_hour_cap", True),
    ],
)
def test_cloud_cell_span_rejects_malformed_envelopes(field: str, value: object):
    span = {
        "schema": "lupine.mlip.cloud_cell_span.v1",
        "origin": "cloud",
        "correlation_id": "wf-nightly-42",
        "run_id": "baseline-20260801",
        "cell_id": "baseline-20260801:baseline:energy_volume:chgnet",
        "row_id": "energy_volume",
        "mlip_id": "chgnet",
        "schedule_name": "nightly-baseline",
        "dispatch_status": "admitted",
        "target_job": "mlip-cell-chgnet",
        "reserved_gpu_hours": 0.5,
        "reservation_gpu_hours": 0.5,
        "daily_gpu_hour_cap": 2.0,
    }
    span[field] = value

    with pytest.raises(ValueError, match=field):
        cloud_cell_span_to_attributes(span)


def test_emit_cloud_cell_trace_uses_cloud_root_and_service(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}
    monkeypatch.setattr(
        mlip_phoenix_trace,
        "emit_trace",
        lambda **kwargs: captured.update(kwargs) or True,
    )
    span = {
        "schema": "lupine.mlip.cloud_cell_span.v1",
        "origin": "cloud",
        "correlation_id": "wf-nightly-42",
        "run_id": "baseline-20260801",
        "cell_id": "baseline-20260801:baseline:energy_volume:chgnet",
        "row_id": "energy_volume",
        "mlip_id": "chgnet",
        "schedule_name": "nightly-baseline",
        "dispatch_status": "admitted",
        "target_job": "mlip-cell-chgnet",
        "reserved_gpu_hours": 0.5,
        "reservation_gpu_hours": 0.5,
        "daily_gpu_hour_cap": 2.0,
    }

    assert mlip_phoenix_trace.emit_cloud_cell_trace(span, dry_run=True)
    assert captured["root_name"] == "mlip.flywheel.cloud_cell"
    assert captured["service"] == "tasks-consumer"
    assert captured["root_attributes"]["mlip.cell_id"] == span["cell_id"]
    assert captured["children"] == []
