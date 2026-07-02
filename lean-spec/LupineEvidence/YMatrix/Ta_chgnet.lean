/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ta/chgnet inputs sha256 b351c7ea58e9.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ta

/-- Ta/chgnet a0 = 3.3237 Angstrom vs reference 3.3180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0057 ≤ tol 0.1659 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_chgnet_a0 : 6 ≤ 166 := by decide

/-- Ta/chgnet B0 = 193.5446 GPa vs reference 194.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 0.6554 ≤ tol 9.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_chgnet_B0 : 655 ≤ 9710 := by decide

/-- Ta/chgnet B0_prime = 4.6576 dimensionless vs reference 3.1700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-90 GPa, He medium): |err| 1.4876 EXCEEDS tol 0.1585 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_chgnet_B0_prime : 158 < 1488 := by decide

/-- Ta/chgnet vacancy_formation_energy = 1.6704 eV vs reference 2.8759 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 1.2055 EXCEEDS tol 0.1438 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_chgnet_vacancy_formation_energy : 144 < 1206 := by decide

/-- Ta/chgnet gamma_100 = 2.3165 J/m^2 vs reference 2.4710 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1545 EXCEEDS tol 0.1236 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_chgnet_gamma_100 : 124 < 155 := by decide

/-- Ta/chgnet gamma_110 = 1.9194 J/m^2 vs reference 2.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.4226 EXCEEDS tol 0.1171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_chgnet_gamma_110 : 117 < 423 := by decide

end Lupine.CalcEvidence.Ta
