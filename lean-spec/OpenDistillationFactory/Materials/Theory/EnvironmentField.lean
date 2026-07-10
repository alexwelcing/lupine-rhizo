import Mathlib.Data.Real.Basic
import Mathlib.Order.Monotone.Basic
import Mathlib.Algebra.Order.BigOperators.Group.List
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# The Environment Error Field: first-shell coordination decomposition of uMLIP error

Formal core of the climate-series program ("A Field, Not a Neural Net"): the
systematic energy error of a universal machine-learning interatomic potential
(uMLIP) is not noise — it is a *field over local atomic environments*,

    E_model − E_ref ≈ Σᵢ P(cᵢ),

where `cᵢ` is the first-shell coordination number of atom `i`, the field
vanishes at the bulk coordination (`P cBulk = 0`, e.g. `cBulk = 12` for fcc),
is non-positive (*systematic softening*: under-coordinated environments are
predicted too stable), and decays monotonically toward the bulk. The runtime
correction is the additive inverse, `E_corr = −Σᵢ P(cᵢ)`.

This module proves the structural laws of that field, each of which is a
physical claim of the platform:

1. `fieldSum_nonpos` — softening at the configuration level: the model
   underestimates every configuration's energy (`model_underestimates`).
2. `fieldSum_bulk` / `corrected_bulk_invariant` — the correction vanishes
   identically on bulk configurations: lattice constants are untouched.
3. `corrected_exact` — the closure law: when the error is exactly
   field-decomposable, runtime correction recovers the reference energy.
4. `fieldSum_transfer` — the family-transfer law: configurations with the same
   coordination multiset receive identical corrections, which is why one
   measured spline transfers across a crystal-structure family (fcc metals,
   the Li–M–Cl close-packed halide family, isostructural MOF nodes).
5. `fieldSum_mono` — the dominance law: pointwise-lower coordination gives a
   lower (more negative) field sum. This is the engine behind provable
   migration-barrier underestimation (`Theory.BarrierArrhenius`).
6. `abs_fieldSum_le` — the boundedness law: the correction magnitude is
   bounded by (atom count) × (field sup); the correction is a *bounded,
   measured* perturbation, not a free re-fit.
7. `affine_continuation_unique` — the blind-prediction law: an affine
   continuation of the field below the lowest anchors has zero adjustable
   parameters; two anchor values determine the blind value. This is the
   formal content of "the (110) surface energy is predicted blind".

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.EnvironmentField

/-- A local atomic configuration, abstracted as the list of first-shell
coordination numbers of its atoms. Order carries no physics (see
`fieldSum_transfer`); a list is used so evidence generators can bind
configurations directly. -/
abbrev Config := List ℕ

/-- The environment error field of one (model, material) cell.

`P c` is the measured per-atom signed energy error contributed by an atom with
first-shell coordination `c`. The three structure fields encode the measured
softening geometry of uMLIPs (Deng et al., npj Comput. Mater. 11, 9 (2025)):

* `bulk_anchor` — the field is pinned to zero at (and above) the bulk
  coordination; uMLIPs are accurate in the bulk they were trained on.
* `softening` — under-coordinated environments are predicted too stable:
  the signed error is never positive.
* `mono` — the error decays monotonically as coordination approaches bulk. -/
structure ErrorField (cBulk : ℕ) where
  /-- Measured per-atom signed error as a function of coordination number. -/
  P : ℕ → ℝ
  /-- The field vanishes at and above the bulk coordination. -/
  bulk_anchor : ∀ c, cBulk ≤ c → P c = 0
  /-- Systematic softening: the per-atom signed error is non-positive. -/
  softening : ∀ c, P c ≤ 0
  /-- The error is monotone non-decreasing in coordination (decays to zero). -/
  mono : Monotone P

namespace ErrorField

variable {cBulk : ℕ} (F : ErrorField cBulk)

/-- The field-predicted systematic energy error of a configuration:
`Σᵢ P(cᵢ)`. This is the quantity the runtime correction subtracts. -/
def fieldSum (cfg : Config) : ℝ := (cfg.map F.P).sum

/-- The runtime-corrected energy: `E_model + E_corr` with
`E_corr = −Σᵢ P(cᵢ)`. -/
def corrected (eModel : ℝ) (cfg : Config) : ℝ := eModel - F.fieldSum cfg

@[simp] theorem fieldSum_nil : F.fieldSum [] = 0 := rfl

theorem fieldSum_cons (c : ℕ) (cfg : Config) :
    F.fieldSum (c :: cfg) = F.P c + F.fieldSum cfg := by
  simp [fieldSum]

/-- **Softening at the configuration level.** The field-predicted error of any
configuration is non-positive: a softened potential never overestimates the
energy of a defect structure. -/
theorem fieldSum_nonpos (cfg : Config) : F.fieldSum cfg ≤ 0 := by
  induction cfg with
  | nil => simp
  | cons c cfg ih =>
    rw [fieldSum_cons]
    have hc := F.softening c
    linarith

/-- **Bulk invariance.** Every atom at (or above) bulk coordination means zero
field error: the field cannot perturb the bulk crystal. -/
theorem fieldSum_bulk (cfg : Config) (h : ∀ c ∈ cfg, cBulk ≤ c) :
    F.fieldSum cfg = 0 := by
  induction cfg with
  | nil => simp
  | cons c cfg ih =>
    rw [fieldSum_cons, F.bulk_anchor c (h c List.mem_cons_self),
      ih fun c' hc' => h c' (List.mem_cons_of_mem c hc')]
    ring

/-- **The closure law.** If a model's energy error is exactly
field-decomposable, the runtime correction recovers the reference energy
exactly. This is the formal statement behind "the fitted observables recover
exactly in closure tests". -/
theorem corrected_exact (eModel eRef : ℝ) (cfg : Config)
    (h : eModel = eRef + F.fieldSum cfg) :
    F.corrected eModel cfg = eRef := by
  unfold corrected
  linarith

/-- **Bulk observables are untouched by correction.** Lattice constants and
other all-bulk quantities pass through the correction unchanged — the formal
content of "bulk lattice constants are unchanged, because the correction
vanishes identically at c = 12". -/
theorem corrected_bulk_invariant (eModel : ℝ) (cfg : Config)
    (h : ∀ c ∈ cfg, cBulk ≤ c) :
    F.corrected eModel cfg = eModel := by
  unfold corrected
  rw [F.fieldSum_bulk cfg h]
  ring

/-- **Softening ⇒ underestimation.** A field-decomposable model never
overestimates a configuration's energy. Surface energies, vacancy formation
energies, and migration barriers computed from such a model are biased low —
the uMLIP failure mode shared by all five climate-series material classes. -/
theorem model_underestimates (eModel eRef : ℝ) (cfg : Config)
    (h : eModel = eRef + F.fieldSum cfg) :
    eModel ≤ eRef := by
  have := F.fieldSum_nonpos cfg
  linarith

/-- **The family-transfer law.** Two configurations with the same coordination
multiset receive identical field corrections, regardless of which material in
a crystal-structure family they come from. This is why the spline measured on
one member (e.g. Li₂ZrCl₆) transfers across the family (the Li–M–Cl
close-packed anion sublattice) without new oracle calls. -/
theorem fieldSum_transfer (cfg₁ cfg₂ : Config) (h : cfg₁.Perm cfg₂) :
    F.fieldSum cfg₁ = F.fieldSum cfg₂ :=
  List.Perm.sum_eq (h.map F.P)

/-- Corrections agree on same-signature configurations (transfer, stated for
the corrected energies). -/
theorem corrected_transfer (eModel : ℝ) (cfg₁ cfg₂ : Config) (h : cfg₁.Perm cfg₂) :
    F.corrected eModel cfg₁ = F.corrected eModel cfg₂ := by
  unfold corrected
  rw [F.fieldSum_transfer cfg₁ cfg₂ h]

/-- **The dominance law.** If one configuration is pointwise at most as
coordinated as another (atom by atom, under a matching), its field sum is at
most the other's: removing coordination can only deepen the softening error.
This drives the barrier-underestimation theorem in
`Theory.BarrierArrhenius`. -/
theorem fieldSum_mono (cfg₁ cfg₂ : Config)
    (h : List.Forall₂ (· ≤ ·) cfg₁ cfg₂) :
    F.fieldSum cfg₁ ≤ F.fieldSum cfg₂ := by
  induction h with
  | nil => simp
  | @cons a b l₁ l₂ hab _ ih =>
    rw [fieldSum_cons, fieldSum_cons]
    exact add_le_add (F.mono hab) ih

/-- **The boundedness law.** The correction magnitude is bounded by the atom
count times the field's sup: the runtime correction is a bounded, measured
perturbation of the uMLIP, never an unconstrained re-fit. -/
theorem abs_fieldSum_le (cfg : Config) (M : ℝ) (hM : ∀ c, |F.P c| ≤ M) :
    |F.fieldSum cfg| ≤ cfg.length * M := by
  induction cfg with
  | nil => simp
  | cons c cfg ih =>
    rw [fieldSum_cons]
    calc |F.P c + F.fieldSum cfg| ≤ |F.P c| + |F.fieldSum cfg| := abs_add_le _ _
      _ ≤ M + cfg.length * M := add_le_add (hM c) ih
      _ = (c :: cfg).length * M := by
          simp only [List.length_cons]
          push_cast
          ring

end ErrorField

/-- **The blind-prediction law.** An affine continuation of the field below the
lowest anchors carries zero adjustable parameters: any two affine maps that
agree at two distinct anchor coordinations (here `x₀` and `x₀ + 1`, e.g. the
(100) anchor c = 8 and the (111) anchor c = 9) agree *everywhere* — in
particular at the blind coordination (c = 7, the (110) surface). The r = 0.906
blind test is a test of physics, not of fitting freedom. -/
theorem affine_continuation_unique (a₁ b₁ a₂ b₂ x₀ x : ℝ)
    (h0 : a₁ + b₁ * x₀ = a₂ + b₂ * x₀)
    (h1 : a₁ + b₁ * (x₀ + 1) = a₂ + b₂ * (x₀ + 1)) :
    a₁ + b₁ * x = a₂ + b₂ * x := by
  have hb : b₁ = b₂ := by nlinarith
  rw [hb] at h0 ⊢
  have ha : a₁ = a₂ := by linarith
  rw [ha]

end OpenDistillationFactory.Materials.Theory.EnvironmentField
