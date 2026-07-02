/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Fe/mace-mpa-0-medium inputs sha256 9cfd9eb39608.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Fe

/-- Fe/mace-mpa-0-medium a0 = 2.8767 Angstrom vs reference 2.8310 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0457 ≤ tol 0.1416 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_mace_mpa_0_medium_a0 : 46 ≤ 142 := by decide

/-- Fe/mace-mpa-0-medium B0 = 199.6322 GPa vs reference 173.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 26.6322 EXCEEDS tol 8.6500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_mace_mpa_0_medium_B0 : 8650 < 26632 := by decide

/-- Fe/mace-mpa-0-medium vacancy_formation_energy = 2.2095 eV vs reference 2.1914 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells, ferromagnetic Fe)): |err| 0.0181 ≤ tol 0.1096 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_mace_mpa_0_medium_vacancy_formation_energy : 18 ≤ 110 := by decide

/-- Fe/mace-mpa-0-medium gamma_100 = 2.4986 J/m^2 vs reference 2.4990 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.0004 ≤ tol 0.1250 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_mace_mpa_0_medium_gamma_100 : 0 ≤ 125 := by decide

/-- Fe/mace-mpa-0-medium gamma_110 = 2.3273 J/m^2 vs reference 2.4470 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1197 ≤ tol 0.1224 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_mace_mpa_0_medium_gamma_110 : 120 ≤ 122 := by decide

end Lupine.CalcEvidence.Fe
