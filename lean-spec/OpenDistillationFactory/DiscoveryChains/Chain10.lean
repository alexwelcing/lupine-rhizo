import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain10

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .partiallyMet
  | .stabilityDurability => .unmet
  | .componentPerformance => .notApplicable
  | .manufacturability => .unmet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain10
    materialClass := "Stability meta-chain"
    capability := "Stability-first discovery loop"
    acceptance := {
      id := .z10
      statement := "A published, third-party-reproduced prospective record in which a majority of delivered candidates survive synthesis"
      scope := .totalUncertaintyToReality
      provenance := .authorProposed }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := ">100,000 synthesized MOFs yielding a handful of products"
      solved := "Majority-survival, third-party-reproduced funnels"
      solvedProvenance := .authorProposed }
    provenance := [{ sourceId := 33, evidenceUnitId := 33, locator := "§15.2.10" },
      { sourceId := 103, evidenceUnitId := 103, locator := "§15.2.10" },
      { sourceId := 370, evidenceUnitId := 370, locator := "§15.2.10" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .stabilityDurability rfl

end OpenDistillationFactory.DiscoveryChains.Chain10
