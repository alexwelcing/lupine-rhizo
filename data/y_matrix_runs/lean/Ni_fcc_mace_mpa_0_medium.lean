/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni/mace-mpa-0-medium inputs sha256 35ede5aaf6a6.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni

/-- Ni/mace-mpa-0-medium a0 = 3.5213 Angstrom vs reference 3.5180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0033 ≤ tol 0.1759 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mpa_0_medium_a0 : 3 ≤ 176 := by decide

/-- Ni/mace-mpa-0-medium B0 = 215.9762 GPa vs reference 187.6000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 28.3762 EXCEEDS tol 9.3800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_B0 : 9380 < 28376 := by decide

/-- Ni/mace-mpa-0-medium B0_prime = 5.6153 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-157 GPa, He medium): |err| 0.7853 EXCEEDS tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_B0_prime : 242 < 785 := by decide

/-- Ni/mace-mpa-0-medium vacancy_formation_energy = 1.5398 eV vs reference 1.3900 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1498 EXCEEDS tol 0.0695 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_vacancy_formation_energy : 69 < 150 := by decide

/-- Ni/mace-mpa-0-medium gamma_100 = 3.2907 J/m^2 vs reference 2.2080 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 1.0827 EXCEEDS tol 0.1104 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_gamma_100 : 110 < 1083 := by decide

/-- Ni/mace-mpa-0-medium gamma_110 = 3.2668 J/m^2 vs reference 2.2860 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.9808 EXCEEDS tol 0.1143 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_gamma_110 : 114 < 981 := by decide

/-- Ni/mace-mpa-0-medium gamma_111 = 2.6092 J/m^2 vs reference 1.9240 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.6852 EXCEEDS tol 0.0962 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_gamma_111 : 96 < 685 := by decide

/-- Ni/mace-mpa-0-medium stacking_fault_energy = 88.2657 mJ/m^2 vs reference 153.5600 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value (ferromagnetic Ni)): |err| 65.2943 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mpa_0_medium_stacking_fault_energy : 10000 < 65294 := by decide

end Lupine.CalcEvidence.Ni
