import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain11

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .partiallyMet
  | .stabilityDurability => .unmet
  | .componentPerformance => .unmet
  | .manufacturability => .unmet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain11
    materialClass := "Thermoelectrics"
    capability := "Anharmonicity-aware thermal-conductivity prediction"
    acceptance := {
      id := .z11
      statement := "Quantitative lattice thermal conductivity with four-phonon and higher-order channels by default on a held-out set including anomalous crystals"
      scope := .totalUncertaintyToReality
      provenance := .physicalTolerance }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "BAs predictions 2200→1400 versus ~2100–2200 W/m·K, unexplained"
      solved := "Quantitative κ with four-phonon and higher channels by default"
      solvedProvenance := .physicalTolerance }
    provenance := [{ sourceId := 90, evidenceUnitId := 90, locator := "§15.2.11" },
      { sourceId := 391, evidenceUnitId := 391, locator := "§15.2.11" },
      { sourceId := 395, evidenceUnitId := 395, locator := "§15.2.11" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by native_decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .stabilityDurability rfl

end OpenDistillationFactory.DiscoveryChains.Chain11
