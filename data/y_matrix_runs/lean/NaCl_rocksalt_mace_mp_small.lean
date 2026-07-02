/- AUTHORED by lupine_distill.lammps_ingest from calculator evidence.
   Inputs: NaCl/mace-mp-small inputs sha256 98674ed5aa1d.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.CalcEvidence.NaCl

/-- NaCl/mace-mp-small a0 = 5.6900 Angstrom vs reference 5.7000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table I, PBE column): |err| 0.0100 ≤ tol 0.2850 Angstrom (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_within_tol_NaCl_mace_mp_small_a0 : 10 ≤ 285 := by decide

/-- NaCl/mace-mp-small B0 = 27.1860 GPa vs reference 23.6000 (G. I. Csonka et al., Phys. Rev. B 79, 155107 (2009), Table V, PBE column): |err| 3.5860 EXCEEDS tol 1.1800 GPa (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_mace_mp_small_B0 : 1180 < 3586 := by decide

/-- NaCl/mace-mp-small B0_prime = 4.6755 dimensionless vs reference 5.0900 (A. Dewaele, Minerals 9, 684 (2019), Table 1 - Rydberg-Vinet fit of NaCl-B1 DAC data 0-35 GPa at 300 K (Mao ruby calibration column)): |err| 0.4145 EXCEEDS tol 0.2545 dimensionless (5%). Machine-checked from calculator evidence (abs error x1000). -/
theorem calc_exceeds_tol_NaCl_mace_mp_small_B0_prime : 254 < 415 := by decide

end Lupine.CalcEvidence.NaCl
