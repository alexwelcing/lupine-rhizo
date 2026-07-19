import Mathlib.Data.Fintype.Card
import Mathlib.Data.List.Basic
import Mathlib.Tactic.DeriveFintype

/-! Evidence, readiness, controlled grammar, and provenance types. -/

namespace OpenDistillationFactory.HonestErrors

inductive EpistemicMark where
  | observed
  | inferred
  | transferred
  | proposed
  | forecast
  deriving DecidableEq, Repr

inductive EvidenceGrade where
  | medium
  | high
  deriving DecidableEq, Fintype, Repr

inductive Readiness where
  | low
  | medium
  | high
  deriving DecidableEq, Repr

inductive ClaimGrammar where
  | seeksToDevelop
  | conditionalTransfer
  | demonstratedNextTest
  deriving DecidableEq, Repr

inductive TargetProvenance where
  | physicalTolerance
  | engineeringRequirement
  | literatureBenchmark
  | authorProposed
  deriving DecidableEq, Repr

structure SourceRef where
  sourceId : Nat
  evidenceUnitId : Nat
  locator : String
  deriving DecidableEq, Repr

structure ReadinessEvidence where
  independentTargetUseful : Nat
  mechanismOrAdjacent : Bool
  deriving DecidableEq, Repr

def classifyReadiness (evidence : ReadinessEvidence) : Readiness :=
  if 2 ≤ evidence.independentTargetUseful then .high
  else if 1 ≤ evidence.independentTargetUseful ∨ evidence.mechanismOrAdjacent then .medium
  else .low

def grammarFor : Readiness → ClaimGrammar
  | .high => .demonstratedNextTest
  | .medium => .conditionalTransfer
  | .low => .seeksToDevelop

theorem evidenceGrade_card : Fintype.card EvidenceGrade = 2 := by decide

theorem readiness_of_two_target_demonstrations
    (evidence : ReadinessEvidence)
    (hcount : 2 ≤ evidence.independentTargetUseful) :
    classifyReadiness evidence = .high := by
  simp [classifyReadiness, hcount]

theorem readiness_of_adjacent_evidence
    (evidence : ReadinessEvidence)
    (hcount : ¬ 2 ≤ evidence.independentTargetUseful)
    (hadjacent : evidence.mechanismOrAdjacent = true) :
    classifyReadiness evidence = .medium := by
  simp [classifyReadiness, hcount, hadjacent]

theorem readiness_of_one_target_demonstration
    (evidence : ReadinessEvidence)
    (hcount : evidence.independentTargetUseful = 1) :
    classifyReadiness evidence = .medium := by
  simp [classifyReadiness, hcount]

theorem readiness_of_no_demonstration
    (evidence : ReadinessEvidence)
    (hcount : evidence.independentTargetUseful = 0)
    (hadjacent : evidence.mechanismOrAdjacent = false) :
    classifyReadiness evidence = .low := by
  simp [classifyReadiness, hcount, hadjacent]

theorem medium_requires_conditional :
    grammarFor .medium = .conditionalTransfer := rfl

theorem low_requires_capability_first :
    grammarFor .low = .seeksToDevelop := rfl

/-- A machine-readable load-bearing claim imported from a report snapshot. -/
structure ClaimRecord where
  marker : EpistemicMark
  sources : List SourceRef
  readinessEvidence : ReadinessEvidence
  readiness : Readiness
  grammar : ClaimGrammar
  targetProvenance : Option TargetProvenance
  asOfDate : String
  deriving Repr

/-- Structural validity checks provenance, rubric classification, and controlled prose. -/
def StructurallyValid (claim : ClaimRecord) : Prop :=
  claim.sources ≠ [] ∧
  claim.targetProvenance ≠ none ∧
  claim.readiness = classifyReadiness claim.readinessEvidence ∧
  claim.grammar = grammarFor claim.readiness

instance (claim : ClaimRecord) : Decidable (StructurallyValid claim) := by
  unfold StructurallyValid
  infer_instance

theorem structurally_valid_requires_canonical_grammar
    (claim : ClaimRecord) (hvalid : StructurallyValid claim) :
    claim.grammar = grammarFor claim.readiness :=
  hvalid.2.2.2

theorem structurally_valid_requires_target_provenance
    (claim : ClaimRecord) (hvalid : StructurallyValid claim) :
    claim.targetProvenance ≠ none :=
  hvalid.2.1

theorem structurally_valid_requires_classified_readiness
    (claim : ClaimRecord) (hvalid : StructurallyValid claim) :
    claim.readiness = classifyReadiness claim.readinessEvidence :=
  hvalid.2.2.1

end OpenDistillationFactory.HonestErrors
