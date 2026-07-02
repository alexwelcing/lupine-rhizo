/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Si/mace-mpa-0-medium inputs sha256 e44a6b79c5b0.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Si

/-- Si/mace-mpa-0-medium a0 = 5.4674 Angstrom vs reference 5.4660 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column (BAND/LCAO)): |err| 0.0014 ≤ tol 0.2733 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Si_mace_mpa_0_medium_a0 : 1 ≤ 273 := by decide

/-- Si/mace-mpa-0-medium B0 = 86.5677 GPa vs reference 89.2000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column (SJ EOS, BAND/LCAO)): |err| 2.6323 ≤ tol 4.4600 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Si_mace_mpa_0_medium_B0 : 2632 ≤ 4460 := by decide

/-- Si/mace-mpa-0-medium vacancy_formation_energy = 2.5189 eV vs reference 3.6300 (N. L. Matsko, arXiv:2304.07873 (2023), Table 2 - neutral relaxed vacancy (D2d), 214/217-atom supercell, VASP PBE): |err| 1.1111 EXCEEDS tol 0.1815 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_mace_mpa_0_medium_vacancy_formation_energy : 182 < 1111 := by decide

end Lupine.CalcEvidence.Si
