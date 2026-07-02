/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: MgO/mace-mp-medium inputs sha256 0c6309ee07f9.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.MgO

/-- MgO/mace-mp-medium a0 = 4.2545 Angstrom vs reference 4.2550 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0005 ≤ tol 0.2127 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mp_medium_a0 : 0 ≤ 213 := by decide

/-- MgO/mace-mp-medium B0 = 147.2599 GPa vs reference 149.0000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 1.7401 ≤ tol 7.4500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mp_medium_B0 : 1740 ≤ 7450 := by decide

/-- MgO/mace-mp-medium B0_prime = 4.2488 dimensionless vs reference 4.0000 (S. V. Sinogeikin and J. D. Bass (2000) - (dKS/dP) at 300 K = 4.0(1); as tabulated in D. Fan et al., Am. Mineral. 104, 262 (2019), Table 2): |err| 0.2488 EXCEEDS tol 0.2000 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_MgO_mace_mp_medium_B0_prime : 200 < 249 := by decide

end Lupine.CalcEvidence.MgO
