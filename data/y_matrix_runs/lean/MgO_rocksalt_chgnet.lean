/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: MgO/chgnet inputs sha256 7b25f25a165b.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.MgO

/-- MgO/chgnet a0 = 4.2536 Angstrom vs reference 4.2550 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0014 ≤ tol 0.2127 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_MgO_chgnet_a0 : 1 ≤ 213 := by decide

/-- MgO/chgnet B0 = 133.5174 GPa vs reference 149.0000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 15.4826 EXCEEDS tol 7.4500 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_MgO_chgnet_B0 : 7450 < 15483 := by decide

/-- MgO/chgnet B0_prime = 5.5895 dimensionless vs reference 4.0000 (S. V. Sinogeikin and J. D. Bass (2000) - (dKS/dP) at 300 K = 4.0(1); as tabulated in D. Fan et al., Am. Mineral. 104, 262 (2019), Table 2): |err| 1.5895 EXCEEDS tol 0.2000 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_MgO_chgnet_B0_prime : 200 < 1590 := by decide

end Lupine.CalcEvidence.MgO
