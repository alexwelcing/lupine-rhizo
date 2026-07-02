/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Mo/mace-mpa-0-medium inputs sha256 e3d2e2f43e46.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Mo

/-- Mo/mace-mpa-0-medium a0 = 3.1512 Angstrom vs reference 3.1610 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0098 ≤ tol 0.1581 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mpa_0_medium_a0 : 10 ≤ 158 := by decide

/-- Mo/mace-mpa-0-medium B0 = 308.3701 GPa vs reference 265.3000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 43.0701 EXCEEDS tol 13.2650 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mpa_0_medium_B0 : 13265 < 43070 := by decide

/-- Mo/mace-mpa-0-medium B0_prime = 6.0206 dimensionless vs reference 3.3400 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-124 GPa, He medium): |err| 2.6806 EXCEEDS tol 0.1670 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mpa_0_medium_B0_prime : 167 < 2681 := by decide

/-- Mo/mace-mpa-0-medium vacancy_formation_energy = 2.9254 eV vs reference 2.7955 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.1299 ≤ tol 0.1398 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mpa_0_medium_vacancy_formation_energy : 130 ≤ 140 := by decide

/-- Mo/mace-mpa-0-medium gamma_100 = 3.2287 J/m^2 vs reference 3.1820 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0467 ≤ tol 0.1591 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mpa_0_medium_gamma_100 : 47 ≤ 159 := by decide

/-- Mo/mace-mpa-0-medium gamma_110 = 2.7559 J/m^2 vs reference 2.7970 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0411 ≤ tol 0.1399 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mpa_0_medium_gamma_110 : 41 ≤ 140 := by decide

end Lupine.CalcEvidence.Mo
