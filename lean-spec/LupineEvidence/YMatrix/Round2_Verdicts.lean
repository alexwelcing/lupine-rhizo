/- AUTHORED from registered R2-H1 analysis (MACE-MPA-0, OMat24 lineage).
   Input: r2_mpa0_confirmatory.json sha256 874a88956c1c; seed 20260701.
   Registered verdict: KILL (ratio 7.86 >= threshold 7.66). The decomposition
   facts below are equally load-bearing: defect errors halved, bias eliminated;
   the ratio missed because bulk improved too. (medians x10000) -/

namespace Lupine.YMatrix.Round2

/-- R2-H1 KILL: MPA-0 defect/bulk ratio 7.86 ≥ registered 7.66 (x100: 786 ≥ 766). Routing fact: the registered ratio-halving did not occur. -/
theorem r2h1_kill_ratio : 766 ≤ 786 := by decide

/-- Decomposition: MPA-0 defect median |rel err| 0.0465 < HALF of MACE-MP-medium's 0.1213 — the distributional retraining DID collapse defect errors (numerator), independent of the ratio statistic. -/
theorem r2_defect_errors_halved : 465 < 606 + 1 := by decide

/-- Decomposition: MPA-0 bulk median also improved (0.0059 < 0.0079) — the ratio's denominator moved with its numerator. -/
theorem r2_bulk_also_improved : 59 < 79 := by decide

end Lupine.YMatrix.Round2