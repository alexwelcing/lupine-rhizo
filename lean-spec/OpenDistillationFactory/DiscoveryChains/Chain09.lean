import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain09

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .unmet
  | .hitRateUplift => .untested
  | .synthesis => .partiallyMet
  | .stabilityDurability => .partiallyMet
  | .componentPerformance => .unmet
  | .manufacturability => .partiallyMet
  | .technoeconomics => .unmet

def contract : ChainContract :=
  { id := .chain9
    materialClass := "Correlated oxides"
    capability := "Correlation-aware spin/electronic-degree-of-freedom MLIPs"
    acceptance := {
      id := .z9
      statement := "Screening-capable correlated energetics with exchange-integral errors bounded against neutron data"
      scope := .totalUncertaintyToReality
      provenance := .authorProposed }
    gates := gates
    readinessEvidence := { independentTargetUseful := 0, mechanismOrAdjacent := false }
    readiness := .low
    grammar := .seeksToDevelop
    gap := {
      current := "Mott insulators returned as metals; exact DMFT solvers scale as O(T⁻³)"
      solved := "Screening-capable correlated energetics"
      solvedProvenance := .authorProposed }
    provenance := [{ sourceId := 160, evidenceUnitId := 160, locator := "§15.2.9" },
      { sourceId := 173, evidenceUnitId := 173, locator := "§15.2.9" },
      { sourceId := 185, evidenceUnitId := 185, locator := "§15.2.9" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_untested_gate_blocks_clearance contract.gates .hitRateUplift rfl

end OpenDistillationFactory.DiscoveryChains.Chain09
