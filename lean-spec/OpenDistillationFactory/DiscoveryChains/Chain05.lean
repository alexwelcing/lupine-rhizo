import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain05

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .partiallyMet
  | .stabilityDurability => .partiallyMet
  | .componentPerformance => .unmet
  | .manufacturability => .partiallyMet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain5
    materialClass := "Porous frameworks"
    capability := "Dispersion-consistent MLIPs with explicit long-range interactions"
    acceptance := {
      id := .z5
      statement := "Scheme-consistent adsorption enthalpies within ~4 kJ/mol plus thermodynamic water-stability classification"
      scope := .totalUncertaintyToReality
      provenance := .physicalTolerance }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "vdW spread 0.77–3.04×; cross-framework degradation ≥10×"
      solved := "~4 kJ/mol plus water-stability classification"
      solvedProvenance := .physicalTolerance }
    provenance := [{ sourceId := 19, evidenceUnitId := 19, locator := "§15.2.5" },
      { sourceId := 7, evidenceUnitId := 7, locator := "§15.2.5" },
      { sourceId := 371, evidenceUnitId := 371, locator := "§15.2.5" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .componentPerformance rfl

end OpenDistillationFactory.DiscoveryChains.Chain05
