/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Sr/chgnet inputs sha256 427f5eb6a1e8.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Sr

/-- Sr/chgnet a0 = 6.0354 Angstrom vs reference 6.0200 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0154 ≤ tol 0.3010 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Sr_chgnet_a0 : 15 ≤ 301 := by decide

/-- Sr/chgnet B0 = 11.3749 GPa vs reference 12.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: M. S. Anderson, C. A. Swenson, D. T. Peterson, Phys. Rev. B 41, 3329 (1990)): |err| 1.0251 EXCEEDS tol 0.6200 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_chgnet_B0 : 620 < 1025 := by decide

/-- Sr/chgnet vacancy_formation_energy = 0.5630 eV vs reference 0.9500 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.3870 EXCEEDS tol 0.0475 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_chgnet_vacancy_formation_energy : 48 < 387 := by decide

/-- Sr/chgnet gamma_100 = 0.2251 J/m^2 vs reference 0.3470 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1219 EXCEEDS tol 0.0174 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_chgnet_gamma_100 : 17 < 122 := by decide

/-- Sr/chgnet gamma_110 = 0.2495 J/m^2 vs reference 0.4070 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1575 EXCEEDS tol 0.0204 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_chgnet_gamma_110 : 20 < 157 := by decide

/-- Sr/chgnet gamma_111 = 0.1748 J/m^2 vs reference 0.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1672 EXCEEDS tol 0.0171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Sr_chgnet_gamma_111 : 17 < 167 := by decide

end Lupine.CalcEvidence.Sr
