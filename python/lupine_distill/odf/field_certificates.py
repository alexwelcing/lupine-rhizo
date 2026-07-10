"""Lean-certificate surface for the environment-error-field layer.

Translates the runtime questions the ODF pipeline asks — "is this
configuration inside the measured field's domain?", "are this cell's anchors
admissible for the directional softening laws?", "can this pair's ranking be
rescued downstream?" — into structured certificates that name the exact
``lean-spec`` theorem backing each answer, so promotion decisions and runner
telemetry carry machine-checkable provenance instead of prose.

Mirror contract: every predicate here MUST match its Lean counterpart
symbol-for-symbol:

- :func:`check_field_domain`        mirrors ``SorptionStability.FieldDomain.admits``
  (soundness/witness: ``admits_iff`` / ``refusal_has_witness``);
- :func:`check_anchor_admissibility` mirrors ``AnchoredField.scaledAnchorsValid``
  (tier-2 constructor: ``mkAnchoredField``; tier-1 fallback: ``mkMeasuredField``);
- :func:`check_ranking_pair`        mirrors ``RankingIntegrity.ReconcilesPair``
  (impossibility: ``inversion_defeats_monotone``; recovery:
  ``measured_corrected_recovers_reference_order``).

``python/tests/test_field_certificates.py`` pins the mirrored semantics on the
same witness values the Lean modules lock (`uniform_node_admitted`,
`mixed_metal_node_refused`, `scaledAnchorsValid_example`,
`cathode_inversion_witness`) and checks every theorem reference resolves to a
declaration in the Lean sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

_THEORY = "OpenDistillationFactory.Materials.Theory"

#: Fully-qualified Lean names for every certificate this module can issue.
THEOREM_REFS: dict[str, str] = {
    "domain_soundness": f"{_THEORY}.SorptionStability.FieldDomain.admits_iff",
    "domain_refusal_witness": (
        f"{_THEORY}.SorptionStability.FieldDomain.refusal_has_witness"
    ),
    "anchored_field": f"{_THEORY}.AnchoredField.mkAnchoredField",
    "measured_field": f"{_THEORY}.AnchoredField.mkMeasuredField",
    "anchor_admissibility": f"{_THEORY}.AnchoredField.scaledAnchorsValid",
    "barrier_underestimated": (
        f"{_THEORY}.BarrierArrhenius.softened_barrier_underestimates"
    ),
    "inversion_impossibility": (
        f"{_THEORY}.RankingIntegrity.inversion_defeats_monotone"
    ),
    "ranking_recovery": (
        f"{_THEORY}.RankingIntegrity.measured_corrected_recovers_reference_order"
    ),
}

# Default measured first-shell domain for the fcc anchors (inclusive), matching
# the FieldDomain witnesses locked in Theory/SorptionStability.lean.
DEFAULT_CMIN = 4
DEFAULT_CMAX = 12


@dataclass(frozen=True)
class DomainCertificate:
    """Outcome of the first-shell domain gate on one configuration."""

    admitted: bool
    cmin: int
    cmax: int
    #: (atom index, coordination) for every out-of-domain atom (refusals only).
    witnesses: tuple[tuple[int, int], ...]
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "field_domain",
            "admitted": self.admitted,
            "cmin": self.cmin,
            "cmax": self.cmax,
            "witnesses": [list(w) for w in self.witnesses],
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_field_domain(
    coordinations: Sequence[int],
    cmin: int = DEFAULT_CMIN,
    cmax: int = DEFAULT_CMAX,
) -> DomainCertificate:
    """Mirror of ``FieldDomain.admits``: admit iff every coordination is inside
    ``[cmin, cmax]``; refusals carry the concrete witness atoms
    (``refusal_has_witness`` guarantees one exists)."""
    witnesses = tuple(
        (i, c) for i, c in enumerate(coordinations) if not (cmin <= c <= cmax)
    )
    admitted = not witnesses
    if admitted:
        reason = (
            f"all {len(coordinations)} coordination(s) inside the measured "
            f"first-shell domain [{cmin}, {cmax}]"
        )
        ref = THEOREM_REFS["domain_soundness"]
    else:
        listed = ", ".join(f"atom {i} (c={c})" for i, c in witnesses)
        reason = (
            f"out of measured domain [{cmin}, {cmax}]: {listed} — escalate to "
            "explicit electronic-structure treatment"
        )
        ref = THEOREM_REFS["domain_refusal_witness"]
    return DomainCertificate(
        admitted=admitted,
        cmin=cmin,
        cmax=cmax,
        witnesses=witnesses,
        theorem_ref=ref,
        reason=reason,
    )


@dataclass(frozen=True)
class AnchorCertificate:
    """Admissibility of one cell's integer-scaled anchors (x1e-4 eV/atom)."""

    #: "error_field" (tier 2: directional laws) or "measured_field" (tier 1).
    tier: str
    p8_scaled: int
    p9_scaled: int
    p11_scaled: int
    violations: tuple[str, ...]
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "anchor_admissibility",
            "tier": self.tier,
            "anchors_scaled": [self.p8_scaled, self.p9_scaled, self.p11_scaled],
            "violations": list(self.violations),
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_anchor_admissibility(
    p8_scaled: int, p9_scaled: int, p11_scaled: int
) -> AnchorCertificate:
    """Mirror of ``scaledAnchorsValid``: monotone softening
    ``p8 <= p9 <= p11 <= 0`` on the exact integer-scaled anchors. Admissible
    cells construct the tier-2 ``ErrorField`` (``mkAnchoredField``); violating
    cells fall back to the tier-1 ``MeasuredField`` (correction and ranking
    laws only) with a kernel-checked refusal certificate."""
    violations: list[str] = []
    if not p8_scaled <= p9_scaled:
        violations.append(f"P(8) = {p8_scaled}e-4 > P(9) = {p9_scaled}e-4 (mono)")
    if not p9_scaled <= p11_scaled:
        violations.append(f"P(9) = {p9_scaled}e-4 > P(11) = {p11_scaled}e-4 (mono)")
    if not p11_scaled <= 0:
        violations.append(f"P(11) = {p11_scaled}e-4 > 0 (softening)")
    if violations:
        tier = "measured_field"
        ref = THEOREM_REFS["measured_field"]
        reason = (
            "tier-2 refusal (¬ scaledAnchorsValid): "
            + "; ".join(violations)
            + " — correction/ranking laws remain valid at the measured tier; "
            "directional softening laws do not apply"
        )
    else:
        tier = "error_field"
        ref = THEOREM_REFS["anchored_field"]
        reason = (
            "monotone softening holds on the measured anchors — directional "
            "laws (barrier underestimation, mobility overestimation) apply"
        )
    return AnchorCertificate(
        tier=tier,
        p8_scaled=p8_scaled,
        p9_scaled=p9_scaled,
        p11_scaled=p11_scaled,
        violations=tuple(violations),
        theorem_ref=ref,
        reason=reason,
    )


@dataclass(frozen=True)
class RankingCertificate:
    """Reconcilability of a two-candidate ranking (model vs reference)."""

    inverted: bool
    #: False exactly when inverted: no monotone recalibration can rescue it.
    monotone_rescuable: bool
    ref_pair: tuple[float, float]
    model_pair: tuple[float, float]
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "ranking_pair",
            "inverted": self.inverted,
            "monotone_rescuable": self.monotone_rescuable,
            "ref_pair": list(self.ref_pair),
            "model_pair": list(self.model_pair),
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_ranking_pair(
    ref_1: float, ref_2: float, model_1: float, model_2: float
) -> RankingCertificate:
    """Mirror of the ``ReconcilesPair`` analysis: the pair is *inverted* when
    the reference strictly orders candidate 1 below candidate 2 but the model
    orders them the other way (or vice versa). By
    ``inversion_defeats_monotone`` an inverted pair cannot be repaired by any
    monotone recalibration of model outputs — it must be corrected inside the
    model (the environment field) or escalated."""
    inverted = (ref_1 < ref_2 and model_2 <= model_1) or (
        ref_2 < ref_1 and model_1 <= model_2
    )
    if inverted:
        reason = (
            f"ranking inversion: reference orders ({ref_1}, {ref_2}) but model "
            f"reports ({model_1}, {model_2}) — no monotone recalibration can "
            "reconcile them (machine-checked impossibility); correct at the "
            "energy level or escalate"
        )
        ref = THEOREM_REFS["inversion_impossibility"]
    else:
        reason = (
            "model ordering consistent with reference ordering — corrected "
            "screening recovers the reference ranking for field-decomposable "
            "errors"
        )
        ref = THEOREM_REFS["ranking_recovery"]
    return RankingCertificate(
        inverted=inverted,
        monotone_rescuable=not inverted,
        ref_pair=(ref_1, ref_2),
        model_pair=(model_1, model_2),
        theorem_ref=ref,
        reason=reason,
    )


Certificate = DomainCertificate | AnchorCertificate | RankingCertificate


def theorem_refs(certificates: Iterable[Certificate]) -> list[str]:
    """Deduplicated, order-preserving theorem references of a certificate set."""
    seen: dict[str, None] = {}
    for cert in certificates:
        seen.setdefault(cert.theorem_ref, None)
    return list(seen)


def merge_into_candidate_metadata(
    metadata: Mapping[str, Any], certificates: Sequence[Certificate]
) -> dict[str, Any]:
    """Enrich promotion-candidate metadata with certificate provenance.

    Appends each certificate's Lean theorem reference to
    ``atlas_theorem_refs`` and its structured outcome to
    ``formal_properties`` (both deduplicated, order preserved), so
    :func:`lupine_distill.odf.promotion_gate.evaluate_promotion` sees the
    formal contract and the gate's telemetry carries the witnesses. The input
    mapping is not mutated."""
    enriched = dict(metadata)
    refs = list(enriched.get("atlas_theorem_refs", []) or [])
    props = list(enriched.get("formal_properties", []) or [])
    for cert in certificates:
        if cert.theorem_ref not in refs:
            refs.append(cert.theorem_ref)
        stamp = f"{cert.to_dict()['kind']}: {cert.reason}"
        if stamp not in props:
            props.append(stamp)
    enriched["atlas_theorem_refs"] = refs
    enriched["formal_properties"] = props
    return enriched


__all__ = [
    "THEOREM_REFS",
    "DEFAULT_CMIN",
    "DEFAULT_CMAX",
    "DomainCertificate",
    "AnchorCertificate",
    "RankingCertificate",
    "Certificate",
    "check_field_domain",
    "check_anchor_admissibility",
    "check_ranking_pair",
    "theorem_refs",
    "merge_into_candidate_metadata",
]
