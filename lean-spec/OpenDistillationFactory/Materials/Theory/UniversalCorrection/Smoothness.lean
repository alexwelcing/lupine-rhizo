import Mathlib.Topology.MetricSpace.Pseudo.Defs
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Residual

/-!
# Scoped scalar smoothness

The Lipschitz premise is an explicit certificate assumption.  Lean proves its
consequences; a concrete campaign must validate and version the constant and
the metric for its own scope.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A scalar residual whose variation is bounded in the configured input
pseudometric. -/
def LipschitzResidual {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (L : ℝ) (field : ResidualField scope X ℝ) : Prop :=
  0 ≤ L ∧ ∀ x y, |field x - field y| ≤ L * dist x y

theorem LipschitzResidual.nonneg {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {L : ℝ} {field : ResidualField scope X ℝ}
    (h : LipschitzResidual L field) : 0 ≤ L :=
  h.1

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
