import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain08

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .unmet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .partiallyMet
  | .stabilityDurability => .unmet
  | .componentPerformance => .unmet
  | .manufacturability => .unmet
  | .technoeconomics => .unmet

def contract : ChainContract :=
  { id := .chain8
    materialClass := "Superconductors"
    capability := "Anharmonicity-aware MLIPs plus ML-accelerated DMFT"
    acceptance := {
      id := .z8
      statement := "Quantitative λ and ωlog with uncertainty, plus superexchange-J trends at cluster-DMFT fidelity"
      scope := .totalUncertaintyToReality
      provenance := .physicalTolerance }
    gates := gates
    readinessEvidence := { independentTargetUseful := 0, mechanismOrAdjacent := false }
    readiness := .low
    grammar := .seeksToDevelop
    gap := {
      current := "Harmonic λ +43%; no generally predictive unconventional-superconductor method"
      solved := "Quantitative λ and ωlog with uncertainty"
      solvedProvenance := .physicalTolerance }
    provenance := [{ sourceId := 11, evidenceUnitId := 11, locator := "§15.2.8" },
      { sourceId := 12, evidenceUnitId := 12, locator := "§15.2.8" },
      { sourceId := 184, evidenceUnitId := 184, locator := "§15.2.8" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .simulationAccuracy rfl

end OpenDistillationFactory.DiscoveryChains.Chain08
