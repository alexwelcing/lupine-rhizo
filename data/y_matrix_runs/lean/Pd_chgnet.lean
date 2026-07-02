/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pd/chgnet inputs sha256 1eeb6ecb25db.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pd

/-- Pd/chgnet a0 = 3.9513 Angstrom vs reference 3.9420 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0093 ≤ tol 0.1971 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pd_chgnet_a0 : 9 ≤ 197 := by decide

/-- Pd/chgnet B0 = 158.2892 GPa vs reference 195.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: D. K. Hsu and R. G. Leisure, Phys. Rev. B 20, 1339 (1979) - ultrasonic elastic constants): |err| 36.7108 EXCEEDS tol 9.7500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_B0 : 9750 < 36711 := by decide

/-- Pd/chgnet vacancy_formation_energy = 0.8659 eV vs reference 1.1600 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.2941 EXCEEDS tol 0.0580 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_vacancy_formation_energy : 58 < 294 := by decide

/-- Pd/chgnet gamma_100 = 1.1027 J/m^2 vs reference 1.5260 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4233 EXCEEDS tol 0.0763 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_gamma_100 : 76 < 423 := by decide

/-- Pd/chgnet gamma_110 = 1.2052 J/m^2 vs reference 1.5740 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3688 EXCEEDS tol 0.0787 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_gamma_110 : 79 < 369 := by decide

/-- Pd/chgnet gamma_111 = 0.9561 J/m^2 vs reference 1.3380 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3819 EXCEEDS tol 0.0669 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_gamma_111 : 67 < 382 := by decide

/-- Pd/chgnet stacking_fault_energy = 5.3519 mJ/m^2 vs reference 139.5000 (A. Linda, M. F. Akhtar, S. Pathak, S. Bhowmick, arXiv:2405.04876 (2024), Table 1 - VASP, PBE-GGA, supercell method): |err| 134.1481 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pd_chgnet_stacking_fault_energy : 10000 < 134148 := by decide

end Lupine.CalcEvidence.Pd
