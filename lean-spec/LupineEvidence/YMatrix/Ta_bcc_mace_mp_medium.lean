/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ta/mace-mp-medium inputs sha256 6f14824e8198.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ta

/-- Ta/mace-mp-medium a0 = 3.3139 Angstrom vs reference 3.3180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0041 ≤ tol 0.1659 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mp_medium_a0 : 4 ≤ 166 := by decide

/-- Ta/mace-mp-medium B0 = 201.7362 GPa vs reference 194.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 7.5362 ≤ tol 9.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mp_medium_B0 : 7536 ≤ 9710 := by decide

/-- Ta/mace-mp-medium B0_prime = 5.6240 dimensionless vs reference 3.1700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-90 GPa, He medium): |err| 2.4540 EXCEEDS tol 0.1585 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_medium_B0_prime : 158 < 2454 := by decide

/-- Ta/mace-mp-medium vacancy_formation_energy = 2.6370 eV vs reference 2.8759 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.2389 EXCEEDS tol 0.1438 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_medium_vacancy_formation_energy : 144 < 239 := by decide

/-- Ta/mace-mp-medium gamma_100 = 2.4303 J/m^2 vs reference 2.4710 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0407 ≤ tol 0.1236 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mp_medium_gamma_100 : 41 ≤ 124 := by decide

/-- Ta/mace-mp-medium gamma_110 = 2.1656 J/m^2 vs reference 2.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1764 EXCEEDS tol 0.1171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_medium_gamma_110 : 117 < 176 := by decide

end Lupine.CalcEvidence.Ta
