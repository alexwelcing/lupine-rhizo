import Mathlib.Algebra.Order.Ring.Rat
import Mathlib.Data.Fintype.Card
import Mathlib.Data.Rat.Defs
import Mathlib.Tactic.DeriveFintype

/-! Typed error taxonomy from Hard Materials, Honest Errors. -/

namespace OpenDistillationFactory.HonestErrors

inductive ErrorAxis where
  | referenceMethod
  | emulatorModelForm
  | domainShift
  | numericalSampling
  | multiscaleClosure
  | validationData
  | observability
  deriving DecidableEq, Fintype, Repr

inductive Metric where
  | migrationBarrierMAE
  | adsorptionEnergyMUE
  | energyMAEPerAtom
  | densityMAPE
  | forceMAE
  | timescaleReach
  | doseQualification
  deriving DecidableEq, Repr

structure MetricValue (metric : Metric) where
  value : ℚ
  nonnegative : 0 ≤ value
  deriving DecidableEq, Repr

structure TypedObservation (axis : ErrorAxis) (metric : Metric) where
  magnitude : MetricValue metric
  sourceIds : List Nat
  asOfDate : String
  deriving Repr

theorem errorAxis_card : Fintype.card ErrorAxis = 7 := by decide

end OpenDistillationFactory.HonestErrors
