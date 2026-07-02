/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Au/chgnet inputs sha256 357acda625ea.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Au

/-- Au/chgnet a0 = 4.1698 Angstrom vs reference 4.1570 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0128 ≤ tol 0.2079 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_chgnet_a0 : 13 ≤ 208 := by decide

/-- Au/chgnet B0 = 123.2609 GPa vs reference 180.9000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. B. Holzapfel, M. Hartwig, W. Sievers, J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 57.6391 EXCEEDS tol 9.0450 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_B0 : 9045 < 57639 := by decide

/-- Au/chgnet B0_prime = 8.3527 dimensionless vs reference 5.4700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Takemura and Dewaele (2008) data, 0-131 GPa, He medium): |err| 2.8827 EXCEEDS tol 0.2735 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_B0_prime : 274 < 2883 := by decide

/-- Au/chgnet vacancy_formation_energy = 0.3000 eV vs reference 0.4000 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1000 EXCEEDS tol 0.0200 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_vacancy_formation_energy : 20 < 100 := by decide

/-- Au/chgnet gamma_100 = 0.4238 J/m^2 vs reference 0.8610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4372 EXCEEDS tol 0.0431 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_gamma_100 : 43 < 437 := by decide

/-- Au/chgnet gamma_110 = 0.4460 J/m^2 vs reference 0.8270 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3810 EXCEEDS tol 0.0413 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_gamma_110 : 41 < 381 := by decide

/-- Au/chgnet gamma_111 = 0.3550 J/m^2 vs reference 0.7420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3870 EXCEEDS tol 0.0371 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_gamma_111 : 37 < 387 := by decide

/-- Au/chgnet stacking_fault_energy = 17.5179 mJ/m^2 vs reference 32.6900 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 15.1721 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_chgnet_stacking_fault_energy : 10000 < 15172 := by decide

end Lupine.CalcEvidence.Au
