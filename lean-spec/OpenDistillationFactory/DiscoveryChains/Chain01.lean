import OpenDistillationFactory.DiscoveryChains.Core

namespace OpenDistillationFactory.DiscoveryChains.Chain01

open HonestErrors

private def gates : GateProfile
  | .simulationAccuracy => .partiallyMet
  | .hitRateUplift => .partiallyMet
  | .synthesis => .untested
  | .stabilityDurability => .unmet
  | .componentPerformance => .unmet
  | .manufacturability => .unmet
  | .technoeconomics => .partiallyMet

def contract : ChainContract :=
  { id := .chain1
    materialClass := "Batteries"
    capability := "Barrier-targeted fine-tuning with signed-error-audited escalation"
    acceptance := {
      id := .z1
      statement := "Migration-barrier MAE ≤ 40 meV against DFT-NEB across chemistries, with balanced signed errors and an experiment-facing uncertainty budget"
      scope := .totalUncertaintyToReality
      provenance := .authorProposed }
    gates := gates
    readinessEvidence := { independentTargetUseful := 1, mechanismOrAdjacent := true }
    readiness := .medium
    grammar := .conditionalTransfer
    gap := {
      current := "0.310–0.349 eV MAE; ~60 meV DFT-NEB floor"
      solved := "≤40 meV against DFT-NEB plus signed-error audit"
      solvedProvenance := .authorProposed }
    provenance := [{ sourceId := 5, evidenceUnitId := 5, locator := "§15.2.1" },
      { sourceId := 6, evidenceUnitId := 6, locator := "§15.2.1" },
      { sourceId := 104, evidenceUnitId := 104, locator := "§15.2.1" }]
    asOfDate := "2026-07-17" }

theorem contract_valid : ContractValid contract := by native_decide

theorem gate_clearance : ¬ Clears contract.gates := by
  exact one_untested_gate_blocks_clearance contract.gates .synthesis rfl

end OpenDistillationFactory.DiscoveryChains.Chain01
