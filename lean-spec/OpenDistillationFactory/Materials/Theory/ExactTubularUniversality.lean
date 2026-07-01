import Mathlib.Analysis.InnerProductSpace.Basic
import Mathlib.Analysis.InnerProductSpace.Calculus
import Mathlib.Analysis.Calculus.FDeriv.Basic
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.Analysis.Normed.Module.FiniteDimension
import Mathlib.Topology.MetricSpace.Basic
import Mathlib.Data.Set.Function
import Mathlib.Tactic

/-! # Exact tubular universality (keystone paper skeleton)

Faithful formal skeleton of the keystone paper's `ErrorGeomData` / `exact_tubular_universality`
statement (A0–A5 regime).  This file supplies the *architecture* of the theorem: definitions of
the configuration-space error field, shared core manifold, radial profile, model perturbations,
high-error tube and boundary, reach, normal bundle, and tubular map.  The main statement is a
`def : Prop` so it can be stated without proof obligations; all supporting lemmas below are
provable trivialities.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.ExactTubularUniversality

open scoped RealInnerProductSpace

open Classical

section helpers

/-- Distance from a point `x` to a nonempty set `H` in Euclidean space.
If `H` is empty the value is defined as `0` to keep the function total. -/
noncomputable def distToSet {n : ℕ} (x : EuclideanSpace ℝ (Fin n))
    (H : Set (EuclideanSpace ℝ (Fin n))) : ℝ :=
  if _h : H.Nonempty then sInf ((fun y => ‖x - y‖) '' H) else 0

lemma distToSet_nonneg {n : ℕ} (x : EuclideanSpace ℝ (Fin n))
    (H : Set (EuclideanSpace ℝ (Fin n))) (hH : H.Nonempty) :
    0 ≤ distToSet x H := by
  unfold distToSet
  rw [dif_pos hH]
  apply Real.sInf_nonneg
  rintro r ⟨y, -, rfl⟩
  exact norm_nonneg _

/-- A chosen core parameter for a point of `H`, using the fact that `H = range φ`. -/
noncomputable def coreParam {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) (h : H) : EuclideanSpace ℝ (Fin d) :=
  Classical.choose (show ∃ p, φ p = h.val by
    let x := h.val
    have hmem : x ∈ H := h.2
    rw [hH] at hmem
    exact hmem)

/-- Tangent space to `H` at a point `h`, pulled back from the derivative of `φ`. -/
noncomputable def tangentSpace {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) (h : H) :
    Submodule ℝ (EuclideanSpace ℝ (Fin m)) :=
  LinearMap.range (fderiv ℝ φ (coreParam H φ hH h)).toLinearMap

/-- Normal space to `H` at a point `h`, as the orthogonal complement of the tangent space. -/
noncomputable def normalSpace {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) (h : H) :
    Submodule ℝ (EuclideanSpace ℝ (Fin m)) :=
  (tangentSpace H φ hH h).orthogonal

/-- Normal bundle of `H` inside the ambient Euclidean space. -/
def normalBundle {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) : Set (EuclideanSpace ℝ (Fin m) × EuclideanSpace ℝ (Fin m)) :=
  { pv | ∃ hh : pv.1 ∈ H, pv.2 ∈ normalSpace H φ hH ⟨pv.1, hh⟩ }

/-- Unit normal bundle of `H` (normal vectors of length one). -/
def unitNormalBundle {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) : Set (EuclideanSpace ℝ (Fin m) × EuclideanSpace ℝ (Fin m)) :=
  { pv ∈ normalBundle H φ hH | ‖pv.2‖ = 1 }

/-- The tubular map sends a core point and a normal vector to the ambient point `h + v`. -/
noncomputable def tubularMap {n : ℕ} : EuclideanSpace ℝ (Fin n) × EuclideanSpace ℝ (Fin n) →
    EuclideanSpace ℝ (Fin n) :=
  fun ⟨h, v⟩ => h + v

/-- `H` has reach at least `τ` if the tubular map is injective on normal vectors of length `< τ`. -/
def HasReach {m d : ℕ} (H : Set (EuclideanSpace ℝ (Fin m)))
    (φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m))
    (hH : H = Set.range φ) (τ : ℝ) : Prop :=
  0 < τ ∧ ∀ {p q}, p ∈ normalBundle H φ hH → q ∈ normalBundle H φ hH →
    ‖p.2‖ < τ → ‖q.2‖ < τ → tubularMap p = tubularMap q → p = q

/-- Positive reach is positive by definition. -/
lemma hasReach_pos {m d : ℕ} {H : Set (EuclideanSpace ℝ (Fin m))}
    {φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m)}
    {hH : H = Set.range φ} {τ : ℝ} (hτ : HasReach H φ hH τ) : 0 < τ :=
  hτ.1

/-- The normal bundle fibers are orthogonal to the corresponding tangent spaces. -/
lemma normalBundle_fiber_orthogonal {m d : ℕ} {H : Set (EuclideanSpace ℝ (Fin m))}
    {φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m)}
    {hH : H = Set.range φ} {pv : EuclideanSpace ℝ (Fin m) × EuclideanSpace ℝ (Fin m)}
    (hpv : pv ∈ normalBundle H φ hH) :
    ∃ hh : pv.1 ∈ H, ∀ (w : EuclideanSpace ℝ (Fin m)),
      w ∈ tangentSpace H φ hH ⟨pv.1, hh⟩ → inner (𝕜 := ℝ) pv.2 w = 0 := by
  rcases hpv with ⟨hh, hnv⟩
  use hh
  intro w hw
  simp [normalSpace, Submodule.mem_orthogonal'] at hnv
  exact hnv w hw

/-- The unit normal bundle sits inside the normal bundle. -/
lemma unitNormalBundle_subset_normalBundle {m d : ℕ}
    {H : Set (EuclideanSpace ℝ (Fin m))}
    {φ : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m)}
    {hH : H = Set.range φ} :
    unitNormalBundle H φ hH ⊆ normalBundle H φ hH := by
  intro pv hpv
  exact hpv.1

/-- The tubular map projects the zero normal vector back to the core point. -/
lemma tubularMap_zero {n : ℕ} (h : EuclideanSpace ℝ (Fin n)) :
    tubularMap ⟨h, 0⟩ = h := by
  simp [tubularMap]

/-- A light-weight predicate expressing that two subsets of normed vector spaces are
`C¹`-diffeomorphic: there exist mutually inverse `C¹` maps between them.  This is exactly the
notion used in the main universality statement. -/
def IsC1Diffeomorphic {E F : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
    [NormedAddCommGroup F] [NormedSpace ℝ F] (A : Set E) (B : Set F) : Prop :=
  ∃ (f : E → F) (g : F → E),
    Set.BijOn f A B ∧
    Set.LeftInvOn g f A ∧
    Set.RightInvOn g f B ∧
    ContDiffOn ℝ 1 f A ∧
    ContDiffOn ℝ 1 g B

end helpers


section error_geom_data

variable (M : Type*) (m d : ℕ)

/-- Error-geometry data for the keystone paper's exact theorem.

Components:
- `Omega`: configuration space (a subset of `ℝᵐ`).
- `H`: shared compact core manifold in configuration space.
- `phi`: a `C¹` embedding parametrizing `H`.
- `q model x`: scalarized error field `q_M(x)` for each model `M`.
- `a model`: positive model-specific amplitude.
- `psi`: common monotone radial profile, with an explicit inverse `psiInv`.
- `eta model`: model-specific perturbation of the error geometry.
- `L model`: Lipschitz constant of `eta model`.
- `tau_H`: a positive reach for `H`.
- `reach_condition`: the tubular map is injective on normal disks of radius `< tau_H`.

The fields are intentionally stated as hypotheses rather than derived facts, so this is a
skeleton that future proofs can discharge from the paper's assumptions A0–A5. -/
structure ErrorGeomData where
  Omega : Set (EuclideanSpace ℝ (Fin m))
  H : Set (EuclideanSpace ℝ (Fin m))
  phi : EuclideanSpace ℝ (Fin d) → EuclideanSpace ℝ (Fin m)
  H_eq_range : H = Set.range phi
  phi_injective : Function.Injective phi
  phi_contDiff : ContDiff ℝ 1 phi
  phi_immersion : ∀ p, Function.Injective (fderiv ℝ phi p)
  q : M → EuclideanSpace ℝ (Fin m) → ℝ
  a : M → ℝ
  psi : ℝ → ℝ
  psi_strictMono : StrictMono psi
  psi_zero : psi 0 = 0
  psiInv : ℝ → ℝ
  psiInv_spec : ∀ e, psi (psiInv e) = e
  eta : M → EuclideanSpace ℝ (Fin m) → ℝ
  L : M → ℝ
  eta_lipschitz : ∀ (model : M) (x y : EuclideanSpace ℝ (Fin m)),
    ‖eta model x - eta model y‖ ≤ L model * ‖x - y‖
  tau_H : ℝ
  tau_H_pos : 0 < tau_H
  reach_condition : HasReach H phi H_eq_range tau_H

end error_geom_data


section tube

variable {M : Type*} {m d : ℕ}

/-- High-error tube of radius `r` around the core `H`. -/
def highErrorTube (H : Set (EuclideanSpace ℝ (Fin m))) (r : ℝ) :
    Set (EuclideanSpace ℝ (Fin m)) :=
  { x | distToSet x H ≤ r }

/-- Boundary of the high-error tube at radius `r`. -/
def highErrorBoundary (H : Set (EuclideanSpace ℝ (Fin m))) (r : ℝ) :
    Set (EuclideanSpace ℝ (Fin m)) :=
  { x | distToSet x H = r }

/-- The high-error sublevel set of the scalarized error field `q_M`. -/
def highErrorSublevel (D : ErrorGeomData M m d) (model : M) (ε : ℝ) :
    Set (EuclideanSpace ℝ (Fin m)) :=
  { x | x ∈ D.Omega ∧ D.q model x ≤ ε }

/-- The radial threshold `r̄_M(ε)` obtained by inverting the common radial profile `ψ`. -/
noncomputable def radialThreshold (D : ErrorGeomData M m d) (model : M) (ε : ℝ) : ℝ :=
  D.psiInv (ε / D.a model)

/-- Nominal dimension of the high-error boundary (`m - 1`). -/
def boundaryDim (_D : ErrorGeomData M m d) : ℕ := m - 1

/-- The boundary lies inside the closed tube. -/
lemma boundary_subset_tube {H : Set (EuclideanSpace ℝ (Fin m))} {r : ℝ} :
    highErrorBoundary H r ⊆ highErrorTube H r := by
  intro x hx
  simp [highErrorBoundary, highErrorTube] at hx ⊢
  exact le_of_eq hx

/-- The nominal boundary dimension is `m - 1` by definition. -/
lemma boundaryDim_eq (_D : ErrorGeomData M m d) : boundaryDim _D = m - 1 := rfl

end tube


section theorem_statement

variable {M : Type*} {m d : ℕ}

/-- **Exact tubular universality** (keystone paper, A0–A5).

For every model `M` and error level `ε > 0`, the high-error sublevel set `{q_M ≤ ε}` equals a
tube of radius `r̄_M(ε)` around the shared core `H`; the boundary `Γ_{M,ε}` is `C¹`-diffeomorphic
to the unit normal bundle `S(NH)`; all model boundaries are pairwise `C¹`-diffeomorphic; and the
boundary has dimension `m - 1`.

This is stated as a `def` of type `Prop`, so it incurs no proof obligation.  The supporting
objects (`reach`, `normalBundle`, `tubularMap`, etc.) are defined above and the trivial lemmas
about them are proved. -/
def exact_tubular_universality (D : ErrorGeomData M m d) : Prop :=
  (∀ model : M, 0 < D.a model) →
  (∀ (model : M) (ε : ℝ), 0 < ε →
    let r := radialThreshold D model ε
    highErrorSublevel D model ε = highErrorTube D.H r ∧
    IsC1Diffeomorphic (highErrorBoundary D.H r)
                      (unitNormalBundle D.H D.phi D.H_eq_range) ∧
    boundaryDim D = m - 1) ∧
  (∀ (m₁ m₂ : M) (ε₁ ε₂ : ℝ), 0 < ε₁ → 0 < ε₂ →
    IsC1Diffeomorphic (highErrorBoundary D.H (radialThreshold D m₁ ε₁))
                      (highErrorBoundary D.H (radialThreshold D m₂ ε₂)))

end theorem_statement

end OpenDistillationFactory.Materials.Theory.ExactTubularUniversality
