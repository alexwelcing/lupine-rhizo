/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni3Al/mace-mpa-0-medium inputs sha256 ab2ab9018206.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni3Al

/-- Ni3Al/mace-mpa-0-medium a0 = 3.5614 Angstrom vs reference 3.5650 (E. Chen, A. Tamm, T. Wang, M. E. Epler, M. Asta, T. Frolov, 'Modeling antiphase boundary energies of Ni3Al-based alloys using automated density functional theory and machine learning', npj Comput. Mater. 8 (2022); LLNL-JRNL-825551 - VASP, PAW, GGA-PBE): |err| 0.0036 ≤ tol 0.1783 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni3Al_mace_mpa_0_medium_a0 : 4 ≤ 178 := by decide

/-- Ni3Al/mace-mpa-0-medium B0 = 159.3829 GPa vs reference 175.0000 (M. H. Yoo, Acta Metall. 35, 1559-1569 (1987); as tabulated in Ward et al., arXiv:1209.0619, Table 1): |err| 15.6171 EXCEEDS tol 8.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni3Al_mace_mpa_0_medium_B0 : 8750 < 15617 := by decide

/-- Ni3Al/mace-mpa-0-medium formation_enthalpy = -0.4263 eV/atom vs reference -0.4325 (Materials Project entry mp-2593 (PBE, GGA), formation energy as recorded in the Kim et al. Sci. Data 4, 170162 (2017) dataset): |err| 0.0062 ≤ tol 0.0216 eV/atom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni3Al_mace_mpa_0_medium_formation_enthalpy : 6 ≤ 22 := by decide

end Lupine.CalcEvidence.Ni3Al
