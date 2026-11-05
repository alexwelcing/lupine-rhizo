import Mathlib.Data.Finset.Lattice.Fold
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring
import OpenDistillationFactory.Materials.Theory.BarrierArrhenius

/-!
# Bounded transfer of reaction barriers (the T1 law)

The sparse-DFT pilot compares barriers between two engines (GPAW vs the VASP
reference) and between two settings (frozen vs loosened). A barrier is an
energy *difference between different structures*, so a constant offset between
two energy functions cancels — only the *wander* of the offset across the
profile reaches the barrier. This module proves exactly that, unconditionally,
for any finite sampled profile. Here the historical `barrier` means sampled
maximum minus sampled minimum; `forwardBarrier` below instead uses a designated
initial image. The two agree exactly when that image is a sampled minimizer.
Neither sampled definition establishes continuous-path coverage or physical
activation-energy validity.

The proved range statements are:

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

* `hopRate_le_exp_wander_mul` / `hopRate_ratio_le_exp_wander` — the kinetic
  T1 corollary: under an offset-wander bound, Vineyard hop rates at the two
  barriers differ by at most `exp(wander / kT)`. Convention wander becomes a
  *bounded* rate amplification for the declared range observable and the same
  prefactor (composed with `Theory.BarrierArrhenius`). A physical forward-rate
  interpretation needs the initial-state condition or the anchored theorem
  below. Conductivity and diffusivity need additional transport premises.

* `barrier_deficit_le_lipschitz_cover` — the sparse-window coverage bound:
  for an `L`-Lipschitz profile with every dense image within `d` of the
  sparse set, the sparse deficit is at most `2Ld`. With
  `barrier_mono_subset` (deficit ≥ 0) and `barrier_eq_barrier_of_extrema_mem`
  (deficit = 0 when extrema are covered), the sparse protocol's error budget
  is closed: placement risk is a covering-radius question, and it is the
  only question.

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

/-- **Extrema sufficiency (the union law).** Any sample set that contains an
argmax and an argmin of the dense profile reproduces the dense barrier
*exactly* — no approximation, no window tolerance. This is the formal basis of
union anchoring: multiple models' predicted-extrema sets each aim at the true
extrema, and their union covers every model's needs with one shared
evaluation (measured: 558 naive vs 154 union anchors,
`data/candidates/z1-union-anchor-economics.json`). -/
theorem barrier_eq_barrier_of_extrema_mem {s t : Finset ι} {hs : s.Nonempty} {ht : t.Nonempty}
    (hst : t ⊆ s) (E : ι → ℝ) {xm xn : ι} (hxm : xm ∈ t) (hxn : xn ∈ t)
    (hmax : ∀ x ∈ s, E x ≤ E xm) (hmin : ∀ x ∈ s, E xn ≤ E x) :
    barrier t ht E = barrier s hs E := by
  have hsup : t.sup' ht E = s.sup' hs E := by
    apply le_antisymm
    · exact Finset.sup'_le (s := t) ht E (fun x hx => Finset.le_sup' (f := E) (hst hx))
    · have h1 : E xm ≤ t.sup' ht E := Finset.le_sup' (f := E) hxm
      have h2 : ∀ x ∈ s, E x ≤ t.sup' ht E := fun x hx => le_trans (hmax x hx) h1
      exact Finset.sup'_le (s := s) hs E h2
  have hinf : t.inf' ht E = s.inf' hs E := by
    apply le_antisymm
    · have h1 : t.inf' ht E ≤ E xn := Finset.inf'_le (f := E) hxn
      have h2 : ∀ x ∈ s, t.inf' ht E ≤ E x := fun x hx => le_trans h1 (hmin x hx)
      exact Finset.le_inf' (s := s) hs E h2
    · exact Finset.le_inf' (s := t) ht E (fun x hx => Finset.inf'_le (f := E) (hst hx))
  unfold barrier
  rw [hsup, hinf]

/-- The sparse-window corollary: if the true saddle region's argmax and argmin
lie inside the sampled window, the sparse protocol's barrier IS the dense
barrier — window error is then exactly zero, and the protocol's residual risk
is purely *coverage* risk (an extremum outside the window), never evaluation
error. -/
theorem barrier_eq_barrier_of_extrema_mem_mono {s t : Finset ι} {hs : s.Nonempty} {ht : t.Nonempty}
    (hst : t ⊆ s) (E : ι → ℝ) {xm xn : ι} (hxm : xm ∈ t) (hxn : xn ∈ t)
    (hmax : ∀ x ∈ s, E x ≤ E xm) (hmin : ∀ x ∈ s, E xn ≤ E x) :
    barrier t ht E = barrier s hs E ∧ barrier t ht E ≤ barrier s hs E :=
  ⟨barrier_eq_barrier_of_extrema_mem hst E hxm hxn hmax hmin,
   barrier_mono_subset hst E⟩

/-- **The sparse-window coverage bound.** If `E` is `L`-Lipschitz over the
image metric and every densely-sampled image lies within distance `d` of the
sparse set, then the sparse deficit is at most `2Ld`. Together with
`barrier_mono_subset` (deficit is non-negative) and
`barrier_eq_barrier_of_extrema_mem` (deficit vanishes when extrema are
covered), this closes the sparse protocol's error budget: *placement* risk is
a covering-radius question, and it is the only question. -/
theorem barrier_deficit_le_lipschitz_cover {s t : Finset ι} {hs : s.Nonempty} {ht : t.Nonempty}
    (E : ι → ℝ) {dist : ι → ι → ℝ} {L d : ℝ}
    (hL0 : 0 ≤ L) (hsymm : ∀ x y, dist x y = dist y x)
    (hL : ∀ x y, |E x - E y| ≤ L * dist x y)
    (hcov : ∀ x ∈ s, ∃ y ∈ t, dist x y ≤ d) :
    barrier s hs E - barrier t ht E ≤ 2 * L * d := by
  have hsup : s.sup' hs E ≤ t.sup' ht E + L * d := by
    refine Finset.sup'_le (s := s) hs E ?_
    intro x hx
    obtain ⟨y, hyt, hdy⟩ := hcov x hx
    have h1 : E x ≤ E y + L * d := by
      have h2 : |E x - E y| ≤ L * dist x y := hL x y
      have h3 : L * dist x y ≤ L * d := mul_le_mul_of_nonneg_left hdy hL0
      rw [abs_le] at h2
      linarith
    have h4 : E y ≤ t.sup' ht E := Finset.le_sup' (f := E) hyt
    linarith
  have hinf : t.inf' ht E ≤ s.inf' hs E + L * d := by
    obtain ⟨x0, hx0s, hx0eq⟩ := Finset.exists_mem_eq_inf' (s := s) (H := hs) E
    obtain ⟨y, hyt, hdy⟩ := hcov x0 hx0s
    have h6 : t.inf' ht E ≤ E y := Finset.inf'_le (f := E) hyt
    have h7 : E y ≤ E x0 + L * d := by
      have h8 : |E y - E x0| ≤ L * dist y x0 := hL y x0
      have h9 : dist y x0 = dist x0 y := hsymm y x0
      have h10 : L * dist y x0 ≤ L * d := by
        rw [h9]; exact mul_le_mul_of_nonneg_left hdy hL0
      rw [abs_le] at h8
      linarith
    linarith
  have hdef : barrier s hs E - barrier t ht E =
      (s.sup' hs E - t.sup' ht E) + (t.inf' ht E - s.inf' hs E) := by
    unfold barrier; ring
  rw [hdef]
  linarith

/-- **The kinetic T1 corollary.** Under the same offset-wander bound, the
Vineyard hop rate at the `g`-predicted barrier overestimates the rate at the
`f`-predicted barrier by at most `exp(wander / kT)` — the convention wander
bounds a scalar hop-rate amplification with the same prefactor. The arguments
here are sampled ranges; interpreting them as forward activation barriers
requires the initial-state condition. Conductivity is not proved here. -/
theorem hopRate_le_exp_wander_mul {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {a b ν kT : ℝ} (hν : 0 < ν) (hkT : 0 < kT)
    (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b) :
    BarrierArrhenius.hopRate ν (barrier s hs g) kT
      ≤ Real.exp ((b - a) / kT) * BarrierArrhenius.hopRate ν (barrier s hs f) kT := by
  have hΔ : barrier s hs f - barrier s hs g ≤ -a - -b :=
    barrier_sub_le_wander (f := g) (g := f) (a := -b) (b := -a)
      (fun x hx => by have h := hb x hx; linarith)
      (fun x hx => by have h := ha x hx; linarith)
  have hbz : BarrierArrhenius.boltzmann (barrier s hs g) kT
      ≤ BarrierArrhenius.boltzmann (barrier s hs f - (b - a)) kT :=
    BarrierArrhenius.boltzmann_antitone hkT (by linarith)
  have hfact : BarrierArrhenius.boltzmann (barrier s hs f - (b - a)) kT
      = Real.exp ((b - a) / kT) * BarrierArrhenius.boltzmann (barrier s hs f) kT :=
    BarrierArrhenius.boltzmann_error_factor (barrier s hs f) (b - a) kT
  unfold BarrierArrhenius.hopRate
  calc ν * BarrierArrhenius.boltzmann (barrier s hs g) kT
      ≤ ν * (Real.exp ((b - a) / kT) * BarrierArrhenius.boltzmann (barrier s hs f) kT) := by
        exact mul_le_mul_of_nonneg_left (le_trans hbz (le_of_eq hfact)) hν.le
    _ = Real.exp ((b - a) / kT) * (ν * BarrierArrhenius.boltzmann (barrier s hs f) kT) := by
        ring

/-- The ratio form: rates at the two barriers differ by at most the proved
exponential factor. -/
theorem hopRate_ratio_le_exp_wander {s : Finset ι} {hs : s.Nonempty} {f g : ι → ℝ}
    {a b ν kT : ℝ} (hν : 0 < ν) (hkT : 0 < kT)
    (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b) :
    BarrierArrhenius.hopRate ν (barrier s hs g) kT
      / BarrierArrhenius.hopRate ν (barrier s hs f) kT
      ≤ Real.exp ((b - a) / kT) := by
  have hmul : BarrierArrhenius.hopRate ν (barrier s hs g) kT
      ≤ Real.exp ((b - a) / kT) * BarrierArrhenius.hopRate ν (barrier s hs f) kT :=
    hopRate_le_exp_wander_mul (f := f) (g := g) hν hkT ha hb
  have hpos : 0 < BarrierArrhenius.hopRate ν (barrier s hs f) kT :=
    BarrierArrhenius.hopRate_pos ν (barrier s hs f) kT hν
  rw [div_le_iff₀ hpos]
  exact hmul

/-! ## Forward barriers anchored to a designated initial image

The historical `barrier` definition above is the sampled energy range. A
forward activation barrier instead subtracts the energy of the designated
initial image. Membership is part of this definition; callers must align the
same initial configuration across the two profiles. Neither definition proves
that the sample contains the continuous-path saddle. -/

/-- Sampled forward barrier relative to a designated initial image in the sample. -/
noncomputable def forwardBarrier (s : Finset ι) (i : ι) (hi : i ∈ s)
    (E : ι → ℝ) : ℝ :=
  s.sup' ⟨i, hi⟩ E - E i

theorem forwardBarrier_nonneg {s : Finset ι} {i : ι} (hi : i ∈ s) (E : ι → ℝ) :
    0 ≤ forwardBarrier s i hi E := by
  have h : E i ≤ s.sup' ⟨i, hi⟩ E := Finset.le_sup' (f := E) hi
  unfold forwardBarrier
  linarith

/-- The range exceeds the forward barrier by the initial image's elevation
above the sampled minimum. The historical range values are not redefined. -/
theorem barrier_sub_forwardBarrier {s : Finset ι} {hs : s.Nonempty} {i : ι}
    (hi : i ∈ s) (E : ι → ℝ) :
    barrier s hs E - forwardBarrier s i hi E = E i - s.inf' hs E := by
  unfold barrier forwardBarrier
  ring

theorem forwardBarrier_le_barrier {s : Finset ι} {hs : s.Nonempty} {i : ι}
    (hi : i ∈ s) (E : ι → ℝ) :
    forwardBarrier s i hi E ≤ barrier s hs E := by
  have hgap := barrier_sub_forwardBarrier (hs := hs) hi E
  have hmin : s.inf' hs E ≤ E i := Finset.inf'_le (f := E) hi
  linarith

/-- Range and forward barrier coincide exactly when the designated initial
image is a sampled minimizer, including ties. -/
theorem barrier_eq_forwardBarrier_iff {s : Finset ι} {hs : s.Nonempty} {i : ι}
    (hi : i ∈ s) (E : ι → ℝ) :
    barrier s hs E = forwardBarrier s i hi E ↔ ∀ x ∈ s, E i ≤ E x := by
  have hgap := barrier_sub_forwardBarrier (hs := hs) hi E
  constructor
  · intro heq x hx
    have hmin : s.inf' hs E ≤ E x := Finset.inf'_le (f := E) hx
    linarith
  · intro hmin
    have hlo : E i ≤ s.inf' hs E := Finset.le_inf' (s := s) hs E hmin
    have hhi : s.inf' hs E ≤ E i := Finset.inf'_le (f := E) hi
    linarith

/-- Forward-barrier transfer uses the same designated initial image. No common
maximum or minimum, and no initial-minimizer premise, is required. -/
theorem abs_forwardBarrier_sub_le_wander {s : Finset ι} {i : ι} (hi : i ∈ s)
    {f g : ι → ℝ} {a b : ℝ}
    (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b) :
    |forwardBarrier s i hi g - forwardBarrier s i hi f| ≤ b - a := by
  have hsup : s.sup' ⟨i, hi⟩ g - s.sup' ⟨i, hi⟩ f ≤ b :=
    sup_sub_sup_le (f := f) (g := g) hb
  have hrev : s.sup' ⟨i, hi⟩ f - s.sup' ⟨i, hi⟩ g ≤ -a :=
    sup_sub_sup_le (f := g) (g := f)
      (fun x hx => by have h := ha x hx; linarith)
  have hia := ha i hi
  have hib := hb i hi
  unfold forwardBarrier
  rw [abs_le]
  constructor <;> linarith

/-- Sparse forward barriers underestimate the dense sampled barrier when both
retain the same initial image. Re-selecting a minimum as the initial image is
a different observable and is not covered by this statement. -/
theorem forwardBarrier_mono_subset {s t : Finset ι} {i : ι}
    (hi : i ∈ t) (hst : t ⊆ s) (E : ι → ℝ) :
    forwardBarrier t i hi E ≤ forwardBarrier s i (hst hi) E := by
  have hsup : t.sup' ⟨i, hi⟩ E ≤ s.sup' ⟨i, hst hi⟩ E :=
    Finset.sup'_le (s := t) ⟨i, hi⟩ E
      (fun x hx => Finset.le_sup' (f := E) (hst hx))
  unfold forwardBarrier
  linarith

/-- Conditional rate transfer for anchored barriers with an explicitly bounded
prefactor ratio. Equal prefactors are the special case `l = u = 1`; no
diffusivity, occupancy, network or conductivity model is supplied here. -/
theorem forward_hopRate_ratio_bounds {s : Finset ι} {i : ι} (hi : i ∈ s)
    {f g : ι → ℝ} {a b νf νg kT l u : ℝ}
    (hνf : 0 < νf) (hνg : 0 < νg) (hkT : 0 < kT)
    (ha : ∀ x ∈ s, a ≤ g x - f x) (hb : ∀ x ∈ s, g x - f x ≤ b)
    (hl : l ≤ νg / νf) (hu : νg / νf ≤ u) :
    l * Real.exp (-(b - a) / kT) ≤
        BarrierArrhenius.hopRate νg (forwardBarrier s i hi g) kT /
          BarrierArrhenius.hopRate νf (forwardBarrier s i hi f) kT ∧
      BarrierArrhenius.hopRate νg (forwardBarrier s i hi g) kT /
          BarrierArrhenius.hopRate νf (forwardBarrier s i hi f) kT ≤
        u * Real.exp ((b - a) / kT) :=
  BarrierArrhenius.hopRate_ratio_bounds hνf hνg hkT
    (abs_forwardBarrier_sub_le_wander hi ha hb) hl hu

/-! ## Separately selected paths and model-specific initial states

A pointwise error bound controls each *shared* candidate profile, not arbitrary
outputs of two path searches. The following finite-family bounds retain each
search's certified suboptimality and the initial-energy difference. A finite
profile family is not a proof of coverage of all continuous physical paths. -/

/-- Selected scores differ by optimum transfer plus the difference between
their actual optimization gaps. The same finite candidate family is required. -/
theorem selected_path_score_sub_decomposition {κ : Type*}
    {s : Finset κ} (hs : s.Nonempty) (f g : κ → ℝ) (p q : κ) :
    g q - f p = (s.inf' hs g - s.inf' hs f) +
      (g q - s.inf' hs g) - (f p - s.inf' hs f) := by
  ring

/-- Transfer for separately selected candidates with certified additive search
gaps. A minimizer assumption is the special case of zero gaps, never a
consequence of an optimizer terminating or a force tolerance being reached. -/
theorem selected_path_score_sub_bounds {κ : Type*}
    {s : Finset κ} {hs : s.Nonempty} {f g : κ → ℝ} {p q : κ}
    {a b ηf ηg : ℝ} (hp : p ∈ s) (hq : q ∈ s)
    (ha : ∀ x ∈ s, a ≤ g x - f x)
    (hb : ∀ x ∈ s, g x - f x ≤ b)
    (hf : f p ≤ s.inf' hs f + ηf)
    (hg : g q ≤ s.inf' hs g + ηg) :
    a - ηf ≤ g q - f p ∧ g q - f p ≤ b + ηg := by
  have hlo : s.inf' hs f - s.inf' hs g ≤ -a :=
    inf_sub_inf_le (f := f) (g := g) ha
  have hhi : s.inf' hs g - s.inf' hs f ≤ -(-b) :=
    inf_sub_inf_le (f := g) (g := f) (a := -b)
      (fun x hx => by have h := hb x hx; linarith)
  have hpf : s.inf' hs f ≤ f p := Finset.inf'_le (f := f) hp
  have hqg : s.inf' hs g ≤ g q := Finset.inf'_le (f := g) hq
  constructor <;> linarith

/-- Two selected sampled forward barriers may use different initial states.
Pointwise energy offsets bound the shift in every candidate profile's maximum;
the actual initial-energy difference and certified search gaps remain explicit.
The declared finite family must be common to both energies. It is not asserted
to contain every physical path, and no NEB convergence theorem is supplied. -/
theorem selected_forwardBarrier_sub_bounds {κ : Type*}
    {paths : Finset κ} {hpaths : paths.Nonempty}
    (samples : κ → Finset ι) (hne : ∀ k, (samples k).Nonempty)
    {f g : ι → ℝ} {p q : κ} {i j : ι} {a b ηf ηg : ℝ}
    (hp : p ∈ paths) (hq : q ∈ paths)
    (hi : i ∈ samples p) (hj : j ∈ samples q)
    (ha : ∀ k ∈ paths, ∀ x ∈ samples k, a ≤ g x - f x)
    (hb : ∀ k ∈ paths, ∀ x ∈ samples k, g x - f x ≤ b)
    (hf : (samples p).sup' (hne p) f ≤
      paths.inf' hpaths (fun k => (samples k).sup' (hne k) f) + ηf)
    (hg : (samples q).sup' (hne q) g ≤
      paths.inf' hpaths (fun k => (samples k).sup' (hne k) g) + ηg) :
    a - (g j - f i) - ηf ≤
        forwardBarrier (samples q) j hj g - forwardBarrier (samples p) i hi f ∧
      forwardBarrier (samples q) j hj g - forwardBarrier (samples p) i hi f ≤
        b - (g j - f i) + ηg := by
  have hlow : ∀ k ∈ paths,
      a ≤ (samples k).sup' (hne k) g - (samples k).sup' (hne k) f := by
    intro k hk
    have hrev : (samples k).sup' (hne k) f -
        (samples k).sup' (hne k) g ≤ -a :=
      sup_sub_sup_le (f := g) (g := f) (b := -a)
        (fun x hx => by have h := ha k hk x hx; linarith)
    linarith
  have hhigh : ∀ k ∈ paths,
      (samples k).sup' (hne k) g - (samples k).sup' (hne k) f ≤ b := by
    intro k hk
    exact sup_sub_sup_le (f := f) (g := g) (hb k hk)
  obtain ⟨hl, hu⟩ := selected_path_score_sub_bounds
    (hs := hpaths) hp hq hlow hhigh hf hg
  unfold forwardBarrier
  constructor <;> linarith

/-- When the selected profiles share the actual initial configuration, offset
wander suffices for optimum transfer, but each selected path's search gap
remains. Zero search gaps require certificates, not a solver success flag. -/
theorem selected_forwardBarrier_sub_bounds_same_initial {κ : Type*}
    {paths : Finset κ} {hpaths : paths.Nonempty}
    (samples : κ → Finset ι) (hne : ∀ k, (samples k).Nonempty)
    {f g : ι → ℝ} {p q : κ} {i : ι} {a b ηf ηg : ℝ}
    (hp : p ∈ paths) (hq : q ∈ paths)
    (hi : i ∈ samples p) (hj : i ∈ samples q)
    (ha : ∀ k ∈ paths, ∀ x ∈ samples k, a ≤ g x - f x)
    (hb : ∀ k ∈ paths, ∀ x ∈ samples k, g x - f x ≤ b)
    (hf : (samples p).sup' (hne p) f ≤
      paths.inf' hpaths (fun k => (samples k).sup' (hne k) f) + ηf)
    (hg : (samples q).sup' (hne q) g ≤
      paths.inf' hpaths (fun k => (samples k).sup' (hne k) g) + ηg) :
    -(b - a) - ηf ≤
        forwardBarrier (samples q) i hj g - forwardBarrier (samples p) i hi f ∧
      forwardBarrier (samples q) i hj g - forwardBarrier (samples p) i hi f ≤
        (b - a) + ηg := by
  obtain ⟨hl, hu⟩ := selected_forwardBarrier_sub_bounds samples hne hp hq hi hj ha hb hf hg
  have hia := ha p hp i hi
  have hib := hb p hp i hi
  constructor <;> linarith

end OpenDistillationFactory.Materials.Theory.UniversalCorrection

#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.barrier_eq_forwardBarrier_iff
#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.abs_forwardBarrier_sub_le_wander
#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.forward_hopRate_ratio_bounds

#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.selected_path_score_sub_bounds
#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.selected_forwardBarrier_sub_bounds
#print axioms OpenDistillationFactory.Materials.Theory.UniversalCorrection.selected_forwardBarrier_sub_bounds_same_initial
