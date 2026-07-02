/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Al/mace-mp-small inputs sha256 a2b27337539d.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Al

/-- Al/mace-mp-small a0 = 4.0531 Angstrom vs reference 4.0410 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0121 ≤ tol 0.2021 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mp_small_a0 : 12 ≤ 202 := by decide

/-- Al/mace-mp-small B0 = 79.4687 GPa vs reference 79.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: G. N. Kamm and G. A. Alers, J. Appl. Phys. 35, 327 (1964) - ultrasonic single-crystal elastic constants): |err| 0.0687 ≤ tol 3.9700 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mp_small_B0 : 69 ≤ 3970 := by decide

/-- Al/mace-mp-small B0_prime = 4.5905 dimensionless vs reference 4.1600 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 0.4305 EXCEEDS tol 0.2080 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mp_small_B0_prime : 208 < 431 := by decide

/-- Al/mace-mp-small vacancy_formation_energy = 0.5851 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0249 ≤ tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mp_small_vacancy_formation_energy : 25 ≤ 30 := by decide

/-- Al/mace-mp-small gamma_100 = 0.8183 J/m^2 vs reference 0.9150 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0967 EXCEEDS tol 0.0458 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mp_small_gamma_100 : 46 < 97 := by decide

/-- Al/mace-mp-small gamma_110 = 0.8700 J/m^2 vs reference 0.9770 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1070 EXCEEDS tol 0.0489 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mp_small_gamma_110 : 49 < 107 := by decide

/-- Al/mace-mp-small gamma_111 = 0.6447 J/m^2 vs reference 0.7950 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1503 EXCEEDS tol 0.0398 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mp_small_gamma_111 : 40 < 150 := by decide

/-- Al/mace-mp-small stacking_fault_energy = -7.6202 mJ/m^2 vs reference 117.5400 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 125.1602 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mp_small_stacking_fault_energy : 10000 < 125160 := by decide

end Lupine.CalcEvidence.Al
