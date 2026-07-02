/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: W/chgnet inputs sha256 43579766ae17.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.W

/-- W/chgnet a0 = 3.1880 Angstrom vs reference 3.1830 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0050 ≤ tol 0.1592 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_W_chgnet_a0 : 5 ≤ 159 := by decide

/-- W/chgnet B0 = 310.2765 GPa vs reference 314.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 3.9235 ≤ tol 15.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_W_chgnet_B0 : 3923 ≤ 15710 := by decide

/-- W/chgnet B0_prime = 2.8670 dimensionless vs reference 3.8200 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-155 GPa, He medium): |err| 0.9530 EXCEEDS tol 0.1910 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_chgnet_B0_prime : 191 < 953 := by decide

/-- W/chgnet vacancy_formation_energy = 1.8604 eV vs reference 3.2310 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 1.3706 EXCEEDS tol 0.1615 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_chgnet_vacancy_formation_energy : 162 < 1371 := by decide

/-- W/chgnet gamma_100 = 2.8603 J/m^2 vs reference 3.9540 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 1.0937 EXCEEDS tol 0.1977 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_chgnet_gamma_100 : 198 < 1094 := by decide

/-- W/chgnet gamma_110 = 2.3094 J/m^2 vs reference 3.2280 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.9186 EXCEEDS tol 0.1614 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_W_chgnet_gamma_110 : 161 < 919 := by decide

end Lupine.CalcEvidence.W
