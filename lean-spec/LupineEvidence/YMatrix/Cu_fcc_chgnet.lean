/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Cu/chgnet inputs sha256 f56b8eaa5364.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Cu

/-- Cu/chgnet a0 = 3.6159 Angstrom vs reference 3.6310 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0151 ≤ tol 0.1815 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Cu_chgnet_a0 : 15 ≤ 182 := by decide

/-- Cu/chgnet B0 = 155.2361 GPa vs reference 142.3000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. C. Overton and J. Gaffney, Phys. Rev. 98, 969 (1955); W. B. Holzapfel et al., J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 12.9361 EXCEEDS tol 7.1150 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_B0 : 7115 < 12936 := by decide

/-- Cu/chgnet B0_prime = 4.2013 dimensionless vs reference 4.9100 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 0.7087 EXCEEDS tol 0.2455 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_B0_prime : 246 < 709 := by decide

/-- Cu/chgnet vacancy_formation_energy = 0.7122 eV vs reference 1.0700 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.3578 EXCEEDS tol 0.0535 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_vacancy_formation_energy : 54 < 358 := by decide

/-- Cu/chgnet gamma_100 = 1.0179 J/m^2 vs reference 1.4680 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4501 EXCEEDS tol 0.0734 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_gamma_100 : 73 < 450 := by decide

/-- Cu/chgnet gamma_110 = 1.1245 J/m^2 vs reference 1.5610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4365 EXCEEDS tol 0.0781 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_gamma_110 : 78 < 436 := by decide

/-- Cu/chgnet gamma_111 = 0.8358 J/m^2 vs reference 1.3140 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4782 EXCEEDS tol 0.0657 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_gamma_111 : 66 < 478 := by decide

/-- Cu/chgnet stacking_fault_energy = -28.4887 mJ/m^2 vs reference 47.4500 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 75.9387 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Cu_chgnet_stacking_fault_energy : 10000 < 75939 := by decide

end Lupine.CalcEvidence.Cu
