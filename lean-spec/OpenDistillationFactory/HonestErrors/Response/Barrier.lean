import OpenDistillationFactory.HonestErrors.Response.Quadratic

/-!
# Exact two-branch barrier response

Subtracting two continued critical values gives the algebraic core of
Corollary 3.1.  The quadratic model makes the expansion exact, so no remainder
hypothesis is hidden.  A separate theorem below requires positive curvature on
the declared minimum branch and negative curvature on the one-dimensional
declared saddle branch before attaching that physical classification.
-/

namespace OpenDistillationFactory.HonestErrors.Response

/--
The signed critical-value difference between branches supplied under the names
`minimum` and `saddle`; the definition itself makes no Morse-index claim.
-/
noncomputable def quadraticBarrier
    (minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical ε : ℝ) : ℝ :=
  quadraticCriticalValue saddleBase saddleCurvature saddleForce saddleVertical ε -
  quadraticCriticalValue minimumBase minimumCurvature minimumForce minimumVertical ε

/-- Exact first- and second-order response for two nondegenerate declared branches. -/
theorem quadraticBarrier_exact
    {minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical ε : ℝ}
    (hminimum : minimumCurvature ≠ 0)
    (hsaddle : saddleCurvature ≠ 0) :
    quadraticBarrier
        minimumBase minimumCurvature minimumForce minimumVertical
        saddleBase saddleCurvature saddleForce saddleVertical ε =
      (saddleBase - minimumBase) +
      ε * (saddleVertical - minimumVertical) -
      ε ^ 2 / 2 *
        (saddleForce ^ 2 / saddleCurvature -
         minimumForce ^ 2 / minimumCurvature) := by
  rw [quadraticBarrier, quadraticCriticalValue_exact hsaddle,
    quadraticCriticalValue_exact hminimum]
  field_simp [hminimum, hsaddle]
  ring

/--
The same exact response with the one-dimensional minimum/saddle curvature
classification made explicit in the premises.
-/
theorem quadraticBarrier_exact_of_min_saddle
    {minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical ε : ℝ}
    (hminimum : 0 < minimumCurvature)
    (hsaddle : saddleCurvature < 0) :
    quadraticBarrier
        minimumBase minimumCurvature minimumForce minimumVertical
        saddleBase saddleCurvature saddleForce saddleVertical ε =
      (saddleBase - minimumBase) +
      ε * (saddleVertical - minimumVertical) -
      ε ^ 2 / 2 *
        (saddleForce ^ 2 / saddleCurvature -
         minimumForce ^ 2 / minimumCurvature) :=
  quadraticBarrier_exact (ne_of_gt hminimum) (ne_of_lt hsaddle)

/-- The complete first-order barrier correction is the saddle-minus-minimum contrast. -/
theorem quadraticBarrier_vertical_error
    {minimumBase minimumCurvature minimumForce minimumVertical
      saddleBase saddleCurvature saddleForce saddleVertical ε : ℝ}
    (hminimum : minimumCurvature ≠ 0)
    (hsaddle : saddleCurvature ≠ 0) :
    quadraticBarrier
        minimumBase minimumCurvature minimumForce minimumVertical
        saddleBase saddleCurvature saddleForce saddleVertical ε -
      ((saddleBase - minimumBase) +
       ε * (saddleVertical - minimumVertical)) =
      -ε ^ 2 / 2 *
        (saddleForce ^ 2 / saddleCurvature -
         minimumForce ^ 2 / minimumCurvature) := by
  rw [quadraticBarrier_exact hminimum hsaddle]
  ring

end OpenDistillationFactory.HonestErrors.Response
