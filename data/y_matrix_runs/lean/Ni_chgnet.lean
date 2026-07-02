/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ni/chgnet inputs sha256 b3447c2e57aa.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ni

/-- Ni/chgnet a0 = 3.5035 Angstrom vs reference 3.5180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0145 ≤ tol 0.1759 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_chgnet_a0 : 14 ≤ 176 := by decide

/-- Ni/chgnet B0 = 206.3216 GPa vs reference 187.6000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 18.7216 EXCEEDS tol 9.3800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_B0 : 9380 < 18722 := by decide

/-- Ni/chgnet B0_prime = 4.6595 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-157 GPa, He medium): |err| 0.1705 ≤ tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ni_chgnet_B0_prime : 171 ≤ 242 := by decide

/-- Ni/chgnet vacancy_formation_energy = 1.2274 eV vs reference 1.3900 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1626 EXCEEDS tol 0.0695 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_vacancy_formation_energy : 69 < 163 := by decide

/-- Ni/chgnet gamma_100 = 1.9523 J/m^2 vs reference 2.2080 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2557 EXCEEDS tol 0.1104 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_gamma_100 : 110 < 256 := by decide

/-- Ni/chgnet gamma_110 = 2.0647 J/m^2 vs reference 2.2860 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2213 EXCEEDS tol 0.1143 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_gamma_110 : 114 < 221 := by decide

/-- Ni/chgnet gamma_111 = 1.7211 J/m^2 vs reference 1.9240 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2029 EXCEEDS tol 0.0962 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_gamma_111 : 96 < 203 := by decide

/-- Ni/chgnet stacking_fault_energy = 22.1469 mJ/m^2 vs reference 153.5600 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value (ferromagnetic Ni)): |err| 131.4131 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ni_chgnet_stacking_fault_energy : 10000 < 131413 := by decide

end Lupine.CalcEvidence.Ni
