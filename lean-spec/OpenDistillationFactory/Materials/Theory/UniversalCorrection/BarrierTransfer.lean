import Mathlib.Data.Finset.Lattice.Fold
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith

/-!
# Bounded transfer of reaction barriers (the T1 law)

The sparse-DFT pilot compares barriers between two engines (GPAW vs the VASP
reference) and between two settings (frozen vs loosened). A barrier is an
energy *difference between different structures*, so a constant offset between
two energy functions cancels — only the *wander* of the offset across the
profile reaches the barrier. This module proves exactly that, unconditionally,
for any finite sampled profile:

* `barrier_sub_le_wander` / `abs_barrier_sub_le_wander` — if the offset
  `g − f` stays in `[a, b]` over the sampled images, the barrier difference
  stays within `b − a` (the offset wander). The mean offset never appears.
  Measured motivation: path-7 (mp-770939) carried a ~14.7 eV mean offset with
  139 meV wander and a 118.8 meV barrier error; the convention is documented
  as theorem line T1 in `docs/analysis/t1-wander-gate.md` and amendment 01.

* `barrier_sub_le_two_eps` — the classical corollary: a uniform `ε` pointwise
  bound transfers to a `2ε` barrier bound.

* `barrier_sub_eq_offset_sub` — when both profiles attain their extrema at the
  *same* two images, the barrier difference IS the offset difference at those
  two points. This is the mathematical explanation of the mp-760344 smoke
  result: ~122 meV of offset wander, yet only a 32.2 meV barrier error,
  because the wander across the barrier-defining extrema was benign.

* `barrier_mono_subset` — the sparse-anchor law: a barrier evaluated over a
  subset of images never *over*estimates the dense barrier. Sparse protocols
  underestimate by omission, which is why anchor placement near the predicted
  saddle is the entire game (preregistration
  `docs/plans/2026-07-20-sparse-dft-pilot-preregistration.md`).

Epistemic grade (per `UniversalCorrection.Empirical.Registry`): **pure
mathematical** — no empirical premise; the hypotheses are pointwise bounds
supplied by the caller, never by this module.
-/

namespace OpenDistillationFactory.Materials.Theory.UniversalCorrection

variable {ι : Type*}

/-- The barrier of an energy profile sampled on a nonempty finite image set:
highest sampled energy minus lowest sampled energy. -/
noncomputable def barrier (s : Finset ι) (hs : s.Nonempty) (E : ι → ℝ) : ℝ :=
  s.sup' hs E - s.inf' hs E

/-- Upper transfer: if `g − f ≤ b` pointwise, the sup moves up at most `b`. -/
theorem sup_sub_sup_le {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ} {b : ℝ}
    (h : ∀ x ∈ s, g x - f x ≤ b) :
    s.sup' hs g - s.sup' hs f ≤ b := by
  have hbound : ∀ x ∈ s, g x ≤ s.sup' hs f + b := fun x hx => by
    have h1 := h x hx
    have h2 : f x ≤ s.sup' hs f := Finset.le_sup' (f := f) hx
    linarith
  have hsup := Finset.sup'_le (s := s) hs g hbound
  linarith

/-- Lower transfer: if `a ≤ g − f` pointwise, the inf moves down at most `−a`. -/
theorem inf_sub_inf_le {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ} {a : ℝ}
    (h : ∀ x ∈ s, a ≤ g x - f x) :
    s.inf' hs f - s.inf' hs g ≤ -a := by
  have hbound : ∀ x ∈ s, s.inf' hs f + a ≤ g x := fun x hx => by
    have h1 := h x hx
    have h2 : s.inf' hs f ≤ f x := Finset.inf'_le (f := f) hx
    linarith
  have hinf := Finset.le_inf' (s := s) hs g hbound
  linarith

/-- **The T1 law.** A barrier difference between two energy functions is
bounded by the *wander* of their pointwise offset over the sampled images —
never by the offset's mean. Constant offsets cancel in energy differences. -/
theorem barrier_sub_le_wander {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {a b : ℝ} (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b) :
    barrier s hs g - barrier s hs f ≤ b - a := by
  have hsup : s.sup' hs g - s.sup' hs f ≤ b := sup_sub_sup_le (f := f) (g := g) hb
  have hinf : s.inf' hs f - s.inf' hs g ≤ -a := inf_sub_inf_le (f := f) (g := g) ha
  unfold barrier
  linarith

/-- The two-sided form: `|barrier g − barrier f| ≤ wander(offset)`. -/
theorem abs_barrier_sub_le_wander {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {a b : ℝ} (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b) :
    |barrier s hs g - barrier s hs f| ≤ b - a := by
  have h1 : barrier s hs g - barrier s hs f ≤ b - a :=
    barrier_sub_le_wander (f := f) (g := g) ha hb
  have h2 : barrier s hs f - barrier s hs g ≤ -a - -b :=
    barrier_sub_le_wander (f := g) (g := f) (a := -b) (b := -a)
      (fun x hx => by have h := hb x hx; linarith)
      (fun x hx => by have h := ha x hx; linarith)
  rw [abs_le]
  constructor <;> linarith

/-- Classical corollary: a uniform `ε` pointwise bound transfers to `2ε`. -/
theorem barrier_sub_le_two_eps {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {ε : ℝ} (hε : ∀ x ∈ s, |g x - f x| ≤ ε) :
    |barrier s hs g - barrier s hs f| ≤ 2 * ε := by
  have ha : ∀ x ∈ s, -ε ≤ g x - f x := fun x hx =>
    (abs_le.mp (hε x hx)).1
  have hb : ∀ x ∈ s, g x - f x ≤ ε := fun x hx =>
    (abs_le.mp (hε x hx)).2
  have hw : |barrier s hs g - barrier s hs f| ≤ ε - -ε :=
    abs_barrier_sub_le_wander (f := f) (g := g) ha hb
  linarith

/-- **The same-extrema identity.** When both profiles attain their maximum at
`xm` and their minimum at `xn`, the barrier difference IS the offset
difference at the two extrema — full-profile wander is then irrelevant. -/
theorem barrier_sub_eq_offset_sub {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {xm xn : ι} (hxm : xm ∈ s) (hxn : xn ∈ s)
    (hmax_f : ∀ x ∈ s, f x ≤ f xm) (hmax_g : ∀ x ∈ s, g x ≤ g xm)
    (hmin_f : ∀ x ∈ s, f xn ≤ f x) (hmin_g : ∀ x ∈ s, g xn ≤ g x) :
    barrier s hs g - barrier s hs f = (g xm - f xm) - (g xn - f xn) := by
  have hsup_f : s.sup' hs f = f xm :=
    le_antisymm (Finset.sup'_le (s := s) hs f hmax_f)
      (Finset.le_sup' (f := f) hxm)
  have hsup_g : s.sup' hs g = g xm :=
    le_antisymm (Finset.sup'_le (s := s) hs g hmax_g)
      (Finset.le_sup' (f := g) hxm)
  have hinf_f : s.inf' hs f = f xn :=
    le_antisymm (Finset.inf'_le (f := f) hxn)
      (Finset.le_inf' (s := s) hs f hmin_f)
  have hinf_g : s.inf' hs g = g xn :=
    le_antisymm (Finset.inf'_le (f := g) hxn)
      (Finset.le_inf' (s := s) hs g hmin_g)
  unfold barrier
  rw [hsup_f, hsup_g, hinf_f, hinf_g]
  linarith

/-- **The sparse-anchor law.** A barrier evaluated over a subset of the
sampled images never *over*estimates the dense barrier: sparse protocols
underestimate by omission. This is unconditional — it is why anchor placement
near the predicted saddle carries the entire error budget of the sparse
protocol. -/
theorem barrier_mono_subset {s t : Finset ι} {hs : s.Nonempty} {ht : t.Nonempty}
    (hst : t ⊆ s) (E : ι → ℝ) :
    barrier t ht E ≤ barrier s hs E := by
  have hsup : t.sup' ht E ≤ s.sup' hs E := by
    refine Finset.sup'_le (s := t) ht E ?_
    intro x hx
    exact Finset.le_sup' (f := E) (hst hx)
  have hinf : s.inf' hs E ≤ t.inf' ht E := by
    refine Finset.le_inf' (s := t) ht E ?_
    intro x hx
    exact Finset.inf'_le (f := E) (hst hx)
  unfold barrier
  linarith

end OpenDistillationFactory.Materials.Theory.UniversalCorrection
