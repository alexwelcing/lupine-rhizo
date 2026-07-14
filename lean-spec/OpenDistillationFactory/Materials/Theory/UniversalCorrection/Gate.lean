import Lean.Elab.Tactic.Omega
import Mathlib.Tactic.SplitIfs

/-!
# Exact runtime gate semantics

The scientific gate is deliberately three-valued.  `admit` means every
premise required by the correction policy has been established; `refuse`
carries a definite counter-witness; `indeterminate` records insufficient
numeric or empirical resolution.  Certified correction is fail-closed: only
`admit` authorizes application.

The executable checker below uses exact integers.  Floating-point ingestion,
unit normalization, and outward rounding belong at a separately verified
boundary; they are not hidden inside the assurance predicate.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

universe u v

/-- Result of a theorem-backed scientific gate. -/
inductive GateDecision (Violation : Type u) (Reason : Type v) where
  | admit
  | refuse (witness : Violation)
  | indeterminate (reason : Reason)
  deriving DecidableEq, Repr

/-- Exact fixed-point enclosure produced by the numeric boundary. -/
structure FixedEnvelope where
  lower : Int
  upper : Int
  deriving DecidableEq, Repr

/-- A definite contradiction in the supplied interval. -/
inductive EnvelopeViolation where
  | inconsistent
  deriving DecidableEq, Repr

/-- A well-formed interval that is too wide for the requested policy. -/
inductive EnvelopeReason where
  | widthTooLarge
  deriving DecidableEq, Repr

namespace FixedEnvelope

/-- Exact admissibility predicate mirrored by `checkFixedEnvelope`. -/
def Admissible (tolerance : Nat) (envelope : FixedEnvelope) : Prop :=
  envelope.lower ≤ envelope.upper ∧
    envelope.upper - envelope.lower ≤ (tolerance : Int)

end FixedEnvelope

/-- Exact, deterministic reference checker for one fixed-point enclosure. -/
def checkFixedEnvelope (tolerance : Nat) (envelope : FixedEnvelope) :
    GateDecision EnvelopeViolation EnvelopeReason :=
  if envelope.upper < envelope.lower then
    .refuse .inconsistent
  else if (tolerance : Int) < envelope.upper - envelope.lower then
    .indeterminate .widthTooLarge
  else
    .admit

/-- Admission is equivalent to the declarative admissibility predicate. -/
theorem checkFixedEnvelope_admit_iff (tolerance : Nat) (envelope : FixedEnvelope) :
    checkFixedEnvelope tolerance envelope = .admit ↔
      envelope.Admissible tolerance := by
  unfold checkFixedEnvelope FixedEnvelope.Admissible
  split_ifs <;> simp_all <;> omega

/-- A refusal occurs exactly when the enclosure itself is inconsistent. -/
theorem checkFixedEnvelope_refuse_iff (tolerance : Nat) (envelope : FixedEnvelope) :
    checkFixedEnvelope tolerance envelope = .refuse .inconsistent ↔
      envelope.upper < envelope.lower := by
  unfold checkFixedEnvelope
  split_ifs <;> simp_all

/-- Indeterminacy is exactly the well-formed-but-too-wide case. -/
theorem checkFixedEnvelope_indeterminate_iff
    (tolerance : Nat) (envelope : FixedEnvelope) :
    checkFixedEnvelope tolerance envelope = .indeterminate .widthTooLarge ↔
      envelope.lower ≤ envelope.upper ∧
        (tolerance : Int) < envelope.upper - envelope.lower := by
  unfold checkFixedEnvelope
  split_ifs <;> simp_all <;> omega

/-- Fail-closed authorization: only an admitted scientific result allows a
correction.  Operational policy actions remain outside this predicate. -/
def correctionAllowed : GateDecision Violation Reason → Bool
  | .admit => true
  | .refuse _ => false
  | .indeterminate _ => false

@[simp] theorem correctionAllowed_admit :
    correctionAllowed (GateDecision.admit : GateDecision Violation Reason) = true := rfl

@[simp] theorem correctionAllowed_refuse (witness : Violation) :
    correctionAllowed (GateDecision.refuse witness : GateDecision Violation Reason) = false := rfl

@[simp] theorem correctionAllowed_indeterminate (reason : Reason) :
    correctionAllowed (GateDecision.indeterminate reason : GateDecision Violation Reason) = false := rfl

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
