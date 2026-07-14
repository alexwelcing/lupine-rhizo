import Mathlib.Tactic.Linarith
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Smoothness

/-!
# Cold-start limits

Smoothness controls relative variation; without at least one absolute anchor
it cannot bound the level of a residual field.  The constant-field witnesses
below formalize why a universal correction engine must refuse a genuinely
anchor-free scope instead of presenting extrapolation as certification.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A constant residual field at a fixed absolute level. -/
def constantResidual {scope : Scope} {X : Type*} (value : ℝ) :
    ResidualField scope X ℝ :=
  fun _ => value

/-- Every constant field is Lipschitz for every nonnegative constant. -/
theorem constantResidual_lipschitz {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (value : ℝ) {L : ℝ} (hL : 0 ≤ L) :
    LipschitzResidual L (constantResidual (scope := scope) (X := X) value) := by
  constructor
  · exact hL
  · intro x y
    simp [constantResidual]
    positivity

/-- No finite upper bound follows from Lipschitz smoothness alone. -/
theorem no_anchor_upper_bound {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (x : X) (bound : ℝ) :
    ∃ field : ResidualField scope X ℝ,
      LipschitzResidual 0 field ∧ bound < field x := by
  refine ⟨constantResidual (scope := scope) (X := X) (bound + 1), ?_, ?_⟩
  · exact constantResidual_lipschitz (bound + 1) (by norm_num)
  · simp [constantResidual]

/-- No finite lower bound follows from Lipschitz smoothness alone. -/
theorem no_anchor_lower_bound {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (x : X) (bound : ℝ) :
    ∃ field : ResidualField scope X ℝ,
      LipschitzResidual 0 field ∧ field x < bound := by
  refine ⟨constantResidual (scope := scope) (X := X) (bound - 1), ?_, ?_⟩
  · exact constantResidual_lipschitz (bound - 1) (by norm_num)
  · simp [constantResidual]

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
