import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

/-!
# Exact quadratic critical-value response

This module supplies a closed-form, zero-remainder certificate for the local
response theorem in one physical coordinate.  It is an exact test case for the
general implicit-function statement in the manuscript and includes minima and
one-dimensional saddle directions according to the sign of `curvature`.
-/

namespace OpenDistillationFactory.HonestErrors.Response

/-- An affine landscape perturbation of a nondegenerate quadratic critical point. -/
noncomputable def quadraticEnergy
    (base curvature force vertical ε x : ℝ) : ℝ :=
  base + curvature * x ^ 2 / 2 + ε * (force * x + vertical)

/-- The continued stationary point of `quadraticEnergy`. -/
noncomputable def quadraticCriticalPoint (curvature force ε : ℝ) : ℝ :=
  -ε * force / curvature

/-- The continued critical value. -/
noncomputable def quadraticCriticalValue
    (base curvature force vertical ε : ℝ) : ℝ :=
  quadraticEnergy base curvature force vertical ε
    (quadraticCriticalPoint curvature force ε)

/-- The declared critical point solves the exact stationarity equation. -/
theorem quadratic_stationary
    {curvature force ε : ℝ} (hcurvature : curvature ≠ 0) :
    curvature * quadraticCriticalPoint curvature force ε + ε * force = 0 := by
  unfold quadraticCriticalPoint
  field_simp [hcurvature]
  ring

/--
Exact critical-value response: vertical evaluation is the complete first-order
term and critical-point motion contributes the inverse-curvature quadratic term.
-/
theorem quadraticCriticalValue_exact
    {base curvature force vertical ε : ℝ}
    (hcurvature : curvature ≠ 0) :
    quadraticCriticalValue base curvature force vertical ε =
      base + ε * vertical - ε ^ 2 * force ^ 2 / (2 * curvature) := by
  unfold quadraticCriticalValue quadraticEnergy quadraticCriticalPoint
  field_simp [hcurvature]
  ring

/-- At zero perturbation the continued critical value is the reference value. -/
theorem quadraticCriticalValue_zero
    (base curvature force vertical : ℝ) :
    quadraticCriticalValue base curvature force vertical 0 = base := by
  simp [quadraticCriticalValue, quadraticEnergy, quadraticCriticalPoint]

/-- The vertical approximation has an exact signed-compliance error. -/
theorem vertical_error_exact
    {base curvature force vertical ε : ℝ}
    (hcurvature : curvature ≠ 0) :
    quadraticCriticalValue base curvature force vertical ε -
        (base + ε * vertical) =
      -ε ^ 2 * force ^ 2 / (2 * curvature) := by
  rw [quadraticCriticalValue_exact hcurvature]
  ring

/--
For a nonzero perturbation, the normalized second-order correction equals the
inverse-Hessian compliance coefficient exactly.
-/
theorem normalized_vertical_error
    {base curvature force vertical ε : ℝ}
    (hcurvature : curvature ≠ 0) (hε : ε ≠ 0) :
    (quadraticCriticalValue base curvature force vertical ε -
        (base + ε * vertical)) / ε ^ 2 =
      -force ^ 2 / (2 * curvature) := by
  rw [vertical_error_exact hcurvature]
  field_simp [hε]

/-- A positive-curvature mode lowers the critical value at quadratic order. -/
theorem stable_mode_correction_nonpos
    {curvature force : ℝ} (hcurvature : 0 < curvature) :
    -force ^ 2 / (2 * curvature) ≤ 0 := by
  have hquotient : 0 ≤ force ^ 2 / (2 * curvature) := by positivity
  simpa only [neg_div] using neg_nonpos.mpr hquotient

/-- A negative-curvature mode raises the critical value at quadratic order. -/
theorem unstable_mode_correction_nonneg
    {curvature force : ℝ} (hcurvature : curvature < 0) :
    0 ≤ -force ^ 2 / (2 * curvature) := by
  have hdenominator : 2 * curvature ≤ 0 := by linarith
  have hquotient : force ^ 2 / (2 * curvature) ≤ 0 :=
    div_nonpos_of_nonneg_of_nonpos (sq_nonneg force) hdenominator
  simpa only [neg_div] using neg_nonneg.mpr hquotient

end OpenDistillationFactory.HonestErrors.Response
