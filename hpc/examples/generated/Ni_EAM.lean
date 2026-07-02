/- AUTHORED by lupine_distill.lammps_ingest from LAMMPS log evidence.
   Inputs: Ni/Ni_u3.eam log sha256 e806686e8220; Ni/Ni_u3.eam log sha256 1f4da1ebb707.
   Decidable Nat facts (abs error vs reference, x1000) — 0 sorry. -/

namespace Lupine.LammpsEvidence.Ni

/-- Ni/Ni_u3.eam C11 = 246.7900 GPa vs reference 246.5000 (Simmons & Wang 1971 (300 K single-crystal experiment)): |err| 0.2900 ≤ tol 12.3250 GPa (5%). Machine-checked from LAMMPS log evidence (abs error x1000). -/
theorem lammps_within_tol_Ni_Ni_u3_eam_C11 : 290 ≤ 12325 := by decide

/-- Ni/Ni_u3.eam C12 = 147.3200 GPa vs reference 147.3000 (Simmons & Wang 1971 (300 K single-crystal experiment)): |err| 0.0200 ≤ tol 7.3650 GPa (5%). Machine-checked from LAMMPS log evidence (abs error x1000). -/
theorem lammps_within_tol_Ni_Ni_u3_eam_C12 : 20 ≤ 7365 := by decide

/-- Ni/Ni_u3.eam C44 = 124.8500 GPa vs reference 124.7000 (Simmons & Wang 1971 (300 K single-crystal experiment)): |err| 0.1500 ≤ tol 6.2350 GPa (5%). Machine-checked from LAMMPS log evidence (abs error x1000). -/
theorem lammps_within_tol_Ni_Ni_u3_eam_C44 : 150 ≤ 6235 := by decide

end Lupine.LammpsEvidence.Ni
