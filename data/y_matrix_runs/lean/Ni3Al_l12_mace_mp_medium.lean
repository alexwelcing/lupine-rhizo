/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni3Al/mace-mp-medium inputs sha256 d3d163a071df.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni3Al

/-- Ni3Al/mace-mp-medium a0 = 3.5556 Angstrom vs reference 3.5650 (E. Chen, A. Tamm, T. Wang, M. E. Epler, M. Asta, T. Frolov, 'Modeling antiphase boundary energies of Ni3Al-based alloys using automated density functional theory and machine learning', npj Comput. Mater. 8 (2022); LLNL-JRNL-825551 - VASP, PAW, GGA-PBE): |err| 0.0094 ≤ tol 0.1783 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni3Al_mace_mp_medium_a0 : 9 ≤ 178 := by decide

/-- Ni3Al/mace-mp-medium B0 = 181.6765 GPa vs reference 175.0000 (M. H. Yoo, Acta Metall. 35, 1559-1569 (1987); as tabulated in Ward et al., arXiv:1209.0619, Table 1): |err| 6.6765 ≤ tol 8.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni3Al_mace_mp_medium_B0 : 6676 ≤ 8750 := by decide

/-- Ni3Al/mace-mp-medium formation_enthalpy = -0.4764 eV/atom vs reference -0.4325 (Materials Project entry mp-2593 (PBE, GGA), formation energy as recorded in the Kim et al. Sci. Data 4, 170162 (2017) dataset): |err| 0.0439 EXCEEDS tol 0.0216 eV/atom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni3Al_mace_mp_medium_formation_enthalpy : 22 < 44 := by decide

end Lupine.CalcEvidence.Ni3Al
