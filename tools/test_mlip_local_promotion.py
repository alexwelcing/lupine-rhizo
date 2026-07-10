"""Unit tests for the promotion packet's Lean field-certificate wiring.

`load_field_certificates` reads the env-field binding report emitted by
`python/scripts/bind_env_field_instances.py` and re-checks each bound
(model, material) cell through the `field_certificates` mirror of the Lean
admissibility predicates. These tests run against the REAL repo report so the
wiring is pinned to the same corpus the Lean `#guard` locks verify — a binder
regeneration that changes the counts breaks here as well as in `lake build`.
"""

from __future__ import annotations

import pathlib

import mlip_local_promotion as promo
import pytest
from lupine_distill.odf.promotion_gate import evaluate_promotion

pytestmark = pytest.mark.unit

REPORT = promo.ENV_FIELD_REPORT


def test_repo_report_exists_and_loads_for_chgnet():
    env_field = promo.load_field_certificates(REPORT, ["chgnet"])
    assert env_field is not None
    assert env_field["corpus_sha256_12"]
    # chgnet binds every fcc (9), bcc (7), and diamond (1) material.
    assert len(env_field["entries"]) == 17
    structures = {entry["structure"] for entry in env_field["entries"]}
    assert structures == {"fcc", "bcc", "diamond"}


def test_chgnet_fe_bcc_cell_is_tier2_with_lean_ref():
    env_field = promo.load_field_certificates(REPORT, ["chgnet"])
    fe = next(
        entry
        for entry in env_field["entries"]
        if entry["material"] == "Fe" and entry["structure"] == "bcc"
    )
    cert = fe["certificate"]
    assert cert.tier == "error_field"
    assert cert.coordinations == (4, 6, 7)
    assert cert.theorem_ref.endswith("AnchoredField.mkAnchoredFieldBcc")
    assert fe["lean_name"] == "chgnet_Fe"


def test_unknown_model_yields_no_entries():
    env_field = promo.load_field_certificates(REPORT, ["no-such-model"])
    assert env_field is not None
    assert env_field["entries"] == []


def test_missing_report_returns_none():
    missing = pathlib.Path("/nonexistent/env_field_binding_report.json")
    assert promo.load_field_certificates(missing, ["chgnet"]) is None


def test_packet_block_rolls_up_tiers_and_refs():
    env_field = promo.load_field_certificates(REPORT, ["chgnet"])
    block = promo.field_certificates_packet_block(env_field, ["chgnet"])
    assert block["n_cells"] == 17
    assert block["n_error_field"] + block["n_measured_field_refusals"] == 17
    # chgnet softens monotonically on Ag/Al/Au/Cu/Ni/Pd (fcc),
    # Cr/Fe/Mo/W (bcc), and Si (diamond): 11 directional-tier cells.
    assert block["n_error_field"] == 11
    assert any(ref.endswith("mkAnchoredFieldBcc") for ref in block["theorem_refs"])
    cell = block["cells"][0]
    assert {"material", "model_id", "structure", "lean_name", "tier",
            "anchors_scaled", "theorem_ref", "reason"} <= set(cell)
    assert promo.field_certificates_packet_block(None, []) is None


def test_certificates_satisfy_odf_formal_gate():
    """The wired certificates ARE the formal contract: a promotable uplift
    plus the bound cells' theorem refs clears the gate without manual
    --atlas-theorem-refs flags."""
    env_field = promo.load_field_certificates(REPORT, ["chgnet"])
    from lupine_distill.odf.field_certificates import merge_into_candidate_metadata

    metadata = {
        "model_id": "chgnet-distill-v3",
        "distill_version": 3,
        "overall_uplift_pct": 7.5,
    }
    bare = evaluate_promotion(metadata)
    assert bare.decision.value == "review"
    enriched = merge_into_candidate_metadata(
        metadata, [entry["certificate"] for entry in env_field["entries"]]
    )
    gated = evaluate_promotion(enriched)
    assert gated.decision.value == "promote"
    assert gated.formal_fields_present
