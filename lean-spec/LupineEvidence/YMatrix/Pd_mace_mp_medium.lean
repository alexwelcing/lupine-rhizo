/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pd/mace-mp-medium inputs sha256 f9bfcbf15fb2.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pd

/-- Pd/mace-mp-medium a0 = 3.9579 Angstrom vs reference 3.9420 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0159 ≤ tol 0.1971 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mp_medium_a0 : 16 ≤ 197 := by decide

/-- Pd/mace-mp-medium B0 = 166.2542 GPa vs reference 195.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: D. K. Hsu and R. G. Leisure, Phys. Rev. B 20, 1339 (1979) - ultrasonic elastic constants): |err| 28.7458 EXCEEDS tol 9.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_medium_B0 : 9750 < 28746 := by decide

/-- Pd/mace-mp-medium vacancy_formation_energy = 1.1822 eV vs reference 1.1600 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0222 ≤ tol 0.0580 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mp_medium_vacancy_formation_energy : 22 ≤ 58 := by decide

/-- Pd/mace-mp-medium gamma_100 = 1.4008 J/m^2 vs reference 1.5260 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1252 EXCEEDS tol 0.0763 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_medium_gamma_100 : 76 < 125 := by decide

/-- Pd/mace-mp-medium gamma_110 = 1.5861 J/m^2 vs reference 1.5740 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0121 ≤ tol 0.0787 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mp_medium_gamma_110 : 12 ≤ 79 := by decide

/-- Pd/mace-mp-medium gamma_111 = 1.3032 J/m^2 vs reference 1.3380 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0348 ≤ tol 0.0669 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mp_medium_gamma_111 : 35 ≤ 67 := by decide

/-- Pd/mace-mp-medium stacking_fault_energy = 44.3075 mJ/m^2 vs reference 139.5000 (A. Linda, M. F. Akhtar, S. Pathak, S. Bhowmick, arXiv:2405.04876 (2024), Table 1 - VASP, PBE-GGA, supercell method): |err| 95.1925 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_medium_stacking_fault_energy : 10000 < 95193 := by decide

end Lupine.CalcEvidence.Pd
