/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NaCl/mace-mp-medium inputs sha256 aaebe27e603b.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NaCl

/-- NaCl/mace-mp-medium a0 = 5.6832 Angstrom vs reference 5.7000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0168 ≤ tol 0.2850 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NaCl_mace_mp_medium_a0 : 17 ≤ 285 := by decide

/-- NaCl/mace-mp-medium B0 = 25.4281 GPa vs reference 23.6000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 1.8281 EXCEEDS tol 1.1800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_mace_mp_medium_B0 : 1180 < 1828 := by decide

/-- NaCl/mace-mp-medium B0_prime = 5.2205 dimensionless vs reference 5.0900 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit of NaCl-B1 DAC data 0-35 GPa at 300 K (Mao ruby calibration column)): |err| 0.1305 ≤ tol 0.2545 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NaCl_mace_mp_medium_B0_prime : 131 ≤ 254 := by decide

end Lupine.CalcEvidence.NaCl
