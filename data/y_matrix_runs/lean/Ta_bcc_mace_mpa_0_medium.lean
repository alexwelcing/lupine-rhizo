/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ta/mace-mpa-0-medium inputs sha256 db031f717673.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ta

/-- Ta/mace-mpa-0-medium a0 = 3.3187 Angstrom vs reference 3.3180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0007 ≤ tol 0.1659 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mpa_0_medium_a0 : 1 ≤ 166 := by decide

/-- Ta/mace-mpa-0-medium B0 = 202.8531 GPa vs reference 194.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 8.6531 ≤ tol 9.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mpa_0_medium_B0 : 8653 ≤ 9710 := by decide

/-- Ta/mace-mpa-0-medium B0_prime = 7.6824 dimensionless vs reference 3.1700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-90 GPa, He medium): |err| 4.5124 EXCEEDS tol 0.1585 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mpa_0_medium_B0_prime : 158 < 4512 := by decide

/-- Ta/mace-mpa-0-medium vacancy_formation_energy = 2.7616 eV vs reference 2.8759 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.1143 ≤ tol 0.1438 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mpa_0_medium_vacancy_formation_energy : 114 ≤ 144 := by decide

/-- Ta/mace-mpa-0-medium gamma_100 = 2.4472 J/m^2 vs reference 2.4710 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0238 ≤ tol 0.1236 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mpa_0_medium_gamma_100 : 24 ≤ 124 := by decide

/-- Ta/mace-mpa-0-medium gamma_110 = 2.2071 J/m^2 vs reference 2.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1349 EXCEEDS tol 0.1171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mpa_0_medium_gamma_110 : 117 < 135 := by decide

end Lupine.CalcEvidence.Ta
