/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NiAl/mace-mp-small inputs sha256 d375954f61dc.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NiAl

/-- NiAl/mace-mp-small a0 = 2.8840 Angstrom vs reference 2.8800 (P. Villars, L. D. Calvert, W. D. Pearson, Pearson's Handbook of Crystallographic Data for Intermetallic Phases (ASM, 1985); as tabulated in L. Ward, A. Agrawal, K. M. Flores, W. Windl, arXiv:1209.0619, Table 1): |err| 0.0040 ≤ tol 0.1440 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NiAl_mace_mp_small_a0 : 4 ≤ 144 := by decide

/-- NiAl/mace-mp-small B0 = 176.2892 GPa vs reference 166.0000 (N. Rusovic and H. Warlimont, Phys. Status Solidi A 44, 609-619 (1977) - elastic constants of B2 NiAl; as tabulated in Ward et al., arXiv:1209.0619, Table 1): |err| 10.2892 EXCEEDS tol 8.3000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NiAl_mace_mp_small_B0 : 8300 < 10289 := by decide

/-- NiAl/mace-mp-small formation_enthalpy = -0.6902 eV/atom vs reference -0.6586 (Materials Project entry mp-1487 (PBE, GGA), formation energy as recorded in the Kim et al. Sci. Data 4, 170162 (2017) dataset): |err| 0.0316 ≤ tol 0.0329 eV/atom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NiAl_mace_mp_small_formation_enthalpy : 32 ≤ 33 := by decide

end Lupine.CalcEvidence.NiAl
