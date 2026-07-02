/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ca/mace-mpa-0-medium inputs sha256 cb186dbf0ac3.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ca

/-- Ca/mace-mpa-0-medium a0 = 5.5449 Angstrom vs reference 5.5270 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0179 ≤ tol 0.2764 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ca_mace_mpa_0_medium_a0 : 18 ≤ 276 := by decide

/-- Ca/mace-mpa-0-medium B0 = 16.2953 GPa vs reference 18.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: M. S. Anderson, C. A. Swenson, D. T. Peterson, Phys. Rev. B 41, 3329 (1990)): |err| 2.1047 EXCEEDS tol 0.9200 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mpa_0_medium_B0 : 920 < 2105 := by decide

/-- Ca/mace-mpa-0-medium vacancy_formation_energy = 1.0205 eV vs reference 1.1300 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1095 EXCEEDS tol 0.0565 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mpa_0_medium_vacancy_formation_energy : 56 < 109 := by decide

/-- Ca/mace-mpa-0-medium gamma_100 = 0.4290 J/m^2 vs reference 0.4580 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0290 EXCEEDS tol 0.0229 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mpa_0_medium_gamma_100 : 23 < 29 := by decide

/-- Ca/mace-mpa-0-medium gamma_110 = 0.4711 J/m^2 vs reference 0.5420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0709 EXCEEDS tol 0.0271 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mpa_0_medium_gamma_110 : 27 < 71 := by decide

/-- Ca/mace-mpa-0-medium gamma_111 = 0.3956 J/m^2 vs reference 0.4610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0654 EXCEEDS tol 0.0231 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mpa_0_medium_gamma_111 : 23 < 65 := by decide

end Lupine.CalcEvidence.Ca
