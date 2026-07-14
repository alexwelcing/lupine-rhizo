import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith

/-!
# Deterministic robust ranking

Portfolio claims begin with interval separation, not uncalibrated probability
labels.  If the complete score interval of one candidate is strictly below
another's, their true minimization order is certified.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A proof-carrying closed real interval used for scientific score bounds. -/
structure ScoreInterval where
  lower : ℝ
  upper : ℝ
  valid : lower ≤ upper

namespace ScoreInterval

/-- A true score is enclosed by an interval. -/
def Contains (interval : ScoreInterval) (score : ℝ) : Prop :=
  interval.lower ≤ score ∧ score ≤ interval.upper

/-- Strict robust precedence for a minimization objective. -/
def RobustlyPrecedes (left right : ScoreInterval) : Prop :=
  left.upper < right.lower

/-- Interval separation certifies the true order for every enclosed pair. -/
theorem robustlyPrecedes_sound {left right : ScoreInterval}
    {leftScore rightScore : ℝ}
    (horder : left.RobustlyPrecedes right)
    (hleft : left.Contains leftScore)
    (hright : right.Contains rightScore) :
    leftScore < rightScore := by
  unfold RobustlyPrecedes at horder
  unfold Contains at hleft hright
  linarith

/-- Exact point intervals recover ordinary strict order. -/
def exact (score : ℝ) : ScoreInterval where
  lower := score
  upper := score
  valid := le_rfl

@[simp] theorem exact_contains_iff (score truth : ℝ) :
    (exact score).Contains truth ↔ truth = score := by
  constructor
  · intro h
    unfold Contains exact at h
    linarith
  · rintro rfl
    simp [Contains, exact]

@[simp] theorem exact_robustlyPrecedes_iff (left right : ℝ) :
    (exact left).RobustlyPrecedes (exact right) ↔ left < right := Iff.rfl

end ScoreInterval

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
