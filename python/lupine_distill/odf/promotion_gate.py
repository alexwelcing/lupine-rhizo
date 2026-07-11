"""Formal-verification promotion gate for the ODF pipeline.

This is the "[NEW] Formal specification check" inserted into the OperatorPack
promotion pipeline (ATLAS_Lean_Integration_Review.md §13.2, step 4):

    ODF Promotion Pipeline (with ATLAS gates):
      1. MLIP training complete (atlas-distill)
      2. TorchSim benchmark run (baseline comparison)
      3. distill_v_uplift calculation
      4. [NEW] Formal specification check   <-- THIS MODULE
      5. Promotion decision (human-in-the-loop if formal checks fail)
      6. OperatorPack artifact generation

The gate checks two things, given a candidate model's metadata:

  (a) the ``distill_v_uplift`` composite score (``overall_uplift_pct``) passes
      the uplift gate:
          promote   : uplift  > +5%
          review    : 0% <= uplift <= +5%
          reject     : uplift  < 0%
  (b) the required formal-verification fields are present and non-empty:
          ``atlas_theorem_refs`` (list) and ``formal_properties`` (list).

A missing/empty formal field downgrades an otherwise-promotable model to
``review`` (human-in-the-loop), and turns a borderline model into ``reject``.
The decision is returned as an immutable, structured value with reasons.

Design notes:
  - Immutable: inputs are validated into frozen pydantic models; the decision
    is a frozen dataclass. Nothing is mutated in place.
  - Boundary validation: untrusted candidate metadata is validated via
    :func:`evaluate_promotion` before any logic runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lupine_distill.odf.field_certificates import check_ranking_pair

# Uplift gate thresholds (percent), per §13.2 decision logic.
PROMOTE_THRESHOLD_PCT = 5.0   # uplift strictly above this -> promote
REJECT_THRESHOLD_PCT = 0.0    # uplift strictly below this -> reject
# In [REJECT_THRESHOLD_PCT, PROMOTE_THRESHOLD_PCT] -> review.


class PromotionDecision(str, Enum):
    """The three terminal promotion outcomes."""

    PROMOTE = "promote"
    REVIEW = "review"
    REJECT = "reject"


class CandidateMetadata(BaseModel):
    """Validated view of a promotion candidate's metadata.

    This is the boundary schema for :func:`evaluate_promotion`. The uplift
    score mirrors ``BenchmarkResult.overall_uplift_pct`` (the ``distill_v_uplift``
    composite); the two list fields carry the ATLAS formal contract.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    model_id: str = Field(..., min_length=1)
    distill_version: int = Field(..., ge=0)
    overall_uplift_pct: float | None = Field(
        default=None,
        description="distill_v_uplift composite score, percent. None == not computed.",
    )
    atlas_theorem_refs: list[str] = Field(
        default_factory=list,
        description="ATLAS/ODF theorem references the model claims to depend on.",
    )
    formal_properties: list[str] = Field(
        default_factory=list,
        description="Proved formal properties of the model.",
    )
    reference_ranking: list[float] | None = Field(
        default=None,
        description=(
            "Reference-property ranking of promotion-representative materials "
            "(lower-is-better, e.g. formation energy). Adjacent pairs are checked "
            "for monotone rescuability against model_ranking."
        ),
    )
    model_ranking: list[float] | None = Field(
        default=None,
        description=(
            "Model-predicted ranking corresponding to reference_ranking. An "
            "inverted adjacent pair is not repairable by any monotone "
            "recalibration (machine-checked impossibility) and downgrades the "
            "promotion decision."
        ),
    )


@dataclass(frozen=True)
class GateResult:
    """The structured, immutable output of the promotion gate."""

    model_id: str
    distill_version: int
    decision: PromotionDecision
    uplift_pct: float | None
    uplift_band: str
    formal_fields_present: bool
    ranking_inverted: bool = False
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable view of the decision (for logs/artifacts)."""
        return {
            "model_id": self.model_id,
            "distill_version": self.distill_version,
            "decision": self.decision.value,
            "uplift_pct": self.uplift_pct,
            "uplift_band": self.uplift_band,
            "formal_fields_present": self.formal_fields_present,
            "ranking_inverted": self.ranking_inverted,
            "reasons": list(self.reasons),
        }


def _uplift_band(uplift_pct: float | None) -> tuple[PromotionDecision, str]:
    """Classify the raw uplift score into the §13.2 uplift band.

    Returns the band's *uplift-only* decision plus a human-readable label.
    The formal-field check may further downgrade this in :func:`evaluate`.
    """
    if uplift_pct is None:
        return PromotionDecision.REJECT, "missing"
    if uplift_pct > PROMOTE_THRESHOLD_PCT:
        return PromotionDecision.PROMOTE, "promote"
    if uplift_pct < REJECT_THRESHOLD_PCT:
        return PromotionDecision.REJECT, "reject"
    return PromotionDecision.REVIEW, "review"


def evaluate(candidate: CandidateMetadata) -> GateResult:
    """Run the formal-verification promotion gate on validated metadata.

    Logic:
      1. Classify the uplift score into promote / review / reject.
      2. Require non-empty ``atlas_theorem_refs`` and ``formal_properties``.
         - If formal fields are missing and the uplift band is ``promote``,
           downgrade to ``review`` (human-in-the-loop, per §13.2 step 5).
         - If formal fields are missing and the uplift band is ``review``,
           downgrade to ``reject`` (cannot promote unverified, marginal model).
         - A ``reject`` uplift band stays ``reject``.
    """
    reasons: list[str] = []
    uplift = candidate.overall_uplift_pct
    band_decision, band_label = _uplift_band(uplift)

    if uplift is None:
        reasons.append("distill_v_uplift (overall_uplift_pct) is missing — cannot assess uplift.")
    elif band_decision is PromotionDecision.PROMOTE:
        reasons.append(f"Uplift {uplift:.2f}% > +{PROMOTE_THRESHOLD_PCT:.0f}% — clears the promote gate.")
    elif band_decision is PromotionDecision.REVIEW:
        reasons.append(
            f"Uplift {uplift:.2f}% in [{REJECT_THRESHOLD_PCT:.0f}%, "
            f"+{PROMOTE_THRESHOLD_PCT:.0f}%] — marginal, needs review."
        )
    else:
        reasons.append(f"Uplift {uplift:.2f}% < {REJECT_THRESHOLD_PCT:.0f}% — regression, reject.")

    has_theorems = len(candidate.atlas_theorem_refs) > 0
    has_properties = len(candidate.formal_properties) > 0
    formal_present = has_theorems and has_properties

    if not has_theorems:
        reasons.append("Formal check FAILED: atlas_theorem_refs is empty.")
    if not has_properties:
        reasons.append("Formal check FAILED: formal_properties is empty.")
    if formal_present:
        reasons.append(
            f"Formal check PASSED: {len(candidate.atlas_theorem_refs)} theorem ref(s), "
            f"{len(candidate.formal_properties)} formal property(ies)."
        )

    decision = band_decision
    if not formal_present:
        if band_decision is PromotionDecision.PROMOTE:
            decision = PromotionDecision.REVIEW
            reasons.append("Downgraded promote -> review: formal spec incomplete (human-in-the-loop).")
        elif band_decision is PromotionDecision.REVIEW:
            decision = PromotionDecision.REJECT
            reasons.append("Downgraded review -> reject: marginal uplift AND incomplete formal spec.")
        # REJECT stays REJECT.

    ranking_present = (
        candidate.reference_ranking is not None and candidate.model_ranking is not None
    )
    ranking_inverted = False
    if ranking_present:
        ref = candidate.reference_ranking
        mod = candidate.model_ranking
        if len(ref) != len(mod):
            reasons.append(
                f"Ranking check FAILED: reference_ranking length {len(ref)} != "
                f"model_ranking length {len(mod)}."
            )
        elif len(ref) < 2:
            reasons.append(
                "Ranking check SKIPPED: at least two ranked materials are required."
            )
        else:
            inverted_pairs: list[tuple[int, float, float, float, float]] = []
            for i in range(len(ref) - 1):
                cert = check_ranking_pair(ref[i], ref[i + 1], mod[i], mod[i + 1])
                if cert.inverted:
                    inverted_pairs.append(
                        (i, ref[i], ref[i + 1], mod[i], mod[i + 1])
                    )
            if inverted_pairs:
                ranking_inverted = True
                details = "; ".join(
                    f"pair {idx}: ref ({r1:.4f}, {r2:.4f}) vs model ({m1:.4f}, {m2:.4f})"
                    for idx, r1, r2, m1, m2 in inverted_pairs
                )
                reasons.append(
                    "Ranking check FAILED: ranking inversion detected — "
                    "no monotone recalibration can reconcile the pair(s) "
                    f"({details})."
                )
                # A ranking inversion is a machine-checked impossibility for
                # field-decomposable errors; it blocks promotion regardless of
                # uplift, because the model is ordering candidates opposite to
                # the reference.
                if decision is PromotionDecision.PROMOTE:
                    decision = PromotionDecision.REVIEW
                    reasons.append(
                        "Downgraded promote -> review: ranking inversion requires "
                        "energy-level correction or escalation."
                    )
                elif decision is PromotionDecision.REVIEW:
                    decision = PromotionDecision.REJECT
                    reasons.append(
                        "Downgraded review -> reject: marginal uplift AND ranking inversion."
                    )
                # REJECT stays REJECT.
            else:
                reasons.append(
                    f"Ranking check PASSED: {len(ref) - 1} adjacent pair(s) are "
                    "monotone-rescuable."
                )

    return GateResult(
        model_id=candidate.model_id,
        distill_version=candidate.distill_version,
        decision=decision,
        uplift_pct=uplift,
        uplift_band=band_label,
        formal_fields_present=formal_present,
        ranking_inverted=ranking_inverted,
        reasons=tuple(reasons),
    )


def evaluate_promotion(metadata: Mapping[str, Any]) -> GateResult:
    """Boundary entry point: validate raw candidate metadata, then evaluate.

    Accepts an untrusted mapping (e.g. parsed JSON from a benchmark run),
    validates it into :class:`CandidateMetadata`, and runs the gate.

    Raises:
        ValueError: if the metadata fails validation (wraps pydantic's
            ``ValidationError`` with a friendly message).
    """
    try:
        candidate = CandidateMetadata.model_validate(dict(metadata))
    except ValidationError as exc:
        raise ValueError(f"Invalid promotion candidate metadata: {exc}") from exc
    return evaluate(candidate)


__all__ = [
    "PROMOTE_THRESHOLD_PCT",
    "REJECT_THRESHOLD_PCT",
    "PromotionDecision",
    "CandidateMetadata",
    "GateResult",
    "evaluate",
    "evaluate_promotion",
]
