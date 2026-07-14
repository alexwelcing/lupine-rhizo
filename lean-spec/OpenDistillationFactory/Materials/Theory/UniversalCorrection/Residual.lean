import Mathlib.Algebra.Group.Basic
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Scope

/-!
# Scoped model residuals

The correction target is the residual `model - reference`, not an unscoped
universal field.  Both predictions carry the same phantom `Scope`; attempting
to subtract predictions with different scopes is therefore a type error.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A prediction function whose meaning is fixed by `scope`. -/
structure Prediction (scope : Scope) (X Y : Type*) where
  eval : X → Y

/-- A residual field over inputs `X` with values in `Y`, indexed by scope. -/
abbrev ResidualField (_scope : Scope) (X Y : Type*) := X → Y

/-- Pointwise residual `model - reference` within one semantic scope. -/
def residual {scope : Scope} {X Y : Type*} [Sub Y]
    (model reference : Prediction scope X Y) : ResidualField scope X Y :=
  fun x => model.eval x - reference.eval x

@[simp] theorem residual_apply {scope : Scope} {X Y : Type*} [Sub Y]
    (model reference : Prediction scope X Y) (x : X) :
    residual model reference x = model.eval x - reference.eval x := rfl

/-- The residual reconstructs the model value from the reference value. -/
theorem residual_add_reference {scope : Scope} {X Y : Type*} [AddGroup Y]
    (model reference : Prediction scope X Y) (x : X) :
    residual model reference x + reference.eval x = model.eval x := by
  simp [residual]

/-- A prediction has zero residual against itself. -/
@[simp] theorem residual_self {scope : Scope} {X Y : Type*} [AddGroup Y]
    (prediction : Prediction scope X Y) (x : X) :
    residual prediction prediction x = 0 := by
  simp [residual]

/-- At a point, the residual vanishes exactly when model and reference agree. -/
theorem residual_eq_zero_iff {scope : Scope} {X Y : Type*} [AddGroup Y]
    (model reference : Prediction scope X Y) (x : X) :
    residual model reference x = 0 ↔ model.eval x = reference.eval x := by
  constructor
  · intro hzero
    change model.eval x - reference.eval x = 0 at hzero
    calc
      model.eval x =
          (model.eval x - reference.eval x) + reference.eval x :=
        (sub_add_cancel (model.eval x) (reference.eval x)).symm
      _ = 0 + reference.eval x := by rw [hzero]
      _ = reference.eval x := zero_add _
  · intro heq
    rw [residual_apply, heq]
    exact sub_self _

/-- Reversing model and reference negates the residual. -/
theorem residual_swap {scope : Scope} {X Y : Type*} [AddGroup Y]
    (model reference : Prediction scope X Y) (x : X) :
    residual reference model x = -residual model reference x := by
  simp [residual]

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
