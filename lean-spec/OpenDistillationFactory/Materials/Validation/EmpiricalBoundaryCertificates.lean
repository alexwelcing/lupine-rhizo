import Mathlib.Tactic.NormNum
import OpenDistillationFactory.Materials.Theory.UniversalCorrection
import OpenDistillationFactory.Materials.Validation.UniversalCorrectionCertificates

/-!
# Executable empirical-boundary certificates

These exact fixtures exercise the second universal-correction milestone:
versioned fixed-point ingestion, every composite runtime-gate outcome,
finite sampled diagnostics, scheduled-validation drift, and normed observable
correction.  They are regression certificates for semantics, not empirical
claims about a material or production model.
-/

namespace OpenDistillationFactory.Materials.Validation.EmpiricalBoundaryCertificates

open OpenDistillationFactory.Materials.Theory.UniversalCorrection
open OpenDistillationFactory.Materials.Validation.UniversalCorrectionCertificates

/-! ## Versioned numeric and runtime contracts -/

def exactNumericContract : NumericContract where
  schemaVersion := currentNumericSchemaVersion
  scale := 1000
  units := fixtureScope.units
  semantics := fixtureScope.numericSemantics
  rounding := .outward

def runtimePolicy : RuntimePolicy where
  scope := fixtureScope
  numeric := exactNumericContract
  tolerance := 5

def admittedMeasurement : FixedMeasurement where
  scope := fixtureScope
  numeric := exactNumericContract
  envelope := { lower := 100, upper := 104 }

def inconsistentMeasurement : FixedMeasurement where
  scope := fixtureScope
  numeric := exactNumericContract
  envelope := { lower := 105, upper := 104 }

def wideMeasurement : FixedMeasurement where
  scope := fixtureScope
  numeric := exactNumericContract
  envelope := { lower := 100, upper := 110 }

def mismatchedScope : Scope :=
  { fixtureScope with observable := "force" }

def mismatchedMeasurement : FixedMeasurement where
  scope := mismatchedScope
  numeric := exactNumericContract
  envelope := { lower := 100, upper := 104 }

def schemaTwoNumericContract : NumericContract :=
  { exactNumericContract with schemaVersion := 2 }

def schemaTwoPolicy : RuntimePolicy :=
  { runtimePolicy with numeric := schemaTwoNumericContract }

def schemaTwoMeasurement : FixedMeasurement :=
  { admittedMeasurement with numeric := schemaTwoNumericContract }

def nearestNumericContract : NumericContract :=
  { exactNumericContract with rounding := .nearest }

def nearestPolicy : RuntimePolicy :=
  { runtimePolicy with numeric := nearestNumericContract }

def nearestMeasurement : FixedMeasurement :=
  { admittedMeasurement with numeric := nearestNumericContract }

def zeroScaleNumericContract : NumericContract :=
  { exactNumericContract with scale := 0 }

def zeroScalePolicy : RuntimePolicy :=
  { runtimePolicy with numeric := zeroScaleNumericContract }

def zeroScaleMeasurement : FixedMeasurement :=
  { admittedMeasurement with numeric := zeroScaleNumericContract }

theorem runtime_contract_admits :
    checkRuntimeContract runtimePolicy admittedMeasurement = .admit := by
  decide

theorem runtime_contract_refuses_scope_mismatch :
    checkRuntimeContract runtimePolicy mismatchedMeasurement =
      .refuse .incompatibleContract := by
  decide

theorem runtime_contract_refuses_zero_scale :
    checkRuntimeContract zeroScalePolicy zeroScaleMeasurement =
      .refuse .incompatibleContract := by
  decide

theorem runtime_contract_refuses_inverted_interval :
    checkRuntimeContract runtimePolicy inconsistentMeasurement =
      .refuse .inconsistentEnvelope := by
  decide

theorem runtime_contract_indeterminate_schema :
    checkRuntimeContract schemaTwoPolicy schemaTwoMeasurement =
      .indeterminate .unsupportedSchema := by
  decide

theorem runtime_contract_indeterminate_rounding :
    checkRuntimeContract nearestPolicy nearestMeasurement =
      .indeterminate .unsupportedRounding := by
  decide

theorem runtime_contract_indeterminate_width :
    checkRuntimeContract runtimePolicy wideMeasurement =
      .indeterminate .widthTooLarge := by
  decide

theorem runtime_contract_is_fail_closed :
    correctionAllowed (checkRuntimeContract runtimePolicy wideMeasurement) = false := by
  rw [runtime_contract_indeterminate_width]
  rfl

/-! ## Outward enclosure and refinement -/

def outwardEnvelope : FixedEnvelope where
  lower := 1249
  upper := 1251

theorem numeric_contract_is_well_formed : exactNumericContract.WellFormed := by
  norm_num [NumericContract.WellFormed, exactNumericContract]

theorem exact_outward_enclosure :
    outwardEnvelope.OutwardEnclosure exactNumericContract
      (12499 / 10000 : ℝ) (12501 / 10000 : ℝ) := by
  norm_num [FixedEnvelope.OutwardEnclosure, outwardEnvelope, exactNumericContract]

theorem outward_enclosure_contains_midpoint :
    outwardEnvelope.Encloses exactNumericContract (5 / 4 : ℝ) := by
  apply FixedEnvelope.encloses_of_outward numeric_contract_is_well_formed
    exact_outward_enclosure
  constructor <;> norm_num

def outwardMeasurement : FixedMeasurement where
  scope := fixtureScope
  numeric := exactNumericContract
  envelope := outwardEnvelope

/-- Structural runtime admission and a verified outward encoding jointly
certify the real residual; neither premise is silently inferred from the
other. -/
theorem outward_measurement_is_scientifically_admitted :
    ScientificAdmission runtimePolicy outwardMeasurement (5 / 4 : ℝ) := by
  apply scientificAdmission_of_outward
  · decide
  · exact exact_outward_enclosure
  · constructor <;> norm_num

/-- The scientifically admitted residual makes midpoint correction exact in
this fixture and therefore satisfies the decoded interval budget. -/
theorem outward_measurement_correction_is_bounded :
    |((13 / 4 : ℝ) - outwardMeasurement.decodedMidpoint) - 2| ≤
      outwardMeasurement.decodedRadius := by
  apply corrected_value_error_le_decodedRadius
    (policy := runtimePolicy) (evidence := outwardMeasurement)
    (residualValue := (5 / 4 : ℝ))
  · norm_num
  · exact outward_measurement_is_scientifically_admitted

def refinedEnvelope : FixedEnvelope where
  lower := 101
  upper := 103

theorem refined_measurement_remains_admissible :
    runtimePolicy.Admissible
      { admittedMeasurement with envelope := refinedEnvelope } := by
  apply admissible_of_refinement
    (policy := runtimePolicy) (coarse := admittedMeasurement)
  · exact (checkRuntimeContract_admit_iff runtimePolicy admittedMeasurement).mp
      runtime_contract_admits
  · norm_num [FixedEnvelope.Refines, refinedEnvelope, admittedMeasurement]
  · norm_num [FixedEnvelope.Ordered, refinedEnvelope]

/-! ## Exact finite sampled diagnostics -/

def acceptedPair : FixedPairObservation where
  leftResidual := 100
  rightResidual := 104
  descriptorDistance := 2

def rejectedPair : FixedPairObservation where
  leftResidual := 100
  rightResidual := 105
  descriptorDistance := 2

def collidingPair : FixedPairObservation where
  leftResidual := 100
  rightResidual := 101
  descriptorDistance := 0

theorem sampled_pair_accepted : acceptedPair.check 2 = true := by
  decide

theorem sampled_pair_rejected : rejectedPair.check 2 = false := by
  decide

theorem sampled_collision_rejected_for_every_factor (factor : Nat) :
    collidingPair.check factor = false := by
  apply FixedPairObservation.zero_distance_collision_rejected
  · rfl
  · decide

theorem sampled_list_reports_counterexample :
    checkFixedSampledLipschitz 2 [acceptedPair, rejectedPair] = false := by
  decide

/-! ## Scheduled validation -/

def linearTrajectory (step : Nat) : ℝ := step

def trajectoryResidual : ResidualField fixtureScope ℝ ℝ := id

theorem trajectory_residual_lipschitz :
    LipschitzResidual 1 trajectoryResidual := by
  constructor
  · norm_num
  · intro x y
    simp [trajectoryResidual, Real.dist_eq]

theorem linear_trajectory_step_bound :
    PerStepDriftBound linearTrajectory 1 := by
  constructor
  · norm_num
  · intro step
    rw [Real.dist_eq]
    norm_num [linearTrajectory]

def trajectoryCheckpointAnchor : Anchor fixtureScope ℝ :=
  Anchor.exact 0 0

theorem trajectory_checkpoint_contains :
    trajectoryCheckpointAnchor.Contains trajectoryResidual := by
  simp [trajectoryCheckpointAnchor, trajectoryResidual]

/-- A five-step validation period safely covers the third intermediate step. -/
theorem scheduled_validation_covers_intermediate_step :
    |trajectoryResidual (linearTrajectory (0 + 3)) -
        (trajectoryCheckpointAnchor.lower + trajectoryCheckpointAnchor.upper) / 2| ≤
      1 * ((5 : ℝ) * 1) + trajectoryCheckpointAnchor.width / 2 := by
  apply checkpoint_midpoint_error_within_period_le
    trajectory_residual_lipschitz linear_trajectory_step_bound
    trajectoryCheckpointAnchor trajectory_checkpoint_contains 0 3 5
  · norm_num
  · norm_num [trajectoryCheckpointAnchor, linearTrajectory, Anchor.exact]

/-! ## Normed observables -/

def normedObservableResidual : ResidualField fixtureScope ℝ ℝ :=
  fun _ => 1

def normedObservableAnchor : ResidualBall fixtureScope ℝ ℝ where
  point := 0
  center := 1
  radius := 0
  radius_nonneg := le_rfl

theorem normed_observable_anchor_contains :
    normedObservableAnchor.Contains normedObservableResidual := by
  simp [ResidualBall.Contains, normedObservableAnchor, normedObservableResidual]

theorem normed_observable_lipschitz :
    NormLipschitzResidual 0 normedObservableResidual := by
  constructor
  · norm_num
  · intro x y
    simp [normedObservableResidual]

theorem normed_observable_is_enclosed :
    ‖normedObservableResidual 7 - normedObservableAnchor.center‖ ≤
      normedObservableAnchor.propagatedRadius 0 7 :=
  ResidualBall.residual_mem_propagated_ball
    normed_observable_anchor_contains normed_observable_lipschitz

end OpenDistillationFactory.Materials.Validation.EmpiricalBoundaryCertificates
