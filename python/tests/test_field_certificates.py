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
    GAP_COORDINATIONS,
    THEOREM_REFS,
    check_anchor_admissibility,
    check_bracket_separation,
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


# ── diamond anchor admissibility: mirrors scaledAnchorDiamondValid ─────────


def test_admissible_diamond_anchor_mirror():
    """Same value as Lean `scaledAnchorDiamondValid_example` (positive half):
    the chgnet/Si cell."""
    cert = check_anchor_admissibility(-6906, structure="diamond")
    assert cert.tier == "error_field"
    assert cert.coordinations == (3,)
    assert cert.theorem_ref == THEOREM_REFS["anchored_field_diamond"]


def test_stiffening_diamond_anchor_refused():
    """Same value as Lean `scaledAnchorDiamondValid_example` (negative half)."""
    cert = check_anchor_admissibility(6906, structure="diamond")
    assert cert.tier == "measured_field"
    assert cert.violations == ("P(3) = 6906e-4 > 0 (softening)",)
    assert "scaledAnchorDiamondValid" in cert.reason


def test_anchor_arity_must_match_layout():
    with pytest.raises(ValueError, match="anchor"):
        check_anchor_admissibility(-3, -2, structure="fcc")
    with pytest.raises(ValueError, match="anchor"):
        check_anchor_admissibility(-3, -2, structure="diamond")


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


# ── Identification payload: mirrors Theory/AnchorBracket.lean ──────────────


def test_fcc_gap_and_width_mirror_chgnet_ni():
    """Same anchors as Lean `chgnet_Ni_gap_certificate` /
    `chgnet_Ni_bracket_width`: gap coordination c = 10, certified per-atom
    width p11 − p9 = 537e-4 eV/atom."""
    cert = check_anchor_admissibility(-980, -673, -136)
    assert cert.gap_coordination == GAP_COORDINATIONS["fcc"] == 10
    assert cert.bracket_width_scaled == 537
    assert cert.identification_ref == THEOREM_REFS["anchor_identification"]
    assert "537e-4" in cert.reason


def test_bcc_gap_and_width_mirror_chgnet_fe():
    """Same anchors as Lean `chgnet_Fe_gap_certificate` /
    `chgnet_Fe_bracket_width`: gap coordination c = 5, width p6 − p4 =
    256e-4 eV/atom."""
    cert = check_anchor_admissibility(-4852, -4596, -1697, structure="bcc")
    assert cert.gap_coordination == 5
    assert cert.bracket_width_scaled == 256
    assert cert.identification_ref == THEOREM_REFS["anchor_identification_bcc"]


def test_diamond_zero_width_mirror():
    """The diamond layout has no unanchored in-range coordination — Lean
    `corrected_exact_diamond`: in-range corrections are exact."""
    cert = check_anchor_admissibility(-6906, structure="diamond")
    assert cert.gap_coordination is None
    assert cert.bracket_width_scaled == 0
    assert "exact" in cert.reason


def test_refused_cell_has_no_bracket_but_carries_impossibility():
    """Same anchors as Lean `no_interpolant_mace_mpa_0_medium_Ni`: a refused
    cell brackets nothing (no consistent field exists), and its
    identification_ref names the existence iff that proves impossibility."""
    cert = check_anchor_admissibility(4190, 2296, 125)
    assert cert.tier == "measured_field"
    assert cert.bracket_width_scaled is None
    assert cert.identification_ref == THEOREM_REFS["anchor_identification"]
    assert "identification impossibility" in cert.reason


# ── Bracket separation: mirrors certified_order_of_separation_fcc/_bcc ─────


def test_separation_certifies_strict_margin():
    """corrected_a < corrected_b − count·width ⇒ certified for every
    consistent field (fcc rule)."""
    cert = check_bracket_separation(
        corrected_a=-1.00,
        corrected_b=-0.50,
        gap_count_b=4,
        bracket_width_scaled=537,
    )
    assert cert.certified
    assert cert.theorem_ref == THEOREM_REFS["bracket_separation"]
    assert cert.margin == pytest.approx(0.5 - 4 * 537e-4)


def test_separation_zero_margin_not_certified():
    """Strictness mirror: the Lean rule is a strict `<`; a pair sitting
    exactly at the budget boundary is NOT certified."""
    cert = check_bracket_separation(
        corrected_a=0.0,
        corrected_b=4 * 537e-4,
        gap_count_b=4,
        bracket_width_scaled=537,
    )
    assert not cert.certified
    assert "budget" in cert.reason


def test_separation_overlap_not_certified():
    cert = check_bracket_separation(
        corrected_a=-0.52,
        corrected_b=-0.50,
        gap_count_b=1,
        bracket_width_scaled=537,
    )
    assert not cert.certified


def test_separation_bcc_uses_bcc_theorem():
    cert = check_bracket_separation(
        corrected_a=-2.0,
        corrected_b=-1.0,
        gap_count_b=2,
        bracket_width_scaled=256,
        structure="bcc",
    )
    assert cert.certified
    assert cert.theorem_ref == THEOREM_REFS["bracket_separation_bcc"]


def test_separation_diamond_degenerates_to_exact_comparison():
    """Zero width: any strictly ordered corrected pair is certified, backed
    by the diamond exactness law."""
    cert = check_bracket_separation(
        corrected_a=-1.0001,
        corrected_b=-1.0,
        gap_count_b=7,
        bracket_width_scaled=0,
        structure="diamond",
    )
    assert cert.certified
    assert cert.theorem_ref == THEOREM_REFS["corrected_exact_diamond"]


def test_separation_rejects_negative_count():
    with pytest.raises(ValueError, match="nonnegative"):
        check_bracket_separation(0.0, 1.0, -1, 537)


def test_separation_certificate_serializes():
    payload = check_bracket_separation(-1.0, -0.5, 4, 537).to_dict()
    assert payload["kind"] == "bracket_separation"
    assert payload["certified"] is True
    assert payload["gap_count_b"] == 4


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
