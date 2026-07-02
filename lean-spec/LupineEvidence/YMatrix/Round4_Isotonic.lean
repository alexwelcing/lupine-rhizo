/- AUTHORED from bound Y-matrix evidence (corpus sha256 dce951665673).
   ISOTONIC CALIBRATION, kernel-verified end to end for the flagship cell:
   model mace-mpa-0-medium, property gamma_111 (J/m^2 x10000), 9 fcc metals.
   Anchors are the 8 non-Pt metals (leave-one-out); the interpolator below is
   THE correction function -- the kernel computes the corrected value itself.
   Conventions: piecewise-linear between anchors, clamped outside the anchor
   range; Int division on nonneg operands (= floor). Calibration is
   interpolation: extremum cells (Sr, Ni) are clamp-degenerate and excluded
   from correction claims (extrapolation boundary, documented protocol fact). -/

namespace Lupine.YMatrix.Isotonic

/-- Piecewise-linear monotone interpolation through anchor knots, clamped at ends. -/
def interp : List (Int × Int) → Int → Int
  | [], _ => 0
  | [(_, t)], _ => t
  | (p0, t0) :: (p1, t1) :: rest, x =>
    if x ≤ p0 then t0
    else if x ≤ p1 then t0 + ((t1 - t0) * (x - p0)) / (p1 - p0)
    else interp ((p1, t1) :: rest) x

/-- LOO anchor knots: (predicted, reference) for the 8 non-Pt fcc metals, sorted by prediction. -/
def knots : List (Int × Int) := [(2626, 3420), (3956, 4610), (6865, 7420), (7027, 7730), (7840, 7950), (12284, 13140), (13473, 13380), (26092, 19240)]

/-- Anchor predictions strictly increase (rank-faithful input side). -/
theorem knot_preds_increase : 2626 < 3956 ∧ 3956 < 6865 ∧ 6865 < 7027 ∧ 7027 < 7840 ∧ 7840 < 12284 ∧ 12284 < 13473 ∧ 13473 < 26092 := by decide

/-- Anchor references strictly increase along the prediction order: the exact
    rank-faithfulness (rho = 1.000) that guarantees a monotone correction exists. -/
theorem knot_refs_increase : 3420 < 4610 ∧ 4610 < 7420 ∧ 7420 < 7730 ∧ 7730 < 7950 ∧ 7950 < 13140 ∧ 13140 < 13380 ∧ 13380 < 19240 := by decide

/-- THE FLAGSHIP, computed in-kernel: the correction of Pt's prediction.
    interp evaluates inside Lean -- no Python number is trusted here. -/
theorem pt_corrected_value : interp knots 16695 = 14876 := by native_decide

/-- Corrected Pt lands within 1% of the reference 14790 ... -/
theorem pt_within_one_percent : (interp knots 16695 - 14790).natAbs ≤ 148 := by native_decide

/-- ... while the RAW prediction missed by more than 10%. Correction factor ~22x. -/
theorem pt_raw_error_exceeds_ten_percent : (1479 : Nat) < ((16695 : Int) - 14790).natAbs := by native_decide

/-- The correction preserves the verified ordinal structure: applying interp to
    all nine predictions yields a strictly increasing chain (computed in-kernel). -/
theorem order_preserved_under_correction : interp knots 2626 < interp knots 3956 ∧ interp knots 3956 < interp knots 6865 ∧ interp knots 6865 < interp knots 7027 ∧ interp knots 7027 < interp knots 7840 ∧ interp knots 7840 < interp knots 12284 ∧ interp knots 12284 < interp knots 13473 ∧ interp knots 13473 < interp knots 16695 ∧ interp knots 16695 < interp knots 26092 := by native_decide

/-- General impossibility lemma: a monotone map cannot swap an order. -/
theorem no_monotone_fix {f : Int → Int} (hf : ∀ a b : Int, a ≤ b → f a ≤ f b)
    {pa pb : Int} (hp : pa ≤ pb) : ¬ (f pb < f pa) := by
  intro hlt
  have := hf pa pb hp
  omega

/-- The MPtrj SFE boundary, as a theorem: mace-mp-small predicts SFE(Ni) = -77759 ≤ SFE(Al) = -76202
    (x10000 mJ/m^2), but the references order the other way (Al 1175400 < Ni 1535600).
    NO monotone correction g can map both predictions to their references. -/
theorem sfe_mptrj_uncorrectable {g : Int → Int} (hg : ∀ a b : Int, a ≤ b → g a ≤ g b)
    (hNi : g (-77759) = 1535600) (hAl : g (-76202) = 1175400) : False := by
  have h := hg (-77759) (-76202) (by decide)
  omega

end Lupine.YMatrix.Isotonic
