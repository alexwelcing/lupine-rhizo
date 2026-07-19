import OpenDistillationFactory.HonestErrors.Kinetics.Arrhenius
import OpenDistillationFactory.HonestErrors.Response.Barrier

/-!
# Bridge from the quadratic barrier certificate to rate response

This module is the direct bridge between *Activated Barriers on Quotient
Configuration Spaces* and the barrier-error program in *Hard Materials, Honest
Errors*.  It composes two conditional models; it does not assert that a real
material is quadratic or that Arrhenius kinetics is complete.
-/

namespace OpenDistillationFactory.HonestErrors.Response

open OpenDistillationFactory.HonestErrors.Kinetics

noncomputable def quadraticBarrierShift
    (minimumCurvature minimumForce minimumVertical
      saddleCurvature saddleForce saddleVertical ε : ℝ) : ℝ :=
  ε * (saddleVertical - minimumVertical) -
  ε ^ 2 / 2 *
    (saddleForce ^ 2 / saddleCurvature -
     minimumForce ^ 2 / minimumCurvature)

theorem quadraticBarrier_arrhenius_exact
    {minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical
      ε prefactor thermalEnergy : ℝ}
    (hminimum : minimumCurvature ≠ 0)
    (hsaddle : saddleCurvature ≠ 0)
    (hthermal : 0 < thermalEnergy) :
    arrheniusRate prefactor
        (quadraticBarrier
          minimumBase minimumCurvature minimumForce minimumVertical
          saddleBase saddleCurvature saddleForce saddleVertical ε)
        thermalEnergy =
      Real.exp
          (-quadraticBarrierShift
            minimumCurvature minimumForce minimumVertical
            saddleCurvature saddleForce saddleVertical ε /
            thermalEnergy) *
        arrheniusRate prefactor (saddleBase - minimumBase) thermalEnergy := by
  calc
    arrheniusRate prefactor
        (quadraticBarrier
          minimumBase minimumCurvature minimumForce minimumVertical
          saddleBase saddleCurvature saddleForce saddleVertical ε)
        thermalEnergy =
      Real.exp
          (-signedBarrierError
            (quadraticBarrier
              minimumBase minimumCurvature minimumForce minimumVertical
              saddleBase saddleCurvature saddleForce saddleVertical ε)
            (saddleBase - minimumBase) / thermalEnergy) *
        arrheniusRate prefactor (saddleBase - minimumBase) thermalEnergy :=
          arrhenius_transport (ne_of_gt hthermal)
    _ = Real.exp
          (-quadraticBarrierShift
            minimumCurvature minimumForce minimumVertical
            saddleCurvature saddleForce saddleVertical ε /
            thermalEnergy) *
        arrheniusRate prefactor (saddleBase - minimumBase) thermalEnergy := by
          rw [quadraticBarrier_exact hminimum hsaddle]
          simp only [signedBarrierError, quadraticBarrierShift]
          ring_nf

/-- The exact bridge with the one-dimensional minimum/saddle classification explicit. -/
theorem quadraticBarrier_arrhenius_exact_of_min_saddle
    {minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical
      ε prefactor thermalEnergy : ℝ}
    (hminimum : 0 < minimumCurvature)
    (hsaddle : saddleCurvature < 0)
    (hthermal : 0 < thermalEnergy) :
    arrheniusRate prefactor
        (quadraticBarrier
          minimumBase minimumCurvature minimumForce minimumVertical
          saddleBase saddleCurvature saddleForce saddleVertical ε)
        thermalEnergy =
      Real.exp
          (-quadraticBarrierShift
            minimumCurvature minimumForce minimumVertical
            saddleCurvature saddleForce saddleVertical ε /
            thermalEnergy) *
        arrheniusRate prefactor (saddleBase - minimumBase) thermalEnergy :=
  quadraticBarrier_arrhenius_exact
    (ne_of_gt hminimum) (ne_of_lt hsaddle) hthermal

end OpenDistillationFactory.HonestErrors.Response
