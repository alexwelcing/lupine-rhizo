/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cr/mace-mp-medium inputs sha256 1eba31e484ba.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cr

/-- Cr/mace-mp-medium a0 = 2.8664 Angstrom vs reference 2.8620 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table I (GGA-PBE, magnetic Cr, 2-atom cell)): |err| 0.0044 ≤ tol 0.1431 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_mace_mp_medium_a0 : 4 ≤ 143 := by decide

/-- Cr/mace-mp-medium B0 = 230.3783 GPa vs reference 160.0000 (CRC Handbook of Chemistry and Physics (bulk modulus of the elements), as tabulated on the Wikipedia 'Elastic properties of the elements (data page)' (CRC and WebElements columns agree)): |err| 70.3783 EXCEEDS tol 8.0000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_medium_B0 : 8000 < 70378 := by decide

/-- Cr/mace-mp-medium B0_prime = 5.5746 dimensionless vs reference 4.9340 (D. A. Young, H. Cynn, P. Soderlind, A. Landa, J. Phys. Chem. Ref. Data 45, 043101 (2016) (LLNL-JRNL-686936) - Birch-Murnaghan fit of new Cr DAC data to 56 GPa): |err| 0.6406 EXCEEDS tol 0.2467 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_medium_B0_prime : 247 < 641 := by decide

/-- Cr/mace-mp-medium vacancy_formation_energy = 1.4476 eV vs reference 3.0093 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 1.5617 EXCEEDS tol 0.1505 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_medium_vacancy_formation_energy : 150 < 1562 := by decide

/-- Cr/mace-mp-medium gamma_100 = 3.1767 J/m^2 vs reference 3.6320 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4553 EXCEEDS tol 0.1816 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_medium_gamma_100 : 182 < 455 := by decide

/-- Cr/mace-mp-medium gamma_110 = 3.4581 J/m^2 vs reference 3.2010 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2571 EXCEEDS tol 0.1601 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_medium_gamma_110 : 160 < 257 := by decide

end Lupine.CalcEvidence.Cr
