/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ag/mace-mp-small inputs sha256 22ac413695fd.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ag

/-- Ag/mace-mp-small a0 = 4.1679 Angstrom vs reference 4.1490 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0189 ≤ tol 0.2075 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_small_a0 : 19 ≤ 207 := by decide

/-- Ag/mace-mp-small B0 = 83.5985 GPa vs reference 110.9000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. B. Holzapfel, M. Hartwig, W. Sievers, J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 27.3015 EXCEEDS tol 5.5450 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_B0 : 5545 < 27301 := by decide

/-- Ag/mace-mp-small B0_prime = 5.5639 dimensionless vs reference 5.7000 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-124 GPa, He medium): |err| 0.1361 ≤ tol 0.2850 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_small_B0_prime : 136 ≤ 285 := by decide

/-- Ag/mace-mp-small vacancy_formation_energy = 0.6271 eV vs reference 0.6800 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0529 EXCEEDS tol 0.0340 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_vacancy_formation_energy : 34 < 53 := by decide

/-- Ag/mace-mp-small gamma_100 = 0.8932 J/m^2 vs reference 0.8100 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0832 EXCEEDS tol 0.0405 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_gamma_100 : 41 < 83 := by decide

/-- Ag/mace-mp-small gamma_110 = 0.9473 J/m^2 vs reference 0.8660 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0813 EXCEEDS tol 0.0433 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_gamma_110 : 43 < 81 := by decide

/-- Ag/mace-mp-small gamma_111 = 0.6901 J/m^2 vs reference 0.7730 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0829 EXCEEDS tol 0.0387 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_gamma_111 : 39 < 83 := by decide

/-- Ag/mace-mp-small stacking_fault_energy = 0.8901 mJ/m^2 vs reference 17.2600 (R. Li, S. Lu, D. Kim, S. Schonecker, J. Zhao, S. K. Kwon, L. Vitos, arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 16.3699 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_small_stacking_fault_energy : 10000 < 16370 := by decide

end Lupine.CalcEvidence.Ag
