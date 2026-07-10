"""Mirror tests for lupine_distill.odf.field_certificates.

Every predicate in field_certificates mirrors a Lean declaration in
lean-spec/. These tests pin the mirrored semantics on the SAME witness values
the Lean modules lock (`uniform_node_admitted`, `mixed_metal_node_refused`,
`scaledAnchorsValid_example`, `cathode_inversion_witness`), and verify that
every theorem reference the module can emit resolves to a real declaration in
the Lean sources — so a Lean rename breaks CI here instead of silently
shipping dangling provenance.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lupine_distill.odf.field_certificates import (
    THEOREM_REFS,
    check_anchor_admissibility,
    check_field_domain,
    check_ranking_pair,
    merge_into_candidate_metadata,
    theorem_refs,
)
from lupine_distill.odf.promotion_gate import evaluate_promotion

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEAN_MATERIALS = _REPO_ROOT / "lean-spec" / "OpenDistillationFactory" / "Materials"

pytestmark = pytest.mark.unit


# ── Domain gate: mirrors FieldDomain.admits ────────────────────────────────


def test_uniform_node_admitted_mirror():
    """Same witness as Lean `uniform_node_admitted`: [8]*6 in [4, 12]."""
    cert = check_field_domain([8, 8, 8, 8, 8, 8], cmin=4, cmax=12)
    assert cert.admitted
    assert cert.witnesses == ()
    assert cert.theorem_ref == THEOREM_REFS["domain_soundness"]


def test_mixed_metal_node_refused_mirror():
    """Same witness as Lean `mixed_metal_node_refused`: [8, 8, 3, 8]."""
    cert = check_field_domain([8, 8, 3, 8], cmin=4, cmax=12)
    assert not cert.admitted
    assert cert.witnesses == ((2, 3),)
    assert cert.theorem_ref == THEOREM_REFS["domain_refusal_witness"]
    assert "atom 2 (c=3)" in cert.reason


def test_empty_config_vacuously_admitted():
    """List.all [] = true — the Lean gate admits the empty configuration."""
    assert check_field_domain([]).admitted


def test_domain_upper_violation_witnessed():
    cert = check_field_domain([12, 13], cmin=4, cmax=12)
    assert not cert.admitted
    assert cert.witnesses == ((1, 13),)


# ── Anchor admissibility: mirrors scaledAnchorsValid ───────────────────────


def test_admissible_anchors_mirror():
    """Same triple as Lean `scaledAnchorsValid_example` (positive half)."""
    cert = check_anchor_admissibility(-980, -673, -136)
    assert cert.tier == "error_field"
    assert cert.violations == ()
    assert cert.theorem_ref == THEOREM_REFS["anchored_field"]


def test_inadmissible_anchors_mirror():
    """Same triple as Lean `scaledAnchorsValid_example` (negative half)."""
    cert = check_anchor_admissibility(-673, -980, -136)
    assert cert.tier == "measured_field"
    assert any("(mono)" in v for v in cert.violations)
    assert cert.theorem_ref == THEOREM_REFS["measured_field"]


def test_stiffening_cell_collects_all_violations():
    cert = check_anchor_admissibility(100, 50, 20)
    assert cert.tier == "measured_field"
    assert len(cert.violations) == 3


def test_boundary_zero_vacancy_anchor_is_admissible():
    """p11 = 0 satisfies p11 <= 0 — softening is non-strict, as in Lean."""
    cert = check_anchor_admissibility(-10, -5, 0)
    assert cert.tier == "error_field"


# ── bcc anchor admissibility: mirrors scaledAnchorsBccValid ────────────────


def test_admissible_bcc_anchors_mirror():
    """Same triple as Lean `scaledAnchorsBccValid_example` (positive half):
    the chgnet/Fe bcc cell."""
    cert = check_anchor_admissibility(-4852, -4596, -1697, structure="bcc")
    assert cert.tier == "error_field"
    assert cert.structure == "bcc"
    assert cert.coordinations == (4, 6, 7)
    assert cert.violations == ()
    assert cert.theorem_ref == THEOREM_REFS["anchored_field_bcc"]


def test_inadmissible_bcc_anchors_mirror():
    """Same triple as Lean `scaledAnchorsBccValid_example` (negative half)."""
    cert = check_anchor_admissibility(-4596, -4852, -1697, structure="bcc")
    assert cert.tier == "measured_field"
    assert cert.theorem_ref == THEOREM_REFS["measured_field_bcc"]
    assert any("P(4)" in v and "P(6)" in v for v in cert.violations)
    assert "scaledAnchorsBccValid" in cert.reason


def test_bcc_stiffening_cell_witnesses_bcc_coordinations():
    """Same triple as the Lean `field_refused_mace_mp_small_V` refusal."""
    cert = check_anchor_admissibility(5401, 3072, 404, structure="bcc")
    assert len(cert.violations) == 3
    assert any("P(7) = 404e-4 > 0 (softening)" in v for v in cert.violations)


def test_unknown_structure_is_rejected():
    with pytest.raises(ValueError, match="unknown anchor structure"):
        check_anchor_admissibility(-3, -2, -1, structure="hcp")


# ── Ranking pairs: mirrors ReconcilesPair / inversion_defeats_monotone ─────


def test_cathode_inversion_witness_mirror():
    """Same values as Lean `cathode_inversion_witness`:
    reference (0.30, 0.45), softened model (0.28, 0.25)."""
    cert = check_ranking_pair(0.30, 0.45, 0.28, 0.25)
    assert cert.inverted
    assert not cert.monotone_rescuable
    assert cert.theorem_ref == THEOREM_REFS["inversion_impossibility"]


def test_consistent_ranking_is_rescuable():
    cert = check_ranking_pair(0.30, 0.45, 0.10, 0.20)
    assert not cert.inverted
    assert cert.monotone_rescuable
    assert cert.theorem_ref == THEOREM_REFS["ranking_recovery"]


def test_reverse_direction_inversion_detected():
    cert = check_ranking_pair(0.45, 0.30, 0.25, 0.28)
    assert cert.inverted


def test_tied_model_values_on_strict_reference_are_inverted():
    """m2 <= m1 includes ties: a monotone g cannot produce strict order."""
    cert = check_ranking_pair(0.30, 0.45, 0.27, 0.27)
    assert cert.inverted


# ── Metadata enrichment: integration with the promotion gate ───────────────


def _sample_certificates():
    return [
        check_field_domain([8, 8, 3, 8]),
        check_anchor_admissibility(-980, -673, -136),
        check_ranking_pair(0.30, 0.45, 0.28, 0.25),
    ]


def test_theorem_refs_deduplicate_and_preserve_order():
    certs = _sample_certificates() + _sample_certificates()
    refs = theorem_refs(certs)
    assert len(refs) == len(set(refs)) == 3


def test_merge_enriches_without_mutation():
    metadata = {
        "model_id": "chgnet-distill-v3",
        "distill_version": 3,
        "overall_uplift_pct": 7.5,
    }
    certs = _sample_certificates()
    enriched = merge_into_candidate_metadata(metadata, certs)
    assert "atlas_theorem_refs" not in metadata  # input untouched
    assert set(theorem_refs(certs)).issubset(set(enriched["atlas_theorem_refs"]))
    assert len(enriched["formal_properties"]) == 3


def test_certificates_flow_through_promotion_gate():
    """Certificates satisfy the gate's formal-field requirement, and their
    witnesses ride the reasons/telemetry path."""
    metadata = {
        "model_id": "chgnet-distill-v3",
        "distill_version": 3,
        "overall_uplift_pct": 7.5,
    }
    bare = evaluate_promotion(metadata)
    assert bare.decision.value == "review"  # promotable uplift, missing formal spec

    enriched = merge_into_candidate_metadata(metadata, _sample_certificates())
    gated = evaluate_promotion(enriched)
    assert gated.decision.value == "promote"
    assert gated.formal_fields_present


def test_refusal_witness_lands_in_formal_properties():
    enriched = merge_into_candidate_metadata(
        {"model_id": "m", "distill_version": 0},
        [check_field_domain([8, 8, 3, 8])],
    )
    assert any("atom 2 (c=3)" in p for p in enriched["formal_properties"])


# ── Mirror integrity: every reference resolves to a Lean declaration ───────


def test_every_theorem_ref_resolves_in_lean_sources():
    lean_text = "\n".join(
        p.read_text(encoding="utf-8") for p in _LEAN_MATERIALS.rglob("*.lean")
    )
    for key, ref in THEOREM_REFS.items():
        short = ref.rsplit(".", 1)[-1]
        pattern = rf"(theorem|def|structure)\s+(FieldDomain\.)?{re.escape(short)}\b"
        assert re.search(pattern, lean_text), (
            f"THEOREM_REFS[{key!r}] = {ref!r}: no declaration named {short!r} "
            "found in lean-spec Materials sources — Lean rename without "
            "updating the Python mirror?"
        )
