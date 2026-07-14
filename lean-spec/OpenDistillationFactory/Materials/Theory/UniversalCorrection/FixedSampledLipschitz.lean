import Mathlib.Data.Int.Basic
import Lean.Elab.Tactic.Omega

/-!
# Exact finite-sample Lipschitz diagnostics

Runtime and campaign tooling need an executable check over serialized numeric
evidence.  A `FixedPairObservation` records an exact fixed-point residual pair
and an exact nonnegative descriptor distance.  The checker below uses only
integer and natural-number arithmetic, so its result is deterministic across
architectures.

Passing this checker establishes only the listed pair inequalities.  It does
not construct a global `LipschitzResidual`; `TrajectoryValidation` records that
separation explicitly and gives a counterexample to the invalid converse.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- One exact pairwise observation in common fixed-point units. -/
structure FixedPairObservation where
  leftResidual : Int
  rightResidual : Int
  descriptorDistance : Nat
  deriving DecidableEq, Repr

namespace FixedPairObservation

/-- Absolute fixed-point residual separation for this observation. -/
def residualGap (observation : FixedPairObservation) : Nat :=
  Int.natAbs (observation.leftResidual - observation.rightResidual)

/-- The exact pair satisfies the proposed integer Lipschitz factor. -/
def Admissible (factor : Nat) (observation : FixedPairObservation) : Prop :=
  observation.residualGap ≤ factor * observation.descriptorDistance

instance (factor : Nat) (observation : FixedPairObservation) :
    Decidable (observation.Admissible factor) := by
  unfold Admissible
  infer_instance

/-- Executable exact checker for one observed pair. -/
def check (factor : Nat) (observation : FixedPairObservation) : Bool :=
  decide (observation.Admissible factor)

@[simp] theorem check_eq_true_iff (factor : Nat)
    (observation : FixedPairObservation) :
    observation.check factor = true ↔ observation.Admissible factor := by
  simp [check]

@[simp] theorem check_eq_false_iff (factor : Nat)
    (observation : FixedPairObservation) :
    observation.check factor = false ↔ ¬ observation.Admissible factor := by
  simp [check]

/-- A zero-distance descriptor collision with unequal residuals is rejected
for every finite factor. -/
theorem zero_distance_collision_rejected
    (observation : FixedPairObservation)
    (hdistance : observation.descriptorDistance = 0)
    (hseparated : observation.leftResidual ≠ observation.rightResidual)
    (factor : Nat) :
    observation.check factor = false := by
  rw [check_eq_false_iff]
  unfold Admissible residualGap
  rw [hdistance]
  simp only [Nat.mul_zero, not_le, Nat.lt_iff_add_one_le]
  have hsub : observation.leftResidual - observation.rightResidual ≠ 0 := by
    omega
  exact Int.natAbs_pos.mpr hsub

end FixedPairObservation

/-- Every exact observed pair satisfies the proposed factor. -/
def FixedSampledLipschitz (factor : Nat)
    (observations : List FixedPairObservation) : Prop :=
  ∀ observation ∈ observations, observation.Admissible factor

instance (factor : Nat) (observations : List FixedPairObservation) :
    Decidable (FixedSampledLipschitz factor observations) := by
  unfold FixedSampledLipschitz
  infer_instance

/-- Architecture-independent finite-sample checker. -/
def checkFixedSampledLipschitz (factor : Nat)
    (observations : List FixedPairObservation) : Bool :=
  observations.all (fun observation => observation.check factor)

/-- The executable list checker is exactly equivalent to the declarative
finite-sample proposition. -/
theorem checkFixedSampledLipschitz_eq_true_iff
    (factor : Nat) (observations : List FixedPairObservation) :
    checkFixedSampledLipschitz factor observations = true ↔
      FixedSampledLipschitz factor observations := by
  simp [checkFixedSampledLipschitz, FixedSampledLipschitz]

/-- Failure returns the existence of an observed counterexample, rather than
a claim about an unobserved configuration. -/
theorem checkFixedSampledLipschitz_eq_false_iff
    (factor : Nat) (observations : List FixedPairObservation) :
    checkFixedSampledLipschitz factor observations = false ↔
      ∃ observation ∈ observations, ¬ observation.Admissible factor := by
  rw [Bool.eq_false_iff]
  constructor
  · intro hnot
    by_contra hnoCounterexample
    apply hnot
    apply (checkFixedSampledLipschitz_eq_true_iff factor observations).mpr
    intro observation hmem
    by_contra hbad
    exact hnoCounterexample ⟨observation, hmem, hbad⟩
  · rintro ⟨observation, hmem, hbad⟩ htrue
    have hall := (checkFixedSampledLipschitz_eq_true_iff factor observations).mp htrue
    exact hbad (hall observation hmem)

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
