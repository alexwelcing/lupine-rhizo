import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain03

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
  { id := .chain3
    materialClass := "Catalysts"
    capability := "Δ-learned hybrid-accuracy screening with operando validation"
    acceptance := {
      id := .z3
      statement := "Adsorption energies within ~0.1 eV of experiment on a held-out benchmark at screening cost, with operando spot-validation"
      scope := .totalUncertaintyToReality
      provenance := .literatureBenchmark }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "GGA adsorption error 0.2–0.4 eV; OC20 consistency floor"
      solved := "~0.1 eV versus experiment at screening cost"
      solvedProvenance := .literatureBenchmark }
    provenance := [{ sourceId := 1, evidenceUnitId := 1, locator := "§15.2.3" },
      { sourceId := 2, evidenceUnitId := 2, locator := "§15.2.3" },
      { sourceId := 255, evidenceUnitId := 255, locator := "§15.2.3" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by native_decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_open_gate_blocks_clearance contract.gates .stabilityDurability rfl

end OpenDistillationFactory.DiscoveryChains.Chain03
