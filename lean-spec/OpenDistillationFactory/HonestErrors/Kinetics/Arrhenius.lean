import Mathlib.Analysis.SpecialFunctions.Exp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
# Exact Arrhenius transport of a barrier error

The theorem is conditional on the report's stated approximation: fixed pathway,
fixed prefactor, and positive thermal energy.  Decimal factors such as `10.34` or
`1.18 × 10^5` are intentionally not asserted without certified transcendental
interval bounds.
-/

namespace OpenDistillationFactory.HonestErrors.Kinetics

noncomputable def arrheniusRate
    (prefactor barrier thermalEnergy : ℝ) : ℝ :=
  prefactor * Real.exp (-barrier / thermalEnergy)

def signedBarrierError (predicted reference : ℝ) : ℝ :=
  predicted - reference

theorem arrhenius_transport
    {prefactor predicted reference thermalEnergy : ℝ}
    (hthermal : thermalEnergy ≠ 0) :
    arrheniusRate prefactor predicted thermalEnergy =
      Real.exp
          (-signedBarrierError predicted reference / thermalEnergy) *
        arrheniusRate prefactor reference thermalEnergy := by
  unfold arrheniusRate signedBarrierError
  calc
    prefactor * Real.exp (-predicted / thermalEnergy) =
        prefactor * Real.exp
          (-(predicted - reference) / thermalEnergy +
            (-reference / thermalEnergy)) := by
          congr 2
          field_simp [hthermal]
          ring
    _ = prefactor *
        (Real.exp (-(predicted - reference) / thermalEnergy) *
          Real.exp (-reference / thermalEnergy)) := by
          rw [Real.exp_add]
    _ = Real.exp (-(predicted - reference) / thermalEnergy) *
        (prefactor * Real.exp (-reference / thermalEnergy)) := by ring

/-! This theorem is an algebraic factor identity; strict amplification is proved below. -/
theorem underestimate_factor_identity
    {prefactor predicted reference thermalEnergy error : ℝ}
    (hthermal : thermalEnergy ≠ 0)
    (hpredicted : predicted = reference - error) :
    arrheniusRate prefactor predicted thermalEnergy =
      Real.exp (error / thermalEnergy) *
        arrheniusRate prefactor reference thermalEnergy := by
  rw [arrhenius_transport hthermal]
  congr 2
  simp only [signedBarrierError, hpredicted]
  ring

theorem positive_underestimate_factor_gt_one
    {thermalEnergy error : ℝ}
    (hthermal : 0 < thermalEnergy) (herror : 0 < error) :
    1 < Real.exp (error / thermalEnergy) := by
  exact Real.one_lt_exp_iff.mpr (div_pos herror hthermal)

/-- With positive prefactor and thermal energy, a positive underestimate strictly raises rate. -/
theorem positive_underestimate_increases_rate
    {prefactor reference thermalEnergy error : ℝ}
    (hprefactor : 0 < prefactor)
    (hthermal : 0 < thermalEnergy)
    (herror : 0 < error) :
    arrheniusRate prefactor reference thermalEnergy <
      arrheniusRate prefactor (reference - error) thermalEnergy := by
  have href : 0 < arrheniusRate prefactor reference thermalEnergy := by
    exact mul_pos hprefactor (Real.exp_pos _)
  have hfactor : 1 < Real.exp (error / thermalEnergy) :=
    positive_underestimate_factor_gt_one hthermal herror
  calc
    arrheniusRate prefactor reference thermalEnergy =
        1 * arrheniusRate prefactor reference thermalEnergy := by ring
    _ < Real.exp (error / thermalEnergy) *
        arrheniusRate prefactor reference thermalEnergy :=
      mul_lt_mul_of_pos_right hfactor href
    _ = arrheniusRate prefactor (reference - error) thermalEnergy := by
      symm
      exact underestimate_factor_identity (ne_of_gt hthermal) rfl

theorem rate_factor_bounds_of_abs_barrier_error
    {predicted reference thermalEnergy radius : ℝ}
    (hthermal : 0 < thermalEnergy)
    (herror : |predicted - reference| ≤ radius) :
    Real.exp (-radius / thermalEnergy) ≤
        Real.exp (-(predicted - reference) / thermalEnergy) ∧
      Real.exp (-(predicted - reference) / thermalEnergy) ≤
        Real.exp (radius / thermalEnergy) := by
  rcases abs_le.mp herror with ⟨hlower, hupper⟩
  constructor
  · apply Real.exp_le_exp.mpr
    apply div_le_div_of_nonneg_right
    · linarith
    · exact le_of_lt hthermal
  · apply Real.exp_le_exp.mpr
    apply div_le_div_of_nonneg_right
    · linarith
    · exact le_of_lt hthermal

end OpenDistillationFactory.HonestErrors.Kinetics
