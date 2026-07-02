/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cr/chgnet inputs sha256 d2854a1c49ec.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cr

/-- Cr/chgnet a0 = 2.8597 Angstrom vs reference 2.8620 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table I (GGA-PBE, magnetic Cr, 2-atom cell)): |err| 0.0023 ≤ tol 0.1431 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_chgnet_a0 : 2 ≤ 143 := by decide

/-- Cr/chgnet B0 = 234.2289 GPa vs reference 160.0000 (CRC Handbook of Chemistry and Physics (bulk modulus of the elements), as tabulated on the Wikipedia 'Elastic properties of the elements (data page)' (CRC and WebElements columns agree)): |err| 74.2289 EXCEEDS tol 8.0000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_chgnet_B0 : 8000 < 74229 := by decide

/-- Cr/chgnet B0_prime = 10.0288 dimensionless vs reference 4.9340 (D. A. Young, H. Cynn, P. Soderlind, A. Landa, J. Phys. Chem. Ref. Data 45, 043101 (2016) (LLNL-JRNL-686936) - Birch-Murnaghan fit of new Cr DAC data to 56 GPa): |err| 5.0948 EXCEEDS tol 0.2467 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_chgnet_B0_prime : 247 < 5095 := by decide

/-- Cr/chgnet vacancy_formation_energy = 1.5983 eV vs reference 3.0093 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 1.4110 EXCEEDS tol 0.1505 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_chgnet_vacancy_formation_energy : 150 < 1411 := by decide

/-- Cr/chgnet gamma_100 = 2.6927 J/m^2 vs reference 3.6320 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.9393 EXCEEDS tol 0.1816 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_chgnet_gamma_100 : 182 < 939 := by decide

/-- Cr/chgnet gamma_110 = 2.4056 J/m^2 vs reference 3.2010 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.7954 EXCEEDS tol 0.1601 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_chgnet_gamma_110 : 160 < 795 := by decide

end Lupine.CalcEvidence.Cr
