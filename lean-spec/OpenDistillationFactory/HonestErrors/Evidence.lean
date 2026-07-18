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

end OpenDistillationFactory.HonestErrors
