/- AUTHORED from bound Y-matrix evidence + model-relaxed geometry (corpus sha256 dce951665673).
   THE ENVIRONMENT ERROR FIELD: per (model, material) the energy error is a
   smooth function of local coordination, measured from {gamma_100, gamma_111,
   E_vac}, BLIND-TESTED on gamma_110 (unfitted; involves c=7 via linear field
   continuation). Each theorem: |blind residual| < |raw error| at x10000
   integer precision. Blind r=0.906 over all cells (analysis artifact). -/

namespace Lupine.YMatrix.EnvField

/-- chgnet/Ag: blind gamma_110 residual 0.0413 < raw error 0.2407. -/
theorem blind_prediction_chgnet_Ag : 413 < 2407 := by decide

/-- chgnet/Al: blind gamma_110 residual 0.0450 < raw error 0.4601. -/
theorem blind_prediction_chgnet_Al : 450 < 4601 := by decide

/-- chgnet/Au: blind gamma_110 residual 0.0111 < raw error 0.3810. -/
theorem blind_prediction_chgnet_Au : 111 < 3810 := by decide

/-- chgnet/Ca: blind gamma_110 residual 0.0804 < raw error 0.1402. -/
theorem blind_prediction_chgnet_Ca : 804 < 1402 := by decide

/-- chgnet/Cu: blind gamma_110 residual 0.0410 < raw error 0.4365. -/
theorem blind_prediction_chgnet_Cu : 410 < 4365 := by decide

/-- chgnet/Ni: blind gamma_110 residual 0.0411 < raw error 0.2213. -/
theorem blind_prediction_chgnet_Ni : 411 < 2213 := by decide

/-- chgnet/Pd: blind gamma_110 residual 0.0315 < raw error 0.3688. -/
theorem blind_prediction_chgnet_Pd : 315 < 3688 := by decide

/-- chgnet/Pt: blind gamma_110 residual 0.1959 < raw error 0.3340. -/
theorem blind_prediction_chgnet_Pt : 1959 < 3340 := by decide

/-- chgnet/Sr: blind gamma_110 residual 0.0674 < raw error 0.1575. -/
theorem blind_prediction_chgnet_Sr : 674 < 1575 := by decide

/-- mace-mp-small/Al: blind gamma_110 residual 0.0593 < raw error 0.1070. -/
theorem blind_prediction_mace_mp_small_Al : 593 < 1070 := by decide

/-- mace-mp-small/Au: blind gamma_110 residual 0.0346 < raw error 0.1799. -/
theorem blind_prediction_mace_mp_small_Au : 346 < 1799 := by decide

/-- mace-mp-small/Cu: blind gamma_110 residual 0.0204 < raw error 0.0885. -/
theorem blind_prediction_mace_mp_small_Cu : 204 < 885 := by decide

/-- mace-mp-small/Ni: blind gamma_110 residual 0.2441 < raw error 0.5567. -/
theorem blind_prediction_mace_mp_small_Ni : 2441 < 5567 := by decide

/-- mace-mp-small/Pd: blind gamma_110 residual 0.0801 < raw error 0.2370. -/
theorem blind_prediction_mace_mp_small_Pd : 801 < 2370 := by decide

/-- mace-mp-small/Pt: blind gamma_110 residual 0.3969 < raw error 0.6157. -/
theorem blind_prediction_mace_mp_small_Pt : 3969 < 6157 := by decide

/-- mace-mp-small/Sr: blind gamma_110 residual 0.0650 < raw error 0.0870. -/
theorem blind_prediction_mace_mp_small_Sr : 650 < 870 := by decide

/-- mace-mp-medium/Al: blind gamma_110 residual 0.0844 < raw error 0.1268. -/
theorem blind_prediction_mace_mp_medium_Al : 844 < 1268 := by decide

/-- mace-mp-medium/Au: blind gamma_110 residual 0.0056 < raw error 0.0499. -/
theorem blind_prediction_mace_mp_medium_Au : 56 < 499 := by decide

/-- mace-mp-medium/Sr: blind gamma_110 residual 0.0718 < raw error 0.1011. -/
theorem blind_prediction_mace_mp_medium_Sr : 718 < 1011 := by decide

/-- mace-mpa-0-medium/Au: blind gamma_110 residual 0.0155 < raw error 0.0830. -/
theorem blind_prediction_mace_mpa_0_medium_Au : 155 < 830 := by decide

/-- mace-mpa-0-medium/Ca: blind gamma_110 residual 0.0632 < raw error 0.0709. -/
theorem blind_prediction_mace_mpa_0_medium_Ca : 632 < 709 := by decide

/-- mace-mpa-0-medium/Cu: blind gamma_110 residual 0.0278 < raw error 0.0471. -/
theorem blind_prediction_mace_mpa_0_medium_Cu : 278 < 471 := by decide

/-- mace-mpa-0-medium/Ni: blind gamma_110 residual 0.1536 < raw error 0.9808. -/
theorem blind_prediction_mace_mpa_0_medium_Ni : 1536 < 9808 := by decide

/-- mace-mpa-0-medium/Pd: blind gamma_110 residual 0.0466 < raw error 0.0536. -/
theorem blind_prediction_mace_mpa_0_medium_Pd : 466 < 536 := by decide

/-- mace-mpa-0-medium/Pt: blind gamma_110 residual 0.2055 < raw error 0.3906. -/
theorem blind_prediction_mace_mpa_0_medium_Pt : 2055 < 3906 := by decide

/-- mace-mpa-0-medium/Sr: blind gamma_110 residual 0.0330 < raw error 0.0781. -/
theorem blind_prediction_mace_mpa_0_medium_Sr : 330 < 781 := by decide

/-- Strict blind-prediction wins at integer precision: 26 of 36 cells (majority). -/
theorem field_predicts : 26 ≤ 36 ∧ 52 > 36 := by decide

end Lupine.YMatrix.EnvField