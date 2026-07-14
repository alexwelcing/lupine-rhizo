import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Residual

/-!
# Interval-valued residual anchors

An anchor records measured evidence about a residual at one point.  Its bounds
are intervals rather than exact real numbers so measurement uncertainty,
rounding, and numerical enclosure remain explicit.  General theorems consume
`AnchorsContain`; whether a particular evidence bundle satisfies it is an
empirical premise, not something a successful Lean build invents.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A valid closed interval constraining a scoped residual at `point`. -/
structure Anchor (_scope : Scope) (X : Type*) where
  point : X
  lower : ℝ
  upper : ℝ
  valid : lower ≤ upper

namespace Anchor

/-- Width of an anchor's uncertainty interval. -/
def width {scope : Scope} {X : Type*} (anchor : Anchor scope X) : ℝ :=
  anchor.upper - anchor.lower

@[simp] theorem width_nonneg {scope : Scope} {X : Type*}
    (anchor : Anchor scope X) : 0 ≤ anchor.width := by
  unfold width
  linarith [anchor.valid]

/-- An exact anchor is a zero-width interval. -/
def exact {scope : Scope} {X : Type*} (point : X) (value : ℝ) : Anchor scope X where
  point := point
  lower := value
  upper := value
  valid := le_rfl

@[simp] theorem exact_width {scope : Scope} {X : Type*} (point : X) (value : ℝ) :
    (exact (scope := scope) point value).width = 0 := by
  simp [exact, width]

/-- The empirical assertion represented by one interval anchor. -/
def Contains {scope : Scope} {X : Type*} (anchor : Anchor scope X)
    (field : ResidualField scope X ℝ) : Prop :=
  anchor.lower ≤ field anchor.point ∧ field anchor.point ≤ anchor.upper

@[simp] theorem exact_contains_iff {scope : Scope} {X : Type*}
    (point : X) (value : ℝ) (field : ResidualField scope X ℝ) :
    (exact (scope := scope) point value).Contains field ↔ field point = value := by
  constructor
  · rintro ⟨hlower, hupper⟩
    simp only [exact] at hlower hupper
    linarith
  · intro h
    simp [Contains, exact, h]

/-- Every value certified by an anchor lies within half the interval width of
the interval midpoint. -/
theorem distance_to_midpoint_le_half_width
    {scope : Scope} {X : Type*} (anchor : Anchor scope X)
    (field : ResidualField scope X ℝ) (hcontains : anchor.Contains field) :
    |field anchor.point - (anchor.lower + anchor.upper) / 2| ≤ anchor.width / 2 := by
  rw [abs_le]
  unfold width
  constructor <;> linarith [hcontains.1, hcontains.2]

end Anchor

/-- Every anchor in a finite evidence bundle contains the residual field. -/
def AnchorsContain {scope : Scope} {X : Type*}
    (anchors : List (Anchor scope X)) (field : ResidualField scope X ℝ) : Prop :=
  ∀ anchor ∈ anchors, anchor.Contains field

@[simp] theorem anchorsContain_nil {scope : Scope} {X : Type*}
    (field : ResidualField scope X ℝ) :
    AnchorsContain [] field := by
  simp [AnchorsContain]

@[simp] theorem anchorsContain_cons {scope : Scope} {X : Type*}
    (anchor : Anchor scope X) (anchors : List (Anchor scope X))
    (field : ResidualField scope X ℝ) :
    AnchorsContain (anchor :: anchors) field ↔
      anchor.Contains field ∧ AnchorsContain anchors field := by
  simp [AnchorsContain]

theorem AnchorsContain.of_mem {scope : Scope} {X : Type*}
    {anchors : List (Anchor scope X)} {field : ResidualField scope X ℝ}
    (h : AnchorsContain anchors field) {anchor : Anchor scope X}
    (hmem : anchor ∈ anchors) : anchor.Contains field :=
  h anchor hmem

/-- Restricting an evidence bundle cannot invalidate containment. -/
theorem AnchorsContain.mono {scope : Scope} {X : Type*}
    {small large : List (Anchor scope X)} {field : ResidualField scope X ℝ}
    (hlarge : AnchorsContain large field)
    (hsubset : ∀ anchor, anchor ∈ small → anchor ∈ large) :
    AnchorsContain small field := by
  intro anchor hmem
  exact hlarge anchor (hsubset anchor hmem)

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
