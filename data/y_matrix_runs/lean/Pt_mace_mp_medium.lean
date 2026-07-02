/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Pt/mace-mp-medium inputs sha256 4ef136f0f549.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Pt

/-- Pt/mace-mp-medium a0 = 3.9762 Angstrom vs reference 3.9700 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0062 ≤ tol 0.1985 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_mace_mp_medium_a0 : 6 ≤ 198 := by decide

/-- Pt/mace-mp-medium B0 = 226.7230 GPa vs reference 277.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: R. E. MacFarlane, J. A. Rayne, C. K. Jones, Phys. Lett. 20, 234 (1966); G. Simmons and H. Wang, Single Crystal Elastic Constants and Calculated Aggregate Properties, 2nd ed. (MIT Press, 1971)): |err| 50.2770 EXCEEDS tol 13.8500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_medium_B0 : 13850 < 50277 := by decide

/-- Pt/mace-mp-medium B0_prime = 4.7709 dimensionless vs reference 4.8300 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-95 GPa, He medium): |err| 0.0591 ≤ tol 0.2415 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_mace_mp_medium_B0_prime : 59 ≤ 242 := by decide

/-- Pt/mace-mp-medium vacancy_formation_energy = 0.4392 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1708 EXCEEDS tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_medium_vacancy_formation_energy : 30 < 171 := by decide

/-- Pt/mace-mp-medium gamma_100 = 1.6241 J/m^2 vs reference 1.8420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2179 EXCEEDS tol 0.0921 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_medium_gamma_100 : 92 < 218 := by decide

/-- Pt/mace-mp-medium gamma_110 = 1.6477 J/m^2 vs reference 1.6810 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0333 ≤ tol 0.0841 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Pt_mace_mp_medium_gamma_110 : 33 ≤ 84 := by decide

/-- Pt/mace-mp-medium gamma_111 = 1.2739 J/m^2 vs reference 1.4790 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2051 EXCEEDS tol 0.0740 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_medium_gamma_111 : 74 < 205 := by decide

/-- Pt/mace-mp-medium stacking_fault_energy = 105.7079 mJ/m^2 vs reference 307.9700 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 202.2621 EXCEEDS tol 15.3985 mJ/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Pt_mace_mp_medium_stacking_fault_energy : 15399 < 202262 := by decide

end Lupine.CalcEvidence.Pt
