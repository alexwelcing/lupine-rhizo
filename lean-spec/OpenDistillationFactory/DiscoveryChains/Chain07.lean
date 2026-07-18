import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain07

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .untested
  | .synthesis => .partiallyMet
  | .stabilityDurability => .unmet
  | .componentPerformance => .unmet
  | .manufacturability => .partiallyMet
  | .technoeconomics => .unmet

def contract : ChainContract :=
  { id := .chain7
    materialClass := "Fusion materials"
    capability := "Rare-event-validated MLIPs with calibrated uncertainty"
    acceptance := {
      id := .z7
      statement := "A validated cascade-to-OKMC-to-rate-theory hand-off with calibrated error bars, supporting 50 dpa qualification"
      scope := .totalUncertaintyToReality
      provenance := .engineeringRequirement }
    gates := gates
    readinessEvidence := { independentTargetUseful := 0, mechanismOrAdjacent := false }
    readiness := .low
    grammar := .seeksToDevelop
    gap := {
      current := "240 ps versus five years; qualification near 20 dpa versus 50 dpa"
      solved := "Calibrated cascade-to-rate-theory hand-off for 50 dpa qualification"
      solvedProvenance := .engineeringRequirement }
    provenance := [{ sourceId := 18, evidenceUnitId := 18, locator := "§15.2.7" },
      { sourceId := 335, evidenceUnitId := 335, locator := "§15.2.7" },
      { sourceId := 412, evidenceUnitId := 412, locator := "§15.2.7" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_untested_gate_blocks_clearance contract.gates .hitRateUplift rfl

end OpenDistillationFactory.DiscoveryChains.Chain07
