/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pt/chgnet inputs sha256 01828d7accaf.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pt

/-- Pt/chgnet a0 = 3.9744 Angstrom vs reference 3.9700 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0044 ≤ tol 0.1985 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_chgnet_a0 : 4 ≤ 198 := by decide

/-- Pt/chgnet B0 = 237.2359 GPa vs reference 277.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: R. E. MacFarlane, J. A. Rayne, C. K. Jones, Phys. Lett. 20, 234 (1966); G. Simmons and H. Wang, Single Crystal Elastic Constants and Calculated Aggregate Properties, 2nd ed. (MIT Press, 1971)): |err| 39.7641 EXCEEDS tol 13.8500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_B0 : 13850 < 39764 := by decide

/-- Pt/chgnet B0_prime = 4.5129 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-95 GPa, He medium): |err| 0.3171 EXCEEDS tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_B0_prime : 242 < 317 := by decide

/-- Pt/chgnet vacancy_formation_energy = 0.7976 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1876 EXCEEDS tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_vacancy_formation_energy : 30 < 188 := by decide

/-- Pt/chgnet gamma_100 = 1.2808 J/m^2 vs reference 1.8420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.5612 EXCEEDS tol 0.0921 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_gamma_100 : 92 < 561 := by decide

/-- Pt/chgnet gamma_110 = 1.3470 J/m^2 vs reference 1.6810 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3340 EXCEEDS tol 0.0841 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_gamma_110 : 84 < 334 := by decide

/-- Pt/chgnet gamma_111 = 1.0848 J/m^2 vs reference 1.4790 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3942 EXCEEDS tol 0.0740 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_gamma_111 : 74 < 394 := by decide

/-- Pt/chgnet stacking_fault_energy = 20.2838 mJ/m^2 vs reference 307.9700 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 287.6862 EXCEEDS tol 15.3985 mJ/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_chgnet_stacking_fault_energy : 15399 < 287686 := by decide

end Lupine.CalcEvidence.Pt
