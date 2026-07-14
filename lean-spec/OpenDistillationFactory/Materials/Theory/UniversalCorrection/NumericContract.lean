import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Lean.Elab.Tactic.Omega
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Gate
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Scope

/-!
# Versioned exact numeric ingestion

Runtime certificates must not silently identify an IEEE floating-point value
with the real numbers used by the scientific theorems.  This module specifies
the smaller, exact boundary consumed by the reference checker:

* values are signed integers interpreted at a positive integer scale;
* units, semantic convention, schema version, and rounding convention are
  part of the contract rather than ambient configuration;
* a `FixedEnvelope` denotes an outward enclosure, not a point estimate; and
* refinement is interval inclusion and therefore preserves every value already
  certified by the finer enclosure.

This module does not claim that a particular floating-point parser or sensor
produces an outward enclosure.  Such an implementation must establish the
`OutwardEnclosure` relation defined below.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- Rounding behavior declared by an encoded numeric payload. -/
inductive RoundingConvention where
  /-- Lower endpoints round down and upper endpoints round up. -/
  | outward
  /-- Round to the nearest representable fixed-point value. -/
  | nearest
  /-- Round toward zero. -/
  | towardZero
  deriving DecidableEq, Repr

/-- Schema version implemented by the current Lean reference checker. -/
def currentNumericSchemaVersion : Nat := 1

/-- Exact interpretation of a fixed-point payload.

`scale = 1000`, for example, means that the raw integer `1250` denotes
`1.250` in `units`.  Malformed contracts with zero scale remain representable
so the runtime gate can refuse them explicitly. -/
structure NumericContract where
  schemaVersion : Nat
  scale : Nat
  units : String
  semantics : String
  rounding : RoundingConvention
  deriving DecidableEq, Repr

namespace NumericContract

/-- The denominator of a fixed-point encoding must be strictly positive. -/
def WellFormed (contract : NumericContract) : Prop := 0 < contract.scale

instance wellFormedDecidable (contract : NumericContract) :
    Decidable contract.WellFormed :=
  inferInstanceAs (Decidable (0 < contract.scale))

/-- The current checker supports exactly its pinned schema and outward
rounding.  Other well-formed encodings are unsupported, not false. -/
def Supported (contract : NumericContract) : Prop :=
  contract.schemaVersion = currentNumericSchemaVersion ∧
    contract.rounding = .outward

instance supportedDecidable (contract : NumericContract) :
    Decidable contract.Supported :=
  inferInstanceAs
    (Decidable
      (contract.schemaVersion = currentNumericSchemaVersion ∧
        contract.rounding = .outward))

/-- Units and numeric semantics must agree exactly with the scientific scope.
No implicit unit conversion or convention aliasing occurs in the trusted gate.
-/
def ScopeCompatible (contract : NumericContract) (scope : Scope) : Prop :=
  contract.units = scope.units ∧
    contract.semantics = scope.numericSemantics

instance scopeCompatibleDecidable (contract : NumericContract) (scope : Scope) :
    Decidable (contract.ScopeCompatible scope) :=
  inferInstanceAs
    (Decidable
      (contract.units = scope.units ∧ contract.semantics = scope.numericSemantics))

@[simp] theorem wellFormed_iff (contract : NumericContract) :
    contract.WellFormed ↔ 0 < contract.scale := Iff.rfl

@[simp] theorem supported_iff (contract : NumericContract) :
    contract.Supported ↔
      contract.schemaVersion = currentNumericSchemaVersion ∧
        contract.rounding = .outward := Iff.rfl

@[simp] theorem scopeCompatible_iff (contract : NumericContract) (scope : Scope) :
    contract.ScopeCompatible scope ↔
      contract.units = scope.units ∧
        contract.semantics = scope.numericSemantics := Iff.rfl

end NumericContract

namespace FixedEnvelope

/-- An interval is structurally ordered. -/
def Ordered (envelope : FixedEnvelope) : Prop := envelope.lower ≤ envelope.upper

instance orderedDecidable (envelope : FixedEnvelope) : Decidable envelope.Ordered :=
  inferInstanceAs (Decidable (envelope.lower ≤ envelope.upper))

/-- Integer width in raw fixed-point ticks.  It is nonnegative for an ordered
envelope. -/
def width (envelope : FixedEnvelope) : Int := envelope.upper - envelope.lower

/-- Exact real value denoted by one raw integer under a numeric contract. -/
noncomputable def decodeRaw (contract : NumericContract) (raw : Int) : ℝ :=
  (raw : ℝ) / (contract.scale : ℝ)

/-- `envelope` contains `value` under the fixed-point interpretation.

The cross-multiplied definition keeps the primitive assurance relation exact
and division-free.  `encloses_iff_decode_bounds` below proves that it has the
usual endpoint interpretation whenever the scale is well formed. -/
def Encloses (envelope : FixedEnvelope) (contract : NumericContract)
    (value : ℝ) : Prop :=
  (envelope.lower : ℝ) ≤ (contract.scale : ℝ) * value ∧
    (contract.scale : ℝ) * value ≤ (envelope.upper : ℝ)

/-- A finer interval is included in a coarser interval. -/
def Refines (fine coarse : FixedEnvelope) : Prop :=
  coarse.lower ≤ fine.lower ∧ fine.upper ≤ coarse.upper

instance refinesDecidable (fine coarse : FixedEnvelope) :
    Decidable (fine.Refines coarse) :=
  inferInstanceAs
    (Decidable (coarse.lower ≤ fine.lower ∧ fine.upper ≤ coarse.upper))

/-- `encoded` is an outward enclosure of the entire nonempty real source
interval `[sourceLower, sourceUpper]`.  Source ordering is part of the
attestation, so an inverted (empty) interval cannot certify an encoding. -/
def OutwardEnclosure (encoded : FixedEnvelope) (contract : NumericContract)
    (sourceLower sourceUpper : ℝ) : Prop :=
  sourceLower ≤ sourceUpper ∧
    (encoded.lower : ℝ) ≤ (contract.scale : ℝ) * sourceLower ∧
      (contract.scale : ℝ) * sourceUpper ≤ (encoded.upper : ℝ)

@[simp] theorem ordered_iff (envelope : FixedEnvelope) :
    envelope.Ordered ↔ envelope.lower ≤ envelope.upper := Iff.rfl

@[simp] theorem width_eq (envelope : FixedEnvelope) :
    envelope.width = envelope.upper - envelope.lower := rfl

theorem width_nonneg {envelope : FixedEnvelope} (h : envelope.Ordered) :
    0 ≤ envelope.width := by
  unfold Ordered width at *
  omega

@[simp] theorem refines_refl (envelope : FixedEnvelope) :
    envelope.Refines envelope := ⟨le_rfl, le_rfl⟩

theorem Refines.trans {fine middle coarse : FixedEnvelope}
    (hfm : fine.Refines middle) (hmc : middle.Refines coarse) :
    fine.Refines coarse :=
  ⟨hmc.1.trans hfm.1, hfm.2.trans hmc.2⟩

theorem Refines.ordered {fine coarse : FixedEnvelope}
    (hrefines : fine.Refines coarse) (hfine : fine.Ordered) : coarse.Ordered := by
  unfold Refines Ordered at *
  omega

/-- Any value enclosed by a refinement is enclosed by the coarser interval. -/
theorem Refines.encloses {fine coarse : FixedEnvelope}
    {contract : NumericContract} {value : ℝ}
    (hrefines : fine.Refines coarse) (hencloses : fine.Encloses contract value) :
    coarse.Encloses contract value := by
  unfold Refines Encloses at *
  have hlower : (coarse.lower : ℝ) ≤ (fine.lower : ℝ) := by
    exact_mod_cast hrefines.1
  have hupper : (fine.upper : ℝ) ≤ (coarse.upper : ℝ) := by
    exact_mod_cast hrefines.2
  constructor
  · exact hlower.trans hencloses.1
  · exact hencloses.2.trans hupper

/-- Refinement cannot increase integer interval width. -/
theorem width_le_of_refines {fine coarse : FixedEnvelope}
    (hrefines : fine.Refines coarse) : fine.width ≤ coarse.width := by
  unfold Refines width at *
  omega

/-- Cross-multiplied enclosure agrees with the familiar decoded endpoint
bounds when the scale is positive. -/
theorem encloses_iff_decode_bounds
    {envelope : FixedEnvelope} {contract : NumericContract} {value : ℝ}
    (hcontract : contract.WellFormed) :
    envelope.Encloses contract value ↔
      decodeRaw contract envelope.lower ≤ value ∧
        value ≤ decodeRaw contract envelope.upper := by
  have hscale : (0 : ℝ) < (contract.scale : ℝ) := by
    exact_mod_cast hcontract
  unfold Encloses decodeRaw
  constructor
  · rintro ⟨hlower, hupper⟩
    constructor
    · apply (div_le_iff₀ hscale).2
      simpa [mul_comm] using hlower
    · apply (le_div_iff₀ hscale).2
      simpa [mul_comm] using hupper
  · rintro ⟨hlower, hupper⟩
    constructor
    · have := (div_le_iff₀ hscale).1 hlower
      simpa [mul_comm] using this
    · have := (le_div_iff₀ hscale).1 hupper
      simpa [mul_comm] using this

/-- Every point in a source interval is contained by a certified outward
encoding of that interval. -/
theorem encloses_of_outward
    {encoded : FixedEnvelope} {contract : NumericContract}
    {sourceLower sourceUpper value : ℝ}
    (hcontract : contract.WellFormed)
    (houtward : encoded.OutwardEnclosure contract sourceLower sourceUpper)
    (hvalue : sourceLower ≤ value ∧ value ≤ sourceUpper) :
    encoded.Encloses contract value := by
  have hscale : (0 : ℝ) ≤ (contract.scale : ℝ) := by
    have : (0 : ℝ) < (contract.scale : ℝ) := by exact_mod_cast hcontract
    exact this.le
  unfold OutwardEnclosure Encloses at *
  constructor
  · exact houtward.2.1.trans (mul_le_mul_of_nonneg_left hvalue.1 hscale)
  · exact (mul_le_mul_of_nonneg_left hvalue.2 hscale).trans houtward.2.2

/-- Replacing an outward enclosure by a coarser interval preserves the
outward-enclosure certificate. -/
theorem outward_of_refines
    {fine coarse : FixedEnvelope} {contract : NumericContract}
    {sourceLower sourceUpper : ℝ}
    (hrefines : fine.Refines coarse)
    (houtward : fine.OutwardEnclosure contract sourceLower sourceUpper) :
    coarse.OutwardEnclosure contract sourceLower sourceUpper := by
  unfold Refines OutwardEnclosure at *
  have hlower : (coarse.lower : ℝ) ≤ (fine.lower : ℝ) := by
    exact_mod_cast hrefines.1
  have hupper : (fine.upper : ℝ) ≤ (coarse.upper : ℝ) := by
    exact_mod_cast hrefines.2
  refine ⟨houtward.1, ?_, ?_⟩
  · exact hlower.trans houtward.2.1
  · exact houtward.2.2.trans hupper

end FixedEnvelope

/-- Complete exact numeric payload passed across the runtime boundary. -/
structure FixedMeasurement where
  scope : Scope
  numeric : NumericContract
  envelope : FixedEnvelope
  deriving DecidableEq, Repr

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
