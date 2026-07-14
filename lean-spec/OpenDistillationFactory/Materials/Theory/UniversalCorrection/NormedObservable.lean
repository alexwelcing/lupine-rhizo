import Mathlib.Analysis.Normed.Group.Basic
import Mathlib.Analysis.Normed.Group.Real
import Mathlib.Tactic.Abel
import Mathlib.Tactic.Linarith
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Residual

/-!
# Normed observable correction

Energies are scalar, while forces, stresses, dipoles, and other molecular
observables are naturally vector- or tensor-valued.  This module propagates a
proof-carrying residual ball through a Lipschitz premise in any normed additive
group.  It therefore covers a force vector or flattened stress tensor once its
scope fixes the representation, units, and norm.

The result is deliberately an observable-level contract.  It does not infer a
force correction by differentiating an energy correction; that stronger claim
requires differentiability and implementation-refinement premises that must be
proved separately for a concrete model.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A residual field whose variation is bounded in norm. -/
def NormLipschitzResidual {scope : Scope} {X V : Type*}
    [PseudoMetricSpace X] [NormedAddCommGroup V]
    (L : ℝ) (field : ResidualField scope X V) : Prop :=
  0 ≤ L ∧ ∀ x y, ‖field x - field y‖ ≤ L * dist x y

/-- A measured norm ball for a vector- or tensor-valued residual. -/
structure ResidualBall (_scope : Scope) (X V : Type*) [Norm V] where
  point : X
  center : V
  radius : ℝ
  radius_nonneg : 0 ≤ radius

namespace ResidualBall

/-- The empirical assertion represented by a residual ball. -/
def Contains {scope : Scope} {X V : Type*} [NormedAddCommGroup V]
    (anchor : ResidualBall scope X V) (field : ResidualField scope X V) : Prop :=
  ‖field anchor.point - anchor.center‖ ≤ anchor.radius

/-- Radius obtained by transporting an anchor ball to a new configuration. -/
def propagatedRadius {scope : Scope} {X V : Type*}
    [PseudoMetricSpace X] [Norm V]
    (anchor : ResidualBall scope X V) (L : ℝ) (x : X) : ℝ :=
  anchor.radius + L * dist x anchor.point

/-- A transported radius is nonnegative under a valid Lipschitz premise. -/
theorem propagatedRadius_nonneg {scope : Scope} {X V : Type*}
    [PseudoMetricSpace X] [NormedAddCommGroup V]
    {anchor : ResidualBall scope X V} {field : ResidualField scope X V}
    {L : ℝ} {x : X} (hL : NormLipschitzResidual L field) :
    0 ≤ anchor.propagatedRadius L x := by
  unfold propagatedRadius
  have hdistance : 0 ≤ dist x anchor.point := dist_nonneg
  nlinarith [anchor.radius_nonneg, hL.1]

/-- **Normed-envelope soundness.** A compatible anchor ball and a global
Lipschitz premise enclose the residual at every configuration. -/
theorem residual_mem_propagated_ball
    {scope : Scope} {X V : Type*}
    [PseudoMetricSpace X] [NormedAddCommGroup V]
    {anchor : ResidualBall scope X V} {field : ResidualField scope X V}
    {L : ℝ} {x : X} (hanchor : anchor.Contains field)
    (hL : NormLipschitzResidual L field) :
    ‖field x - anchor.center‖ ≤ anchor.propagatedRadius L x := by
  have hdecomp :
      field x - anchor.center =
        (field x - field anchor.point) + (field anchor.point - anchor.center) := by
    abel
  rw [hdecomp]
  calc
    ‖(field x - field anchor.point) +
        (field anchor.point - anchor.center)‖ ≤
        ‖field x - field anchor.point‖ +
          ‖field anchor.point - anchor.center‖ := norm_add_le _ _
    _ ≤ L * dist x anchor.point + anchor.radius :=
      add_le_add (hL.2 x anchor.point) hanchor
    _ = anchor.propagatedRadius L x := by
      simp [propagatedRadius, add_comm]

/-- Subtracting the transported ball center from a model observable leaves an
error bounded by the transported radius. -/
theorem corrected_observable_error_le
    {scope : Scope} {X V : Type*}
    [PseudoMetricSpace X] [NormedAddCommGroup V]
    {anchor : ResidualBall scope X V} {field : ResidualField scope X V}
    {L : ℝ} {x : X} {modelValue referenceValue : V}
    (hresidual : field x = modelValue - referenceValue)
    (hanchor : anchor.Contains field)
    (hL : NormLipschitzResidual L field) :
    ‖(modelValue - anchor.center) - referenceValue‖ ≤
      anchor.propagatedRadius L x := by
  have hbound := residual_mem_propagated_ball (x := x) hanchor hL
  have heq :
      (modelValue - anchor.center) - referenceValue =
        field x - anchor.center := by
    rw [hresidual]
    abel
  rw [heq]
  exact hbound

end ResidualBall

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
