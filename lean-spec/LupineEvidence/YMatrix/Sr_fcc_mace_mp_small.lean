/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Sr/mace-mp-small inputs sha256 c397ef130c8a.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Sr

/-- Sr/mace-mp-small a0 = 5.9925 Angstrom vs reference 6.0200 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0275 ≤ tol 0.3010 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Sr_mace_mp_small_a0 : 28 ≤ 301 := by decide

/-- Sr/mace-mp-small B0 = 15.2392 GPa vs reference 12.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: M. S. Anderson, C. A. Swenson, D. T. Peterson, Phys. Rev. B 41, 3329 (1990)): |err| 2.8392 EXCEEDS tol 0.6200 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_mace_mp_small_B0 : 620 < 2839 := by decide

/-- Sr/mace-mp-small vacancy_formation_energy = 0.7827 eV vs reference 0.9500 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1673 EXCEEDS tol 0.0475 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_mace_mp_small_vacancy_formation_energy : 48 < 167 := by decide

/-- Sr/mace-mp-small gamma_100 = 0.2917 J/m^2 vs reference 0.3470 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0553 EXCEEDS tol 0.0174 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_mace_mp_small_gamma_100 : 17 < 55 := by decide

/-- Sr/mace-mp-small gamma_110 = 0.3200 J/m^2 vs reference 0.4070 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0870 EXCEEDS tol 0.0204 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_mace_mp_small_gamma_110 : 20 < 87 := by decide

/-- Sr/mace-mp-small gamma_111 = 0.2358 J/m^2 vs reference 0.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1062 EXCEEDS tol 0.0171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_mace_mp_small_gamma_111 : 17 < 106 := by decide

end Lupine.CalcEvidence.Sr
