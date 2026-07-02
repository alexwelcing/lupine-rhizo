/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ca/mace-mp-small inputs sha256 29135511cc7e.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ca

/-- Ca/mace-mp-small a0 = 5.5163 Angstrom vs reference 5.5270 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0107 ≤ tol 0.2764 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ca_mace_mp_small_a0 : 11 ≤ 276 := by decide

/-- Ca/mace-mp-small B0 = 20.7050 GPa vs reference 18.4000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: M. S. Anderson, C. A. Swenson, D. T. Peterson, Phys. Rev. B 41, 3329 (1990)): |err| 2.3050 EXCEEDS tol 0.9200 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mp_small_B0 : 920 < 2305 := by decide

/-- Ca/mace-mp-small vacancy_formation_energy = 1.0145 eV vs reference 1.1300 (T. Angsten, T. Mayeshiba, H. Wu, D. Morgan, New J. Phys. 16, 015018 (2014), Table A.1 (VASP 5.2.2, PBE-GGA)): |err| 0.1155 EXCEEDS tol 0.0565 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mp_small_vacancy_formation_energy : 56 < 115 := by decide

/-- Ca/mace-mp-small gamma_100 = 0.4786 J/m^2 vs reference 0.4580 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0206 ≤ tol 0.0229 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ca_mace_mp_small_gamma_100 : 21 ≤ 23 := by decide

/-- Ca/mace-mp-small gamma_110 = 0.5198 J/m^2 vs reference 0.5420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0222 ≤ tol 0.0271 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ca_mace_mp_small_gamma_110 : 22 ≤ 27 := by decide

/-- Ca/mace-mp-small gamma_111 = 0.3935 J/m^2 vs reference 0.4610 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0675 EXCEEDS tol 0.0231 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ca_mace_mp_small_gamma_111 : 23 < 67 := by decide

end Lupine.CalcEvidence.Ca
