/- AUTHORED by python/scripts/bind_env_field_instances.py from the
   Y-matrix statics corpus + DFT-PBE targets (corpus sha256 c4393f3e3bcb).
   THE MEASURED FIELDS: per (model, material) cell, the measured anchors —
   fcc: P(8)/P(9)/P(11) with bulk pin c = 12; bcc: P(4)/P(6)/P(7) with
   bulk pin c = 8; diamond: P(3) with bulk pin c = 4 (eV/atom, x1e-4
   exact integers) — are bound from the facet surface-energy and
   vacancy-formation errors on model-relaxed geometry.
   TIER 1: every cell yields a `MeasuredField`
   (closure/transfer/ranking laws, no shape assumption). TIER 2: cells
   passing monotone softening (p_lo <= p_mid <= p_hi <= 0, checked on
   the emitted literals) also yield an `ErrorField` via
   the layout constructor (directional barrier laws);
   violating cells get kernel-checked refusal certificates instead.
   68 measured fields; fcc: 8 instances + 28 refusals = 36 cells; bcc: 7 instances + 21 refusals = 28 cells; diamond: 4 instances + 0 refusals = 4 cells; rocksalt: 0 instances + 0 refusals = 0 cells;
   total 19 instances + 49 refusals =
   68 cells. 0 sorry. -/

import OpenDistillationFactory.Materials.Theory.AnchoredField

namespace OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances

open OpenDistillationFactory.Materials.Theory.EnvironmentField
open OpenDistillationFactory.Materials.Theory.AnchoredField

/-! ## Tier 1: measured fields (every bound cell) -/

/-- chgnet/Ag (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1359e-4 from Δγ₁₀₀ = 0.5578 − 0.8100 J/m² on a₀²/2, P(9) = -1355e-4 from Δγ₁₁₁ = 0.4828 − 0.7730 J/m² on √3a₀²/4, P(11) = -156e-4 from ΔE_vac = 0.4931 − 0.6800 eV over 12 shell atoms; a₀ = 4.1560 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ag : MeasuredField 12 :=
  mkMeasuredField (-1359 / 10000 : ℝ) (-1355 / 10000 : ℝ) (-156 / 10000 : ℝ)

/-- chgnet/Al (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2230e-4 from Δγ₁₀₀ = 0.4775 − 0.9150 J/m² on a₀²/2, P(9) = -1862e-4 from Δγ₁₁₁ = 0.3732 − 0.7950 J/m² on √3a₀²/4, P(11) = -394e-4 from ΔE_vac = 0.1372 − 0.6100 eV over 12 shell atoms; a₀ = 4.0414 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Al : MeasuredField 12 :=
  mkMeasuredField (-2230 / 10000 : ℝ) (-1862 / 10000 : ℝ) (-394 / 10000 : ℝ)

/-- chgnet/Au (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2372e-4 from Δγ₁₀₀ = 0.4238 − 0.8610 J/m² on a₀²/2, P(9) = -1819e-4 from Δγ₁₁₁ = 0.3550 − 0.7420 J/m² on √3a₀²/4, P(11) = -83e-4 from ΔE_vac = 0.3000 − 0.4000 eV over 12 shell atoms; a₀ = 4.1698 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Au : MeasuredField 12 :=
  mkMeasuredField (-2372 / 10000 : ℝ) (-1819 / 10000 : ℝ) (-83 / 10000 : ℝ)

/-- chgnet/Ca (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -926e-4 from Δγ₁₀₀ = 0.3608 − 0.4580 J/m² on a₀²/2, P(9) = -1363e-4 from Δγ₁₁₁ = 0.2959 − 0.4610 J/m² on √3a₀²/4, P(11) = -316e-4 from ΔE_vac = 0.7508 − 1.1300 eV over 12 shell atoms; a₀ = 5.5263 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ca : MeasuredField 12 :=
  mkMeasuredField (-926 / 10000 : ℝ) (-1363 / 10000 : ℝ) (-316 / 10000 : ℝ)

/-- chgnet/Cu (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1837e-4 from Δγ₁₀₀ = 1.0179 − 1.4680 J/m² on a₀²/2, P(9) = -1690e-4 from Δγ₁₁₁ = 0.8358 − 1.3140 J/m² on √3a₀²/4, P(11) = -298e-4 from ΔE_vac = 0.7122 − 1.0700 eV over 12 shell atoms; a₀ = 3.6159 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Cu : MeasuredField 12 :=
  mkMeasuredField (-1837 / 10000 : ℝ) (-1690 / 10000 : ℝ) (-298 / 10000 : ℝ)

/-- chgnet/Ni (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -980e-4 from Δγ₁₀₀ = 1.9523 − 2.2080 J/m² on a₀²/2, P(9) = -673e-4 from Δγ₁₁₁ = 1.7211 − 1.9240 J/m² on √3a₀²/4, P(11) = -136e-4 from ΔE_vac = 1.2274 − 1.3900 eV over 12 shell atoms; a₀ = 3.5035 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ni : MeasuredField 12 :=
  mkMeasuredField (-980 / 10000 : ℝ) (-673 / 10000 : ℝ) (-136 / 10000 : ℝ)

/-- chgnet/Pd (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2063e-4 from Δγ₁₀₀ = 1.1027 − 1.5260 J/m² on a₀²/2, P(9) = -1612e-4 from Δγ₁₁₁ = 0.9561 − 1.3380 J/m² on √3a₀²/4, P(11) = -245e-4 from ΔE_vac = 0.8659 − 1.1600 eV over 12 shell atoms; a₀ = 3.9513 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Pd : MeasuredField 12 :=
  mkMeasuredField (-2063 / 10000 : ℝ) (-1612 / 10000 : ℝ) (-245 / 10000 : ℝ)

/-- chgnet/Pt (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -2766e-4 from Δγ₁₀₀ = 1.2808 − 1.8420 J/m² on a₀²/2, P(9) = -1683e-4 from Δγ₁₁₁ = 1.0848 − 1.4790 J/m² on √3a₀²/4, P(11) = 156e-4 from ΔE_vac = 0.7976 − 0.6100 eV over 12 shell atoms; a₀ = 3.9744 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Pt : MeasuredField 12 :=
  mkMeasuredField (-2766 / 10000 : ℝ) (-1683 / 10000 : ℝ) (156 / 10000 : ℝ)

/-- chgnet/Sr (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1386e-4 from Δγ₁₀₀ = 0.2251 − 0.3470 J/m² on a₀²/2, P(9) = -1646e-4 from Δγ₁₁₁ = 0.1748 − 0.3420 J/m² on √3a₀²/4, P(11) = -322e-4 from ΔE_vac = 0.5630 − 0.9500 eV over 12 shell atoms; a₀ = 6.0354 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Sr : MeasuredField 12 :=
  mkMeasuredField (-1386 / 10000 : ℝ) (-1646 / 10000 : ℝ) (-322 / 10000 : ℝ)

/-- mace-mp-medium/Ag (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -22e-4 from Δγ₁₀₀ = 0.8059 − 0.8100 J/m² on a₀²/2, P(9) = -356e-4 from Δγ₁₁₁ = 0.6971 − 0.7730 J/m² on √3a₀²/4, P(11) = 0e-4 from ΔE_vac = 0.6802 − 0.6800 eV over 12 shell atoms; a₀ = 4.1677 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ag : MeasuredField 12 :=
  mkMeasuredField (-22 / 10000 : ℝ) (-356 / 10000 : ℝ) (0 / 10000 : ℝ)

/-- mace-mp-medium/Al (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -423e-4 from Δγ₁₀₀ = 0.8328 − 0.9150 J/m² on a₀²/2, P(9) = -645e-4 from Δγ₁₁₁ = 0.6503 − 0.7950 J/m² on √3a₀²/4, P(11) = -107e-4 from ΔE_vac = 0.4812 − 0.6100 eV over 12 shell atoms; a₀ = 4.0604 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Al : MeasuredField 12 :=
  mkMeasuredField (-423 / 10000 : ℝ) (-645 / 10000 : ℝ) (-107 / 10000 : ℝ)

/-- mace-mp-medium/Au (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 21e-4 from Δγ₁₀₀ = 0.8649 − 0.8610 J/m² on a₀²/2, P(9) = -265e-4 from Δγ₁₁₁ = 0.6857 − 0.7420 J/m² on √3a₀²/4, P(11) = 33e-4 from ΔE_vac = 0.4394 − 0.4000 eV over 12 shell atoms; a₀ = 4.1765 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Au : MeasuredField 12 :=
  mkMeasuredField (21 / 10000 : ℝ) (-265 / 10000 : ℝ) (33 / 10000 : ℝ)

/-- mace-mp-medium/Ca (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -218e-4 from Δγ₁₀₀ = 0.4349 − 0.4580 J/m² on a₀²/2, P(9) = -825e-4 from Δγ₁₁₁ = 0.3600 − 0.4610 J/m² on √3a₀²/4, P(11) = -150e-4 from ΔE_vac = 0.9501 − 1.1300 eV over 12 shell atoms; a₀ = 5.4972 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ca : MeasuredField 12 :=
  mkMeasuredField (-218 / 10000 : ℝ) (-825 / 10000 : ℝ) (-150 / 10000 : ℝ)

/-- mace-mp-medium/Cu (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 131e-4 from Δγ₁₀₀ = 1.5000 − 1.4680 J/m² on a₀²/2, P(9) = -37e-4 from Δγ₁₁₁ = 1.3037 − 1.3140 J/m² on √3a₀²/4, P(11) = -21e-4 from ΔE_vac = 1.0443 − 1.0700 eV over 12 shell atoms; a₀ = 3.6257 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Cu : MeasuredField 12 :=
  mkMeasuredField (131 / 10000 : ℝ) (-37 / 10000 : ℝ) (-21 / 10000 : ℝ)

/-- mace-mp-medium/Ni (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1052e-4 from Δγ₁₀₀ = 1.9345 − 2.2080 J/m² on a₀²/2, P(9) = -310e-4 from Δγ₁₁₁ = 1.8310 − 1.9240 J/m² on √3a₀²/4, P(11) = -229e-4 from ΔE_vac = 1.1154 − 1.3900 eV over 12 shell atoms; a₀ = 3.5104 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ni : MeasuredField 12 :=
  mkMeasuredField (-1052 / 10000 : ℝ) (-310 / 10000 : ℝ) (-229 / 10000 : ℝ)

/-- mace-mp-medium/Pd (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -612e-4 from Δγ₁₀₀ = 1.4008 − 1.5260 J/m² on a₀²/2, P(9) = -148e-4 from Δγ₁₁₁ = 1.3032 − 1.3380 J/m² on √3a₀²/4, P(11) = 18e-4 from ΔE_vac = 1.1822 − 1.1600 eV over 12 shell atoms; a₀ = 3.9579 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Pd : MeasuredField 12 :=
  mkMeasuredField (-612 / 10000 : ℝ) (-148 / 10000 : ℝ) (18 / 10000 : ℝ)

/-- mace-mp-medium/Pt (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -1075e-4 from Δγ₁₀₀ = 1.6241 − 1.8420 J/m² on a₀²/2, P(9) = -876e-4 from Δγ₁₁₁ = 1.2739 − 1.4790 J/m² on √3a₀²/4, P(11) = -142e-4 from ΔE_vac = 0.4392 − 0.6100 eV over 12 shell atoms; a₀ = 3.9762 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Pt : MeasuredField 12 :=
  mkMeasuredField (-1075 / 10000 : ℝ) (-876 / 10000 : ℝ) (-142 / 10000 : ℝ)

/-- mace-mp-medium/Sr (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -690e-4 from Δγ₁₀₀ = 0.2859 − 0.3470 J/m² on a₀²/2, P(9) = -1151e-4 from Δγ₁₁₁ = 0.2244 − 0.3420 J/m² on √3a₀²/4, P(11) = -238e-4 from ΔE_vac = 0.6649 − 0.9500 eV over 12 shell atoms; a₀ = 6.0162 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Sr : MeasuredField 12 :=
  mkMeasuredField (-690 / 10000 : ℝ) (-1151 / 10000 : ℝ) (-238 / 10000 : ℝ)

/-- mace-mp-small/Ag (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 451e-4 from Δγ₁₀₀ = 0.8932 − 0.8100 J/m² on a₀²/2, P(9) = -389e-4 from Δγ₁₁₁ = 0.6901 − 0.7730 J/m² on √3a₀²/4, P(11) = -44e-4 from ΔE_vac = 0.6271 − 0.6800 eV over 12 shell atoms; a₀ = 4.1679 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ag : MeasuredField 12 :=
  mkMeasuredField (451 / 10000 : ℝ) (-389 / 10000 : ℝ) (-44 / 10000 : ℝ)

/-- mace-mp-small/Al (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -496e-4 from Δγ₁₀₀ = 0.8183 − 0.9150 J/m² on a₀²/2, P(9) = -667e-4 from Δγ₁₁₁ = 0.6447 − 0.7950 J/m² on √3a₀²/4, P(11) = -21e-4 from ΔE_vac = 0.5851 − 0.6100 eV over 12 shell atoms; a₀ = 4.0531 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Al : MeasuredField 12 :=
  mkMeasuredField (-496 / 10000 : ℝ) (-667 / 10000 : ℝ) (-21 / 10000 : ℝ)

/-- mace-mp-small/Au (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 569e-4 from Δγ₁₀₀ = 0.9660 − 0.8610 J/m² on a₀²/2, P(9) = 54e-4 from Δγ₁₁₁ = 0.7535 − 0.7420 J/m² on √3a₀²/4, P(11) = 30e-4 from ΔE_vac = 0.4356 − 0.4000 eV over 12 shell atoms; a₀ = 4.1681 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Au : MeasuredField 12 :=
  mkMeasuredField (569 / 10000 : ℝ) (54 / 10000 : ℝ) (30 / 10000 : ℝ)

/-- mace-mp-small/Ca (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 196e-4 from Δγ₁₀₀ = 0.4786 − 0.4580 J/m² on a₀²/2, P(9) = -555e-4 from Δγ₁₁₁ = 0.3935 − 0.4610 J/m² on √3a₀²/4, P(11) = -96e-4 from ΔE_vac = 1.0145 − 1.1300 eV over 12 shell atoms; a₀ = 5.5163 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ca : MeasuredField 12 :=
  mkMeasuredField (196 / 10000 : ℝ) (-555 / 10000 : ℝ) (-96 / 10000 : ℝ)

/-- mace-mp-small/Cu (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 335e-4 from Δγ₁₀₀ = 1.5503 − 1.4680 J/m² on a₀²/2, P(9) = 9e-4 from Δγ₁₁₁ = 1.3165 − 1.3140 J/m² on √3a₀²/4, P(11) = -35e-4 from ΔE_vac = 1.0285 − 1.0700 eV over 12 shell atoms; a₀ = 3.6128 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Cu : MeasuredField 12 :=
  mkMeasuredField (335 / 10000 : ℝ) (9 / 10000 : ℝ) (-35 / 10000 : ℝ)

/-- mace-mp-small/Ni (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 1473e-4 from Δγ₁₀₀ = 2.5907 − 2.2080 J/m² on a₀²/2, P(9) = 934e-4 from Δγ₁₁₁ = 2.2042 − 1.9240 J/m² on √3a₀²/4, P(11) = -310e-4 from ΔE_vac = 1.0175 − 1.3900 eV over 12 shell atoms; a₀ = 3.5115 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ni : MeasuredField 12 :=
  mkMeasuredField (1473 / 10000 : ℝ) (934 / 10000 : ℝ) (-310 / 10000 : ℝ)

/-- mace-mp-small/Pd (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 671e-4 from Δγ₁₀₀ = 1.6629 − 1.5260 J/m² on a₀²/2, P(9) = 322e-4 from Δγ₁₁₁ = 1.4139 − 1.3380 J/m² on √3a₀²/4, P(11) = 68e-4 from ΔE_vac = 1.2411 − 1.1600 eV over 12 shell atoms; a₀ = 3.9644 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Pd : MeasuredField 12 :=
  mkMeasuredField (671 / 10000 : ℝ) (322 / 10000 : ℝ) (68 / 10000 : ℝ)

/-- mace-mp-small/Pt (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 1098e-4 from Δγ₁₀₀ = 2.0640 − 1.8420 J/m² on a₀²/2, P(9) = 901e-4 from Δγ₁₁₁ = 1.6892 − 1.4790 J/m² on √3a₀²/4, P(11) = 236e-4 from ΔE_vac = 0.8927 − 0.6100 eV over 12 shell atoms; a₀ = 3.9820 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Pt : MeasuredField 12 :=
  mkMeasuredField (1098 / 10000 : ℝ) (901 / 10000 : ℝ) (236 / 10000 : ℝ)

/-- mace-mp-small/Sr (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -620e-4 from Δγ₁₀₀ = 0.2917 − 0.3470 J/m² on a₀²/2, P(9) = -1031e-4 from Δγ₁₁₁ = 0.2358 − 0.3420 J/m² on √3a₀²/4, P(11) = -139e-4 from ΔE_vac = 0.7827 − 0.9500 eV over 12 shell atoms; a₀ = 5.9925 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Sr : MeasuredField 12 :=
  mkMeasuredField (-620 / 10000 : ℝ) (-1031 / 10000 : ℝ) (-139 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ag (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 23e-4 from Δγ₁₀₀ = 0.8143 − 0.8100 J/m² on a₀²/2, P(9) = -329e-4 from Δγ₁₁₁ = 0.7027 − 0.7730 J/m² on √3a₀²/4, P(11) = 80e-4 from ΔE_vac = 0.7764 − 0.6800 eV over 12 shell atoms; a₀ = 4.1616 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ag : MeasuredField 12 :=
  mkMeasuredField (23 / 10000 : ℝ) (-329 / 10000 : ℝ) (80 / 10000 : ℝ)

/-- mace-mpa-0-medium/Al (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 416e-4 from Δγ₁₀₀ = 0.9968 − 0.9150 J/m² on a₀²/2, P(9) = -49e-4 from Δγ₁₁₁ = 0.7840 − 0.7950 J/m² on √3a₀²/4, P(11) = 57e-4 from ΔE_vac = 0.6781 − 0.6100 eV over 12 shell atoms; a₀ = 4.0386 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Al : MeasuredField 12 :=
  mkMeasuredField (416 / 10000 : ℝ) (-49 / 10000 : ℝ) (57 / 10000 : ℝ)

/-- mace-mpa-0-medium/Au (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 99e-4 from Δγ₁₀₀ = 0.8793 − 0.8610 J/m² on a₀²/2, P(9) = -260e-4 from Δγ₁₁₁ = 0.6865 − 0.7420 J/m² on √3a₀²/4, P(11) = 59e-4 from ΔE_vac = 0.4705 − 0.4000 eV over 12 shell atoms; a₀ = 4.1665 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Au : MeasuredField 12 :=
  mkMeasuredField (99 / 10000 : ℝ) (-260 / 10000 : ℝ) (59 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ca (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -278e-4 from Δγ₁₀₀ = 0.4290 − 0.4580 J/m² on a₀²/2, P(9) = -544e-4 from Δγ₁₁₁ = 0.3956 − 0.4610 J/m² on √3a₀²/4, P(11) = -91e-4 from ΔE_vac = 1.0205 − 1.1300 eV over 12 shell atoms; a₀ = 5.5449 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ca : MeasuredField 12 :=
  mkMeasuredField (-278 / 10000 : ℝ) (-544 / 10000 : ℝ) (-91 / 10000 : ℝ)

/-- mace-mpa-0-medium/Cu (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -209e-4 from Δγ₁₀₀ = 1.4176 − 1.4680 J/m² on a₀²/2, P(9) = -306e-4 from Δγ₁₁₁ = 1.2284 − 1.3140 J/m² on √3a₀²/4, P(11) = -2e-4 from ΔE_vac = 1.0675 − 1.0700 eV over 12 shell atoms; a₀ = 3.6398 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Cu : MeasuredField 12 :=
  mkMeasuredField (-209 / 10000 : ℝ) (-306 / 10000 : ℝ) (-2 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ni (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 4190e-4 from Δγ₁₀₀ = 3.2907 − 2.2080 J/m² on a₀²/2, P(9) = 2296e-4 from Δγ₁₁₁ = 2.6092 − 1.9240 J/m² on √3a₀²/4, P(11) = 125e-4 from ΔE_vac = 1.5398 − 1.3900 eV over 12 shell atoms; a₀ = 3.5213 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ni : MeasuredField 12 :=
  mkMeasuredField (4190 / 10000 : ℝ) (2296 / 10000 : ℝ) (125 / 10000 : ℝ)

/-- mace-mpa-0-medium/Pd (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 346e-4 from Δγ₁₀₀ = 1.5966 − 1.5260 J/m² on a₀²/2, P(9) = 40e-4 from Δγ₁₁₁ = 1.3473 − 1.3380 J/m² on √3a₀²/4, P(11) = 42e-4 from ΔE_vac = 1.2100 − 1.1600 eV over 12 shell atoms; a₀ = 3.9596 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Pd : MeasuredField 12 :=
  mkMeasuredField (346 / 10000 : ℝ) (40 / 10000 : ℝ) (42 / 10000 : ℝ)

/-- mace-mpa-0-medium/Pt (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = 962e-4 from Δγ₁₀₀ = 2.0370 − 1.8420 J/m² on a₀²/2, P(9) = 814e-4 from Δγ₁₁₁ = 1.6695 − 1.4790 J/m² on √3a₀²/4, P(11) = 181e-4 from ΔE_vac = 0.8273 − 0.6100 eV over 12 shell atoms; a₀ = 3.9766 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Pt : MeasuredField 12 :=
  mkMeasuredField (962 / 10000 : ℝ) (814 / 10000 : ℝ) (181 / 10000 : ℝ)

/-- mace-mpa-0-medium/Sr (fcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(8) = -750e-4 from Δγ₁₀₀ = 0.2809 − 0.3470 J/m² on a₀²/2, P(9) = -780e-4 from Δγ₁₁₁ = 0.2626 − 0.3420 J/m² on √3a₀²/4, P(11) = -4e-4 from ΔE_vac = 0.9451 − 0.9500 eV over 12 shell atoms; a₀ = 6.0298 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Sr : MeasuredField 12 :=
  mkMeasuredField (-750 / 10000 : ℝ) (-780 / 10000 : ℝ) (-4 / 10000 : ℝ)

/-- chgnet/Cr (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -4794e-4 from Δγ₁₀₀ = 2.6927 − 3.6320 J/m² on a₀², P(6) = -2871e-4 from Δγ₁₁₀ = 2.4056 − 3.2010 J/m² on a₀²/√2, P(7) = -1764e-4 from ΔE_vac = 1.5983 − 3.0093 eV over 8 shell atoms; a₀ = 2.8597 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Cr : MeasuredField 8 :=
  mkMeasuredFieldBcc (-4794 / 10000 : ℝ) (-2871 / 10000 : ℝ) (-1764 / 10000 : ℝ)

/-- chgnet/Fe (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -4852e-4 from Δγ₁₀₀ = 1.5386 − 2.4990 J/m² on a₀², P(6) = -4596e-4 from Δγ₁₁₀ = 1.1605 − 2.4470 J/m² on a₀²/√2, P(7) = -1697e-4 from ΔE_vac = 0.8337 − 2.1914 eV over 8 shell atoms; a₀ = 2.8451 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Fe : MeasuredField 8 :=
  mkMeasuredFieldBcc (-4852 / 10000 : ℝ) (-4596 / 10000 : ℝ) (-1697 / 10000 : ℝ)

/-- chgnet/Mo (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -5409e-4 from Δγ₁₀₀ = 2.3185 − 3.1820 J/m² on a₀², P(6) = -3833e-4 from Δγ₁₁₀ = 1.9316 − 2.7970 J/m² on a₀²/√2, P(7) = -1408e-4 from ΔE_vac = 1.6688 − 2.7955 eV over 8 shell atoms; a₀ = 3.1680 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Mo : MeasuredField 8 :=
  mkMeasuredFieldBcc (-5409 / 10000 : ℝ) (-3833 / 10000 : ℝ) (-1408 / 10000 : ℝ)

/-- chgnet/Nb (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -2279e-4 from Δγ₁₀₀ = 1.9457 − 2.2750 J/m² on a₀², P(6) = -2501e-4 from Δγ₁₁₀ = 1.5629 − 2.0740 J/m² on a₀²/√2, P(7) = -1474e-4 from ΔE_vac = 1.4796 − 2.6589 eV over 8 shell atoms; a₀ = 3.3296 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Nb : MeasuredField 8 :=
  mkMeasuredFieldBcc (-2279 / 10000 : ℝ) (-2501 / 10000 : ℝ) (-1474 / 10000 : ℝ)

/-- chgnet/Ta (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -1065e-4 from Δγ₁₀₀ = 2.3165 − 2.4710 J/m² on a₀², P(6) = -2060e-4 from Δγ₁₁₀ = 1.9194 − 2.3420 J/m² on a₀²/√2, P(7) = -1507e-4 from ΔE_vac = 1.6704 − 2.8759 eV over 8 shell atoms; a₀ = 3.3237 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Ta : MeasuredField 8 :=
  mkMeasuredFieldBcc (-1065 / 10000 : ℝ) (-2060 / 10000 : ℝ) (-1507 / 10000 : ℝ)

/-- chgnet/V (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -378e-4 from Δγ₁₀₀ = 2.3134 − 2.3810 J/m² on a₀², P(6) = -1664e-4 from Δγ₁₁₀ = 2.0005 − 2.4210 J/m² on a₀²/√2, P(7) = -395e-4 from ΔE_vac = 1.7261 − 2.0422 eV over 8 shell atoms; a₀ = 2.9945 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_V : MeasuredField 8 :=
  mkMeasuredFieldBcc (-378 / 10000 : ℝ) (-1664 / 10000 : ℝ) (-395 / 10000 : ℝ)

/-- chgnet/W (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -6938e-4 from Δγ₁₀₀ = 2.8603 − 3.9540 J/m² on a₀², P(6) = -4120e-4 from Δγ₁₁₀ = 2.3094 − 3.2280 J/m² on a₀²/√2, P(7) = -1713e-4 from ΔE_vac = 1.8604 − 3.2310 eV over 8 shell atoms; a₀ = 3.1880 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_W : MeasuredField 8 :=
  mkMeasuredFieldBcc (-6938 / 10000 : ℝ) (-4120 / 10000 : ℝ) (-1713 / 10000 : ℝ)

/-- mace-mp-medium/Cr (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -2335e-4 from Δγ₁₀₀ = 3.1767 − 3.6320 J/m² on a₀², P(6) = 932e-4 from Δγ₁₁₀ = 3.4581 − 3.2010 J/m² on a₀²/√2, P(7) = -1952e-4 from ΔE_vac = 1.4476 − 3.0093 eV over 8 shell atoms; a₀ = 2.8664 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Cr : MeasuredField 8 :=
  mkMeasuredFieldBcc (-2335 / 10000 : ℝ) (932 / 10000 : ℝ) (-1952 / 10000 : ℝ)

/-- mace-mp-medium/Fe (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -2286e-4 from Δγ₁₀₀ = 2.0491 − 2.4990 J/m² on a₀², P(6) = -1547e-4 from Δγ₁₁₀ = 2.0164 − 2.4470 J/m² on a₀²/√2, P(7) = -945e-4 from ΔE_vac = 1.4357 − 2.1914 eV over 8 shell atoms; a₀ = 2.8534 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Fe : MeasuredField 8 :=
  mkMeasuredFieldBcc (-2286 / 10000 : ℝ) (-1547 / 10000 : ℝ) (-945 / 10000 : ℝ)

/-- mace-mp-medium/Mo (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -4228e-4 from Δγ₁₀₀ = 2.5080 − 3.1820 J/m² on a₀², P(6) = -2039e-4 from Δγ₁₁₀ = 2.3374 − 2.7970 J/m² on a₀²/√2, P(7) = -684e-4 from ΔE_vac = 2.2484 − 2.7955 eV over 8 shell atoms; a₀ = 3.1702 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Mo : MeasuredField 8 :=
  mkMeasuredFieldBcc (-4228 / 10000 : ℝ) (-2039 / 10000 : ℝ) (-684 / 10000 : ℝ)

/-- mace-mp-medium/Nb (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 1838e-4 from Δγ₁₀₀ = 2.5433 − 2.2750 J/m² on a₀², P(6) = 1896e-4 from Δγ₁₁₀ = 2.4654 − 2.0740 J/m² on a₀²/√2, P(7) = -535e-4 from ΔE_vac = 2.2306 − 2.6589 eV over 8 shell atoms; a₀ = 3.3134 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Nb : MeasuredField 8 :=
  mkMeasuredFieldBcc (1838 / 10000 : ℝ) (1896 / 10000 : ℝ) (-535 / 10000 : ℝ)

/-- mace-mp-medium/Ta (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -279e-4 from Δγ₁₀₀ = 2.4303 − 2.4710 J/m² on a₀², P(6) = -855e-4 from Δγ₁₁₀ = 2.1656 − 2.3420 J/m² on a₀²/√2, P(7) = -299e-4 from ΔE_vac = 2.6370 − 2.8759 eV over 8 shell atoms; a₀ = 3.3139 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Ta : MeasuredField 8 :=
  mkMeasuredFieldBcc (-279 / 10000 : ℝ) (-855 / 10000 : ℝ) (-299 / 10000 : ℝ)

/-- mace-mp-medium/V (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 1621e-4 from Δγ₁₀₀ = 2.6698 − 2.3810 J/m² on a₀², P(6) = 578e-4 from Δγ₁₁₀ = 2.5667 − 2.4210 J/m² on a₀²/√2, P(7) = 801e-4 from ΔE_vac = 2.6834 − 2.0422 eV over 8 shell atoms; a₀ = 2.9991 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_V : MeasuredField 8 :=
  mkMeasuredFieldBcc (1621 / 10000 : ℝ) (578 / 10000 : ℝ) (801 / 10000 : ℝ)

/-- mace-mp-medium/W (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -3585e-4 from Δγ₁₀₀ = 3.3890 − 3.9540 J/m² on a₀², P(6) = 480e-4 from Δγ₁₁₀ = 3.3350 − 3.2280 J/m² on a₀²/√2, P(7) = -732e-4 from ΔE_vac = 2.6456 − 3.2310 eV over 8 shell atoms; a₀ = 3.1885 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_W : MeasuredField 8 :=
  mkMeasuredFieldBcc (-3585 / 10000 : ℝ) (480 / 10000 : ℝ) (-732 / 10000 : ℝ)

/-- mace-mp-small/Cr (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -2466e-4 from Δγ₁₀₀ = 3.1500 − 3.6320 J/m² on a₀², P(6) = 236e-4 from Δγ₁₁₀ = 3.2662 − 3.2010 J/m² on a₀²/√2, P(7) = -451e-4 from ΔE_vac = 2.6485 − 3.0093 eV over 8 shell atoms; a₀ = 2.8630 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Cr : MeasuredField 8 :=
  mkMeasuredFieldBcc (-2466 / 10000 : ℝ) (236 / 10000 : ℝ) (-451 / 10000 : ℝ)

/-- mace-mp-small/Fe (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 658e-4 from Δγ₁₀₀ = 2.6278 − 2.4990 J/m² on a₀², P(6) = 539e-4 from Δγ₁₁₀ = 2.5963 − 2.4470 J/m² on a₀²/√2, P(7) = -721e-4 from ΔE_vac = 1.6142 − 2.1914 eV over 8 shell atoms; a₀ = 2.8609 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Fe : MeasuredField 8 :=
  mkMeasuredFieldBcc (658 / 10000 : ℝ) (539 / 10000 : ℝ) (-721 / 10000 : ℝ)

/-- mace-mp-small/Mo (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 28e-4 from Δγ₁₀₀ = 3.1866 − 3.1820 J/m² on a₀², P(6) = -989e-4 from Δγ₁₁₀ = 2.5723 − 2.7970 J/m² on a₀²/√2, P(7) = 723e-4 from ΔE_vac = 3.3737 − 2.7955 eV over 8 shell atoms; a₀ = 3.1569 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Mo : MeasuredField 8 :=
  mkMeasuredFieldBcc (28 / 10000 : ℝ) (-989 / 10000 : ℝ) (723 / 10000 : ℝ)

/-- mace-mp-small/Nb (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 666e-4 from Δγ₁₀₀ = 2.3717 − 2.2750 J/m² on a₀², P(6) = 732e-4 from Δγ₁₁₀ = 2.2244 − 2.0740 J/m² on a₀²/√2, P(7) = 310e-4 from ΔE_vac = 2.9070 − 2.6589 eV over 8 shell atoms; a₀ = 3.3215 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Nb : MeasuredField 8 :=
  mkMeasuredFieldBcc (666 / 10000 : ℝ) (732 / 10000 : ℝ) (310 / 10000 : ℝ)

/-- mace-mp-small/Ta (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 3788e-4 from Δγ₁₀₀ = 3.0214 − 2.4710 J/m² on a₀², P(6) = 1768e-4 from Δγ₁₁₀ = 2.7053 − 2.3420 J/m² on a₀²/√2, P(7) = 561e-4 from ΔE_vac = 3.3245 − 2.8759 eV over 8 shell atoms; a₀ = 3.3204 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Ta : MeasuredField 8 :=
  mkMeasuredFieldBcc (3788 / 10000 : ℝ) (1768 / 10000 : ℝ) (561 / 10000 : ℝ)

/-- mace-mp-small/V (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 5401e-4 from Δγ₁₀₀ = 3.3575 − 2.3810 J/m² on a₀², P(6) = 3072e-4 from Δγ₁₁₀ = 3.2065 − 2.4210 J/m² on a₀²/√2, P(7) = 404e-4 from ΔE_vac = 2.3657 − 2.0422 eV over 8 shell atoms; a₀ = 2.9769 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_V : MeasuredField 8 :=
  mkMeasuredFieldBcc (5401 / 10000 : ℝ) (3072 / 10000 : ℝ) (404 / 10000 : ℝ)

/-- mace-mp-small/W (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 5643e-4 from Δγ₁₀₀ = 4.8418 − 3.9540 J/m² on a₀², P(6) = 2429e-4 from Δγ₁₁₀ = 3.7684 − 3.2280 J/m² on a₀²/√2, P(7) = 8e-4 from ΔE_vac = 3.2375 − 3.2310 eV over 8 shell atoms; a₀ = 3.1911 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_W : MeasuredField 8 :=
  mkMeasuredFieldBcc (5643 / 10000 : ℝ) (2429 / 10000 : ℝ) (8 / 10000 : ℝ)

/-- mace-mpa-0-medium/Cr (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -954e-4 from Δγ₁₀₀ = 3.4459 − 3.6320 J/m² on a₀², P(6) = -466e-4 from Δγ₁₁₀ = 3.0724 − 3.2010 J/m² on a₀²/√2, P(7) = 233e-4 from ΔE_vac = 3.1957 − 3.0093 eV over 8 shell atoms; a₀ = 2.8651 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Cr : MeasuredField 8 :=
  mkMeasuredFieldBcc (-954 / 10000 : ℝ) (-466 / 10000 : ℝ) (233 / 10000 : ℝ)

/-- mace-mpa-0-medium/Fe (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -2e-4 from Δγ₁₀₀ = 2.4986 − 2.4990 J/m² on a₀², P(6) = -437e-4 from Δγ₁₁₀ = 2.3273 − 2.4470 J/m² on a₀²/√2, P(7) = 23e-4 from ΔE_vac = 2.2095 − 2.1914 eV over 8 shell atoms; a₀ = 2.8767 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Fe : MeasuredField 8 :=
  mkMeasuredFieldBcc (-2 / 10000 : ℝ) (-437 / 10000 : ℝ) (23 / 10000 : ℝ)

/-- mace-mpa-0-medium/Mo (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 289e-4 from Δγ₁₀₀ = 3.2287 − 3.1820 J/m² on a₀², P(6) = -180e-4 from Δγ₁₁₀ = 2.7559 − 2.7970 J/m² on a₀²/√2, P(7) = 162e-4 from ΔE_vac = 2.9254 − 2.7955 eV over 8 shell atoms; a₀ = 3.1512 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Mo : MeasuredField 8 :=
  mkMeasuredFieldBcc (289 / 10000 : ℝ) (-180 / 10000 : ℝ) (162 / 10000 : ℝ)

/-- mace-mpa-0-medium/Nb (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -627e-4 from Δγ₁₀₀ = 2.1838 − 2.2750 J/m² on a₀², P(6) = -95e-4 from Δγ₁₁₀ = 2.0545 − 2.0740 J/m² on a₀²/√2, P(7) = -56e-4 from ΔE_vac = 2.6140 − 2.6589 eV over 8 shell atoms; a₀ = 3.3170 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Nb : MeasuredField 8 :=
  mkMeasuredFieldBcc (-627 / 10000 : ℝ) (-95 / 10000 : ℝ) (-56 / 10000 : ℝ)

/-- mace-mpa-0-medium/Ta (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = -164e-4 from Δγ₁₀₀ = 2.4472 − 2.4710 J/m² on a₀², P(6) = -656e-4 from Δγ₁₁₀ = 2.2071 − 2.3420 J/m² on a₀²/√2, P(7) = -143e-4 from ΔE_vac = 2.7616 − 2.8759 eV over 8 shell atoms; a₀ = 3.3187 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Ta : MeasuredField 8 :=
  mkMeasuredFieldBcc (-164 / 10000 : ℝ) (-656 / 10000 : ℝ) (-143 / 10000 : ℝ)

/-- mace-mpa-0-medium/V (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 2020e-4 from Δγ₁₀₀ = 2.7455 − 2.3810 J/m² on a₀², P(6) = 307e-4 from Δγ₁₁₀ = 2.4994 − 2.4210 J/m² on a₀²/√2, P(7) = 856e-4 from ΔE_vac = 2.7268 − 2.0422 eV over 8 shell atoms; a₀ = 2.9794 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_V : MeasuredField 8 :=
  mkMeasuredFieldBcc (2020 / 10000 : ℝ) (307 / 10000 : ℝ) (856 / 10000 : ℝ)

/-- mace-mpa-0-medium/W (bcc) measured field, tier 1 (eV/atom, ×1e-4 exact): P(4) = 691e-4 from Δγ₁₀₀ = 4.0639 − 3.9540 J/m² on a₀², P(6) = 163e-4 from Δγ₁₁₀ = 3.2646 − 3.2280 J/m² on a₀²/√2, P(7) = 216e-4 from ΔE_vac = 3.4040 − 3.2310 eV over 8 shell atoms; a₀ = 3.1748 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_W : MeasuredField 8 :=
  mkMeasuredFieldBcc (691 / 10000 : ℝ) (163 / 10000 : ℝ) (216 / 10000 : ℝ)

/-- chgnet/Si (diamond) measured field, tier 1 (eV/atom, ×1e-4 exact): P(3) = -6906e-4 from ΔE_vac = 0.8676 − 3.6300 eV over 4 shell atoms; a₀ = 5.4671 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_chgnet_Si : MeasuredField 4 :=
  mkMeasuredFieldDiamond (-6906 / 10000 : ℝ)

/-- mace-mp-medium/Si (diamond) measured field, tier 1 (eV/atom, ×1e-4 exact): P(3) = -4451e-4 from ΔE_vac = 1.8494 − 3.6300 eV over 4 shell atoms; a₀ = 5.4556 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_medium_Si : MeasuredField 4 :=
  mkMeasuredFieldDiamond (-4451 / 10000 : ℝ)

/-- mace-mp-small/Si (diamond) measured field, tier 1 (eV/atom, ×1e-4 exact): P(3) = -3973e-4 from ΔE_vac = 2.0408 − 3.6300 eV over 4 shell atoms; a₀ = 5.4646 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mp_small_Si : MeasuredField 4 :=
  mkMeasuredFieldDiamond (-3973 / 10000 : ℝ)

/-- mace-mpa-0-medium/Si (diamond) measured field, tier 1 (eV/atom, ×1e-4 exact): P(3) = -2778e-4 from ΔE_vac = 2.5189 − 3.6300 eV over 4 shell atoms; a₀ = 5.4674 Å (model-relaxed). Closure, bulk-invariance, family-transfer, and ranking-recovery laws apply unconditionally. -/
noncomputable def mfield_mace_mpa_0_medium_Si : MeasuredField 4 :=
  mkMeasuredFieldDiamond (-2778 / 10000 : ℝ)

/-! ## Tier 2: anchored softening fields (monotone-softening cells) -/

/-- chgnet/Ag (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Ag` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Ag : ErrorField 12 :=
  mkAnchoredField (-1359 / 10000 : ℝ) (-1355 / 10000 : ℝ) (-156 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Al (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Al` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Al : ErrorField 12 :=
  mkAnchoredField (-2230 / 10000 : ℝ) (-1862 / 10000 : ℝ) (-394 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Au (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Au` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Au : ErrorField 12 :=
  mkAnchoredField (-2372 / 10000 : ℝ) (-1819 / 10000 : ℝ) (-83 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Cu (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Cu` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Cu : ErrorField 12 :=
  mkAnchoredField (-1837 / 10000 : ℝ) (-1690 / 10000 : ℝ) (-298 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Ni (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Ni` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Ni : ErrorField 12 :=
  mkAnchoredField (-980 / 10000 : ℝ) (-673 / 10000 : ℝ) (-136 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Pd (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Pd` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_chgnet_Pd : ErrorField 12 :=
  mkAnchoredField (-2063 / 10000 : ℝ) (-1612 / 10000 : ℝ) (-245 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Ni (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Ni` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Ni : ErrorField 12 :=
  mkAnchoredField (-1052 / 10000 : ℝ) (-310 / 10000 : ℝ) (-229 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Pt (fcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Pt` (`mkAnchoredField_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Pt : ErrorField 12 :=
  mkAnchoredField (-1075 / 10000 : ℝ) (-876 / 10000 : ℝ) (-142 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Cr (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Cr` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_chgnet_Cr : ErrorField 8 :=
  mkAnchoredFieldBcc (-4794 / 10000 : ℝ) (-2871 / 10000 : ℝ) (-1764 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Fe (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Fe` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_chgnet_Fe : ErrorField 8 :=
  mkAnchoredFieldBcc (-4852 / 10000 : ℝ) (-4596 / 10000 : ℝ) (-1697 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Mo (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Mo` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_chgnet_Mo : ErrorField 8 :=
  mkAnchoredFieldBcc (-5409 / 10000 : ℝ) (-3833 / 10000 : ℝ) (-1408 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/W (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_W` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_chgnet_W : ErrorField 8 :=
  mkAnchoredFieldBcc (-6938 / 10000 : ℝ) (-4120 / 10000 : ℝ) (-1713 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Fe (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Fe` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Fe : ErrorField 8 :=
  mkAnchoredFieldBcc (-2286 / 10000 : ℝ) (-1547 / 10000 : ℝ) (-945 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mp-medium/Mo (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Mo` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Mo : ErrorField 8 :=
  mkAnchoredFieldBcc (-4228 / 10000 : ℝ) (-2039 / 10000 : ℝ) (-684 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- mace-mpa-0-medium/Nb (bcc) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mpa_0_medium_Nb` (`mkAnchoredFieldBcc_toMeasuredField`). -/
noncomputable def field_mace_mpa_0_medium_Nb : ErrorField 8 :=
  mkAnchoredFieldBcc (-627 / 10000 : ℝ) (-95 / 10000 : ℝ) (-56 / 10000 : ℝ)
    (by norm_num) (by norm_num) (by norm_num)

/-- chgnet/Si (diamond) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_chgnet_Si` (`mkAnchoredFieldDiamond_toMeasuredField`). -/
noncomputable def field_chgnet_Si : ErrorField 4 :=
  mkAnchoredFieldDiamond (-6906 / 10000 : ℝ)
    (by norm_num)

/-- mace-mp-medium/Si (diamond) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_medium_Si` (`mkAnchoredFieldDiamond_toMeasuredField`). -/
noncomputable def field_mace_mp_medium_Si : ErrorField 4 :=
  mkAnchoredFieldDiamond (-4451 / 10000 : ℝ)
    (by norm_num)

/-- mace-mp-small/Si (diamond) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mp_small_Si` (`mkAnchoredFieldDiamond_toMeasuredField`). -/
noncomputable def field_mace_mp_small_Si : ErrorField 4 :=
  mkAnchoredFieldDiamond (-3973 / 10000 : ℝ)
    (by norm_num)

/-- mace-mpa-0-medium/Si (diamond) anchored softening field, tier 2: monotone softening holds on the measured anchors, so the directional laws of `Theory.BarrierArrhenius` (barrier underestimation, mobility overestimation) also apply. Forgets to `mfield_mace_mpa_0_medium_Si` (`mkAnchoredFieldDiamond_toMeasuredField`). -/
noncomputable def field_mace_mpa_0_medium_Si : ErrorField 4 :=
  mkAnchoredFieldDiamond (-2778 / 10000 : ℝ)
    (by norm_num)

/-! ## Tier-2 refusal certificates (outside the softening domain) -/

/-- chgnet/Ca (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-926, -1363, -316)e-4 eV/atom violate monotone softening — P(8) = -926e-4 > P(9) = -1363e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Ca` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Ca :
    ¬ scaledAnchorsValid (-926) (-1363) (-316) := by decide

/-- chgnet/Pt (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-2766, -1683, 156)e-4 eV/atom violate monotone softening — P(11) = 156e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Pt` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Pt :
    ¬ scaledAnchorsValid (-2766) (-1683) 156 := by decide

/-- chgnet/Sr (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-1386, -1646, -322)e-4 eV/atom violate monotone softening — P(8) = -1386e-4 > P(9) = -1646e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Sr` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Sr :
    ¬ scaledAnchorsValid (-1386) (-1646) (-322) := by decide

/-- mace-mp-medium/Ag (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-22, -356, 0)e-4 eV/atom violate monotone softening — P(8) = -22e-4 > P(9) = -356e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Ag :
    ¬ scaledAnchorsValid (-22) (-356) 0 := by decide

/-- mace-mp-medium/Al (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-423, -645, -107)e-4 eV/atom violate monotone softening — P(8) = -423e-4 > P(9) = -645e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Al :
    ¬ scaledAnchorsValid (-423) (-645) (-107) := by decide

/-- mace-mp-medium/Au (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (21, -265, 33)e-4 eV/atom violate monotone softening — P(8) = 21e-4 > P(9) = -265e-4 (mono); P(11) = 33e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Au :
    ¬ scaledAnchorsValid 21 (-265) 33 := by decide

/-- mace-mp-medium/Ca (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-218, -825, -150)e-4 eV/atom violate monotone softening — P(8) = -218e-4 > P(9) = -825e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Ca :
    ¬ scaledAnchorsValid (-218) (-825) (-150) := by decide

/-- mace-mp-medium/Cu (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (131, -37, -21)e-4 eV/atom violate monotone softening — P(8) = 131e-4 > P(9) = -37e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Cu :
    ¬ scaledAnchorsValid 131 (-37) (-21) := by decide

/-- mace-mp-medium/Pd (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-612, -148, 18)e-4 eV/atom violate monotone softening — P(11) = 18e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Pd :
    ¬ scaledAnchorsValid (-612) (-148) 18 := by decide

/-- mace-mp-medium/Sr (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-690, -1151, -238)e-4 eV/atom violate monotone softening — P(8) = -690e-4 > P(9) = -1151e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Sr :
    ¬ scaledAnchorsValid (-690) (-1151) (-238) := by decide

/-- mace-mp-small/Ag (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (451, -389, -44)e-4 eV/atom violate monotone softening — P(8) = 451e-4 > P(9) = -389e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ag :
    ¬ scaledAnchorsValid 451 (-389) (-44) := by decide

/-- mace-mp-small/Al (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-496, -667, -21)e-4 eV/atom violate monotone softening — P(8) = -496e-4 > P(9) = -667e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Al :
    ¬ scaledAnchorsValid (-496) (-667) (-21) := by decide

/-- mace-mp-small/Au (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (569, 54, 30)e-4 eV/atom violate monotone softening — P(8) = 569e-4 > P(9) = 54e-4 (mono); P(9) = 54e-4 > P(11) = 30e-4 (mono); P(11) = 30e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Au :
    ¬ scaledAnchorsValid 569 54 30 := by decide

/-- mace-mp-small/Ca (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (196, -555, -96)e-4 eV/atom violate monotone softening — P(8) = 196e-4 > P(9) = -555e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ca :
    ¬ scaledAnchorsValid 196 (-555) (-96) := by decide

/-- mace-mp-small/Cu (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (335, 9, -35)e-4 eV/atom violate monotone softening — P(8) = 335e-4 > P(9) = 9e-4 (mono); P(9) = 9e-4 > P(11) = -35e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Cu :
    ¬ scaledAnchorsValid 335 9 (-35) := by decide

/-- mace-mp-small/Ni (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (1473, 934, -310)e-4 eV/atom violate monotone softening — P(8) = 1473e-4 > P(9) = 934e-4 (mono); P(9) = 934e-4 > P(11) = -310e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ni` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ni :
    ¬ scaledAnchorsValid 1473 934 (-310) := by decide

/-- mace-mp-small/Pd (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (671, 322, 68)e-4 eV/atom violate monotone softening — P(8) = 671e-4 > P(9) = 322e-4 (mono); P(9) = 322e-4 > P(11) = 68e-4 (mono); P(11) = 68e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Pd :
    ¬ scaledAnchorsValid 671 322 68 := by decide

/-- mace-mp-small/Pt (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (1098, 901, 236)e-4 eV/atom violate monotone softening — P(8) = 1098e-4 > P(9) = 901e-4 (mono); P(9) = 901e-4 > P(11) = 236e-4 (mono); P(11) = 236e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Pt` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Pt :
    ¬ scaledAnchorsValid 1098 901 236 := by decide

/-- mace-mp-small/Sr (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-620, -1031, -139)e-4 eV/atom violate monotone softening — P(8) = -620e-4 > P(9) = -1031e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Sr :
    ¬ scaledAnchorsValid (-620) (-1031) (-139) := by decide

/-- mace-mpa-0-medium/Ag (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (23, -329, 80)e-4 eV/atom violate monotone softening — P(8) = 23e-4 > P(9) = -329e-4 (mono); P(11) = 80e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ag` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ag :
    ¬ scaledAnchorsValid 23 (-329) 80 := by decide

/-- mace-mpa-0-medium/Al (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (416, -49, 57)e-4 eV/atom violate monotone softening — P(8) = 416e-4 > P(9) = -49e-4 (mono); P(11) = 57e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Al` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Al :
    ¬ scaledAnchorsValid 416 (-49) 57 := by decide

/-- mace-mpa-0-medium/Au (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (99, -260, 59)e-4 eV/atom violate monotone softening — P(8) = 99e-4 > P(9) = -260e-4 (mono); P(11) = 59e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Au` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Au :
    ¬ scaledAnchorsValid 99 (-260) 59 := by decide

/-- mace-mpa-0-medium/Ca (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-278, -544, -91)e-4 eV/atom violate monotone softening — P(8) = -278e-4 > P(9) = -544e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ca` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ca :
    ¬ scaledAnchorsValid (-278) (-544) (-91) := by decide

/-- mace-mpa-0-medium/Cu (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-209, -306, -2)e-4 eV/atom violate monotone softening — P(8) = -209e-4 > P(9) = -306e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Cu` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Cu :
    ¬ scaledAnchorsValid (-209) (-306) (-2) := by decide

/-- mace-mpa-0-medium/Ni (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (4190, 2296, 125)e-4 eV/atom violate monotone softening — P(8) = 4190e-4 > P(9) = 2296e-4 (mono); P(9) = 2296e-4 > P(11) = 125e-4 (mono); P(11) = 125e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ni` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ni :
    ¬ scaledAnchorsValid 4190 2296 125 := by decide

/-- mace-mpa-0-medium/Pd (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (346, 40, 42)e-4 eV/atom violate monotone softening — P(8) = 346e-4 > P(9) = 40e-4 (mono); P(11) = 42e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Pd` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Pd :
    ¬ scaledAnchorsValid 346 40 42 := by decide

/-- mace-mpa-0-medium/Pt (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (962, 814, 181)e-4 eV/atom violate monotone softening — P(8) = 962e-4 > P(9) = 814e-4 (mono); P(9) = 814e-4 > P(11) = 181e-4 (mono); P(11) = 181e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Pt` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Pt :
    ¬ scaledAnchorsValid 962 814 181 := by decide

/-- mace-mpa-0-medium/Sr (fcc) tier-2 REFUSAL: measured anchors (P(8), P(9), P(11)) = (-750, -780, -4)e-4 eV/atom violate monotone softening — P(8) = -750e-4 > P(9) = -780e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Sr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Sr :
    ¬ scaledAnchorsValid (-750) (-780) (-4) := by decide

/-- chgnet/Nb (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-2279, -2501, -1474)e-4 eV/atom violate monotone softening — P(4) = -2279e-4 > P(6) = -2501e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Nb` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Nb :
    ¬ scaledAnchorsBccValid (-2279) (-2501) (-1474) := by decide

/-- chgnet/Ta (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-1065, -2060, -1507)e-4 eV/atom violate monotone softening — P(4) = -1065e-4 > P(6) = -2060e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_Ta` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_Ta :
    ¬ scaledAnchorsBccValid (-1065) (-2060) (-1507) := by decide

/-- chgnet/V (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-378, -1664, -395)e-4 eV/atom violate monotone softening — P(4) = -378e-4 > P(6) = -1664e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_chgnet_V` still carries the correction and ranking laws. -/
theorem field_refused_chgnet_V :
    ¬ scaledAnchorsBccValid (-378) (-1664) (-395) := by decide

/-- mace-mp-medium/Cr (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-2335, 932, -1952)e-4 eV/atom violate monotone softening — P(6) = 932e-4 > P(7) = -1952e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Cr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Cr :
    ¬ scaledAnchorsBccValid (-2335) 932 (-1952) := by decide

/-- mace-mp-medium/Nb (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (1838, 1896, -535)e-4 eV/atom violate monotone softening — P(6) = 1896e-4 > P(7) = -535e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Nb` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Nb :
    ¬ scaledAnchorsBccValid 1838 1896 (-535) := by decide

/-- mace-mp-medium/Ta (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-279, -855, -299)e-4 eV/atom violate monotone softening — P(4) = -279e-4 > P(6) = -855e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_Ta` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_Ta :
    ¬ scaledAnchorsBccValid (-279) (-855) (-299) := by decide

/-- mace-mp-medium/V (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (1621, 578, 801)e-4 eV/atom violate monotone softening — P(4) = 1621e-4 > P(6) = 578e-4 (mono); P(7) = 801e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_V` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_V :
    ¬ scaledAnchorsBccValid 1621 578 801 := by decide

/-- mace-mp-medium/W (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-3585, 480, -732)e-4 eV/atom violate monotone softening — P(6) = 480e-4 > P(7) = -732e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_medium_W` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_medium_W :
    ¬ scaledAnchorsBccValid (-3585) 480 (-732) := by decide

/-- mace-mp-small/Cr (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-2466, 236, -451)e-4 eV/atom violate monotone softening — P(6) = 236e-4 > P(7) = -451e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Cr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Cr :
    ¬ scaledAnchorsBccValid (-2466) 236 (-451) := by decide

/-- mace-mp-small/Fe (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (658, 539, -721)e-4 eV/atom violate monotone softening — P(4) = 658e-4 > P(6) = 539e-4 (mono); P(6) = 539e-4 > P(7) = -721e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Fe` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Fe :
    ¬ scaledAnchorsBccValid 658 539 (-721) := by decide

/-- mace-mp-small/Mo (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (28, -989, 723)e-4 eV/atom violate monotone softening — P(4) = 28e-4 > P(6) = -989e-4 (mono); P(7) = 723e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Mo` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Mo :
    ¬ scaledAnchorsBccValid 28 (-989) 723 := by decide

/-- mace-mp-small/Nb (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (666, 732, 310)e-4 eV/atom violate monotone softening — P(6) = 732e-4 > P(7) = 310e-4 (mono); P(7) = 310e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Nb` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Nb :
    ¬ scaledAnchorsBccValid 666 732 310 := by decide

/-- mace-mp-small/Ta (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (3788, 1768, 561)e-4 eV/atom violate monotone softening — P(4) = 3788e-4 > P(6) = 1768e-4 (mono); P(6) = 1768e-4 > P(7) = 561e-4 (mono); P(7) = 561e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_Ta` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_Ta :
    ¬ scaledAnchorsBccValid 3788 1768 561 := by decide

/-- mace-mp-small/V (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (5401, 3072, 404)e-4 eV/atom violate monotone softening — P(4) = 5401e-4 > P(6) = 3072e-4 (mono); P(6) = 3072e-4 > P(7) = 404e-4 (mono); P(7) = 404e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_V` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_V :
    ¬ scaledAnchorsBccValid 5401 3072 404 := by decide

/-- mace-mp-small/W (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (5643, 2429, 8)e-4 eV/atom violate monotone softening — P(4) = 5643e-4 > P(6) = 2429e-4 (mono); P(6) = 2429e-4 > P(7) = 8e-4 (mono); P(7) = 8e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mp_small_W` still carries the correction and ranking laws. -/
theorem field_refused_mace_mp_small_W :
    ¬ scaledAnchorsBccValid 5643 2429 8 := by decide

/-- mace-mpa-0-medium/Cr (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-954, -466, 233)e-4 eV/atom violate monotone softening — P(7) = 233e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Cr` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Cr :
    ¬ scaledAnchorsBccValid (-954) (-466) 233 := by decide

/-- mace-mpa-0-medium/Fe (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-2, -437, 23)e-4 eV/atom violate monotone softening — P(4) = -2e-4 > P(6) = -437e-4 (mono); P(7) = 23e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Fe` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Fe :
    ¬ scaledAnchorsBccValid (-2) (-437) 23 := by decide

/-- mace-mpa-0-medium/Mo (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (289, -180, 162)e-4 eV/atom violate monotone softening — P(4) = 289e-4 > P(6) = -180e-4 (mono); P(7) = 162e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Mo` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Mo :
    ¬ scaledAnchorsBccValid 289 (-180) 162 := by decide

/-- mace-mpa-0-medium/Ta (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (-164, -656, -143)e-4 eV/atom violate monotone softening — P(4) = -164e-4 > P(6) = -656e-4 (mono). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_Ta` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_Ta :
    ¬ scaledAnchorsBccValid (-164) (-656) (-143) := by decide

/-- mace-mpa-0-medium/V (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (2020, 307, 856)e-4 eV/atom violate monotone softening — P(4) = 2020e-4 > P(6) = 307e-4 (mono); P(7) = 856e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_V` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_V :
    ¬ scaledAnchorsBccValid 2020 307 856 := by decide

/-- mace-mpa-0-medium/W (bcc) tier-2 REFUSAL: measured anchors (P(4), P(6), P(7)) = (691, 163, 216)e-4 eV/atom violate monotone softening — P(4) = 691e-4 > P(6) = 163e-4 (mono); P(7) = 216e-4 > 0 (softening). The directional softening laws do not apply to this cell (noise floor or stiffening regime); its measured tier `mfield_mace_mpa_0_medium_W` still carries the correction and ranking laws. -/
theorem field_refused_mace_mpa_0_medium_W :
    ¬ scaledAnchorsBccValid 691 163 216 := by decide

/-- Every fcc sweep cell is accounted for: instances + refusals = cells. -/
theorem fcc_cells_accounted : 8 + 28 = 36 := by
  decide

/-- Every bcc sweep cell is accounted for: instances + refusals = cells. -/
theorem bcc_cells_accounted : 7 + 21 = 28 := by
  decide

/-- Every diamond sweep cell is accounted for: instances + refusals = cells. -/
theorem diamond_cells_accounted : 4 + 0 = 4 := by
  decide

/-- Every rocksalt sweep cell is accounted for: instances + refusals = cells. -/
theorem rocksalt_cells_accounted : 0 + 0 = 0 := by
  decide

/-- Every sweep cell is accounted for: instances + refusals = cells. -/
theorem cells_accounted : 19 + 49 = 68 := by
  decide

end OpenDistillationFactory.Materials.DistillAtlas.EnvFieldInstances
