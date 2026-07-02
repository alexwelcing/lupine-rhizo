/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Au/mace-mp-medium inputs sha256 f42c0ca12658.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Au

/-- Au/mace-mp-medium a0 = 4.1765 Angstrom vs reference 4.1570 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0195 ≤ tol 0.2079 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_medium_a0 : 19 ≤ 208 := by decide

/-- Au/mace-mp-medium B0 = 133.9346 GPa vs reference 180.9000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: W. B. Holzapfel, M. Hartwig, W. Sievers, J. Phys. Chem. Ref. Data 30, 515 (2001)): |err| 46.9654 EXCEEDS tol 9.0450 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_medium_B0 : 9045 < 46965 := by decide

/-- Au/mace-mp-medium B0_prime = 5.4501 dimensionless vs reference 5.4700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Takemura and Dewaele (2008) data, 0-131 GPa, He medium): |err| 0.0199 ≤ tol 0.2735 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_medium_B0_prime : 20 ≤ 274 := by decide

/-- Au/mace-mp-medium vacancy_formation_energy = 0.4394 eV vs reference 0.4000 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.0394 EXCEEDS tol 0.0200 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_medium_vacancy_formation_energy : 20 < 39 := by decide

/-- Au/mace-mp-medium gamma_100 = 0.8649 J/m^2 vs reference 0.8610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0039 ≤ tol 0.0431 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_medium_gamma_100 : 4 ≤ 43 := by decide

/-- Au/mace-mp-medium gamma_110 = 0.8769 J/m^2 vs reference 0.8270 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0499 EXCEEDS tol 0.0413 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_medium_gamma_110 : 41 < 50 := by decide

/-- Au/mace-mp-medium gamma_111 = 0.6857 J/m^2 vs reference 0.7420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0563 EXCEEDS tol 0.0371 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Au_mace_mp_medium_gamma_111 : 37 < 56 := by decide

/-- Au/mace-mp-medium stacking_fault_energy = 32.1680 mJ/m^2 vs reference 32.6900 (R. Li et al., arXiv:1511.08634 (2015), Table 3 - EMTO, PBE-GGA, gamma(9) supercell value): |err| 0.5220 ≤ tol 10.0000 mJ/m^2 (explicit). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Au_mace_mp_medium_stacking_fault_energy : 522 ≤ 10000 := by decide

end Lupine.CalcEvidence.Au
