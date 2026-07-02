/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NaCl/mace-mpa-0-medium inputs sha256 79e97a8d9af9.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NaCl

/-- NaCl/mace-mpa-0-medium a0 = 5.7135 Angstrom vs reference 5.7000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0135 ≤ tol 0.2850 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NaCl_mace_mpa_0_medium_a0 : 13 ≤ 285 := by decide

/-- NaCl/mace-mpa-0-medium B0 = 20.9037 GPa vs reference 23.6000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 2.6963 EXCEEDS tol 1.1800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_mace_mpa_0_medium_B0 : 1180 < 2696 := by decide

/-- NaCl/mace-mpa-0-medium B0_prime = 3.8602 dimensionless vs reference 5.0900 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit of NaCl-B1 DAC data 0-35 GPa at 300 K (Mao ruby calibration column)): |err| 1.2298 EXCEEDS tol 0.2545 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_mace_mpa_0_medium_B0_prime : 254 < 1230 := by decide

end Lupine.CalcEvidence.NaCl
