/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Mo/mace-mp-small inputs sha256 6b39c510bb06.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Mo

/-- Mo/mace-mp-small a0 = 3.1569 Angstrom vs reference 3.1610 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0041 ≤ tol 0.1581 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mp_small_a0 : 4 ≤ 158 := by decide

/-- Mo/mace-mp-small B0 = 231.5643 GPa vs reference 265.3000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 33.7357 EXCEEDS tol 13.2650 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mp_small_B0 : 13265 < 33736 := by decide

/-- Mo/mace-mp-small B0_prime = 7.8547 dimensionless vs reference 3.3400 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele et al. (2008) data, 0-124 GPa, He medium): |err| 4.5147 EXCEEDS tol 0.1670 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mp_small_B0_prime : 167 < 4515 := by decide

/-- Mo/mace-mp-small vacancy_formation_energy = 3.3737 eV vs reference 2.7955 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.5782 EXCEEDS tol 0.1398 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mp_small_vacancy_formation_energy : 140 < 578 := by decide

/-- Mo/mace-mp-small gamma_100 = 3.1866 J/m^2 vs reference 3.1820 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0046 ≤ tol 0.1591 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Mo_mace_mp_small_gamma_100 : 5 ≤ 159 := by decide

/-- Mo/mace-mp-small gamma_110 = 2.5723 J/m^2 vs reference 2.7970 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2247 EXCEEDS tol 0.1399 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Mo_mace_mp_small_gamma_110 : 140 < 225 := by decide

end Lupine.CalcEvidence.Mo
