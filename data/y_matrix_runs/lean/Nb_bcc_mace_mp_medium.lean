/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Nb/mace-mp-medium inputs sha256 89575d213179.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Nb

/-- Nb/mace-mp-medium a0 = 3.3134 Angstrom vs reference 3.3100 (G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table II, PBE 'Uncorr.' column (FHI-aims, all-electron, no zero-point correction)): |err| 0.0034 ≤ tol 0.1655 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Nb_mace_mp_medium_a0 : 3 ≤ 166 := by decide

/-- Nb/mace-mp-medium B0 = 155.0670 GPa vs reference 174.0000 (Experimental bulk modulus as tabulated in G.-X. Zhang, A. M. Reilly, A. Tkatchenko, M. Scheffler, New J. Phys. 20, 063020 (2018), supplementary Table IV 'Exp.' column; primary: G. A. Alers and D. L. Waldorf, Phys. Rev. Lett. 6, 677 (1961); K. A. Jones et al., Acta Metall. 17, 365 (1969); W. C. Hubbell and F. R. Brotzen, J. Appl. Phys. 43, 3306 (1972)): |err| 18.9330 EXCEEDS tol 8.7000 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Nb_mace_mp_medium_B0 : 8700 < 18933 := by decide

/-- Nb/mace-mp-medium vacancy_formation_energy = 2.2306 eV vs reference 2.6589 (P.-W. Ma and S. L. Dudarev, Phys. Rev. Materials 3, 013605 (2019), Table IV (GGA-PBE, stress-free relaxed supercells)): |err| 0.4283 EXCEEDS tol 0.1329 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Nb_mace_mp_medium_vacancy_formation_energy : 133 < 428 := by decide

/-- Nb/mace-mp-medium gamma_100 = 2.5433 J/m^2 vs reference 2.2750 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.2683 EXCEEDS tol 0.1138 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Nb_mace_mp_medium_gamma_100 : 114 < 268 := by decide

/-- Nb/mace-mp-medium gamma_110 = 2.4654 J/m^2 vs reference 2.0740 (R. Tran, Z. Xu, B. Radhakrishnan, D. Winston, W. Sun, K. A. Persson, S. P. Ong, Surface energies of elemental crystals, Sci. Data 3, 160080 (2016); dataset: Dryad doi:10.5061/dryad.f2n6f, file surfaces.json (VASP, PBE-GGA)): |err| 0.3914 EXCEEDS tol 0.1037 J/m^2 (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Nb_mace_mp_medium_gamma_110 : 104 < 391 := by decide

end Lupine.CalcEvidence.Nb
