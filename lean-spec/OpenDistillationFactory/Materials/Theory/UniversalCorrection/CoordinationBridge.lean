import Mathlib.Data.Multiset.Basic
import OpenDistillationFactory.Materials.Theory.EnvironmentField
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Descriptor

/-!
# Coordination-field specialization

The existing environment error field is a concrete specialization of the
representation-agnostic correction interface.  Its descriptor is the multiset
of first-shell coordination numbers; the order of atoms is intentionally
discarded.  Both `ErrorField.fieldSum` and `MeasuredField.fieldSum` factor
through that descriptor, so the earlier family-transfer theorems are recovered
as descriptor-collision laws.

This bridge does **not** assert a global Lipschitz constant for the clamped
step fields.  Such a constant depends on a separately chosen metric and must be
validated per scope rather than inferred from monotonicity.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

open OpenDistillationFactory.Materials.Theory.EnvironmentField

/-- The coordination representation used by the existing error-field theory,
quotiented by permutation of atoms. -/
def coordinationMultisetDescriptor (scope : Scope) :
    Descriptor scope Config (Multiset ℕ) where
  encode := fun config => config

/-- Read an `ErrorField` on an unordered coordination signature. -/
def ErrorField.multisetFieldSum {cBulk : ℕ} (field : ErrorField cBulk)
    (signature : Multiset ℕ) : ℝ :=
  (signature.map field.P).sum

/-- Read a `MeasuredField` on an unordered coordination signature. -/
def MeasuredField.multisetFieldSum {cBulk : ℕ} (field : MeasuredField cBulk)
    (signature : Multiset ℕ) : ℝ :=
  (signature.map field.P).sum

@[simp] theorem coordinationMultiset_collision_iff
    {scope : Scope} {left right : Config} :
    (coordinationMultisetDescriptor scope).Collision left right ↔
      left.Perm right := by
  exact Multiset.coe_eq_coe

/-- Every directional coordination field factors exactly through the
permutation-invariant coordination descriptor. -/
theorem ErrorField.fieldSum_factorsThrough {scope : Scope} {cBulk : ℕ}
    (field : ErrorField cBulk) :
    Descriptor.FactorsThrough (coordinationMultisetDescriptor scope)
      (fun config => field.fieldSum config) := by
  refine ⟨ErrorField.multisetFieldSum field, ?_⟩
  intro config
  rfl

/-- The weaker measured tier has the same descriptor factorization, without
requiring monotone softening. -/
theorem MeasuredField.fieldSum_factorsThrough {scope : Scope} {cBulk : ℕ}
    (field : MeasuredField cBulk) :
    Descriptor.FactorsThrough (coordinationMultisetDescriptor scope)
      (fun config => field.fieldSum config) := by
  refine ⟨MeasuredField.multisetFieldSum field, ?_⟩
  intro config
  rfl

/-- Descriptor equality recovers the existing directional-field transfer law. -/
theorem ErrorField.fieldSum_eq_of_descriptor_collision
    {scope : Scope} {cBulk : ℕ} (field : ErrorField cBulk)
    {left right : Config}
    (hcollision : (coordinationMultisetDescriptor scope).Collision left right) :
    field.fieldSum left = field.fieldSum right := by
  exact field.fieldSum_transfer left right
    (coordinationMultiset_collision_iff.mp hcollision)

/-- Descriptor equality also recovers transfer at the measured tier. -/
theorem MeasuredField.fieldSum_eq_of_descriptor_collision
    {scope : Scope} {cBulk : ℕ} (field : MeasuredField cBulk)
    {left right : Config}
    (hcollision : (coordinationMultisetDescriptor scope).Collision left right) :
    field.fieldSum left = field.fieldSum right := by
  exact field.fieldSum_transfer left right
    (coordinationMultiset_collision_iff.mp hcollision)

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
