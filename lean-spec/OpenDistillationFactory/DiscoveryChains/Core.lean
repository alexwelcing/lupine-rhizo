import Mathlib.Data.Fintype.Card
import Mathlib.Tactic.DeriveFintype
import OpenDistillationFactory.ErrorLandscape.MasterMatrix
import OpenDistillationFactory.HonestErrors.Acceptance
import OpenDistillationFactory.HonestErrors.StageGates

/-! Shared typed contract for the eleven Chapter 15 discovery chains. -/

namespace OpenDistillationFactory.DiscoveryChains

open HonestErrors

inductive ChainId where
  | chain1 | chain2 | chain3 | chain4 | chain5 | chain6
  | chain7 | chain8 | chain9 | chain10 | chain11
  deriving DecidableEq, Fintype, Repr

/-- Stable ontology identifiers for the nine rows of the material-class matrix. -/
inductive MaterialClassId where
  | MC1 | MC2 | MC3 | MC4 | MC5 | MC6 | MC7 | MC8 | MC9
  deriving DecidableEq, Fintype, Repr

/-- Bind each discovery chain to its material-class ontology identifier.
Chain 10 is the class-independent stability meta-chain; MC9 intentionally owns
both the excited-state (C6) and thermal-transport (C11) chains. -/
def classFor : ChainId → Option MaterialClassId
  | .chain1 => some .MC4
  | .chain2 => some .MC6
  | .chain3 => some .MC5
  | .chain4 => some .MC3
  | .chain5 => some .MC8
  | .chain6 => some .MC9
  | .chain7 => some .MC7
  | .chain8 => some .MC1
  | .chain9 => some .MC2
  | .chain10 => none
  | .chain11 => some .MC9

/-- Interpret the one-based discovery-chain numbers stored in the master matrix. -/
def chainIdOfNat? : Nat → Option ChainId
  | 1 => some .chain1
  | 2 => some .chain2
  | 3 => some .chain3
  | 4 => some .chain4
  | 5 => some .chain5
  | 6 => some .chain6
  | 7 => some .chain7
  | 8 => some .chain8
  | 9 => some .chain9
  | 10 => some .chain10
  | 11 => some .chain11
  | _ => none

/-- Check that a nonempty master-matrix chain list belongs to one material class. -/
def chainsBelongTo (chains : List Nat) (materialClass : MaterialClassId) : Bool :=
  !chains.isEmpty && chains.all fun n =>
    match chainIdOfNat? n with
    | some chain => classFor chain == some materialClass
    | none => false

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

-- Ontology binding locks: the nine material IDs match the nine rows of the
-- master matrix, C10 is the class-independent meta-chain, and acceptance tests
-- remain a one-to-one map over all eleven chains.
#guard ErrorLandscape.masterMatrix.length = Fintype.card MaterialClassId
#guard classFor .chain1 == some .MC4
#guard classFor .chain2 == some .MC6
#guard classFor .chain3 == some .MC5
#guard classFor .chain4 == some .MC3
#guard classFor .chain5 == some .MC8
#guard classFor .chain6 == some .MC9
#guard classFor .chain7 == some .MC7
#guard classFor .chain8 == some .MC1
#guard classFor .chain9 == some .MC2
#guard classFor .chain10 == none
#guard classFor .chain11 == some .MC9
#guard chainIdOfNat? 0 == none
#guard chainIdOfNat? 12 == none
#guard chainsBelongTo [] .MC4 == false
#guard chainsBelongTo [1] .MC6 == false
#guard chainsBelongTo ErrorLandscape.batteriesRow.discoveryChains .MC4
#guard chainsBelongTo ErrorLandscape.magnetsRow.discoveryChains .MC6
#guard chainsBelongTo ErrorLandscape.catalystsRow.discoveryChains .MC5
#guard chainsBelongTo ErrorLandscape.heasRow.discoveryChains .MC3
#guard chainsBelongTo ErrorLandscape.frameworksRow.discoveryChains .MC8
#guard chainsBelongTo ErrorLandscape.semiconductorsRow.discoveryChains .MC9
#guard chainsBelongTo ErrorLandscape.fusionRow.discoveryChains .MC7
#guard chainsBelongTo ErrorLandscape.superconductorsRow.discoveryChains .MC1
#guard chainsBelongTo ErrorLandscape.correlatedOxidesRow.discoveryChains .MC2
#guard decide ([acceptanceFor .chain1, acceptanceFor .chain2,
  acceptanceFor .chain3, acceptanceFor .chain4, acceptanceFor .chain5,
  acceptanceFor .chain6, acceptanceFor .chain7, acceptanceFor .chain8,
  acceptanceFor .chain9, acceptanceFor .chain10,
  acceptanceFor .chain11].Nodup)

end OpenDistillationFactory.DiscoveryChains
