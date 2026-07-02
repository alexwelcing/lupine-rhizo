/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ag/mace-mp-medium inputs sha256 d8a22886c444.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ag

/-- Ag/mace-mp-medium a0 = 4.1677 Angstrom vs reference 4.1490 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0187 ≤ tol 0.2075 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_a0 : 19 ≤ 207 := by decide

/-- Ag/mace-mp-medium B0 = 88.6334 GPa vs reference 110.9000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. B. Holzapfel, M. Hartwig, W. Sievers, J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 22.2666 EXCEEDS tol 5.5450 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_medium_B0 : 5545 < 22267 := by decide

/-- Ag/mace-mp-medium B0_prime = 5.7883 dimensionless vs reference 5.7000 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-124 GPa, He medium): |err| 0.0883 ≤ tol 0.2850 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_B0_prime : 88 ≤ 285 := by decide

/-- Ag/mace-mp-medium vacancy_formation_energy = 0.6802 eV vs reference 0.6800 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0002 ≤ tol 0.0340 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_vacancy_formation_energy : 0 ≤ 34 := by decide

/-- Ag/mace-mp-medium gamma_100 = 0.8059 J/m^2 vs reference 0.8100 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0041 ≤ tol 0.0405 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_gamma_100 : 4 ≤ 41 := by decide

/-- Ag/mace-mp-medium gamma_110 = 0.8441 J/m^2 vs reference 0.8660 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0219 ≤ tol 0.0433 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_gamma_110 : 22 ≤ 43 := by decide

/-- Ag/mace-mp-medium gamma_111 = 0.6971 J/m^2 vs reference 0.7730 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0759 EXCEEDS tol 0.0387 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ag_mace_mp_medium_gamma_111 : 39 < 76 := by decide

/-- Ag/mace-mp-medium stacking_fault_energy = 8.8138 mJ/m^2 vs reference 17.2600 (R. Li, S. Lu, D. Kim, S. Schonecker, J. Zhao, S. K. Kwon, L. Vitos, arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 8.4462 ≤ tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ag_mace_mp_medium_stacking_fault_energy : 8446 ≤ 10000 := by decide

end Lupine.CalcEvidence.Ag
