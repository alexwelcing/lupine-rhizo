/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni/mace-mp-medium inputs sha256 c8378911fd78.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni

/-- Ni/mace-mp-medium a0 = 3.5104 Angstrom vs reference 3.5180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0076 ≤ tol 0.1759 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mp_medium_a0 : 8 ≤ 176 := by decide

/-- Ni/mace-mp-medium B0 = 211.5933 GPa vs reference 187.6000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 23.9933 EXCEEDS tol 9.3800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_B0 : 9380 < 23993 := by decide

/-- Ni/mace-mp-medium B0_prime = 5.1638 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-157 GPa, He medium): |err| 0.3338 EXCEEDS tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_B0_prime : 242 < 334 := by decide

/-- Ni/mace-mp-medium vacancy_formation_energy = 1.1154 eV vs reference 1.3900 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.2746 EXCEEDS tol 0.0695 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_vacancy_formation_energy : 69 < 275 := by decide

/-- Ni/mace-mp-medium gamma_100 = 1.9345 J/m^2 vs reference 2.2080 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2735 EXCEEDS tol 0.1104 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_gamma_100 : 110 < 273 := by decide

/-- Ni/mace-mp-medium gamma_110 = 2.1412 J/m^2 vs reference 2.2860 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1448 EXCEEDS tol 0.1143 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_gamma_110 : 114 < 145 := by decide

/-- Ni/mace-mp-medium gamma_111 = 1.8310 J/m^2 vs reference 1.9240 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0930 ≤ tol 0.0962 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_mace_mp_medium_gamma_111 : 93 ≤ 96 := by decide

/-- Ni/mace-mp-medium stacking_fault_energy = 10.5665 mJ/m^2 vs reference 153.5600 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value (ferromagnetic Ni)): |err| 142.9935 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_mace_mp_medium_stacking_fault_energy : 10000 < 142993 := by decide

end Lupine.CalcEvidence.Ni
