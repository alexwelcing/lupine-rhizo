/- AUTHORED from bound Y-matrix evidence (corpus sha256 dce951665673).
   THE FAMILY-EXPONENT LAW: pred ~ c * T^alpha, exponent alpha owned by the
   property FAMILY (shared across models), prefactor c owned by the MODEL.
   Point-estimate separation facts (alpha x1000): every model's surface
   exponent exceeds every model's vacancy and B0 exponent. Statistical
   uncertainty lives in the analysis artifact; these are the point facts. -/

namespace Lupine.YMatrix.FamilyExponent

-- surfaces: alpha x1000 across all four models spans [1065, 1138]
-- vacancy: alpha x1000 across all four models spans [808, 917]
-- B0: alpha x1000 across all four models spans [901, 1019]
/-- Family separation: EVERY surface exponent > EVERY vacancy and B0 exponent (all four models; alpha x1000). -/
theorem surface_exponent_dominates : 808 < 1138 ∧ 917 < 1138 ∧ 857 < 1138 ∧ 894 < 1138 ∧ 1002 < 1138 ∧ 907 < 1138 ∧ 901 < 1138 ∧ 1019 < 1138 ∧ 808 < 1129 ∧ 917 < 1129 ∧ 857 < 1129 ∧ 894 < 1129 ∧ 1002 < 1129 ∧ 907 < 1129 ∧ 901 < 1129 ∧ 1019 < 1129 ∧ 808 < 1065 ∧ 917 < 1065 ∧ 857 < 1065 ∧ 894 < 1065 ∧ 1002 < 1065 ∧ 907 < 1065 ∧ 901 < 1065 ∧ 1019 < 1065 ∧ 808 < 1098 ∧ 917 < 1098 ∧ 857 < 1098 ∧ 894 < 1098 ∧ 1002 < 1098 ∧ 907 < 1098 ∧ 901 < 1098 ∧ 1019 < 1098 := by decide

end Lupine.YMatrix.FamilyExponent