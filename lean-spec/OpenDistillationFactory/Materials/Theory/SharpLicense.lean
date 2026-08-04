import LupineEvidence.Shapes.Certificates
import Mathlib.Tactic

/-!
# Sharp calibration-only licenses for in-hull correction

`LupineEvidence.Shapes.Certificates` retains the frozen Round-4 sufficient
caps proved by `capped_inhull_correction_helps_inflation` and
`capped_inhull_correction_helps_deflation`.  This module proves the sharp
conditions that supersede those caps for future campaigns:

* inflation: `b * (2 * 10000 - lo) < lo * 10000`;
* deflation: `hi * (10000 + b) < 2 * 10000 * b`.

Both conditions use calibration data alone.  Neither uses the hull spread;
the deflation condition has no `b ≥ 0.5` floor.  Necessity is witnessed at the
relevant hull endpoint, so a uniform-over-hull license cannot be widened
without weakening strict improvement.  The compatibility theorems prove that
the frozen caps imply the sharp conditions, preserving every previously
licensed case.  This does not retroactively alter any frozen campaign.

Ratios are integer-scaled by 10000, matching `Certificates.lean`.
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

end OpenDistillationFactory.Materials.Theory.SharpLicense
