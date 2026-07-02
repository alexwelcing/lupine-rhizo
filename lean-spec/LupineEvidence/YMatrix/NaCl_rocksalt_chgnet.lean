/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NaCl/chgnet inputs sha256 b9ec95789cd3.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NaCl

/-- NaCl/chgnet a0 = 5.6955 Angstrom vs reference 5.7000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0045 ≤ tol 0.2850 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NaCl_chgnet_a0 : 5 ≤ 285 := by decide

/-- NaCl/chgnet B0 = 25.0267 GPa vs reference 23.6000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 1.4267 EXCEEDS tol 1.1800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_chgnet_B0 : 1180 < 1427 := by decide

/-- NaCl/chgnet B0_prime = -0.9674 dimensionless vs reference 5.0900 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit of NaCl-B1 DAC data 0-35 GPa at 300 K (Mao ruby calibration column)): |err| 6.0574 EXCEEDS tol 0.2545 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_chgnet_B0_prime : 254 < 6057 := by decide

end Lupine.CalcEvidence.NaCl
