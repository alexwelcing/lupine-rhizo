/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Ta/mace-mp-small inputs sha256 678313aae730.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Ta

/-- Ta/mace-mp-small a0 = 3.3204 Angstrom vs reference 3.3180 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0024 ≤ tol 0.1659 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Ta_mace_mp_small_a0 : 2 ≤ 166 := by decide

/-- Ta/mace-mp-small B0 = 206.0281 GPa vs reference 194.2000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: F. H. Featherston and J. R. Neighbours, Phys. Rev. 130, 1324 (1963) - ultrasonic elastic constants): |err| 11.8281 EXCEEDS tol 9.7100 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_small_B0 : 9710 < 11828 := by decide

/-- Ta/mace-mp-small B0_prime = 4.9454 dimensionless vs reference 3.1700 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit at 300 K (Mao ruby calibration column) of Dewaele, Loubeyre, Mezouar, Phys. Rev. B 70, 094112 (2004) data, 0-90 GPa, He medium): |err| 1.7754 EXCEEDS tol 0.1585 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_small_B0_prime : 158 < 1775 := by decide

/-- Ta/mace-mp-small vacancy_formation_energy = 3.3245 eV vs reference 2.8759 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.4486 EXCEEDS tol 0.1438 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_small_vacancy_formation_energy : 144 < 449 := by decide

/-- Ta/mace-mp-small gamma_100 = 3.0214 J/m^2 vs reference 2.4710 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.5504 EXCEEDS tol 0.1236 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_small_gamma_100 : 124 < 550 := by decide

/-- Ta/mace-mp-small gamma_110 = 2.7053 J/m^2 vs reference 2.3420 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3633 EXCEEDS tol 0.1171 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Ta_mace_mp_small_gamma_110 : 117 < 363 := by decide

end Lupine.CalcEvidence.Ta
