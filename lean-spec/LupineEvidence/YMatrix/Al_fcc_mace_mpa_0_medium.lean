/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Al/mace-mpa-0-medium inputs sha256 5e532312c775.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Al

/-- Al/mace-mpa-0-medium a0 = 4.0386 Angstrom vs reference 4.0410 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0024 ≤ tol 0.2021 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mpa_0_medium_a0 : 2 ≤ 202 := by decide

/-- Al/mace-mpa-0-medium B0 = 81.8289 GPa vs reference 79.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: G. N. Kamm and G. A. Alers, J. Appl. Phys. 35, 327 (1964) - ultrasonic single-crystal elastic constants): |err| 2.4289 ≤ tol 3.9700 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mpa_0_medium_B0 : 2429 ≤ 3970 := by decide

/-- Al/mace-mpa-0-medium B0_prime = 3.9026 dimensionless vs reference 4.1600 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 0.2574 EXCEEDS tol 0.2080 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mpa_0_medium_B0_prime : 208 < 257 := by decide

/-- Al/mace-mpa-0-medium vacancy_formation_energy = 0.6781 eV vs reference 0.6100 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0681 EXCEEDS tol 0.0305 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mpa_0_medium_vacancy_formation_energy : 30 < 68 := by decide

/-- Al/mace-mpa-0-medium gamma_100 = 0.9968 J/m^2 vs reference 0.9150 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0818 EXCEEDS tol 0.0458 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mpa_0_medium_gamma_100 : 46 < 82 := by decide

/-- Al/mace-mpa-0-medium gamma_110 = 0.9429 J/m^2 vs reference 0.9770 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0341 ≤ tol 0.0489 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mpa_0_medium_gamma_110 : 34 ≤ 49 := by decide

/-- Al/mace-mpa-0-medium gamma_111 = 0.7840 J/m^2 vs reference 0.7950 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0110 ≤ tol 0.0398 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Al_mace_mpa_0_medium_gamma_111 : 11 ≤ 40 := by decide

/-- Al/mace-mpa-0-medium stacking_fault_energy = 87.4074 mJ/m^2 vs reference 117.5400 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 30.1326 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Al_mace_mpa_0_medium_stacking_fault_energy : 10000 < 30133 := by decide

end Lupine.CalcEvidence.Al
