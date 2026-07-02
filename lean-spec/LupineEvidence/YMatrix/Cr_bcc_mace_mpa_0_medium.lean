/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cr/mace-mpa-0-medium inputs sha256 0b7a795b7b42.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cr

/-- Cr/mace-mpa-0-medium a0 = 2.8651 Angstrom vs reference 2.8620 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table I (GGA-PBE, magnetic Cr, 2-atom cell)): |err| 0.0031 ≤ tol 0.1431 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_mace_mpa_0_medium_a0 : 3 ≤ 143 := by decide

/-- Cr/mace-mpa-0-medium B0 = 205.4746 GPa vs reference 160.0000 (CRC Handbook of Chemistry and Physics (bulk modulus of the elements), as tabulated on the Wikipedia 'Elastic properties of the elements (data page)' (CRC and WebElements columns agree)): |err| 45.4746 EXCEEDS tol 8.0000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mpa_0_medium_B0 : 8000 < 45475 := by decide

/-- Cr/mace-mpa-0-medium B0_prime = 2.0274 dimensionless vs reference 4.9340 (D. A. Young, H. Cynn, P. Soderlind, A. Landa, J. Phys. Chem. Ref. Data 45, 043101 (2016) (LLNL-JRNL-686936) - Birch-Murnaghan fit of new Cr DAC data to 56 GPa): |err| 2.9066 EXCEEDS tol 0.2467 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mpa_0_medium_B0_prime : 247 < 2907 := by decide

/-- Cr/mace-mpa-0-medium vacancy_formation_energy = 3.1957 eV vs reference 3.0093 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.1864 EXCEEDS tol 0.1505 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mpa_0_medium_vacancy_formation_energy : 150 < 186 := by decide

/-- Cr/mace-mpa-0-medium gamma_100 = 3.4459 J/m^2 vs reference 3.6320 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1861 EXCEEDS tol 0.1816 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mpa_0_medium_gamma_100 : 182 < 186 := by decide

/-- Cr/mace-mpa-0-medium gamma_110 = 3.0724 J/m^2 vs reference 3.2010 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1286 ≤ tol 0.1601 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_mace_mpa_0_medium_gamma_110 : 129 ≤ 160 := by decide

end Lupine.CalcEvidence.Cr
