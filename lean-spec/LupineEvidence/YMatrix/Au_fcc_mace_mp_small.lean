/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Au/mace-mp-small inputs sha256 9689f0a88abe.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Au

/-- Au/mace-mp-small a0 = 4.1681 Angstrom vs reference 4.1570 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0111 ≤ tol 0.2079 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_small_a0 : 11 ≤ 208 := by decide

/-- Au/mace-mp-small B0 = 132.7825 GPa vs reference 180.9000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. B. Holzapfel, M. Hartwig, W. Sievers, J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 48.1175 EXCEEDS tol 9.0450 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_B0 : 9045 < 48117 := by decide

/-- Au/mace-mp-small B0_prime = 5.9061 dimensionless vs reference 5.4700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Takemura and Dewaele (2008) data, 0-131 GPa, He medium): |err| 0.4361 EXCEEDS tol 0.2735 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_B0_prime : 274 < 436 := by decide

/-- Au/mace-mp-small vacancy_formation_energy = 0.4356 eV vs reference 0.4000 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0356 EXCEEDS tol 0.0200 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_vacancy_formation_energy : 20 < 36 := by decide

/-- Au/mace-mp-small gamma_100 = 0.9660 J/m^2 vs reference 0.8610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1050 EXCEEDS tol 0.0431 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_gamma_100 : 43 < 105 := by decide

/-- Au/mace-mp-small gamma_110 = 1.0069 J/m^2 vs reference 0.8270 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1799 EXCEEDS tol 0.0413 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_gamma_110 : 41 < 180 := by decide

/-- Au/mace-mp-small gamma_111 = 0.7535 J/m^2 vs reference 0.7420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0115 ≤ tol 0.0371 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_small_gamma_111 : 11 ≤ 37 := by decide

/-- Au/mace-mp-small stacking_fault_energy = 56.6563 mJ/m^2 vs reference 32.6900 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 23.9663 EXCEEDS tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_small_stacking_fault_energy : 10000 < 23966 := by decide

end Lupine.CalcEvidence.Au
