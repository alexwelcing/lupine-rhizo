/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: MgO/mace-mpa-0-medium inputs sha256 ca0c654b7436.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.MgO

/-- MgO/mace-mpa-0-medium a0 = 4.2565 Angstrom vs reference 4.2550 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0015 ≤ tol 0.2127 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mpa_0_medium_a0 : 1 ≤ 213 := by decide

/-- MgO/mace-mpa-0-medium B0 = 148.1193 GPa vs reference 149.0000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 0.8807 ≤ tol 7.4500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mpa_0_medium_B0 : 881 ≤ 7450 := by decide

/-- MgO/mace-mpa-0-medium B0_prime = 4.2413 dimensionless vs reference 4.0000 (S. V. Sinogeikin and J. D. Bass (2000) - (dKS/dP) at 300 K = 4.0(1); as tabulated in D. Fan et al., Am. Mineral. 104, 262 (2019), Table 2): |err| 0.2413 EXCEEDS tol 0.2000 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_MgO_mace_mpa_0_medium_B0_prime : 200 < 241 := by decide

end Lupine.CalcEvidence.MgO
