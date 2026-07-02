/- AUTHORED from registered H4 transfer analysis (Y-matrix Round 1).
   Input: h4_transfer.json sha256 be02d2a687ea; seed 20260702; LOO scalar-bulk operator.
   Registered verdict: INCONCLUSIVE (neither pass nor kill fired). The decidable
   sub-facts below are the routing knowledge: the per-model stiffness scalar fails
   to improve even its own fitted family — correction structure is finer than
   (model) or (model, family). (median |rel err| x1000) -/

namespace Lupine.YMatrix.Round1.H4

/-- H4 mace-mp-small: the LOO scalar does NOT improve its own fitted family — EOS median |err| 0.125 → 0.149. Routing fact: no per-model scalar gear exists even within EOS. -/
theorem h4_no_self_improvement_mace_mp_small : 125 ≤ 149 := by decide

/-- H4 mace-mp-medium: the LOO scalar does NOT improve its own fitted family — EOS median |err| 0.147 → 0.167. Routing fact: no per-model scalar gear exists even within EOS. -/
theorem h4_no_self_improvement_mace_mp_medium : 147 ≤ 167 := by decide

/-- H4 mace-mp-medium/planar_fault: isolated significant improvement 0.682 → 0.665 (bootstrap-significant). Candidate gear, unregistered — replication required before routing. -/
theorem h4_isolated_improvement_mace_mp_medium_planar_fault : 665 < 682 := by decide

/-- H4 chgnet: the LOO scalar does NOT improve its own fitted family — EOS median |err| 0.144 → 0.213. Routing fact: no per-model scalar gear exists even within EOS. -/
theorem h4_no_self_improvement_chgnet : 144 ≤ 213 := by decide

/-- H4 chgnet/surfaces: isolated significant improvement 0.285 → 0.215 (bootstrap-significant). Candidate gear, unregistered — replication required before routing. -/
theorem h4_isolated_improvement_chgnet_surfaces : 215 < 285 := by decide

end Lupine.YMatrix.Round1.H4