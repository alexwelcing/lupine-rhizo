/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NiAl/mace-mpa-0-medium inputs sha256 25feda5e2a22.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NiAl

/-- NiAl/mace-mpa-0-medium a0 = 2.8846 Angstrom vs reference 2.8800 (P. Villars, L. D. Calvert, W. D. Pearson, Pearson's Handbook of Crystallographic Data for Intermetallic Phases (ASM, 1985); as tabulated in L. Ward, A. Agrawal, K. M. Flores, W. Windl, arXiv:1209.0619, Table 1): |err| 0.0046 ≤ tol 0.1440 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NiAl_mace_mpa_0_medium_a0 : 5 ≤ 144 := by decide

/-- NiAl/mace-mpa-0-medium B0 = 170.5192 GPa vs reference 166.0000 (N. Rusovic and H. Warlimont, Phys. Status Solidi A 44, 609-619 (1977) - elastic constants of B2 NiAl; as tabulated in Ward et al., arXiv:1209.0619, Table 1): |err| 4.5192 ≤ tol 8.3000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NiAl_mace_mpa_0_medium_B0 : 4519 ≤ 8300 := by decide

/-- NiAl/mace-mpa-0-medium formation_enthalpy = -0.6593 eV/atom vs reference -0.6586 (Materials Project entry mp-1487 (PBE, GGA), formation energy as recorded in the Kim et al. Sci. Data 4, 170162 (2017) dataset): |err| 0.0007 ≤ tol 0.0329 eV/atom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NiAl_mace_mpa_0_medium_formation_enthalpy : 1 ≤ 33 := by decide

end Lupine.CalcEvidence.NiAl
