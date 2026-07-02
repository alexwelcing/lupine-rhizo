/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pt/mace-mp-small inputs sha256 84ae31428f62.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pt

/-- Pt/mace-mp-small a0 = 3.9820 Angstrom vs reference 3.9700 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0120 ≤ tol 0.1985 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_mace_mp_small_a0 : 12 ≤ 198 := by decide

/-- Pt/mace-mp-small B0 = 235.1239 GPa vs reference 277.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: R. E. MacFarlane, J. A. Rayne, C. K. Jones, Phys. Lett. 20, 234 (1966); G. Simmons and H. Wang, Single Crystal Elastic Constants and Calculated Aggregate Properties, 2nd ed. (MIT Press, 1971)): |err| 41.8761 EXCEEDS tol 13.8500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_B0 : 13850 < 41876 := by decide

/-- Pt/mace-mp-small B0_prime = 4.9786 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-95 GPa, He medium): |err| 0.1486 ≤ tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_mace_mp_small_B0_prime : 149 ≤ 242 := by decide

/-- Pt/mace-mp-small vacancy_formation_energy = 0.8927 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.2827 EXCEEDS tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_vacancy_formation_energy : 30 < 283 := by decide

/-- Pt/mace-mp-small gamma_100 = 2.0640 J/m^2 vs reference 1.8420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2220 EXCEEDS tol 0.0921 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_gamma_100 : 92 < 222 := by decide

/-- Pt/mace-mp-small gamma_110 = 2.2967 J/m^2 vs reference 1.6810 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.6157 EXCEEDS tol 0.0841 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_gamma_110 : 84 < 616 := by decide

/-- Pt/mace-mp-small gamma_111 = 1.6892 J/m^2 vs reference 1.4790 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2102 EXCEEDS tol 0.0740 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_gamma_111 : 74 < 210 := by decide

/-- Pt/mace-mp-small stacking_fault_energy = 66.3154 mJ/m^2 vs reference 307.9700 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 241.6546 EXCEEDS tol 15.3985 mJ/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_small_stacking_fault_energy : 15399 < 241655 := by decide

end Lupine.CalcEvidence.Pt
