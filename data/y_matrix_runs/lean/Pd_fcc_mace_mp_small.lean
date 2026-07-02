/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pd/mace-mp-small inputs sha256 78d5cd1051a8.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pd

/-- Pd/mace-mp-small a0 = 3.9644 Angstrom vs reference 3.9420 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0224 ≤ tol 0.1971 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_mace_mp_small_a0 : 22 ≤ 197 := by decide

/-- Pd/mace-mp-small B0 = 148.5650 GPa vs reference 195.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: D. K. Hsu and R. G. Leisure, Phys. Rev. B 20, 1339 (1979) - ultrasonic elastic constants): |err| 46.4350 EXCEEDS tol 9.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_B0 : 9750 < 46435 := by decide

/-- Pd/mace-mp-small vacancy_formation_energy = 1.2411 eV vs reference 1.1600 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0811 EXCEEDS tol 0.0580 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_vacancy_formation_energy : 58 < 81 := by decide

/-- Pd/mace-mp-small gamma_100 = 1.6629 J/m^2 vs reference 1.5260 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1369 EXCEEDS tol 0.0763 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_gamma_100 : 76 < 137 := by decide

/-- Pd/mace-mp-small gamma_110 = 1.8110 J/m^2 vs reference 1.5740 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2370 EXCEEDS tol 0.0787 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_gamma_110 : 79 < 237 := by decide

/-- Pd/mace-mp-small gamma_111 = 1.4139 J/m^2 vs reference 1.3380 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0759 EXCEEDS tol 0.0669 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_gamma_111 : 67 < 76 := by decide

/-- Pd/mace-mp-small stacking_fault_energy = 26.7416 mJ/m^2 vs reference 139.5000 (A. Linda, M. F. Akhtar, S. Pathak, S. Bhowmick, arXiv:2405.04876 (2024), Table 1 - VASP, PBE-GGA, supercell method): |err| 112.7584 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_mace_mp_small_stacking_fault_energy : 10000 < 112758 := by decide

end Lupine.CalcEvidence.Pd
