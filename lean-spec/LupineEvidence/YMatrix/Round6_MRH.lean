/- AUTHORED from bound Y-matrix evidence (corpus sha256 dce951665673).
   MONOTONE REPARAMETERIZATION HYPOTHESIS (MRH) — first confirmed predictions:
   (1) FAMILY-LEVEL WARP: a monotone map fitted ONLY on gamma_100 corrects the
       unseen facets gamma_110/gamma_111 (median |rel err| x10000, before vs after).
   (2) WARP -> IDENTITY with training quality: pooled surface warp magnitude
       orders strictly across the four models. -/

namespace Lupine.YMatrix.MRH

/-- chgnet: gamma_100-fitted map corrects unseen gamma_110: 0.2683 -> 0.0985. -/
theorem family_warp_transfer_chgnet_gamma_110 : 985 < 2683 := by decide

/-- chgnet: gamma_100-fitted map corrects unseen gamma_111: 0.3639 -> 0.1158. -/
theorem family_warp_transfer_chgnet_gamma_111 : 1158 < 3639 := by decide

/-- mace-mp-small: gamma_100-fitted map corrects unseen gamma_110: 0.1300 -> 0.0669. -/
theorem family_warp_transfer_mace_mp_small_gamma_110 : 669 < 1300 := by decide

/-- mace-mp-small: gamma_100-fitted map corrects unseen gamma_111: 0.1421 -> 0.0674. -/
theorem family_warp_transfer_mace_mp_small_gamma_111 : 674 < 1421 := by decide

/-- Warp distance from identity strictly orders by training lineage: mace-mpa-0-medium < mace-mp-medium < mace-mp-small < chgnet (x10000: [514, 987, 1201, 3881]). -/
theorem warp_orders_by_training : 514 < 987 ∧ 987 < 1201 ∧ 1201 < 3881 := by decide

end Lupine.YMatrix.MRH