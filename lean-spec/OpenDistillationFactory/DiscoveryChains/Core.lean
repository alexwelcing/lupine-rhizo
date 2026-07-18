import Mathlib.Data.Fintype.Card
import Mathlib.Tactic.DeriveFintype
import OpenDistillationFactory.HonestErrors.Acceptance
import OpenDistillationFactory.HonestErrors.StageGates

/-! Shared typed contract for the eleven Chapter 15 discovery chains. -/

namespace OpenDistillationFactory.DiscoveryChains

open HonestErrors

inductive ChainId where
  | chain1 | chain2 | chain3 | chain4 | chain5 | chain6
  | chain7 | chain8 | chain9 | chain10 | chain11
  deriving DecidableEq, Fintype, Repr

inductive AcceptanceTestId where
  | z1 | z2 | z3 | z4 | z5 | z6 | z7 | z8 | z9 | z10 | z11
  deriving DecidableEq, Fintype, Repr

def acceptanceFor : ChainId → AcceptanceTestId
  | .chain1 => .z1
  | .chain2 => .z2
  | .chain3 => .z3
  | .chain4 => .z4
  | .chain5 => .z5
  | .chain6 => .z6
  | .chain7 => .z7
  | .chain8 => .z8
  | .chain9 => .z9
  | .chain10 => .z10
  | .chain11 => .z11

/-- A named, scope-aware acceptance test. Composite tests retain their exact prose. -/
structure AcceptanceTest where
  id : AcceptanceTestId
  statement : String
  scope : AcceptanceScope
  provenance : TargetProvenance
  deriving DecidableEq, Repr

/-- The Chapter 15 current-versus-solved pair, including solved-target provenance. -/
structure CurrentSolvedGap where
  current : String
  solved : String
  solvedProvenance : TargetProvenance
  deriving DecidableEq, Repr

structure ChainContract where
  id : ChainId
  materialClass : String
  capability : String
  acceptance : AcceptanceTest
  gates : GateProfile
  readinessEvidence : ReadinessEvidence
  readiness : Readiness
  grammar : ClaimGrammar
  gap : CurrentSolvedGap
  provenance : List SourceRef
  asOfDate : String

/-- Structural validity links Z-number, readiness rubric, grammar, and provenance. -/
def ContractValid (contract : ChainContract) : Prop :=
  contract.acceptance.id = acceptanceFor contract.id ∧
  contract.acceptance.statement ≠ "" ∧
  contract.readiness = classifyReadiness contract.readinessEvidence ∧
  contract.grammar = grammarFor contract.readiness ∧
  contract.provenance ≠ [] ∧
  contract.asOfDate = "2026-07-17"

instance (contract : ChainContract) : Decidable (ContractValid contract) := by
  unfold ContractValid
  infer_instance

theorem chainId_card : Fintype.card ChainId = 11 := by decide

theorem acceptanceTestId_card : Fintype.card AcceptanceTestId = 11 := by decide

end OpenDistillationFactory.DiscoveryChains
