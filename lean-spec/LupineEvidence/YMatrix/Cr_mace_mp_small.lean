/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cr/mace-mp-small inputs sha256 87ff493347ef.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cr

/-- Cr/mace-mp-small a0 = 2.8630 Angstrom vs reference 2.8620 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table I (GGA-PBE, magnetic Cr, 2-atom cell)): |err| 0.0010 ≤ tol 0.1431 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_mace_mp_small_a0 : 1 ≤ 143 := by decide

/-- Cr/mace-mp-small B0 = 250.9454 GPa vs reference 160.0000 (CRC Handbook of Chemistry and Physics (bulk modulus of the elements), as tabulated on the Wikipedia 'Elastic properties of the elements (data page)' (CRC and WebElements columns agree)): |err| 90.9454 EXCEEDS tol 8.0000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_small_B0 : 8000 < 90945 := by decide

/-- Cr/mace-mp-small B0_prime = 3.6202 dimensionless vs reference 4.9340 (D. A. Young, H. Cynn, P. Soderlind, A. Landa, J. Phys. Chem. Ref. Data 45, 043101 (2016) (LLNL-JRNL-686936) - Birch-Murnaghan fit of new Cr DAC data to 56 GPa): |err| 1.3138 EXCEEDS tol 0.2467 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_small_B0_prime : 247 < 1314 := by decide

/-- Cr/mace-mp-small vacancy_formation_energy = 2.6485 eV vs reference 3.0093 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.3608 EXCEEDS tol 0.1505 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_small_vacancy_formation_energy : 150 < 361 := by decide

/-- Cr/mace-mp-small gamma_100 = 3.1500 J/m^2 vs reference 3.6320 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4820 EXCEEDS tol 0.1816 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cr_mace_mp_small_gamma_100 : 182 < 482 := by decide

/-- Cr/mace-mp-small gamma_110 = 3.2662 J/m^2 vs reference 3.2010 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0652 ≤ tol 0.1601 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cr_mace_mp_small_gamma_110 : 65 ≤ 160 := by decide

end Lupine.CalcEvidence.Cr
