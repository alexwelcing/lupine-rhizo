/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Si/mace-mp-medium inputs sha256 010ece34ef16.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Si

/-- Si/mace-mp-medium a0 = 5.4556 Angstrom vs reference 5.4660 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column (BAND/LCAO)): |err| 0.0104 ≤ tol 0.2733 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Si_mace_mp_medium_a0 : 10 ≤ 273 := by decide

/-- Si/mace-mp-medium B0 = 74.5624 GPa vs reference 89.2000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column (SJ EOS, BAND/LCAO)): |err| 14.6376 EXCEEDS tol 4.4600 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_mace_mp_medium_B0 : 4460 < 14638 := by decide

/-- Si/mace-mp-medium vacancy_formation_energy = 1.8494 eV vs reference 3.6300 (N. L. Matsko, arXiv:2304.07873 (2023), Table 2 - neutral relaxed vacancy (D2d), 214/217-atom supercell, VASP PBE): |err| 1.7806 EXCEEDS tol 0.1815 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_mace_mp_medium_vacancy_formation_energy : 182 < 1781 := by decide

end Lupine.CalcEvidence.Si
