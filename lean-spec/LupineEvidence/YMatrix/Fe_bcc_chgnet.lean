/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Fe/chgnet inputs sha256 5e9df5d8478c.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Fe

/-- Fe/chgnet a0 = 2.8451 Angstrom vs reference 2.8310 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0141 ≤ tol 0.1416 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_chgnet_a0 : 14 ≤ 142 := by decide

/-- Fe/chgnet B0 = 88.8229 GPa vs reference 173.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 84.1771 EXCEEDS tol 8.6500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_chgnet_B0 : 8650 < 84177 := by decide

/-- Fe/chgnet vacancy_formation_energy = 0.8337 eV vs reference 2.1914 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells, ferromagnetic Fe)): |err| 1.3577 EXCEEDS tol 0.1096 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_chgnet_vacancy_formation_energy : 110 < 1358 := by decide

/-- Fe/chgnet gamma_100 = 1.5386 J/m^2 vs reference 2.4990 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.9604 EXCEEDS tol 0.1250 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_chgnet_gamma_100 : 125 < 960 := by decide

/-- Fe/chgnet gamma_110 = 1.1605 J/m^2 vs reference 2.4470 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 1.2865 EXCEEDS tol 0.1224 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_chgnet_gamma_110 : 122 < 1286 := by decide

end Lupine.CalcEvidence.Fe
