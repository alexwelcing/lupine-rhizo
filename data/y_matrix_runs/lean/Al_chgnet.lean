/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Al/chgnet inputs sha256 65264a68fb96.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Al

/-- Al/chgnet a0 = 4.0414 Angstrom vs reference 4.0410 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0004 ≤ tol 0.2021 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_chgnet_a0 : 0 ≤ 202 := by decide

/-- Al/chgnet B0 = 54.1877 GPa vs reference 79.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: G. N. Kamm and G. A. Alers, J. Appl. Phys. 35, 327 (1964) - ultrasonic single-crystal elastic constants): |err| 25.2123 EXCEEDS tol 3.9700 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_B0 : 3970 < 25212 := by decide

/-- Al/chgnet B0_prime = 20.1857 dimensionless vs reference 4.1600 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 16.0257 EXCEEDS tol 0.2080 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_B0_prime : 208 < 16026 := by decide

/-- Al/chgnet vacancy_formation_energy = 0.1372 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.4728 EXCEEDS tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_vacancy_formation_energy : 30 < 473 := by decide

/-- Al/chgnet gamma_100 = 0.4775 J/m^2 vs reference 0.9150 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4375 EXCEEDS tol 0.0458 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_gamma_100 : 46 < 438 := by decide

/-- Al/chgnet gamma_110 = 0.5169 J/m^2 vs reference 0.9770 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4601 EXCEEDS tol 0.0489 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_gamma_110 : 49 < 460 := by decide

/-- Al/chgnet gamma_111 = 0.3732 J/m^2 vs reference 0.7950 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4218 EXCEEDS tol 0.0398 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_gamma_111 : 40 < 422 := by decide

/-- Al/chgnet stacking_fault_energy = 8.2098 mJ/m^2 vs reference 117.5400 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 109.3302 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_chgnet_stacking_fault_energy : 10000 < 109330 := by decide

end Lupine.CalcEvidence.Al
