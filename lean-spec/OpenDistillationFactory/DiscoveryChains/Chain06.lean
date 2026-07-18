import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain06

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .unmet
  | .synthesis => .unmet
  | .stabilityDurability => .unmet
  | .componentPerformance => .partiallyMet
  | .manufacturability => .unmet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain6
    materialClass := "Semiconductors and perovskites"
    capability := "Error-cancellation-free excited-state stack"
    acceptance := {
      id := .z6
      statement := "Right gaps for the right reasons at screening cost, with ±0.05 eV compositional targeting"
      scope := .totalUncertaintyToReality
      provenance := .engineeringRequirement }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "LDA ~50% low; ~1 eV spin-orbit cancellation"
      solved := "Right gaps at screening cost with ±0.05 eV targeting"
      solvedProvenance := .engineeringRequirement }
    provenance := [{ sourceId := 20, evidenceUnitId := 20, locator := "§15.2.6" },
      { sourceId := 386, evidenceUnitId := 386, locator := "§15.2.6" },
      { sourceId := 407, evidenceUnitId := 407, locator := "§15.2.6" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .hitRateUplift rfl

end OpenDistillationFactory.DiscoveryChains.Chain06
