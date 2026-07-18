import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain02

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
  { id := .chain2
    materialClass := "Magnets"
    capability := "Spin-aware multi-fidelity magnetic simulation"
    acceptance := {
      id := .z2
      statement := "Ranking-faithful magnetocrystalline anisotropy energy and Tc on a held-out rare-earth-free set, with microstructure-aware coercivity bounds"
      scope := .totalUncertaintyToReality
      provenance := .engineeringRequirement }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "Tc errors 15–35% with unstable sign; coercivity overestimated ~5×"
      solved := "Ranking-faithful anisotropy and Tc plus coercivity bounds"
      solvedProvenance := .engineeringRequirement }
    provenance := [{ sourceId := 16, evidenceUnitId := 16, locator := "§15.2.2" },
      { sourceId := 17, evidenceUnitId := 17, locator := "§15.2.2" },
      { sourceId := 285, evidenceUnitId := 285, locator := "§15.2.2" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by native_decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .stabilityDurability rfl

end OpenDistillationFactory.DiscoveryChains.Chain02
