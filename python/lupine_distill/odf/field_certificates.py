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
  (fcc; tier-2 constructor: ``mkAnchoredField``; tier-1 fallback:
  ``mkMeasuredField``) and ``AnchoredField.scaledAnchorsBccValid`` (bcc;
  ``mkAnchoredFieldBcc`` / ``mkMeasuredFieldBcc``), selected by its
  ``structure`` argument;
- :func:`check_ranking_pair`        mirrors ``RankingIntegrity.ReconcilesPair``
  (impossibility: ``inversion_defeats_monotone``; recovery:
  ``measured_corrected_recovers_reference_order``);
- the identification payload of :class:`AnchorCertificate`
  (``gap_coordination`` / ``bracket_width_scaled`` / ``identification_ref``)
  mirrors ``AnchorBracket.interpolant_gap_mem`` /
  ``AnchorBracket.corrected_bracket_fcc`` (bcc mirror
  ``corrected_bracket_bcc``; diamond exactness ``corrected_exact_diamond``)
  and the existence/impossibility iffs
  ``AnchorBracket.exists_interpolant_iff_fcc`` / ``…_bcc`` / ``…_diamond``:
  an admissible cell's correction uncertainty is one scalar per atom at the
  unanchored coordination, bounded by the anchor gap; a refused cell admits
  *no* consistent softening field at all;
- :func:`check_bracket_separation` mirrors
  ``AnchorBracket.certified_order_of_separation_fcc`` (bcc mirror
  ``certified_order_of_separation_bcc``; diamond degenerate case
  ``corrected_exact_diamond``): interval separation certifies the corrected
  order against every field consistent with the anchors.

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
    "anchored_field_bcc": f"{_THEORY}.AnchoredField.mkAnchoredFieldBcc",
    "measured_field_bcc": f"{_THEORY}.AnchoredField.mkMeasuredFieldBcc",
    "anchor_admissibility_bcc": f"{_THEORY}.AnchoredField.scaledAnchorsBccValid",
    "anchored_field_diamond": f"{_THEORY}.AnchoredField.mkAnchoredFieldDiamond",
    "measured_field_diamond": f"{_THEORY}.AnchoredField.mkMeasuredFieldDiamond",
    "anchor_admissibility_diamond": (
        f"{_THEORY}.AnchoredField.scaledAnchorDiamondValid"
    ),
    "barrier_underestimated": (
        f"{_THEORY}.BarrierArrhenius.softened_barrier_underestimates"
    ),
    "inversion_impossibility": (
        f"{_THEORY}.RankingIntegrity.inversion_defeats_monotone"
    ),
    "ranking_recovery": (
        f"{_THEORY}.RankingIntegrity.measured_corrected_recovers_reference_order"
    ),
    "anchor_identification": f"{_THEORY}.AnchorBracket.exists_interpolant_iff_fcc",
    "anchor_identification_bcc": (
        f"{_THEORY}.AnchorBracket.exists_interpolant_iff_bcc"
    ),
    "anchor_identification_diamond": (
        f"{_THEORY}.AnchorBracket.exists_interpolant_iff_diamond"
    ),
    "corrected_bracket": f"{_THEORY}.AnchorBracket.corrected_bracket_fcc",
    "corrected_bracket_bcc": f"{_THEORY}.AnchorBracket.corrected_bracket_bcc",
    "corrected_exact_diamond": f"{_THEORY}.AnchorBracket.corrected_exact_diamond",
    "bracket_separation": (
        f"{_THEORY}.AnchorBracket.certified_order_of_separation_fcc"
    ),
    "bracket_separation_bcc": (
        f"{_THEORY}.AnchorBracket.certified_order_of_separation_bcc"
    ),
}

# Default measured first-shell domain for the fcc anchors (inclusive), matching
# the FieldDomain witnesses locked in Theory/SorptionStability.lean.
DEFAULT_CMIN = 4
DEFAULT_CMAX = 12

#: First-shell coordinations probed by the anchors of each supported
#: crystal-structure layout (mirrors the `stepField` / `stepFieldBcc` /
#: `stepFieldDiamond` layouts).
ANCHOR_COORDINATIONS: dict[str, tuple[int, ...]] = {
    "fcc": (8, 9, 11),
    "bcc": (4, 6, 7),
    "diamond": (3,),
}

#: (tier-2 constructor, tier-1 fallback, admissibility predicate) theorem-ref
#: keys per structure.
_ANCHOR_REF_KEYS: dict[str, tuple[str, str, str]] = {
    "fcc": ("anchored_field", "measured_field", "anchor_admissibility"),
    "bcc": ("anchored_field_bcc", "measured_field_bcc", "anchor_admissibility_bcc"),
    "diamond": (
        "anchored_field_diamond",
        "measured_field_diamond",
        "anchor_admissibility_diamond",
    ),
}

#: The single unanchored in-range coordination of each layout (`None` when the
#: anchors and the bulk pin leave no gap) — mirrors the one-scalar reduction
#: of ``Theory/AnchorBracket.lean``: all in-range correction ambiguity lives
#: at this coordination (fcc c = 10, bcc c = 5, diamond none).
GAP_COORDINATIONS: dict[str, int | None] = {
    "fcc": 10,
    "bcc": 5,
    "diamond": None,
}

#: (identification iff, bracket law, separation law) theorem-ref keys per
#: structure. For the diamond layout, whose gap budget is zero, both the
#: bracket and separation laws degenerate to exact correction.
_BRACKET_REF_KEYS: dict[str, tuple[str, str, str]] = {
    "fcc": ("anchor_identification", "corrected_bracket", "bracket_separation"),
    "bcc": (
        "anchor_identification_bcc",
        "corrected_bracket_bcc",
        "bracket_separation_bcc",
    ),
    "diamond": (
        "anchor_identification_diamond",
        "corrected_exact_diamond",
        "corrected_exact_diamond",
    ),
}


def _bracket_width_scaled(structure: str, anchors_scaled: Sequence[int]) -> int:
    """Certified per-atom bracket width (x1e-4 eV/atom) of an admissible cell:
    the anchor gap bounding the correction ambiguity at the unanchored
    coordination — fcc: ``p11 − p9``; bcc: ``p6 − p4``; diamond: ``0`` (fully
    identified). Mirrors the width term of ``corrected_bracket_fcc`` /
    ``corrected_bracket_bcc`` / ``corrected_exact_diamond``."""
    if structure == "fcc":
        return anchors_scaled[2] - anchors_scaled[1]
    if structure == "bcc":
        return anchors_scaled[1] - anchors_scaled[0]
    return 0


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
    #: Crystal-structure layout the anchors were measured on
    #: ("fcc" | "bcc" | "diamond").
    structure: str
    #: First-shell coordinations the anchors probe (fcc: 8/9/11; bcc: 4/6/7;
    #: diamond: 3).
    coordinations: tuple[int, ...]
    anchors_scaled: tuple[int, ...]
    violations: tuple[str, ...]
    theorem_ref: str
    reason: str
    #: The single unanchored in-range coordination whose field value the
    #: anchors do not pin (fcc: 10; bcc: 5; diamond: None) — the one scalar
    #: of ``AnchorBracket``'s reduction identity.
    gap_coordination: int | None = None
    #: Certified per-atom bracket width (x1e-4 eV/atom) for admissible cells:
    #: the exact bound on correction overshoot per gap-coordination atom
    #: (``corrected_bracket_fcc`` / ``…_bcc``; 0 for diamond = exact).
    #: ``None`` for refused cells — no consistent field exists to bracket.
    bracket_width_scaled: int | None = None
    #: Existence/impossibility law backing this cell's identification status
    #: (``exists_interpolant_iff_fcc`` / ``…_bcc`` / ``…_diamond``): for
    #: admissible anchors a softening field exists; for refused anchors NO
    #: softening field is consistent — the refusal is scheme-independent.
    identification_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "anchor_admissibility",
            "tier": self.tier,
            "structure": self.structure,
            "coordinations": list(self.coordinations),
            "anchors_scaled": list(self.anchors_scaled),
            "violations": list(self.violations),
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
            "gap_coordination": self.gap_coordination,
            "bracket_width_scaled": self.bracket_width_scaled,
            "identification_ref": self.identification_ref,
        }


def check_anchor_admissibility(
    *anchors_scaled: int,
    structure: str = "fcc",
) -> AnchorCertificate:
    """Mirror of ``scaledAnchorsValid`` (fcc) / ``scaledAnchorsBccValid``
    (bcc) / ``scaledAnchorDiamondValid`` (diamond): monotone softening
    ``p_1 <= p_2 <= ... <= p_n <= 0`` on the exact integer-scaled anchors,
    ordered by the coordination they probe (fcc: P(8)/P(9)/P(11); bcc:
    P(4)/P(6)/P(7); diamond: P(3)). Admissible cells construct the tier-2
    ``ErrorField`` via the layout constructor; violating cells fall back to
    the tier-1 ``MeasuredField`` (correction and ranking laws only) with a
    kernel-checked refusal certificate."""
    try:
        coordinations = ANCHOR_COORDINATIONS[structure]
        anchored_key, measured_key, predicate_key = _ANCHOR_REF_KEYS[structure]
    except KeyError:
        raise ValueError(
            f"unknown anchor structure {structure!r}; "
            f"expected one of {sorted(ANCHOR_COORDINATIONS)}"
        ) from None
    if len(anchors_scaled) != len(coordinations):
        raise ValueError(
            f"{structure} layout has {len(coordinations)} anchor(s) at "
            f"coordinations {coordinations}; got {len(anchors_scaled)} value(s)"
        )
    predicate = THEOREM_REFS[predicate_key].rsplit(".", 1)[-1]
    identification_key, _bracket_key, _separation_key = _BRACKET_REF_KEYS[structure]
    gap_coordination = GAP_COORDINATIONS[structure]
    violations: list[str] = []
    for (c_lo, p_lo), (c_hi, p_hi) in zip(
        zip(coordinations, anchors_scaled), zip(coordinations[1:], anchors_scaled[1:])
    ):
        if not p_lo <= p_hi:
            violations.append(f"P({c_lo}) = {p_lo}e-4 > P({c_hi}) = {p_hi}e-4 (mono)")
    if not anchors_scaled[-1] <= 0:
        violations.append(
            f"P({coordinations[-1]}) = {anchors_scaled[-1]}e-4 > 0 (softening)"
        )
    if violations:
        tier = "measured_field"
        ref = THEOREM_REFS[measured_key]
        bracket_width = None
        reason = (
            f"tier-2 refusal (¬ {predicate}): "
            + "; ".join(violations)
            + " — correction/ranking laws remain valid at the measured tier; "
            "directional softening laws do not apply; no softening field is "
            "consistent with these anchors (identification impossibility)"
        )
    else:
        tier = "error_field"
        ref = THEOREM_REFS[anchored_key]
        bracket_width = _bracket_width_scaled(structure, anchors_scaled)
        if gap_coordination is None:
            width_note = (
                "no unanchored in-range coordination — in-range corrections "
                "are certified exact"
            )
        else:
            width_note = (
                f"certified per-atom bracket width {bracket_width}e-4 eV/atom "
                f"at the unanchored coordination c = {gap_coordination}"
            )
        reason = (
            "monotone softening holds on the measured anchors — directional "
            "laws (barrier underestimation, mobility overestimation) apply; "
            + width_note
        )
    return AnchorCertificate(
        tier=tier,
        structure=structure,
        coordinations=tuple(coordinations),
        anchors_scaled=tuple(anchors_scaled),
        violations=tuple(violations),
        theorem_ref=ref,
        reason=reason,
        gap_coordination=gap_coordination,
        bracket_width_scaled=bracket_width,
        identification_ref=THEOREM_REFS[identification_key],
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


@dataclass(frozen=True)
class BracketSeparationCertificate:
    """Margin-certified corrected ranking of one candidate pair in one cell.

    Mirrors ``AnchorBracket.certified_order_of_separation_fcc`` (bcc mirror
    ``certified_order_of_separation_bcc``; diamond degenerate case
    ``corrected_exact_diamond``): candidate A ranks strictly below candidate
    B against **every** softening field consistent with the cell's anchors
    when A's corrected energy sits strictly below B's corrected energy minus
    B's gap budget (B's count of gap-coordination atoms times the certified
    per-atom bracket width). ``certified = False`` does not mean the order
    is wrong — only that the measured anchors cannot exclude a flip.
    """

    certified: bool
    corrected_a: float
    corrected_b: float
    #: Number of gap-coordination atoms in candidate B's configuration (the
    #: budget side of the separation rule). Candidate A needs no budget: its
    #: corrected value is already its certified upper bound.
    gap_count_b: int
    #: Certified per-atom bracket width, x1e-4 eV/atom (0 for diamond).
    bracket_width_scaled: int
    structure: str
    #: Certified slack in eV: ``corrected_b − budget − corrected_a``;
    #: certification holds iff this is strictly positive.
    margin: float
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "bracket_separation",
            "certified": self.certified,
            "corrected_a": self.corrected_a,
            "corrected_b": self.corrected_b,
            "gap_count_b": self.gap_count_b,
            "bracket_width_scaled": self.bracket_width_scaled,
            "structure": self.structure,
            "margin": self.margin,
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_bracket_separation(
    corrected_a: float,
    corrected_b: float,
    gap_count_b: int,
    bracket_width_scaled: int,
    structure: str = "fcc",
    scale: int = 10000,
) -> BracketSeparationCertificate:
    """Mirror of ``certified_order_of_separation_fcc`` / ``…_bcc``: certify
    ``corrected_a < corrected_b − gap_count_b · width`` (width in eV =
    ``bracket_width_scaled / scale``), which by the Lean theorem forces
    A's reference energy strictly below B's for every field consistent with
    the anchors. Inputs are the *step-field corrected* energies of the two
    candidates in the SAME (model, material) cell, and ``gap_count_b`` is
    candidate B's population of the layout's unanchored coordination
    (``GAP_COORDINATIONS``); for the diamond layout the width is zero and
    the rule degenerates to the exact-correction comparison
    (``corrected_exact_diamond``). Strictness matters: a zero margin is NOT
    certified, exactly as in Lean.

    Two honesty caveats. (1) The Lean theorem governs the coordination-
    resolved *step-field* correction; the runtime policy engine's live
    correction is a uniform additive bias per (row, mlip) — do NOT feed
    engine-bias-corrected energies here and read the result as certified.
    (2) This mirror compares floats; the Lean statement compares exact
    rationals, so margins within float rounding (~1e-12 of the boundary)
    are not trustworthy — treat hairline certifications as ambiguous."""
    if structure not in _BRACKET_REF_KEYS:
        raise ValueError(
            f"unknown anchor structure {structure!r}; "
            f"expected one of {sorted(_BRACKET_REF_KEYS)}"
        )
    if gap_count_b < 0:
        raise ValueError(f"gap_count_b must be nonnegative; got {gap_count_b}")
    _identification_key, _bracket_key, separation_key = _BRACKET_REF_KEYS[structure]
    budget = gap_count_b * bracket_width_scaled / scale
    margin = corrected_b - budget - corrected_a
    certified = margin > 0
    ref = THEOREM_REFS[separation_key]
    if certified:
        reason = (
            f"corrected order certified against every consistent field: "
            f"corrected_a = {corrected_a} < {corrected_b} − "
            f"{gap_count_b}·{bracket_width_scaled}e-4 (margin {margin:.6g} eV)"
        )
    else:
        reason = (
            f"anchor-gap budget can flip this pair: corrected separation "
            f"{corrected_b - corrected_a:.6g} eV does not exceed the gap "
            f"budget {budget:.6g} eV — rank only after tightening the "
            "anchors or escalate to the oracle"
        )
    return BracketSeparationCertificate(
        certified=certified,
        corrected_a=corrected_a,
        corrected_b=corrected_b,
        gap_count_b=gap_count_b,
        bracket_width_scaled=bracket_width_scaled,
        structure=structure,
        margin=margin,
        theorem_ref=ref,
        reason=reason,
    )


Certificate = (
    DomainCertificate
    | AnchorCertificate
    | RankingCertificate
    | BracketSeparationCertificate
)


#: Runtime backend ids (the cell runner's ``load_calculator`` /
#: ``backend_catalog.json``) -> binder model ids
#: (``bind_env_field_instances.MODELS``). The runner's ``mace-mp-0`` loads
#: ``mace_mp(model="medium")`` — i.e. the binder's ``mace-mp-medium`` — so
#: certificate lookups must resolve the alias or MACE cells silently never
#: gate production predictions.
RUNTIME_MLIP_ALIASES: dict[str, str] = {
    "mace-mp-0": "mace-mp-medium",
}


def resolve_binder_model_id(mlip_id: str) -> str:
    """Binder model id for a runtime backend id (identity when unaliased)."""
    return RUNTIME_MLIP_ALIASES.get(mlip_id, mlip_id)


def certificates_from_binding_report(
    report: Mapping[str, Any],
    model_ids: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Re-check every bound cell of an env-field binding report
    (``lupine.env_field_binding_report.v2``, emitted by
    ``python/scripts/bind_env_field_instances.py``) through the Lean-mirror
    admissibility predicate.

    Returns one entry per cell — ``material``, ``model_id``, ``structure``,
    ``lean_name``, and the :class:`AnchorCertificate` — optionally filtered to
    the given model ids (runtime backend ids are resolved through
    :data:`RUNTIME_MLIP_ALIASES` before matching). Cells with unknown
    structures or malformed anchors are skipped rather than guessed at.
    Shared by the promotion packet builder (``tools/mlip_local_promotion.py``)
    and the run-time certificate gate
    (``lupine_distill_runtime.policy_engine``)."""
    wanted = (
        {resolve_binder_model_id(str(m)) for m in model_ids}
        if model_ids is not None
        else None
    )
    entries: list[dict[str, Any]] = []
    for cell in report.get("cells", []):
        if not isinstance(cell, Mapping):
            continue
        model_id = cell.get("model_id")
        if wanted is not None and model_id not in wanted:
            continue
        structure = str(cell.get("structure", "fcc"))
        expected = ANCHOR_COORDINATIONS.get(structure)
        if expected is None:
            continue
        anchors = [
            anchor.get("p_scaled")
            for anchor in cell.get("anchors", [])
            if isinstance(anchor, Mapping)
        ]
        if len(anchors) != len(expected) or not all(
            isinstance(a, int) for a in anchors
        ):
            continue
        entries.append(
            {
                "material": cell.get("material"),
                "model_id": model_id,
                "structure": structure,
                "lean_name": cell.get("lean_name"),
                "certificate": check_anchor_admissibility(
                    *anchors, structure=structure
                ),
            }
        )
    return entries


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
    "ANCHOR_COORDINATIONS",
    "GAP_COORDINATIONS",
    "DomainCertificate",
    "AnchorCertificate",
    "RankingCertificate",
    "BracketSeparationCertificate",
    "Certificate",
    "check_field_domain",
    "check_anchor_admissibility",
    "check_ranking_pair",
    "check_bracket_separation",
    "RUNTIME_MLIP_ALIASES",
    "resolve_binder_model_id",
    "certificates_from_binding_report",
    "theorem_refs",
    "merge_into_candidate_metadata",
]
