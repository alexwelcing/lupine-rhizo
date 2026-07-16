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
- :func:`check_bracket_separation` mirrors the exact two-envelope laws
  ``AnchorBracket.certified_order_iff_endpoint_margins_fcc`` (bcc mirror
  ``certified_order_iff_endpoint_margins_bcc``; diamond degenerate case
  ``corrected_exact_diamond``): interval separation certifies the corrected
  order against every field consistent with the anchors.

``python/tests/test_field_certificates.py`` pins the mirrored semantics on the
same witness values the Lean modules lock (`uniform_node_admitted`,
`mixed_metal_node_refused`, `scaledAnchorsValid_example`,
`cathode_inversion_witness`) and checks every theorem reference resolves to a
declaration in the Lean sources.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

_THEORY = "OpenDistillationFactory.Materials.Theory"
_BINDING_REPORT_SCHEMA = "lupine.env_field_binding_report.v2"
_BINDING_LEAN_MODULE = (
    "lean-spec/OpenDistillationFactory/Materials/DistillAtlas/EnvFieldInstances.lean"
)
_BINDING_NAMESPACE = (
    "OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances"
)
_BINDING_TARGET_FILES = (
    "surface_energies.json",
    "vacancy_formation.json",
    "beyond_metals.json",
)

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
        f"{_THEORY}.AnchorBracket.certified_order_iff_endpoint_margins_fcc"
    ),
    "bracket_separation_bcc": (
        f"{_THEORY}.AnchorBracket.certified_order_iff_endpoint_margins_bcc"
    ),
    "anchored_field_rocksalt": (
        f"{_THEORY}.AnchoredField.mkAnchoredFieldRocksalt"
    ),
    "measured_field_rocksalt": (
        f"{_THEORY}.AnchoredField.mkMeasuredFieldRocksalt"
    ),
    "anchor_admissibility_rocksalt": (
        f"{_THEORY}.AnchoredField.scaledAnchorRocksaltValid"
    ),
    "barrier_conservatism": (
        f"{_THEORY}.BarrierArrhenius.softening_never_hides_conductor"
    ),
    "anchor_identification_rocksalt": (
        f"{_THEORY}.AnchorBracket.exists_interpolant_iff_rocksalt"
    ),
    "corrected_exact_rocksalt": (
        f"{_THEORY}.AnchorBracket.corrected_exact_rocksalt"
    ),
}

# Default measured first-shell domain for the fcc anchors (inclusive), matching
# the FieldDomain witnesses locked in Theory/SorptionStability.lean.
DEFAULT_CMIN = 4
DEFAULT_CMAX = 12

#: First-shell coordinations probed by the anchors of each supported
#: crystal-structure layout (mirrors the `stepField` / `stepFieldBcc` /
#: `stepFieldDiamond` / `stepFieldRocksalt` layouts).
ANCHOR_COORDINATIONS: dict[str, tuple[int, ...]] = {
    "fcc": (8, 9, 11),
    "bcc": (4, 6, 7),
    "diamond": (3,),
    "rocksalt": (5,),
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
    "rocksalt": (
        "anchored_field_rocksalt",
        "measured_field_rocksalt",
        "anchor_admissibility_rocksalt",
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
    "rocksalt": None,
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
    "rocksalt": (
        "anchor_identification_rocksalt",
        "corrected_exact_rocksalt",
        "corrected_exact_rocksalt",
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
    (bcc) / ``scaledAnchorDiamondValid`` (diamond) /
    ``scaledAnchorRocksaltValid`` (rocksalt): monotone softening
    ``p_1 <= p_2 <= ... <= p_n <= 0`` on the exact integer-scaled anchors,
    ordered by the coordination they probe (fcc: P(8)/P(9)/P(11); bcc:
    P(4)/P(6)/P(7); diamond: P(3); rocksalt: P(5)). Admissible cells construct the tier-2
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
        zip(coordinations, anchors_scaled, strict=True),
        zip(coordinations[1:], anchors_scaled[1:], strict=True),
        strict=False,
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
    """Exact two-envelope corrected ranking of one candidate pair in one cell.

    Mirrors ``AnchorBracket.certified_order_iff_endpoint_margins_fcc`` (bcc
    mirror ``certified_order_iff_endpoint_margins_bcc``; diamond/rocksalt
    exact cases). Candidate A ranks strictly below candidate B against every
    softening field consistent with the cell's anchors exactly when both the
    deep and shallow envelope margins are positive. ``certified = False``
    means one concrete envelope fails to preserve strict order; it does not
    assert that the physical reference order is reversed.
    """

    certified: bool
    corrected_a: float
    corrected_b: float
    #: Number of gap-coordination atoms in each configuration. The exact rule
    #: budgets both sides; equal populations cancel.
    gap_count_a: int
    gap_count_b: int
    #: Certified per-atom bracket width, x1e-4 eV/atom (0 for diamond).
    bracket_width_scaled: int
    structure: str
    #: Strict-order margins at the concrete deep and shallow envelopes.
    deep_margin: float
    shallow_margin: float
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "bracket_separation",
            "certified": self.certified,
            "corrected_a": self.corrected_a,
            "corrected_b": self.corrected_b,
            "gap_count_a": self.gap_count_a,
            "gap_count_b": self.gap_count_b,
            "bracket_width_scaled": self.bracket_width_scaled,
            "structure": self.structure,
            "deep_margin": self.deep_margin,
            "shallow_margin": self.shallow_margin,
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_bracket_separation(
    corrected_a: float,
    corrected_b: float,
    coordinations_a: Sequence[int],
    coordinations_b: Sequence[int],
    bracket_width_scaled: int,
    structure: str = "fcc",
    scale: int = 10000,
) -> BracketSeparationCertificate:
    """Run the exact two-envelope ranking criterion for one anchor layout.

    The supplied energies are the measured step-field corrections. This
    function derives each candidate's gap population from its coordination
    list, checks the layout-specific in-range precondition, and tests strict
    order at both concrete envelopes::

        deep:    corrected_a < corrected_b
        shallow: corrected_a - count_a*width
                   < corrected_b - count_b*width

    The two inequalities are equivalent in Lean to strict corrected order for
    every softening field consistent with the anchors. A statement about the
    *reference* order additionally requires exact field-decomposition for both
    model errors; this runtime certificate does not assert that empirical
    hypothesis. ``bracket_width_scaled`` should come from an admissible
    :class:`AnchorCertificate` for the same cell.

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
    if bracket_width_scaled < 0:
        raise ValueError(
            "bracket_width_scaled must be nonnegative; "
            f"got {bracket_width_scaled}"
        )
    if scale <= 0:
        raise ValueError(f"scale must be positive; got {scale}")
    floor = min(ANCHOR_COORDINATIONS[structure])
    for label, coordinations in (
        ("candidate A", coordinations_a),
        ("candidate B", coordinations_b),
    ):
        below = [(i, c) for i, c in enumerate(coordinations) if c < floor]
        if below:
            witnesses = ", ".join(f"atom {i} (c={c})" for i, c in below)
            raise ValueError(
                f"{label} is below the {structure} anchor floor c={floor}: "
                f"{witnesses}"
            )
    _identification_key, _bracket_key, separation_key = _BRACKET_REF_KEYS[structure]
    gap_coordination = GAP_COORDINATIONS[structure]
    gap_count_a = (
        sum(1 for c in coordinations_a if c == gap_coordination)
        if gap_coordination is not None
        else 0
    )
    gap_count_b = (
        sum(1 for c in coordinations_b if c == gap_coordination)
        if gap_coordination is not None
        else 0
    )
    if gap_coordination is None and bracket_width_scaled != 0:
        raise ValueError(
            f"{structure} has no unanchored in-range coordination; "
            "bracket_width_scaled must be 0"
        )
    width = bracket_width_scaled / scale
    deep_margin = corrected_b - corrected_a
    shallow_a = corrected_a - gap_count_a * width
    shallow_b = corrected_b - gap_count_b * width
    shallow_margin = shallow_b - shallow_a
    certified = deep_margin > 0 and shallow_margin > 0
    ref = THEOREM_REFS[separation_key]
    if certified:
        reason = (
            "corrected order certified against every consistent field: "
            f"deep margin {deep_margin:.6g} eV and shallow margin "
            f"{shallow_margin:.6g} eV are both strict; reference-order use "
            "still requires exact field-decomposable errors"
        )
    else:
        failed = []
        if deep_margin <= 0:
            failed.append(f"deep envelope margin {deep_margin:.6g} eV is not strict")
        if shallow_margin <= 0:
            failed.append(
                f"shallow envelope margin {shallow_margin:.6g} eV is not strict"
            )
        reason = (
            "measured anchors do not certify strict order: "
            + "; ".join(failed)
            + " — the named envelope is a concrete consistent field where "
            "the strict comparison fails; tighten anchors or abstain"
        )
    return BracketSeparationCertificate(
        certified=certified,
        corrected_a=corrected_a,
        corrected_b=corrected_b,
        gap_count_a=gap_count_a,
        gap_count_b=gap_count_b,
        bracket_width_scaled=bracket_width_scaled,
        structure=structure,
        deep_margin=deep_margin,
        shallow_margin=shallow_margin,
        theorem_ref=ref,
        reason=reason,
    )


@dataclass(frozen=True)
class BarrierCertificate:
    """Conservatism of a model-predicted barrier under monotone softening.

    Mirrors ``BarrierArrhenius.softened_barrier_underestimates``: when the
    transition-state configuration is *softer* (lower or equal first-shell
    coordination at every anchor) than the initial state, the model barrier
    is a lower bound on the reference barrier. The certificate also carries
    the ``softening_never_hides_conductor`` conservatism check: if the true
    material is not a conductor at the threshold ``EaStar``, the softened
    model cannot falsely claim it is.
    """

    conservative: bool
    model_barrier_ev: float
    reference_barrier_ev: float | None
    init_coordination: tuple[int, ...]
    ts_coordination: tuple[int, ...]
    theorem_ref: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "barrier_conservatism",
            "conservative": self.conservative,
            "model_barrier_ev": self.model_barrier_ev,
            "reference_barrier_ev": self.reference_barrier_ev,
            "init_coordination": list(self.init_coordination),
            "ts_coordination": list(self.ts_coordination),
            "theorem_ref": self.theorem_ref,
            "reason": self.reason,
        }


def check_barrier_conservatism(
    model_init_ev: float,
    model_ts_ev: float,
    init_coordination: Sequence[int],
    ts_coordination: Sequence[int],
    reference_init_ev: float | None = None,
    reference_ts_ev: float | None = None,
    conductor_threshold_ev: float | None = None,
) -> BarrierCertificate:
    """Mirror of the barrier-underestimation / conductor-conservatism laws.

    The softening law applies when ``ts_coordination`` is element-wise less
    than or equal to ``init_coordination`` (a transition state that is no more
    coordinated than the initial state). Under that ordering,
    ``softened_barrier_underestimates`` guarantees ``model_barrier <=
    reference_barrier``, so the model cannot overestimate the barrier and
    falsely screen out a viable ion conductor or catalyst.

    When ``conductor_threshold_ev`` is supplied, the additional
    ``softening_never_hides_conductor`` check is performed: a true conductor
    (reference barrier below threshold) remains classified as a conductor by
    the softened model.
    """
    model_barrier = model_ts_ev - model_init_ev
    reference_barrier = (
        None
        if reference_init_ev is None or reference_ts_ev is None
        else reference_ts_ev - reference_init_ev
    )

    if len(init_coordination) != len(ts_coordination):
        return BarrierCertificate(
            conservative=False,
            model_barrier_ev=model_barrier,
            reference_barrier_ev=reference_barrier,
            init_coordination=tuple(init_coordination),
            ts_coordination=tuple(ts_coordination),
            theorem_ref=THEOREM_REFS["barrier_underestimated"],
            reason=(
                "cannot assess barrier conservatism: initial and transition-state "
                f"configurations have different lengths ({len(init_coordination)} vs "
                f"{len(ts_coordination)})"
            ),
        )

    ordering_holds = all(
        ts <= init
        for ts, init in zip(ts_coordination, init_coordination, strict=True)
    )

    if not ordering_holds:
        return BarrierCertificate(
            conservative=False,
            model_barrier_ev=model_barrier,
            reference_barrier_ev=reference_barrier,
            init_coordination=tuple(init_coordination),
            ts_coordination=tuple(ts_coordination),
            theorem_ref=THEOREM_REFS["barrier_underestimated"],
            reason=(
                "transition state is not softer than initial state at every anchor — "
                "barrier-underestimation law does not apply"
            ),
        )

    # Under the softening ordering, the model barrier is a lower bound on the
    # reference barrier (or equal when the field sum cancels exactly).
    conservative = True
    reasons: list[str] = [
        "transition state is softer than initial state at every anchor; "
        "model barrier is a lower bound on the reference barrier "
        "(softened_barrier_underestimates)"
    ]

    if reference_barrier is not None and model_barrier > reference_barrier + 1e-9:
        conservative = False
        reasons.append(
            f"model barrier {model_barrier:.6f} eV exceeds reference barrier "
            f"{reference_barrier:.6f} eV — lower-bound guarantee is violated"
        )

    if conductor_threshold_ev is not None and reference_barrier is not None:
        true_conductor = reference_barrier <= conductor_threshold_ev
        model_conductor = model_barrier <= conductor_threshold_ev
        if true_conductor and not model_conductor:
            conservative = False
            reasons.append(
                "softened model hides a true conductor ("
                "softening_never_hides_conductor violated)"
            )
        else:
            reasons.append(
                "softened model does not hide a true conductor "
                "(softening_never_hides_conductor)"
            )

    return BarrierCertificate(
        conservative=conservative,
        model_barrier_ev=model_barrier,
        reference_barrier_ev=reference_barrier,
        init_coordination=tuple(init_coordination),
        ts_coordination=tuple(ts_coordination),
        theorem_ref=THEOREM_REFS["barrier_conservatism"]
        if conductor_threshold_ev is not None
        else THEOREM_REFS["barrier_underestimated"],
        reason="; ".join(reasons),
    )


Certificate = (
    DomainCertificate
    | AnchorCertificate
    | RankingCertificate
    | BarrierCertificate
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


def _binding_source_digest(
    report: Mapping[str, Any], report_path: pathlib.Path | None
) -> str | None:
    """Recompute the binder's corpus digest when its source files are adjacent."""
    if report_path is None:
        return None
    runs_dir = report_path.parent
    targets_dir = runs_dir.parent / "y_matrix_targets"
    run_paths = [
        runs_dir
        / f"{cell['material']}_{cell['structure']}_{cell['model_id']}.json"
        for cell in report["cells"]
    ]
    target_paths = [targets_dir / name for name in _BINDING_TARGET_FILES]
    if not all(path.is_file() for path in run_paths + target_paths):
        return None
    adjacent_sources = {
        path
        for structure in report["structures"]
        for path in runs_dir.glob(f"*_{structure}_*.json")
        if not path.name.endswith(".evidence.json") and path != report_path
    }
    if adjacent_sources != set(run_paths):
        # v2 does not carry a source manifest. Extra source runs may have been
        # hashed even when binding failed, so the exact digest is unknowable.
        return None
    sha = hashlib.sha256()
    for path in sorted(run_paths) + sorted(target_paths):
        sha.update(path.name.encode())
        sha.update(path.read_bytes())
    return sha.hexdigest()[:12]


def _report_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _lean_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_")


def certificates_from_binding_report(
    report: Mapping[str, Any],
    model_ids: Iterable[str] | None = None,
    *,
    report_path: str | pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Re-check every bound cell of an env-field binding report
    (``lupine.env_field_binding_report.v2``, emitted by
    ``python/scripts/bind_env_field_instances.py``) through the Lean-mirror
    admissibility predicate.

    The complete v2 report is validated before model filtering. Malformed cells
    are errors, never silently omitted. When ``report_path`` sits next to the
    source Y-matrix corpus, the binder's declared digest is recomputed too.
    """
    if not isinstance(report, Mapping):
        raise ValueError("binding report must be a JSON object")
    schema = report.get("schema")
    if schema != _BINDING_REPORT_SCHEMA:
        raise ValueError(
            f"unsupported binding report schema {schema!r}; "
            f"expected {_BINDING_REPORT_SCHEMA!r}"
        )
    if report.get("generator") != "python/scripts/bind_env_field_instances.py":
        raise ValueError("binding report has an unexpected generator")
    lean_module = report.get("lean_module")
    # The binder may legitimately write the Lean module outside the repo
    # (``--lean-out`` to a scratch dir records an absolute path). Fail closed
    # on a *different module*, not on a different output location: accept the
    # canonical repo-relative path or any path whose final component is the
    # EnvFieldInstances module file. The theorem namespace used below is
    # derived per-cell from ``lean_name``, independent of this provenance.
    normalized_module = lean_module.replace("\\", "/") if isinstance(lean_module, str) else ""
    if not (
        normalized_module == _BINDING_LEAN_MODULE
        or normalized_module == "EnvFieldInstances.lean"
        or normalized_module.endswith("/EnvFieldInstances.lean")
    ):
        raise ValueError("binding report has an unexpected lean_module")
    if report.get("scale") != 10000:
        raise ValueError("binding report scale must be 10000")
    digest = report.get("corpus_sha256_12")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{12}", digest) is None:
        raise ValueError("binding report corpus_sha256_12 must be 12 lowercase hex digits")
    cells = report.get("cells")
    if not isinstance(cells, list):
        raise ValueError("binding report cells must be a list")

    wanted = (
        {resolve_binder_model_id(str(m)) for m in model_ids}
        if model_ids is not None
        else None
    )
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    instance_count = 0
    structure_counts = {
        structure: {"cells": 0, "instances": 0, "refusals": 0}
        for structure in ANCHOR_COORDINATIONS
    }
    for index, cell in enumerate(cells):
        if not isinstance(cell, Mapping):
            raise ValueError(f"binding report cells[{index}] must be an object")
        material = cell.get("material")
        model_id = cell.get("model_id")
        structure = cell.get("structure")
        lean_name = cell.get("lean_name")
        for field_name, value in (
            ("material", material),
            ("model_id", model_id),
            ("structure", structure),
            ("lean_name", lean_name),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"binding report cells[{index}].{field_name} must be a non-empty string"
                )
        for field_name, value in (("material", material), ("model_id", model_id)):
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", value) is None:
                raise ValueError(
                    f"binding report cells[{index}].{field_name} contains unsafe characters"
                )
        expected = ANCHOR_COORDINATIONS.get(structure)
        if expected is None:
            raise ValueError(
                f"binding report cells[{index}].structure is unsupported: {structure!r}"
            )
        expected_lean_name = f"{_lean_name(model_id)}_{_lean_name(material)}"
        if lean_name != expected_lean_name:
            raise ValueError(
                f"binding report cells[{index}].lean_name is {lean_name!r}; "
                f"expected {expected_lean_name!r}"
            )
        key = (model_id, material, structure)
        if key in seen:
            raise ValueError(f"binding report contains duplicate cell {key!r}")
        seen.add(key)
        cell_anchors = cell.get("anchors")
        if not isinstance(cell_anchors, list) or len(cell_anchors) != len(expected):
            raise ValueError(
                f"binding report cells[{index}].anchors must contain "
                f"{len(expected)} entries"
            )
        anchors: list[int] = []
        for anchor_index, (anchor, coordination) in enumerate(
            zip(cell_anchors, expected, strict=True)
        ):
            if not isinstance(anchor, Mapping):
                raise ValueError(
                    f"binding report cells[{index}].anchors[{anchor_index}] must be an object"
                )
            if anchor.get("coordination") != coordination:
                raise ValueError(
                    f"binding report cells[{index}].anchors[{anchor_index}].coordination "
                    f"must be {coordination}"
                )
            p_scaled = anchor.get("p_scaled")
            if not _report_integer(p_scaled):
                raise ValueError(
                    f"binding report cells[{index}].anchors[{anchor_index}].p_scaled "
                    "must be an integer"
                )
            anchors.append(p_scaled)
        certificate = check_anchor_admissibility(*anchors, structure=structure)
        valid = cell.get("valid")
        violations = cell.get("violations")
        if not isinstance(valid, bool):
            raise ValueError(f"binding report cells[{index}].valid must be a boolean")
        if not isinstance(violations, list) or not all(
            isinstance(item, str) for item in violations
        ):
            raise ValueError(f"binding report cells[{index}].violations must be strings")
        certificate_valid = certificate.tier == "error_field"
        if valid != certificate_valid or tuple(violations) != certificate.violations:
            raise ValueError(
                f"binding report cells[{index}] declared outcome does not match anchors"
            )
        structure_counts[structure]["cells"] += 1
        structure_counts[structure]["instances" if valid else "refusals"] += 1
        instance_count += int(valid)
        if wanted is not None and model_id not in wanted:
            continue
        outcome_theorem_ref = (
            certificate.theorem_ref
            if valid
            else f"{_BINDING_NAMESPACE}.field_refused_{lean_name}"
        )
        entries.append(
            {
                "material": material,
                "model_id": model_id,
                "structure": structure,
                "lean_name": lean_name,
                "outcome_theorem_ref": outcome_theorem_ref,
                "certificate": certificate,
            }
        )

    expected_counts = {
        "n_cells": len(cells),
        "n_instances": instance_count,
        "n_refusals": len(cells) - instance_count,
    }
    for field_name, expected_count in expected_counts.items():
        value = report.get(field_name)
        if not _report_integer(value) or value != expected_count:
            raise ValueError(
                f"binding report {field_name} is {value!r}; expected {expected_count}"
            )
    structures = report.get("structures")
    if not isinstance(structures, Mapping):
        raise ValueError("binding report structures must be an object")
    if set(structures) != set(ANCHOR_COORDINATIONS):
        raise ValueError(
            "binding report structures must exactly match the supported layouts"
        )
    for structure, counts in structure_counts.items():
        summary = structures.get(structure)
        if not isinstance(summary, Mapping):
            raise ValueError(f"binding report structures.{structure} must be an object")
        for report_field, count_key in (
            ("n_cells", "cells"),
            ("n_instances", "instances"),
            ("n_refusals", "refusals"),
        ):
            if summary.get(report_field) != counts[count_key]:
                raise ValueError(
                    f"binding report structures.{structure}.{report_field} mismatch"
                )
    source_digest = _binding_source_digest(
        report, pathlib.Path(report_path) if report_path is not None else None
    )
    if source_digest is not None and source_digest != digest:
        raise ValueError(
            f"binding report digest mismatch: declared {digest}, recomputed {source_digest}"
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

    Every outcome is retained in ``certificate_evidence`` for telemetry, but
    only affirmative outcomes populate the promotion-authorizing formal
    fields. Refusals and indeterminate/non-applicable results therefore cannot
    satisfy the formal gate merely by existing. The input is not mutated."""
    enriched = dict(metadata)
    refs = list(enriched.get("atlas_theorem_refs", []) or [])
    props = list(enriched.get("formal_properties", []) or [])
    evidence = list(enriched.get("certificate_evidence", []) or [])
    for cert in certificates:
        payload = cert.to_dict()
        authorizes = (
            payload.get("admitted") is True
            or payload.get("tier") == "error_field"
            or payload.get("monotone_rescuable") is True
            or payload.get("conservative") is True
            or payload.get("certified") is True
        )
        evidence_item = {**payload, "authorizes_promotion": authorizes}
        if evidence_item not in evidence:
            evidence.append(evidence_item)
        if not authorizes:
            continue
        if cert.theorem_ref not in refs:
            refs.append(cert.theorem_ref)
        stamp = f"{payload['kind']}: {cert.reason}"
        if stamp not in props:
            props.append(stamp)
    enriched["atlas_theorem_refs"] = refs
    enriched["formal_properties"] = props
    enriched["certificate_evidence"] = evidence
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
    "BarrierCertificate",
    "BracketSeparationCertificate",
    "Certificate",
    "check_field_domain",
    "check_anchor_admissibility",
    "check_ranking_pair",
    "check_barrier_conservatism",
    "check_bracket_separation",
    "RUNTIME_MLIP_ALIASES",
    "resolve_binder_model_id",
    "certificates_from_binding_report",
    "theorem_refs",
    "merge_into_candidate_metadata",
]
