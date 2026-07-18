/-
Shared vocabulary for the error landscape in Hard Materials, Honest Errors.
The seven constructors are axes, not severity ranks; a case may carry several.
-/
namespace OpenDistillationFactory.ErrorLandscape

inductive ErrorType where
  | T1 -- reference-method bias
  | T2 -- emulator / model-form error
  | T3 -- domain shift / coverage failure
  | T4 -- numerical / sampling error
  | T5 -- multiscale closure gap
  | T6 -- validation-data gap
  | T7 -- observability / experimental-reference uncertainty
  deriving Repr, DecidableEq, BEq

/-- A primary binding error and any compounding axes. -/
structure ErrorClassification where
  primary : ErrorType
  secondary : List ErrorType := []
  deriving Repr, DecidableEq, BEq

namespace ErrorClassification

/-- All tags, with the binding type first. This is nonempty by construction. -/
def tags (classification : ErrorClassification) : List ErrorType :=
  classification.primary :: classification.secondary

@[simp] theorem primary_mem_tags (classification : ErrorClassification) :
    classification.primary ∈ classification.tags := by
  simp [tags]

end ErrorClassification

/-- A source-preserving scalar or range. `value` remains lexical because the
nine emblems mix ranges, ratios, percentages, energies, doses, and timescales. -/
structure Quantity where
  label : String
  value : String
  unit : String
  deriving Repr, DecidableEq, BEq

/-- A heterogeneous magnitude with its exact reported quantities. -/
structure QuantifiedMagnitude where
  headline : String
  quantities : List Quantity
  deriving Repr, DecidableEq, BEq

/-- Location and bracket markers in the source report. -/
structure SourceCitation where
  document : String := "Hard Materials, Honest Errors"
  chapter : Nat
  location : String
  markers : List Nat
  verifiedAsOf : Option String := none
  deriving Repr, DecidableEq, BEq

/-- The intervention or explicitly missing capability attached to an error. -/
structure CorrectionLever where
  name : String
  intervention : String
  evidence : String
  deriving Repr, DecidableEq, BEq

inductive Readiness where
  | high
  | medium
  | low
  deriving Repr, DecidableEq, BEq

end OpenDistillationFactory.ErrorLandscape
