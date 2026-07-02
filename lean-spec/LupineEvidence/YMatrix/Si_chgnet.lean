/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Si/chgnet inputs sha256 2f2442721fa9.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Si

/-- Si/chgnet a0 = 5.4671 Angstrom vs reference 5.4660 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column (BAND/LCAO)): |err| 0.0011 ≤ tol 0.2733 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Si_chgnet_a0 : 1 ≤ 273 := by decide

/-- Si/chgnet B0 = 78.2138 GPa vs reference 89.2000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column (SJ EOS, BAND/LCAO)): |err| 10.9862 EXCEEDS tol 4.4600 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_chgnet_B0 : 4460 < 10986 := by decide

/-- Si/chgnet vacancy_formation_energy = 0.8676 eV vs reference 3.6300 (N. L. Matsko, arXiv:2304.07873 (2023), Table 2 - neutral relaxed vacancy (D2d), 214/217-atom supercell, VASP PBE): |err| 2.7624 EXCEEDS tol 0.1815 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_chgnet_vacancy_formation_energy : 182 < 2762 := by decide

end Lupine.CalcEvidence.Si
