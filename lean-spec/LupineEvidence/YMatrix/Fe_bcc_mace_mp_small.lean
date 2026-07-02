/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Fe/mace-mp-small inputs sha256 d80ce9e8ddc2.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Fe

/-- Fe/mace-mp-small a0 = 2.8609 Angstrom vs reference 2.8310 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0299 ≤ tol 0.1416 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Fe_mace_mp_small_a0 : 30 ≤ 142 := by decide

/-- Fe/mace-mp-small B0 = 86.7834 GPa vs reference 173.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: O. L. Anderson, in Physical Acoustics, Vol. III-B (Academic, 1965); V. L. Moruzzi and P. M. Marcus, Phys. Rev. B 48, 7665 (1993)): |err| 86.2166 EXCEEDS tol 8.6500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_mace_mp_small_B0 : 8650 < 86217 := by decide

/-- Fe/mace-mp-small vacancy_formation_energy = 1.6142 eV vs reference 2.1914 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells, ferromagnetic Fe)): |err| 0.5772 EXCEEDS tol 0.1096 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_mace_mp_small_vacancy_formation_energy : 110 < 577 := by decide

/-- Fe/mace-mp-small gamma_100 = 2.6278 J/m^2 vs reference 2.4990 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1288 EXCEEDS tol 0.1250 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_mace_mp_small_gamma_100 : 125 < 129 := by decide

/-- Fe/mace-mp-small gamma_110 = 2.5963 J/m^2 vs reference 2.4470 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.1493 EXCEEDS tol 0.1224 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Fe_mace_mp_small_gamma_110 : 122 < 149 := by decide

end Lupine.CalcEvidence.Fe
