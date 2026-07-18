/-! The seven stage gates and their five Chapter 15 statuses. -/

namespace OpenDistillationFactory.HonestErrors

inductive GateStage where
  | simulationAccuracy
  | hitRateUplift
  | synthesis
  | stabilityDurability
  | componentPerformance
  | manufacturability
  | technoeconomics
  deriving DecidableEq, Repr

inductive GateStatus where
  | met
  | partiallyMet
  | unmet
  | untested
  | notApplicable
  deriving DecidableEq, Repr

abbrev GateProfile := GateStage → GateStatus

def ClearedStatus (status : GateStatus) : Prop :=
  status = .met ∨ status = .notApplicable

def Clears (profile : GateProfile) : Prop :=
  ∀ stage, ClearedStatus (profile stage)

def mayAdvance : GateStatus → GateStatus → Bool
  | .met, .met => true
  | .notApplicable, .notApplicable => true
  | .partiallyMet, .partiallyMet | .partiallyMet, .met => true
  | .unmet, .unmet | .unmet, .partiallyMet | .unmet, .met => true
  | .untested, .untested | .untested, .partiallyMet | .untested, .met => true
  | _, _ => false

theorem one_open_gate_blocks_clearance (profile : GateProfile) (stage : GateStage)
    (hopen : profile stage = .unmet) : ¬ Clears profile := by
  intro hclears
  have hstage := hclears stage
  simp [ClearedStatus, hopen] at hstage

theorem one_untested_gate_blocks_clearance (profile : GateProfile) (stage : GateStage)
    (huntested : profile stage = .untested) : ¬ Clears profile := by
  intro hclears
  have hstage := hclears stage
  simp [ClearedStatus, huntested] at hstage

end OpenDistillationFactory.HonestErrors
