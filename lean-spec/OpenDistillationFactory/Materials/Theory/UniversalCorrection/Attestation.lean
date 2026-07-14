import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.RuntimeContract

/-!
# Scientific attestation at the runtime boundary

`checkRuntimeContract` validates scope identity, numeric semantics, interval
structure, implementation support, and precision.  Those are necessary
runtime checks, but they do not by themselves establish that the serialized
interval contains a physical residual.  This module keeps that empirical
claim separate and then composes the two layers.

A production evidence producer must supply either `AttestsValue` directly or
an `AttestsInterval` proof obtained from a verified outward-rounding/parser
refinement.  Only `ScientificAdmission` combines runtime admission with that
semantic evidence.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

namespace FixedMeasurement

/-- The encoded envelope contains one specified real value under its declared
numeric contract. -/
def AttestsValue (evidence : FixedMeasurement) (value : ℝ) : Prop :=
  evidence.envelope.Encloses evidence.numeric value

/-- The encoded envelope is an outward enclosure of a nonempty real source
interval. -/
def AttestsInterval (evidence : FixedMeasurement)
    (sourceLower sourceUpper : ℝ) : Prop :=
  evidence.envelope.OutwardEnclosure evidence.numeric sourceLower sourceUpper

/-- Midpoint of the decoded exact fixed-point endpoints. -/
noncomputable def decodedMidpoint (evidence : FixedMeasurement) : ℝ :=
  (FixedEnvelope.decodeRaw evidence.numeric evidence.envelope.lower +
      FixedEnvelope.decodeRaw evidence.numeric evidence.envelope.upper) / 2

/-- Half-width of the decoded exact fixed-point interval. -/
noncomputable def decodedRadius (evidence : FixedMeasurement) : ℝ :=
  (FixedEnvelope.decodeRaw evidence.numeric evidence.envelope.upper -
      FixedEnvelope.decodeRaw evidence.numeric evidence.envelope.lower) / 2

/-- A value attested by a well-formed fixed-point interval lies within its
decoded midpoint/half-width correction budget. -/
theorem error_to_decodedMidpoint_le_radius
    {evidence : FixedMeasurement} {value : ℝ}
    (hcontract : evidence.numeric.WellFormed)
    (hattests : evidence.AttestsValue value) :
    |value - evidence.decodedMidpoint| ≤ evidence.decodedRadius := by
  have hbounds :=
    (FixedEnvelope.encloses_iff_decode_bounds hcontract).mp hattests
  rw [abs_le]
  unfold decodedMidpoint decodedRadius
  constructor <;> linarith

end FixedMeasurement

/-- Full scientific authorization for one real residual: the runtime contract
is admissible and the exact envelope actually contains the residual. -/
def ScientificAdmission (policy : RuntimePolicy) (evidence : FixedMeasurement)
    (residualValue : ℝ) : Prop :=
  policy.Admissible evidence ∧ evidence.AttestsValue residualValue

/-- The executable runtime result plus a semantic attestation is exactly the
full scientific-admission proposition. -/
theorem checkRuntimeContract_admit_and_attests_iff
    (policy : RuntimePolicy) (evidence : FixedMeasurement) (residualValue : ℝ) :
    checkRuntimeContract policy evidence = .admit ∧
        evidence.AttestsValue residualValue ↔
      ScientificAdmission policy evidence residualValue := by
  rw [checkRuntimeContract_admit_iff]
  rfl

/-- A verified outward encoding supplies a value attestation for every point
in its real source interval; runtime admission then yields scientific
admission. -/
theorem scientificAdmission_of_outward
    {policy : RuntimePolicy} {evidence : FixedMeasurement}
    {sourceLower sourceUpper residualValue : ℝ}
    (hadmit : checkRuntimeContract policy evidence = .admit)
    (houtward : evidence.AttestsInterval sourceLower sourceUpper)
    (hvalue : sourceLower ≤ residualValue ∧ residualValue ≤ sourceUpper) :
    ScientificAdmission policy evidence residualValue := by
  have hadmissible :=
    (checkRuntimeContract_admit_iff policy evidence).mp hadmit
  have hnumeric : evidence.numeric.WellFormed := by
    rw [← hadmissible.1.2.1]
    exact hadmissible.1.2.2.2
  exact
    ⟨hadmissible,
      FixedEnvelope.encloses_of_outward hnumeric houtward hvalue⟩

/-- Subtracting the decoded midpoint from a model value is a certified
correction only after both runtime admission and residual attestation. -/
theorem corrected_value_error_le_decodedRadius
    {policy : RuntimePolicy} {evidence : FixedMeasurement}
    {modelValue referenceValue residualValue : ℝ}
    (hresidual : residualValue = modelValue - referenceValue)
    (hscientific : ScientificAdmission policy evidence residualValue) :
    |(modelValue - evidence.decodedMidpoint) - referenceValue| ≤
      evidence.decodedRadius := by
  have hnumeric : evidence.numeric.WellFormed := by
    rw [← hscientific.1.1.2.1]
    exact hscientific.1.1.2.2.2
  have hbound := evidence.error_to_decodedMidpoint_le_radius
    hnumeric hscientific.2
  have heq :
      (modelValue - evidence.decodedMidpoint) - referenceValue =
        residualValue - evidence.decodedMidpoint := by
    rw [hresidual]
    ring
  rw [heq]
  exact hbound

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
