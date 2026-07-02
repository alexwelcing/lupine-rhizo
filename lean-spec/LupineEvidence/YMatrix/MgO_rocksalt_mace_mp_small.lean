/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: MgO/mace-mp-small inputs sha256 f82407270eb6.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.MgO

/-- MgO/mace-mp-small a0 = 4.2533 Angstrom vs reference 4.2550 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0017 ≤ tol 0.2127 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mp_small_a0 : 2 ≤ 213 := by decide

/-- MgO/mace-mp-small B0 = 149.3580 GPa vs reference 149.0000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 0.3580 ≤ tol 7.4500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mp_small_B0 : 358 ≤ 7450 := by decide

/-- MgO/mace-mp-small B0_prime = 3.8238 dimensionless vs reference 4.0000 (S. V. Sinogeikin and J. D. Bass (2000) - (dKS/dP) at 300 K = 4.0(1); as tabulated in D. Fan et al., Am. Mineral. 104, 262 (2019), Table 2): |err| 0.1762 ≤ tol 0.2000 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_mace_mp_small_B0_prime : 176 ≤ 200 := by decide

end Lupine.CalcEvidence.MgO
