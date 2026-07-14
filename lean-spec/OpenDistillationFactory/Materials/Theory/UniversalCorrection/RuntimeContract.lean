import Lean.Elab.Tactic.Omega
import Mathlib.Tactic.SplitIfs
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.NumericContract

/-!
# Composite runtime correction contract

This module is the exact reference monitor at the Lean/runtime boundary.  A
request declares one scientific scope, one numeric contract, and a maximum
accepted interval width.  Evidence is admitted only when:

1. its scope is exactly the requested scope;
2. its complete numeric contract is exactly the requested contract;
3. that numeric contract agrees with the scope's units and semantic name;
4. its fixed-point scale is positive;
5. its interval is ordered;
6. the checker supports the declared schema and outward-rounding convention;
7. its interval width is within policy tolerance.

Definite contract contradictions and inverted intervals are refusals.
Well-formed but unsupported or insufficiently precise inputs are
indeterminate.  Only admission authorizes correction.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- Immutable runtime expectations for one correction decision. -/
structure RuntimePolicy where
  scope : Scope
  numeric : NumericContract
  tolerance : Nat
  deriving DecidableEq, Repr

namespace RuntimePolicy

/-- Strict contract compatibility before checking implementation support or
the width of an individual interval. -/
def ContractCompatible (policy : RuntimePolicy) (evidence : FixedMeasurement) : Prop :=
  policy.scope = evidence.scope ∧
    policy.numeric = evidence.numeric ∧
      policy.numeric.ScopeCompatible policy.scope ∧
        policy.numeric.WellFormed

instance contractCompatibleDecidable (policy : RuntimePolicy)
    (evidence : FixedMeasurement) : Decidable (policy.ContractCompatible evidence) :=
  inferInstanceAs
    (Decidable
      (policy.scope = evidence.scope ∧
        policy.numeric = evidence.numeric ∧
          policy.numeric.ScopeCompatible policy.scope ∧
            policy.numeric.WellFormed))

/-- Complete declarative admission predicate implemented by
`checkRuntimeContract`. -/
def Admissible (policy : RuntimePolicy) (evidence : FixedMeasurement) : Prop :=
  policy.ContractCompatible evidence ∧
    evidence.envelope.Ordered ∧
      policy.numeric.Supported ∧
        evidence.envelope.width ≤ (policy.tolerance : Int)

instance admissibleDecidable (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    Decidable (policy.Admissible evidence) :=
  inferInstanceAs
    (Decidable
      (policy.ContractCompatible evidence ∧
        evidence.envelope.Ordered ∧
          policy.numeric.Supported ∧
            evidence.envelope.width ≤ (policy.tolerance : Int)))

end RuntimePolicy

/-- Definite contradictions that invalidate a runtime certificate. -/
inductive RuntimeViolation where
  /-- Scope, numeric identity, units, semantics, or scale is incompatible. -/
  | incompatibleContract
  /-- The encoded lower endpoint exceeds the upper endpoint. -/
  | inconsistentEnvelope
  deriving DecidableEq, Repr

/-- Non-false inputs that the current checker cannot authorize. -/
inductive RuntimeReason where
  | unsupportedSchema
  | unsupportedRounding
  | widthTooLarge
  deriving DecidableEq, Repr

/-- Exact composite reference checker.  The order is part of its deterministic
certificate semantics: contract contradictions dominate interval failures,
which dominate unsupported encodings, which dominate insufficient precision.
-/
def checkRuntimeContract (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    GateDecision RuntimeViolation RuntimeReason :=
  if policy.ContractCompatible evidence then
    if evidence.envelope.Ordered then
      if policy.numeric.schemaVersion = currentNumericSchemaVersion then
        if policy.numeric.rounding = .outward then
          if evidence.envelope.width ≤ (policy.tolerance : Int) then
            .admit
          else
            .indeterminate .widthTooLarge
        else
          .indeterminate .unsupportedRounding
      else
        .indeterminate .unsupportedSchema
    else
      .refuse .inconsistentEnvelope
  else
    .refuse .incompatibleContract

/-- Admission is exactly the declarative composite runtime contract. -/
theorem checkRuntimeContract_admit_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .admit ↔
      policy.Admissible evidence := by
  unfold checkRuntimeContract RuntimePolicy.Admissible NumericContract.Supported
  split_ifs <;> simp_all

/-- Contract refusal has no hidden empirical meaning: it occurs exactly when
the serialized scope/numeric contract is incompatible. -/
theorem checkRuntimeContract_incompatible_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .refuse .incompatibleContract ↔
      ¬ policy.ContractCompatible evidence := by
  unfold checkRuntimeContract
  split_ifs <;> simp_all

/-- An interval inconsistency is reported exactly after contract compatibility
has succeeded and the raw endpoints are inverted. -/
theorem checkRuntimeContract_inconsistent_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .refuse .inconsistentEnvelope ↔
      policy.ContractCompatible evidence ∧
        evidence.envelope.upper < evidence.envelope.lower := by
  unfold checkRuntimeContract FixedEnvelope.Ordered
  split_ifs <;> simp_all

/-- Unsupported schema is an indeterminate result, never a scientific
refutation. -/
theorem checkRuntimeContract_unsupportedSchema_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .indeterminate .unsupportedSchema ↔
      policy.ContractCompatible evidence ∧
        evidence.envelope.Ordered ∧
          policy.numeric.schemaVersion ≠ currentNumericSchemaVersion := by
  unfold checkRuntimeContract
  split_ifs <;> simp_all

/-- Unsupported rounding is reached only for a supported schema after every
definite compatibility check has passed. -/
theorem checkRuntimeContract_unsupportedRounding_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .indeterminate .unsupportedRounding ↔
      policy.ContractCompatible evidence ∧
        evidence.envelope.Ordered ∧
          policy.numeric.schemaVersion = currentNumericSchemaVersion ∧
            policy.numeric.rounding ≠ .outward := by
  unfold checkRuntimeContract
  split_ifs <;> simp_all

/-- A width failure is reached only after scope, numeric semantics, schema,
rounding, and interval consistency have all been established. -/
theorem checkRuntimeContract_widthTooLarge_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    checkRuntimeContract policy evidence = .indeterminate .widthTooLarge ↔
      policy.ContractCompatible evidence ∧
        evidence.envelope.Ordered ∧
          policy.numeric.schemaVersion = currentNumericSchemaVersion ∧
            policy.numeric.rounding = .outward ∧
              (policy.tolerance : Int) < evidence.envelope.width := by
  unfold checkRuntimeContract
  split_ifs <;> simp_all
  omega

/-- The composite runtime monitor is fail-closed. -/
theorem correctionAllowed_checkRuntimeContract_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) :
    correctionAllowed (checkRuntimeContract policy evidence) = true ↔
      policy.Admissible evidence := by
  rw [← checkRuntimeContract_admit_iff]
  cases h : checkRuntimeContract policy evidence <;> simp_all

/-- Refining an already admitted interval preserves admission as long as the
refined payload uses the same scope and numeric contract. -/
theorem admissible_of_refinement
    {policy : RuntimePolicy} {coarse : FixedMeasurement}
    (hcoarse : policy.Admissible coarse)
    {fineEnvelope : FixedEnvelope}
    (hrefines : fineEnvelope.Refines coarse.envelope)
    (hordered : fineEnvelope.Ordered) :
    policy.Admissible
      { scope := coarse.scope, numeric := coarse.numeric, envelope := fineEnvelope } := by
  rcases hcoarse with ⟨hcontract, _, hsupported, hwidth⟩
  refine ⟨?_, hordered, hsupported, ?_⟩
  · exact hcontract
  · exact (FixedEnvelope.width_le_of_refines hrefines).trans hwidth

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
