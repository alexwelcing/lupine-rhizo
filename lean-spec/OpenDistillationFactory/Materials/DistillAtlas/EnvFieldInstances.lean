/- AUTHORED by python/scripts/bind_env_field_instances.py from the
   Y-matrix statics corpus + DFT-PBE targets (corpus sha256 1f244b71846b).
   THE MEASURED FIELDS: per fcc (model, material) cell, the three anchors
   P(8)/P(9)/P(11) (eV/atom, x1e-4 exact integers) are bound from the
   (100)/(111) surface-energy and vacancy-formation errors on
   model-relaxed geometry. TIER 1: every cell yields a `MeasuredField 12`
   (closure/transfer/ranking laws, no shape assumption). TIER 2: cells
   passing monotone softening (p8 <= p9 <= p11 <= 0, checked on the
   emitted literals) also yield an `ErrorField 12` via `mkAnchoredField`
   (directional barrier laws); violating cells get kernel-checked
   refusal certificates instead. 36 measured fields;
   8 softening instances + 28 refusals =
   36 cells. 0 sorry. -/

import OpenDistillationFactory.Materials.Theory.AnchoredField

namespace OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances

open OpenDistillationFactory.Materials.Theory.EnvironmentField
open OpenDistillationFactory.Materials.Theory.AnchoredField

/-! ## Tier 1: measured fields (every bound cell) -/

/-- chgnet/Ag measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1359e-4 from Δγ₁₀₀ = 0.5578 − 0.8100 J/m² on a₀²/2, P(9) = -1355e-4 from Δγ₁₁₁ = 0.4828 − 0.7730 J/m² on √3a₀²/4, P(11) = -156e-4 from ΔE_vac = 0.4931 − 0.6800 eV over 12 shell atoms; a₀ = 4.1560 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ag : MeasuredField 12 :=
  mkMeasuredField (-1359 / 10000 : ℝ) (-1355 / 10000 : ℝ) (-156 / 10000 : ℝ)

/-- chgnet/Al measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2230e-4 from Δγ₁₀₀ = 0.4775 − 0.9150 J/m² on a₀²/2, P(9) = -1862e-4 from Δγ₁₁₁ = 0.3732 − 0.7950 J/m² on √3a₀²/4, P(11) = -394e-4 from ΔE_vac = 0.1372 − 0.6100 eV over 12 shell atoms; a₀ = 4.0414 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Al : MeasuredField 12 :=
  mkMeasuredField (-2230 / 10000 : ℝ) (-1862 / 10000 : ℝ) (-394 / 10000 : ℝ)

/-- chgnet/Au measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2372e-4 from Δγ₁₀₀ = 0.4238 − 0.8610 J/m² on a₀²/2, P(9) = -1819e-4 from Δγ₁₁₁ = 0.3550 − 0.7420 J/m² on √3a₀²/4, P(11) = -83e-4 from ΔE_vac = 0.3000 − 0.4000 eV over 12 shell atoms; a₀ = 4.1698 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Au : MeasuredField 12 :=
  mkMeasuredField (-2372 / 10000 : ℝ) (-1819 / 10000 : ℝ) (-83 / 10000 : ℝ)

/-- chgnet/Ca measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -926e-4 from Δγ₁₀₀ = 0.3608 − 0.4580 J/m² on a₀²/2, P(9) = -1363e-4 from Δγ₁₁₁ = 0.2959 − 0.4610 J/m² on √3a₀²/4, P(11) = -316e-4 from ΔE_vac = 0.7508 − 1.1300 eV over 12 shell atoms; a₀ = 5.5263 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ca : MeasuredField 12 :=
  mkMeasuredField (-926 / 10000 : ℝ) (-1363 / 10000 : ℝ) (-316 / 10000 : ℝ)

/-- chgnet/Cu measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1837e-4 from Δγ₁₀₀ = 1.0179 − 1.4680 J/m² on a₀²/2, P(9) = -1690e-4 from Δγ₁₁₁ = 0.8358 − 1.3140 J/m² on √3a₀²/4, P(11) = -298e-4 from ΔE_vac = 0.7122 − 1.0700 eV over 12 shell atoms; a₀ = 3.6159 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Cu : MeasuredField 12 :=
  mkMeasuredField (-1837 / 10000 : ℝ) (-1690 / 10000 : ℝ) (-298 / 10000 : ℝ)

/-- chgnet/Ni measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -980e-4 from Δγ₁₀₀ = 1.9523 − 2.2080 J/m² on a₀²/2, P(9) = -673e-4 from Δγ₁₁₁ = 1.7211 − 1.9240 J/m² on √3a₀²/4, P(11) = -136e-4 from ΔE_vac = 1.2274 − 1.3900 eV over 12 shell atoms; a₀ = 3.5035 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ni : MeasuredField 12 :=
  mkMeasuredField (-980 / 10000 : ℝ) (-673 / 10000 : ℝ) (-136 / 10000 : ℝ)

/-- chgnet/Pd measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2063e-4 from Δγ₁₀₀ = 1.1027 − 1.5260 J/m² on a₀²/2, P(9) = -1612e-4 from Δγ₁₁₁ = 0.9561 − 1.3380 J/m² on √3a₀²/4, P(11) = -245e-4 from ΔE_vac = 0.8659 − 1.1600 eV over 12 shell atoms; a₀ = 3.9513 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Pd : MeasuredField 12 :=
  mkMeasuredField (-2063 / 10000 : ℝ) (-1612 / 10000 : ℝ) (-245 / 10000 : ℝ)

/-- chgnet/Pt measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2766e-4 from Δγ₁₀₀ = 1.2808 − 1.8420 J/m² on a₀²/2, P(9) = -1683e-4 from Δγ₁₁₁ = 1.0848 − 1.4790 J/m² on √3a₀²/4, P(11) = 156e-4 from ΔE_vac = 0.7976 − 0.6100 eV over 12 shell atoms; a₀ = 3.9744 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Pt : MeasuredField 12 :=
  mkMeasuredField (-2766 / 10000 : ℝ) (-1683 / 10000 : ℝ) (156 / 10000 : ℝ)

/-- chgnet/Sr measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1386e-4 from Δγ₁₀₀ = 0.2251 − 0.3470 J/m² on a₀²/2, P(9) = -1646e-4 from Δγ₁₁₁ = 0.1748 − 0.3420 J/m² on √3a₀²/4, P(11) = -322e-4 from ΔE_vac = 0.5630 − 0.9500 eV over 12 shell atoms; a₀ = 6.0354 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Sr : MeasuredField 12 :=
  mkMeasuredField (-1386 / 10000 : ℝ) (-1646 / 10000 : ℝ) (-322 / 10000 : ℝ)

/-- mace-mp-medium/Ag measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -22e-4 from Δγ₁₀₀ = 0.8059 − 0.8100 J/m² on a₀²/2, P(9) = -356e-4 from Δγ₁₁₁ = 0.6971 − 0.7730 J/m² on √3a₀²/4, P(11) = 0e-4 from ΔE_vac = 0.6802 − 0.6800 eV over 12 shell atoms; a₀ = 4.1677 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ag : MeasuredField 12 :=
  mkMeasuredField (-22 / 10000 : ℝ) (-356 / 10000 : ℝ) (0 / 10000 : ℝ)

/-- mace-mp-medium/Al measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -423e-4 from Δγ₁₀₀ = 0.8328 − 0.9150 J/m² on a₀²/2, P(9) = -645e-4 from Δγ₁₁₁ = 0.6503 − 0.7950 J/m² on √3a₀²/4, P(11) = -107e-4 from ΔE_vac = 0.4812 − 0.6100 eV over 12 shell atoms; a₀ = 4.0604 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Al : MeasuredField 12 :=
  mkMeasuredField (-423 / 10000 : ℝ) (-645 / 10000 : ℝ) (-107 / 10000 : ℝ)

/-- mace-mp-medium/Au measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 21e-4 from Δγ₁₀₀ = 0.8649 − 0.8610 J/m² on a₀²/2, P(9) = -265e-4 from Δγ₁₁₁ = 0.6857 − 0.7420 J/m² on √3a₀²/4, P(11) = 33e-4 from ΔE_vac = 0.4394 − 0.4000 eV over 12 shell atoms; a₀ = 4.1765 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Au : MeasuredField 12 :=
  mkMeasuredField (21 / 10000 : ℝ) (-265 / 10000 : ℝ) (33 / 10000 : ℝ)

/-- mace-mp-medium/Ca measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -218e-4 from Δγ₁₀₀ = 0.4349 − 0.4580 J/m² on a₀²/2, P(9) = -825e-4 from Δγ₁₁₁ = 0.3600 − 0.4610 J/m² on √3a₀²/4, P(11) = -150e-4 from ΔE_vac = 0.9501 − 1.1300 eV over 12 shell atoms; a₀ = 5.4972 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ca : MeasuredField 12 :=
  mkMeasuredField (-218 / 10000 : ℝ) (-825 / 10000 : ℝ) (-150 / 10000 : ℝ)

/-- mace-mp-medium/Cu measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 131e-4 from Δγ₁₀₀ = 1.5000 − 1.4680 J/m² on a₀²/2, P(9) = -37e-4 from Δγ₁₁₁ = 1.3037 − 1.3140 J/m² on √3a₀²/4, P(11) = -21e-4 from ΔE_vac = 1.0443 − 1.0700 eV over 12 shell atoms; a₀ = 3.6257 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Cu : MeasuredField 12 :=
  mkMeasuredField (131 / 10000 : ℝ) (-37 / 10000 : ℝ) (-21 / 10000 : ℝ)

/-- mace-mp-medium/Ni measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1052e-4 from Δγ₁₀₀ = 1.9345 − 2.2080 J/m² on a₀²/2, P(9) = -310e-4 from Δγ₁₁₁ = 1.8310 − 1.9240 J/m² on √3a₀²/4, P(11) = -229e-4 from ΔE_vac = 1.1154 − 1.3900 eV over 12 shell atoms; a₀ = 3.5104 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ni : MeasuredField 12 :=
  mkMeasuredField (-1052 / 10000 : ℝ) (-310 / 10000 : ℝ) (-229 / 10000 : ℝ)

/-- mace-mp-medium/Pd measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -612e-4 from Δγ₁₀₀ = 1.4008 − 1.5260 J/m² on a₀²/2, P(9) = -148e-4 from Δγ₁₁₁ = 1.3032 − 1.3380 J/m² on √3a₀²/4, P(11) = 18e-4 from ΔE_vac = 1.1822 − 1.1600 eV over 12 shell atoms; a₀ = 3.9579 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Pd : MeasuredField 12 :=
  mkMeasuredField (-612 / 10000 : ℝ) (-148 / 10000 : ℝ) (18 / 10000 : ℝ)

/-- mace-mp-medium/Pt measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1075e-4 from Δγ₁₀₀ = 1.6241 − 1.8420 J/m² on a₀²/2, P(9) = -876e-4 from Δγ₁₁₁ = 1.2739 − 1.4790 J/m² on √3a₀²/4, P(11) = -142e-4 from ΔE_vac = 0.4392 − 0.6100 eV over 12 shell atoms; a₀ = 3.9762 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Pt : MeasuredField 12 :=
  mkMeasuredField (-1075 / 10000 : ℝ) (-876 / 10000 : ℝ) (-142 / 10000 : ℝ)

/-- mace-mp-medium/Sr measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -690e-4 from Δγ₁₀₀ = 0.2859 − 0.3470 J/m² on a₀²/2, P(9) = -1151e-4 from Δγ₁₁₁ = 0.2244 − 0.3420 J/m² on √3a₀²/4, P(11) = -238e-4 from ΔE_vac = 0.6649 − 0.9500 eV over 12 shell atoms; a₀ = 6.0162 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Sr : MeasuredField 12 :=
  mkMeasuredField (-690 / 10000 : ℝ) (-1151 / 10000 : ℝ) (-238 / 10000 : ℝ)

/-- mace-mp-small/Ag measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 451e-4 from Δγ₁₀₀ = 0.8932 − 0.8100 J/m² on a₀²/2, P(9) = -389e-4 from Δγ₁₁₁ = 0.6901 − 0.7730 J/m² on √3a₀²/4, P(11) = -44e-4 from ΔE_vac = 0.6271 − 0.6800 eV over 12 shell atoms; a₀ = 4.1679 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ag : MeasuredField 12 :=
  mkMeasuredField (451 / 10000 : ℝ) (-389 / 10000 : ℝ) (-44 / 10000 : ℝ)

/-- mace-mp-small/Al measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -496e-4 from Δγ₁₀₀ = 0.8183 − 0.9150 J/m² on a₀²/2, P(9) = -667e-4 from Δγ₁₁₁ = 0.6447 − 0.7950 J/m² on √3a₀²/4, P(11) = -21e-4 from ΔE_vac = 0.5851 − 0.6100 eV over 12 shell atoms; a₀ = 4.0531 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Al : MeasuredField 12 :=
  mkMeasuredField (-496 / 10000 : ℝ) (-667 / 10000 : ℝ) (-21 / 10000 : ℝ)

/-- mace-mp-small/Au measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 569e-4 from Δγ₁₀₀ = 0.9660 − 0.8610 J/m² on a₀²/2, P(9) = 54e-4 from Δγ₁₁₁ = 0.7535 − 0.7420 J/m² on √3a₀²/4, P(11) = 30e-4 from ΔE_vac = 0.4356 − 0.4000 eV over 12 shell atoms; a₀ = 4.1681 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Au : MeasuredField 12 :=
  mkMeasuredField (569 / 10000 : ℝ) (54 / 10000 : ℝ) (30 / 10000 : ℝ)

/-- mace-mp-small/Ca measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 196e-4 from Δγ₁₀₀ = 0.4786 − 0.4580 J/m² on a₀²/2, P(9) = -555e-4 from Δγ₁₁₁ = 0.3935 − 0.4610 J/m² on √3a₀²/4, P(11) = -96e-4 from ΔE_vac = 1.0145 − 1.1300 eV over 12 shell atoms; a₀ = 5.5163 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ca : MeasuredField 12 :=
  mkMeasuredField (196 / 10000 : ℝ) (-555 / 10000 : ℝ) (-96 / 10000 : ℝ)

/-- mace-mp-small/Cu measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 335e-4 from Δγ₁₀₀ = 1.5503 − 1.4680 J/m² on a₀²/2, P(9) = 9e-4 from Δγ₁₁₁ = 1.3165 − 1.3140 J/m² on √3a₀²/4, P(11) = -35e-4 from ΔE_vac = 1.0285 − 1.0700 eV over 12 shell atoms; a₀ = 3.6128 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Cu : MeasuredField 12 :=
  mkMeasuredField (335 / 10000 : ℝ) (9 / 10000 : ℝ) (-35 / 10000 : ℝ)

/-- mace-mp-small/Ni measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 1473e-4 from Δγ₁₀₀ = 2.5907 − 2.2080 J/m² on a₀²/2, P(9) = 934e-4 from Δγ₁₁₁ = 2.2042 − 1.9240 J/m² on √3a₀²/4, P(11) = -310e-4 from ΔE_vac = 1.0175 − 1.3900 eV over 12 shell atoms; a₀ = 3.5115 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ni : MeasuredField 12 :=
  mkMeasuredField (1473 / 10000 : ℝ) (934 / 10000 : ℝ) (-310 / 10000 : ℝ)

/-- mace-mp-small/Pd measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 671e-4 from Δγ₁₀₀ = 1.6629 − 1.5260 J/m² on a₀²/2, P(9) = 322e-4 from Δγ₁₁₁ = 1.4139 − 1.3380 J/m² on √3a₀²/4, P(11) = 68e-4 from ΔE_vac = 1.2411 − 1.1600 eV over 12 shell atoms; a₀ = 3.9644 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Pd : MeasuredField 12 :=
  mkMeasuredField (671 / 10000 : ℝ) (322 / 10000 : ℝ) (68 / 10000 : ℝ)

/-- mace-mp-small/Pt measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 1098e-4 from Δγ₁₀₀ = 2.0640 − 1.8420 J/m² on a₀²/2, P(9) = 901e-4 from Δγ₁₁₁ = 1.6892 − 1.4790 J/m² on √3a₀²/4, P(11) = 236e-4 from ΔE_vac = 0.8927 − 0.6100 eV over 12 shell atoms; a₀ = 3.9820 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Pt : MeasuredField 12 :=
  mkMeasuredField (1098 / 10000 : ℝ) (901 / 10000 : ℝ) (236 / 10000 : ℝ)

/-- mace-mp-small/Sr measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -620e-4 from Δγ₁₀₀ = 0.2917 − 0.3470 J/m² on a₀²/2, P(9) = -1031e-4 from Δγ₁₁₁ = 0.2358 − 0.3420 J/m² on √3a₀²/4, P(11) = -139e-4 from ΔE_vac = 0.7827 − 0.9500 eV over 12 shell atoms; a₀ = 5.9925 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Sr : MeasuredField 12 :=
  mkMeasuredField (-620 / 10000 : ℝ) (-1031 / 10000 : ℝ) (-139 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ag measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 23e-4 from Δγ₁₀₀ = 0.8143 − 0.8100 J/m² on a₀²/2, P(9) = -329e-4 from Δγ₁₁₁ = 0.7027 − 0.7730 J/m² on √3a₀²/4, P(11) = 80e-4 from ΔE_vac = 0.7764 − 0.6800 eV over 12 shell atoms; a₀ = 4.1616 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ag : MeasuredField 12 :=
  mkMeasuredField (23 / 10000 : ℝ) (-329 / 10000 : ℝ) (80 / 10000 : ℝ)

/-- mace-mpa-0-medium/Al measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 416e-4 from Δγ₁₀₀ = 0.9968 − 0.9150 J/m² on a₀²/2, P(9) = -49e-4 from Δγ₁₁₁ = 0.7840 − 0.7950 J/m² on √3a₀²/4, P(11) = 57e-4 from ΔE_vac = 0.6781 − 0.6100 eV over 12 shell atoms; a₀ = 4.0386 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Al : MeasuredField 12 :=
  mkMeasuredField (416 / 10000 : ℝ) (-49 / 10000 : ℝ) (57 / 10000 : ℝ)

/-- mace-mpa-0-medium/Au measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 99e-4 from Δγ₁₀₀ = 0.8793 − 0.8610 J/m² on a₀²/2, P(9) = -260e-4 from Δγ₁₁₁ = 0.6865 − 0.7420 J/m² on √3a₀²/4, P(11) = 59e-4 from ΔE_vac = 0.4705 − 0.4000 eV over 12 shell atoms; a₀ = 4.1665 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Au : MeasuredField 12 :=
  mkMeasuredField (99 / 10000 : ℝ) (-260 / 10000 : ℝ) (59 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ca measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -278e-4 from Δγ₁₀₀ = 0.4290 − 0.4580 J/m² on a₀²/2, P(9) = -544e-4 from Δγ₁₁₁ = 0.3956 − 0.4610 J/m² on √3a₀²/4, P(11) = -91e-4 from ΔE_vac = 1.0205 − 1.1300 eV over 12 shell atoms; a₀ = 5.5449 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ca : MeasuredField 12 :=
  mkMeasuredField (-278 / 10000 : ℝ) (-544 / 10000 : ℝ) (-91 / 10000 : ℝ)

/-- mace-mpa-0-medium/Cu measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -209e-4 from Δγ₁₀₀ = 1.4176 − 1.4680 J/m² on a₀²/2, P(9) = -306e-4 from Δγ₁₁₁ = 1.2284 − 1.3140 J/m² on √3a₀²/4, P(11) = -2e-4 from ΔE_vac = 1.0675 − 1.0700 eV over 12 shell atoms; a₀ = 3.6398 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Cu : MeasuredField 12 :=
  mkMeasuredField (-209 / 10000 : ℝ) (-306 / 10000 : ℝ) (-2 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ni measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 4190e-4 from Δγ₁₀₀ = 3.2907 − 2.2080 J/m² on a₀²/2, P(9) = 2296e-4 from Δγ₁₁₁ = 2.6092 − 1.9240 J/m² on √3a₀²/4, P(11) = 125e-4 from ΔE_vac = 1.5398 − 1.3900 eV over 12 shell atoms; a₀ = 3.5213 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ni : MeasuredField 12 :=
  mkMeasuredField (4190 / 10000 : ℝ) (2296 / 10000 : ℝ) (125 / 10000 : ℝ)

/-- mace-mpa-0-medium/Pd measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 346e-4 from Δγ₁₀₀ = 1.5966 − 1.5260 J/m² on a₀²/2, P(9) = 40e-4 from Δγ₁₁₁ = 1.3473 − 1.3380 J/m² on √3a₀²/4, P(11) = 42e-4 from ΔE_vac = 1.2100 − 1.1600 eV over 12 shell atoms; a₀ = 3.9596 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Pd : MeasuredField 12 :=
  mkMeasuredField (346 / 10000 : ℝ) (40 / 10000 : ℝ) (42 / 10000 : ℝ)

/-- mace-mpa-0-medium/Pt measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 962e-4 from Δγ₁₀₀ = 2.0370 − 1.8420 J/m² on a₀²/2, P(9) = 814e-4 from Δγ₁₁₁ = 1.6695 − 1.4790 J/m² on √3a₀²/4, P(11) = 181e-4 from ΔE_vac = 0.8273 − 0.6100 eV over 12 shell atoms; a₀ = 3.9766 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Pt : MeasuredField 12 :=
  mkMeasuredField (962 / 10000 : ℝ) (814 / 10000 : ℝ) (181 / 10000 : ℝ)

/-- mace-mpa-0-medium/Sr measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -750e-4 from Δγ₁₀₀ = 0.2809 − 0.3470 J/m² on a₀²/2, P(9) = -780e-4 from Δγ₁₁₁ = 0.2626 − 0.3420 J/m² on √3a₀²/4, P(11) = -4e-4 from ΔE_vac = 0.9451 − 0.9500 eV over 12 shell atoms; a₀ = 6.0298 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Sr : MeasuredField 12 :=
  mkMeasuredField (-750 / 10000 : ℝ) (-780 / 10000 : ℝ) (-4 / 10000 : ℝ)

/-! ## Tier 2: anchored softening fields (monotone-softening cells) -/

/-- chgnet/Ag anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Ag` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Ag : ErrorField 12 :=
  mkAnchoredField (-1359 / 10000 : ℝ) (-1355 / 10000 : ℝ) (-156 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Al anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Al` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Al : ErrorField 12 :=
  mkAnchoredField (-2230 / 10000 : ℝ) (-1862 / 10000 : ℝ) (-394 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Au anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Au` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Au : ErrorField 12 :=
  mkAnchoredField (-2372 / 10000 : ℝ) (-1819 / 10000 : ℝ) (-83 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Cu anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Cu` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Cu : ErrorField 12 :=
  mkAnchoredField (-1837 / 10000 : ℝ) (-1690 / 10000 : ℝ) (-298 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Ni anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Ni` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Ni : ErrorField 12 :=
  mkAnchoredField (-980 / 10000 : ℝ) (-673 / 10000 : ℝ) (-136 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Pd anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Pd` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Pd : ErrorField 12 :=
  mkAnchoredField (-2063 / 10000 : ℝ) (-1612 / 10000 : ℝ) (-245 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Ni anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Ni` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Ni : ErrorField 12 :=
  mkAnchoredField (-1052 / 10000 : ℝ) (-310 / 10000 : ℝ) (-229 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Pt anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Pt` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Pt : ErrorField 12 :=
  mkAnchoredField (-1075 / 10000 : ℝ) (-876 / 10000 : ℝ) (-142 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-! ## Tier-2 refusal certificates (outside the softening domain) -/

/-- chgnet/Ca tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-926, -1363, -316)e-4 eV/atom violate monotone softening — P(8) = -926e-4 > P(9) = -1363e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Ca` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Ca :
    ¬ scaledAnchorsValid (-926) (-1363) (-316) := by decide

/-- chgnet/Pt tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-2766, -1683, 156)e-4 eV/atom violate monotone softening — P(11) = 156e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Pt` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Pt :
    ¬ scaledAnchorsValid (-2766) (-1683) 156 := by decide

/-- chgnet/Sr tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-1386, -1646, -322)e-4 eV/atom violate monotone softening — P(8) = -1386e-4 > P(9) = -1646e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Sr` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Sr :
    ¬ scaledAnchorsValid (-1386) (-1646) (-322) := by decide

/-- mace-mp-medium/Ag tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-22, -356, 0)e-4 eV/atom violate monotone softening — P(8) = -22e-4 > P(9) = -356e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Ag :
    ¬ scaledAnchorsValid (-22) (-356) 0 := by decide

/-- mace-mp-medium/Al tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-423, -645, -107)e-4 eV/atom violate monotone softening — P(8) = -423e-4 > P(9) = -645e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Al :
    ¬ scaledAnchorsValid (-423) (-645) (-107) := by decide

/-- mace-mp-medium/Au tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (21, -265, 33)e-4 eV/atom violate monotone softening — P(8) = 21e-4 > P(9) = -265e-4 (mono); P(11) = 33e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Au :
    ¬ scaledAnchorsValid 21 (-265) 33 := by decide

/-- mace-mp-medium/Ca tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-218, -825, -150)e-4 eV/atom violate monotone softening — P(8) = -218e-4 > P(9) = -825e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Ca :
    ¬ scaledAnchorsValid (-218) (-825) (-150) := by decide

/-- mace-mp-medium/Cu tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (131, -37, -21)e-4 eV/atom violate monotone softening — P(8) = 131e-4 > P(9) = -37e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Cu :
    ¬ scaledAnchorsValid 131 (-37) (-21) := by decide

/-- mace-mp-medium/Pd tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-612, -148, 18)e-4 eV/atom violate monotone softening — P(11) = 18e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Pd :
    ¬ scaledAnchorsValid (-612) (-148) 18 := by decide

/-- mace-mp-medium/Sr tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-690, -1151, -238)e-4 eV/atom violate monotone softening — P(8) = -690e-4 > P(9) = -1151e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Sr :
    ¬ scaledAnchorsValid (-690) (-1151) (-238) := by decide

/-- mace-mp-small/Ag tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (451, -389, -44)e-4 eV/atom violate monotone softening — P(8) = 451e-4 > P(9) = -389e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ag :
    ¬ scaledAnchorsValid 451 (-389) (-44) := by decide

/-- mace-mp-small/Al tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-496, -667, -21)e-4 eV/atom violate monotone softening — P(8) = -496e-4 > P(9) = -667e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Al :
    ¬ scaledAnchorsValid (-496) (-667) (-21) := by decide

/-- mace-mp-small/Au tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (569, 54, 30)e-4 eV/atom violate monotone softening — P(8) = 569e-4 > P(9) = 54e-4 (mono); P(9) = 54e-4 > P(11) = 30e-4 (mono); P(11) = 30e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Au :
    ¬ scaledAnchorsValid 569 54 30 := by decide

/-- mace-mp-small/Ca tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (196, -555, -96)e-4 eV/atom violate monotone softening — P(8) = 196e-4 > P(9) = -555e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ca :
    ¬ scaledAnchorsValid 196 (-555) (-96) := by decide

/-- mace-mp-small/Cu tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (335, 9, -35)e-4 eV/atom violate monotone softening — P(8) = 335e-4 > P(9) = 9e-4 (mono); P(9) = 9e-4 > P(11) = -35e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Cu :
    ¬ scaledAnchorsValid 335 9 (-35) := by decide

/-- mace-mp-small/Ni tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (1473, 934, -310)e-4 eV/atom violate monotone softening — P(8) = 1473e-4 > P(9) = 934e-4 (mono); P(9) = 934e-4 > P(11) = -310e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ni` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ni :
    ¬ scaledAnchorsValid 1473 934 (-310) := by decide

/-- mace-mp-small/Pd tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (671, 322, 68)e-4 eV/atom violate monotone softening — P(8) = 671e-4 > P(9) = 322e-4 (mono); P(9) = 322e-4 > P(11) = 68e-4 (mono); P(11) = 68e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Pd :
    ¬ scaledAnchorsValid 671 322 68 := by decide

/-- mace-mp-small/Pt tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (1098, 901, 236)e-4 eV/atom violate monotone softening — P(8) = 1098e-4 > P(9) = 901e-4 (mono); P(9) = 901e-4 > P(11) = 236e-4 (mono); P(11) = 236e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Pt` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Pt :
    ¬ scaledAnchorsValid 1098 901 236 := by decide

/-- mace-mp-small/Sr tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-620, -1031, -139)e-4 eV/atom violate monotone softening — P(8) = -620e-4 > P(9) = -1031e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Sr :
    ¬ scaledAnchorsValid (-620) (-1031) (-139) := by decide

/-- mace-mpa-0-medium/Ag tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (23, -329, 80)e-4 eV/atom violate monotone softening — P(8) = 23e-4 > P(9) = -329e-4 (mono); P(11) = 80e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ag :
    ¬ scaledAnchorsValid 23 (-329) 80 := by decide

/-- mace-mpa-0-medium/Al tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (416, -49, 57)e-4 eV/atom violate monotone softening — P(8) = 416e-4 > P(9) = -49e-4 (mono); P(11) = 57e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Al :
    ¬ scaledAnchorsValid 416 (-49) 57 := by decide

/-- mace-mpa-0-medium/Au tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (99, -260, 59)e-4 eV/atom violate monotone softening — P(8) = 99e-4 > P(9) = -260e-4 (mono); P(11) = 59e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Au :
    ¬ scaledAnchorsValid 99 (-260) 59 := by decide

/-- mace-mpa-0-medium/Ca tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-278, -544, -91)e-4 eV/atom violate monotone softening — P(8) = -278e-4 > P(9) = -544e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ca :
    ¬ scaledAnchorsValid (-278) (-544) (-91) := by decide

/-- mace-mpa-0-medium/Cu tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-209, -306, -2)e-4 eV/atom violate monotone softening — P(8) = -209e-4 > P(9) = -306e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Cu :
    ¬ scaledAnchorsValid (-209) (-306) (-2) := by decide

/-- mace-mpa-0-medium/Ni tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (4190, 2296, 125)e-4 eV/atom violate monotone softening — P(8) = 4190e-4 > P(9) = 2296e-4 (mono); P(9) = 2296e-4 > P(11) = 125e-4 (mono); P(11) = 125e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ni` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ni :
    ¬ scaledAnchorsValid 4190 2296 125 := by decide

/-- mace-mpa-0-medium/Pd tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (346, 40, 42)e-4 eV/atom violate monotone softening — P(8) = 346e-4 > P(9) = 40e-4 (mono); P(11) = 42e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Pd :
    ¬ scaledAnchorsValid 346 40 42 := by decide

/-- mace-mpa-0-medium/Pt tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (962, 814, 181)e-4 eV/atom violate monotone softening — P(8) = 962e-4 > P(9) = 814e-4 (mono); P(9) = 814e-4 > P(11) = 181e-4 (mono); P(11) = 181e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Pt` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Pt :
    ¬ scaledAnchorsValid 962 814 181 := by decide

/-- mace-mpa-0-medium/Sr tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-750, -780, -4)e-4 eV/atom violate monotone softening — P(8) = -750e-4 > P(9) = -780e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Sr :
    ¬ scaledAnchorsValid (-750) (-780) (-4) := by decide

/-- Every sweep cell is accounted for: instances + refusals = cells. -/
theorem cells_accounted : 8 + 28 = 36 := by
  decide

end OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances
