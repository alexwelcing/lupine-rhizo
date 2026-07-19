import Mathlib.Data.Real.Basic
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-!
# Fixed-reference fidelity and a reality-facing error budget

This is the formal core of §3.4.  Every quantity and budget is indexed by one
observable and one common unit, so the typed budget API rejects (for example) an
eV component supplied directly as a percentage or label fraction.  A caller can
still erase an index by projecting `.value`; assigning the correct index,
converting units, and avoiding unjustified erasure remain modeling obligations.

Lean proves the conservative triangle-inequality certificate that follows from
the signed decomposition.  The bound does not assert statistical independence
or the absence of cancellation.
-/

namespace OpenDistillationFactory.HonestErrors

inductive BudgetObservable where
  | migrationBarrier
  | adsorptionEnergy
  | energyPerAtom
  | density
  | force
  | timescale
  | dose
  | labelFraction
  deriving DecidableEq, Repr

inductive BudgetUnit where
  | electronVolt
  | milliElectronVolt
  | electronVoltPerAtom
  | percent
  | fraction
  | picosecond
  | year
  | displacementPerAtom
  deriving DecidableEq, Repr

/-- A signed scalar whose observable and unit are phantom type indices. -/
structure Quantity
    (observable : BudgetObservable) (unit : BudgetUnit) where
  value : ℝ

structure RealityBudget
    (observable : BudgetObservable) (unit : BudgetUnit) where
  referenceMethod : Quantity observable unit
  numerical : Quantity observable unit
  model : Quantity observable unit
  domain : Quantity observable unit
  experimentalReference : Quantity observable unit

def RealityBudget.signedTotal
    {observable : BudgetObservable} {unit : BudgetUnit}
    (budget : RealityBudget observable unit) : ℝ :=
  ((((budget.referenceMethod.value + budget.numerical.value) +
    budget.model.value) + budget.domain.value) +
    budget.experimentalReference.value)

def RealityBudget.l1Radius
    {observable : BudgetObservable} {unit : BudgetUnit}
    (budget : RealityBudget observable unit) : ℝ :=
  ((((|budget.referenceMethod.value| + |budget.numerical.value|) +
    |budget.model.value|) + |budget.domain.value|) +
    |budget.experimentalReference.value|)

theorem RealityBudget.abs_signedTotal_le_l1Radius
    {observable : BudgetObservable} {unit : BudgetUnit}
    (budget : RealityBudget observable unit) :
    |budget.signedTotal| ≤ budget.l1Radius := by
  unfold signedTotal l1Radius
  calc
    |((((budget.referenceMethod.value + budget.numerical.value) +
        budget.model.value) + budget.domain.value) +
        budget.experimentalReference.value)|
        ≤ |(((budget.referenceMethod.value + budget.numerical.value) +
            budget.model.value) + budget.domain.value)| +
            |budget.experimentalReference.value| := abs_add_le _ _
    _ ≤ (|((budget.referenceMethod.value + budget.numerical.value) +
          budget.model.value)| + |budget.domain.value|) +
          |budget.experimentalReference.value| := by
          exact add_le_add
            (abs_add_le
              ((budget.referenceMethod.value + budget.numerical.value) +
                budget.model.value) budget.domain.value)
            (le_refl |budget.experimentalReference.value|)
    _ ≤ ((|(budget.referenceMethod.value + budget.numerical.value)| +
          |budget.model.value|) + |budget.domain.value|) +
          |budget.experimentalReference.value| := by
          exact add_le_add
            (add_le_add
              (abs_add_le
                (budget.referenceMethod.value + budget.numerical.value)
                budget.model.value)
              (le_refl |budget.domain.value|))
            (le_refl |budget.experimentalReference.value|)
    _ ≤ (((|budget.referenceMethod.value| + |budget.numerical.value|) +
          |budget.model.value|) + |budget.domain.value|) +
          |budget.experimentalReference.value| := by
          exact add_le_add
            (add_le_add
              (add_le_add
                (abs_add_le budget.referenceMethod.value
                  budget.numerical.value)
                (le_refl |budget.model.value|))
              (le_refl |budget.domain.value|))
            (le_refl |budget.experimentalReference.value|)

/-- Fixed-reference fidelity plus reference error bounds total reality error. -/
theorem fidelity_plus_reference_bound
    {observable : BudgetObservable} {unit : BudgetUnit}
    {model label reality : Quantity observable unit}
    {fidelityBound referenceBound : ℝ}
    (hfidelity : |model.value - label.value| ≤ fidelityBound)
    (hreference : |label.value - reality.value| ≤ referenceBound) :
    |model.value - reality.value| ≤ fidelityBound + referenceBound := by
  have hdecomp : model.value - reality.value =
      (model.value - label.value) + (label.value - reality.value) := by ring
  rw [hdecomp]
  exact le_trans (abs_add_le _ _) (add_le_add hfidelity hreference)

def exampleModel : Quantity .migrationBarrier .electronVolt := ⟨1⟩
def exampleLabel : Quantity .migrationBarrier .electronVolt := ⟨1⟩
def exampleReality : Quantity .migrationBarrier .electronVolt := ⟨0⟩

/-- Perfect label fidelity can coexist with a nonzero error to reality. -/
theorem zero_fidelity_can_have_reality_error :
    |exampleModel.value - exampleLabel.value| = 0 ∧
      |exampleModel.value - exampleReality.value| = 1 := by
  norm_num [exampleModel, exampleLabel, exampleReality]

noncomputable def twoPointMAE
    {observable : BudgetObservable} {unit : BudgetUnit}
    (first second : Quantity observable unit) : ℝ :=
  (|first.value| + |second.value|) / 2

noncomputable def twoPointSignedMean
    {observable : BudgetObservable} {unit : BudgetUnit}
    (first second : Quantity observable unit) : ℝ :=
  (first.value + second.value) / 2

/-- Equal MAE does not determine signed bias, so a signed-error audit is additional evidence. -/
theorem same_mae_different_signed_bias
    {observable : BudgetObservable} {unit : BudgetUnit}
    (error : Quantity observable unit) (herror : 0 < error.value) :
    twoPointMAE error ⟨-error.value⟩ = twoPointMAE error error ∧
    twoPointSignedMean error ⟨-error.value⟩ = 0 ∧
    twoPointSignedMean error error = error.value := by
  simp [twoPointMAE, twoPointSignedMean, abs_of_pos herror]

end OpenDistillationFactory.HonestErrors
