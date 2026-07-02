/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pd/mace-mpa-0-medium inputs sha256 c789568ca087.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pd

/-- Pd/mace-mpa-0-medium a0 = 3.9596 Angstrom vs reference 3.9420 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0176 ≤ tol 0.1971 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mpa_0_medium_a0 : 18 ≤ 197 := by decide

/-- Pd/mace-mpa-0-medium B0 = 140.2987 GPa vs reference 195.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: D. K. Hsu and R. G. Leisure, Phys. Rev. B 20, 1339 (1979) - ultrasonic elastic constants): |err| 54.7013 EXCEEDS tol 9.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mpa_0_medium_B0 : 9750 < 54701 := by decide

/-- Pd/mace-mpa-0-medium vacancy_formation_energy = 1.2100 eV vs reference 1.1600 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0500 ≤ tol 0.0580 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mpa_0_medium_vacancy_formation_energy : 50 ≤ 58 := by decide

/-- Pd/mace-mpa-0-medium gamma_100 = 1.5966 J/m^2 vs reference 1.5260 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0706 ≤ tol 0.0763 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mpa_0_medium_gamma_100 : 71 ≤ 76 := by decide

/-- Pd/mace-mpa-0-medium gamma_110 = 1.6276 J/m^2 vs reference 1.5740 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0536 ≤ tol 0.0787 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mpa_0_medium_gamma_110 : 54 ≤ 79 := by decide

/-- Pd/mace-mpa-0-medium gamma_111 = 1.3473 J/m^2 vs reference 1.3380 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0093 ≤ tol 0.0669 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mpa_0_medium_gamma_111 : 9 ≤ 67 := by decide

/-- Pd/mace-mpa-0-medium stacking_fault_energy = 86.9810 mJ/m^2 vs reference 139.5000 (A. Linda, M. F. Akhtar, S. Pathak, S. Bhowmick, arXiv:2405.04876 (2024), Table 1 - VASP, PBE-GGA, supercell method): |err| 52.5190 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mpa_0_medium_stacking_fault_energy : 10000 < 52519 := by decide

end Lupine.CalcEvidence.Pd
