import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain04

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .partiallyMet
  | .stabilityDurability => .unmet
  | .componentPerformance => .unmet
  | .manufacturability => .partiallyMet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain4
    materialClass := "High-entropy alloys"
    capability := "Disorder-native MLIPs"
    acceptance := {
      id := .z4
      statement := "Energy MAE ≤ 2.5 meV/atom on a DFT-labeled, short-range-order-resolved multi-composition benchmark"
      scope := .fidelityToFixedReference
      provenance := .literatureBenchmark }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "MS25 at 4–5× threshold; separate HEA25S fine-tune 617.9→3.5 meV/atom"
      solved := "≤2.5 meV/atom across the controlled benchmark"
      solvedProvenance := .literatureBenchmark }
    provenance := [{ sourceId := 7, evidenceUnitId := 7, locator := "§15.2.4" },
      { sourceId := 8, evidenceUnitId := 8, locator := "§15.2.4" },
      { sourceId := 210, evidenceUnitId := 210, locator := "§15.2.4" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .stabilityDurability rfl

end OpenDistillationFactory.DiscoveryChains.Chain04
