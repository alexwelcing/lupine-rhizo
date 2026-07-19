import OpenDistillationFactory.HonestErrors.Evidence
import OpenDistillationFactory.HonestErrors.Taxonomy

/-! Scope-indexed executable acceptance thresholds. -/

namespace OpenDistillationFactory.HonestErrors

inductive AcceptanceScope where
  | fidelityToFixedReference
  | totalUncertaintyToReality
  deriving DecidableEq, Repr

inductive BoundDirection where
  | atMost
  | atLeast
  deriving DecidableEq, Repr

inductive Decision where
  | pass
  | fail
  deriving DecidableEq, Repr

structure ScopedObservation (metric : Metric) (scope : AcceptanceScope) where
  magnitude : MetricValue metric
  deriving DecidableEq, Repr

structure Threshold (metric : Metric) (scope : AcceptanceScope) where
  boundary : MetricValue metric
  direction : BoundDirection
  provenance : TargetProvenance
  deriving DecidableEq, Repr

def evaluate {metric : Metric} {scope : AcceptanceScope}
    (threshold : Threshold metric scope)
    (observed : ScopedObservation metric scope) : Decision :=
  match threshold.direction with
  | .atMost => if observed.magnitude.value ≤ threshold.boundary.value then .pass else .fail
  | .atLeast => if threshold.boundary.value ≤ observed.magnitude.value then .pass else .fail

theorem evaluate_atMost_iff {metric : Metric} {scope : AcceptanceScope}
    (boundary observed : MetricValue metric) (provenance : TargetProvenance) :
    evaluate (scope := scope)
        { boundary := boundary, direction := .atMost, provenance := provenance }
        { magnitude := observed } = .pass ↔ observed.value ≤ boundary.value := by
  simp [evaluate]

theorem evaluate_atLeast_iff {metric : Metric} {scope : AcceptanceScope}
    (boundary observed : MetricValue metric) (provenance : TargetProvenance) :
    evaluate (scope := scope)
        { boundary := boundary, direction := .atLeast, provenance := provenance }
        { magnitude := observed } = .pass ↔ boundary.value ≤ observed.value := by
  simp [evaluate]

theorem atMost_improvement_preserves_pass
    {metric : Metric} {scope : AcceptanceScope}
    (boundary oldValue newValue : MetricValue metric)
    (provenance : TargetProvenance)
    (himproves : newValue.value ≤ oldValue.value)
    (hold : evaluate (scope := scope)
        { boundary := boundary, direction := .atMost, provenance := provenance }
        { magnitude := oldValue } = .pass) :
    evaluate (scope := scope)
        { boundary := boundary, direction := .atMost, provenance := provenance }
        { magnitude := newValue } = .pass := by
  rw [evaluate_atMost_iff (scope := scope)] at hold ⊢
  exact le_trans (α := ℚ) himproves hold

theorem tighter_atMost_pass_implies_looser_pass
    {metric : Metric} {scope : AcceptanceScope}
    (tight loose observed : MetricValue metric)
    (provenance : TargetProvenance)
    (htight : tight.value ≤ loose.value)
    (hpass : evaluate (scope := scope)
        { boundary := tight, direction := .atMost, provenance := provenance }
        { magnitude := observed } = .pass) :
    evaluate (scope := scope)
        { boundary := loose, direction := .atMost, provenance := provenance }
        { magnitude := observed } = .pass := by
  rw [evaluate_atMost_iff (scope := scope)] at hpass ⊢
  exact le_trans (α := ℚ) hpass htight

end OpenDistillationFactory.HonestErrors
