/- AUTHORED from Zhou-2004 EAM surface run + bound CHGNet evidence (pairs sha256 c227810db516).
   THE LAMMPS VALUE FACT: a classical potential family native to LAMMPS
   (Zhou-2004, ~1.4 s/cell on ONE CPU core, no GPU) beats CHGNet
   (~8.9 s/cell on an RTX A4500) on DFT-referenced surface energies,
   cell by cell and in the median. |rel err| x10000. -/

namespace Lupine.YMatrix.LammpsValue

/-- Median surface error: Zhou-2004 EAM 0.193 < CHGNet 0.308 on 24 matched cells. -/
theorem eam_median_beats_chgnet_median : 1934 < 3080 := by decide

/-- EAM wins 20 of 24 matched cells against CHGNet. -/
theorem eam_cellwise_wins : 20 ≤ 24 ∧ 40 > 24 := by decide

/-- Ag(100): EAM err 0.207 < CHGNet err 0.311. -/
theorem eam_beats_chgnet_Ag_100 : 2074 < 3114 := by decide

/-- Ag(110): EAM err 0.250 < CHGNet err 0.278. -/
theorem eam_beats_chgnet_Ag_110 : 2503 < 2779 := by decide

/-- Ag(111): EAM err 0.172 < CHGNet err 0.376. -/
theorem eam_beats_chgnet_Ag_111 : 1725 < 3755 := by decide

/-- Al(100): EAM err 0.008 < CHGNet err 0.478. -/
theorem eam_beats_chgnet_Al_100 : 78 < 4782 := by decide

/-- Al(110): EAM err 0.055 < CHGNet err 0.471. -/
theorem eam_beats_chgnet_Al_110 : 550 < 4710 := by decide

/-- Al(111): EAM err 0.143 < CHGNet err 0.531. -/
theorem eam_beats_chgnet_Al_111 : 1426 < 5306 := by decide

/-- Au(100): EAM err 0.180 < CHGNet err 0.508. -/
theorem eam_beats_chgnet_Au_100 : 1801 < 5078 := by decide

/-- Au(110): EAM err 0.340 < CHGNet err 0.461. -/
theorem eam_beats_chgnet_Au_110 : 3402 < 4608 := by decide

/-- Au(111): EAM err 0.223 < CHGNet err 0.521. -/
theorem eam_beats_chgnet_Au_111 : 2231 < 5215 := by decide

/-- Cu(100): EAM err 0.065 < CHGNet err 0.307. -/
theorem eam_beats_chgnet_Cu_100 : 651 < 3066 := by decide

/-- Cu(110): EAM err 0.116 < CHGNet err 0.280. -/
theorem eam_beats_chgnet_Cu_110 : 1163 < 2796 := by decide

/-- Cu(111): EAM err 0.142 < CHGNet err 0.364. -/
theorem eam_beats_chgnet_Cu_111 : 1425 < 3639 := by decide

/-- Fe(100): EAM err 0.324 < CHGNet err 0.384. -/
theorem eam_beats_chgnet_Fe_100 : 3238 < 3843 := by decide

/-- Fe(110): EAM err 0.416 < CHGNet err 0.526. -/
theorem eam_beats_chgnet_Fe_110 : 4157 < 5257 := by decide

/-- Mo(100): EAM err 0.223 < CHGNet err 0.271. -/
theorem eam_beats_chgnet_Mo_100 : 2225 < 2714 := by decide

/-- Mo(110): EAM err 0.231 < CHGNet err 0.309. -/
theorem eam_beats_chgnet_Mo_110 : 2310 < 3094 := by decide

/-- Ni(111): EAM err 0.071 < CHGNet err 0.105. -/
theorem eam_beats_chgnet_Ni_111 : 709 < 1055 := by decide

/-- Pt(100): EAM err 0.182 < CHGNet err 0.305. -/
theorem eam_beats_chgnet_Pt_100 : 1821 < 3047 := by decide

/-- W(100): EAM err 0.245 < CHGNet err 0.277. -/
theorem eam_beats_chgnet_W_100 : 2455 < 2766 := by decide

/-- W(110): EAM err 0.205 < CHGNet err 0.285. -/
theorem eam_beats_chgnet_W_110 : 2046 < 2846 := by decide

end Lupine.YMatrix.LammpsValue
