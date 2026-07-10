import Mathlib.Data.Real.Basic
import Mathlib.Algebra.Order.Group.MinMax
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-!
# Scaling relations and the Sabatier volcano: error propagation in catalyst screening

Electrochemical ammonia synthesis needs a catalyst that activates N≡N
(dissociation energy 945 kJ/mol) without being poisoned by its own
intermediates. Computational screening rests on two structures this module
formalizes:

* **Linear scaling relations**: intermediate binding energies are affine in a
  single descriptor (e.g. `ΔE_N`), so *one* descriptor error propagates to
  *every* intermediate — `descriptor_error_propagates` gives the exact
  propagation, and `shared_error_correlates` shows two intermediates' induced
  errors are rigidly correlated through their slopes. A mistake in one binding
  energy is never local.

* **The Sabatier volcano**: activity is the minimum of an ascending leg
  (N₂ activation limits: binding too weak) and a descending leg (product
  desorption limits: binding too strong). We prove the volcano's laws from
  first principles: `volcano_le_peak` (the crossover bounds all activity),
  `volcano_peak_value` (the bound is attained at the crossover),
  `volcano_ascending` / `volcano_descending` (monotone on each side), and
  `volcano_not_monotone_in_descriptor` — activity is *not* a monotone
  function of the descriptor, so by
  `RankingIntegrity.inversion_defeats_monotone` no monotone recalibration in
  descriptor space can repair an activity ranking that straddles the peak.
  Cross-peak candidates must be corrected at the energy level (the
  environment field) or escalated.

* **Breaker flagging**: `volcano_deviation_bound` — if a site's measured leg
  energies deviate from the scaling-relation prediction by at most τ, its
  scaling-predicted activity is τ-accurate; contrapositive
  (`activity_error_implicates_breaker`), an activity error larger than τ
  *proves* one of the legs broke the scaling relation by more than τ. That is
  the machine-checkable core of "the field's selective failure identifies
  scaling-relation-breaking catalysts" — the single-atom and multi-metal
  sites worth ab initio treatment precisely because they can beat the
  volcano peak.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.ScalingVolcano

/-- A linear (Brønsted–Evans–Polanyi-type) scaling relation: an intermediate's
binding or activation energy as an affine function of a descriptor energy. -/
structure ScalingRelation where
  /-- Sensitivity of this intermediate to the descriptor. -/
  slope : ℝ
  /-- Offset of this intermediate at zero descriptor. -/
  intercept : ℝ

namespace ScalingRelation

/-- The energy this relation assigns at descriptor value `x`. -/
def energyAt (S : ScalingRelation) (x : ℝ) : ℝ := S.slope * x + S.intercept

/-- **Exact error propagation.** A descriptor error δ shifts this
intermediate's energy by exactly `slope · δ`: errors ride the scaling
relation undamped. -/
theorem descriptor_error_propagates (S : ScalingRelation) (x δ : ℝ) :
    S.energyAt (x + δ) - S.energyAt x = S.slope * δ := by
  unfold energyAt; ring

/-- **Rigid error correlation.** The errors a shared descriptor error induces
in two scaling-related intermediates are locked in the ratio of their slopes
(stated cross-multiplied to avoid division): "a mistake in one binding energy
propagates to all others". -/
theorem shared_error_correlates (S₁ S₂ : ScalingRelation) (x δ : ℝ) :
    (S₁.energyAt (x + δ) - S₁.energyAt x) * S₂.slope =
      (S₂.energyAt (x + δ) - S₂.energyAt x) * S₁.slope := by
  unfold energyAt; ring

end ScalingRelation

/-- Sabatier activity: the minimum of the ascending (activation-limited) leg
`L` and the descending (desorption-limited) leg `R` at descriptor `x`. -/
def volcano (L R : ScalingRelation) (x : ℝ) : ℝ :=
  min (L.energyAt x) (R.energyAt x)

section Volcano

variable {L R : ScalingRelation} {xpk : ℝ}

/-- Left of the crossover the ascending leg is the active constraint. -/
theorem left_leg_below_iff (hL : 0 < L.slope) (hR : R.slope < 0)
    (hpk : L.energyAt xpk = R.energyAt xpk) (x : ℝ) :
    L.energyAt x ≤ R.energyAt x ↔ x ≤ xpk := by
  unfold ScalingRelation.energyAt at hpk ⊢
  constructor
  · intro h
    nlinarith
  · intro h
    nlinarith

/-- Right of the crossover the descending leg is the active constraint. -/
theorem right_leg_below_iff (hL : 0 < L.slope) (hR : R.slope < 0)
    (hpk : L.energyAt xpk = R.energyAt xpk) (x : ℝ) :
    R.energyAt x ≤ L.energyAt x ↔ xpk ≤ x := by
  unfold ScalingRelation.energyAt at hpk ⊢
  constructor
  · intro h
    nlinarith
  · intro h
    nlinarith

/-- **The volcano bound.** Activity anywhere is at most activity at the
crossover: the Sabatier peak is a provable ceiling for every
scaling-relation-obeying catalyst. -/
theorem volcano_le_peak (hL : 0 < L.slope) (hR : R.slope < 0)
    (hpk : L.energyAt xpk = R.energyAt xpk) (x : ℝ) :
    volcano L R x ≤ L.energyAt xpk := by
  rcases le_total x xpk with hx | hx
  · calc volcano L R x ≤ L.energyAt x := min_le_left _ _
      _ ≤ L.energyAt xpk := by
          unfold ScalingRelation.energyAt
          nlinarith
  · calc volcano L R x ≤ R.energyAt x := min_le_right _ _
      _ ≤ R.energyAt xpk := by
          unfold ScalingRelation.energyAt
          nlinarith
      _ = L.energyAt xpk := hpk.symm

/-- The volcano bound is attained at the crossover. -/
theorem volcano_peak_value (hpk : L.energyAt xpk = R.energyAt xpk) :
    volcano L R xpk = L.energyAt xpk := by
  unfold volcano
  rw [← hpk, min_self]

/-- Ascending flank: activity is monotone in the descriptor left of the
peak — within-flank rankings are descriptor rankings. -/
theorem volcano_ascending (hL : 0 < L.slope) (hR : R.slope < 0)
    (hpk : L.energyAt xpk = R.energyAt xpk) {x₁ x₂ : ℝ}
    (h12 : x₁ ≤ x₂) (h2 : x₂ ≤ xpk) :
    volcano L R x₁ ≤ volcano L R x₂ := by
  have e₁ : volcano L R x₁ = L.energyAt x₁ :=
    min_eq_left ((left_leg_below_iff hL hR hpk x₁).mpr (le_trans h12 h2))
  have e₂ : volcano L R x₂ = L.energyAt x₂ :=
    min_eq_left ((left_leg_below_iff hL hR hpk x₂).mpr h2)
  rw [e₁, e₂]
  unfold ScalingRelation.energyAt
  nlinarith

/-- Descending flank: activity is antitone in the descriptor right of the
peak. -/
theorem volcano_descending (hL : 0 < L.slope) (hR : R.slope < 0)
    (hpk : L.energyAt xpk = R.energyAt xpk) {x₁ x₂ : ℝ}
    (h1 : xpk ≤ x₁) (h12 : x₁ ≤ x₂) :
    volcano L R x₂ ≤ volcano L R x₁ := by
  have e₁ : volcano L R x₁ = R.energyAt x₁ :=
    min_eq_right ((right_leg_below_iff hL hR hpk x₁).mpr h1)
  have e₂ : volcano L R x₂ = R.energyAt x₂ :=
    min_eq_right ((right_leg_below_iff hL hR hpk x₂).mpr (le_trans h1 h12))
  rw [e₁, e₂]
  unfold ScalingRelation.energyAt
  nlinarith

end Volcano

/-- **Activity is not monotone in the descriptor.** Witnessed on the canonical
volcano min(x, 2 − x): the descriptor orders 0.5 < 1.8 but activity orders
them oppositely (0.5 > 0.2). Combined with
`RankingIntegrity.inversion_defeats_monotone`, no monotone recalibration in
descriptor space can repair an activity ranking that straddles the volcano
peak — cross-peak candidates need energy-level correction or ab initio
escalation. -/
theorem volcano_not_monotone_in_descriptor :
    ¬ Monotone (volcano ⟨1, 0⟩ ⟨-1, 2⟩) := by
  intro h
  have h1 : volcano ⟨1, 0⟩ ⟨-1, 2⟩ (0.5 : ℝ) = 0.5 := by
    unfold volcano ScalingRelation.energyAt
    rw [min_eq_left (by norm_num)]
    norm_num
  have h2 : volcano ⟨1, 0⟩ ⟨-1, 2⟩ (1.8 : ℝ) = 0.2 := by
    unfold volcano ScalingRelation.energyAt
    rw [min_eq_right (by norm_num)]
    norm_num
  have := h (show (0.5 : ℝ) ≤ 1.8 by norm_num)
  rw [h1, h2] at this
  norm_num at this

/-- **Breaker-flag soundness.** If both measured legs deviate from their
scaling-relation predictions by at most τ, the scaling-predicted activity is
τ-accurate. Screening by scaling relations is provably safe for
non-breakers. -/
theorem volcano_deviation_bound {τ lm rm lp rp : ℝ}
    (hl : |lm - lp| ≤ τ) (hr : |rm - rp| ≤ τ) :
    |min lm rm - min lp rp| ≤ τ :=
  le_trans (abs_min_sub_min_le_max lm rm lp rp) (max_le hl hr)

/-- **Breaker detection.** Contrapositive: an activity discrepancy larger
than τ *proves* at least one leg broke its scaling relation by more than τ —
the machine-checkable flag that routes single-atom and multi-metal sites to
explicit ab initio treatment, exactly the sites that can beat the volcano
peak. -/
theorem activity_error_implicates_breaker {τ lm rm lp rp : ℝ}
    (h : τ < |min lm rm - min lp rp|) :
    τ < |lm - lp| ∨ τ < |rm - rp| := by
  by_contra hno
  push Not at hno
  exact absurd (volcano_deviation_bound hno.1 hno.2) (not_le.mpr h)

end OpenDistillationFactory.Materials.Theory.ScalingVolcano
