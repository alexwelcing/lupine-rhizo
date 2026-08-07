import LupineEvidence.Shapes.Certificates
import Mathlib.Tactic

/-!
# Sharp calibration-only licenses for in-hull correction

`LupineEvidence.Shapes.Certificates` retains the frozen Round-4 sufficient
caps proved by `capped_inhull_correction_helps_inflation` and
`capped_inhull_correction_helps_deflation`.  This module proves the sharp
conditions that supersede those caps for future campaigns:

* exact/discretized inflation: `b * (2 * 10000 - lo) < lo * 10000`;
* exact/discretized deflation: `hi * (10000 + b) < 2 * 10000 * b`;
* round-to-nearest inputs: the robust `Certificates.lean` predicates, whose
  margin accounts for both half-grid input errors.

Both conditions use calibration data alone.  Neither uses the hull spread;
the deflation condition has no `b ≥ 0.5` floor.  Necessity is witnessed at the
relevant hull endpoint, so a uniform-over-hull license cannot be widened
without weakening strict improvement.  The compatibility theorems prove that
the frozen caps imply the sharp conditions, preserving every previously
licensed case.  This does not retroactively alter any frozen campaign.

Ratios are integer-scaled by 10000, matching `Certificates.lean`.  Future
campaigns that evaluate a gate on rounded ratios must use the robust predicates;
the un-margined sharp gates license only values treated as exact.
-/

namespace OpenDistillationFactory.Materials.Theory.SharpLicense

/-- Sharp inflation license: for a hull strictly above one, the calibration-
only boundary implies strict correction improvement for every target ratio in
the hull. -/
theorem sharp_inhull_correction_helps_inflation
    (lo hi b r : Int)
    (hlo : 10000 < lo) (_hle : lo ≤ hi)
    (hb1 : lo ≤ b) (_hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (_hr2 : r ≤ hi)
    (hsharp : b * (2 * 10000 - lo) < lo * 10000) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b := by
  have hbU : 10000 < b := lt_of_lt_of_le hlo hb1
  have hrU : 10000 < r := lt_of_lt_of_le hlo hr1
  have hcast : ((r - 10000).natAbs : Int) = r - 10000 := by omega
  rw [hcast]
  rcases le_or_gt b r with hbr | hrb
  · have hcast2 : ((r - b).natAbs : Int) = r - b := by omega
    rw [hcast2]
    nlinarith
  · have hcast2 : ((r - b).natAbs : Int) = b - r := by omega
    rw [hcast2]
    have hkey : 2 * b * 10000 < lo * (b + 10000) := by nlinarith
    nlinarith

/-- Sharp deflation license: for a positive hull strictly below one, the
calibration-only boundary implies strict correction improvement for every
target ratio in the hull, with no bias floor. -/
theorem sharp_inhull_correction_helps_deflation
    (lo hi b r : Int)
    (hlo : 0 < lo) (_hle : lo ≤ hi) (hhi : hi < 10000)
    (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hr1 : lo ≤ r) (hr2 : r ≤ hi)
    (hsharp : hi * (10000 + b) < 2 * 10000 * b) :
    ((r - b).natAbs : Int) * 10000 < ((r - 10000).natAbs : Int) * b := by
  have hbpos : 0 < b := lt_of_lt_of_le hlo hb1
  have hrpos : 0 < r := lt_of_lt_of_le hlo hr1
  have hbU : b < 10000 := lt_of_le_of_lt hb2 hhi
  have hrU : r < 10000 := lt_of_le_of_lt hr2 hhi
  have hcast : ((r - 10000).natAbs : Int) = 10000 - r := by omega
  rw [hcast]
  rcases le_or_gt r b with hrb | hbr
  · have hcast2 : ((r - b).natAbs : Int) = b - r := by omega
    rw [hcast2]
    nlinarith
  · have hcast2 : ((r - b).natAbs : Int) = r - b := by omega
    rw [hcast2]
    have hkey : r * (10000 + b) ≤ hi * (10000 + b) := by nlinarith
    nlinarith

/-! ## Sound gates for round-to-nearest inputs

The sharp integer gates above are exact only at the discretized values.  When
`lo`/`hi` and `b` were rounded from measured real ratios, a strict gate with no
margin can cross the true boundary.  The operational predicates in
`Certificates.lean` clear the two half-grid errors exactly; these theorems bind
those decidable predicates back to the true real-valued guarantee. -/

/-- Round-to-nearest-safe inflation license.  `L` and `B` are the true hull
minimum and bias, while `lo` and `b` are their nearest x10000 integers.  The
robust gate licenses every target at or above the true `L`. -/
theorem rounding_robust_inhull_correction_helps_inflation
    (lo b : Int) (L B : ℝ)
    (hlo : 10000 < lo) (hlo2 : lo ≤ 20000) (hb : lo ≤ b)
    (hL : |10000 * L - (lo : ℝ)| ≤ 1 / 2)
    (hB : |10000 * B - (b : ℝ)| ≤ 1 / 2)
    (hgate : Lupine.Shapes.roundingRobustInflationGate lo b) :
    ∀ R : ℝ, L ≤ R → |R / B - 1| < |R - 1| := by
  unfold Lupine.Shapes.roundingRobustInflationGate at hgate
  have hloR : (10000 : ℝ) < (lo : ℝ) := by exact_mod_cast hlo
  have hlo2R : (lo : ℝ) ≤ 20000 := by exact_mod_cast hlo2
  have hbR : (lo : ℝ) ≤ (b : ℝ) := by exact_mod_cast hb
  have hmargin :
      (1 / 2 : ℝ) * (3 * 10000 + 1 / 2 + (b : ℝ) - (lo : ℝ))
        < (lo : ℝ) * (10000 + (b : ℝ)) - 2 * 10000 * (b : ℝ) := by
    have hgateR :
        ((60001 + 2 * b - 2 * lo : Int) : ℝ)
          < ((4 * (lo * (10000 + b) - 2 * 10000 * b) : Int) : ℝ) := by
      exact_mod_cast hgate
    push_cast at hgateR
    nlinarith
  rw [abs_le] at hL hB
  obtain ⟨hL1, hL2⟩ := hL
  obtain ⟨hB1, hB2⟩ := hB
  have hBgt1 : 1 < B := by nlinarith
  have hBpos : 0 < B := by linarith
  have hA : 0 ≤ (10000 : ℝ) + 10000 * B := by linarith
  have p1 : 0 ≤ ((10000 : ℝ) + 10000 * B) * ((10000 * L - lo) + 1 / 2) :=
    mul_nonneg hA (by linarith)
  have p2 : 0 ≤ ((10000 + (b : ℝ) + 1 / 2) - (10000 + 10000 * B)) * (1 / 2) :=
    mul_nonneg (by linarith) (by norm_num)
  have p3 : 0 ≤ (2 * 10000 - (lo : ℝ)) * (1 / 2 - (10000 * B - b)) :=
    mul_nonneg (by linarith) (by linarith)
  have htrue : 0 < (10000 * L) * (10000 + 10000 * B) - 2 * 10000 * (10000 * B) := by
    nlinarith [p1, p2, p3]
  have hL0 : 0 < L := by nlinarith
  intro R hR
  have hR0 : 0 < R := lt_of_lt_of_le hL0 hR
  have hmono : 0 ≤ 10000 * (R - L) * (10000 + 10000 * B) :=
    mul_nonneg (mul_nonneg (by norm_num) (by linarith)) hA
  have hkey : 0 < R * (1 + B) - 2 * B := by nlinarith [htrue, hmono]
  have hdisc : 0 < (B - 1) * (R * (1 + B) - 2 * B) :=
    mul_pos (by linarith) hkey
  have hB2 : 0 < B ^ 2 := by positivity
  have hrewrite : R / B - 1 = (R - B) / B := by field_simp
  rw [← sq_lt_sq, hrewrite, div_pow, div_lt_iff₀ hB2]
  nlinarith [mul_pos hR0 hdisc]

/-- Round-to-nearest-safe deflation license.  The robust gate licenses every
positive target at or below the true hull maximum `H`. -/
theorem rounding_robust_inhull_correction_helps_deflation
    (hi b : Int) (H B : ℝ)
    (hb0 : 1 ≤ b) (hb : b ≤ hi) (hhi : hi ≤ 9999)
    (hH : |10000 * H - (hi : ℝ)| ≤ 1 / 2)
    (hB : |10000 * B - (b : ℝ)| ≤ 1 / 2)
    (hgate : Lupine.Shapes.roundingRobustDeflationGate hi b) :
    ∀ R : ℝ, 0 < R → R ≤ H → |R / B - 1| < |R - 1| := by
  unfold Lupine.Shapes.roundingRobustDeflationGate at hgate
  have hb0R : (1 : ℝ) ≤ (b : ℝ) := by exact_mod_cast hb0
  have hbR : (b : ℝ) ≤ (hi : ℝ) := by exact_mod_cast hb
  have hhiR : (hi : ℝ) ≤ 9999 := by exact_mod_cast hhi
  have hmargin :
      (1 / 2 : ℝ) * (3 * 10000 - (hi : ℝ) + (b : ℝ) + 1 / 2)
        < 2 * 10000 * (b : ℝ) - (hi : ℝ) * (10000 + (b : ℝ)) := by
    have hgateR :
        ((60001 + 2 * b - 2 * hi : Int) : ℝ)
          < ((4 * (2 * 10000 * b - hi * (10000 + b)) : Int) : ℝ) := by
      exact_mod_cast hgate
    push_cast at hgateR
    nlinarith
  rw [abs_le] at hH hB
  obtain ⟨hH1, hH2⟩ := hH
  obtain ⟨hB1, hB2⟩ := hB
  have hBpos : 0 < B := by nlinarith
  have hBlt1 : B < 1 := by nlinarith
  have hA : 0 ≤ (10000 : ℝ) + 10000 * B := by nlinarith
  have p1 : 0 ≤ (2 * 10000 - (hi : ℝ)) * (1 / 2 + (10000 * B - b)) :=
    mul_nonneg (by linarith) (by linarith)
  have p2 : 0 ≤ ((10000 : ℝ) + 10000 * B) * (1 / 2 - (10000 * H - hi)) :=
    mul_nonneg hA (by linarith)
  have p3 : 0 ≤ ((10000 + (b : ℝ) + 1 / 2) - (10000 + 10000 * B)) * (1 / 2) :=
    mul_nonneg (by linarith) (by norm_num)
  have htrue : 0 < 2 * 10000 * (10000 * B) - (10000 * H) * (10000 + 10000 * B) := by
    nlinarith [p1, p2, p3]
  intro R hR0 hR
  have hmono : 0 ≤ 10000 * (H - R) * (10000 + 10000 * B) :=
    mul_nonneg (mul_nonneg (by norm_num) (by linarith)) hA
  have hkey : R * (1 + B) - 2 * B < 0 := by nlinarith [htrue, hmono]
  have hdisc : 0 < (B - 1) * (R * (1 + B) - 2 * B) :=
    mul_pos_of_neg_of_neg (by linarith) hkey
  have hBsq : 0 < B ^ 2 := by positivity
  have hrewrite : R / B - 1 = (R - B) / B := by field_simp
  rw [← sq_lt_sq, hrewrite, div_pow, div_lt_iff₀ hBsq]
  nlinarith [mul_pos hR0 hdisc]

/-! ## Rounded-input defect regression witnesses

These examples lock the soundness bug that the robust predicates close.  In
each case the un-margined integer gate passes on nearest-rounded inputs while
the correction strictly increases the error at the true hull endpoint. -/

/-- Inflation witness with a five-thousand-unit apparent gate margin. -/
theorem rounding_defect_inflation :
    (10100 : Int) * (2 * 10000 - 10050) < 10050 * 10000
    ∧ |10000 * (1004951 / 1000000 : ℝ) - 10050| ≤ 1 / 2
    ∧ |10000 * (101004 / 100000 : ℝ) - 10100| ≤ 1 / 2
    ∧ |(1004951 / 1000000 : ℝ) - 1|
        < |(1004951 / 1000000 : ℝ) / (101004 / 100000 : ℝ) - 1| := by
  norm_num [abs_of_pos, abs_of_neg]

/-- Severe inflation witness: the corrected error exceeds 3.9 times the raw
error even though the rounded gate passes. -/
theorem rounding_defect_inflation_severe :
    (10002 : Int) * (2 * 10000 - 10001) < 10001 * 10000
    ∧ |10000 * (10000501 / 10000000 : ℝ) - 10001| ≤ 1 / 2
    ∧ |10000 * (10002499 / 10000000 : ℝ) - 10002| ≤ 1 / 2
    ∧ (39 / 10 : ℝ) * |(10000501 / 10000000 : ℝ) - 1|
        < |(10000501 / 10000000 : ℝ) / (10002499 / 10000000 : ℝ) - 1| := by
  norm_num [abs_of_pos, abs_of_neg]

/-- Deflation witness whose rounded gate passes by only four integer units. -/
theorem rounding_defect_deflation :
    (5756 : Int) * (10000 + 4041) < 2 * 10000 * 4041
    ∧ |10000 * (57564 / 100000 : ℝ) - 5756| ≤ 1 / 2
    ∧ |10000 * (40406 / 100000 : ℝ) - 4041| ≤ 1 / 2
    ∧ |(57564 / 100000 : ℝ) - 1|
        < |(57564 / 100000 : ℝ) / (40406 / 100000 : ℝ) - 1| := by
  norm_num [abs_of_pos, abs_of_neg]

/-- The frozen Round-4 inflation cap implies the sharp inflation license, so
moving to the sharp gate preserves all formerly licensed inflation cases. -/
theorem old_inflation_cap_implies_sharp
    (lo hi s b : Int) (hs : s = hi - lo)
    (hlo : 10000 < lo) (_hle : lo ≤ hi) (hb1 : lo ≤ b) (hb2 : b ≤ hi)
    (hcap : 2 * s < b - 10000) :
    b * (2 * 10000 - lo) < lo * 10000 := by
  nlinarith [sq_nonneg (lo - 10000)]

/-- The frozen Round-4 deflation cap and its bias floor imply the sharp
condition, so moving to the sharp gate preserves all formerly licensed
deflation cases. -/
theorem old_deflation_cap_implies_sharp
    (lo hi s b : Int) (hs : s = hi - lo)
    (hlo : 0 < lo) (hle : lo ≤ hi) (hhi : hi < 10000)
    (hb1 : lo ≤ b) (_hb2 : b ≤ hi)
    (hfloor : 5000 ≤ b) (hcap : 3 * s < 10000 - b) :
    hi * (10000 + b) < 2 * 10000 * b := by
  nlinarith

/-- Inflation sharpness: when the boundary condition fails and the bias lies
strictly above the lower endpoint, correction does not strictly improve at
`r = lo`. -/
theorem sharp_inflation_necessary
    (lo b : Int) (hlo : 10000 < lo) (hb1 : lo < b)
    (hfail : lo * 10000 ≤ b * (2 * 10000 - lo)) :
    ¬ (((lo - b).natAbs : Int) * 10000 < ((lo - 10000).natAbs : Int) * b) := by
  have h1 : ((lo - b).natAbs : Int) = b - lo := by omega
  have h2 : ((lo - 10000).natAbs : Int) = lo - 10000 := by omega
  rw [h1, h2]
  push Not
  nlinarith

/-- Deflation sharpness: when the boundary condition fails and the bias lies
strictly below the upper endpoint, correction does not strictly improve at
`r = hi`. -/
theorem sharp_deflation_necessary
    (hi b : Int) (hhi : hi < 10000) (_hbpos : 0 < b) (hb2 : b < hi)
    (hfail : 2 * 10000 * b ≤ hi * (10000 + b)) :
    ¬ (((hi - b).natAbs : Int) * 10000 < ((hi - 10000).natAbs : Int) * b) := by
  have h1 : ((hi - b).natAbs : Int) = hi - b := by omega
  have h2 : ((hi - 10000).natAbs : Int) = 10000 - hi := by omega
  rw [h1, h2]
  push Not
  nlinarith

/-! ## Kernel-checked non-vacuity tests -/

/-- The sharp inflation gate admits a cell refused by the old `2s` cap. -/
example : ¬ (2 * (10110 - 10050) < (10100 : Int) - 10000) := by decide

example : (10100 : Int) * (2 * 10000 - 10050) < 10050 * 10000 := by decide

example : ((10110 - 10100 : Int).natAbs : Int) * 10000
    < ((10110 - 10000 : Int).natAbs : Int) * 10100 :=
  sharp_inhull_correction_helps_inflation 10050 10110 10100 10110
    (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)

/-- The sharp deflation gate admits a cell below the old `b ≥ 0.5` floor. -/
example : ¬ ((5000 : Int) ≤ 3000) := by decide

example : (3400 : Int) * (10000 + 3000) < 2 * 10000 * 3000 := by decide

example : ((3400 - 3000 : Int).natAbs : Int) * 10000
    < ((3400 - 10000 : Int).natAbs : Int) * 3000 :=
  sharp_inhull_correction_helps_deflation 3000 3400 3000 3400
    (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide) (by decide)

/-! ## Round-to-nearest robustness regression tests -/

example :
    |(201 / 200 : ℝ) / (503 / 500 : ℝ) - 1| < |(201 / 200 : ℝ) - 1| :=
  rounding_robust_inhull_correction_helps_inflation
    10050 10060 (201 / 200) (503 / 500)
    (by decide) (by decide) (by decide) (by norm_num) (by norm_num) (by decide)
    (201 / 200) (by norm_num)

example :
    |(17 / 50 : ℝ) / (3 / 10 : ℝ) - 1| < |(17 / 50 : ℝ) - 1| :=
  rounding_robust_inhull_correction_helps_deflation
    3400 3000 (17 / 50) (3 / 10)
    (by decide) (by decide) (by decide) (by norm_num) (by norm_num) (by decide)
    (17 / 50) (by norm_num) (by norm_num)

end OpenDistillationFactory.Materials.Theory.SharpLicense
