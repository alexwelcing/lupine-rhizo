import Mathlib.Data.String.Basic

/-!
# Scope identities for universal correction

A correction claim is never unqualified: it is about one model artifact, one
reference method, one observable, one molecular context, one descriptor, one
unit convention, and one numerical interpretation.  `Scope` records those
choices as immutable data.  Later modules index predictions, residuals, and
anchors by a `Scope`, so values from different scopes cannot be combined by
accident.

The strings in these records are identifiers, not scientific assumptions.
Production certificates are expected to populate every digest with a
content-addressed hash and every convention field with a versioned name.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A versioned, content-addressed computational artifact. -/
structure ArtifactId where
  name : String
  version : String
  digest : String
  deriving DecidableEq, Repr

/-- The physical context that determines the meaning of an observable.

`species` is deliberately a list rather than a set: a certificate may retain
the canonical ordering used by its serialized configuration. -/
structure MolecularContext where
  species : List String
  charge : Int
  spinConvention : String
  boundaryConditions : String
  deriving DecidableEq, Repr

/-- Identity of a local/global environment representation and its metric. -/
structure DescriptorId where
  artifact : ArtifactId
  metricConvention : String
  deriving DecidableEq, Repr

/-- Complete semantic scope of one correction problem.

Equality of `Scope` is intentionally strict.  Even two scientifically similar
models are different scopes when their checkpoint, precision, reference
settings, descriptor metric, units, or numerical convention differs. -/
structure Scope where
  model : ArtifactId
  reference : ArtifactId
  observable : String
  context : MolecularContext
  descriptor : DescriptorId
  units : String
  numericSemantics : String
  deriving DecidableEq, Repr

/-- Explicit compatibility predicate used at serialization boundaries.

Inside Lean, dependent types usually enforce this equality directly. -/
def Compatible (left right : Scope) : Prop := left = right

instance compatibleDecidable (left right : Scope) : Decidable (Compatible left right) :=
  inferInstanceAs (Decidable (left = right))

@[simp] theorem compatible_iff_eq (left right : Scope) :
    Compatible left right ↔ left = right := Iff.rfl

@[simp] theorem compatible_refl (scope : Scope) : Compatible scope scope := rfl

theorem Compatible.symm {left right : Scope} (h : Compatible left right) :
    Compatible right left := Eq.symm h

theorem Compatible.trans {left middle right : Scope}
    (h₁ : Compatible left middle) (h₂ : Compatible middle right) :
    Compatible left right := Eq.trans h₁ h₂

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
