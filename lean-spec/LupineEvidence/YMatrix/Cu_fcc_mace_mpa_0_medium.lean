/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cu/mace-mpa-0-medium inputs sha256 27f497be27a0.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cu

/-- Cu/mace-mpa-0-medium a0 = 3.6398 Angstrom vs reference 3.6310 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0088 ≤ tol 0.1815 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cu_mace_mpa_0_medium_a0 : 9 ≤ 182 := by decide

/-- Cu/mace-mpa-0-medium B0 = 130.2437 GPa vs reference 142.3000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. C. Overton and J. Gaffney, Phys. Rev. 98, 969 (1955); W. B. Holzapfel et al., J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 12.0563 EXCEEDS tol 7.1150 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_mace_mpa_0_medium_B0 : 7115 < 12056 := by decide

/-- Cu/mace-mpa-0-medium B0_prime = 4.3813 dimensionless vs reference 4.9100 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 0.5287 EXCEEDS tol 0.2455 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_mace_mpa_0_medium_B0_prime : 246 < 529 := by decide

/-- Cu/mace-mpa-0-medium vacancy_formation_energy = 1.0675 eV vs reference 1.0700 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0025 ≤ tol 0.0535 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cu_mace_mpa_0_medium_vacancy_formation_energy : 3 ≤ 54 := by decide

/-- Cu/mace-mpa-0-medium gamma_100 = 1.4176 J/m^2 vs reference 1.4680 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0504 ≤ tol 0.0734 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cu_mace_mpa_0_medium_gamma_100 : 50 ≤ 73 := by decide

/-- Cu/mace-mpa-0-medium gamma_110 = 1.5139 J/m^2 vs reference 1.5610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0471 ≤ tol 0.0781 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cu_mace_mpa_0_medium_gamma_110 : 47 ≤ 78 := by decide

/-- Cu/mace-mpa-0-medium gamma_111 = 1.2284 J/m^2 vs reference 1.3140 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0856 EXCEEDS tol 0.0657 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_mace_mpa_0_medium_gamma_111 : 66 < 86 := by decide

/-- Cu/mace-mpa-0-medium stacking_fault_energy = 27.8823 mJ/m^2 vs reference 47.4500 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 19.5677 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_mace_mpa_0_medium_stacking_fault_energy : 10000 < 19568 := by decide

end Lupine.CalcEvidence.Cu
