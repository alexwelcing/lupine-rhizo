import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.IntervalCases
import OpenDistillationFactory.Materials.Theory.EnvironmentField
import OpenDistillationFactory.Materials.Theory.AnchoredField
import OpenDistillationFactory.Materials.Theory.BarrierArrhenius
import OpenDistillationFactory.Materials.Theory.SorptionStability

/-!
# The identification laws of anchored measurement

`Theory.AnchoredField` builds one concrete softening field from a cell's
measured anchors — the clamped step field — and its docstring *claims* that
this is "the conservative envelope of the measured data … with no
extrapolation freedom". This module is the proof of that sentence, and of
everything the sentence quietly implies about which downstream decisions the
anchors do and do not license. The question it answers is the platform's
central epistemic question:

> **Exactly what does a finite set of measured anchors determine about the
> true error field, and which corrections, error bars, and rankings does it
> therefore certify?**

The answers, each a theorem below (fcc layout; bcc, diamond, and rocksalt
mirrors follow in the later sections):

1. **Existence ↔ admissibility** (`exists_interpolant_iff_fcc`): a softening
   field through the measured anchors exists *iff* the anchors satisfy the
   admissibility test `p8 ≤ p9 ≤ p11 ≤ 0` (decidable in its scaled-integer
   form, `norm_num`-checkable on rational anchors). The forward direction
   upgrades every kernel-checked tier-2 refusal in
   `DistillAtlas.EnvFieldInstances`: a refused cell is not merely "outside
   our constructor's precondition" — **no `ErrorField` whatsoever is
   consistent with its anchors**. Refusal is complete, not an artifact of
   the chosen interpolation scheme (`scaledAnchorsValid_iff_exists_interpolant`).

2. **The one-scalar reduction** (`interpolant_fieldSum_reduction_fcc`): on
   configurations whose coordinations stay in the anchored range (`c ≥ 8`),
   the field sum of *any* consistent field equals the step-field sum plus
   `count₁₀ · (P 10 − p9)`, where `count₁₀` is the number of atoms at the
   single unanchored coordination c = 10 and `P 10 ∈ [p9, p11]` is forced
   (`interpolant_gap_mem`). The entire in-range ambiguity of a measured
   cell is **one scalar**.

3. **Envelope extremality** (`stepField_le_interpolant_inRange`,
   `interpolant_le_stepFieldSup`): the step field is the pointwise-least
   consistent field on the anchored range, and the shallow variant
   `stepFieldSup` is the pointwise-greatest consistent field *everywhere* —
   the two kernel-checked envelopes of the measurement.

4. **Certified error bars** (`corrected_ge_ref_fcc`, `corrected_bracket_fcc`):
   for in-range configurations of an exactly field-decomposable model, the
   reference energy is bracketed by computable quantities:
   `corrected − count₁₀·(p11 − p9) ≤ E_ref ≤ corrected`. The step-field
   correction never undershoots the reference, and its overshoot is at most
   the anchor gap times the population of the unanchored coordination.

5. **Margin-certified ranking** (`certified_order_iff_fcc`,
   `certified_order_of_separation_fcc`): the strict corrected order of two
   candidates holds against **every** consistent field iff it holds at the
   two envelope fields — a two-point test that is `norm_num`-checkable on
   rational anchor data (and decidable in the scaled-integer form); and
   interval separation is a sufficient margin rule. When the two-point
   test fails, one of the envelopes is a concrete consistent field on
   which the strict order does not hold (the order may flip or tie there).
   This is the formal promotion rule: rank on corrected values only when
   the anchor-gap budget cannot flip the comparison.

6. **Certified kinetics** (`corrected_barrier_bracket_fcc`,
   `rate_factor_cap_fcc`): the step-corrected migration barrier is within
   `|count₁₀(TS) − count₁₀(init)| · (p11 − p9)` of the true barrier, so the
   corrected Arrhenius rate is within a factor `exp(width / kT)` of the
   true rate — a certified error bar on every corrected rate, through the
   exact amplification identity of `Theory.BarrierArrhenius`.

7. **Honest non-identifiability** (`below_range_unidentified_fcc`,
   `measured_gap_unidentified_fcc`, diamond exactness by contrast): below
   the lowest anchor the consistent fields are unbounded (every value
   `v ≤ p8` is realized at c = 7), so no finite below-range certificate
   exists — the formal reason the platform must refuse rather than
   extrapolate; and at the *measured* tier (bulk pin only) even the
   in-range gap value at c = 10 is arbitrary — the directional tier-2
   hypotheses are exactly what buys a finite bracket. The diamond layout,
   having no unanchored in-range coordination, is by contrast *fully
   identified* in range even at the measured tier
   (`measured_fieldSum_exact_diamond`).

**Assumption taxonomy.** Mathematical: the `ErrorField` axioms (bulk pin,
softening, monotonicity) and list arithmetic. Model: exact
field-decomposability of the energy error, wherever a hypothesis
`eModel = eRef + F.fieldSum cfg` appears. Empirical: the measured anchors
are the true field's values at the anchor coordinations (the
`Interpolates…` hypotheses; per-cell anchor numerals enter through
`DistillAtlas.EnvFieldInstances` and its binder report). Policy: the
in-range gate (`InRange…`) and any margin thresholds chosen downstream.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.AnchorBracket

open EnvironmentField AnchoredField BarrierArrhenius

/-! ## Field-sum comparison lemmas

`ErrorField.fieldSum_mono` compares one field on two configurations. The
identification question needs the transpose: two fields on one
configuration. These lemmas are stated for raw summand functions so that
both tiers (`ErrorField`, `MeasuredField`) and both envelopes reuse them. -/

/-- Two per-atom error functions that agree on every coordination of a
configuration produce the same field sum. -/
theorem mapSum_congr_on (P Q : ℕ → ℝ) (cfg : Config)
    (h : ∀ c ∈ cfg, P c = Q c) :
    (cfg.map P).sum = (cfg.map Q).sum := by
  induction cfg with
  | nil => rfl
  | cons c cfg ih =>
    simp only [List.map_cons, List.sum_cons]
    rw [h c List.mem_cons_self, ih fun c' hc' => h c' (List.mem_cons_of_mem c hc')]

/-- A per-atom error function pointwise below another on a configuration
produces a field sum below the other's. -/
theorem mapSum_le_on (P Q : ℕ → ℝ) (cfg : Config)
    (h : ∀ c ∈ cfg, P c ≤ Q c) :
    (cfg.map P).sum ≤ (cfg.map Q).sum := by
  induction cfg with
  | nil => exact le_refl _
  | cons c cfg ih =>
    simp only [List.map_cons, List.sum_cons]
    exact add_le_add (h c List.mem_cons_self)
      (ih fun c' hc' => h c' (List.mem_cons_of_mem c hc'))

/-- **The count collapse.** If two per-atom error functions agree everywhere
on a configuration except possibly at one distinguished coordination `c₀`,
their field sums differ by exactly `(count of c₀) × (pointwise difference
at c₀)`. This is the engine of the one-scalar reduction: all in-range
ambiguity collapses onto the population of the unanchored coordination. -/
theorem mapSum_sub_of_eq_off (P Q : ℕ → ℝ) (c₀ : ℕ) (cfg : Config)
    (h : ∀ c ∈ cfg, c ≠ c₀ → P c = Q c) :
    (cfg.map P).sum - (cfg.map Q).sum = (cfg.count c₀ : ℝ) * (P c₀ - Q c₀) := by
  induction cfg with
  | nil => simp
  | cons c cfg ih =>
    have ih' := ih fun c' hc' hne => h c' (List.mem_cons_of_mem c hc') hne
    by_cases hc : c = c₀
    · subst hc
      simp only [List.map_cons, List.sum_cons, List.count_cons_self]
      push_cast
      linear_combination ih'
    · have hPQ : P c = Q c := h c List.mem_cons_self hc
      have hcount : (c :: cfg).count c₀ = cfg.count c₀ := by
        simp [hc]
      simp only [List.map_cons, List.sum_cons, hcount]
      linear_combination ih' + hPQ

/-! ## The fcc layout: anchors at c = 8, 9, 11, bulk pin c = 12

The single unanchored in-range coordination is c = 10. -/

/-- A softening field is *consistent with* (interpolates) the measured fcc
anchors when it takes exactly the measured values at the three anchor
coordinations. This is the empirical hypothesis of the identification
theory: the anchors are true values of the field. -/
def InterpolatesFcc (F : ErrorField 12) (p8 p9 p11 : ℝ) : Prop :=
  F.P 8 = p8 ∧ F.P 9 = p9 ∧ F.P 11 = p11

/-- The constructed step field interpolates its own anchors. -/
theorem mkAnchoredField_interpolates (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    InterpolatesFcc (mkAnchoredField p8 p9 p11 h89 h911 h110) p8 p9 p11 :=
  ⟨rfl, rfl, rfl⟩

/-- **Existence ↔ admissibility (refusal completeness).** A softening field
through the measured fcc anchors exists iff the anchors pass the decidable
admissibility test `p8 ≤ p9 ≤ p11 ≤ 0`. The forward direction quantifies
over *all* softening fields: a cell whose anchors violate monotone
softening is consistent with **no** `ErrorField 12` at all, so its
kernel-checked refusal rules out every interpolation scheme, not merely the
clamped step field. -/
theorem exists_interpolant_iff_fcc (p8 p9 p11 : ℝ) :
    (∃ F : ErrorField 12, InterpolatesFcc F p8 p9 p11) ↔
      p8 ≤ p9 ∧ p9 ≤ p11 ∧ p11 ≤ 0 := by
  constructor
  · rintro ⟨F, h8, h9, h11⟩
    refine ⟨?_, ?_, ?_⟩
    · rw [← h8, ← h9]; exact F.mono (by omega)
    · rw [← h9, ← h11]; exact F.mono (by omega)
    · rw [← h11]; exact F.softening 11
  · rintro ⟨h89, h911, h110⟩
    exact ⟨mkAnchoredField p8 p9 p11 h89 h911 h110,
      mkAnchoredField_interpolates p8 p9 p11 h89 h911 h110⟩

/-- The scaled-integer bridge: the generator's decidable admissibility test
on ×10⁻⁴-scaled anchors decides exactly the existence of a consistent
softening field for the real anchors it encodes. Composed with a generated
refusal theorem `¬ scaledAnchorsValid a b c`, it yields the impossibility
statement: no `ErrorField 12` passes through that cell's measured anchors. -/
theorem scaledAnchorsValid_iff_exists_interpolant (a b c : Int) :
    scaledAnchorsValid a b c ↔
      ∃ F : ErrorField 12,
        InterpolatesFcc F ((a : ℝ) / 10000) ((b : ℝ) / 10000) ((c : ℝ) / 10000) := by
  rw [exists_interpolant_iff_fcc]
  unfold scaledAnchorsValid
  constructor
  · rintro ⟨h1, h2, h3⟩
    have h1' : (a : ℝ) ≤ (b : ℝ) := by exact_mod_cast h1
    have h2' : (b : ℝ) ≤ (c : ℝ) := by exact_mod_cast h2
    have h3' : (c : ℝ) ≤ 0 := by exact_mod_cast h3
    refine ⟨by linarith, by linarith, by linarith⟩
  · rintro ⟨h1, h2, h3⟩
    have h1' : (a : ℝ) ≤ (b : ℝ) := by linarith
    have h2' : (b : ℝ) ≤ (c : ℝ) := by linarith
    have h3' : (c : ℝ) ≤ 0 := by linarith
    exact ⟨by exact_mod_cast h1', by exact_mod_cast h2', by exact_mod_cast h3'⟩

/-- A consistent field agrees with the clamped step field at every in-range
coordination except possibly the unanchored c = 10: the anchors pin c = 8,
9, 11 and the bulk axiom pins everything from c = 12 up. -/
theorem interpolant_eq_step_off_gap {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11) :
    ∀ c, 8 ≤ c → c ≠ 10 → F.P c = stepField p8 p9 p11 c := by
  obtain ⟨h8, h9, h11⟩ := hF
  intro c hc hne
  rcases lt_or_ge c 12 with hlt | hge
  · interval_cases c
    · exact h8
    · exact h9
    · exact absurd rfl hne
    · exact h11
  · rw [F.bulk_anchor c hge, stepField_bulk_anchor p8 p9 p11 c hge]

/-- The unanchored gap value of a consistent field is forced between the
neighboring anchors: `p9 ≤ P 10 ≤ p11`. -/
theorem interpolant_gap_mem {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11) :
    p9 ≤ F.P 10 ∧ F.P 10 ≤ p11 := by
  obtain ⟨_, h9, h11⟩ := hF
  exact ⟨h9 ▸ F.mono (by omega), h11 ▸ F.mono (by omega)⟩

/-- A configuration is *in range* for the fcc layout when every atom's
coordination is at least the lowest anchor c = 8. This is the policy gate
under which the anchors certify finite error bars; below it,
`below_range_unidentified_fcc` shows certification is impossible. -/
def InRangeFcc (cfg : Config) : Prop := ∀ c ∈ cfg, 8 ≤ c

/-- The tier-2 anchored field and the tier-1 measured constructor compute
the same field sum: both sum the clamped step field. -/
theorem mkAnchoredField_fieldSum_eq (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) (cfg : Config) :
    (mkAnchoredField p8 p9 p11 h89 h911 h110).fieldSum cfg =
      (mkMeasuredField p8 p9 p11).fieldSum cfg := rfl

/-- **The one-scalar reduction.** On an in-range configuration, the field
sum of any consistent field is the step-field sum plus
`count₁₀ · (P 10 − p9)`: the entire ambiguity left by the three measured
anchors is the single scalar `P 10 ∈ [p9, p11]`, weighted by the population
of the unanchored coordination c = 10. Everything the anchors certify
follows from this identity. -/
theorem interpolant_fieldSum_reduction_fcc {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11) {cfg : Config} (hcfg : InRangeFcc cfg) :
    F.fieldSum cfg =
      (mkMeasuredField p8 p9 p11).fieldSum cfg
        + (cfg.count 10 : ℝ) * (F.P 10 - p9) := by
  have h := mapSum_sub_of_eq_off F.P (stepField p8 p9 p11) 10 cfg
    (fun c hc hne => interpolant_eq_step_off_gap hF c (hcfg c hc) hne)
  have hstep10 : stepField p8 p9 p11 10 = p9 := rfl
  rw [hstep10] at h
  have hFsum : F.fieldSum cfg = (cfg.map F.P).sum := rfl
  have hSsum : (mkMeasuredField p8 p9 p11).fieldSum cfg =
      (cfg.map (stepField p8 p9 p11)).sum := rfl
  rw [hFsum, hSsum]
  linarith

/-! ### The shallow envelope `stepFieldSup`

The clamped step field holds the *deeper* neighboring anchor across each
gap. Its mirror image holds the *shallower* one: `p9` only at c = 9, `p11`
across c = 10, 11. Together they are the two extremal consistent fields. -/

/-- Shallow-envelope interpolation of the three fcc anchors: `p8` up to
c = 8 (and below), `p9` at c = 9, `p11` on c = 10, 11, zero at bulk
(c ≥ 12). Where `stepField` takes the deeper side of the unanchored gap,
`stepFieldSup` takes the shallower side. -/
def stepFieldSup (p8 p9 p11 : ℝ) : ℕ → ℝ := fun c =>
  if c ≤ 8 then p8
  else if c ≤ 9 then p9
  else if c ≤ 11 then p11
  else 0

theorem stepFieldSup_bulk_anchor (p8 p9 p11 : ℝ) :
    ∀ c, 12 ≤ c → stepFieldSup p8 p9 p11 c = 0 := by
  intro c hc
  unfold stepFieldSup
  split_ifs <;> first | rfl | omega

theorem stepFieldSup_softening {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    ∀ c, stepFieldSup p8 p9 p11 c ≤ 0 := by
  intro c
  unfold stepFieldSup
  split_ifs <;> linarith

theorem stepFieldSup_monotone {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    Monotone (stepFieldSup p8 p9 p11) := by
  intro a b hab
  unfold stepFieldSup
  split_ifs <;> linarith

/-- The shallow envelope as a softening field: admissible anchors yield a
genuine `ErrorField 12` taking the shallower side of the unanchored gap. -/
def mkAnchoredFieldSup (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    ErrorField 12 where
  P := stepFieldSup p8 p9 p11
  bulk_anchor := stepFieldSup_bulk_anchor p8 p9 p11
  softening := stepFieldSup_softening h89 h911 h110
  mono := stepFieldSup_monotone h89 h911 h110

/-- The shallow envelope interpolates the measured anchors. -/
theorem mkAnchoredFieldSup_interpolates (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    InterpolatesFcc (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110) p8 p9 p11 :=
  ⟨rfl, rfl, rfl⟩

/-- The shallow envelope takes the shallower anchor across the unanchored
gap: `P 10 = p11`. -/
theorem mkAnchoredFieldSup_at_gap (p8 p9 p11 : ℝ)
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).P 10 = p11 := rfl

/-- **Deep-envelope extremality.** On the anchored range (c ≥ 8) the clamped
step field lies pointwise at or below every consistent field: it is the
most conservative (deepest) interpolation of the measured anchors — the
formal content of "the deeper (more negative) side of every gap". -/
theorem stepField_le_interpolant_inRange {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11) :
    ∀ c, 8 ≤ c → stepField p8 p9 p11 c ≤ F.P c := by
  intro c hc
  by_cases hne : c = 10
  · subst hne
    have h9 := (interpolant_gap_mem hF).1
    have hstep : stepField p8 p9 p11 10 = p9 := rfl
    rw [hstep]
    exact h9
  · rw [interpolant_eq_step_off_gap hF c hc hne]

/-- **Shallow-envelope extremality.** The shallow envelope lies pointwise at
or above every consistent field *everywhere* — including below the lowest
anchor, where monotonicity caps every consistent field by `p8`. It is the
greatest element of the set of fields consistent with the anchors. -/
theorem interpolant_le_stepFieldSup {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11) :
    ∀ c, F.P c ≤ stepFieldSup p8 p9 p11 c := by
  obtain ⟨h8, h9, h11⟩ := hF
  intro c
  unfold stepFieldSup
  split_ifs with hc8 hc9 hc11
  · exact h8 ▸ F.mono hc8
  · exact h9 ▸ F.mono hc9
  · exact h11 ▸ F.mono hc11
  · have h12 : (12 : ℕ) ≤ c := by omega
    exact le_of_eq (F.bulk_anchor c h12)

/-! ### Certified error bars on corrected energies -/

/-- **Correction never undershoots.** For an exactly field-decomposable
model on an in-range configuration, the step-field-corrected energy is at
least the reference energy: the deep envelope can only overcorrect, never
undercorrect. One half of the certified error bar. -/
theorem corrected_ge_ref_fcc {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11)
    {eModel eRef : ℝ} {cfg : Config} (hcfg : InRangeFcc cfg)
    (h : eModel = eRef + F.fieldSum cfg) :
    eRef ≤ (mkMeasuredField p8 p9 p11).corrected eModel cfg := by
  have hred := interpolant_fieldSum_reduction_fcc hF hcfg
  have hgap := (interpolant_gap_mem hF).1
  have hcount : (0 : ℝ) ≤ (cfg.count 10 : ℝ) := by positivity
  have hprod : (0 : ℝ) ≤ (cfg.count 10 : ℝ) * (F.P 10 - p9) :=
    mul_nonneg hcount (by linarith)
  unfold MeasuredField.corrected
  linarith

/-- **The certified error bar.** For an exactly field-decomposable model on
an in-range configuration, the reference energy is bracketed by computable
quantities: the corrected energy overshoots the reference by at most
`count₁₀ · (p11 − p9)` — the anchor gap times the population of the
unanchored coordination. Zero atoms at c = 10 means exact recovery. -/
theorem corrected_bracket_fcc {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11)
    {eModel eRef : ℝ} {cfg : Config} (hcfg : InRangeFcc cfg)
    (h : eModel = eRef + F.fieldSum cfg) :
    eRef ≤ (mkMeasuredField p8 p9 p11).corrected eModel cfg ∧
      (mkMeasuredField p8 p9 p11).corrected eModel cfg ≤
        eRef + (cfg.count 10 : ℝ) * (p11 - p9) := by
  refine ⟨corrected_ge_ref_fcc hF hcfg h, ?_⟩
  have hred := interpolant_fieldSum_reduction_fcc hF hcfg
  have hgap := (interpolant_gap_mem hF).2
  have hcount : (0 : ℝ) ≤ (cfg.count 10 : ℝ) := by positivity
  have hprod : (cfg.count 10 : ℝ) * (F.P 10 - p9) ≤
      (cfg.count 10 : ℝ) * (p11 - p9) :=
    mul_le_mul_of_nonneg_left (by linarith) hcount
  unfold MeasuredField.corrected
  linarith

/-! ### Margin-certified ranking

Two candidates corrected by the *same* unknown cell field: when is their
corrected order independent of which consistent field is true? -/

/-- **The two-point certification test.** The strict corrected order of two
in-range candidates holds for *every* field consistent with the anchors iff
it holds at the two envelope fields — the deep step field and the shallow
`Sup` field. The universally-quantified ranking guarantee collapses to a
two-point check on concrete fields (`norm_num`-checkable on rational anchor
data); when the check fails, the failing envelope is a concrete consistent
field on which the strict order does not hold — the anchors cannot certify
the ranking, though they may still permit a tie rather than a reversal. -/
theorem certified_order_iff_fcc {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0)
    {cfgA cfgB : Config} (hA : InRangeFcc cfgA) (hB : InRangeFcc cfgB)
    (eA eB : ℝ) :
    (∀ F : ErrorField 12, InterpolatesFcc F p8 p9 p11 →
        F.corrected eA cfgA < F.corrected eB cfgB) ↔
      ((mkAnchoredField p8 p9 p11 h89 h911 h110).corrected eA cfgA <
          (mkAnchoredField p8 p9 p11 h89 h911 h110).corrected eB cfgB ∧
        (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).corrected eA cfgA <
          (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).corrected eB cfgB) := by
  constructor
  · intro hall
    exact ⟨hall _ (mkAnchoredField_interpolates p8 p9 p11 h89 h911 h110),
      hall _ (mkAnchoredFieldSup_interpolates p8 p9 p11 h89 h911 h110)⟩
  · rintro ⟨hS, hSup⟩ F hF
    -- Reduce all six corrected values to the shared measured-tier baseline.
    have hredA := interpolant_fieldSum_reduction_fcc hF hA
    have hredB := interpolant_fieldSum_reduction_fcc hF hB
    have hredSA := interpolant_fieldSum_reduction_fcc
      (mkAnchoredField_interpolates p8 p9 p11 h89 h911 h110) hA
    have hredSB := interpolant_fieldSum_reduction_fcc
      (mkAnchoredField_interpolates p8 p9 p11 h89 h911 h110) hB
    have hredHA := interpolant_fieldSum_reduction_fcc
      (mkAnchoredFieldSup_interpolates p8 p9 p11 h89 h911 h110) hA
    have hredHB := interpolant_fieldSum_reduction_fcc
      (mkAnchoredFieldSup_interpolates p8 p9 p11 h89 h911 h110) hB
    have hSat : (mkAnchoredField p8 p9 p11 h89 h911 h110).P 10 = p9 := rfl
    have hHat : (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).P 10 = p11 := rfl
    rw [hSat] at hredSA hredSB
    rw [hHat] at hredHA hredHB
    have hgap := interpolant_gap_mem hF
    have hu0 : 0 ≤ F.P 10 - p9 := by linarith [hgap.1]
    have hug : F.P 10 - p9 ≤ p11 - p9 := by linarith [hgap.2]
    have hnA0 : (0 : ℝ) ≤ (cfgA.count 10 : ℝ) := by positivity
    have hnB0 : (0 : ℝ) ≤ (cfgB.count 10 : ℝ) := by positivity
    -- Unfold every corrected value to the shared baseline and finish by
    -- the affine endpoint argument in u := F.P 10 − p9 ∈ [0, p11 − p9].
    unfold ErrorField.corrected at hS hSup ⊢
    rw [hredA, hredB]
    rw [hredSA, hredSB] at hS
    rw [hredHA, hredHB] at hSup
    simp only [sub_self, mul_zero, add_zero] at hS
    rcases le_total ((cfgA.count 10 : ℝ) - (cfgB.count 10 : ℝ)) 0 with hk | hk
    · nlinarith [mul_le_mul_of_nonpos_left hug hk]
    · nlinarith [mul_nonneg hk hu0]

/-- **The executable two-envelope criterion, fcc.** The universal corrected
order is equivalent to two inequalities over the measured step correction:
the deep-envelope order itself, and the shallow-envelope order obtained by
subtracting each candidate's own c = 10 population times the anchor width.

Unlike the one-sided separation rule below, this criterion is exact. In
particular, equal gap populations cancel rather than charging candidate B for
an uncertainty that candidate A shares. -/
theorem certified_order_iff_endpoint_margins_fcc {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0)
    {cfgA cfgB : Config} (hA : InRangeFcc cfgA) (hB : InRangeFcc cfgB)
    (eA eB : ℝ) :
    (∀ F : ErrorField 12, InterpolatesFcc F p8 p9 p11 →
        F.corrected eA cfgA < F.corrected eB cfgB) ↔
      ((mkMeasuredField p8 p9 p11).corrected eA cfgA <
          (mkMeasuredField p8 p9 p11).corrected eB cfgB ∧
        (mkMeasuredField p8 p9 p11).corrected eA cfgA
            - (cfgA.count 10 : ℝ) * (p11 - p9) <
          (mkMeasuredField p8 p9 p11).corrected eB cfgB
            - (cfgB.count 10 : ℝ) * (p11 - p9)) := by
  have hdeepA :
      (mkAnchoredField p8 p9 p11 h89 h911 h110).corrected eA cfgA =
        (mkMeasuredField p8 p9 p11).corrected eA cfgA := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [mkAnchoredField_fieldSum_eq]
  have hdeepB :
      (mkAnchoredField p8 p9 p11 h89 h911 h110).corrected eB cfgB =
        (mkMeasuredField p8 p9 p11).corrected eB cfgB := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [mkAnchoredField_fieldSum_eq]
  have hredA := interpolant_fieldSum_reduction_fcc
    (mkAnchoredFieldSup_interpolates p8 p9 p11 h89 h911 h110) hA
  have hredB := interpolant_fieldSum_reduction_fcc
    (mkAnchoredFieldSup_interpolates p8 p9 p11 h89 h911 h110) hB
  rw [mkAnchoredFieldSup_at_gap p8 p9 p11 h89 h911 h110] at hredA hredB
  have hshallowA :
      (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).corrected eA cfgA =
        (mkMeasuredField p8 p9 p11).corrected eA cfgA
          - (cfgA.count 10 : ℝ) * (p11 - p9) := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [hredA]
    ring
  have hshallowB :
      (mkAnchoredFieldSup p8 p9 p11 h89 h911 h110).corrected eB cfgB =
        (mkMeasuredField p8 p9 p11).corrected eB cfgB
          - (cfgB.count 10 : ℝ) * (p11 - p9) := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [hredB]
    ring
  rw [certified_order_iff_fcc h89 h911 h110 hA hB]
  rw [hdeepA, hdeepB, hshallowA, hshallowB]

/-- If both exact endpoint margins pass and the two model errors are exactly
decomposed by one consistent field, the reference energies have the same
strict order. This corollary keeps the empirical field-decomposition
hypotheses explicit rather than attributing reference truth to the endpoint
test alone. -/
theorem certified_reference_order_of_endpoint_margins_fcc
    {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0)
    (hF : InterpolatesFcc F p8 p9 p11)
    {cfgA cfgB : Config} (hA : InRangeFcc cfgA) (hB : InRangeFcc cfgB)
    {eA eB refA refB : ℝ}
    (hDecompA : eA = refA + F.fieldSum cfgA)
    (hDecompB : eB = refB + F.fieldSum cfgB)
    (hdeep : (mkMeasuredField p8 p9 p11).corrected eA cfgA <
      (mkMeasuredField p8 p9 p11).corrected eB cfgB)
    (hshallow : (mkMeasuredField p8 p9 p11).corrected eA cfgA
        - (cfgA.count 10 : ℝ) * (p11 - p9) <
      (mkMeasuredField p8 p9 p11).corrected eB cfgB
        - (cfgB.count 10 : ℝ) * (p11 - p9)) :
    refA < refB := by
  have hall := (certified_order_iff_endpoint_margins_fcc
    h89 h911 h110 hA hB eA eB).2 ⟨hdeep, hshallow⟩
  have horder := hall F hF
  rw [F.corrected_exact eA refA cfgA hDecompA,
    F.corrected_exact eB refB cfgB hDecompB] at horder
  exact horder

/-- **Interval separation certifies order.** If candidate A's certified
upper bound (its corrected value) sits strictly below candidate B's
certified lower bound (its corrected value minus B's gap budget), then
every field consistent with the anchors ranks A strictly below B. The
simplest sufficient margin rule, phrased entirely in computable
quantities — this is the check a promotion gate can run. -/
theorem certified_order_of_separation_fcc {p8 p9 p11 : ℝ}
    {cfgA cfgB : Config} (hA : InRangeFcc cfgA) (hB : InRangeFcc cfgB)
    {eA eB : ℝ}
    (hsep : (mkMeasuredField p8 p9 p11).corrected eA cfgA <
      (mkMeasuredField p8 p9 p11).corrected eB cfgB
        - (cfgB.count 10 : ℝ) * (p11 - p9)) :
    ∀ F : ErrorField 12, InterpolatesFcc F p8 p9 p11 →
      F.corrected eA cfgA < F.corrected eB cfgB := by
  intro F hF
  have hredA := interpolant_fieldSum_reduction_fcc hF hA
  have hredB := interpolant_fieldSum_reduction_fcc hF hB
  have hgap := interpolant_gap_mem hF
  have hnA0 : (0 : ℝ) ≤ (cfgA.count 10 : ℝ) := by positivity
  have hnB0 : (0 : ℝ) ≤ (cfgB.count 10 : ℝ) := by positivity
  have hprodA : (0 : ℝ) ≤ (cfgA.count 10 : ℝ) * (F.P 10 - p9) :=
    mul_nonneg hnA0 (by linarith [hgap.1])
  have hprodB : (cfgB.count 10 : ℝ) * (F.P 10 - p9) ≤
      (cfgB.count 10 : ℝ) * (p11 - p9) :=
    mul_le_mul_of_nonneg_left (by linarith [hgap.2]) hnB0
  unfold ErrorField.corrected
  unfold MeasuredField.corrected at hsep
  rw [hredA, hredB]
  linarith

/-! ### Certified kinetics: barrier and rate error bars -/

/-- **The certified barrier bracket.** For a migration event with both
endpoint configurations in range, the step-corrected barrier is within
`|count₁₀(TS) − count₁₀(init)| · (p11 − p9)` of the true reference barrier.
The gap budget of a *barrier* is controlled by the imbalance of the
unanchored populations, not their sum: a transition state and basin with
equal c = 10 populations have an exactly-corrected barrier. -/
theorem corrected_barrier_bracket_fcc {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11)
    {eModelInit eModelTS eRefInit eRefTS : ℝ} {cfgInit cfgTS : Config}
    (hInitR : InRangeFcc cfgInit) (hTSR : InRangeFcc cfgTS)
    (hInit : eModelInit = eRefInit + F.fieldSum cfgInit)
    (hTS : eModelTS = eRefTS + F.fieldSum cfgTS) :
    |((mkMeasuredField p8 p9 p11).corrected eModelTS cfgTS
        - (mkMeasuredField p8 p9 p11).corrected eModelInit cfgInit)
      - (eRefTS - eRefInit)| ≤
      |(cfgTS.count 10 : ℝ) - (cfgInit.count 10 : ℝ)| * (p11 - p9) := by
  have hredI := interpolant_fieldSum_reduction_fcc hF hInitR
  have hredT := interpolant_fieldSum_reduction_fcc hF hTSR
  have hgap := interpolant_gap_mem hF
  have hkey : (mkMeasuredField p8 p9 p11).corrected eModelTS cfgTS
      - (mkMeasuredField p8 p9 p11).corrected eModelInit cfgInit
      - (eRefTS - eRefInit)
      = ((cfgTS.count 10 : ℝ) - (cfgInit.count 10 : ℝ)) * (F.P 10 - p9) := by
    unfold MeasuredField.corrected
    have h1 : (mkMeasuredField p8 p9 p11).fieldSum cfgTS =
        F.fieldSum cfgTS - (cfgTS.count 10 : ℝ) * (F.P 10 - p9) := by
      linarith [hredT]
    have h2 : (mkMeasuredField p8 p9 p11).fieldSum cfgInit =
        F.fieldSum cfgInit - (cfgInit.count 10 : ℝ) * (F.P 10 - p9) := by
      linarith [hredI]
    rw [h1, h2]
    linear_combination hTS - hInit
  rw [hkey, abs_mul]
  have hu : |F.P 10 - p9| ≤ p11 - p9 := by
    rw [abs_le]
    constructor <;> linarith [hgap.1, hgap.2]
  exact mul_le_mul_of_nonneg_left hu (abs_nonneg _)

/-- Barriers within `W` of each other have Arrhenius rates within a factor
`exp (W / kT)` — the bracket-to-rate bridge, by the exact amplification
identity. Stated for one direction; swap the barriers for the other. -/
theorem hopRate_le_of_barrier_close {E₁ E₂ W ν kT : ℝ}
    (hν : 0 ≤ ν) (hkT : 0 < kT) (hclose : E₁ - E₂ ≤ W) :
    hopRate ν E₂ kT ≤ Real.exp (W / kT) * hopRate ν E₁ kT := by
  have hE : E₁ - W ≤ E₂ := by linarith
  have hmono : boltzmann E₂ kT ≤ boltzmann (E₁ - W) kT :=
    boltzmann_antitone hkT hE
  have hfactor : boltzmann (E₁ - W) kT = Real.exp (W / kT) * boltzmann E₁ kT :=
    boltzmann_error_factor E₁ W kT
  unfold hopRate
  calc ν * boltzmann E₂ kT ≤ ν * (Real.exp (W / kT) * boltzmann E₁ kT) := by
        rw [← hfactor]
        exact mul_le_mul_of_nonneg_left hmono hν
    _ = Real.exp (W / kT) * (ν * boltzmann E₁ kT) := by ring

/-- **The certified rate cap.** The true Arrhenius rate of a migration event
with in-range endpoints is within a factor `exp (W / kT)` of the rate
computed from the step-corrected barrier, where
`W = |count₁₀(TS) − count₁₀(init)| · (p11 − p9)` is the certified barrier
bracket. Correction turns an *unbounded* softening error (raw uMLIP
kinetics) into a certified multiplicative error bar. -/
theorem rate_factor_cap_fcc {F : ErrorField 12} {p8 p9 p11 : ℝ}
    (hF : InterpolatesFcc F p8 p9 p11)
    {eModelInit eModelTS eRefInit eRefTS ν kT : ℝ} {cfgInit cfgTS : Config}
    (hν : 0 ≤ ν) (hkT : 0 < kT)
    (hInitR : InRangeFcc cfgInit) (hTSR : InRangeFcc cfgTS)
    (hInit : eModelInit = eRefInit + F.fieldSum cfgInit)
    (hTS : eModelTS = eRefTS + F.fieldSum cfgTS) :
    hopRate ν (eRefTS - eRefInit) kT ≤
        Real.exp ((|(cfgTS.count 10 : ℝ) - (cfgInit.count 10 : ℝ)| * (p11 - p9)) / kT)
          * hopRate ν
              ((mkMeasuredField p8 p9 p11).corrected eModelTS cfgTS
                - (mkMeasuredField p8 p9 p11).corrected eModelInit cfgInit) kT ∧
      hopRate ν
          ((mkMeasuredField p8 p9 p11).corrected eModelTS cfgTS
            - (mkMeasuredField p8 p9 p11).corrected eModelInit cfgInit) kT ≤
        Real.exp ((|(cfgTS.count 10 : ℝ) - (cfgInit.count 10 : ℝ)| * (p11 - p9)) / kT)
          * hopRate ν (eRefTS - eRefInit) kT := by
  have hbr := corrected_barrier_bracket_fcc hF hInitR hTSR hInit hTS
  rw [abs_le] at hbr
  constructor
  · exact hopRate_le_of_barrier_close hν hkT (by linarith [hbr.2])
  · exact hopRate_le_of_barrier_close hν hkT (by linarith [hbr.1])

/-! ### Honest non-identifiability -/

/-- **Below the anchored range, the anchors certify nothing.** Every value
`v ≤ p8` is realized at c = 7 by some field consistent with the anchors:
the set of consistent per-atom errors below the lowest anchor is unbounded.
This is the formal reason the platform clamps and refuses below range
rather than extrapolating — no finite below-range error bar is provable
from the anchors alone. -/
theorem below_range_unidentified_fcc {p8 p9 p11 : ℝ}
    (h89 : p8 ≤ p9) (h911 : p9 ≤ p11) (h110 : p11 ≤ 0) :
    ∀ v ≤ p8, ∃ F : ErrorField 12, InterpolatesFcc F p8 p9 p11 ∧ F.P 7 = v := by
  intro v hv
  have hstep_ge : ∀ b : ℕ, p8 ≤ stepField p8 p9 p11 b := by
    intro b
    unfold stepField
    split_ifs <;> linarith
  refine ⟨⟨fun c => if c ≤ 7 then v else stepField p8 p9 p11 c, ?_, ?_, ?_⟩,
    ⟨?_, ?_, ?_⟩, ?_⟩
  · intro c hc
    show (if c ≤ 7 then v else stepField p8 p9 p11 c) = 0
    have h7 : ¬ c ≤ 7 := by omega
    rw [if_neg h7]
    exact stepField_bulk_anchor p8 p9 p11 c hc
  · intro c
    show (if c ≤ 7 then v else stepField p8 p9 p11 c) ≤ 0
    by_cases hc : c ≤ 7
    · rw [if_pos hc]; linarith
    · rw [if_neg hc]
      exact stepField_softening h89 h911 h110 c
  · intro a b hab
    show (if a ≤ 7 then v else stepField p8 p9 p11 a) ≤
      (if b ≤ 7 then v else stepField p8 p9 p11 b)
    by_cases ha : a ≤ 7
    · by_cases hb : b ≤ 7
      · rw [if_pos ha, if_pos hb]
      · rw [if_pos ha, if_neg hb]
        linarith [hstep_ge b]
    · have hb : ¬ b ≤ 7 := by omega
      rw [if_neg ha, if_neg hb]
      exact stepField_monotone h89 h911 h110 hab
  · rfl
  · rfl
  · rfl
  · rfl

/-- **The measured tier does not identify the gap.** Without the softening
and monotonicity axioms, even the in-range coordination c = 10 is
completely free: every real value is realized by some `MeasuredField 12`
through the anchors. The tier-2 directional hypotheses are exactly what
buys the finite bracket of `corrected_bracket_fcc` — the two-tier
architecture is load-bearing, not decorative. -/
theorem measured_gap_unidentified_fcc (p8 p9 p11 : ℝ) :
    ∀ v : ℝ, ∃ M : MeasuredField 12,
      (M.P 8 = p8 ∧ M.P 9 = p9 ∧ M.P 11 = p11) ∧ M.P 10 = v := by
  intro v
  refine ⟨⟨fun c => if c = 10 then v else stepField p8 p9 p11 c, ?_⟩,
    ⟨?_, ?_, ?_⟩, ?_⟩
  · intro c hc
    show (if c = 10 then v else stepField p8 p9 p11 c) = 0
    have h10 : ¬ c = 10 := by omega
    rw [if_neg h10]
    exact stepField_bulk_anchor p8 p9 p11 c hc
  · rfl
  · rfl
  · rfl
  · rfl

/-! ## The bcc layout: anchors at c = 4, 6, 7, bulk pin c = 8

The single unanchored in-range coordination is c = 5, sitting in the gap
between the (100) anchor (c = 4) and the (110) anchor (c = 6). The theory
mirrors the fcc case, with the gap value forced into `[p4, p6]`. The
kinetics corollaries follow the fcc pattern verbatim and are not
duplicated. -/

/-- Consistency with the measured bcc anchors. -/
def InterpolatesBcc (F : ErrorField 8) (p4 p6 p7 : ℝ) : Prop :=
  F.P 4 = p4 ∧ F.P 6 = p6 ∧ F.P 7 = p7

/-- The constructed bcc step field interpolates its own anchors. -/
theorem mkAnchoredFieldBcc_interpolates (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    InterpolatesBcc (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70) p4 p6 p7 :=
  ⟨rfl, rfl, rfl⟩

/-- **Existence ↔ admissibility, bcc.** A softening field through the
measured bcc anchors exists iff `p4 ≤ p6 ≤ p7 ≤ 0`: every generated bcc
refusal certifies that no `ErrorField 8` is consistent with the cell. -/
theorem exists_interpolant_iff_bcc (p4 p6 p7 : ℝ) :
    (∃ F : ErrorField 8, InterpolatesBcc F p4 p6 p7) ↔
      p4 ≤ p6 ∧ p6 ≤ p7 ∧ p7 ≤ 0 := by
  constructor
  · rintro ⟨F, h4, h6, h7⟩
    refine ⟨?_, ?_, ?_⟩
    · rw [← h4, ← h6]; exact F.mono (by omega)
    · rw [← h6, ← h7]; exact F.mono (by omega)
    · rw [← h7]; exact F.softening 7
  · rintro ⟨h46, h67, h70⟩
    exact ⟨mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70,
      mkAnchoredFieldBcc_interpolates p4 p6 p7 h46 h67 h70⟩

/-- The scaled-integer bridge for the bcc layout. -/
theorem scaledAnchorsBccValid_iff_exists_interpolant (a b c : Int) :
    scaledAnchorsBccValid a b c ↔
      ∃ F : ErrorField 8,
        InterpolatesBcc F ((a : ℝ) / 10000) ((b : ℝ) / 10000) ((c : ℝ) / 10000) := by
  rw [exists_interpolant_iff_bcc]
  unfold scaledAnchorsBccValid
  constructor
  · rintro ⟨h1, h2, h3⟩
    have h1' : (a : ℝ) ≤ (b : ℝ) := by exact_mod_cast h1
    have h2' : (b : ℝ) ≤ (c : ℝ) := by exact_mod_cast h2
    have h3' : (c : ℝ) ≤ 0 := by exact_mod_cast h3
    refine ⟨by linarith, by linarith, by linarith⟩
  · rintro ⟨h1, h2, h3⟩
    have h1' : (a : ℝ) ≤ (b : ℝ) := by linarith
    have h2' : (b : ℝ) ≤ (c : ℝ) := by linarith
    have h3' : (c : ℝ) ≤ 0 := by linarith
    exact ⟨by exact_mod_cast h1', by exact_mod_cast h2', by exact_mod_cast h3'⟩

/-- A consistent bcc field agrees with the bcc step field at every in-range
coordination except possibly the unanchored c = 5. -/
theorem interpolant_eq_stepBcc_off_gap {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7) :
    ∀ c, 4 ≤ c → c ≠ 5 → F.P c = stepFieldBcc p4 p6 p7 c := by
  obtain ⟨h4, h6, h7⟩ := hF
  intro c hc hne
  rcases lt_or_ge c 8 with hlt | hge
  · interval_cases c
    · exact h4
    · exact absurd rfl hne
    · exact h6
    · exact h7
  · rw [F.bulk_anchor c hge, stepFieldBcc_bulk_anchor p4 p6 p7 c hge]

/-- The unanchored bcc gap value is forced between its neighboring anchors:
`p4 ≤ P 5 ≤ p6`. -/
theorem interpolant_gap_mem_bcc {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7) :
    p4 ≤ F.P 5 ∧ F.P 5 ≤ p6 := by
  obtain ⟨h4, h6, _⟩ := hF
  exact ⟨h4 ▸ F.mono (by omega), h6 ▸ F.mono (by omega)⟩

/-- In-range gate for the bcc layout: every coordination at least the
lowest anchor c = 4. -/
def InRangeBcc (cfg : Config) : Prop := ∀ c ∈ cfg, 4 ≤ c

/-- **The one-scalar reduction, bcc.** On an in-range configuration, any
consistent field's sum is the bcc step-field sum plus
`count₅ · (P 5 − p4)` with `P 5 ∈ [p4, p6]` forced. -/
theorem interpolant_fieldSum_reduction_bcc {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7) {cfg : Config} (hcfg : InRangeBcc cfg) :
    F.fieldSum cfg =
      (mkMeasuredFieldBcc p4 p6 p7).fieldSum cfg
        + (cfg.count 5 : ℝ) * (F.P 5 - p4) := by
  have h := mapSum_sub_of_eq_off F.P (stepFieldBcc p4 p6 p7) 5 cfg
    (fun c hc hne => interpolant_eq_stepBcc_off_gap hF c (hcfg c hc) hne)
  have hstep5 : stepFieldBcc p4 p6 p7 5 = p4 := rfl
  rw [hstep5] at h
  have hFsum : F.fieldSum cfg = (cfg.map F.P).sum := rfl
  have hSsum : (mkMeasuredFieldBcc p4 p6 p7).fieldSum cfg =
      (cfg.map (stepFieldBcc p4 p6 p7)).sum := rfl
  rw [hFsum, hSsum]
  linarith

/-- **The certified error bar, bcc.** The reference energy of an in-range
configuration is bracketed: correction never undershoots, and overshoots by
at most `count₅ · (p6 − p4)`. -/
theorem corrected_bracket_bcc {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7)
    {eModel eRef : ℝ} {cfg : Config} (hcfg : InRangeBcc cfg)
    (h : eModel = eRef + F.fieldSum cfg) :
    eRef ≤ (mkMeasuredFieldBcc p4 p6 p7).corrected eModel cfg ∧
      (mkMeasuredFieldBcc p4 p6 p7).corrected eModel cfg ≤
        eRef + (cfg.count 5 : ℝ) * (p6 - p4) := by
  have hred := interpolant_fieldSum_reduction_bcc hF hcfg
  have hgap := interpolant_gap_mem_bcc hF
  have hcount : (0 : ℝ) ≤ (cfg.count 5 : ℝ) := by positivity
  have hlo : (0 : ℝ) ≤ (cfg.count 5 : ℝ) * (F.P 5 - p4) :=
    mul_nonneg hcount (by linarith [hgap.1])
  have hhi : (cfg.count 5 : ℝ) * (F.P 5 - p4) ≤ (cfg.count 5 : ℝ) * (p6 - p4) :=
    mul_le_mul_of_nonneg_left (by linarith [hgap.2]) hcount
  unfold MeasuredField.corrected
  constructor <;> linarith

/-- Shallow-envelope interpolation of the bcc anchors: `p4` up to c = 4
(and below), `p6` on c = 5, 6, `p7` at c = 7, zero at bulk (c ≥ 8). -/
def stepFieldBccSup (p4 p6 p7 : ℝ) : ℕ → ℝ := fun c =>
  if c ≤ 4 then p4
  else if c ≤ 6 then p6
  else if c ≤ 7 then p7
  else 0

theorem stepFieldBccSup_bulk_anchor (p4 p6 p7 : ℝ) :
    ∀ c, 8 ≤ c → stepFieldBccSup p4 p6 p7 c = 0 := by
  intro c hc
  unfold stepFieldBccSup
  split_ifs <;> first | rfl | omega

theorem stepFieldBccSup_softening {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    ∀ c, stepFieldBccSup p4 p6 p7 c ≤ 0 := by
  intro c
  unfold stepFieldBccSup
  split_ifs <;> linarith

theorem stepFieldBccSup_monotone {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    Monotone (stepFieldBccSup p4 p6 p7) := by
  intro a b hab
  unfold stepFieldBccSup
  split_ifs <;> linarith

/-- The bcc shallow envelope as a softening field. -/
def mkAnchoredFieldBccSup (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    ErrorField 8 where
  P := stepFieldBccSup p4 p6 p7
  bulk_anchor := stepFieldBccSup_bulk_anchor p4 p6 p7
  softening := stepFieldBccSup_softening h46 h67 h70
  mono := stepFieldBccSup_monotone h46 h67 h70

/-- The bcc shallow envelope interpolates the measured anchors. -/
theorem mkAnchoredFieldBccSup_interpolates (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    InterpolatesBcc (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70) p4 p6 p7 :=
  ⟨rfl, rfl, rfl⟩

/-- The bcc shallow envelope takes the shallower anchor across the
unanchored gap: `P 5 = p6`. -/
theorem mkAnchoredFieldBccSup_at_gap (p4 p6 p7 : ℝ)
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0) :
    (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).P 5 = p6 := rfl

/-- **Deep-envelope extremality, bcc.** On the anchored range (c ≥ 4) the
bcc step field lies pointwise at or below every consistent field. -/
theorem stepFieldBcc_le_interpolant_inRange {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7) :
    ∀ c, 4 ≤ c → stepFieldBcc p4 p6 p7 c ≤ F.P c := by
  intro c hc
  by_cases hne : c = 5
  · subst hne
    have h4 := (interpolant_gap_mem_bcc hF).1
    have hstep : stepFieldBcc p4 p6 p7 5 = p4 := rfl
    rw [hstep]
    exact h4
  · rw [interpolant_eq_stepBcc_off_gap hF c hc hne]

/-- **Shallow-envelope extremality, bcc.** The bcc shallow envelope lies
pointwise at or above every consistent field everywhere. -/
theorem interpolant_le_stepFieldBccSup {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (hF : InterpolatesBcc F p4 p6 p7) :
    ∀ c, F.P c ≤ stepFieldBccSup p4 p6 p7 c := by
  obtain ⟨h4, h6, h7⟩ := hF
  intro c
  unfold stepFieldBccSup
  split_ifs with hc4 hc6 hc7
  · exact h4 ▸ F.mono hc4
  · exact h6 ▸ F.mono hc6
  · exact h7 ▸ F.mono hc7
  · have h8 : (8 : ℕ) ≤ c := by omega
    exact le_of_eq (F.bulk_anchor c h8)

/-- **The two-point certification test, bcc.** The strict corrected order
holds for every field consistent with the bcc anchors iff it holds at the
deep and shallow envelopes. -/
theorem certified_order_iff_bcc {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0)
    {cfgA cfgB : Config} (hA : InRangeBcc cfgA) (hB : InRangeBcc cfgB)
    (eA eB : ℝ) :
    (∀ F : ErrorField 8, InterpolatesBcc F p4 p6 p7 →
        F.corrected eA cfgA < F.corrected eB cfgB) ↔
      ((mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).corrected eA cfgA <
          (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).corrected eB cfgB ∧
        (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).corrected eA cfgA <
          (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).corrected eB cfgB) := by
  constructor
  · intro hall
    exact ⟨hall _ (mkAnchoredFieldBcc_interpolates p4 p6 p7 h46 h67 h70),
      hall _ (mkAnchoredFieldBccSup_interpolates p4 p6 p7 h46 h67 h70)⟩
  · rintro ⟨hS, hSup⟩ F hF
    have hredA := interpolant_fieldSum_reduction_bcc hF hA
    have hredB := interpolant_fieldSum_reduction_bcc hF hB
    have hredSA := interpolant_fieldSum_reduction_bcc
      (mkAnchoredFieldBcc_interpolates p4 p6 p7 h46 h67 h70) hA
    have hredSB := interpolant_fieldSum_reduction_bcc
      (mkAnchoredFieldBcc_interpolates p4 p6 p7 h46 h67 h70) hB
    have hredHA := interpolant_fieldSum_reduction_bcc
      (mkAnchoredFieldBccSup_interpolates p4 p6 p7 h46 h67 h70) hA
    have hredHB := interpolant_fieldSum_reduction_bcc
      (mkAnchoredFieldBccSup_interpolates p4 p6 p7 h46 h67 h70) hB
    have hSat : (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).P 5 = p4 := rfl
    have hHat : (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).P 5 = p6 := rfl
    rw [hSat] at hredSA hredSB
    rw [hHat] at hredHA hredHB
    have hgap := interpolant_gap_mem_bcc hF
    have hu0 : 0 ≤ F.P 5 - p4 := by linarith [hgap.1]
    have hug : F.P 5 - p4 ≤ p6 - p4 := by linarith [hgap.2]
    have hnA0 : (0 : ℝ) ≤ (cfgA.count 5 : ℝ) := by positivity
    have hnB0 : (0 : ℝ) ≤ (cfgB.count 5 : ℝ) := by positivity
    unfold ErrorField.corrected at hS hSup ⊢
    rw [hredA, hredB]
    rw [hredSA, hredSB] at hS
    rw [hredHA, hredHB] at hSup
    simp only [sub_self, mul_zero, add_zero] at hS
    rcases le_total ((cfgA.count 5 : ℝ) - (cfgB.count 5 : ℝ)) 0 with hk | hk
    · nlinarith [mul_le_mul_of_nonpos_left hug hk]
    · nlinarith [mul_nonneg hk hu0]

/-- **The executable two-envelope criterion, bcc.** The bcc universal
corrected order is equivalent to strict order at the measured deep envelope
and at the shallow envelope formed by subtracting each candidate's own c = 5
population times `p6 - p4`. -/
theorem certified_order_iff_endpoint_margins_bcc {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0)
    {cfgA cfgB : Config} (hA : InRangeBcc cfgA) (hB : InRangeBcc cfgB)
    (eA eB : ℝ) :
    (∀ F : ErrorField 8, InterpolatesBcc F p4 p6 p7 →
        F.corrected eA cfgA < F.corrected eB cfgB) ↔
      ((mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA <
          (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB ∧
        (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA
            - (cfgA.count 5 : ℝ) * (p6 - p4) <
          (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB
            - (cfgB.count 5 : ℝ) * (p6 - p4)) := by
  have hdeepA :
      (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).corrected eA cfgA =
        (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA := rfl
  have hdeepB :
      (mkAnchoredFieldBcc p4 p6 p7 h46 h67 h70).corrected eB cfgB =
        (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB := rfl
  have hredA := interpolant_fieldSum_reduction_bcc
    (mkAnchoredFieldBccSup_interpolates p4 p6 p7 h46 h67 h70) hA
  have hredB := interpolant_fieldSum_reduction_bcc
    (mkAnchoredFieldBccSup_interpolates p4 p6 p7 h46 h67 h70) hB
  rw [mkAnchoredFieldBccSup_at_gap p4 p6 p7 h46 h67 h70] at hredA hredB
  have hshallowA :
      (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).corrected eA cfgA =
        (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA
          - (cfgA.count 5 : ℝ) * (p6 - p4) := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [hredA]
    ring
  have hshallowB :
      (mkAnchoredFieldBccSup p4 p6 p7 h46 h67 h70).corrected eB cfgB =
        (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB
          - (cfgB.count 5 : ℝ) * (p6 - p4) := by
    unfold ErrorField.corrected MeasuredField.corrected
    rw [hredB]
    ring
  rw [certified_order_iff_bcc h46 h67 h70 hA hB]
  rw [hdeepA, hdeepB, hshallowA, hshallowB]

/-- The reference-order closure of the exact bcc endpoint criterion under
explicit exact field-decomposition hypotheses. -/
theorem certified_reference_order_of_endpoint_margins_bcc
    {F : ErrorField 8} {p4 p6 p7 : ℝ}
    (h46 : p4 ≤ p6) (h67 : p6 ≤ p7) (h70 : p7 ≤ 0)
    (hF : InterpolatesBcc F p4 p6 p7)
    {cfgA cfgB : Config} (hA : InRangeBcc cfgA) (hB : InRangeBcc cfgB)
    {eA eB refA refB : ℝ}
    (hDecompA : eA = refA + F.fieldSum cfgA)
    (hDecompB : eB = refB + F.fieldSum cfgB)
    (hdeep : (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA <
      (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB)
    (hshallow : (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA
        - (cfgA.count 5 : ℝ) * (p6 - p4) <
      (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB
        - (cfgB.count 5 : ℝ) * (p6 - p4)) :
    refA < refB := by
  have hall := (certified_order_iff_endpoint_margins_bcc
    h46 h67 h70 hA hB eA eB).2 ⟨hdeep, hshallow⟩
  have horder := hall F hF
  rw [F.corrected_exact eA refA cfgA hDecompA,
    F.corrected_exact eB refB cfgB hDecompB] at horder
  exact horder

/-- **Interval separation certifies order, bcc.** The bcc mirror of
`certified_order_of_separation_fcc`: if A's corrected value sits strictly
below B's corrected value minus B's c = 5 gap budget, every consistent
field ranks A strictly below B. -/
theorem certified_order_of_separation_bcc {p4 p6 p7 : ℝ}
    {cfgA cfgB : Config} (hA : InRangeBcc cfgA) (hB : InRangeBcc cfgB)
    {eA eB : ℝ}
    (hsep : (mkMeasuredFieldBcc p4 p6 p7).corrected eA cfgA <
      (mkMeasuredFieldBcc p4 p6 p7).corrected eB cfgB
        - (cfgB.count 5 : ℝ) * (p6 - p4)) :
    ∀ F : ErrorField 8, InterpolatesBcc F p4 p6 p7 →
      F.corrected eA cfgA < F.corrected eB cfgB := by
  intro F hF
  have hredA := interpolant_fieldSum_reduction_bcc hF hA
  have hredB := interpolant_fieldSum_reduction_bcc hF hB
  have hgap := interpolant_gap_mem_bcc hF
  have hnA0 : (0 : ℝ) ≤ (cfgA.count 5 : ℝ) := by positivity
  have hnB0 : (0 : ℝ) ≤ (cfgB.count 5 : ℝ) := by positivity
  have hprodA : (0 : ℝ) ≤ (cfgA.count 5 : ℝ) * (F.P 5 - p4) :=
    mul_nonneg hnA0 (by linarith [hgap.1])
  have hprodB : (cfgB.count 5 : ℝ) * (F.P 5 - p4) ≤
      (cfgB.count 5 : ℝ) * (p6 - p4) :=
    mul_le_mul_of_nonneg_left (by linarith [hgap.2]) hnB0
  unfold ErrorField.corrected
  unfold MeasuredField.corrected at hsep
  rw [hredA, hredB]
  linarith

/-! ## The diamond layout: single anchor at c = 3, bulk pin c = 4

There is no unanchored in-range coordination, so the identification is
*complete*: in range, the measured anchor determines the field sum exactly —
even at the measured tier, where no softening or monotonicity is assumed.
The single-anchor layout is the fully-identified degenerate case of the
bracket theory: its gap budget is zero. -/

/-- In-range gate for the diamond layout: every coordination at least the
anchor c = 3. -/
def InRangeDiamond (cfg : Config) : Prop := ∀ c ∈ cfg, 3 ≤ c

/-- **Existence ↔ admissibility, diamond.** A softening field through the
single measured diamond anchor exists iff `p3 ≤ 0`. -/
theorem exists_interpolant_iff_diamond (p3 : ℝ) :
    (∃ F : ErrorField 4, F.P 3 = p3) ↔ p3 ≤ 0 := by
  constructor
  · rintro ⟨F, h3⟩
    rw [← h3]
    exact F.softening 3
  · intro h30
    exact ⟨mkAnchoredFieldDiamond p3 h30, rfl⟩

/-- The scaled-integer bridge for the diamond layout. -/
theorem scaledAnchorDiamondValid_iff_exists_interpolant (a : Int) :
    scaledAnchorDiamondValid a ↔
      ∃ F : ErrorField 4, F.P 3 = (a : ℝ) / 10000 := by
  rw [exists_interpolant_iff_diamond]
  unfold scaledAnchorDiamondValid
  constructor
  · intro h
    have h' : (a : ℝ) ≤ 0 := by exact_mod_cast h
    linarith
  · intro h
    have h' : (a : ℝ) ≤ 0 := by linarith
    exact_mod_cast h'

/-- **Complete identification, diamond, measured tier.** Any measured field
through the diamond anchor — no softening, no monotonicity assumed —
computes exactly the step-field sum on every in-range configuration: with
no unanchored coordination between anchor and bulk, the measurement leaves
zero freedom. The diamond gap budget is zero. -/
theorem measured_fieldSum_exact_diamond {M : MeasuredField 4} {p3 : ℝ}
    (hM : M.P 3 = p3) {cfg : Config} (hcfg : InRangeDiamond cfg) :
    M.fieldSum cfg = (mkMeasuredFieldDiamond p3).fieldSum cfg := by
  have hcongr : ∀ c ∈ cfg, M.P c = stepFieldDiamond p3 c := by
    intro c hc
    have h3c : 3 ≤ c := hcfg c hc
    rcases lt_or_ge c 4 with hlt | hge
    · interval_cases c
      exact hM
    · rw [M.bulk_anchor c hge, stepFieldDiamond_bulk_anchor p3 c hge]
  exact mapSum_congr_on M.P (stepFieldDiamond p3) cfg hcongr

/-- **Exact correction, diamond.** For an exactly field-decomposable model
on an in-range diamond configuration, the step-field correction recovers
the reference energy *exactly* — not within a bracket: the single anchor
fully identifies the in-range field. -/
theorem corrected_exact_diamond {M : MeasuredField 4} {p3 : ℝ}
    (hM : M.P 3 = p3) {eModel eRef : ℝ} {cfg : Config}
    (hcfg : InRangeDiamond cfg) (h : eModel = eRef + M.fieldSum cfg) :
    (mkMeasuredFieldDiamond p3).corrected eModel cfg = eRef := by
  have hex := measured_fieldSum_exact_diamond hM hcfg
  unfold MeasuredField.corrected
  linarith

/-! ## The rocksalt layout: single anchor at c = 5, bulk pin c = 6

The rocksalt mirror of the diamond case: one anchor, no unanchored in-range
coordination, so in-range identification is complete at the measured tier
and the gap budget is zero. The binder currently emits no bound rocksalt
cells (the statics runs carry no anchor observables), but the layout's
identification laws are ready for when charge-balanced slab and defect
runs land. -/

/-- In-range gate for the rocksalt layout: every coordination at least the
anchor c = 5. -/
def InRangeRocksalt (cfg : Config) : Prop := ∀ c ∈ cfg, 5 ≤ c

/-- **Existence ↔ admissibility, rocksalt.** A softening field through the
single measured rocksalt anchor exists iff `p5 ≤ 0`. -/
theorem exists_interpolant_iff_rocksalt (p5 : ℝ) :
    (∃ F : ErrorField 6, F.P 5 = p5) ↔ p5 ≤ 0 := by
  constructor
  · rintro ⟨F, h5⟩
    rw [← h5]
    exact F.softening 5
  · intro h50
    exact ⟨mkAnchoredFieldRocksalt p5 h50, rfl⟩

/-- The scaled-integer bridge for the rocksalt layout. -/
theorem scaledAnchorRocksaltValid_iff_exists_interpolant (a : Int) :
    scaledAnchorRocksaltValid a ↔
      ∃ F : ErrorField 6, F.P 5 = (a : ℝ) / 10000 := by
  rw [exists_interpolant_iff_rocksalt]
  unfold scaledAnchorRocksaltValid
  constructor
  · intro h
    have h' : (a : ℝ) ≤ 0 := by exact_mod_cast h
    linarith
  · intro h
    have h' : (a : ℝ) ≤ 0 := by linarith
    exact_mod_cast h'

/-- **Complete identification, rocksalt, measured tier.** Any measured field
through the rocksalt anchor computes exactly the step-field sum on every
in-range configuration: zero gap budget. -/
theorem measured_fieldSum_exact_rocksalt {M : MeasuredField 6} {p5 : ℝ}
    (hM : M.P 5 = p5) {cfg : Config} (hcfg : InRangeRocksalt cfg) :
    M.fieldSum cfg = (mkMeasuredFieldRocksalt p5).fieldSum cfg := by
  have hcongr : ∀ c ∈ cfg, M.P c = stepFieldRocksalt p5 c := by
    intro c hc
    have h5c : 5 ≤ c := hcfg c hc
    rcases lt_or_ge c 6 with hlt | hge
    · interval_cases c
      exact hM
    · rw [M.bulk_anchor c hge, stepFieldRocksalt_bulk_anchor p5 c hge]
  exact mapSum_congr_on M.P (stepFieldRocksalt p5) cfg hcongr

/-- **Exact correction, rocksalt.** For an exactly field-decomposable model
on an in-range rocksalt configuration, the step-field correction recovers
the reference energy exactly. -/
theorem corrected_exact_rocksalt {M : MeasuredField 6} {p5 : ℝ}
    (hM : M.P 5 = p5) {eModel eRef : ℝ} {cfg : Config}
    (hcfg : InRangeRocksalt cfg) (h : eModel = eRef + M.fieldSum cfg) :
    (mkMeasuredFieldRocksalt p5).corrected eModel cfg = eRef := by
  have hex := measured_fieldSum_exact_rocksalt hM hcfg
  unfold MeasuredField.corrected
  linarith

/-! ## Gate compatibility: the runtime domain gate and the in-range policy

The runtime's first-shell domain gate (`SorptionStability.FieldDomain`,
mirrored by `lupine_distill.odf.field_certificates.check_field_domain`)
admits configurations inside a measured interval `[cmin, cmax]`. The bracket
laws above apply under the `InRange…` predicates — every coordination at
least the layout's lowest anchor. These lemmas make the compatibility
condition explicit and checkable: **a domain gate implies the bracket
precondition exactly when its lower edge sits at or above the layout's
lowest anchor.** In particular the platform's default fcc domain
`[4, 12]` does *not* discharge `InRangeFcc` (its floor is below the c = 8
anchor); a gate must run with `cmin ≥ 8` for the fcc bracket certificates
to attach. Runtime policy weaker than the proved precondition is surfaced
here as a hypothesis, not hidden. -/

open SorptionStability in
/-- A domain-gate pass discharges the fcc in-range precondition whenever the
gate's floor is at or above the lowest fcc anchor c = 8. -/
theorem inRangeFcc_of_admits {D : FieldDomain} (h8 : 8 ≤ D.cmin)
    {cfg : Config} (h : D.admits cfg = true) : InRangeFcc cfg := by
  intro c hc
  have := (FieldDomain.admits_iff D cfg).mp h c hc
  omega

open SorptionStability in
/-- A domain-gate pass discharges the bcc in-range precondition whenever the
gate's floor is at or above the lowest bcc anchor c = 4 — in particular the
platform's default `[4, 12]` domain suffices for bcc. -/
theorem inRangeBcc_of_admits {D : FieldDomain} (h4 : 4 ≤ D.cmin)
    {cfg : Config} (h : D.admits cfg = true) : InRangeBcc cfg := by
  intro c hc
  have := (FieldDomain.admits_iff D cfg).mp h c hc
  omega

open SorptionStability in
/-- A domain-gate pass discharges the diamond in-range precondition whenever
the gate's floor is at or above the diamond anchor c = 3. -/
theorem inRangeDiamond_of_admits {D : FieldDomain} (h3 : 3 ≤ D.cmin)
    {cfg : Config} (h : D.admits cfg = true) : InRangeDiamond cfg := by
  intro c hc
  have := (FieldDomain.admits_iff D cfg).mp h c hc
  omega

open SorptionStability in
/-- A domain-gate pass discharges the rocksalt in-range precondition whenever
the gate's floor is at or above the rocksalt anchor c = 5. -/
theorem inRangeRocksalt_of_admits {D : FieldDomain} (h5 : 5 ≤ D.cmin)
    {cfg : Config} (h : D.admits cfg = true) : InRangeRocksalt cfg := by
  intro c hc
  have := (FieldDomain.admits_iff D cfg).mp h c hc
  omega

end OpenDistillationFactory.Materials.Theory.AnchorBracket
