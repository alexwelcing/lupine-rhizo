/- AUTHORED from registered confirmatory analysis (Y-matrix Round 1).
   Input: confirmatory_primary_16x5.json sha256 48d088c07f37; seed 20260701; 1000 null draws.
   EVERY verdict encoded — passes AND kills. A kill is correction knowledge:
   it machine-checks where transfer must NOT be routed. (x1000-scaled Nat facts) -/

namespace Lupine.YMatrix.Round1

/-- H1 KILL mace-mp-small: PR 2.763 ≥ null p05 2.344 — no compression beyond within-family coupling. Routing fact: no shared cross-family mode to exploit for this model. -/
theorem h1_kill_mace_mp_small : 2344 ≤ 2763 := by decide

/-- H1 KILL mace-mp-medium: PR 2.356 ≥ null p05 2.113 — no compression beyond within-family coupling. Routing fact: no shared cross-family mode to exploit for this model. -/
theorem h1_kill_mace_mp_medium : 2113 ≤ 2356 := by decide

/-- H1 PASS chgnet: PR 1.999 < null p05 2.168 — cross-property compression below the coupling-aware null. -/
theorem h1_pass_chgnet : 1999 < 2168 := by decide

/-- H2 KILL mace-mp-small|mace-mp-medium: cosine 0.086 ≤ null p95 0.845 — apparent mode alignment is inside the family-permutation null. Routing fact: do NOT transfer corrections between these models via a shared mode. -/
theorem h2_kill_mace_mp_small__mace_mp_medium : 86 ≤ 845 := by decide

/-- H2 KILL mace-mp-small|chgnet: cosine 0.700 ≤ null p95 0.903 — apparent mode alignment is inside the family-permutation null. Routing fact: do NOT transfer corrections between these models via a shared mode. -/
theorem h2_kill_mace_mp_small__chgnet : 700 ≤ 903 := by decide

/-- H2 KILL mace-mp-medium|chgnet: cosine 0.763 ≤ null p95 0.773 — apparent mode alignment is inside the family-permutation null. Routing fact: do NOT transfer corrections between these models via a shared mode. -/
theorem h2_kill_mace_mp_medium__chgnet : 763 ≤ 773 := by decide

/-- H3 PASS mace-mp-small: defect/bulk median-error ratio 18.9 ≥ registered threshold 2.0 (defect 0.1076 vs bulk 0.0057). Routing fact: defect families are the high-ROI correction target for this model. -/
theorem h3_pass_mace_mp_small : 2000 ≤ 18929 := by decide

/-- H3 PASS mace-mp-medium: defect/bulk median-error ratio 15.3 ≥ registered threshold 2.0 (defect 0.1213 vs bulk 0.0079). Routing fact: defect families are the high-ROI correction target for this model. -/
theorem h3_pass_mace_mp_medium : 2000 ≤ 15325 := by decide

/-- H3 PASS chgnet: defect/bulk median-error ratio 57.0 ≥ registered threshold 2.0 (defect 0.2846 vs bulk 0.0050). Routing fact: defect families are the high-ROI correction target for this model. -/
theorem h3_pass_chgnet : 2000 ≤ 56966 := by decide

end Lupine.YMatrix.Round1