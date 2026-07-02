/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: Si/mace-mp-small inputs sha256 1be56dac8286.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.Si

/-- Si/mace-mp-small a0 = 5.4646 Angstrom vs reference 5.4660 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column (BAND/LCAO)): |err| 0.0014 ≤ tol 0.2733 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_Si_mace_mp_small_a0 : 1 ≤ 273 := by decide

/-- Si/mace-mp-small B0 = 71.4960 GPa vs reference 89.2000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column (SJ EOS, BAND/LCAO)): |err| 17.7040 EXCEEDS tol 4.4600 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_mace_mp_small_B0 : 4460 < 17704 := by decide

/-- Si/mace-mp-small vacancy_formation_energy = 2.0408 eV vs reference 3.6300 (N. L. Matsko, arXiv:2304.07873 (2023), Table 2 - neutral relaxed vacancy (D2d), 214/217-atom supercell, VASP PBE): |err| 1.5892 EXCEEDS tol 0.1815 eV (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_Si_mace_mp_small_vacancy_formation_energy : 182 < 1589 := by decide

end Lupine.CalcEvidence.Si
