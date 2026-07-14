import Mathlib.Topology.MetricSpace.Pseudo.Defs
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Anchor
import OpenDistillationFactory.Materials.Theory.UniversalCorrection.Smoothness

/-!
# Sound scalar correction envelopes

A finite collection of interval-valued anchors and a Lipschitz premise bound a
scalar residual at every point.  This module constructs the finite McShane--
Whitney-style envelope used by the universal correction gate:

* every anchor contributes a lower cone and an upper cone;
* the greatest lower cone and least upper cone enclose every compatible
  Lipschitz residual;
* the envelope midpoint is a correction whose error is at most half the
  envelope width; and
* adding evidence can only tighten the envelope.

The corpus is nonempty by construction (`head` plus `tail`).  Consequently the
envelope is a real-valued total function and requires neither artificial
infinities nor a default value.  The Lipschitz and containment hypotheses are
explicit scientific premises; this file proves their consequences and does not
assert that any empirical residual satisfies them.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

/-- A nonempty, finite bundle of interval anchors in one semantic scope. -/
structure AnchorCorpus (scope : Scope) (X : Type*) where
  head : Anchor scope X
  tail : List (Anchor scope X)

namespace AnchorCorpus

/-- The list represented by a nonempty corpus. -/
def toList {scope : Scope} {X : Type*} (corpus : AnchorCorpus scope X) :
    List (Anchor scope X) :=
  corpus.head :: corpus.tail

/-- Every anchor in the corpus contains the candidate residual field. -/
def Contains {scope : Scope} {X : Type*} (corpus : AnchorCorpus scope X)
    (field : ResidualField scope X ℝ) : Prop :=
  AnchorsContain corpus.toList field

@[simp] theorem contains_iff {scope : Scope} {X : Type*}
    (corpus : AnchorCorpus scope X) (field : ResidualField scope X ℝ) :
    corpus.Contains field ↔
      corpus.head.Contains field ∧ AnchorsContain corpus.tail field := by
  simp [Contains, toList]

/-- Add an anchor without changing the corpus head.  Keeping the original head
makes the tightening equations below definitionally simple. -/
def add {scope : Scope} {X : Type*} (corpus : AnchorCorpus scope X)
    (anchor : Anchor scope X) : AnchorCorpus scope X :=
  { corpus with tail := anchor :: corpus.tail }

@[simp] theorem contains_add_iff {scope : Scope} {X : Type*}
    (corpus : AnchorCorpus scope X) (anchor : Anchor scope X)
    (field : ResidualField scope X ℝ) :
    (corpus.add anchor).Contains field ↔
      anchor.Contains field ∧ corpus.Contains field := by
  simp [Contains, toList, add, and_assoc, and_left_comm, and_comm]

end AnchorCorpus

/-- The lower cone contributed by one interval anchor. -/
def lowerTerm {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (L : ℝ) (x : X) (anchor : Anchor scope X) : ℝ :=
  anchor.lower - L * dist x anchor.point

/-- The upper cone contributed by one interval anchor. -/
def upperTerm {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (L : ℝ) (x : X) (anchor : Anchor scope X) : ℝ :=
  anchor.upper + L * dist x anchor.point

namespace AnchorCorpus

/-- Greatest lower cone over the nonempty corpus. -/
def lowerBound {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (L : ℝ) (x : X) : ℝ :=
  corpus.tail.foldr
    (fun anchor accumulated => max (lowerTerm L x anchor) accumulated)
    (lowerTerm L x corpus.head)

/-- Least upper cone over the nonempty corpus. -/
def upperBound {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (L : ℝ) (x : X) : ℝ :=
  corpus.tail.foldr
    (fun anchor accumulated => min (upperTerm L x anchor) accumulated)
    (upperTerm L x corpus.head)

/-- Midpoint correction selected from a nonempty scalar envelope. -/
noncomputable def midpoint {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (L : ℝ) (x : X) : ℝ :=
  (corpus.lowerBound L x + corpus.upperBound L x) / 2

/-- Half-width of a scalar envelope.  Under the soundness hypotheses below it
is nonnegative. -/
noncomputable def radius {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (L : ℝ) (x : X) : ℝ :=
  (corpus.upperBound L x - corpus.lowerBound L x) / 2

end AnchorCorpus

/-! ## Pointwise soundness -/

/-- Every compatible Lipschitz residual lies above an anchor's lower cone. -/
theorem lowerTerm_le_residual {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {L : ℝ} {field : ResidualField scope X ℝ}
    {anchor : Anchor scope X} {x : X}
    (hanchor : anchor.Contains field) (hL : LipschitzResidual L field) :
    lowerTerm L x anchor ≤ field x := by
  have hdistance := (abs_le.mp (hL.2 x anchor.point)).1
  unfold lowerTerm
  linarith [hanchor.1]

/-- Every compatible Lipschitz residual lies below an anchor's upper cone. -/
theorem residual_le_upperTerm {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {L : ℝ} {field : ResidualField scope X ℝ}
    {anchor : Anchor scope X} {x : X}
    (hanchor : anchor.Contains field) (hL : LipschitzResidual L field) :
    field x ≤ upperTerm L x anchor := by
  have hdistance := (abs_le.mp (hL.2 x anchor.point)).2
  unfold upperTerm
  linarith [hanchor.2]

private theorem foldr_max_le {A : Type*} (term : A → ℝ) (items : List A)
    (base bound : ℝ) (hbase : base ≤ bound)
    (hitems : ∀ item ∈ items, term item ≤ bound) :
    items.foldr (fun item accumulated => max (term item) accumulated) base ≤
      bound := by
  induction items with
  | nil => simpa using hbase
  | cons item items ih =>
      simp only [List.foldr_cons]
      apply max_le
      · exact hitems item (by simp)
      · apply ih
        intro other hother
        exact hitems other (by simp [hother])

private theorem le_foldr_min {A : Type*} (term : A → ℝ) (items : List A)
    (base bound : ℝ) (hbase : bound ≤ base)
    (hitems : ∀ item ∈ items, bound ≤ term item) :
    bound ≤
      items.foldr (fun item accumulated => min (term item) accumulated) base := by
  induction items with
  | nil => simpa using hbase
  | cons item items ih =>
      simp only [List.foldr_cons]
      apply le_min
      · exact hitems item (by simp)
      · apply ih
        intro other hother
        exact hitems other (by simp [hother])

/-! ## Corpus envelopes -/

/-- **Finite-envelope soundness.** Every residual that is contained by all
anchors and obeys the stated Lipschitz bound lies in the computed envelope. -/
theorem residual_mem_envelope {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {corpus : AnchorCorpus scope X}
    {field : ResidualField scope X ℝ} {L : ℝ} {x : X}
    (hcorpus : corpus.Contains field) (hL : LipschitzResidual L field) :
    corpus.lowerBound L x ≤ field x ∧
      field x ≤ corpus.upperBound L x := by
  rw [AnchorCorpus.contains_iff] at hcorpus
  constructor
  · unfold AnchorCorpus.lowerBound
    apply foldr_max_le (fun anchor => lowerTerm L x anchor)
    · exact lowerTerm_le_residual hcorpus.1 hL
    · intro anchor hanchor
      exact lowerTerm_le_residual (hcorpus.2 anchor hanchor) hL
  · unfold AnchorCorpus.upperBound
    apply le_foldr_min (fun anchor => upperTerm L x anchor)
    · exact residual_le_upperTerm hcorpus.1 hL
    · intro anchor hanchor
      exact residual_le_upperTerm (hcorpus.2 anchor hanchor) hL

/-- A sound envelope is ordered.  In particular, an inverted envelope is a
concrete witness that no residual can satisfy all stated premises. -/
theorem envelope_ordered {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {corpus : AnchorCorpus scope X}
    {field : ResidualField scope X ℝ} {L : ℝ} {x : X}
    (hcorpus : corpus.Contains field) (hL : LipschitzResidual L field) :
    corpus.lowerBound L x ≤ corpus.upperBound L x := by
  have hmem := residual_mem_envelope (x := x) hcorpus hL
  exact hmem.1.trans hmem.2

/-- The radius of a sound envelope is nonnegative. -/
theorem envelope_radius_nonneg {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {corpus : AnchorCorpus scope X}
    {field : ResidualField scope X ℝ} {L : ℝ} {x : X}
    (hcorpus : corpus.Contains field) (hL : LipschitzResidual L field) :
    0 ≤ corpus.radius L x := by
  unfold AnchorCorpus.radius
  linarith [envelope_ordered (x := x) hcorpus hL]

/-- The envelope midpoint approximates every compatible residual to within
the envelope radius. -/
theorem midpoint_error_le_radius {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {corpus : AnchorCorpus scope X}
    {field : ResidualField scope X ℝ} {L : ℝ} {x : X}
    (hcorpus : corpus.Contains field) (hL : LipschitzResidual L field) :
    |field x - corpus.midpoint L x| ≤ corpus.radius L x := by
  have hmem := residual_mem_envelope (x := x) hcorpus hL
  rw [abs_le]
  unfold AnchorCorpus.midpoint AnchorCorpus.radius
  constructor <;> linarith [hmem.1, hmem.2]

/-- If `field x` is the signed residual `model - reference`, subtracting the
envelope midpoint from the model leaves at most the envelope radius of error. -/
theorem corrected_error_le_radius {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] {corpus : AnchorCorpus scope X}
    {field : ResidualField scope X ℝ} {L modelValue referenceValue : ℝ}
    {x : X} (hresidual : field x = modelValue - referenceValue)
    (hcorpus : corpus.Contains field) (hL : LipschitzResidual L field) :
    |(modelValue - corpus.midpoint L x) - referenceValue| ≤
      corpus.radius L x := by
  have herror := midpoint_error_le_radius (x := x) hcorpus hL
  have heq :
      (modelValue - corpus.midpoint L x) - referenceValue =
        field x - corpus.midpoint L x := by
    rw [hresidual]
    ring
  rw [heq]
  exact herror

/-! ## Monotone tightening under added evidence -/

@[simp] theorem AnchorCorpus.lowerBound_add {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (corpus : AnchorCorpus scope X)
    (anchor : Anchor scope X) (L : ℝ) (x : X) :
    (corpus.add anchor).lowerBound L x =
      max (lowerTerm L x anchor) (corpus.lowerBound L x) := rfl

@[simp] theorem AnchorCorpus.upperBound_add {scope : Scope} {X : Type*}
    [PseudoMetricSpace X] (corpus : AnchorCorpus scope X)
    (anchor : Anchor scope X) (L : ℝ) (x : X) :
    (corpus.add anchor).upperBound L x =
      min (upperTerm L x anchor) (corpus.upperBound L x) := rfl

/-- Adding an anchor can only raise the lower envelope. -/
theorem AnchorCorpus.lowerBound_le_lowerBound_add
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (anchor : Anchor scope X)
    (L : ℝ) (x : X) :
    corpus.lowerBound L x ≤ (corpus.add anchor).lowerBound L x := by
  rw [AnchorCorpus.lowerBound_add]
  exact le_max_right _ _

/-- Adding an anchor can only lower the upper envelope. -/
theorem AnchorCorpus.upperBound_add_le_upperBound
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (anchor : Anchor scope X)
    (L : ℝ) (x : X) :
    (corpus.add anchor).upperBound L x ≤ corpus.upperBound L x := by
  rw [AnchorCorpus.upperBound_add]
  exact min_le_right _ _

/-- Consequently, adding an anchor cannot increase the envelope radius. -/
theorem AnchorCorpus.radius_add_le_radius
    {scope : Scope} {X : Type*} [PseudoMetricSpace X]
    (corpus : AnchorCorpus scope X) (anchor : Anchor scope X)
    (L : ℝ) (x : X) :
    (corpus.add anchor).radius L x ≤ corpus.radius L x := by
  unfold AnchorCorpus.radius
  have hlower := corpus.lowerBound_le_lowerBound_add anchor L x
  have hupper := corpus.upperBound_add_le_upperBound anchor L x
  linarith

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
