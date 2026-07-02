/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: W/mace-mpa-0-medium inputs sha256 89c35ed5e3cc.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.W

/-- W/mace-mpa-0-medium a0 = 3.1748 Angstrom vs reference 3.1830 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0082 ≤ tol 0.1592 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_W_mace_mpa_0_medium_a0 : 8 ≤ 159 := by decide

/-- W/mace-mpa-0-medium B0 = 368.4093 GPa vs reference 314.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 54.2093 EXCEEDS tol 15.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_mace_mpa_0_medium_B0 : 15710 < 54209 := by decide

/-- W/mace-mpa-0-medium B0_prime = 7.9088 dimensionless vs reference 3.8200 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 4.0888 EXCEEDS tol 0.1910 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_mace_mpa_0_medium_B0_prime : 191 < 4089 := by decide

/-- W/mace-mpa-0-medium vacancy_formation_energy = 3.4040 eV vs reference 3.2310 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.1730 EXCEEDS tol 0.1615 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_mace_mpa_0_medium_vacancy_formation_energy : 162 < 173 := by decide

/-- W/mace-mpa-0-medium gamma_100 = 4.0639 J/m^2 vs reference 3.9540 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1099 ≤ tol 0.1977 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_W_mace_mpa_0_medium_gamma_100 : 110 ≤ 198 := by decide

/-- W/mace-mpa-0-medium gamma_110 = 3.2646 J/m^2 vs reference 3.2280 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0366 ≤ tol 0.1614 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_W_mace_mpa_0_medium_gamma_110 : 37 ≤ 161 := by decide

end Lupine.CalcEvidence.W
