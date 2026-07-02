/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: V/mace-mpa-0-medium inputs sha256 51f639dd2577.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.V

/-- V/mace-mpa-0-medium a0 = 2.9794 Angstrom vs reference 2.9960 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0166 ≤ tol 0.1498 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_V_mace_mpa_0_medium_a0 : 17 ≤ 150 := by decide

/-- V/mace-mpa-0-medium B0 = 185.5164 GPa vs reference 157.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: G. A. Alers, Phys. Rev. 119, 1532 (1960) - ultrasonic elastic constants): |err| 28.5164 EXCEEDS tol 7.8500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_V_mace_mpa_0_medium_B0 : 7850 < 28516 := by decide

/-- V/mace-mpa-0-medium vacancy_formation_energy = 2.7268 eV vs reference 2.0422 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.6846 EXCEEDS tol 0.1021 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_V_mace_mpa_0_medium_vacancy_formation_energy : 102 < 685 := by decide

/-- V/mace-mpa-0-medium gamma_100 = 2.7455 J/m^2 vs reference 2.3810 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3645 EXCEEDS tol 0.1190 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_V_mace_mpa_0_medium_gamma_100 : 119 < 365 := by decide

/-- V/mace-mpa-0-medium gamma_110 = 2.4994 J/m^2 vs reference 2.4210 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0784 ≤ tol 0.1210 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_V_mace_mpa_0_medium_gamma_110 : 78 ≤ 121 := by decide

end Lupine.CalcEvidence.V
