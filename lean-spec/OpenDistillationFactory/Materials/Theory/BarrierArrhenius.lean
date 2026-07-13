import Mathlib.Analysis.Complex.ExponentialBounds
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import OpenDistillationFactory.Materials.Theory.EnvironmentField

/-!
# Barrier softening under the Arrhenius law: exponential error amplification

The kinetic properties that decide whether a climate-critical material works —
Li⁺ hopping in halide solid electrolytes, transition-metal migration in
cobalt-free LMR cathodes, vacancy-mediated oxidation in tin perovskites — obey
the Arrhenius/Boltzmann law: rate ∝ exp(−Ea / kB T). A *linear* error in the
barrier is an *exponential* error in the rate. This module proves that chain
end to end:

1. `boltzmann_error_factor` / `hopRate_error_factor` — the amplification
   identity: underestimating a barrier by δ multiplies the predicted rate by
   exactly exp(δ / kT).
2. `boltzmann_antitone` — monotonicity: lower barrier, faster rate. Combined
   with the environment error field, softening *always overestimates*
   mobility.
3. `softened_barrier_underestimates` — the mechanism theorem: when the
   transition state is under-coordinated relative to the initial basin
   (pointwise, under a matching) and the model error is field-decomposable,
   the model barrier is at most the reference barrier.
4. `corrected_barrier_exact` — runtime correction restores the exact
   reference barrier.
5. `exp_ge_two_pow` and the numeric locks: at room temperature
   (kB·300 K = 25.85 meV = 517/20 meV),
   * `barrier_error_100meV_amplifies_32x` and `…_at_most_64x` — a 100 meV
     barrier error changes a hopping rate by a factor strictly bracketed in
     (32, 64): the "roughly 50×" of the proof pack, now with proved bounds;
   * `halide_barrier_error_three_orders` — the 60 % underestimation of a
     300 meV Li⁺ barrier reported for uMLIPs (δ = 180 meV) overstates
     conductivity by more than 1000×: fast-ion conductors and insulators
     become indistinguishable without correction.
6. `softening_never_hides_conductor` / `false_positive_iff` — softening
   errors are one-sided: a true fast-ion conductor is never misread as an
   insulator; the failure mode of raw screening is the false positive, and it
   occurs exactly when the error crosses the classification threshold.

House rules: zero `sorry`, zero new axioms. Numeric bounds use the
Mathlib-verified decimal bounds on log 2; nothing is asserted about exp
beyond what the kernel checks.
-/

namespace OpenDistillationFactory.Materials.Theory.BarrierArrhenius

open EnvironmentField

/-- Boltzmann factor `exp(−E / kT)`. With `E` a formation energy this is the
equilibrium defect site-fraction (dilute limit); with `E` an activation energy
it is the activated-hop success probability. -/
noncomputable def boltzmann (E kT : ℝ) : ℝ := Real.exp (-(E / kT))

/-- Harmonic transition-state-theory (Vineyard) hop rate: attempt frequency ν
times the Boltzmann factor of the migration barrier `Ea`. -/
noncomputable def hopRate (ν Ea kT : ℝ) : ℝ := ν * boltzmann Ea kT

theorem boltzmann_pos (E kT : ℝ) : 0 < boltzmann E kT := Real.exp_pos _

theorem hopRate_pos (ν Ea kT : ℝ) (hν : 0 < ν) : 0 < hopRate ν Ea kT :=
  mul_pos hν (boltzmann_pos Ea kT)

/-- Lower barrier, faster process: the Boltzmann factor is antitone in the
energy at any positive temperature. -/
theorem boltzmann_antitone {E₁ E₂ kT : ℝ} (hkT : 0 < kT) (h : E₁ ≤ E₂) :
    boltzmann E₂ kT ≤ boltzmann E₁ kT := by
  unfold boltzmann
  apply Real.exp_le_exp.mpr
  have hdiv : E₁ / kT ≤ E₂ / kT := by
    rw [div_eq_mul_inv, div_eq_mul_inv]
    exact mul_le_mul_of_nonneg_right h (inv_nonneg.mpr hkT.le)
  linarith

/-- Strict version: a strictly lower barrier gives a strictly faster process. -/
theorem boltzmann_strictAnti {E₁ E₂ kT : ℝ} (hkT : 0 < kT) (h : E₁ < E₂) :
    boltzmann E₂ kT < boltzmann E₁ kT := by
  unfold boltzmann
  apply Real.exp_lt_exp.mpr
  have hdiv : E₁ / kT < E₂ / kT := by
    rw [div_eq_mul_inv, div_eq_mul_inv]
    exact mul_lt_mul_of_pos_right h (inv_pos.mpr hkT)
  linarith

/-- **The amplification identity (Boltzmann form).** Underestimating an energy
by δ multiplies the Boltzmann factor by exactly `exp(δ / kT)`. An identity —
no hypotheses, no approximation. -/
theorem boltzmann_error_factor (E δ kT : ℝ) :
    boltzmann (E - δ) kT = Real.exp (δ / kT) * boltzmann E kT := by
  unfold boltzmann
  rw [show -((E - δ) / kT) = δ / kT + -(E / kT) by rw [sub_div]; ring,
    Real.exp_add]

/-- **The amplification identity (rate form).** A barrier error δ multiplies
the predicted hop rate — hence ionic conductivity via Nernst–Einstein — by
exactly `exp(δ / kT)`. -/
theorem hopRate_error_factor (ν Ea δ kT : ℝ) :
    hopRate ν (Ea - δ) kT = Real.exp (δ / kT) * hopRate ν Ea kT := by
  unfold hopRate
  rw [boltzmann_error_factor]
  ring

/-! ## The mechanism: softening ⇒ barrier underestimation ⇒ rate overestimation -/

/-- **The mechanism theorem.** In a migration event whose transition state is
under-coordinated relative to the initial basin (pointwise, under a matching
of the atoms), a field-decomposable softened model *underestimates the
barrier*: `E_model^barrier ≤ E_ref^barrier`. This is the formal core of "uMLIPs
systematically underestimate the migration barriers that govern voltage fade
because the transition state involves under-coordinated metal ions". -/
theorem softened_barrier_underestimates {cBulk : ℕ} (F : ErrorField cBulk)
    (eModelInit eModelTS eRefInit eRefTS : ℝ) (cfgInit cfgTS : Config)
    (hInit : eModelInit = eRefInit + F.fieldSum cfgInit)
    (hTS : eModelTS = eRefTS + F.fieldSum cfgTS)
    (hUnder : List.Forall₂ (· ≤ ·) cfgTS cfgInit) :
    eModelTS - eModelInit ≤ eRefTS - eRefInit := by
  have h := F.fieldSum_mono cfgTS cfgInit hUnder
  linarith

/-- **Correction restores the exact barrier.** Runtime correction applied to
both endpoints of a field-decomposable migration event returns the reference
barrier exactly. -/
theorem corrected_barrier_exact {cBulk : ℕ} (F : ErrorField cBulk)
    (eModelInit eModelTS eRefInit eRefTS : ℝ) (cfgInit cfgTS : Config)
    (hInit : eModelInit = eRefInit + F.fieldSum cfgInit)
    (hTS : eModelTS = eRefTS + F.fieldSum cfgTS) :
    F.corrected eModelTS cfgTS - F.corrected eModelInit cfgInit =
      eRefTS - eRefInit := by
  rw [F.corrected_exact eModelTS eRefTS cfgTS hTS,
    F.corrected_exact eModelInit eRefInit cfgInit hInit]

/-- **Softening overestimates mobility.** The raw model's predicted hop rate is
at least the reference rate whenever the transition state is under-coordinated
relative to the initial basin: softened screening inflates every candidate's
kinetics. -/
theorem softened_rate_overestimates {cBulk : ℕ} (F : ErrorField cBulk)
    (ν kT eModelInit eModelTS eRefInit eRefTS : ℝ) (cfgInit cfgTS : Config)
    (hν : 0 < ν) (hkT : 0 < kT)
    (hInit : eModelInit = eRefInit + F.fieldSum cfgInit)
    (hTS : eModelTS = eRefTS + F.fieldSum cfgTS)
    (hUnder : List.Forall₂ (· ≤ ·) cfgTS cfgInit) :
    hopRate ν (eRefTS - eRefInit) kT ≤ hopRate ν (eModelTS - eModelInit) kT := by
  unfold hopRate
  exact mul_le_mul_of_nonneg_left
    (boltzmann_antitone hkT
      (softened_barrier_underestimates F eModelInit eModelTS eRefInit eRefTS
        cfgInit cfgTS hInit hTS hUnder))
    hν.le

/-! ## Order-of-magnitude locks

Room temperature: kB · 300 K = 8.617 × 10⁻² meV/K · 300 K = 25.85 meV
= 517/20 meV. Barrier errors below are in meV. The bounds ride on Mathlib's
verified decimal bounds for log 2. -/

/-- Bridge from powers of two to the exponential: if `n·log 2 ≤ x` then
`2^n ≤ exp x`. Turns "orders of magnitude" claims into kernel-checkable
inequalities. -/
theorem exp_ge_two_pow (n : ℕ) (x : ℝ) (h : (n : ℝ) * Real.log 2 ≤ x) :
    (2 : ℝ) ^ n ≤ Real.exp x := by
  calc (2 : ℝ) ^ n = Real.exp (Real.log 2) ^ n := by
        rw [Real.exp_log (by norm_num : (0 : ℝ) < 2)]
    _ = Real.exp ((n : ℝ) * Real.log 2) := (Real.exp_nat_mul _ n).symm
    _ ≤ Real.exp x := Real.exp_le_exp.mpr h

/-- Companion upper bridge: if `x ≤ n·log 2` then `exp x ≤ 2^n`. -/
theorem exp_le_two_pow (n : ℕ) (x : ℝ) (h : x ≤ (n : ℝ) * Real.log 2) :
    Real.exp x ≤ (2 : ℝ) ^ n := by
  calc Real.exp x ≤ Real.exp ((n : ℝ) * Real.log 2) := Real.exp_le_exp.mpr h
    _ = Real.exp (Real.log 2) ^ n := Real.exp_nat_mul _ n
    _ = (2 : ℝ) ^ n := by rw [Real.exp_log (by norm_num : (0 : ℝ) < 2)]

/-- **A 100 meV barrier error is at least a 32× rate error at room
temperature.** Lower half of the proof pack's "roughly 50×" claim:
exp(100 / 25.85) > 2⁵ = 32, because 5·log 2 < 100/(517/20). -/
theorem barrier_error_100meV_amplifies_32x :
    (32 : ℝ) ≤ Real.exp ((100 : ℝ) / (517 / 20)) := by
  have hlog := Real.log_two_lt_d9
  have h : ((5 : ℕ) : ℝ) * Real.log 2 ≤ (100 : ℝ) / (517 / 20) := by
    push_cast
    nlinarith
  calc (32 : ℝ) = 2 ^ (5 : ℕ) := by norm_num
    _ ≤ Real.exp ((100 : ℝ) / (517 / 20)) := exp_ge_two_pow 5 _ h

/-- **…and at most a 64× rate error.** Upper half of the bracket:
exp(100 / 25.85) < 2⁶ = 64, because 100/(517/20) < 6·log 2. The proof pack's
"≈50×" sits strictly inside the proved interval (32, 64). -/
theorem barrier_error_100meV_amplifies_at_most_64x :
    Real.exp ((100 : ℝ) / (517 / 20)) ≤ 64 := by
  have hlog := Real.log_two_gt_d9
  have h : (100 : ℝ) / (517 / 20) ≤ ((6 : ℕ) : ℝ) * Real.log 2 := by
    push_cast
    nlinarith
  calc Real.exp ((100 : ℝ) / (517 / 20)) ≤ 2 ^ (6 : ℕ) := exp_le_two_pow 6 _ h
    _ = 64 := by norm_num

/-- **The halide-electrolyte false-classification lock.** uMLIPs underestimate
Li⁺ migration barriers by 60 %+ (Deng et al. 2025); on a typical 300 meV
halide barrier that is δ = 180 meV, and exp(180 / 25.85) > 2¹⁰ = 1024 > 10³:
the predicted room-temperature conductivity is wrong by more than three orders
of magnitude. Screening by raw uMLIP kinetics cannot distinguish a superionic
conductor from an ordinary ion conductor at this error level. -/
theorem halide_barrier_error_three_orders :
    (1000 : ℝ) ≤ Real.exp ((180 : ℝ) / (517 / 20)) := by
  have hlog := Real.log_two_lt_d9
  have h : ((10 : ℕ) : ℝ) * Real.log 2 ≤ (180 : ℝ) / (517 / 20) := by
    push_cast
    nlinarith
  calc (1000 : ℝ) ≤ 2 ^ (10 : ℕ) := by norm_num
    _ ≤ Real.exp ((180 : ℝ) / (517 / 20)) := exp_ge_two_pow 10 _ h

/-! ## Classification: softening errors are one-sided -/

/-- A candidate is classified as a (fast-ion) conductor at threshold `EaStar`
when its migration barrier does not exceed the threshold. -/
def ConductorAt (Ea EaStar : ℝ) : Prop := Ea ≤ EaStar

/-- **Softening never hides a conductor.** If the model barrier underestimates
the true barrier (the softening direction), every true conductor is still
classified as a conductor by the model. Raw softened screening has no false
negatives on conductivity — its failure mode is the false positive. -/
theorem softening_never_hides_conductor {eModel eTrue EaStar : ℝ}
    (h : eModel ≤ eTrue) (hc : ConductorAt eTrue EaStar) :
    ConductorAt eModel EaStar :=
  le_trans h hc

/-- **False positives are exactly threshold crossings.** The model calls a
candidate a conductor while the reference calls it an insulator iff the pair
of barriers straddles the classification threshold. The wasted-synthesis
failure mode is a provable, checkable event — not a vague uncertainty. -/
theorem false_positive_iff (eModel eTrue EaStar : ℝ) :
    (ConductorAt eModel EaStar ∧ ¬ ConductorAt eTrue EaStar) ↔
      (eModel ≤ EaStar ∧ EaStar < eTrue) := by
  simp [ConductorAt, not_le]

end OpenDistillationFactory.Materials.Theory.BarrierArrhenius
