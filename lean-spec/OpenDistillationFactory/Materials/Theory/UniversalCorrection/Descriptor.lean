import Mathlib.Topology.MetricSpace.Pseudo.Defs
import Mathlib.Tactic.Linarith
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Residual

/-!
# Representation-agnostic environment descriptors

`Descriptor` deliberately does not prescribe coordination number, Wyckoff
data, SOAP, ACE, or a learned embedding.  It is a scoped map into a feature
space.  A pseudometric on that feature space induces the distance used by a
correction certificate; pseudometrics naturally identify symmetry-equivalent
representations.

The collision theorem at the end records an important refusal condition: if
two configurations have the same descriptor but distinct residuals, no finite
Lipschitz correction can be justified through that descriptor.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A scoped representation of configurations as feature values. -/
structure Descriptor (_scope : Scope) (Config Feature : Type*) where
  encode : Config → Feature

namespace Descriptor

/-- Distance between two configurations induced by their encoded features. -/
def distance {scope : Scope} {Config Feature : Type*} [PseudoMetricSpace Feature]
    (descriptor : Descriptor scope Config Feature) (x y : Config) : ℝ :=
  dist (descriptor.encode x) (descriptor.encode y)

@[simp] theorem distance_self {scope : Scope} {Config Feature : Type*}
    [PseudoMetricSpace Feature] (descriptor : Descriptor scope Config Feature)
    (x : Config) : descriptor.distance x x = 0 := by
  simp [distance]

theorem distance_nonneg {scope : Scope} {Config Feature : Type*}
    [PseudoMetricSpace Feature] (descriptor : Descriptor scope Config Feature)
    (x y : Config) : 0 ≤ descriptor.distance x y :=
  dist_nonneg

theorem distance_comm {scope : Scope} {Config Feature : Type*}
    [PseudoMetricSpace Feature] (descriptor : Descriptor scope Config Feature)
    (x y : Config) : descriptor.distance x y = descriptor.distance y x :=
  dist_comm _ _

theorem distance_triangle {scope : Scope} {Config Feature : Type*}
    [PseudoMetricSpace Feature] (descriptor : Descriptor scope Config Feature)
    (x y z : Config) :
    descriptor.distance x z ≤ descriptor.distance x y + descriptor.distance y z :=
  dist_triangle _ _ _

/-- A descriptor is invariant under a supplied family of transformations. -/
def InvariantUnder {scope : Scope} {Config Feature Transform : Type*}
    (descriptor : Descriptor scope Config Feature)
    (act : Transform → Config → Config) : Prop :=
  ∀ transformation x,
    descriptor.encode (act transformation x) = descriptor.encode x

/-- Two configurations collide when the descriptor cannot distinguish them. -/
def Collision {scope : Scope} {Config Feature : Type*}
    (descriptor : Descriptor scope Config Feature) (x y : Config) : Prop :=
  descriptor.encode x = descriptor.encode y

/-- A residual field factors through a descriptor when some function on the
feature space reproduces it exactly.  This is the representation-level claim
that the descriptor contains all information needed by the residual. -/
def FactorsThrough {scope : Scope} {Config Feature Output : Type*}
    (descriptor : Descriptor scope Config Feature)
    (field : ResidualField scope Config Output) : Prop :=
  ∃ readout : Feature → Output, ∀ x, field x = readout (descriptor.encode x)

@[simp] theorem collision_refl {scope : Scope} {Config Feature : Type*}
    (descriptor : Descriptor scope Config Feature) (x : Config) :
    descriptor.Collision x x := rfl

theorem Collision.symm {scope : Scope} {Config Feature : Type*}
    {descriptor : Descriptor scope Config Feature} {x y : Config}
    (h : descriptor.Collision x y) : descriptor.Collision y x := Eq.symm h

theorem Collision.distance_eq_zero {scope : Scope} {Config Feature : Type*}
    [PseudoMetricSpace Feature] {descriptor : Descriptor scope Config Feature}
    {x y : Config} (h : descriptor.Collision x y) :
    descriptor.distance x y = 0 := by
  change descriptor.encode x = descriptor.encode y at h
  rw [distance, h]
  exact dist_self _

/-- **Descriptor-collision factorization obstruction.** If two configurations
collide in feature space but have distinct residuals, the residual cannot be a
function of the descriptor alone. -/
theorem collision_obstructs_factorization
    {scope : Scope} {Config Feature Output : Type*}
    {descriptor : Descriptor scope Config Feature}
    {field : ResidualField scope Config Output} {x y : Config}
    (hcollision : descriptor.Collision x y) (hresidual : field x ≠ field y) :
    ¬ FactorsThrough descriptor field := by
  rintro ⟨readout, hreadout⟩
  apply hresidual
  rw [hreadout x, hreadout y, hcollision]

/-- A residual field is `L`-Lipschitz through a descriptor when feature
distance controls residual distance.  The nonnegativity of `L` is retained in
the predicate so certificates cannot silently use a negative constant. -/
def DescriptorLipschitz {scope : Scope} {Config Feature Output : Type*}
    [PseudoMetricSpace Feature] [PseudoMetricSpace Output]
    (descriptor : Descriptor scope Config Feature)
    (field : ResidualField scope Config Output) (L : ℝ) : Prop :=
  0 ≤ L ∧ ∀ x y,
    dist (field x) (field y) ≤ L * descriptor.distance x y

/-- A Lipschitz residual has zero residual distance at every descriptor
collision. -/
theorem DescriptorLipschitz.collision_distance_eq_zero
    {scope : Scope} {Config Feature Output : Type*}
    [PseudoMetricSpace Feature] [PseudoMetricSpace Output]
    {descriptor : Descriptor scope Config Feature}
    {field : ResidualField scope Config Output} {L : ℝ}
    (hL : DescriptorLipschitz descriptor field L) {x y : Config}
    (hxy : descriptor.Collision x y) :
    dist (field x) (field y) = 0 := by
  apply le_antisymm
  · have hbound := hL.2 x y
    rw [hxy.distance_eq_zero] at hbound
    simpa using hbound
  · exact dist_nonneg

/-- **Descriptor-collision obstruction.** If equal descriptor values hide a
strictly positive residual separation, no finite Lipschitz certificate through
that descriptor exists. -/
theorem collision_obstructs_lipschitz
    {scope : Scope} {Config Feature Output : Type*}
    [PseudoMetricSpace Feature] [PseudoMetricSpace Output]
    {descriptor : Descriptor scope Config Feature}
    {field : ResidualField scope Config Output} {x y : Config}
    (hcollision : descriptor.Collision x y)
    (hseparated : 0 < dist (field x) (field y)) :
    ¬ ∃ L : ℝ, DescriptorLipschitz descriptor field L := by
  rintro ⟨L, hL⟩
  have hzero := hL.collision_distance_eq_zero hcollision
  linarith

end Descriptor

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
