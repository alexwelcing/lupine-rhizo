/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni/mace-mp-small inputs sha256 410358a4b398.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni

/-- Ni/mace-mp-small a0 = 3.5115 Angstrom vs reference 3.5180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0065 ≤ tol 0.1759 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mp_small_a0 : 7 ≤ 176 := by decide

/-- Ni/mace-mp-small B0 = 186.5799 GPa vs reference 187.6000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 1.0201 ≤ tol 9.3800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mp_small_B0 : 1020 ≤ 9380 := by decide

/-- Ni/mace-mp-small B0_prime = 4.6082 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-157 GPa, He medium): |err| 0.2218 ≤ tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mp_small_B0_prime : 222 ≤ 242 := by decide

/-- Ni/mace-mp-small vacancy_formation_energy = 1.0175 eV vs reference 1.3900 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.3725 EXCEEDS tol 0.0695 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_small_vacancy_formation_energy : 69 < 372 := by decide

/-- Ni/mace-mp-small gamma_100 = 2.5907 J/m^2 vs reference 2.2080 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3827 EXCEEDS tol 0.1104 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_small_gamma_100 : 110 < 383 := by decide

/-- Ni/mace-mp-small gamma_110 = 2.8427 J/m^2 vs reference 2.2860 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.5567 EXCEEDS tol 0.1143 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_small_gamma_110 : 114 < 557 := by decide

/-- Ni/mace-mp-small gamma_111 = 2.2042 J/m^2 vs reference 1.9240 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2802 EXCEEDS tol 0.0962 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_small_gamma_111 : 96 < 280 := by decide

/-- Ni/mace-mp-small stacking_fault_energy = -7.7759 mJ/m^2 vs reference 153.5600 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value (ferromagnetic Ni)): |err| 161.3359 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_small_stacking_fault_energy : 10000 < 161336 := by decide

end Lupine.CalcEvidence.Ni
