import Mathlib.Data.Real.Basic
import Mathlib.Algebra.Order.BigOperators.Group.List
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum

/-! # Climate forcers beyond CO₂

The climate-materials program is not only about CO₂ abatement. Methane (CH₄),
nitrous oxide (N₂O), and fluorinated refrigerants (HFCs, SF₆) are responsible
for a large share of near-term warming and are deeply tied to materials:
- low-GWP refrigerants and heat-pump working fluids,
- methane-oxidation catalysts and leak-sealing membranes,
- nitrous-emitting fertilizer catalysts and nitrous-decomposition materials.

This module formalizes the radiative-forcing accounting that connects those
materials to climate outcomes. All numerical claims are stated as integer- or
rational-scaled bounds so they can be kernel-checked; the central estimates are
drawn from IPCC AR6 WGI Table 7.15 (100-year and 20-year GWPs) and NOAA/AGAGE
lifetime values.

House rules: zero `sorry`, zero new axioms.
-/

namespace OpenDistillationFactory.Materials.Theory.ClimateForcers

/-- The principal climate forcers treated in the expansion series.
Values are 100-year global warming potentials (GWP₁₀₀) relative to CO₂.
We use AR6 central estimates rounded to integers for kernel arithmetic. -/
inductive ClimateForcer
  | co2
  | methane
  | nitrousOxide
  | hfc134a
  | hfc410a
  | sf6
  deriving DecidableEq, Repr, Inhabited

namespace ClimateForcer

/-- 100-year GWP (relative to CO₂ = 1) from IPCC AR6 WGI Table 7.15.
Methane uses the fossil-fuel/feedstock central estimate; bounds below capture
the non-fossil estimate as well. -/
def gwp100 : ClimateForcer → ℕ
  | .co2           => 1
  | .methane       => 29
  | .nitrousOxide  => 273
  | .hfc134a       => 1530
  | .hfc410a       => 2088
  | .sf6           => 25200

/-- 20-year GWP (relative to CO₂ = 1) from IPCC AR6 WGI Table 7.15.
Short-lived climate forcers such as methane are far more potent on this horizon. -/
def gwp20 : ClimateForcer → ℕ
  | .co2           => 1
  | .methane       => 81
  | .nitrousOxide  => 273
  | .hfc134a       => 4140
  | .hfc410a       => 5760
  | .sf6           => 27800

/-- Atmospheric lifetime in years, rounded from AR6 / NOAA best estimates.
Methane ~12 yr, N₂O ~109 yr, HFC-134a ~14 yr, HFC-410A ~16.9 yr, SF₆ ~3200 yr. -/
def lifetimeYears : ClimateForcer → ℕ
  | .co2           => 1000  -- long-tail abstraction; CO₂ is the reference
  | .methane       => 12
  | .nitrousOxide  => 109
  | .hfc134a       => 14
  | .hfc410a       => 17
  | .sf6           => 3200

theorem gwp100_pos (f : ClimateForcer) : 0 < gwp100 f := by
  cases f <;> decide

theorem gwp20_pos (f : ClimateForcer) : 0 < gwp20 f := by
  cases f <;> decide

theorem lifetime_pos (f : ClimateForcer) : 0 < lifetimeYears f := by
  cases f <;> decide

/-- CO₂-equivalent mass for a given emitted mass and forcer.
Mass and result share the same mass unit; GWP is dimensionless. -/
def co2e (mass : ℝ) (f : ClimateForcer) : ℝ := mass * (gwp100 f : ℝ)

theorem co2e_pos {mass : ℝ} {f : ClimateForcer} (hm : 0 < mass) : 0 < co2e mass f := by
  unfold co2e
  have hg : 0 < (gwp100 f : ℝ) := by exact_mod_cast gwp100_pos f
  exact mul_pos hm hg

/-- CO₂-equivalent is strictly monotone in emitted mass. -/
theorem co2e_monotone_mass {m₁ m₂ : ℝ} {f : ClimateForcer} (h : m₁ ≤ m₂) :
    co2e m₁ f ≤ co2e m₂ f := by
  unfold co2e
  have hg : 0 < (gwp100 f : ℝ) := by exact_mod_cast gwp100_pos f
  exact mul_le_mul_of_nonneg_right h hg.le

/-- A larger-GWP forcer dominates the CO₂e of an equal mass. -/
theorem co2e_monotone_gwp {mass : ℝ} {f₁ f₂ : ClimateForcer}
    (hm : 0 ≤ mass) (hg : gwp100 f₁ ≤ gwp100 f₂) :
    co2e mass f₁ ≤ co2e mass f₂ := by
  unfold co2e
  exact mul_le_mul_of_nonneg_left (by exact_mod_cast hg) hm

/-- The short-horizon CO₂e of a forcer, used for near-term warming budgets. -/
def co2e20 (mass : ℝ) (f : ClimateForcer) : ℝ := mass * (gwp20 f : ℝ)

/-- For non-CO₂ forcers, the 20-year GWP is at least the 100-year GWP. -/
theorem gwp20_ge_gwp100 (f : ClimateForcer) (hf : f ≠ .co2) :
    gwp100 f ≤ gwp20 f := by
  cases f with
  | co2 => contradiction
  | methane => decide
  | nitrousOxide => decide
  | hfc134a => decide
  | hfc410a => decide
  | sf6 => decide

/-- Near-term CO₂e is at least long-term CO₂e for any non-CO₂ forcer. -/
theorem co2e20_ge_co2e {mass : ℝ} (hm : 0 ≤ mass) {f : ClimateForcer}
    (hf : f ≠ .co2) :
    co2e mass f ≤ co2e20 mass f := by
  unfold co2e co2e20
  exact mul_le_mul_of_nonneg_left (by exact_mod_cast gwp20_ge_gwp100 f hf) hm

end ClimateForcer

open ClimateForcer

/-! ## Bounds that make the forcers comparable in CO₂e

These theorems are the formal counterpart of statements like
"one kilogram of R-410A is nearly two tonnes of CO₂e" or
"methane is ~30–80× CO₂ depending on horizon". -/

/-- A 1 kg leak of HFC-410A is more than 1 tonne (1000 kg) of CO₂e on the
100-year horizon. This is why heat-pump working-fluid choice dominates the
embodied-climate impact of small-residential systems. -/
theorem hfc410a_1kg_exceeds_1tonne_co2e :
    1000 < co2e 1 .hfc410a := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- A 1 kg leak of HFC-134a is more than 1 tonne (1000 kg) of CO₂e on the
100-year horizon. -/
theorem hfc134a_1kg_exceeds_1tonne_co2e :
    1000 < co2e 1 .hfc134a := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- A 1 kg release of SF₆ exceeds 25 tonnes of CO₂e — the reason electrical
switchgear leak detection is a materials-integrity problem. -/
theorem sf6_1kg_exceeds_25tonne_co2e :
    25000 < co2e 1 .sf6 := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- Methane's 100-year GWP is bracketed between 27 and 30, covering both
fossil and non-fossil AR6 central estimates. -/
theorem methane_gwp100_bounds :
    27 ≤ gwp100 .methane ∧ gwp100 .methane ≤ 30 := by decide

/-- Methane's 20-year GWP is bracketed between 80 and 85. -/
theorem methane_gwp20_bounds :
    80 ≤ gwp20 .methane ∧ gwp20 .methane ≤ 85 := by decide

/-- Nitrous oxide's 100-year GWP is bracketed between 265 and 280. -/
theorem nitrous_oxide_gwp100_bounds :
    265 ≤ gwp100 .nitrousOxide ∧ gwp100 .nitrousOxide ≤ 280 := by decide

/-- Replacing 1 kg of HFC-410A with 1 kg of CO₂ (or a CO₂-equivalent working
fluid) saves more than 2 tonnes of CO₂e on the 100-year horizon. -/
theorem hfc410a_substitution_savings :
    co2e 1 .hfc410a - co2e 1 .co2 > 2000 := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-- Replacing 1 kg of HFC-134a with 1 kg of CO₂ saves more than 1.5 tonnes
of CO₂e on the 100-year horizon. -/
theorem hfc134a_substitution_savings :
    co2e 1 .hfc134a - co2e 1 .co2 > 1500 := by
  simp [co2e, ClimateForcer.gwp100]
  norm_num

/-! ## Aggregate forcer accounting

A materials platform may be asked to certify a mixed emissions footprint
(e.g., a refrigerant blend, or a process stream containing CH₄ and N₂O).
The lemmas below keep those sums monotone and positive. -/

/-- Total 100-year CO₂e of a list of (mass, forcer) pairs. -/
def totalCo2e (entries : List (ℝ × ClimateForcer)) : ℝ :=
  (entries.map fun p => co2e p.1 p.2).sum

theorem totalCo2e_pos {entries : List (ℝ × ClimateForcer)}
    (h : ∀ p ∈ entries, 0 ≤ p.1) :
    0 ≤ totalCo2e entries := by
  unfold totalCo2e
  apply List.sum_nonneg
  intro x hx
  simp at hx
  rcases hx with ⟨r, f, hr, rfl⟩
  unfold co2e
  have hg : 0 < (gwp100 f : ℝ) := by exact_mod_cast gwp100_pos f
  exact mul_nonneg (h (r, f) hr) hg.le

/-- Adding a non-negative entry can only increase the total CO₂e footprint. -/
theorem totalCo2e_append_nonneg {entries : List (ℝ × ClimateForcer)}
    {mass : ℝ} {f : ClimateForcer} (hm : 0 ≤ mass) :
    totalCo2e entries ≤ totalCo2e (entries ++ [(mass, f)]) := by
  unfold totalCo2e
  rw [List.map_append, List.sum_append]
  simp [co2e]
  have hg : 0 < (gwp100 f : ℝ) := by exact_mod_cast gwp100_pos f
  linarith [mul_nonneg hm hg.le]

end OpenDistillationFactory.Materials.Theory.ClimateForcers
